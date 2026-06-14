"""Core ports (abstractions): the boundaries behind which concrete providers live.

The core depends ONLY on these abstractions (Principio I/II); adapters in `adapters/` implement
them by importing external SDKs. Defined as `Protocol` (structural typing): an adapter is
compliant if it has the right methods, without any inheritance — easy to mock in tests.
"""
from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from sertor_core.domain.entities import (
    ContextBundle,
    EmbeddedChunk,
    GraphData,
    LexicalEntry,
    ObservedEvent,
    RetrievalResult,
    SymbolHit,
)

DocTypeFilter = Literal["code", "doc", "both"]


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Abstraction for the embedding provider (contracts/embedding-provider.md).

    `embed` processes texts in batches and preserves order; `dim` is the vector dimension,
    discovered on the first batch if initially `None`.
    """

    name: str
    dim: int | None
    batch_size: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Vectors for each text (order preserved). `[]` for empty input."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Abstraction for the vector persistence+search backend (contracts/vector-store.md).

    Namespaced by `collection`. `query` filters by document type without separate indexes.
    A missing collection causes `query` to return `[]` and `exists()==False`; an unreachable
    backend raises `VectorStoreError` (Principio IV).
    """

    def upsert(self, collection: str, records: list[EmbeddedChunk]) -> None:
        """Insert/replace chunks (id, vector, payload). Idempotent for the same ids."""
        ...

    def query(
        self,
        collection: str,
        vector: list[float],
        k: int,
        doc_type: DocTypeFilter = "both",
    ) -> list[RetrievalResult]:
        """Top-k by similarity, with optional doc_type filter. `[]` if collection is absent."""
        ...

    def delete(self, collection: str, ids: list[str]) -> None:
        """Remove the given chunks from the collection."""
        ...

    def reset(self, collection: str) -> None:
        """Empty/delete the collection (for idempotent rebuild-from-scratch).

        Idempotent: resetting a missing collection is not an error.
        """
        ...

    def exists(self, collection: str) -> bool:
        """True if the collection exists and is initialised."""
        ...

    def list_collections(self) -> list[str]:
        """Names of existing collections in the backend.

        Used by the multi-collection combined search to distinguish a corpus that has never
        been indexed (soft degradation) from one indexed with a different provider (explicit
        error, FR-009).
        """
        ...


@runtime_checkable
class LexicalIndex(Protocol):
    """Abstraction for the lexical index of the hybrid engine (contracts/lexical-index-port.md).

    Namespaced by `collection` (the same corpus+provider namespaced name as the vector
    collection it mirrors, FR-005). The policy for a missing index (degradation REQ-034) belongs
    to the engine: the caller checks `exists()` before `query`.
    """

    def build(self, collection: str, entries: list[LexicalEntry]) -> None:
        """Fully replace the collection's index (idempotent, atomic rebuild)."""
        ...

    def query(
        self,
        collection: str,
        query: str,
        k: int,
        doc_type: DocTypeFilter = "both",
    ) -> list[str]:
        """Chunk ids in lexical relevance order, max `k`; doc_type filter applied BEFORE cut."""
        ...

    def lookup(self, collection: str, chunk_ids: list[str]) -> list[LexicalEntry]:
        """Entries for the requested ids (order preserved, missing ones skipped).

        Used by the hybrid engine to materialise `RetrievalResult`s for candidates that
        arrived via the lexical path only (absent from the dense pool).
        """
        ...

    def exists(self, collection: str) -> bool:
        """True if the lexical index for the collection is present."""
        ...

    def reset(self, collection: str) -> None:
        """Delete the collection's index (absent = no-op)."""
        ...


@runtime_checkable
class Reranker(Protocol):
    """Abstraction for the second reranking stage (FEAT-004, group C — optional extra).

    `model` identifies the cross-encoder for the `rerank` log event (REQ-061).
    """

    model: str

    def rerank(
        self, query: str, results: list[RetrievalResult], k: int
    ) -> list[RetrievalResult]:
        """Top-k re-ordered by query-passage relevance; `score` = cross-encoder score."""
        ...


@runtime_checkable
class CodeGraph(Protocol):
    """Abstraction for the structural code graph (FEAT-005, contracts/code-graph-port.md).

    Namespaced by corpus ONLY (the graph does not depend on the embedding provider). Two
    absence semantics: graph not built → `GraphNotFoundError` (explicit); symbol absent →
    empty results (legitimate). `build` does not require the graph library.
    """

    def build(self, corpus: str, data: GraphData) -> None:
        """Fully replace the corpus artifact (snapshot, atomic, idempotent)."""
        ...

    def find_symbol(self, name: str) -> list[SymbolHit]:
        """Definitions with an exact name match (class/function/method); empty if absent."""
        ...

    def who_calls(self, name: str) -> list[SymbolHit]:
        """Nodes with an outgoing `calls` edge to the symbol."""
        ...

    def related_docs(self, name: str) -> list[str]:
        """Paths of documents with a `mentions` edge to the symbol."""
        ...

    def get_context(self, name: str) -> ContextBundle:
        """Multi-hop bundle (definitions, callers, callees, bases, docs), sections limited."""
        ...

    def exists(self, corpus: str) -> bool:
        """True if the graph artifact for the corpus is present."""
        ...

    def reset(self, corpus: str) -> None:
        """Delete the corpus artifact (absent = no-op)."""
        ...


@runtime_checkable
class ObservabilityStore(Protocol):
    """Abstraction for the persistent observability archive (feature 020,
    contracts/observability-store.md).

    The seam between where events live (the persistence handler writes here) and who queries them
    (FEAT-002 aggregation/report reads here). A store failure is non-fatal: `record_event` is a
    no-op and `query_events` returns `[]`, both with a warning — the observed operation is never
    affected (the observability layer is a service add-on, not a source of truth).
    """

    def record_event(self, ts: float, operation: str, fields: dict) -> None:
        """Append an observed event (instant, operation kind, already-redacted fields)."""
        ...

    def query_events(
        self, operation: str | None, since: float | None, until: float | None
    ) -> list[ObservedEvent]:
        """Events matching the filters (None = unconstrained), ordered by `ts` ascending."""
        ...


@runtime_checkable
class RetrieverStrategy(Protocol):
    """Retrieval strategy injected into the facade by the composition root (FR-017/018).

    The caller guarantees that the primary collection exists (the facade keeps its tolerant
    policy: the `exists()` check + warning remain its responsibility).
    """

    def retrieve(self, query: str, k: int, doc_type: DocTypeFilter) -> list[RetrievalResult]:
        """Retrieval on the primary collection, already verified to exist."""
        ...
