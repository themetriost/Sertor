"""US1 — `MemoryArchive` store: idempotence, conservation, non-fatal degradation (031).

Contract `memory.archive/1`. Offline with `tmp_path`; SC-001/002/006/007.
"""
from __future__ import annotations

import logging

from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.domain.memory import ArchivedSession, TranscriptTurn


def _session(key: str, project_id: str = "proj", *, retention_days: int | None = None,
             text: str = "hello") -> ArchivedSession:
    return ArchivedSession(
        session_key=key,
        project_id=project_id,
        captured_at=1000.0,
        adapter_kind="claude-code",
        turns=(
            TranscriptTurn(index=0, role="user", text=text, ts=1.0),
            TranscriptTurn(index=1, role="assistant", text=text + "!", ts=None),
        ),
        retention_days=retention_days,
    )


def test_n_distinct_sessions_n_records_no_duplicates(tmp_path):
    # SC-001: N distinct sessions → exactly N records, zero duplicates.
    archive = MemoryArchive(tmp_path)
    keys = [f"sess-{i}" for i in range(5)]
    for key in keys:
        assert archive.upsert(_session(key)) is True
    for key in keys:
        got = archive.get(key)
        assert got is not None
        assert got.session_key == key
        assert len(got.turns) == 2


def test_repeated_upsert_is_idempotent_returns_true_then_false(tmp_path):
    # SC-002: K upserts of the same session → 1 record, content unchanged; True once, then False.
    archive = MemoryArchive(tmp_path)
    first = archive.upsert(_session("sess", text="original"))
    assert first is True
    for _ in range(3):
        assert archive.upsert(_session("sess", text="OVERWRITTEN")) is False
    got = archive.get("sess")
    assert got is not None
    assert got.turns[0].text == "original"  # existing record never mutated (FR-014)


def test_distinct_project_ids_kept_separate(tmp_path):
    # US1 scenario 4 / FR-010: same archive, two project_ids → records not mixed.
    archive = MemoryArchive(tmp_path)
    archive.upsert(_session("a", project_id="projA"))
    archive.upsert(_session("b", project_id="projB"))
    assert archive.get("a").project_id == "projA"
    assert archive.get("b").project_id == "projB"


def test_earlier_sessions_never_deleted_by_later_archiving(tmp_path):
    # SC-006: archiving new sessions never removes the previously archived ones.
    archive = MemoryArchive(tmp_path)
    archive.upsert(_session("old"))
    archive.upsert(_session("new"))
    assert archive.exists("old") is True
    assert archive.exists("new") is True


def test_retention_days_recorded_but_no_deletion(tmp_path):
    # FR-022 (finding F3): retention_days is written to metadata and NO record is deleted.
    archive = MemoryArchive(tmp_path)
    archive.upsert(_session("with-retention", retention_days=30))
    archive.upsert(_session("other", retention_days=30))
    got = archive.get("with-retention")
    assert got is not None
    assert got.retention_days == 30          # value persisted in metadata (hook only)
    # No enforcement here: both records still present after a second session is archived.
    assert archive.exists("with-retention") is True
    assert archive.exists("other") is True


def test_corrupt_store_is_non_fatal(tmp_path, caplog):
    # SC-007: a corrupt DB file → upsert/get/exists do not raise; a warning is emitted.
    db = tmp_path / "memory.sqlite"
    db.write_bytes(b"not a database")
    archive = MemoryArchive(tmp_path)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        assert archive.upsert(_session("x")) is False
        assert archive.get("x") is None
        assert archive.exists("x") is False
    assert any("memory_archive_unavailable" in r.getMessage() for r in caplog.records)


def test_get_missing_session_returns_none(tmp_path):
    archive = MemoryArchive(tmp_path)
    assert archive.get("absent") is None
    assert archive.exists("absent") is False


def test_no_file_created_until_first_use(tmp_path):
    # Lazy: constructing the store opens/creates nothing (flag-off safe at the store level).
    MemoryArchive(tmp_path)
    assert not (tmp_path / "memory.sqlite").exists()
