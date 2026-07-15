"""US1/US3 — `MemoryArchiveService` orchestration (031, contract `memory.archive-service/1`).

Offline with mock adapters (structural typing, no inheritance) + `tmp_path` store. Covers
idempotence, observable skip, empty sessions, store failure, host-agnosticity (>=2 adapters).
"""
from __future__ import annotations

import logging

from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.config.settings import Settings
from sertor_core.domain.memory import SessionRef, TranscriptContent, TranscriptTurn
from sertor_core.services.memory_archive import ArchiveRunReport, MemoryArchiveService


class FakeAdapter:
    """Structural `TranscriptCaptureAdapter`: serves a fixed map of session_key → turns."""

    def __init__(self, sessions: dict[str, list[TranscriptTurn]], *, kind: str = "fake",
                 project_id: str = "proj", source_available: bool = True):
        self.kind = kind
        self._sessions = sessions
        self._project_id = project_id
        self._source_available = source_available

    def source_available(self) -> bool:
        return self._source_available

    def list_sessions(self) -> list[SessionRef]:
        return [
            SessionRef(session_key=key, project_id=self._project_id, source_path=f"/x/{key}")
            for key in self._sessions
        ]

    def read_session(self, ref: SessionRef) -> TranscriptContent:
        return TranscriptContent(
            session_key=ref.session_key,
            project_id=ref.project_id,
            adapter_kind=self.kind,
            captured_at=1000.0,
            turns=tuple(self._sessions[ref.session_key]),
        )


def _turn(text: str, index: int = 0, role: str = "user") -> TranscriptTurn:
    return TranscriptTurn(index=index, role=role, text=text, ts=None)


def _settings() -> Settings:
    return Settings.load(env_file=None)


def test_three_sessions_then_idempotent_rerun(tmp_path):
    # SC-001/002: first run archives 3; second run skips 3, archive unchanged.
    adapter = FakeAdapter({f"s{i}": [_turn(f"text {i}")] for i in range(3)})
    archive = MemoryArchive(tmp_path)
    service = MemoryArchiveService(adapter, archive, _settings())

    first = service.archive_all()
    assert (first.archived, first.skipped) == (3, 0)

    second = service.archive_all()
    assert (second.archived, second.skipped) == (0, 3)
    # Archive content unchanged after the rerun (SC-006).
    assert archive.get("s0").turns[0].text == "text 0"


def test_observable_skip_emits_event(tmp_path, caplog):
    adapter = FakeAdapter({"s": [_turn("hi")]})
    archive = MemoryArchive(tmp_path)
    service = MemoryArchiveService(adapter, archive, _settings())
    service.archive_all()  # archive once
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        report = service.archive_all()
    assert report.skipped == 1
    assert any("memory_session_skipped" in r.getMessage() for r in caplog.records)


def test_empty_turns_session_is_skipped(tmp_path):
    # A session with no turns is skipped: no empty record is created (D3 rule 5).
    adapter = FakeAdapter({"empty": []})
    archive = MemoryArchive(tmp_path)
    report = MemoryArchiveService(adapter, archive, _settings()).archive_all()
    assert (report.archived, report.skipped) == (0, 1)
    assert archive.get("empty") is None


class _BrokenArchive:
    """Archive whose `upsert` always fails (simulates a guasto store, F7)."""

    def __init__(self):
        self.events: list[str] = []

    def exists(self, session_key: str) -> bool:
        return False

    def upsert(self, session) -> bool:  # noqa: ANN001 - structural stub
        self.events.append(session.session_key)
        return False  # store failure → no new record (FR-025)


def test_store_failure_does_not_increment_archived_and_continues(tmp_path, caplog):
    # F7 + SC-007: upsert returns False (guasto) → service does not count `archived`, no `archived`
    # event; the run proceeds across refs (no exception).
    adapter = FakeAdapter({"a": [_turn("x")], "b": [_turn("y")]})
    archive = _BrokenArchive()
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        report = MemoryArchiveService(adapter, archive, _settings()).archive_all()
    assert report.archived == 0
    assert report.skipped == 2  # both refs attempted, both not new
    assert archive.events == ["a", "b"]  # the run did not stop at the first failure
    assert not any("memory_session_archived" in r.getMessage() for r in caplog.records)


def test_two_distinct_adapters_same_behaviour(tmp_path):
    # SC-005 / FR-005: two adapters with different `kind` → identical orchestration, no host branch.
    adapter_a = FakeAdapter({"a1": [_turn("alpha")]}, kind="adapter-a")
    adapter_b = FakeAdapter({"b1": [_turn("beta")]}, kind="adapter-b")

    archive_a = MemoryArchive(tmp_path / "a")
    archive_b = MemoryArchive(tmp_path / "b")
    report_a = MemoryArchiveService(adapter_a, archive_a, _settings()).archive_all()
    report_b = MemoryArchiveService(adapter_b, archive_b, _settings()).archive_all()

    assert report_a == ArchiveRunReport(archived=1, skipped=0, errors=0)
    assert report_b == ArchiveRunReport(archived=1, skipped=0, errors=0)
    # adapter_kind flows through from each adapter (host-agnostic, not hardcoded).
    assert archive_a.get("a1").adapter_kind == "adapter-a"
    assert archive_b.get("b1").adapter_kind == "adapter-b"


def test_source_absent_sets_report_flag_and_archives_zero(tmp_path):
    # E4-FEAT-011: memory ON but the adapter source is absent → source_absent flag True + archives 0
    # (host-agnostic: the port reports it, the service never checks the adapter identity).
    adapter = FakeAdapter({}, source_available=False)
    report = MemoryArchiveService(adapter, MemoryArchive(tmp_path), _settings()).archive_all()
    assert report.source_absent is True
    assert report.archived == 0


def test_source_present_leaves_flag_false(tmp_path):
    # Present source (default) → source_absent stays False, unchanged behaviour.
    adapter = FakeAdapter({"s": [_turn("hi")]})
    report = MemoryArchiveService(adapter, MemoryArchive(tmp_path), _settings()).archive_all()
    assert report.source_absent is False


def test_archived_event_carries_size_not_raw_content(tmp_path, caplog):
    # FR-023/027: the archived event reports content_size/turn_count, never the raw text.
    secret_text = "token sk-abcdefgh12345678"
    adapter = FakeAdapter({"s": [_turn(secret_text)]})
    archive = MemoryArchive(tmp_path)
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        MemoryArchiveService(adapter, archive, _settings()).archive_all()
    archived = [r for r in caplog.records if "memory_session_archived" in r.getMessage()]
    assert archived
    msg = archived[0].getMessage()
    assert "content_size=" in msg and "turn_count=" in msg
    assert "sk-abcdefgh12345678" not in msg  # raw secret never in the event
