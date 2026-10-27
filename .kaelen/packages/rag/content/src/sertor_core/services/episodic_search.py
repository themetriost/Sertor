"""Local episodic full-text search over the memory archive (033, FEAT-002).

Makes the transcript archive produced by FEAT-001 (`<index_dir>/memory.sqlite`) *queryable* at
turn granularity: «have we talked about this before?», «how did that end?». Technical approach
(research.md): native **SQLite FTS5** — an external-content virtual table `turns_fts` indexing
`turns.content` in the SAME file, ranked with `bm25()` and snippeted with `snippet()`, kept in
sync by triggers on `turns`. Stdlib only (`sqlite3`, `hashlib`, `time`, `logging`); zero cloud in
the query path (privacy by design).

Concrete component, NO port (single consumer/backend today — same profile as `MemoryArchive`).
Read-only on FEAT-001 data: it never writes `sessions`/`turns`; the FTS index is a derived,
rebuildable artefact created lazily and idempotently. Degradation is non-fatal everywhere except
an impossible time window (`since > until` → `InvalidTimeWindowError`, Principio IV): a missing /
empty / corrupt archive, or an `sqlite3` built without FTS5, all degrade to an explicit empty
state + warning, never a crash. Host-agnostic (Principio X): `adapter_kind`/`project_id` are
opaque data, never branched on.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sertor_core.domain.errors import InvalidTimeWindowError
from sertor_core.observability.logging import log_event

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchQuery:
    """Input of an episodic search: text + optional constraints (data-model.md).

    `text` is free text — each whitespace token is matched as a punctuation-safe literal, tokens
    implicitly AND-ed (`_to_fts_match`); empty/whitespace/no-token → explicit empty state (not an
    error). Raw FTS5 operators are NOT interpreted (memory search is not a boolean-query surface).
    `since`/`until` are epoch-UTC bounds on the parent session's `captured_at` (`None` = open).
    `since > until` → `InvalidTimeWindowError`. `limit`/`snippet_tokens` default to `Settings`
    (the caller passes the resolved values; the bare dataclass uses the same documented defaults).
    """

    text: str
    since: float | None = None
    until: float | None = None
    order: Literal["relevance", "recency"] = "relevance"
    limit: int = 20
    snippet_tokens: int = 12


@dataclass(frozen=True)
class EpisodicHit:
    """A matching turn enriched with its citation (data-model.md). Unit of return (FR-021).

    `source_path` is `None` today: FEAT-001 does not persist it in `sessions` (edge case "session
    without path"); the field stays in the contract, populatable later without changing it.
    `score` = `-bm25()` (higher = more relevant).
    """

    session_key: str
    captured_at: float
    role: str
    turn_index: int
    snippet: str
    score: float
    source_path: str | None = None


@dataclass(frozen=True)
class EpisodicResults:
    """Explicit outcome of a search (avoids an ambiguous `None`, Principio IV).

    `hits` empty = explicit empty state (no match / missing / empty / unindexable archive — all
    legitimate, NOT errors). `latency_ms` feeds observability (FR-017) and the latency test
    (SC-006).
    """

    hits: tuple[EpisodicHit, ...]
    latency_ms: float


# --- SQL fragments (schema is derived & idempotent; see data-model.md) ---------------------------

_CREATE_FTS = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts "
    "USING fts5(content, content='turns', content_rowid='rowid')"
)
_CREATE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS turns_ai AFTER INSERT ON turns BEGIN "
    "INSERT INTO turns_fts(rowid, content) VALUES (new.rowid, new.content); END",
    "CREATE TRIGGER IF NOT EXISTS turns_ad AFTER DELETE ON turns BEGIN "
    "INSERT INTO turns_fts(turns_fts, rowid, content) "
    "VALUES('delete', old.rowid, old.content); END",
    "CREATE TRIGGER IF NOT EXISTS turns_au AFTER UPDATE ON turns BEGIN "
    "INSERT INTO turns_fts(turns_fts, rowid, content) VALUES('delete', old.rowid, old.content); "
    "INSERT INTO turns_fts(rowid, content) VALUES (new.rowid, new.content); END",
)


def _to_fts_match(text: str) -> str:
    """Turn free user text into a SAFE FTS5 MATCH expression (pure, stdlib only).

    FTS5 parses the MATCH value as a *query expression*, so ordinary input — version numbers
    (`0.1.1`), paths (`a/b.py`), `tipo:esito` tags, hyphenated words — hits special syntax
    (`.`, `-`, `:`, `"`, `*`, parentheses) and raises `fts5: syntax error`, which the search then
    masks as "no results" (the opposite of Fail Loud). The cure: split on whitespace and wrap EACH
    token in a double-quoted FTS5 **string literal** (an inner `"` is escaped by doubling it), so
    punctuation is CONTENT, not operator. Tokens are space-joined = implicit AND (the prior
    behaviour for multi-word queries). Returns `''` when there are no tokens (caller → empty state).

    Trade-off: raw FTS5 operators (AND/OR/NEAR/prefix `*`) are no longer honoured — memory search is
    free text, not a boolean-query surface (the common case never types them). A `--raw` escape
    hatch is a possible follow-up, not needed for the bug.
    """
    return " ".join('"' + token.replace('"', '""') + '"' for token in text.split())


class EpisodicSearch:
    """Local FTS5 full-text search over `<index_dir>/memory.sqlite` (concrete, stdlib only)."""

    def __init__(self, index_dir: Path | str):
        # Stores the path only; opens no connection (lazy — same discipline as MemoryArchive).
        self._path = Path(index_dir) / "memory.sqlite"

    def _connect(self) -> sqlite3.Connection | None:
        """Open the archive read-write and ensure the FTS5 index (lazy, idempotent).

        Read-only on the *data* (never writes `sessions`/`turns`); the FTS table + triggers are a
        derived artefact. Returns `None` — never raises — for the non-fatal empty-state paths:
        the archive file does not exist (P-NOARCH), `sqlite3` lacks FTS5 (P-NOINDEX), or any other
        store failure. The caller treats `None` as an empty result + warning.
        """
        if not self._path.exists():
            log_event(logging.WARNING, "episodic_search_unavailable", reason="archive_absent")
            return None
        try:
            conn = sqlite3.connect(self._path)
            self._ensure_index(conn)
            return conn
        except sqlite3.OperationalError as exc:
            # Most likely: this sqlite3 build has no FTS5 (CREATE VIRTUAL TABLE ... fts5 fails).
            # Non-fatal: warn and degrade to empty state — never a second LIKE engine (research).
            log_event(
                logging.WARNING, "episodic_search_unavailable",
                reason="fts5_unavailable", detail=type(exc).__name__,
            )
            return None
        except sqlite3.Error as exc:
            log_event(
                logging.WARNING, "episodic_search_unavailable",
                reason=type(exc).__name__,
            )
            return None

    @staticmethod
    def _ensure_index(conn: sqlite3.Connection) -> None:
        """Create the FTS table + sync triggers (idempotent) and back-fill once if needed (I-ONCE).

        The table is created only if absent; in that case a one-shot `'rebuild'` populates the
        index from the turns already present (an archive predating this feature, or one written
        before the triggers existed). From then on the triggers keep it in sync (I-SYNC). Note: for
        an external-content table `count(*) FROM turns_fts` mirrors the content table, not the
        index, so it is NOT a reliable "is the index populated?" probe — we key the back-fill on
        whether we just created the table. May raise `sqlite3.OperationalError` if FTS5 is absent.
        """
        existed = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='turns_fts'"
        ).fetchone()
        conn.execute(_CREATE_FTS)
        for trigger in _CREATE_TRIGGERS:
            conn.execute(trigger)
        if existed is None:
            turns_count = conn.execute("SELECT count(*) FROM turns").fetchone()[0]
            if turns_count > 0:
                conn.execute("INSERT INTO turns_fts(turns_fts) VALUES('rebuild')")
        conn.commit()

    def search(self, query: SearchQuery) -> EpisodicResults:
        """Run a local, turn-grained full-text search (contract `sertor.episodic-search/1`).

        Empty/whitespace query → empty state (P-EMPTY). `since > until` → `InvalidTimeWindowError`
        (C-ERR). Missing / empty / unindexable archive → empty state + warning. Malformed rows are
        skipped with a warning (P-BADROW). Emits the `episodic_search` event (query hashed, never
        in clear) — non-fatal (P-OBSFAIL).
        """
        start = time.monotonic()

        if not query.text.strip():
            return EpisodicResults(hits=(), latency_ms=0.0)
        if query.since is not None and query.until is not None and query.since > query.until:
            raise InvalidTimeWindowError(query.since, query.until)

        hits = self._run_query(query)
        latency_ms = (time.monotonic() - start) * 1000.0
        results = EpisodicResults(hits=hits, latency_ms=latency_ms)
        self._emit_event(query, results)
        return results

    def _run_query(self, query: SearchQuery) -> tuple[EpisodicHit, ...]:
        """Execute the FTS query, returning the hits (empty tuple on any non-fatal degradation)."""
        conn = self._connect()
        if conn is None:
            return ()  # P-NOARCH / P-NOINDEX: explicit empty state, never an error.
        try:
            match = _to_fts_match(query.text)
            if not match:
                return ()  # no tokens (all punctuation/whitespace) → explicit empty state
            sql, params = self._build_sql(query, match)
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.Error as exc:
            log_event(logging.WARNING, "episodic_search_unavailable", reason=type(exc).__name__)
            return ()
        finally:
            conn.close()
        return self._rows_to_hits(rows)

    @staticmethod
    def _build_sql(query: SearchQuery, match: str) -> tuple[str, list[object]]:
        """Build the SQL + params: JOIN turns_fts ↔ turns ↔ sessions, optional time window, order.

        `match` is the sanitized FTS5 MATCH expression (`_to_fts_match`, punctuation-safe), NOT the
        raw user text. `snippet(turns_fts, 0, ...)` gives the contextual excerpt; `bm25(turns_fts)`
        the relevance (lower = more relevant → natural ASC). Time window filters on
        `sessions.captured_at`. Params are built in the exact `?` order of the final SQL:
        snippet_tokens, MATCH expression, then the optional since/until, then the limit.
        """
        params: list[object] = [query.snippet_tokens, match]
        window = ""
        if query.since is not None:
            window += " AND s.captured_at >= ?"
            params.append(query.since)
        if query.until is not None:
            window += " AND s.captured_at <= ?"
            params.append(query.until)
        if query.order == "recency":
            order_by = "s.captured_at DESC"
        else:
            order_by = "bm25(turns_fts), s.captured_at DESC"
        params.append(query.limit)
        sql = (
            "SELECT t.session_key, s.captured_at, t.role, t.turn_index, "
            "snippet(turns_fts, 0, '[', ']', '…', ?), bm25(turns_fts) "
            "FROM turns_fts "
            "JOIN turns t ON t.rowid = turns_fts.rowid "
            "JOIN sessions s ON s.session_key = t.session_key "
            f"WHERE turns_fts MATCH ?{window} "
            f"ORDER BY {order_by} LIMIT ?"
        )
        return sql, params

    @staticmethod
    def _rows_to_hits(rows: list[tuple[object, ...]]) -> tuple[EpisodicHit, ...]:
        """Map result rows to `EpisodicHit`, skipping malformed rows with a warning (P-BADROW)."""
        hits: list[EpisodicHit] = []
        for row in rows:
            try:
                session_key, captured_at, role, turn_index, snippet, bm25_score = row
                hits.append(
                    EpisodicHit(
                        session_key=str(session_key),
                        captured_at=float(captured_at),
                        role=str(role),
                        turn_index=int(turn_index),
                        snippet=str(snippet),
                        score=-float(bm25_score),  # higher = more relevant (research)
                        source_path=None,
                    )
                )
            except (TypeError, ValueError) as exc:
                log_event(
                    logging.WARNING, "episodic_search_bad_row", reason=type(exc).__name__,
                )
        return tuple(hits)

    @staticmethod
    def _emit_event(query: SearchQuery, results: EpisodicResults) -> None:
        """Emit the `episodic_search` event — query HASHED, never in clear (DA-FT-004).

        Non-fatal (P-OBSFAIL): a failure here must never break a search.
        """
        try:
            query_hash = hashlib.sha256(query.text.encode()).hexdigest()[:16]
            log_event(
                logging.INFO, "episodic_search",
                query_hash=query_hash,
                query_len=len(query.text),
                since=query.since,
                until=query.until,
                order=query.order,
                limit=query.limit,
                results=len(results.hits),
                latency_ms=round(results.latency_ms, 3),
            )
        except Exception as exc:  # noqa: BLE001 — observability must never break the search.
            _LOGGER.debug("episodic_search event emission failed: %s", exc)
