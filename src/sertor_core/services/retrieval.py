"""Retrieval facade: single stable access point to the indexed corpus (REQ-023..029).

Depends only on the ports `EmbeddingProvider` and `VectorStore` (Principio I): importable as a
library by consumers (RAG engines, wiki skill, CLI) without knowledge of the store/embeddings.
Exposes code search, documentation search, and combined search; every query emits structured logs
(REQ-031). On an empty index it returns empty results with a warning, without raising exceptions
(REQ-028).

Combined search can **fan-out across multiple collections** (primary corpus + extra corpora declared
in configuration, feature 010): top-k results from each collection are merged by score.
Deliberate exception to the tolerant policy: an extra corpus indexed with a **different provider**
raises `ProviderMismatchError` (scores from different vector spaces cannot be merged, FR-009).
"""
from __future__ import annotations

import logging
import time
from collections.abc import Mapping

from sertor_core.domain.entities import RetrievalResult
from sertor_core.domain.errors import ProviderMismatchError
from sertor_core.domain.ports import (
    DocTypeFilter,
    EmbeddingProvider,
    RetrieverStrategy,
    VectorStore,
)
from sertor_core.observability.logging import log_event
from sertor_core.observability.scrub import scrub_text


def apply_min_score(
    results: list[RetrievalResult], min_score: float | None
) -> tuple[list[RetrievalResult], bool]:
    """Filter results below the cosine-similarity threshold (018, REQ-H1/H2).

    `min_score=None` → passthrough `(results, False)` (today's behaviour, FR-013). Otherwise keep
    only results scoring `>= min_score`; the second value (`low_confidence`) is true when there
    WERE candidates but none passed — the consumer can use it to abstain (FR-011). Pure and
    deterministic, so it is shared by the facade and both engines (D5).
    """
    if min_score is None:
        return results, False
    kept = [r for r in results if r.score >= min_score]
    return kept, (bool(results) and not kept)


_SNIPPET_MAX = 200


def content_fields(query: str, results: list[RetrievalResult], k: int, *, enabled: bool) -> dict:
    """Optional RAG-demonstrability content for a retrieval event (064, FEAT-015).

    Returns `{}` unless `enabled` (the local opt-in). When on: the (secret-scrubbed) `query`, a
    `results_preview` of the top-k as `path|score`, and a scrubbed/truncated `snippet` of the top-1.
    Paths are not content (already visible to whoever has the repo); the snippet is the only free
    text, so it is scrubbed and capped. Pure → shared by the facade and the hybrid engine (D1).
    """
    if not enabled:
        return {}
    out: dict = {
        "query": scrub_text(query),
        "results_preview": [f"{r.path}|{round(r.score, 3)}" for r in results[:k]],
    }
    if results:
        out["snippet"] = scrub_text(results[0].text or "")[:_SNIPPET_MAX]
    return out


