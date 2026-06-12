"""Facade di retrieval: punto d'accesso unico e stabile al corpus indicizzato (REQ-023..029).

Dipende solo dalle porte `EmbeddingProvider` e `VectorStore` (Principio I): è importabile come
libreria dai consumatori (motori RAG, skill wiki, CLI) senza conoscere store/embeddings. Espone la
ricerca su codice, su documentazione e combinata; ogni query emette log strutturati (REQ-031). Su
indice vuoto restituisce risultati vuoti con un warning, senza eccezioni (REQ-028).

La ricerca combinata può fare **fan-out su più collezioni** (corpus primario + corpora extra
dichiarati in configurazione, feature 010): i top-k delle collezioni vengono fusi per score.
Eccezione deliberata alla policy tollerante: un corpus extra indicizzato con un **altro provider**
solleva `ProviderMismatchError` (gli score di spazi vettoriali diversi non si fondono, FR-009).
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


class RetrievalFacade:
    """Interfaccia di retrieval indipendente dal backend."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection: str,
        default_k: int = 5,
        *,
        extra_collections: Mapping[str, str] | None = None,
        retriever: RetrieverStrategy | None = None,
    ):
        self._embedder = embedder
        self._store = store
        self._collection = collection
        self._default_k = default_k
        # corpus -> collezione attesa (nome derivato dal provider corrente, vedi composition).
        self._extra_collections = dict(extra_collections or {})
        # Strategia di retrieval iniettata dal composition root (FEAT-004, FR-017/018): se
        # presente, il percorso single-collection delega a lei (es. motore ibrido); l'interfaccia
        # della facade e la sua policy tollerante restano invariate per i consumatori.
        self._retriever = retriever

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
            # La strategia logga il proprio evento (es. `hybrid_query`); la collezione è già
            # verificata esistente — la policy tollerante resta della facade.
            return self._retriever.retrieve(query, k, doc_type)
        started = time.perf_counter()
        vector = self._embedder.embed([query])[0]
        results = self._store.query(self._collection, vector, k, doc_type)
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
        """Ricerca semantica su codice + documentazione insieme.

        Con corpora extra configurati fa fan-out su tutte le collezioni bersaglio e fonde i
        top-k per score (FR-001/002); senza, il comportamento è identico al passato (FR-006).
        """
        if not self._extra_collections:
            return self._search(query, k, "both")
        return self._search_multi(query, k)

    def _available_targets(self) -> list[str]:
        """Collezioni bersaglio interrogabili; degrada o fallisce per quelle assenti.

        Primaria assente → warning `no_index` (policy tollerante invariata, FR-004). Corpus extra
        assente: mai indicizzato → warning; indicizzato con un altro provider (esiste una
        collezione `{corpus}__*` diversa dall'attesa) → `ProviderMismatchError` (FR-009).
        """
        targets: list[str] = []
        if self._store.exists(self._collection):
            targets.append(self._collection)
        else:
            log_event(logging.WARNING, "retrieve", collection=self._collection,
                      status="no_index", doc_type="both")
        existing: list[str] | None = None  # elenco lazy: solo se un'attesa manca
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
                    "corpus indicizzato con un provider di embeddings diverso",
                    corpus=corpus, expected=expected, found=mismatched,
                )
            log_event(logging.WARNING, "retrieve", collection=expected,
                      status="no_index", doc_type="both")
        return targets

    def _search_multi(self, query: str, k: int | None) -> list[RetrievalResult]:
        """Fan-out sulle collezioni bersaglio + fusione dei top-k per score (FR-001..005)."""
        k = k or self._default_k
        targets = self._available_targets()
        if not targets:
            return []
        started = time.perf_counter()
        vector = self._embedder.embed([query])[0]
        candidates: list[RetrievalResult] = []
        for collection in targets:
            candidates.extend(self._store.query(collection, vector, k, "both"))
        # Ordinamento totale e deterministico: score decrescente, pareggi per chunk_id (FR-003).
        fused = sorted(candidates, key=lambda r: (-r.score, r.chunk_id))[:k]
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
        return fused
