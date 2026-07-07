"""Vector RAG engine — "baseline" mode (FEAT-002).

Thin engine on top of the core: orchestrates ingestion/chunking/embeddings/vector store (FEAT-001)
to index a codebase and query it by similarity. Does not redefine core primitives
(Principle III). Uses **only** vector similarity retrieval (REQ-014): no hybrid/graph/agentic
mechanism.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import IndexReport, RetrievalResult
from sertor_core.domain.errors import IndexNotFoundError
from sertor_core.domain.ports import EmbeddingProvider, VectorStore
from sertor_core.observability.logging import log_event
from sertor_core.services.dedup import dedup_results
from sertor_core.services.indexing import IndexingService
from sertor_core.services.retrieval import apply_min_score


class BaselineEngine:
    """Baseline vector RAG mode. Built via `composition.build_baseline_engine`."""

    name = "baseline"  # stable mode name (REQ-013)

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection: str,
        settings: Settings,
        default_k: int | None = None,
    ):
        self._embedder = embedder
        self._store = store
        self._collection = collection
        self._settings = settings
        self._default_k = default_k or settings.default_k

    @property
    def provider(self) -> str:
        return self._embedder.name

    def index(self, root: Path | str) -> IndexReport:
        """Indexes the codebase by rebuilding the index from scratch (idempotent rebuild,
        REQ-001/002).

        Delegates to the core orchestrator with `rebuild=True`: a provider error during
        embedding leaves the pre-existing index intact (REQ-004).
        """
        indexer = IndexingService(self._embedder, self._store, self._collection, self._settings)
        return indexer.index(root, rebuild=True)

    def ensure_index(self) -> None:
        """Strictly checks that the index exists, otherwise raises `IndexNotFoundError` (REQ-009).

        **Explicit** check (no silent empty list) reusable by consumers — e.g. the CLI
        invokes it before routing the search by `--type code|doc|both`, keeping the strict path
        for all filters (FEAT-011, D6). `query()` delegates here: the check lives in one place.
        """
        if not self._store.exists(self._collection):
            raise IndexNotFoundError(
                "index not found: build it (index) before querying",
                collection=self._collection,
            )

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Top-k chunks by vector similarity (REQ-005..008).

        If the index does not exist raises `IndexNotFoundError` (REQ-009) — no silent empty list.
        An unavailable provider propagates `EmbeddingError` (REQ-010).
        """
        k = k or self._default_k
        self.ensure_index()
        started = time.perf_counter()
        vector = self._embedder.embed([query])[0]
        # Fetch a pool > k when dedup is on so collapsing duplicates can backfill (A-07).
        fetch = max(k, self._settings.rerank_pool) if self._settings.dedup_enabled else k
        raw = self._store.query(self._collection, vector, fetch, "both")
        # Confidence threshold (018, REQ-H1/H2): filter weak hits on the EXISTING index. A result
        # filter, not an absent index — the strict `IndexNotFoundError` policy stays unchanged.
        filtered, low = apply_min_score(raw, self._settings.retrieval_min_score)
        deduped = 0
        if self._settings.dedup_enabled:
            filtered, deduped = dedup_results(filtered)
        results = filtered[:k]
        log_event(
            logging.INFO,
            "baseline_query",
            collection=self._collection,
            provider=self._embedder.name,
            k=k,
            results=len(results),
            deduped=deduped,  # near-duplicate results removed before the cut (A-07)
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        if low:
            log_event(
                logging.WARNING,
                "low_confidence",
                collection=self._collection,
                provider=self._embedder.name,
                min_score=self._settings.retrieval_min_score,
                best_score=max((r.score for r in raw), default=None),
                candidates=len(raw),
            )
        return results
