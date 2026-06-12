"""Motore RAG ibrido — seconda modalità del core (FEAT-004).

Fonde la via densa (similarità vettoriale) con la via lessicale (BM25) tramite Reciprocal Rank
Fusion; reranking cross-encoder opzionale come secondo stadio. Stessa interfaccia del
`BaselineEngine` (REQ-033) + `retrieve()` come `RetrieverStrategy` per la facade (FR-018).

Policy errori (riconciliazione REQ-004 ↔ REQ-034, research D7):
- corpus MAI indicizzato (collezione vettoriale assente) → `IndexNotFoundError` (strict);
- corpus pre-ibrido (vettoriale presente, indice lessicale assente) → degradazione a dense-only
  con WARNING strutturato `lexical_index_missing` — mai errore, mai silenzio (decisione DA-1b).
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
from sertor_core.services.indexing import IndexingService


def rrf(rankings: list[list[str]], k: int, c: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: `score(id) = Σ 1/(c + rank)` sulle liste (REQ-010/011).

    Fusione per ranghi, non per score: similarità coseno e punteggi BM25 non sono
    commensurabili. Deterministica: pareggi risolti per chunk_id crescente (REQ-012).
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, 1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (c + rank)
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return ordered[:k]


class HybridEngine:
    """Modalità RAG ibrida. Costruita via `composition.build_engine`."""

    name = "hybrid"  # nome stabile della modalità (REQ-033)

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
        """Rebuild congiunto vettoriale + lessicale dagli stessi chunk (REQ-001/003)."""
        indexer = IndexingService(
            self._embedder, self._store, self._collection, self._settings, lexical=self._lexical
        )
        return indexer.index(root, rebuild=True)

    def ensure_index(self) -> None:
        """Strict sulla collezione vettoriale: assente → `IndexNotFoundError` (FR-004)."""
        if not self._store.exists(self._collection):
            raise IndexNotFoundError(
                "indice inesistente: costruiscilo (index) prima di interrogare",
                collection=self._collection,
            )

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Top-k ibridi, via strict (consumo diretto del motore)."""
        k = k or self._default_k
        self.ensure_index()
        return self.retrieve(query, k, "both")

    def retrieve(self, query: str, k: int, doc_type: DocTypeFilter) -> list[RetrievalResult]:
        """Cuore ibrido (`RetrieverStrategy`): collezione già verificata esistente dal chiamante."""
        started = time.perf_counter()
        vector = self._embedder.embed([query])[0]

        if not self._lexical.exists(self._collection):
            # Degradazione REQ-034 (corpus pre-ibrido): dense-only + warning, mai errore.
            log_event(
                logging.WARNING,
                "lexical_index_missing",
                collection=self._collection,
                hint="re-index del corpus per abilitare il retrieval ibrido",
            )
            results = self._store.query(self._collection, vector, k, doc_type)
            self._log_query(results, lexical_hits=0, dense_hits=len(results),
                            rerank_applied=False, started=started)
            return results

        pool = self._settings.rrf_pool
        dense = self._store.query(self._collection, vector, pool, doc_type)
        lexical_ids = self._lexical.query(self._collection, query, pool, doc_type)
        # Il pool fuso copre k oppure, se il reranker è attivo, il pool del secondo stadio.
        fused_k = max(k, self._settings.rerank_pool) if self._use_reranker() else k
        fused = rrf([[r.chunk_id for r in dense], lexical_ids], k=fused_k, c=self._settings.rrf_c)
        candidates = self._materialize(fused, dense)

        if self._use_reranker():
            results = self._rerank(query, candidates[: self._settings.rerank_pool], k)
        else:
            results = candidates[:k]

        self._log_query(results, lexical_hits=len(lexical_ids), dense_hits=len(dense),
                        rerank_applied=self._use_reranker(), started=started)
        return results

    def _use_reranker(self) -> bool:
        return self._reranker is not None and self._settings.rerank_enabled

    def _materialize(
        self, fused: list[tuple[str, float]], dense: list[RetrievalResult]
    ) -> list[RetrievalResult]:
        """`RetrievalResult` per ogni id fuso, score = RRF (REQ-013).

        I candidati di sola via lessicale (assenti dal pool denso) si materializzano dalle voci
        del sidecar via `lookup`.
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
            # id non risolvibile (indici disallineati): si salta — il rebuild congiunto (REQ-003)
            # rende il caso non raggiungibile a indici coerenti.
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
    ) -> None:
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
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
