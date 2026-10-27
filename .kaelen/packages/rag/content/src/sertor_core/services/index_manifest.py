"""Index manifest: the persistent memory of «what is already indexed» (046, FEAT-009).

Concrete store on SQLite (`<index_dir>/index_manifest.sqlite`), NO port — single consumer is the
indexing service, same pattern as `EmbeddingCache`/`MemoryArchive` (Principio III). stdlib only
(`sqlite3`/`hashlib`). It remembers, per source file, `mtime + content-hash + logic-version` and
CONSERVES the derived units (`Document` text + `Chunk`s) so the incremental run can rebuild BM25 and
the code-graph from the FULL set of units without re-reading/re-chunking the unchanged files (F1).

The manifest is namespaced per collection `(corpus, provider)`: `load(collection)` returns the state
only when the stored schema/collection match; an incompatible schema → `None`, so the caller falls
back to a full rebuild (FR-011, Principio IV — no silent stale state). Everything here is additive
and rigenerabile (gitignored): it never replaces the vector store / sidecars as source of truth.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sertor_core.domain.entities import (
    Chunk,
    ChunkerKind,
    ChunkMetadata,
    DocType,
    Document,
    FileClassification,
)

_SCHEMA_VERSION = "sertor.manifest/1"


def content_hash(text: str) -> str:
    """Stable content key for a source file's text: sha256 hex (same scheme as EmbeddingCache)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FileStat:
    """Cheap stat of a source file + a lazy hash thunk (046, FR-002/003).

    `mtime` is the pre-filter (cheap); `read_hash` computes the content-hash only for the candidates
    whose mtime changed or that are new — so an unchanged corpus costs ~just the `stat` (NFR-4).
    """

    path: str
    mtime: float
    read_hash: Callable[[], str]


@dataclass(frozen=True)
class Classification:
    """Per-file verdict of `classify`: which files are new/modified/deleted/unchanged."""

    unchanged: tuple[str, ...] = ()
    new: tuple[str, ...] = ()
    modified: tuple[str, ...] = ()
    deleted: tuple[str, ...] = ()
    # content-hash computed during classification, reused by `apply` (avoid re-hashing).
    hashes: dict[str, str] = field(default_factory=dict)

    def has_changes(self) -> bool:
        return bool(self.new or self.modified or self.deleted)


@dataclass(frozen=True)
class ManifestState:
    """Loaded manifest snapshot for a collection: enough to classify + reconcile."""

    collection: str
    logic_version: str
    reconcile_counter: int
    files: dict[str, tuple[float, str, str]]  # path -> (mtime, content_hash, logic_version)


