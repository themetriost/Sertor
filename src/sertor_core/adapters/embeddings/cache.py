"""Embedding cache by content-hash (019, REQ-H4).

Re-indexing an unchanged corpus should not re-pay the embedding cost. `CachingEmbedder` is a
DECORATOR of the `EmbeddingProvider` port: it serves a chunk's vector from a persistent cache when
its `(model, content-hash)` key is known, and delegates only the misses to the wrapped embedder.
`services/indexing.py` is untouched — the decorator is transparent (Principio I: extend in
adapters + composition, not in services).

The cache is an OPTIMISATION, never a source of truth: a store failure degrades to a cache miss
with a warning, never an indexing error (FR-004 — not "silent null": a miss is a legitimate
outcome). Vectors round-trip as float64 (`array('d')`) so a cached index is byte-equivalent to fresh
(FR-005).
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
from array import array
from pathlib import Path

from sertor_core.domain.ports import EmbeddingProvider
from sertor_core.observability.logging import log_event

# SQLite parameter limit is 999; chunk the `IN (...)` lookups well below it.
_LOOKUP_CHUNK = 500


def _content_hash(text: str) -> str:
    """Stable key for a chunk's text: sha256 hex (position-independent → free dedup)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """Persistent `(model, content_hash) -> vector` store backed by SQLite (stdlib only).

    Lives at `<index_dir>/embed_cache.sqlite` (git-ignored cache artifact). Never raises on store
    failure: `get` returns no hit, `put` is a no-op, both emit a warning (FR-004).
    """

    def __init__(self, index_dir: Path | str):
        self._path = Path(index_dir) / "embed_cache.sqlite"
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Open the DB and ensure the schema (lazy, idempotent). May raise `sqlite3.Error`."""
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._path)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS embeddings "
                "(model TEXT, content_hash TEXT, vector BLOB, PRIMARY KEY (model, content_hash))"
            )
            self._conn = conn  # assigned only after a successful CREATE (corrupt file → stays None)
        return self._conn

    def get(self, model: str, hashes: list[str]) -> dict[str, list[float]]:
        """Map `content_hash -> vector` for the keys present under `model` (missing ones absent)."""
        if not hashes:
            return {}
        try:
            conn = self._connect()
            out: dict[str, list[float]] = {}
            for start in range(0, len(hashes), _LOOKUP_CHUNK):
                batch = hashes[start : start + _LOOKUP_CHUNK]
                placeholders = ",".join("?" * len(batch))
                rows = conn.execute(
                    f"SELECT content_hash, vector FROM embeddings "
                    f"WHERE model = ? AND content_hash IN ({placeholders})",
                    [model, *batch],
                ).fetchall()
                for content_hash, blob in rows:
                    vec = array("d")
                    vec.frombytes(blob)
                    out[content_hash] = vec.tolist()
            return out
        except sqlite3.Error as exc:
            log_event(logging.WARNING, "embeddings_cache_unavailable",
                      provider=model, reason=type(exc).__name__)
            return {}

    def put(self, model: str, items: list[tuple[str, list[float]]]) -> None:
        """Insert new `(content_hash, vector)` pairs (idempotent via INSERT OR IGNORE)."""
        if not items:
            return
        try:
            conn = self._connect()
            conn.executemany(
                "INSERT OR IGNORE INTO embeddings (model, content_hash, vector) VALUES (?, ?, ?)",
                [(model, h, array("d", vector).tobytes()) for h, vector in items],
            )
            conn.commit()
        except sqlite3.Error as exc:
            log_event(logging.WARNING, "embeddings_cache_unavailable",
                      provider=model, reason=type(exc).__name__)


class CachingEmbedder:
    """`EmbeddingProvider` decorator that memoises embeddings by content-hash.

    Order-preserving, with in-call dedup (identical texts embed once). The wrapped embedder keeps
    its own behaviour (retry, token logging, `EmbeddingError` on provider failures): the cache only
    spares it the chunks already known.
    """

    def __init__(self, inner: EmbeddingProvider, cache: EmbeddingCache):
        self._inner = inner
        self._cache = cache
        self.name = inner.name
        self.batch_size = inner.batch_size
        self.dim = inner.dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        hashes = [_content_hash(t) for t in texts]
        cached = self._cache.get(self._inner.name, hashes)

        # Unique misses in first-seen order: a text repeated in this call is embedded once (D8).
        miss_texts: list[str] = []
        miss_hashes: list[str] = []
        seen: set[str] = set()
        for text, content_hash in zip(texts, hashes, strict=True):
            if content_hash not in cached and content_hash not in seen:
                seen.add(content_hash)
                miss_texts.append(text)
                miss_hashes.append(content_hash)

        fresh: dict[str, list[float]] = {}
        if miss_texts:
            vectors = self._inner.embed(miss_texts)
            fresh = dict(zip(miss_hashes, vectors, strict=True))
            self._cache.put(self._inner.name, list(fresh.items()))

        # Reassemble in the original order; `fresh` covers every miss, `cached` every hit.
        out = [cached[h] if h in cached else fresh[h] for h in hashes]
        if out:
            self.dim = len(out[0])  # correct even at 100% cache-hit (inner never called)

        hits = sum(1 for content_hash in hashes if content_hash in cached)
        log_event(logging.INFO, "embeddings_cache",
                  provider=self._inner.name, hits=hits, misses=len(texts) - hits, total=len(texts))
        return out
