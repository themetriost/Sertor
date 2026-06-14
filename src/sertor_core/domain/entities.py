"""Domain entities for the retrieval core.

No external SDK imports (Principio I): these are pure data structures, shared by services and
adapters. Identifiers are **stable** and derived from paths/positions (Principio VI):
`Document.id` = relative path; `Chunk.id` = `document_id#index`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DocType(StrEnum):
    """Type of ingested document."""

    CODE = "code"
    DOC = "doc"


class ChunkerKind(StrEnum):
    """How a chunk was produced (useful for observability and quality analysis)."""

    SYNTACTIC = "syntactic"      # tree-sitter, at syntactic boundaries
    MARKDOWN = "markdown"        # at heading boundaries
    SIZE_FALLBACK = "size_fallback"  # size window (language outside supported set)


@dataclass(frozen=True)
class Document:
    """Unit ingested from a repository: a code or documentation file.

    `id` is the stable identifier derived from the POSIX relative path from the repo root
    (REQ-004): re-ingesting an unchanged file produces the same id.
    """

    id: str
    text: str
    doc_type: DocType
    language: str
    path: str = ""  # = id; redundant for readability in metadata

    def __post_init__(self) -> None:
        if not self.path:
            object.__setattr__(self, "path", self.id)


@dataclass(frozen=True)
class ChunkMetadata:
    """Structural metadata for a chunk.

    For code: `qualname`, `symbol`, `node_type`, `start_line`, `end_line` (REQ-007).
    For Markdown: `heading_path` (section hierarchy, REQ-008). `chunker` indicates the
    chunk's origin.
    """

    path: str
    chunker: ChunkerKind
    language: str = ""
    # code
    qualname: str | None = None
    symbol: str | None = None
    node_type: str | None = None  # function | class | method | module
    start_line: int | None = None
    end_line: int | None = None
    # markdown
    heading_path: tuple[str, ...] = ()


@dataclass(frozen=True)
class Chunk:
    """Indexable portion of a document.

    `id` = `f"{document_id}#{index}"`, where `index` is the positional ordinal in the
    chunker emission order (REQ-010): stable and idempotent for unchanged content.
    """

    id: str
    document_id: str
    text: str
    doc_type: DocType
    metadata: ChunkMetadata


@dataclass(frozen=True)
class EmbeddedChunk:
    """Record persisted in the vector store: chunk + vector, inside a namespaced collection.

    `payload` carries text and metadata (including `doc_type` for filtering). The collection is
    consistent for (corpus, provider, embedding dimension): vectors of different dimensions do
    not mix.
    """

    chunk_id: str
    vector: list[float]
    payload: dict


@dataclass(frozen=True)
class LexicalEntry:
    """Entry in the lexical index of the hybrid engine (FEAT-004, FR-001/002).

    Mirrors a chunk indexed in the vector store: same identity (`chunk_id`) and same
    `doc_type` (for consistent filtering across both retrieval paths of the hybrid engine).
    """

    chunk_id: str
    text: str
    doc_type: str
    path: str


@dataclass(frozen=True)
class GraphNode:
    """Node in the structural code graph (FEAT-005).

    `id` is stable and idempotent: `path` for module/doc, `path::qualname` for symbols
    (prototype 03 pattern) — same corpus → same ids (FR-008).
    """

    id: str
    kind: str               # module | class | function | method | doc
    name: str
    path: str
    line: int | None = None
    qualname: str | None = None


@dataclass(frozen=True)
class GraphEdge:
    """Typed edge in the code graph: contains | calls | imports | inherits | mentions."""

    source: str
    target: str
    type: str


@dataclass(frozen=True)
class GraphData:
    """Output of extraction and input to `CodeGraph.build` (full corpus snapshot).

    `coverage` is the per-language declaration of supported relational edges
    (FR-003, DA-3): persisted in the artifact, never silently absent.
    """

    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    coverage: tuple[tuple[str, tuple[str, ...]], ...] = ()


@dataclass(frozen=True)
class SymbolHit:
    """Citable result of a structural navigation query (FR-018): `ref = path#qualname`."""

    path: str
    line: int | None
    kind: str
    qualname: str
    ref: str


@dataclass(frozen=True)
class ContextBundle:
    """Multi-hop response from `get_context` (FR-016), sections limited by Settings knobs."""

    definitions: tuple[SymbolHit, ...] = ()
    callers: tuple[SymbolHit, ...] = ()
    callees: tuple[SymbolHit, ...] = ()
    bases: tuple[SymbolHit, ...] = ()
    docs: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalResult:
    """Result returned by the facade for each hit (REQ-025)."""

    text: str
    path: str
    chunk_id: str
    doc_type: DocType
    score: float
    metadata: dict | None = None


@dataclass
class IndexReport:
    """Outcome of an indexing operation (observability, REQ-031)."""

    collection: str
    documents: int = 0
    chunks: int = 0
    skipped: int = 0
    embedding_dim: int | None = None
    elapsed_ms: float | None = None
    skipped_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ObservedEvent:
    """A persisted observability event (feature 020): a structured `log_event`, kept.

    `ts` is the emission instant (epoch seconds); `operation` the event kind (`index`,
    `embeddings`, `retrieve`, …); `fields` the already-redacted applicative fields. The value
    type returned by `ObservabilityStore.query_events` (no backend type leaks into the domain).
    """

    ts: float
    operation: str
    fields: dict