class IndexManifest:
    """SQLite-backed manifest of indexed files + their derived units (concrete, stdlib only)."""

    def __init__(self, index_dir: Path | str):
        self._path = Path(index_dir) / "index_manifest.sqlite"
        self._conn: sqlite3.Connection | None = None

    # -- connection / schema ---------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Open the DB and ensure the schema (lazy, idempotent). May raise `sqlite3.Error`."""
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._path)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS meta ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS files ("
                "path TEXT PRIMARY KEY, mtime REAL NOT NULL, content_hash TEXT NOT NULL, "
                "logic_version TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS documents ("
                "doc_id TEXT PRIMARY KEY, text TEXT NOT NULL, doc_type TEXT NOT NULL, "
                "language TEXT NOT NULL, path TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS chunks ("
                "chunk_id TEXT PRIMARY KEY, doc_id TEXT NOT NULL, ordinal INTEGER NOT NULL, "
                "text TEXT NOT NULL, doc_type TEXT NOT NULL, path TEXT NOT NULL, "
                "metadata_json TEXT NOT NULL)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks (doc_id)")
            self._conn = conn  # assigned only after a successful schema (corrupt → stays None)
        return self._conn

    @staticmethod
    def schema_version() -> str:
        return _SCHEMA_VERSION

    # -- load / classify -------------------------------------------------------------------------

    def load(self, collection: str) -> ManifestState | None:
        """Return the manifest state for `collection`, or `None` → caller does a full (FR-011).

        `None` when: the file is empty/never written for this collection, the schema version is
        incompatible, or the stored collection differs (provider/corpus changed → vectors live in a
        different collection, the manifest does not apply). Non-fatal on `sqlite3.Error`: `None`.
        """
        try:
            conn = self._connect()
            meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
            if meta.get("schema_version") != _SCHEMA_VERSION:
                return None
            if meta.get("collection") != collection:
                return None
            rows = conn.execute(
                "SELECT path, mtime, content_hash, logic_version FROM files"
            ).fetchall()
            files = {p: (m, h, lv) for p, m, h, lv in rows}
            return ManifestState(
                collection=collection,
                logic_version=meta.get("logic_version", ""),
                reconcile_counter=int(meta.get("reconcile_counter", "0")),
                files=files,
            )
        except sqlite3.Error:
            return None

    def classify(
        self, state: ManifestState, current: list[FileStat], logic_version: str
    ) -> Classification:
        """Compare the current source files against the manifest (FR-002/003/013).

        mtime is the cheap pre-filter; the content-hash confirms (a file touched but not changed
        stays UNCHANGED). If `logic_version` differs from the file's recorded one, the file is
        MODIFIED even if its content is identical (the derived units would differ — FR-013).
        """
        unchanged: list[str] = []
        new: list[str] = []
        modified: list[str] = []
        hashes: dict[str, str] = {}
        current_paths = {f.path for f in current}

        for stat in current:
            recorded = state.files.get(stat.path)
            if recorded is None:
                new.append(stat.path)
                hashes[stat.path] = stat.read_hash()
                continue
            rec_mtime, rec_hash, rec_logic = recorded
            if rec_mtime == stat.mtime and rec_logic == logic_version:
                # cheap path: mtime + logic-version unchanged → trust the recorded hash.
                unchanged.append(stat.path)
                continue
            # mtime/logic changed → confirm with the hash.
            new_hash = stat.read_hash()
            hashes[stat.path] = new_hash
            if new_hash == rec_hash and rec_logic == logic_version:
                unchanged.append(stat.path)
            else:
                modified.append(stat.path)

        deleted = [p for p in state.files if p not in current_paths]
        return Classification(
            unchanged=tuple(unchanged),
            new=tuple(new),
            modified=tuple(modified),
            deleted=tuple(deleted),
            hashes=hashes,
        )

    # -- read derived units (for the secondary rebuild) ------------------------------------------

    def units_for(self, doc_ids: list[str]) -> tuple[list[Document], list[Chunk]]:
        """Reconstruct the conserved `Document`s + `Chunk`s for the given file ids (FR-007).

        Used to feed BM25 and the code-graph the FULL set of units (unchanged from manifest ∪ fresh)
        without re-reading/re-chunking the unchanged files. Order is by id (determinism).
        """
        if not doc_ids:
            return [], []
        conn = self._connect()
        documents: list[Document] = []
        for doc_id in sorted(doc_ids):
            row = conn.execute(
                "SELECT doc_id, text, doc_type, language, path FROM documents WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
            if row is None:
                continue
            d_id, text, doc_type, language, path = row
            documents.append(
                Document(
                    id=d_id, text=text, doc_type=DocType(doc_type), language=language, path=path
                )
            )
        chunks: list[Chunk] = []
        for doc in documents:
            rows = conn.execute(
                "SELECT chunk_id, doc_id, ordinal, text, doc_type, path, metadata_json "
                "FROM chunks WHERE doc_id = ? ORDER BY ordinal",
                (doc.id,),
            ).fetchall()
            for chunk_id, doc_id, _ordinal, text, doc_type, _path, metadata_json in rows:
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        document_id=doc_id,
                        text=text,
                        doc_type=DocType(doc_type),
                        metadata=_metadata_from_json(metadata_json),
                    )
                )
        return documents, chunks

    def chunk_ids_for(self, doc_ids: list[str]) -> list[str]:
        """Chunk ids recorded for the files (for the targeted `VectorStore.delete`, FR-005)."""
        if not doc_ids:
            return []
        conn = self._connect()
        out: list[str] = []
        for doc_id in doc_ids:
            rows = conn.execute(
                "SELECT chunk_id FROM chunks WHERE doc_id = ? ORDER BY ordinal", (doc_id,)
            ).fetchall()
            out.extend(r[0] for r in rows)
        return out

    # -- write -----------------------------------------------------------------------------------

    def apply(
        self,
        collection: str,
        logic_version: str,
        *,
        added: list[tuple[Document, list[Chunk], FileStat, str]],
        updated: list[tuple[Document, list[Chunk], FileStat, str]],
        removed: list[str],
        reconcile_counter: int | None = None,
    ) -> None:
        """Persist the run's changes in ONE transaction (FR-005, atomic — no partial state, FR-014).

        `added`/`updated` items carry the fresh `Document`, its `Chunk`s, the `FileStat` (mtime) and
        the content-hash; `removed` is the list of deleted file paths. Writes `meta` (schema,
        collection, logic-version, reconcile counter), upserts files/documents/chunks for the
        changed files, and removes the rows of deleted/modified files first (so stale chunks of a
        modified file do not linger).
        """
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            self._write_meta(conn, collection, logic_version, reconcile_counter)
            # Modified files: drop old document+chunk rows first (the chunk count may shrink).
            for _doc, _chunks, stat, _h in updated:
                conn.execute("DELETE FROM documents WHERE doc_id = ?", (stat.path,))
                conn.execute("DELETE FROM chunks WHERE doc_id = ?", (stat.path,))
            for path in removed:
                conn.execute("DELETE FROM files WHERE path = ?", (path,))
                conn.execute("DELETE FROM documents WHERE doc_id = ?", (path,))
                conn.execute("DELETE FROM chunks WHERE doc_id = ?", (path,))
            for doc, chunks, stat, file_hash in (*added, *updated):
                self._upsert_file(conn, stat, file_hash, logic_version)
                self._upsert_document(conn, doc)
                self._upsert_chunks(conn, doc.id, chunks)
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise

    def write_full(
        self,
        collection: str,
        logic_version: str,
        files: list[tuple[Document, list[Chunk], FileStat, str]],
    ) -> None:
        """Rewrite the whole manifest after a FULL run (rebuild=True / fallback): clears + rewrites.

        Keeps the manifest the single truth of «what is indexed» after a full reset, with the
        reconcile counter reset to 0 (a full IS a reconciliation).
        """
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM files")
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM chunks")
            self._write_meta(conn, collection, logic_version, 0)
            for doc, chunks, stat, file_hash in files:
                self._upsert_file(conn, stat, file_hash, logic_version)
                self._upsert_document(conn, doc)
                self._upsert_chunks(conn, doc.id, chunks)
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise

    def bump_reconcile(self, state: ManifestState | None, reconcile_every: int) -> bool:
        """Return True when this run should be a reconciliation full (FR-019); OFF when every<=0.

        Counts indexing runs in `meta.reconcile_counter`; when `(counter+1) % every == 0` the caller
        runs a full instead of an incremental. The counter is advanced by `apply`/`write_full` via
        `reconcile_counter`; this method only DECIDES (pure read of the loaded state).
        """
        if reconcile_every <= 0 or state is None:
            return False
        return (state.reconcile_counter + 1) % reconcile_every == 0

    # -- internals -------------------------------------------------------------------------------

    @staticmethod
    def _write_meta(
        conn: sqlite3.Connection, collection: str, logic_version: str, counter: int | None
    ) -> None:
        items = {
            "schema_version": _SCHEMA_VERSION,
            "collection": collection,
            "logic_version": logic_version,
        }
        if counter is not None:
            items["reconcile_counter"] = str(counter)
        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            list(items.items()),
        )

    @staticmethod
    def _upsert_file(
        conn: sqlite3.Connection, stat: FileStat, file_hash: str, logic_version: str
    ) -> None:
        conn.execute(
            "INSERT INTO files (path, mtime, content_hash, logic_version) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(path) DO UPDATE SET mtime = excluded.mtime, "
            "content_hash = excluded.content_hash, logic_version = excluded.logic_version",
            (stat.path, stat.mtime, file_hash, logic_version),
        )

    @staticmethod
    def _upsert_document(conn: sqlite3.Connection, doc: Document) -> None:
        conn.execute(
            "INSERT INTO documents (doc_id, text, doc_type, language, path) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(doc_id) DO UPDATE SET text = excluded.text, doc_type = excluded.doc_type, "
            "language = excluded.language, path = excluded.path",
            (doc.id, doc.text, doc.doc_type.value, doc.language, doc.path),
        )

    @staticmethod
    def _upsert_chunks(conn: sqlite3.Connection, doc_id: str, chunks: list[Chunk]) -> None:
        conn.executemany(
            "INSERT INTO chunks "
            "(chunk_id, doc_id, ordinal, text, doc_type, path, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(chunk_id) DO UPDATE SET doc_id = excluded.doc_id, "
            "ordinal = excluded.ordinal, text = excluded.text, doc_type = excluded.doc_type, "
            "path = excluded.path, metadata_json = excluded.metadata_json",
            [
                (
                    c.id, doc_id, ordinal, c.text, c.doc_type.value,
                    c.metadata.path, _metadata_to_json(c.metadata),
                )
                for ordinal, c in enumerate(chunks)
            ],
        )


