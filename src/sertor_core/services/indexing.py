"""Indexing orchestrator: the full pipeline ingest → chunk → embed → store.

Wires services and adapters behind ports (Principio I) to index a repository into a namespaced
collection. Full idempotent re-index (A-4/DA-004): re-running on an unchanged corpus produces the
same set of chunk ids (REQ-010, SC-005). Emits structured logs (REQ-031).
`install ≠ run`: indexing only happens when `index()` is called (Principio VI).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import Chunk, EmbeddedChunk, IndexReport, LexicalEntry
from sertor_core.domain.ports import CodeGraph, EmbeddingProvider, LexicalIndex, VectorStore
from sertor_core.observability.logging import log_event
from sertor_core.services.chunking.dispatch import chunk_document
from sertor_core.services.graph_extraction import extract_graph
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
    """Indexes a repository into a collection, wiring ingestion/chunking/embeddings/store."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection: str,
        settings: Settings,
        lexical: LexicalIndex | None = None,
        graph: CodeGraph | None = None,
    ):
        self._embedder = embedder
        self._store = store
        self._collection = collection
        self._settings = settings
        # Lexical sink for the hybrid engine (FEAT-004): when present, every index() also writes
        # the sidecar as a SNAPSHOT OF THE FULL chunk set (mirror semantics, REQ-002) — partial
        # upsert flows must not wire it (a partial sidecar would violate REQ-002).
        self._lexical = lexical
        # Code-graph sink (FEAT-005, DA-2): same mirror principle — the graph is rebuilt on every
        # index() from the same documents/chunks, never stale.
        self._graph = graph

    def index(self, root: Path | str, rebuild: bool = False) -> IndexReport:
        """Runs the full pipeline and returns a report with counts.

        With `rebuild=True` rebuilds the index from scratch: the collection `reset` happens
        **after** embedding and **before** upsert, so a provider error (during embed)
        leaves the pre-existing index intact (rebuild atomicity, REQ-004/NFR-004 of FEAT-002).
        """
        started = time.perf_counter()
        documents = discover(root, self._settings)

        chunks: list[Chunk] = []
        for doc in documents:
            chunks.extend(chunk_document(doc, self._settings))

        if chunks:
            vectors = self._embedder.embed([c.text for c in chunks])  # may fail: index intact
            records = [
                EmbeddedChunk(chunk_id=c.id, vector=v, payload=_payload(c))
                for c, v in zip(chunks, vectors, strict=True)
            ]
            if rebuild:
                self._store.reset(self._collection)  # discard the previous index, then rebuild
            self._store.upsert(self._collection, records)
            if self._lexical is not None:
                # Joint rebuild (REQ-003): same chunk set for both paths, written after a
                # successful embed (a provider error leaves BOTH indexes intact).
                self._lexical.build(self._collection, [
                    LexicalEntry(c.id, c.text, c.doc_type.value, c.metadata.path) for c in chunks
                ])
            if self._graph is not None:
                # The ambiguity threshold comes from Settings (Principio VIII, fix analyze W1).
                self._graph.build(self._settings.corpus, extract_graph(
                    documents, chunks,
                    ambiguity_threshold=self._settings.graph_ambiguity_threshold,
                ))
        elif rebuild:
            self._store.reset(self._collection)  # empty corpus on rebuild: clear the index
            if self._lexical is not None:
                self._lexical.build(self._collection, [])  # mirror: lexical index is also cleared
            if self._graph is not None:
                self._graph.build(self._settings.corpus, extract_graph(
                    [], [], ambiguity_threshold=self._settings.graph_ambiguity_threshold,
                ))

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
