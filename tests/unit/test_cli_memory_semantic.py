"""CLI `memory search --semantic` + `memory index-semantic` (072, FEAT-004).

Covers TASK-US1-04 (routing/gate/render), TASK-US4-01 (full-text default invariata), TASK-US4-02
(no-fallback + actionable message), TASK-US6-03 (backfill + idempotence). Offline: the core is
mocked by monkeypatching the composition factories imported into the CLI module (no network/disk),
same style as `test_cli_memory.py`.
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.cli import output
from sertor_core.config.settings import Settings
from sertor_core.services.episodic_search import EpisodicResults
from sertor_core.services.memory_semantic import (
    SemanticIndexReport,
    SemanticMemoryHit,
    SemanticMemoryQuery,
    SemanticMemoryResults,
)


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    _orig = Settings.load.__func__
    monkeypatch.setattr(
        Settings, "load", classmethod(lambda c, env_file=".env": _orig(c, env_file=None))
    )


def _run(argv):
    return cli.main(argv)


def _hit(**kw):
    base = dict(
        session_key="sess-abc", turn_index=7, captured_at=1718360463.0,
        role="assistant", snippet="…RRF fonde i due ranking…", score=0.91,
    )
    base.update(kw)
    return SemanticMemoryHit(**base)


class _FakeSemanticIndex:
    """Fake `MemorySemanticIndex`: records the query/backfill it received; returns fixed results."""

    def __init__(self, search_results=None, index_report=None):
        self._search = search_results or SemanticMemoryResults(hits=(), latency_ms=0.0)
        self._report = index_report or SemanticIndexReport()
        self.searched: SemanticMemoryQuery | None = None
        self.indexed = 0

    def search(self, query: SemanticMemoryQuery) -> SemanticMemoryResults:
        self.searched = query
        return self._search

    def index_all(self, archive) -> SemanticIndexReport:
        self.indexed += 1
        return self._report


# --- US1: semantic search routing/render --------------------------------------------------------


def test_search_without_semantic_uses_fulltext(monkeypatch, capsys):
    """SC-004/US4-AC1: no --semantic → full-text path; semantic index never built."""
    class _FTS:
        def __init__(self):
            self.calls = 0

        def search(self, q):
            self.calls += 1
            return EpisodicResults(hits=(), latency_ms=0.0)

    fts = _FTS()
    monkeypatch.setattr(cli, "build_episodic_search", lambda s: fts)
    sentinel = {"built": False}
    monkeypatch.setattr(
        cli, "build_memory_semantic_index",
        lambda s, **kw: sentinel.__setitem__("built", True) or None,
    )
    code = _run(["memory", "search", "query"])
    capsys.readouterr()
    assert code == 0
    assert fts.calls == 1
    assert sentinel["built"] is False  # semantic factory never invoked


def test_search_semantic_human_and_json(monkeypatch, capsys):
    """REQ-010/US1-AC2/AC3: --semantic renders snippet+score (human) and 6 fields (JSON)."""
    fake = _FakeSemanticIndex(SemanticMemoryResults(hits=(_hit(),), latency_ms=1.0))
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: fake)
    code = _run(["memory", "search", "query", "--semantic"])
    out = capsys.readouterr().out
    assert code == 0
    assert "score=" in out and "session=" in out

    code = _run(["memory", "search", "query", "--semantic", "--json"])
    arr = json.loads(capsys.readouterr().out)
    assert isinstance(arr, list) and arr
    expected = {"session_key", "turn_index", "captured_at", "role", "snippet", "score"}
    assert expected <= arr[0].keys()


def test_search_semantic_time_window_passed(monkeypatch, capsys):
    """REQ-012/US1-AC1: --since/--until reach the SemanticMemoryQuery."""
    fake = _FakeSemanticIndex(SemanticMemoryResults(hits=(), latency_ms=0.0))
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: fake)
    code = _run(["memory", "search", "q", "--semantic",
                 "--since", "2026-06-01", "--until", "2026-06-30"])
    capsys.readouterr()
    assert code == 0
    assert fake.searched is not None
    assert fake.searched.since is not None and fake.searched.until is not None
    assert fake.searched.since < fake.searched.until


def test_search_semantic_empty_results_exit0(monkeypatch, capsys):
    """REQ-021: hits=() → exit 0 with honest empty state."""
    fake = _FakeSemanticIndex(SemanticMemoryResults(hits=(), latency_ms=0.0))
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: fake)
    code = _run(["memory", "search", "nothing", "--semantic"])
    out = capsys.readouterr().out
    assert code == 0
    assert "(no results)" in out


def test_search_semantic_k_limit(monkeypatch, capsys):
    fake = _FakeSemanticIndex(SemanticMemoryResults(hits=(), latency_ms=0.0))
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: fake)
    code = _run(["memory", "search", "q", "--semantic", "-k", "3"])
    capsys.readouterr()
    assert code == 0
    assert fake.searched.limit == 3


# --- US4: gate / no fallback --------------------------------------------------------------------


def test_search_semantic_gate_off_semantic(monkeypatch, capsys):
    """REQ-015/US4-AC3: --semantic with SERTOR_MEMORY on but SERTOR_MEMORY_SEMANTIC off → exit 1."""
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.delenv("SERTOR_MEMORY_SEMANTIC", raising=False)
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: None)
    code = _run(["memory", "search", "q", "--semantic"])
    err = capsys.readouterr().err
    assert code == 1
    assert "SERTOR_MEMORY_SEMANTIC" in err
    assert "index-semantic" in err


def test_search_semantic_gate_off_capture(monkeypatch, capsys):
    """REQ-002/US2-AC2: --semantic with SERTOR_MEMORY off → exit 1, names SERTOR_MEMORY."""
    monkeypatch.delenv("SERTOR_MEMORY", raising=False)
    monkeypatch.delenv("SERTOR_MEMORY_SEMANTIC", raising=False)
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: None)
    code = _run(["memory", "search", "q", "--semantic"])
    err = capsys.readouterr().err
    assert code == 1
    assert "SERTOR_MEMORY" in err


def test_search_semantic_no_fulltext_in_error(monkeypatch, capsys):
    """SC-005: the gate error never carries full-text results (no silent fallback)."""
    monkeypatch.delenv("SERTOR_MEMORY", raising=False)
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: None)
    # If the command wrongly fell back, this FTS would be queried.
    called = {"fts": False}
    monkeypatch.setattr(
        cli, "build_episodic_search",
        lambda s: called.__setitem__("fts", True) or None,
    )
    code = _run(["memory", "search", "q", "--semantic"])
    capsys.readouterr()
    assert code == 1
    assert called["fts"] is False


def test_fulltext_default_unaffected_by_semantic_knob(monkeypatch, capsys):
    """REQ-013: enabling SERTOR_MEMORY_SEMANTIC does not change `memory search` (no --semantic)."""
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.setenv("SERTOR_MEMORY_SEMANTIC", "true")

    class _FTS:
        def __init__(self):
            self.calls = 0

        def search(self, q):
            self.calls += 1
            return EpisodicResults(hits=(), latency_ms=0.0)

    fts = _FTS()
    monkeypatch.setattr(cli, "build_episodic_search", lambda s: fts)
    code = _run(["memory", "search", "query"])
    capsys.readouterr()
    assert code == 0
    assert fts.calls == 1


# --- US6: backfill ------------------------------------------------------------------------------


def test_index_semantic_human_and_json(monkeypatch, capsys):
    """US6-AC5/REQ-007: index-semantic reports embedded/skipped/errors."""
    fake = _FakeSemanticIndex(index_report=SemanticIndexReport(embedded=3, skipped=1, errors=0))
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: fake)
    monkeypatch.setattr(cli, "build_memory_archive", lambda s: object())
    code = _run(["memory", "index-semantic"])
    out = capsys.readouterr().out
    assert code == 0
    assert "embedded=3" in out and "skipped=1" in out and "errors=0" in out
    assert fake.indexed == 1

    code = _run(["memory", "index-semantic", "--json"])
    assert json.loads(capsys.readouterr().out) == {"embedded": 3, "skipped": 1, "errors": 0}


def test_index_semantic_gate_off_exit1(monkeypatch, capsys):
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.delenv("SERTOR_MEMORY_SEMANTIC", raising=False)
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: None)
    code = _run(["memory", "index-semantic"])
    err = capsys.readouterr().err
    assert code == 1
    assert "SERTOR_MEMORY_SEMANTIC" in err


def test_index_semantic_idempotent_no_new(monkeypatch, capsys):
    """SC-006: a backfill without new sessions reports embedded=0, exit 0."""
    fake = _FakeSemanticIndex(index_report=SemanticIndexReport(embedded=0, skipped=5, errors=0))
    monkeypatch.setattr(cli, "build_memory_semantic_index", lambda s, **kw: fake)
    monkeypatch.setattr(cli, "build_memory_archive", lambda s: object())
    code = _run(["memory", "index-semantic"])
    out = capsys.readouterr().out
    assert code == 0
    assert "embedded=0" in out


# --- pure render functions ----------------------------------------------------------------------


def test_format_semantic_results_pure():
    results = SemanticMemoryResults(hits=(_hit(),), latency_ms=1.0)
    human = output.format_semantic_results(results, json=False)
    assert "score=" in human and "sess-abc" in human
    arr = json.loads(output.format_semantic_results(results, json=True))
    assert arr[0]["session_key"] == "sess-abc"
    assert output.format_semantic_results(
        SemanticMemoryResults(hits=(), latency_ms=0.0), json=False
    ) == "(no results)"


def test_format_semantic_index_report_pure():
    report = SemanticIndexReport(embedded=4, skipped=2, errors=1)
    assert "embedded=4" in output.format_semantic_index_report(report, json=False)
    assert json.loads(output.format_semantic_index_report(report, json=True)) == {
        "embedded": 4, "skipped": 2, "errors": 1
    }
