"""Facade di retrieval: punto d'accesso unico e stabile al corpus indicizzato (REQ-023..029).

Dipende solo dalle porte `EmbeddingProvider` e `VectorStore` (Principio I): è importabile come
libreria dai consumatori (motori RAG, skill wiki, CLI) senza conoscere store/embeddings. Espone la
ricerca su codice, su documentazione e combinata; ogni query emette log strutturati (REQ-031). Su
indice vuoto restituisce risultati vuoti con un warning, senza eccezioni (REQ-028).
"""
from __future__ import annotations

import logging
import time

from sertor_core.domain.entities import RetrievalResult
from sertor_core.domain.ports import DocTypeFilter, EmbeddingProvider, VectorStore
from sertor_core.observability.logging import log_error, log_event


class RetrievalFacade:
    """Interfaccia di retrieval indipendente dal backend."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection: str,
        default_k: int = 5,
    ):
        self._embedder = embedder
        self._store = store
        self._collection = collection
        self._default_k = default_k

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
        started = time.perf_counter()
        try:
            vector = self._embedder.embed([query])[0]
            results = self._store.query(self._collection, vector, k, doc_type)
        except Exception as exc:  # boundary: logga l'errore prima di propagarlo (REQ-053)
            log_error("retrieve", exc, collection=self._collection, provider=self._embedder.name)
            raise
        log_event(
            logging.INFO,
            "retrieve",
            collection=self._collection,
            provider=self._embedder.name,
            doc_type=doc_type,
            k=k,
            results=len(results),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return results

    def search_code(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Ricerca semantica sul solo codice."""
        return self._search(query, k, "code")

    def search_docs(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Ricerca semantica sulla sola documentazione."""
        return self._search(query, k, "doc")

    def search_combined(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        """Ricerca semantica su codice + documentazione insieme."""
        return self._search(query, k, "both")
