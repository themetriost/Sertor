"""Porte (astrazioni) del nucleo: i boundary dietro cui vivono i provider concreti.

Il core dipende SOLO da queste astrazioni (Principio I/II); gli adapter in `adapters/` le
implementano importando gli SDK esterni. Definite come `Protocol` (structural typing): un
adapter è conforme se ha i metodi giusti, senza ereditare nulla — facile da mockare nei test.
"""
from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from sertor_core.domain.entities import EmbeddedChunk, RetrievalResult

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


@runtime_checkable
class LLMProvider(Protocol):
    """Astrazione di un provider di generazione testo (LLM).

    Usata solo dalle capacità che richiedono generazione (es. distillazione del wiki, FEAT-003).
    Minimale di proposito (Principio III): un solo metodo. Gli adapter concreti avvolgono gli SDK.
    """

    name: str

    def generate(self, prompt: str, system: str | None = None) -> str:
        """Genera testo dal prompt (con un eventuale messaggio di sistema)."""
        ...
