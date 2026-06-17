"""Indexing orchestrator: the pipeline ingest → chunk → embed → store (full + incremental).

Wires services and adapters behind ports (Principio I) to index a repository into a namespaced
collection. Two paths share the same primitives:

- **Full** (`rebuild=True`, `index_incremental=False`, or no valid manifest — FR-010/011): the
  original 5-stage pipeline (discover → chunk → embed → reset+upsert → build BM25/graph). It also
  (re)writes the manifest so the next run can go incremental.
- **Incremental** (default when a valid manifest exists — FR-002): classify the source files
  (unchanged/new/modified/deleted), re-chunk+embed only the changed files, **upsert/delete mirati**
  on the vector store (`delete` already exists on the port), then **rebuild BM25 + code-graph from
  the FULL set of units** (manifest-conserved units of the unchanged files ∪ fresh — F1). The
  postcondition is equivalence with a full on the same source (FR-012).

A single-writer lock (FR-020) prevents concurrent runs from corrupting the manifest. Errors are
explicit (Principio IV): an incompatible manifest → fallback to full; a failure mid-run leaves no
partial state (the manifest transaction rolls back). `install ≠ run`: indexing only happens when
`index()` is called (Principio VI).
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import Chunk, Document, EmbeddedChunk, IndexReport, LexicalEntry
from sertor_core.domain.errors import IndexLockedError
from sertor_core.domain.ports import CodeGraph, EmbeddingProvider, LexicalIndex, VectorStore
from sertor_core.observability.logging import log_event
from sertor_core.services.chunking.dispatch import chunk_document
from sertor_core.services.graph_extraction import COVERAGE, extract_graph
from sertor_core.services.index_manifest import (
    FileStat,
    IndexManifest,
    ManifestState,
    content_hash,
)
from sertor_core.services.ingestion import SourceFile, discover_files, read_source


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


def _logic_version(settings: Settings) -> str:
    """Identity of the chunking + graph-extraction logic (046, FR-013).

    When chunking parameters or the graph coverage change, the derived units (chunks/edges) of an
    unchanged file would differ: a manifest stamped with a different logic-version is treated as
    MODIFIED for every file (in `classify`), so the incremental result stays equivalent to a full.
    """
    coverage_sig = ";".join(f"{lang}:{','.join(kinds)}" for lang, kinds in sorted(COVERAGE.items()))
    return (
        f"chunk={settings.chunk_size}/{settings.chunk_overlap}/maxtok{settings.max_chunk_tokens}"
        f"|cov={coverage_sig}"
    )


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
        manifest: IndexManifest | None = None,
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
        # Index manifest (046): the memory of «what is already indexed» that enables the incremental
        # path. None → the service always runs full (manifest disabled).
        self._manifest = manifest

    # -- public entry ----------------------------------------------------------------------------

    def index(self, root: Path | str, rebuild: bool = False) -> IndexReport:
        """Run the pipeline (full or incremental) under a single-writer lock; return a report.

        `rebuild=True` (or `index_incremental=False`, or a missing/incompatible manifest, or a due
        reconciliation) forces a full rebuild from scratch — the collection `reset` happens after
        embedding and before upsert, so a provider error leaves the pre-existing index intact
        (rebuild atomicity, REQ-004/NFR-004 of FEAT-002). Otherwise the run is incremental (FR-002).
        Raises `IndexLockedError` if another process holds the lock (FR-020).
        """
        root = Path(root)
        with self._lock():
            return self._index_locked(root, rebuild)

    # -- dispatch --------------------------------------------------------------------------------

    def _index_locked(self, root: Path, rebuild: bool) -> IndexReport:
        state = self._load_manifest_state()
        reconcile_due = (
            self._manifest is not None
            and self._manifest.bump_reconcile(state, self._settings.index_reconcile_every)
        )
        go_full = (
            rebuild
            or not self._settings.index_incremental
            or self._manifest is None
            or state is None
            or reconcile_due
        )
        if go_full:
            return self._run_full(root)
        return self._run_incremental(root, state)

    # -- full path -------------------------------------------------------------------------------

    def _run_full(self, root: Path) -> IndexReport:
        """The original full pipeline, plus (re)writing the manifest (FR-010).

        `write_full` resets the manifest's reconcile counter to 0 (a full IS a reconciliation).
        """
        started = time.perf_counter()
        # discover_files gives the stats; read via the split so the manifest records mtime/hash.
        sources = discover_files(root, self._settings)
        documents: list[Document] = []
        stats: dict[str, FileStat] = {}
        for source in sources:
            doc = read_source(source)
            if doc is None:
                continue
            documents.append(doc)
            stats[source.rel] = _file_stat(source, doc)
        log_event(
            logging.INFO, "ingest", root=str(root), documents=len(documents),
            skipped=len(sources) - len(documents),
        )

        chunks_by_doc: dict[str, list[Chunk]] = {
            doc.id: chunk_document(doc, self._settings) for doc in documents
        }
        chunks: list[Chunk] = [c for doc in documents for c in chunks_by_doc[doc.id]]

        if chunks:
            vectors = self._embedder.embed([c.text for c in chunks])  # may fail: index intact
            records = [
                EmbeddedChunk(chunk_id=c.id, vector=v, payload=_payload(c))
                for c, v in zip(chunks, vectors, strict=True)
            ]
            self._store.reset(self._collection)  # discard the previous index, then rebuild
            self._store.upsert(self._collection, records)
            self._rebuild_secondary(documents, chunks)
        else:
            self._store.reset(self._collection)  # empty corpus on rebuild: clear the index
            self._rebuild_secondary([], [])

        if self._manifest is not None:
            self._manifest.write_full(
                self._collection,
                _logic_version(self._settings),
                [(doc, chunks_by_doc[doc.id], stats[doc.id], stats[doc.id].read_hash())
                 for doc in documents],
            )

        report = IndexReport(
            collection=self._collection,
            documents=len(documents),
            chunks=len(chunks),
            embedding_dim=self._embedder.dim,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            added=len(documents),
            cache_hits=self._cache_hits(),
            mode="full",
        )
        self._emit(report)
        return report

    # -- incremental path ------------------------------------------------------------------------

    def _run_incremental(self, root: Path, state: ManifestState) -> IndexReport:
        """Classify → process changed → prune → rebuild secondaries → persist (FR-002..008)."""
        assert self._manifest is not None  # guaranteed by the dispatch (go_full handles None)
        started = time.perf_counter()
        logic_version = _logic_version(self._settings)

        sources = discover_files(root, self._settings)
        by_rel = {s.rel: s for s in sources}
        current = [
            FileStat(path=s.rel, mtime=s.mtime, read_hash=_hash_thunk(s)) for s in sources
        ]
        classification = self._manifest.classify(state, current, logic_version)

        # Read+chunk the changed files (NEW/MODIFIED). DELETED files are not read (gone from disk).
        changed_rels = [*classification.new, *classification.modified]
        fresh_docs: dict[str, Document] = {}
        fresh_chunks: dict[str, list[Chunk]] = {}
        for rel in changed_rels:
            doc = read_source(by_rel[rel])
            if doc is None:
                continue  # unreadable now → skip (read_source warned); leave the manifest row
            fresh_docs[rel] = doc
            fresh_chunks[rel] = chunk_document(doc, self._settings)

        # Embed only the fresh chunks (the cache spares identical text — FEAT-019).
        all_fresh_chunks = [
            c for rel in changed_rels if rel in fresh_chunks for c in fresh_chunks[rel]
        ]
        if all_fresh_chunks:
            vectors = self._embedder.embed([c.text for c in all_fresh_chunks])
            records = [
                EmbeddedChunk(chunk_id=c.id, vector=v, payload=_payload(c))
                for c, v in zip(all_fresh_chunks, vectors, strict=True)
            ]
        else:
            records = []

        # Prune: delete the OLD chunk ids of MODIFIED + DELETED files BEFORE upserting the fresh
        # ones (a modified file may now have fewer chunks → stale ids must go). FR-005.
        prune_ids = self._manifest.chunk_ids_for(
            [*classification.modified, *classification.deleted]
        )
        if prune_ids:
            self._store.delete(self._collection, prune_ids)
        if records:
            self._store.upsert(self._collection, records)

        # Rebuild secondaries from the FULL unit set: manifest-conserved (UNCHANGED) ∪ fresh (F1).
        kept_docs, kept_chunks = self._manifest.units_for(list(classification.unchanged))
        all_documents = [*kept_docs, *(fresh_docs[r] for r in changed_rels if r in fresh_docs)]
        all_chunks = [*kept_chunks,
                      *(c for r in changed_rels if r in fresh_chunks for c in fresh_chunks[r])]
        self._rebuild_secondary(all_documents, all_chunks)

        # Persist the manifest atomically (FR-005/014): no partial state on failure (rollback).
        # Reuse the hash already computed during classification (no re-read).
        def _entry(rel: str):
            stat = FileStat(rel, by_rel[rel].mtime, lambda r=rel: classification.hashes[r])
            return (fresh_docs[rel], fresh_chunks[rel], stat, classification.hashes[rel])

        self._manifest.apply(
            self._collection,
            logic_version,
            added=[_entry(r) for r in classification.new if r in fresh_docs],
            updated=[_entry(r) for r in classification.modified if r in fresh_docs],
            removed=list(classification.deleted),
            reconcile_counter=state.reconcile_counter + 1,
        )

        report = IndexReport(
            collection=self._collection,
            documents=len(all_documents),
            chunks=len(all_chunks),
            embedding_dim=self._embedder.dim,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            added=len([r for r in classification.new if r in fresh_docs]),
            updated=len([r for r in classification.modified if r in fresh_docs]),
            removed=len(classification.deleted),
            unchanged=len(classification.unchanged),
            cache_hits=self._cache_hits(),
            mode="incremental",
        )
        self._emit(report)
        return report

    # -- shared helpers --------------------------------------------------------------------------

    def _rebuild_secondary(self, documents: list[Document], chunks: list[Chunk]) -> None:
        """(Re)build BM25 + code-graph as a full snapshot of the given units (mirror, REQ-002)."""
        if self._lexical is not None:
            self._lexical.build(self._collection, [
                LexicalEntry(c.id, c.text, c.doc_type.value, c.metadata.path) for c in chunks
            ])
        if self._graph is not None:
            self._graph.build(self._settings.corpus, extract_graph(
                documents, chunks,
                ambiguity_threshold=self._settings.graph_ambiguity_threshold,
            ))

    def _load_manifest_state(self) -> ManifestState | None:
        if self._manifest is None:
            return None
        return self._manifest.load(self._collection)

    def _cache_hits(self) -> int:
        """Best-effort embeddings cache hits this run (FR-015); 0 when the cache is not wired."""
        return int(getattr(self._embedder, "total_hits", 0))

    def _emit(self, report: IndexReport) -> None:
        log_event(
            logging.INFO,
            "index",
            collection=self._collection,
            provider=self._embedder.name,
            mode=report.mode,
            documents=report.documents,
            chunks=report.chunks,
            added=report.added,
            updated=report.updated,
            removed=report.removed,
            unchanged=report.unchanged,
            cache_hits=report.cache_hits,
            embedding_dim=report.embedding_dim,
            elapsed_ms=report.elapsed_ms,
        )

    # -- single-writer lock (FR-020) -------------------------------------------------------------

    def _lock(self) -> _IndexLock:
        return _IndexLock(self._settings.index_dir)


class _IndexLock:
    """Single-writer lock via an exclusive lockfile in `index_dir` (046, FR-020).

    A second concurrent run finds the lockfile already present (`O_CREAT | O_EXCL`) and raises
    `IndexLockedError`. The lock is released on exit even on error. Stdlib only (`os.open`); the
    lockfile is gitignored and rigenerabile (a stale file left by a crash can be removed by hand,
    the error message says so).
    """

    def __init__(self, index_dir: Path | str):
        self._dir = Path(index_dir)
        self._path = self._dir / ".index.lock"
        self._fd: int | None = None

    def __enter__(self) -> _IndexLock:
        self._dir.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise IndexLockedError(str(self._dir)) from exc
        os.write(self._fd, str(os.getpid()).encode("utf-8"))
        return self

    def __exit__(self, *exc) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self._path.unlink()
        except OSError:
            pass


def _file_stat(source: SourceFile, doc: Document) -> FileStat:
    """A `FileStat` whose hash is computed from the already-read document text (no extra read)."""
    text = doc.text
    return FileStat(path=source.rel, mtime=source.mtime, read_hash=lambda: content_hash(text))


def _hash_thunk(source: SourceFile):
    """Lazy hash thunk: reads + hashes a discovered file only when invoked (classify candidates)."""
    def _read() -> str:
        doc = read_source(source)
        return content_hash(doc.text) if doc is not None else ""
    return _read
