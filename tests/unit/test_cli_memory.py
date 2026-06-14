"""Test US1/US2 — CLI `sertor-rag memory archive` / `memory search` (035, FR-002..016, SC-001..007).

Offline: the core is mocked by monkeypatching the composition factories
`build_memory_archiver`/`build_episodic_search` (no network, no disk). Same style as
`tests/unit/test_cli_search.py`.

`ArchiveRunReport` is re-exported by `sertor_core.__init__`; `SearchQuery`/`EpisodicHit`/
`EpisodicResults` are NOT, so they are imported from `sertor_core.services.episodic_search`
(F2 analyze).

Host-agnosticity (SC-008): the commands carry no host branch — they are thin consumers of the
host-agnostic factories. It is covered STRUCTURALLY (no host-specific code path in the commands),
so no dedicated multi-host test is needed; the host specificity lives only in the SessionEnd hook
(verified manually, quickstart §3). (F7 analyze.)
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import InvalidTimeWindowError
from sertor_core.services.episodic_search import EpisodicHit, EpisodicResults, SearchQuery
from sertor_core.services.memory_archive import ArchiveRunReport


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    """Isolate from the repo `.env` (load_dotenv override would mutate os.environ persistently)."""
    _orig = Settings.load.__func__
    monkeypatch.setattr(
        Settings, "load", classmethod(lambda c, env_file=".env": _orig(c, env_file=None))
    )


def _run(argv):
    return cli.main(argv)


def _hit(**kw):
    base = dict(
        session_key="sess-abc",
        captured_at=1718360463.0,
        role="user",
        turn_index=12,
        snippet="…combina BM25 e dense con [hybrid search] e RRF…",
        score=0.873,
    )
    base.update(kw)
    return EpisodicHit(**base)


# =========================================================================== US1: memory archive


class _FakeArchiver:
    """Fake `MemoryArchiveService`: returns a fixed report; records that archive_all was called."""

    def __init__(self, report: ArchiveRunReport):
        self._report = report
        self.calls = 0

    def archive_all(self) -> ArchiveRunReport:
        self.calls += 1
        return self._report


def test_memory_archive_human_output(monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "build_memory_archiver",
        lambda s: _FakeArchiver(ArchiveRunReport(archived=2, skipped=1, errors=0)),
    )
    code = _run(["memory", "archive"])
    out = capsys.readouterr().out
    assert code == 0
    assert "archived=2" in out
    assert "skipped=1" in out
    assert "errors=0" in out


def test_memory_archive_json_output(monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "build_memory_archiver",
        lambda s: _FakeArchiver(ArchiveRunReport(archived=2, skipped=1, errors=0)),
    )
    code = _run(["memory", "archive", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert json.loads(out) == {"archived": 2, "skipped": 1, "errors": 0}


def test_memory_archive_idempotent(monkeypatch, capsys):
    # A re-run on already-archived sessions reports archived=0 (all skipped): no duplicates.
    monkeypatch.setattr(
        cli, "build_memory_archiver",
        lambda s: _FakeArchiver(ArchiveRunReport(archived=0, skipped=2, errors=0)),
    )
    code = _run(["memory", "archive"])
    out = capsys.readouterr().out
    assert code == 0
    assert "archived=0" in out
    assert "skipped=2" in out


def test_memory_archive_gate_off_exit1(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_memory_archiver", lambda s: None)
    code = _run(["memory", "archive"])
    err = capsys.readouterr().err
    assert code == 1
    assert "error:" in err
    assert "SERTOR_MEMORY" in err


# =========================================================================== US2: memory search


class _FakeSearch:
    """Fake `EpisodicSearch`: returns a fixed result; records the `SearchQuery` it received.

    Read-only (FR-008): exposes only `search()`; no write method — a write call would AttributeError
    (test_memory_search_readonly asserts the contract).
    """

    def __init__(self, results: EpisodicResults | None = None, raises: Exception | None = None):
        self._results = results if results is not None else EpisodicResults(hits=(), latency_ms=0.0)
        self._raises = raises
        self.received: SearchQuery | None = None

    def search(self, query: SearchQuery) -> EpisodicResults:
        self.received = query
        if self._raises is not None:
            raise self._raises
        return self._results


def test_memory_search_human_output(monkeypatch, capsys):
    fake = _FakeSearch(EpisodicResults(hits=(_hit(),), latency_ms=1.2))
    monkeypatch.setattr(cli, "build_episodic_search", lambda s: fake)
    code = _run(["memory", "search", "hybrid"])
    out = capsys.readouterr().out
    assert code == 0
    for token in ("score=", "role=", "session=", "turn=", "@="):
        assert token in out


def test_memory_search_json_fields(monkeypatch, capsys):
    fake = _FakeSearch(EpisodicResults(hits=(_hit(),), latency_ms=1.2))
    monkeypatch.setattr(cli, "build_episodic_search", lambda s: fake)
    code = _run(["memory", "search", "hybrid", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    arr = json.loads(out)
    assert isinstance(arr, list) and arr
    expected = {"session_key", "captured_at", "role", "turn_index", "snippet", "score"}
    for hit in arr:
        assert expected <= hit.keys()


def test_memory_search_k_limits(monkeypatch, capsys):
    fake = _FakeSearch(EpisodicResults(hits=tuple(_hit() for _ in range(5)), latency_ms=1.0))
    monkeypatch.setattr(cli, "build_episodic_search", lambda s: fake)
    code = _run(["memory", "search", "retrieval", "-k", "2"])
    capsys.readouterr()
    assert code == 0
    assert fake.received is not None
    assert fake.received.limit == 2


def test_memory_search_empty_results(monkeypatch, capsys):
    fake = _FakeSearch(EpisodicResults(hits=(), latency_ms=0.0))
    monkeypatch.setattr(cli, "build_episodic_search", lambda s: fake)
    code = _run(["memory", "search", "nothing-here"])
    out = capsys.readouterr().out
    assert code == 0
    assert "(no results)" in out


def test_memory_search_gate_off_exit1(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_episodic_search", lambda s: None)
    code = _run(["memory", "search", "x"])
    err = capsys.readouterr().err
    assert code == 1
    assert "error:" in err
    assert "SERTOR_MEMORY" in err


def test_memory_search_invalid_window_exit1(monkeypatch, capsys):
    # The core validates the window; the command just lets InvalidTimeWindowError propagate (F6).
    fake = _FakeSearch(raises=InvalidTimeWindowError(2.0, 1.0))
    monkeypatch.setattr(cli, "build_episodic_search", lambda s: fake)
    code = _run(["memory", "search", "x", "--since", "2026-06-14", "--until", "2026-06-10"])
    err = capsys.readouterr().err
    assert code == 1
    assert "error:" in err


# =========================================================================== Polish / edge cases


def test_memory_archive_json_gate_off(monkeypatch, capsys):
    # Structured output requested but memory off: error on stderr, exit 1 (no half JSON on stdout).
    monkeypatch.setattr(cli, "build_memory_archiver", lambda s: None)
    code = _run(["memory", "archive", "--json"])
    captured = capsys.readouterr()
    assert code == 1
    assert "SERTOR_MEMORY" in captured.err
    assert captured.out.strip() == ""


def test_memory_search_readonly(monkeypatch, capsys):
    # The fake exposes only search(): the command never calls a write method (FR-008).
    fake = _FakeSearch(EpisodicResults(hits=(_hit(),), latency_ms=1.0))
    monkeypatch.setattr(cli, "build_episodic_search", lambda s: fake)
    code = _run(["memory", "search", "x"])
    capsys.readouterr()
    assert code == 0
    # archive is untouched: the only interaction recorded is the read query.
    assert fake.received is not None
    assert not hasattr(fake, "written")
