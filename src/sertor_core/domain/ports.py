"""Porte (astrazioni) del nucleo: i boundary dietro cui vivono i provider concreti.

Il core dipende SOLO da queste astrazioni (Principio I/II); gli adapter in `adapters/` le
implementano importando gli SDK esterni. Definite come `Protocol` (structural typing): un
adapter è conforme se ha i metodi giusti, senza ereditare nulla — facile da mockare nei test.
"""
from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from sertor_core.domain.entities import EmbeddedChunk, LexicalEntry, RetrievalResult

DocTypeFilter = Literal["code", "doc", "both"]


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Astrazione del provider di embeddings (contracts/embedding-provider.md).

    `embed` processa i testi a batch e preserva l'ordine; `dim` è la dimensione del vettore,
    scoperta al primo batch se inizialmente `None`.
    """

    name: str
    dim: int | None
    batch_size: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Vettori per ciascun testo (ordine preservato). `[]` per input vuoto."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Astrazione del backend di persistenza+ricerca vettoriale (contracts/vector-store.md).

    Namespacing per `collection`. `query` filtra per tipo di documento senza indici separati.
    Una collezione assente fa restituire `[]` a `query` ed è `exists()==False`; un backend
    irraggiungibile solleva `VectorStoreError` (Principio IV).
    """

    def upsert(self, collection: str, records: list[EmbeddedChunk]) -> None:
        """Inserisce/sostituisce chunk (id, vettore, payload). Idempotente sugli stessi id."""
        ...

    def query(
        self,
        collection: str,
        vector: list[float],
        k: int,
        doc_type: DocTypeFilter = "both",
    ) -> list[RetrievalResult]:
        """Top-k per similarità, con filtro opzionale su doc_type. `[]` se collezione assente."""
        ...

    def delete(self, collection: str, ids: list[str]) -> None:
        """Rimuove i chunk indicati dalla collezione."""
        ...

    def reset(self, collection: str) -> None:
        """Svuota/elimina la collezione (per il rebuild-from-scratch idempotente).

        Idempotente: resettare una collezione assente non è un errore.
        """
        ...

    def exists(self, collection: str) -> bool:
        """True se la collezione esiste ed è inizializzata."""
        ...

    def list_collections(self) -> list[str]:
        """Nomi delle collezioni esistenti nel backend.

        Serve alla ricerca combinata multi-collezione per distinguere un corpus mai indicizzato
        (degradazione morbida) da uno indicizzato con un altro provider (errore esplicito, FR-009).
        """
        ...


@runtime_checkable
class LexicalIndex(Protocol):
    """Astrazione dell'indice lessicale del motore ibrido (contracts/lexical-index-port.md).

    Namespacing per `collection` (lo stesso nome namespaced per corpus+provider della collezione
    vettoriale che rispecchia, FR-005). La policy sull'assenza dell'indice (degradazione REQ-034)
    è del motore: il chiamante verifica `exists()` prima di `query`.
    """

    def build(self, collection: str, entries: list[LexicalEntry]) -> None:
        """Sostituisce integralmente l'indice della collezione (rebuild idempotente, atomico)."""
        ...

    def query(
        self,
        collection: str,
        query: str,
        k: int,
        doc_type: DocTypeFilter = "both",
    ) -> list[str]:
        """Chunk id in ordine di rilevanza lessicale, max `k`; filtro doc_type PRIMA del taglio."""
        ...

    def lookup(self, collection: str, chunk_ids: list[str]) -> list[LexicalEntry]:
        """Voci per gli id richiesti (ordine preservato, assenti saltati).

        Serve al motore ibrido per materializzare i `RetrievalResult` dei candidati arrivati
        dalla sola via lessicale (assenti dal pool denso).
        """
        ...

    def exists(self, collection: str) -> bool:
        """True se l'indice lessicale della collezione è presente."""
        ...

    def reset(self, collection: str) -> None:
        """Elimina l'indice della collezione (assente = no-op)."""
        ...


@runtime_checkable
class Reranker(Protocol):
    """Astrazione del secondo stadio di reranking (FEAT-004, gruppo C — extra opzionale).

    `model` identifica il cross-encoder per l'evento di log `rerank` (REQ-061).
    """

    model: str

    def rerank(
        self, query: str, results: list[RetrievalResult], k: int
    ) -> list[RetrievalResult]:
        """Top-k ri-ordinati per rilevanza query-passaggio; `score` = punteggio cross-encoder."""
        ...


@runtime_checkable
class RetrieverStrategy(Protocol):
    """Strategia di retrieval iniettata nella facade dal composition root (FR-017/018).

    Il chiamante garantisce che la collezione primaria esista (la facade conserva la sua policy
    tollerante: il check `exists()` + warning restano suoi).
    """

    def retrieve(self, query: str, k: int, doc_type: DocTypeFilter) -> list[RetrievalResult]:
        """Retrieval sulla collezione primaria, già verificata esistente."""
        ...
