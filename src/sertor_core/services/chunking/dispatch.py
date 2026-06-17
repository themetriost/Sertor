"""Chunking dispatcher: selects the right chunker for a document and produces domain `Chunk`s.

Code → syntactic chunker (with size-based fallback if the language is not supported, REQ-009);
Markdown → heading-based chunker (REQ-008); other text → size-based fallback. Assigns each
chunk a stable id `f"{document_id}#{index}"` (positional ordinal, REQ-010) to guarantee
idempotency when content is unchanged (Principio VI).
"""
from __future__ import annotations

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import Chunk, ChunkerKind, ChunkMetadata, DocType, Document
from sertor_core.services.chunking.code import code_chunks
from sertor_core.services.chunking.fallback import size_chunks
from sertor_core.services.chunking.markdown import markdown_chunks


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


def _cap_oversized(raw: dict, max_chars: int, overlap: int) -> list[dict]:
    """Sub-split a raw chunk that exceeds `max_chars` on line boundaries (robustness).

    Structural chunkers (markdown by heading, code by symbol) can emit a unit far larger than
    `chunk_size`; embedding providers reject inputs over a token budget (text-embedding-3-large:
    8192 tokens → http 400). A raw within the cap is returned unchanged; an oversized one is split
    into windows of `max_chars`, the structural metadata (heading_path/qualname/…) inherited and the
    line range offset back onto the document so it stays correct.
    """
    if len(raw["text"]) <= max_chars:
        return [raw]
    base = raw.get("start_line", 1) or 1
    pieces: list[dict] = []
    for piece in size_chunks(raw["text"], max_chars, overlap):
        sub = dict(raw)  # inherit heading_path/qualname/symbol/node_type/language
        sub["text"] = piece["text"]
        sub["start_line"] = base + piece["start_line"] - 1
        sub["end_line"] = base + piece["end_line"] - 1
        pieces.append(sub)
    return pieces


def chunk_document(doc: Document, settings: Settings) -> list[Chunk]:
    """Produces the `Chunk`s for a document, with stable ids and structural metadata."""
    if doc.doc_type is DocType.DOC:
        raws = markdown_chunks(doc.text)
        meta_of = _markdown_metadata
    else:
        raws = code_chunks(doc.text, doc.language, settings.chunk_size)
        if raws is None:  # language not supported syntactically -> size-based fallback
            raws = size_chunks(doc.text, settings.chunk_size, settings.chunk_overlap)
            meta_of = _fallback_metadata
        else:
            meta_of = _code_metadata

    # Cap oversized units so no chunk exceeds the embedding token budget (see _cap_oversized).
    capped = [
        sub
        for raw in raws
        for sub in _cap_oversized(raw, settings.max_chunk_chars, settings.chunk_overlap)
    ]

    chunks: list[Chunk] = []
    for index, raw in enumerate(capped):
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
