"""US2 — `MemoryArchive.list_recent`: recency order, limit, turn_count, non-fatal (036, FR-002/004).

Contract `sertor.memory-reader/1` (R-LIST-*). Offline with `tmp_path` over a real SQLite archive
(no mock): the read path is exercised against the actual store written by `upsert`.
"""
from __future__ import annotations

import json
import logging
import sqlite3

from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.domain.memory import ArchivedSession, TranscriptTurn


def _session(key: str, captured_at: float, *, n_turns: int = 2) -> ArchivedSession:
    return ArchivedSession(
        session_key=key,
        project_id="proj",
        captured_at=captured_at,
        adapter_kind="claude-code",
        turns=tuple(
            TranscriptTurn(index=i, role="user", text=f"turn {i}", ts=None)
            for i in range(n_turns)
        ),
    )


def test_list_recent_is_recency_first(tmp_path):
    # R-LIST-ORDER: most recent captured_at first.
    archive = MemoryArchive(tmp_path)
    archive.upsert(_session("old", 1000.0))
    archive.upsert(_session("mid", 2000.0))
    archive.upsert(_session("new", 3000.0))
    summaries = archive.list_recent(10)
    assert [s.session_key for s in summaries] == ["new", "mid", "old"]


def test_list_recent_respects_limit(tmp_path):
    archive = MemoryArchive(tmp_path)
    for i in range(5):
        archive.upsert(_session(f"sess-{i}", float(i)))
    summaries = archive.list_recent(2)
    assert len(summaries) == 2
    # the two most recent (highest captured_at)
    assert [s.session_key for s in summaries] == ["sess-4", "sess-3"]


def test_list_recent_turn_count_from_metadata(tmp_path):
    # R-LIST-COUNT: turn_count matches the archived turns (read from metadata).
    archive = MemoryArchive(tmp_path)
    archive.upsert(_session("a", 1000.0, n_turns=3))
    archive.upsert(_session("b", 2000.0, n_turns=0))
    by_key = {s.session_key: s.turn_count for s in archive.list_recent(10)}
    assert by_key["a"] == 3
    assert by_key["b"] == 0


def test_list_recent_fallback_count_when_metadata_missing(tmp_path):
    # Defensive fallback: a row whose metadata lacks turn_count → COUNT(*) on turns.
    archive = MemoryArchive(tmp_path)
    archive.upsert(_session("a", 1000.0, n_turns=4))
    # Tamper with metadata to drop the turn_count field (simulate an older/odd record).
    conn = sqlite3.connect(tmp_path / "memory.sqlite")
    conn.execute(
        "UPDATE sessions SET metadata = ? WHERE session_key = ?",
        (json.dumps({"retention_days": None}), "a"),
    )
    conn.commit()
    conn.close()
    fresh = MemoryArchive(tmp_path)
    summaries = fresh.list_recent(10)
    assert summaries[0].turn_count == 4  # recovered via COUNT(*)


def test_list_recent_absent_archive_returns_empty(tmp_path):
    # R-LIST-EMPTY: no rows yet → empty tuple, no exception (schema is created lazily, like `get`).
    archive = MemoryArchive(tmp_path)
    assert archive.list_recent(10) == ()


def test_list_recent_empty_archive_returns_empty(tmp_path):
    archive = MemoryArchive(tmp_path)
    archive.exists("x")  # forces schema creation, no rows
    assert archive.list_recent(10) == ()


def test_list_recent_store_ko_is_non_fatal(tmp_path, caplog):
    # R-LIST-STOREKO: corrupt DB → () + warning, never crash.
    db = tmp_path / "memory.sqlite"
    db.write_bytes(b"not a database")
    archive = MemoryArchive(tmp_path)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        assert archive.list_recent(10) == ()
    assert any("memory_archive_unavailable" in r.getMessage() for r in caplog.records)


def test_list_recent_non_positive_limit_returns_empty(tmp_path):
    # F5 guard: limit <= 0 → () (Python guard, not LIMIT 0).
    archive = MemoryArchive(tmp_path)
    archive.upsert(_session("a", 1000.0))
    assert archive.list_recent(0) == ()
    assert archive.list_recent(-3) == ()


def test_list_recent_is_read_only(tmp_path):
    # R-READONLY: list_recent does not mutate sessions/turns.
    archive = MemoryArchive(tmp_path)
    archive.upsert(_session("a", 1000.0, n_turns=2))
    before = archive.get("a")
    archive.list_recent(10)
    after = archive.get("a")
    assert before == after
