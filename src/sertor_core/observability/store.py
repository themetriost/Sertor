"""Persistent observability store on SQLite (feature 020, REQ-H9-adjacent).

Keeps the structured events the core already emits via `log_event` in a local, queryable archive
(`<index_dir>/observability.sqlite`, git-ignored — same pattern as the embedding cache of feat.
019). Implements the `ObservabilityStore` port: the persistence handler writes here, the aggregation
feature (FEAT-002) will read here.

The store is an OPTIMISATION/service add-on, never a source of truth: a store failure degrades to a
no-op (write) / `[]` (read) with a warning, never an error of the observed operation (FR-007 — this
is not "silent null": a store outage is a legitimate, explicitly logged outcome).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from sertor_core.domain.entities import ObservedEvent
from sertor_core.observability.logging import log_event


class SqliteObservabilityStore:
    """`ObservabilityStore` on SQLite (stdlib only). Append-only events table."""

    def __init__(self, index_dir: Path | str):
        self._path = Path(index_dir) / "observability.sqlite"
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Open the DB and ensure the schema (lazy, idempotent). May raise `sqlite3.Error`."""
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._path)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events "
                "(id INTEGER PRIMARY KEY, ts REAL, operation TEXT, fields TEXT)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_op_ts ON events (operation, ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts)")
            self._conn = conn  # assigned only after a successful schema (corrupt file → stays None)
        return self._conn

    def record_event(self, ts: float, operation: str, fields: dict) -> None:
        """Append an event. Non-fatal on store failure (no-op + warning)."""
        try:
            conn = self._connect()
            conn.execute(
                "INSERT INTO events (ts, operation, fields) VALUES (?, ?, ?)",
                (ts, operation, json.dumps(fields, default=str, ensure_ascii=False)),
            )
            conn.commit()
        except sqlite3.Error as exc:
            log_event(logging.WARNING, "observability_store_unavailable",
                      reason=type(exc).__name__)

    def query_events(
        self, operation: str | None, since: float | None, until: float | None
    ) -> list[ObservedEvent]:
        """Events matching the filters, ordered by `ts`. `[]` on store failure (+ warning)."""
        clauses: list[str] = []
        params: list[object] = []
        if operation is not None:
            clauses.append("operation = ?")
            params.append(operation)
        if since is not None:
            clauses.append("ts >= ?")
            params.append(since)
        if until is not None:
            clauses.append("ts <= ?")
            params.append(until)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        try:
            conn = self._connect()
            rows = conn.execute(
                f"SELECT ts, operation, fields FROM events{where} ORDER BY ts, id", params
            ).fetchall()
            return [ObservedEvent(ts=ts, operation=op, fields=json.loads(fields))
                    for ts, op, fields in rows]
        except sqlite3.Error as exc:
            log_event(logging.WARNING, "observability_store_unavailable",
                      reason=type(exc).__name__)
            return []