def _metadata_to_json(meta: ChunkMetadata) -> str:
    """Serialise `ChunkMetadata` to JSON (round-trips exactly: the graph needs every field)."""
    return json.dumps(
        {
            "path": meta.path,
            "chunker": meta.chunker.value,
            "language": meta.language,
            "qualname": meta.qualname,
            "symbol": meta.symbol,
            "node_type": meta.node_type,
            "start_line": meta.start_line,
            "end_line": meta.end_line,
            "heading_path": list(meta.heading_path),
        },
        ensure_ascii=False,
    )


def _metadata_from_json(raw: str) -> ChunkMetadata:
    """Rebuild `ChunkMetadata` from the persisted JSON (inverse of `_metadata_to_json`)."""
    d = json.loads(raw)
    return ChunkMetadata(
        path=d["path"],
        chunker=ChunkerKind(d["chunker"]),
        language=d.get("language", ""),
        qualname=d.get("qualname"),
        symbol=d.get("symbol"),
        node_type=d.get("node_type"),
        start_line=d.get("start_line"),
        end_line=d.get("end_line"),
        heading_path=tuple(d.get("heading_path", ())),
    )


# Keep the classification enum importable from this module too (alias, T006).
__all__ = [
    "Classification",
    "FileClassification",
    "FileStat",
    "IndexManifest",
    "ManifestState",
    "content_hash",
]