class RetrievalFacade:
    """Backend-independent retrieval interface."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection: str,
        default_k: int = 5,
        *,
        extra_collections: Mapping[str, str] | None = None,
        retriever: RetrieverStrategy | None = None,
        min_score: float | None = None,
        content_enabled: bool = False,
    ):
        self._embedder = embedder
        self._store = store
        self._collection = collection
        self._default_k = default_k
        # RAG-demonstrability opt-in (064, FEAT-015): when on, the facade's own dense `retrieve`
        # event also carries the query/preview/snippet (scrubbed). Default off (privacy-by-default).
        self._content_enabled = content_enabled
        # corpus -> expected collection name (derived from the current provider, see composition).
        self._extra_collections = dict(extra_collections or {})
        # Retrieval strategy injected by the composition root (FEAT-004, FR-017/018): when
        # present, the single-collection path delegates to it (e.g. hybrid engine); the facade
        # interface and its tolerant policy remain unchanged for consumers.
        self._retriever = retriever
        # Optional confidence threshold (018, REQ-H1/H2): applied only on the facade's own dense
        # path; on the retriever path the hybrid engine applies it (no double filtering).
        self._min_score = min_score

    @property
    def provider(self) -> str:
        """The embedding provider name (069): identifies the vector space of the measure.

        Exposed so the fused-eval surface adapters can satisfy `QueryableEngine.provider` and the
        report/baseline can carry the provider, without reaching into the private embedder.
        """
        return self._embedder.name

    def _search(self, query: str, k: int | None, doc_type: DocTypeFilter) -> list[RetrievalResult]:
        k = k or self._default_k
        if not self._store.exists(self._collection):
            log_event(
                logging.WARNING,
                "retrieve",
                collection=self._collection,
                status="no_index",
                doc_type=doc_type,
            )
            return []
        if self._retriever is not None:
            # The strategy logs its own event (e.g. `hybrid_query`); the collection has already
            # been verified to exist — the tolerant policy remains with the facade.
            return self._retriever.retrieve(query, k, doc_type)
        started = time.perf_counter()
        vector = self._embedder.embed([query])[0]
        raw = self._store.query(self._collection, vector, k, doc_type)
        results, low = apply_min_score(raw, self._min_score)
        log_event(
            logging.INFO,
            "retrieve",
            collection=self._collection,
            provider=self._embedder.name,
            doc_type=doc_type,
            k=k,
            results=len(results),
            abstained=low,  # results==0 + abstained → "abstained" verdict (vs plain miss)
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            **content_fields(query, results, k, enabled=self._content_enabled),
        )
        if low:
            self._log_low_confidence([self._collection], raw)
        return results

    def _log_low_confidence(self, collections: list[str], raw: list[RetrievalResult]) -> None:
        """Structured signal that the threshold emptied the result set (018, REQ-H2/FR-012)."""
        log_event(
            logging.WARNING,
            "low_confidence",
            collections=collections,
            provider=self._embedder.name,
            min_score=self._min_score,
            best_score=max((r.score for r in raw), default=None),
            candidates=len(raw),
        )

    def search_code(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Semantic search over code only."""
        return self._search(query, k, "code")

    def search_docs(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Semantic search over documentation only."""
        return self._search(query, k, "doc")

    def search_combined(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Semantic search over code + documentation together.

        With extra corpora configured, fans out across all target collections and merges the
        top-k results by score (FR-001/002); without them, behaviour is identical to before
        (FR-006).
        """
        if not self._extra_collections:
            return self._search(query, k, "both")
        return self._search_multi(query, k)

    def _available_targets(self) -> list[str]:
        """Queryable target collections; degrades or fails for missing ones.

        Primary absent → warning `no_index` (unchanged tolerant policy, FR-004). Extra corpus
        absent: never indexed → warning; indexed with a different provider (a `{corpus}__*`
        collection exists that differs from the expected one) → `ProviderMismatchError` (FR-009).
        """
        targets: list[str] = []
        if self._store.exists(self._collection):
            targets.append(self._collection)
        else:
            log_event(logging.WARNING, "retrieve", collection=self._collection,
                      status="no_index", doc_type="both")
        existing: list[str] | None = None  # lazy list: only fetched when an expected one is missing
        for corpus, expected in self._extra_collections.items():
            if self._store.exists(expected):
                targets.append(expected)
                continue
            if existing is None:
                existing = self._store.list_collections()
            mismatched = [name for name in existing
                          if name.startswith(f"{corpus}__") and name != expected]
            if mismatched:
                raise ProviderMismatchError(
                    "corpus indexed with a different embedding provider",
                    corpus=corpus, expected=expected, found=mismatched,
                )
            log_event(logging.WARNING, "retrieve", collection=expected,
                      status="no_index", doc_type="both")
        return targets

    def _search_multi(self, query: str, k: int | None) -> list[RetrievalResult]:
        """Fan-out across target collections + top-k merge by score (FR-001..005)."""
        k = k or self._default_k
        targets = self._available_targets()
        if not targets:
            return []
        started = time.perf_counter()
        vector = self._embedder.embed([query])[0]
        candidates: list[RetrievalResult] = []
        for collection in targets:
            candidates.extend(self._store.query(collection, vector, k, "both"))
        # Total deterministic ordering: descending score, ties broken by chunk_id (FR-003).
        fused = sorted(candidates, key=lambda r: (-r.score, r.chunk_id))[:k]
        fused, low = apply_min_score(fused, self._min_score)
        log_event(
            logging.INFO,
            "retrieve",
            collections=targets,
            provider=self._embedder.name,
            doc_type="both",
            k=k,
            results=len(fused),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        if low:
            self._log_low_confidence(targets, candidates)
        return fused
