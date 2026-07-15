"""Polish — end-to-end offline archiving (031): all Success Criteria via the composition root.

No network, no real Claude Code: a synthetic Claude Code projects directory under `tmp_path` drives
`build_memory_archiver(settings).archive_all()`. SC-001..SC-007 mapped to the quickstart.
"""
from __future__ import annotations

import json
import logging

from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.composition import build_memory_archiver
from sertor_core.config.settings import Settings
from sertor_core.domain.memory import SessionRef, TranscriptContent, TranscriptTurn
from sertor_core.services.memory_archive import MemoryArchiveService


def _enabled_settings(monkeypatch, tmp_path, projects_dir):
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.setenv("SERTOR_MEMORY_CLAUDE_PROJECTS_DIR", str(projects_dir))
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    return settings


def _project_dir(monkeypatch, projects_root):
    """Create the encoded project folder for the current cwd under a synthetic projects root."""
    from pathlib import Path

    from sertor_core.adapters.capture.claude_code import encode_project_path

    encoded = encode_project_path(str(Path.cwd()))
    project_dir = projects_root / encoded
    project_dir.mkdir(parents=True)
    return project_dir


def _session_line(content, role="user", ts=None):
    event = {"type": role, "message": {"role": role, "content": content}}
    if ts is not None:
        event["timestamp"] = ts
    return json.dumps(event)


def test_e2e_archive_n_records_and_idempotent(monkeypatch, tmp_path):
    projects_root = tmp_path / "projects"
    project_dir = _project_dir(monkeypatch, projects_root)
    for i in range(3):
        (project_dir / f"s{i}.jsonl").write_text(
            _session_line(f"message {i}"), encoding="utf-8")

    settings = _enabled_settings(monkeypatch, tmp_path, projects_root)
    archiver = build_memory_archiver(settings)
    assert archiver is not None

    first = archiver.archive_all()
    assert (first.archived, first.skipped) == (3, 0)   # SC-001

    second = build_memory_archiver(settings).archive_all()
    assert (second.archived, second.skipped) == (0, 3)  # SC-002

    archive = MemoryArchive(tmp_path)
    assert archive.get("s0").turns[0].text == "message 0"  # SC-006 (unchanged)


def test_e2e_disabled_creates_no_file(monkeypatch, tmp_path):
    # SC-003: with memory off, no archiver and no memory.sqlite, even if a source exists.
    monkeypatch.delenv("SERTOR_MEMORY", raising=False)
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    assert build_memory_archiver(settings) is None
    assert not (tmp_path / "memory.sqlite").exists()


def test_e2e_secrets_scrubbed(monkeypatch, tmp_path):
    # SC-004: synthetic secrets in a real JSONL turn → 0 clear occurrences in the archive.
    projects_root = tmp_path / "projects"
    project_dir = _project_dir(monkeypatch, projects_root)
    (project_dir / "sec.jsonl").write_text(
        _session_line("here is sk-leakedsecret999 and PASSWORD=topsecret"), encoding="utf-8")

    settings = _enabled_settings(monkeypatch, tmp_path, projects_root)
    build_memory_archiver(settings).archive_all()

    content = MemoryArchive(tmp_path).get("sec").turns[0].text
    assert "sk-leakedsecret999" not in content
    assert "topsecret" not in content


class _MockAdapter:
    def __init__(self, kind):
        self.kind = kind

    def source_available(self):
        return True

    def list_sessions(self):
        return [SessionRef(session_key=f"{self.kind}-1", project_id="p", source_path="/x")]

    def read_session(self, ref):
        return TranscriptContent(
            session_key=ref.session_key, project_id=ref.project_id, adapter_kind=self.kind,
            captured_at=1.0, turns=(TranscriptTurn(0, "user", "hi", None),))


def test_e2e_two_adapters_same_logic(tmp_path):
    # SC-005: two adapters with different kind → identical service behaviour, no host branch.
    settings = Settings.load(env_file=None)
    for kind in ("adapter-x", "adapter-y"):
        archive = MemoryArchive(tmp_path / kind)
        report = MemoryArchiveService(_MockAdapter(kind), archive, settings).archive_all()
        assert (report.archived, report.skipped) == (1, 0)
        assert archive.get(f"{kind}-1").adapter_kind == kind


def test_e2e_corrupt_store_non_fatal(monkeypatch, tmp_path, caplog):
    # SC-007: a corrupt store file → archive_all does not raise, warning emitted.
    projects_root = tmp_path / "projects"
    project_dir = _project_dir(monkeypatch, projects_root)
    (project_dir / "s.jsonl").write_text(_session_line("hello"), encoding="utf-8")
    (tmp_path / "memory.sqlite").write_bytes(b"not a database")

    settings = _enabled_settings(monkeypatch, tmp_path, projects_root)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        report = build_memory_archiver(settings).archive_all()  # must not raise
    assert report.archived == 0
    assert any("memory_archive_unavailable" in r.getMessage() for r in caplog.records)
