"""Local memory archive store on SQLite (feature 031, FR-009..016/025).

Keeps the captured, scrubbed transcripts in a local, queryable archive
(`<index_dir>/memory.sqlite`, git-ignored — same pattern as `SqliteObservabilityStore` and
`EmbeddingCache`). Concrete component, NO port (single consumer today — D2): lazy connect, schema
idempotent, degradation non-fatal.

The archive is conserved and append-only: `INSERT OR IGNORE` makes re-archiving a session a no-op
(FR-015/016); no `DELETE`/`REPLACE` (FR-014). A store failure degrades to a warning + no-op/`None`,
never an error of the archiving run (FR-025 — not "silent null": a store outage is a legitimate,
explicitly logged outcome). **stdlib-only** (`sqlite3`, `json`).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from sertor_core.domain.memory import ArchivedSession, TranscriptTurn
from sertor_core.observability.logging import log_event


class MemoryArchive:
    """SQLite archive of scrubbed sessions+turns (concrete, stdlib only)."""

    def __init__(self, index_dir: Path | str):
        self._path = Path(index_dir) / "memory.sqlite"
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Open the DB and ensure the schema (lazy, idempotent). May raise `sqlite3.Error`."""
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._path)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sessions ("
                "session_key TEXT PRIMARY KEY, project_id TEXT NOT NULL, "
                "captured_at REAL NOT NULL, adapter_kind TEXT NOT NULL, metadata TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS turns ("
                "session_key TEXT NOT NULL, turn_index INTEGER NOT NULL, role TEXT NOT NULL, "
                "ts REAL, content TEXT NOT NULL, PRIMARY KEY (session_key, turn_index))"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions (project_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_turns_session ON turns (session_key, turn_index)"
            )
            self._conn = conn  # assigned only after a successful schema (corrupt file → stays None)
        return self._conn

    def upsert(self, session: ArchivedSession) -> bool:
        """Insert the session + its turns in one transaction. `True` if NEW, `False` otherwise.

        Idempotent (FR-015/016): `INSERT OR IGNORE` makes a re-archive a no-op, the existing record
        stays untouched (FR-014). Non-fatal on `sqlite3.Error`: warning + `False` (FR-025).
        `session.turns` is ALREADY scrubbed (the scrub is the service's responsibility).
        """
        try:
            conn = self._connect()
            cursor = conn.execute(
                "INSERT OR IGNORE INTO sessions "
                "(session_key, project_id, captured_at, adapter_kind, metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    session.session_key,
                    session.project_id,
                    session.captured_at,
                    session.adapter_kind,
                    _metadata_json(session),
                ),
            )
            is_new = cursor.rowcount > 0
            if is_new:
                conn.executemany(
                    "INSERT OR IGNORE INTO turns "
                    "(session_key, turn_index, role, ts, content) VALUES (?, ?, ?, ?, ?)",
                    [
                        (session.session_key, turn.index, turn.role, turn.ts, turn.text)
                        for turn in session.turns
                    ],
                )
            conn.commit()
            return is_new
        except sqlite3.Error as exc:
            log_event(logging.WARNING, "memory_archive_unavailable", reason=type(exc).__name__)
            return False

    def exists(self, session_key: str) -> bool:
        """`True` if the session is archived. Non-fatal: store failure → warning + `False`."""
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE session_key = ?", (session_key,)
            ).fetchone()
            return row is not None
        except sqlite3.Error as exc:
            log_event(logging.WARNING, "memory_archive_unavailable", reason=type(exc).__name__)
            return False

    def get(self, session_key: str) -> ArchivedSession | None:
        """Recompose the archived session (turns in `turn_index` order), or `None` if absent.

        Non-fatal: store failure → warning + `None`. Used by tests and, in future, FEAT-002.
        """
        try:
            conn = self._connect()
            session_row = conn.execute(
                "SELECT project_id, captured_at, adapter_kind, metadata "
                "FROM sessions WHERE session_key = ?",
                (session_key,),
            ).fetchone()
            if session_row is None:
                return None
            project_id, captured_at, adapter_kind, metadata = session_row
            turn_rows = conn.execute(
                "SELECT turn_index, role, ts, content FROM turns "
                "WHERE session_key = ? ORDER BY turn_index",
                (session_key,),
            ).fetchall()
            turns = tuple(
                TranscriptTurn(index=idx, role=role, text=content, ts=ts)
                for idx, role, ts, content in turn_rows
            )
            retention_days = json.loads(metadata).get("retention_days")
            return ArchivedSession(
                session_key=session_key,
                project_id=project_id,
                captured_at=captured_at,
                adapter_kind=adapter_kind,
                turns=turns,
                retention_days=retention_days,
            )
        except sqlite3.Error as exc:
            log_event(logging.WARNING, "memory_archive_unavailable", reason=type(exc).__name__)
            return None


def _metadata_json(session: ArchivedSession) -> str:
    """JSON metadata for the session row: retention hook + provenance (FR-021/022, gancio only)."""
    return json.dumps(
        {
            "retention_days": session.retention_days,
            "turn_count": len(session.turns),
        },
        ensure_ascii=False,
    )
