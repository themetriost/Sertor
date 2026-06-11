"""Motore RAG vettoriale — modalità "baseline" (FEAT-002).

Motore sottile sopra il nucleo: orchestra ingestione/chunking/embeddings/vector store (FEAT-001)
per indicizzare una codebase e interrogarla per similarità. Non ridefinisce le primitive del nucleo
(Principio III). Usa **solo** retrieval per similarità vettoriale (REQ-014): nessun meccanismo
ibrido/grafo/agentico.
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
from sertor_core.services.indexing import IndexingService


class BaselineEngine:
    """Modalità RAG vettoriale baseline. Costruita via `composition.build_baseline_engine`."""

    name = "baseline"  # nome stabile della modalità (REQ-013)

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
        """Indicizza la codebase ricostruendo l'indice da zero (rebuild idempotente, REQ-001/002).

        Delega all'orchestratore del nucleo con `rebuild=True`: un errore del provider durante
        l'embedding lascia l'indice preesistente intatto (REQ-004).
        """
        indexer = IndexingService(self._embedder, self._store, self._collection, self._settings)
        return indexer.index(root, rebuild=True)

    def ensure_index(self) -> None:
        """Verifica strict che l'indice esista, altrimenti `IndexNotFoundError` (REQ-009).

        Check **esplicito** (niente lista vuota silenziosa) riusabile dai consumatori — es. la CLI
        lo invoca prima di instradare la ricerca per `--type code|doc|both`, mantenendo la via
        strict per tutti i filtri (FEAT-011, D6). `query()` vi delega: il check vive in un solo
        punto.
        """
        if not self._store.exists(self._collection):
            raise IndexNotFoundError(
                "indice inesistente: costruiscilo (index) prima di interrogare",
                collection=self._collection,
            )

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Top-k chunk per similarità vettoriale (REQ-005..008).

        Se l'indice non esiste solleva `IndexNotFoundError` (REQ-009) — niente lista vuota
        silenziosa. Un provider non disponibile propaga `EmbeddingError` (REQ-010).
        """
        k = k or self._default_k
        self.ensure_index()
        started = time.perf_counter()
        vector = self._embedder.embed([query])[0]
        results = self._store.query(self._collection, vector, k, "both")
        log_event(
            logging.INFO,
            "baseline_query",
            collection=self._collection,
            provider=self._embedder.name,
            k=k,
            results=len(results),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return results
