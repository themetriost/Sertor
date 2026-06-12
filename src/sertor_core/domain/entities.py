"""Entità di dominio del nucleo di retrieval.

Nessun import di SDK esterni (Principio I): sono strutture dati pure, condivise da servizi e
adapter. Gli identificatori sono **stabili** e derivati dai path/posizioni (Principio VI):
`Document.id` = path relativo; `Chunk.id` = `document_id#indice`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DocType(StrEnum):
    """Tipo di documento ingerito."""

    CODE = "code"
    DOC = "doc"


class ChunkerKind(StrEnum):
    """Come è stato prodotto un chunk (utile per osservabilità e analisi di qualità)."""

    SYNTACTIC = "syntactic"      # tree-sitter, ai confini sintattici
    MARKDOWN = "markdown"        # ai confini di heading
    SIZE_FALLBACK = "size_fallback"  # finestra dimensionale (linguaggio fuori set)


@dataclass(frozen=True)
class Document:
    """Unità ingerita da un repository: un file di codice o documentazione.

    `id` è l'identificatore stabile derivato dal path relativo POSIX rispetto alla radice del
    repo (REQ-004): la re-ingestione di un file invariato produce lo stesso id.
    """

    id: str
    text: str
    doc_type: DocType
    language: str
    path: str = ""  # = id; ridondante per leggibilità nei metadati

    def __post_init__(self) -> None:
        if not self.path:
            object.__setattr__(self, "path", self.id)


@dataclass(frozen=True)
class ChunkMetadata:
    """Metadati strutturali di un chunk.

    Per il codice: `qualname`, `symbol`, `node_type`, `start_line`, `end_line` (REQ-007).
    Per il Markdown: `heading_path` (gerarchia di sezione, REQ-008). `chunker` indica la
    provenienza del chunk.
    """

    path: str
    chunker: ChunkerKind
    language: str = ""
    # codice
    qualname: str | None = None
    symbol: str | None = None
    node_type: str | None = None  # function | class | method | module
    start_line: int | None = None
    end_line: int | None = None
    # markdown
    heading_path: tuple[str, ...] = ()


@dataclass(frozen=True)
class Chunk:
    """Porzione indicizzabile di un documento.

    `id` = `f"{document_id}#{index}"`, dove `index` è l'ordinale posizionale nell'ordine di
    emissione del chunker (REQ-010): stabile e idempotente a contenuto invariato.
    """

    id: str
    document_id: str
    text: str
    doc_type: DocType
    metadata: ChunkMetadata


@dataclass(frozen=True)
class EmbeddedChunk:
    """Record persistito nel vector store: chunk + vettore, dentro una collezione namespaced.

    `payload` porta testo e metadati (incluso `doc_type` per il filtro). La collezione è coerente
    per (corpus, provider, dimensione embedding): vettori di dimensioni diverse non si mescolano.
    """

    chunk_id: str
    vector: list[float]
    payload: dict


@dataclass(frozen=True)
class LexicalEntry:
    """Voce dell'indice lessicale del motore ibrido (FEAT-004, FR-001/002).

    Rispecchia un chunk indicizzato nel vector store: stessa identità (`chunk_id`) e stesso
    `doc_type` (per il filtro coerente sulle due vie del retrieval ibrido).
    """

    chunk_id: str
    text: str
    doc_type: str
    path: str


@dataclass(frozen=True)
class RetrievalResult:
    """Risultato restituito dalla facade per ogni hit (REQ-025)."""

    text: str
    path: str
    chunk_id: str
    doc_type: DocType
    score: float
    metadata: dict | None = None


@dataclass
class IndexReport:
    """Esito di un'operazione di indicizzazione (osservabilità, REQ-031)."""

    collection: str
    documents: int = 0
    chunks: int = 0
    skipped: int = 0
    embedding_dim: int | None = None
    elapsed_ms: float | None = None
    skipped_paths: list[str] = field(default_factory=list)
