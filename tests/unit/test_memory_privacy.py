"""US2 — privacy by default + scrubbed content (031, SC-003/004, FR-017/027).

(a) `SERTOR_MEMORY=false` → no archiver, no file. (b) synthetic secrets never land in clear in
the archive. Offline, mock adapter + `tmp_path`.
"""
from __future__ import annotations

from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.composition import build_memory_archiver
from sertor_core.config.settings import Settings
from sertor_core.domain.memory import SessionRef, TranscriptContent, TranscriptTurn
from sertor_core.services.memory_archive import MemoryArchiveService


class FakeAdapter:
    def __init__(self, text: str):
        self.kind = "fake"
        self._text = text

    def list_sessions(self) -> list[SessionRef]:
        return [SessionRef(session_key="s", project_id="proj", source_path="/x/s")]

    def read_session(self, ref: SessionRef) -> TranscriptContent:
        return TranscriptContent(
            session_key=ref.session_key, project_id=ref.project_id, adapter_kind=self.kind,
            captured_at=1.0,
            turns=(TranscriptTurn(index=0, role="user", text=self._text, ts=None),),
        )


def test_disabled_memory_yields_no_archiver_and_no_file(monkeypatch, tmp_path):
    # SC-003: with memory off, build_memory_archiver returns None and no memory.sqlite is created.
    monkeypatch.delenv("SERTOR_MEMORY", raising=False)
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    assert settings.memory_enabled is False
    assert build_memory_archiver(settings) is None
    assert not (tmp_path / "memory.sqlite").exists()


def test_secrets_scrubbed_in_stored_content(tmp_path):
    # SC-004/FR-017: a turn with synthetic secrets → no clear occurrence in the stored content.
    adapter = FakeAdapter("my key is sk-supersecret12345 and PASSWORD=hunter2")
    archive = MemoryArchive(tmp_path)
    settings = Settings.load(env_file=None)
    MemoryArchiveService(adapter, archive, settings).archive_all()

    stored = archive.get("s")
    assert stored is not None
    content = stored.turns[0].text
    assert "sk-supersecret12345" not in content
    assert "hunter2" not in content
    assert "[REDACTED]" in content


def test_extra_scrub_patterns_from_settings_applied(tmp_path):
    adapter = FakeAdapter("token GH_PAT_zzz999 here")
    archive = MemoryArchive(tmp_path)
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "memory_scrub_patterns", ("GH_PAT_[A-Za-z0-9]+",))
    MemoryArchiveService(adapter, archive, settings).archive_all()
    assert "GH_PAT_zzz999" not in archive.get("s").turns[0].text
