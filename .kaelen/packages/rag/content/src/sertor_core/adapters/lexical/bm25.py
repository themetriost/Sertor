"""Adapter `LexicalIndex` on BM25 (rank-bm25) with a persisted JSON sidecar (FEAT-004, group A).

The sidecar lives in the same namespaced index directory as the vector store
(`<index_dir>/lexical/<collection>.json`, REQ-072): the collection name already encodes
`(corpus, provider)` → free namespacing (REQ-005). Persisting an artifact makes
the **absence of the index detectable** (pre-hybrid corpus), the trigger for the degradation
REQ-034 — the policy belongs to the engine, only `exists()` lives here.

Text is stored raw and tokenised on load; the BM25 index is built in memory once per
collection and cached in the instance (typical corpora < 10k chunks).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from sertor_core.domain.entities import LexicalEntry
from sertor_core.domain.errors import ConfigError
from sertor_core.domain.ports import DocTypeFilter

_FORMAT = "sertor.lexical/1"
_TOKENIZER_VERSION = 1
_WORD = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    """Lowercase tokens; for snake_case also adds sub-tokens (REQ-001).

    This is the differentiator for exact-symbol queries (on par with prototype 02).
    """
    out: list[str] = []
    for word in _WORD.findall(text.lower()):
        out.append(word)
        if "_" in word:
            out.extend(part for part in word.split("_") if part)
    return out


class Bm25LexicalIndex:
    """`LexicalIndex` on BM25Okapi + atomic JSON sidecar."""

    def __init__(self, index_dir: Path | str):
        self._dir = Path(index_dir) / "lexical"
        # per-collection cache: on-disk token (mtime_ns, size) -> (entries, bm25, token_sets).
        # Invalidated by a changed/vanished sidecar on disk (staleness auto-heal, see `_load`) as
        # well as by build/reset in-process.
        self._cache: dict[
            str, tuple[tuple[int, int], tuple[list[LexicalEntry], object, list[set[str]]]]
        ] = {}

    def _sidecar(self, collection: str) -> Path:
        return self._dir / f"{collection}.json"

    def build(self, collection: str, entries: list[LexicalEntry]) -> None:
        """Fully replaces the sidecar (complete snapshot, idempotent, atomic)."""
        self._dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": _FORMAT,
            "tokenizer_version": _TOKENIZER_VERSION,
            "collection": collection,
            "entries": [
                {"chunk_id": e.chunk_id, "path": e.path, "doc_type": e.doc_type, "text": e.text}
                for e in entries
            ],
        }
        # Atomic write: tmp in the same directory + replace (sidecar never left truncated).
        fd, tmp_name = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            os.replace(tmp_name, self._sidecar(collection))
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
        self._cache.pop(collection, None)

    def _load(self, collection: str) -> tuple[list[LexicalEntry], object, list[set[str]]]:
        path = self._sidecar(collection)
        # Reload when the sidecar changed on disk (mtime+size): keeps a long-lived server (the MCP
        # memoizes this adapter, and the default engine is hybrid) from fusing against a lexical
        # corpus left stale by a re-index in another process — the missing leg of the staleness
        # auto-heal, twin of the code-graph reload (adapters/graph/networkx_graph.py) and the
        # Chroma client refresh (adapters/vectorstores/chroma.py).
        try:
            stat = path.stat()
        except OSError:
            self._cache.pop(collection, None)  # a vanished sidecar invalidates a stale cache
            token: tuple[int, int] | None = None
        else:
            token = (stat.st_mtime_ns, stat.st_size)
            cached = self._cache.get(collection)
            if cached is not None and cached[0] == token:
                return cached[1]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"corrupt lexical sidecar: {path} — rebuild it with a re-index",
            ) from exc
        if data.get("format") != _FORMAT:
            raise ConfigError(
                f"unrecognised lexical sidecar format ({data.get('format')!r}): "
                f"{path} — rebuild it with a re-index",
            )
        entries = [
            LexicalEntry(item["chunk_id"], item["text"], item["doc_type"], item["path"])
            for item in data.get("entries", [])
        ]
        bm25 = None
        token_sets: list[set[str]] = []
        if entries:
            from rank_bm25 import BM25Okapi

            tokenized = [tokenize(e.text) or [""] for e in entries]
            bm25 = BM25Okapi(tokenized)
            token_sets = [set(tokens) for tokens in tokenized]
        result = (entries, bm25, token_sets)
        if token is not None:
            self._cache[collection] = (token, result)
        return result

    def query(
        self,
        collection: str,
        query: str,
        k: int,
        doc_type: DocTypeFilter = "both",
    ) -> list[str]:
        if k <= 0:
            return []
        entries, bm25, token_sets = self._load(collection)
        if not entries or bm25 is None:
            return []
        query_tokens = tokenize(query)
        query_set = set(query_tokens)
        scores = bm25.get_scores(query_tokens)
        # Candidate = contains at least one query token. Rank comes from the BM25 score even
        # when ≤ 0: with small corpora Okapi IDF for very common terms is negative (epsilon
        # floor of rank_bm25) and a "score > 0" filter would drop legitimate matches.
        scored = [
            (float(score), entry.chunk_id)
            for score, entry, tokens in zip(scores, entries, token_sets, strict=True)
            if tokens & query_set and (doc_type == "both" or entry.doc_type == doc_type)
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))  # ties broken by chunk_id (REQ-012)
        return [chunk_id for _, chunk_id in scored[:k]]

    def lookup(self, collection: str, chunk_ids: list[str]) -> list[LexicalEntry]:
        entries, _, _ = self._load(collection)
        by_id = {e.chunk_id: e for e in entries}
        return [by_id[cid] for cid in chunk_ids if cid in by_id]

    def exists(self, collection: str) -> bool:
        return self._sidecar(collection).exists()

    def reset(self, collection: str) -> None:
        self._sidecar(collection).unlink(missing_ok=True)  # absent = no-op (idempotent)
        self._cache.pop(collection, None)
