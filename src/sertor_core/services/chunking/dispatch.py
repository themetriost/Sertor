"""Chunking dispatcher: selects the right chunker for a document and produces domain `Chunk`s.

Code → syntactic chunker (with size-based fallback if the language is not supported, REQ-009);
Markdown → heading-based chunker (REQ-008); ASP.NET pages → syntactic chunks of their server-side
C# plus size-based chunks of their markup (140); other text → size-based fallback. Assigns each
chunk a stable id `f"{document_id}#{index}"` (positional ordinal, REQ-010) to guarantee
idempotency when content is unchanged (Principio VI).
"""
from __future__ import annotations

from collections.abc import Callable

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import Chunk, ChunkerKind, ChunkMetadata, DocType, Document
from sertor_core.services.chunking._tokens import cap_to_tokens
from sertor_core.services.chunking.aspnet import PAGE_LANGUAGES, page_raws
from sertor_core.services.chunking.code import code_chunks
from sertor_core.services.chunking.fallback import size_chunks
from sertor_core.services.chunking.markdown import markdown_chunks

MetadataOf = Callable[[Document, dict], ChunkMetadata]


def _code_metadata(doc: Document, raw: dict) -> ChunkMetadata:
    return ChunkMetadata(
        path=doc.path,
        chunker=ChunkerKind.SYNTACTIC,
        language=doc.language,
        qualname=raw.get("qualname"),
        symbol=raw.get("symbol"),
        node_type=raw.get("symbol_kind"),
        start_line=raw.get("start_line"),
        end_line=raw.get("end_line"),
    )


def _fallback_metadata(doc: Document, raw: dict) -> ChunkMetadata:
    return ChunkMetadata(
        path=doc.path,
        chunker=ChunkerKind.SIZE_FALLBACK,
        language=doc.language,
        start_line=raw.get("start_line"),
        end_line=raw.get("end_line"),
    )


def _markdown_metadata(doc: Document, raw: dict) -> ChunkMetadata:
    return ChunkMetadata(
        path=doc.path,
        chunker=ChunkerKind.MARKDOWN,
        language=doc.language,
        heading_path=tuple(raw.get("heading_path", ())),
        start_line=raw.get("start_line"),
        end_line=raw.get("end_line"),
    )


def _cap_oversized(raw: dict, max_tokens: int, overlap_tokens: int) -> list[dict]:
    """Sub-split a raw chunk that exceeds `max_tokens` (robustness).

    Structural chunkers (markdown by heading, code by symbol) can emit a unit far larger than
    `chunk_size`; embedding providers reject inputs over a token budget (text-embedding-3-large:
    8192 tokens → http 400). A raw within the cap is returned unchanged; an oversized one is split
    so each piece fits the budget (see `_tokens.cap_to_tokens`), the structural metadata
    (heading_path/qualname/…) inherited and the document line range kept (approximate for the rare
    oversized split).
    """
    pieces_text = cap_to_tokens(raw["text"], max_tokens, overlap_tokens)
    if len(pieces_text) == 1:
        return [raw]
    pieces: list[dict] = []
    for text in pieces_text:
        sub = dict(raw)  # inherit heading_path/qualname/symbol/node_type/language + line range
        sub["text"] = text
        pieces.append(sub)
    return pieces


def _raws_with_metadata(doc: Document, settings: Settings) -> list[tuple[dict, MetadataOf]]:
    """The document's raw chunks, each paired with the function that builds its metadata.

    Most documents use a single chunker; an ASP.NET page mixes syntactic code chunks with size-based
    markup chunks (140), hence the per-raw pairing.
    """
    if doc.doc_type is DocType.DOC:
        return [(raw, _markdown_metadata) for raw in markdown_chunks(doc.text)]
    if doc.language in PAGE_LANGUAGES:
        return [
            (raw, _code_metadata if syntactic else _fallback_metadata)
            for raw, syntactic in page_raws(doc, settings)
        ]
    raws = code_chunks(doc.text, doc.language, settings.chunk_size)
    if raws is None:  # language not supported syntactically -> size-based fallback
        fallback = size_chunks(doc.text, settings.chunk_size, settings.chunk_overlap)
        return [(raw, _fallback_metadata) for raw in fallback]
    return [(raw, _code_metadata) for raw in raws]


def chunk_document(doc: Document, settings: Settings) -> list[Chunk]:
    """Produces the `Chunk`s for a document, with stable ids and structural metadata."""
    # Cap oversized units so no chunk exceeds the embedding token budget (see _cap_oversized).
    capped = [
        (sub, meta_of)
        for raw, meta_of in _raws_with_metadata(doc, settings)
        for sub in _cap_oversized(raw, settings.max_chunk_tokens, settings.chunk_overlap)
    ]

    chunks: list[Chunk] = []
    for index, (raw, meta_of) in enumerate(capped):
        chunks.append(
            Chunk(
                id=f"{doc.id}#{index}",
                document_id=doc.id,
                text=raw["text"],
                doc_type=doc.doc_type,
                metadata=meta_of(doc, raw),
            )
        )
    return chunks
