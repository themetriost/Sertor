"""US1/US2/US3 — CLI `memory show` / `memory list` (036, FR-001/002/008/009, contract).

Offline: the core is mocked by monkeypatching `build_memory_reader` (no disk, no network), same
style as `tests/unit/test_cli_memory.py`. Covers the gate (None → ConfigError exit 1), not-found
vs existing-but-empty, recency/limit pass-through, and the `--json` flag.
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.composition import build_memory_reader
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError
from sertor_core.domain.memory import ArchivedSession, SessionSummary, TranscriptTurn


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    """Isolate from the repo `.env` (same pattern as test_cli_memory.py)."""
    _orig = Settings.load.__func__
    monkeypatch.setattr(
        Settings, "load", classmethod(lambda c, env_file=".env": _orig(c, env_file=None))
    )


def _run(argv):
    return cli.main(argv)


def _archived(*, turns):
    return ArchivedSession(
        session_key="sess-abc",
        project_id="proj",
        captured_at=1718360463.0,
        adapter_kind="claude-code",
        turns=turns,
    )


class _FakeReader:
    """Fake `MemoryArchive`: serves `get`/`list_recent` from fixtures; records the calls."""

    def __init__(self, *, session=None, summaries=()):
        self._session = session
        self._summaries = summaries
        self.got = None
        self.listed = None

    def get(self, session_key):
        self.got = session_key
        return self._session

    def list_recent(self, limit):
        self.listed = limit
        return self._summaries


# ============================================================ US1: memory show


def test_show_full_transcript_exit0(monkeypatch, capsys):
    session = _archived(
        turns=(
            TranscriptTurn(index=0, role="user", text="alpha", ts=1718360455.0),
            TranscriptTurn(index=1, role="assistant", text="beta", ts=1718360461.0),
        )
    )
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: _FakeReader(session=session))
    code = _run(["memory", "show", "sess-abc"])
    out = capsys.readouterr().out
    assert code == 0
    assert "[0] user" in out
    assert "[1] assistant" in out
    assert "alpha" in out and "beta" in out


def test_show_json(monkeypatch, capsys):
    session = _archived(
        turns=(TranscriptTurn(index=0, role="user", text="alpha", ts=1718360455.0),)
    )
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: _FakeReader(session=session))
    code = _run(["memory", "show", "sess-abc", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["session_key"] == "sess-abc"
    assert payload["turns"][0]["text"] == "alpha"


def test_show_not_found_exit1(monkeypatch, capsys):
    # get → None = session absent → SessionNotFoundError, exit 1, actionable message.
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: _FakeReader(session=None))
    code = _run(["memory", "show", "ghost"])
    captured = capsys.readouterr()
    assert code == 1
    assert "error:" in captured.err
    assert "session not found" in captured.err
    assert "ghost" in captured.err
    assert "memory list" in captured.err  # suggestion (distinguishes from store-ko, F3)
    assert captured.out.strip() == ""


def test_show_existing_but_empty_exit0(monkeypatch, capsys):
    # existing session with no turns → explicit empty state, exit 0 (distinct from not-found).
    empty = _archived(turns=())
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: _FakeReader(session=empty))
    code = _run(["memory", "show", "sess-abc"])
    out = capsys.readouterr().out
    assert code == 0
    assert "(empty session)" in out


def test_show_gate_off_exit1(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: None)
    code = _run(["memory", "show", "sess-abc"])
    captured = capsys.readouterr()
    assert code == 1
    assert "error:" in captured.err
    assert "SERTOR_MEMORY" in captured.err
    assert captured.out.strip() == ""


# ============================================================ US2: memory list


def _summary(key, captured_at, count):
    return SessionSummary(session_key=key, captured_at=captured_at, turn_count=count)


def test_list_human_output(monkeypatch, capsys):
    summaries = (_summary("new", 3000.0, 3), _summary("old", 1000.0, 12))
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: _FakeReader(summaries=summaries))
    code = _run(["memory", "list"])
    out = capsys.readouterr().out
    assert code == 0
    assert "session=new" in out and "session=old" in out
    assert "turns=3" in out and "turns=12" in out


def test_list_json(monkeypatch, capsys):
    summaries = (_summary("new", 3000.0, 3),)
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: _FakeReader(summaries=summaries))
    code = _run(["memory", "list", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    arr = json.loads(out)
    assert arr == [{"session_key": "new", "captured_at": 3000.0, "turn_count": 3}]


def test_list_empty_archive_exit0(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: _FakeReader(summaries=()))
    code = _run(["memory", "list"])
    out = capsys.readouterr().out
    assert code == 0
    assert "(no sessions)" in out


def test_list_default_limit_from_settings(monkeypatch, capsys):
    reader = _FakeReader(summaries=())
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: reader)
    code = _run(["memory", "list"])
    capsys.readouterr()
    assert code == 0
    assert reader.listed == 20  # Settings.memory_list_limit default


def test_list_k_overrides_default(monkeypatch, capsys):
    reader = _FakeReader(summaries=())
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: reader)
    code = _run(["memory", "list", "-k", "5"])
    capsys.readouterr()
    assert code == 0
    assert reader.listed == 5


def test_list_gate_off_exit1(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: None)
    code = _run(["memory", "list"])
    captured = capsys.readouterr()
    assert code == 1
    assert "SERTOR_MEMORY" in captured.err
    assert captured.out.strip() == ""


# ============================================================ US3: gate consistency (no-automation)


def test_build_memory_reader_returns_none_when_memory_off():
    # R-GATE: privacy-by-default — memory off → factory None (no file opened).
    settings = Settings(memory_enabled=False)
    assert build_memory_reader(settings) is None


def test_build_memory_reader_returns_archive_when_enabled(tmp_path):
    settings = Settings(memory_enabled=True, index_dir=tmp_path)
    reader = build_memory_reader(settings)
    assert reader is not None
    assert hasattr(reader, "get") and hasattr(reader, "list_recent")


def test_require_memory_reader_none_raises_configerror_naming_lever(monkeypatch):
    # The CLI helper turns the gate's None into a ConfigError that names SERTOR_MEMORY.
    monkeypatch.setattr(cli, "build_memory_reader", lambda s: None)
    with pytest.raises(ConfigError) as exc:
        cli._require_memory_reader(Settings(memory_enabled=False))
    assert "SERTOR_MEMORY" in str(exc.value)
