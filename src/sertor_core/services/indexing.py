"""Orchestratore di indicizzazione: la pipeline completa ingest → chunk → embed → store.

Concatena i servizi e gli adapter dietro le porte (Principio I) per indicizzare un repository in
una collezione namespaced. Full re-index idempotente (A-4/DA-004): rieseguire su un corpus
invariato produce lo stesso insieme di chunk id (REQ-010, SC-005). Emette log strutturati
(REQ-031). `installazione ≠ esecuzione`: l'indicizzazione avviene solo quando `index()` è chiamato
(Principio VI).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import Chunk, EmbeddedChunk, IndexReport
from sertor_core.domain.ports import EmbeddingProvider, VectorStore
from sertor_core.observability.logging import log_event
from sertor_core.services.chunking.dispatch import chunk_document
from sertor_core.services.ingestion import discover


def _payload(chunk: Chunk) -> dict:
    m = chunk.metadata
    return {
        "text": chunk.text,
        "path": m.path,
        "doc_type": chunk.doc_type.value,
        "chunker": m.chunker.value,
        "language": m.language,
        "qualname": m.qualname,
        "node_type": m.node_type,
        "start_line": m.start_line,
        "end_line": m.end_line,
        "heading_path": list(m.heading_path),
    }


class IndexingService:
    """Indicizza un repository in una collezione, cablando ingestione/chunking/embeddings/store."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection: str,
        settings: Settings,
    ):
        self._embedder = embedder
        self._store = store
        self._collection = collection
        self._settings = settings

    def index(self, root: Path | str) -> IndexReport:
        """Esegue la pipeline completa e restituisce un report con i conteggi."""
        started = time.perf_counter()
        documents = discover(root, self._settings)

        chunks: list[Chunk] = []
        for doc in documents:
            chunks.extend(chunk_document(doc, self._settings))

        if chunks:
            vectors = self._embedder.embed([c.text for c in chunks])
            records = [
                EmbeddedChunk(chunk_id=c.id, vector=v, payload=_payload(c))
                for c, v in zip(chunks, vectors, strict=True)
            ]
            self._store.upsert(self._collection, records)

        report = IndexReport(
            collection=self._collection,
            documents=len(documents),
            chunks=len(chunks),
            embedding_dim=self._embedder.dim,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        log_event(
            logging.INFO,
            "index",
            collection=self._collection,
            provider=self._embedder.name,
            documents=report.documents,
            chunks=report.chunks,
            embedding_dim=report.embedding_dim,
            elapsed_ms=report.elapsed_ms,
        )
        return report
