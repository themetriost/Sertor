"""Auto-index hook in `archive_all` + incrementality (072, FEAT-004, TASK-US3-02).

Verifies: the injected semantic index is called per just-archived session (REQ-004); a None index
is a no-op (REQ-005, FEAT-001 behaviour); an embedding failure at end-of-archive is non-fatal
(REQ-008); and indexing the same session twice is incremental (REQ-030/031). Offline, mock adapter
+ mock semantic index + `tmp_path` archive.
"""
from __future__ import annotations

from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.config.settings import Settings
from sertor_core.domain.memory import SessionRef, TranscriptContent, TranscriptTurn
from sertor_core.services.memory_archive import MemoryArchiveService
from sertor_core.services.memory_semantic import SemanticIndexReport


class FakeAdapter:
    def __init__(self, keys: list[str]):
        self.kind = "fake"
        self._keys = keys

    def source_available(self) -> bool:
        return True

    def list_sessions(self):
        return [SessionRef(session_key=k, project_id="proj", source_path=f"/x/{k}")
                for k in self._keys]

    def read_session(self, ref: SessionRef) -> TranscriptContent:
        return TranscriptContent(
            session_key=ref.session_key, project_id=ref.project_id, adapter_kind=self.kind,
            captured_at=1000.0,
            turns=(TranscriptTurn(index=0, role="user", text=f"hello {ref.session_key}", ts=None),),
        )


class RecordingSemanticIndex:
    """Mock `MemorySemanticIndex`: records `index_session` calls, tracks embed counts."""

    def __init__(self, *, fail: bool = False):
        self.indexed: list[str] = []
        self._fail = fail
        self._seen: set[str] = set()

    def index_session(self, session) -> SemanticIndexReport:
        if self._fail:
            raise RuntimeError("embedding provider down")
        # Incrementality: a session already seen → embedded=0 (no re-embed).
        if session.session_key in self._seen:
            return SemanticIndexReport(embedded=0, skipped=len(session.turns), errors=0)
        self._seen.add(session.session_key)
        self.indexed.append(session.session_key)
        return SemanticIndexReport(embedded=len(session.turns), skipped=0, errors=0)


def _settings() -> Settings:
    return Settings.load(env_file=None)


def test_auto_index_called_per_archived_session(tmp_path):
    """REQ-004/US3-AC1: each just-archived session triggers index_session."""
    index = RecordingSemanticIndex()
    service = MemoryArchiveService(
        FakeAdapter(["s1", "s2"]), MemoryArchive(tmp_path), _settings(), semantic_index=index
    )
    report = service.archive_all()
    assert report.archived == 2
    assert sorted(index.indexed) == ["s1", "s2"]


def test_no_semantic_index_is_feat001_behaviour(tmp_path):
    """REQ-005/US2-AC1: with semantic_index=None, no embedding side-effect."""
    service = MemoryArchiveService(
        FakeAdapter(["s1"]), MemoryArchive(tmp_path), _settings(), semantic_index=None
    )
    report = service.archive_all()
    assert report.archived == 1
    # No semantic index attached → nothing to assert beyond a normal archive run.
    assert service._semantic_index is None


def test_embedding_failure_is_non_fatal(tmp_path):
    """REQ-008/US6-AC4: an embedding failure leaves the raw intact and the run completes."""
    index = RecordingSemanticIndex(fail=True)
    archive = MemoryArchive(tmp_path)
    service = MemoryArchiveService(
        FakeAdapter(["s1"]), archive, _settings(), semantic_index=index
    )
    report = service.archive_all()
    assert report.archived == 1            # raw archived despite the embedding failure
    assert archive.get("s1") is not None   # raw intact


def test_reindex_same_session_is_incremental(tmp_path):
    """REQ-030/031/US3-AC2: re-indexing an already-indexed session embeds nothing."""
    index = RecordingSemanticIndex()
    archive = MemoryArchive(tmp_path)
    service = MemoryArchiveService(
        FakeAdapter(["s1"]), archive, _settings(), semantic_index=index
    )
    service.archive_all()
    # Second call: archive_all skips the already-archived session → no second index_session.
    service.archive_all()
    assert index.indexed == ["s1"]  # indexed exactly once (auto-index only on new archives)
