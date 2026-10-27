"""Hybrid RAG engine — second core mode (FEAT-004).

Fuses the dense path (vector similarity) with the lexical path (BM25) via Reciprocal Rank
Fusion; optional cross-encoder reranking as a second stage. Same interface as
`BaselineEngine` (REQ-033) + `retrieve()` as `RetrieverStrategy` for the facade (FR-018).

Error policy (reconciliation REQ-004 ↔ REQ-034, research D7):
- corpus NEVER indexed (vector collection absent) → `IndexNotFoundError` (strict);
- pre-hybrid corpus (vector present, lexical index absent) → degradation to dense-only
  with structured WARNING `lexical_index_missing` — never an error, never silent (decision DA-1b).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType, IndexReport, RetrievalResult
from sertor_core.domain.errors import IndexNotFoundError
from sertor_core.domain.ports import (
    DocTypeFilter,
    EmbeddingProvider,
    LexicalIndex,
    Reranker,
    VectorStore,
)
from sertor_core.observability.logging import log_event
from sertor_core.services.dedup import dedup_results
from sertor_core.services.indexing import IndexingService
from sertor_core.services.retrieval import apply_min_score, content_fields


def rrf(rankings: list[list[str]], k: int, c: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: `score(id) = Σ 1/(c + rank)` across lists (REQ-010/011).

    Fusion by rank, not by score: cosine similarity and BM25 scores are not
    commensurable. Deterministic: ties broken by ascending chunk_id (REQ-012).
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, 1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (c + rank)
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return ordered[:k]


class HybridEngine:
    """Hybrid RAG mode. Built via `composition.build_engine`."""

    name = "hybrid"  # stable mode name (REQ-033)

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        lexical: LexicalIndex,
        collection: str,
        settings: Settings,
        reranker: Reranker | None = None,
        default_k: int | None = None,
    ):
        self._embedder = embedder
        self._store = store
        self._lexical = lexical
        self._collection = collection
        self._settings = settings
        self._reranker = reranker
        self._default_k = default_k or settings.default_k

    @property
    def provider(self) -> str:
        return self._embedder.name

    def index(self, root: Path | str) -> IndexReport:
        """Joint vector + lexical rebuild from the same chunks (REQ-001/003)."""
        indexer = IndexingService(
            self._embedder, self._store, self._collection, self._settings, lexical=self._lexical
        )
        return indexer.index(root, rebuild=True)

    def ensure_index(self) -> None:
        """Strict on the vector collection: absent → `IndexNotFoundError` (FR-004)."""
        if not self._store.exists(self._collection):
            raise IndexNotFoundError(
                "index not found: build it (index) before querying",
                collection=self._collection,
            )

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Top-k hybrid results, strict path (direct engine consumption)."""
        k = k or self._default_k
        self.ensure_index()
        return self.retrieve(query, k, "both")

    def retrieve(self, query: str, k: int, doc_type: DocTypeFilter) -> list[RetrievalResult]:
        """Hybrid core (`RetrieverStrategy`): collection already verified as existing by the
        caller."""
        started = time.perf_counter()
        vector = self._embedder.embed([query])[0]

        min_score = self._settings.retrieval_min_score
        if not self._lexical.exists(self._collection):
            # Degradation REQ-034 (pre-hybrid corpus): dense-only + warning, never an error.
            log_event(
                logging.WARNING,
                "lexical_index_missing",
                collection=self._collection,
                hint="re-index the corpus to enable hybrid retrieval",
            )
            # Fetch a pool > k when dedup is on so collapsing duplicates can backfill (A-07).
            fetch = max(k, self._settings.rerank_pool) if self._settings.dedup_enabled else k
            raw = self._store.query(self._collection, vector, fetch, doc_type)
            # Confidence threshold (018, REQ-H1/H2): here the score is cosine similarity → filter.
            filtered, low = apply_min_score(raw, min_score)
            deduped = 0
            if self._settings.dedup_enabled:
                filtered, deduped = dedup_results(filtered)
            results = filtered[:k]
            self._log_query(results, lexical_hits=0, dense_hits=len(raw),
                            rerank_applied=False, started=started, query=query,
                            abstained=low, deduped=deduped)
            if low:
                self._log_low_confidence(raw)
            return results

        pool = self._settings.rrf_pool
        dense_raw = self._store.query(self._collection, vector, pool, doc_type)
        # Confidence gate on the DENSE leg (018, REQ-H1/H2, research D4): the final score is RRF
        # (rank-based, not a similarity), so the cosine threshold acts on the dense pool BEFORE
        # fusion. If the dense leg is emptied by the threshold, abstain (empty + low_confidence).
        dense, low = apply_min_score(dense_raw, min_score)
        if low:
            self._log_query([], lexical_hits=0, dense_hits=0, rerank_applied=False,
                            started=started, query=query, abstained=True)
            self._log_low_confidence(dense_raw)
            return []
        lexical_ids = self._lexical.query(self._collection, query, pool, doc_type)
        # The fused pool must be large enough for the reranker AND for dedup to backfill after
        # removing duplicates (E5-FEAT-003 / A-07): even with the reranker off, dedup needs a pool
        # bigger than k, otherwise collapsing duplicates would shrink the result below k with no
        # distinct content to take their place.
        needs_pool = self._use_reranker() or self._settings.dedup_enabled
        fused_k = max(k, self._settings.rerank_pool) if needs_pool else k
        fused = rrf([[r.chunk_id for r in dense], lexical_ids], k=fused_k, c=self._settings.rrf_c)
        candidates = self._materialize(fused, dense)

        deduped = 0
        if self._settings.dedup_enabled:
            candidates, deduped = dedup_results(candidates)

        if self._use_reranker():
            results = self._rerank(query, candidates[: self._settings.rerank_pool], k)
        else:
            results = candidates[:k]

        self._log_query(results, lexical_hits=len(lexical_ids), dense_hits=len(dense),
                        rerank_applied=self._use_reranker(), started=started,
                        query=query, abstained=False, deduped=deduped)
        return results

    def _use_reranker(self) -> bool:
        return self._reranker is not None and self._settings.rerank_enabled

    def _log_low_confidence(self, dense_raw: list[RetrievalResult]) -> None:
        """Structured signal that the threshold emptied the dense leg (018, REQ-H2/FR-012)."""
        log_event(
            logging.WARNING,
            "low_confidence",
            collection=self._collection,
            provider=self._embedder.name,
            min_score=self._settings.retrieval_min_score,
            best_score=max((r.score for r in dense_raw), default=None),
            candidates=len(dense_raw),
        )

    def _materialize(
        self, fused: list[tuple[str, float]], dense: list[RetrievalResult]
    ) -> list[RetrievalResult]:
        """`RetrievalResult` for each fused id, score = RRF (REQ-013).

        Candidates from the lexical path only (absent from the dense pool) are materialised
        from sidecar entries via `lookup`.
        """
        dense_by_id = {r.chunk_id: r for r in dense}
        missing = [cid for cid, _ in fused if cid not in dense_by_id]
        lexical_by_id = {
            e.chunk_id: e for e in self._lexical.lookup(self._collection, missing)
        }
        results: list[RetrievalResult] = []
        for chunk_id, score in fused:
            if chunk_id in dense_by_id:
                hit = dense_by_id[chunk_id]
                results.append(RetrievalResult(
                    text=hit.text, path=hit.path, chunk_id=chunk_id,
                    doc_type=hit.doc_type, score=score, metadata=hit.metadata,
                ))
            elif chunk_id in lexical_by_id:
                entry = lexical_by_id[chunk_id]
                results.append(RetrievalResult(
                    text=entry.text, path=entry.path, chunk_id=chunk_id,
                    doc_type=DocType(entry.doc_type), score=score,
                ))
            # id not resolvable (misaligned indexes): skipped — the joint rebuild (REQ-003)
            # makes this case unreachable when indexes are consistent.
        return results

    def _rerank(
        self, query: str, pool: list[RetrievalResult], k: int
    ) -> list[RetrievalResult]:
        started = time.perf_counter()
        results = self._reranker.rerank(query, pool, k)
        log_event(
            logging.INFO,
            "rerank",
            reranker_model=self._reranker.model,
            pool_size=len(pool),
            top_k=k,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return results

    def _log_query(
        self,
        results: list[RetrievalResult],
        *,
        lexical_hits: int,
        dense_hits: int,
        rerank_applied: bool,
        started: float,
        query: str,
        abstained: bool,
        deduped: int = 0,
    ) -> None:
        content_on = (
            self._settings.observability_content_enabled and self._settings.observability_enabled
        )
        log_event(
            logging.INFO,
            "hybrid_query",
            engine=self.name,
            provider=self._embedder.name,
            collection=self._collection,
            lexical_hits=lexical_hits,
            dense_hits=dense_hits,
            fused_k=len(results),
            rerank_applied=rerank_applied,
            deduped=deduped,  # near-duplicate results removed before the cut (A-07)
            abstained=abstained,  # 0 results + abstained → "abstained" verdict (vs plain miss)
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            **content_fields(query, results, self._default_k, enabled=content_on),
        )
