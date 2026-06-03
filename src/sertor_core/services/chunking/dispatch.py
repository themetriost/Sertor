"""Dispatcher di chunking: seleziona il chunker giusto per documento e produce `Chunk` di dominio.

Codice → chunker sintattico (con fallback dimensionale se la lingua non è supportata, REQ-009);
Markdown → chunker per heading (REQ-008); altro testo → fallback dimensionale. Assegna a ogni
chunk un id stabile `f"{document_id}#{index}"` (ordinale posizionale, REQ-010) per garantire
l'idempotenza a contenuto invariato (Principio VI).
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


def chunk_document(doc: Document, settings: Settings) -> list[Chunk]:
    """Produce i `Chunk` di un documento, con id stabili e metadati strutturali."""
    if doc.doc_type is DocType.DOC:
        raws = markdown_chunks(doc.text)
        meta_of = _markdown_metadata
    else:
        raws = code_chunks(doc.text, doc.language, settings.chunk_size)
        if raws is None:  # lingua non supportata sintatticamente -> fallback dimensionale
            raws = size_chunks(doc.text, settings.chunk_size, settings.chunk_overlap)
            meta_of = _fallback_metadata
        else:
            meta_of = _code_metadata

    chunks: list[Chunk] = []
    for index, raw in enumerate(raws):
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
