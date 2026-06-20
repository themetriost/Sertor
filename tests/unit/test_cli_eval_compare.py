"""Test `eval run --compare` with two mock engines (065, TASK-018, US4).

Reuses the fake-runner wiring of `test_cli_eval`: two labelled configs produce a side-by-side report
and an `eval` event per config.
"""
from __future__ import annotations

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.engines.evaluation import EvalReport, QueryOutcome
from sertor_core.services.eval.models import EvalCase
from sertor_core.services.eval.suite_io import add_case


class _FakeRunner:
    def __init__(self, settings):
        self._settings = settings

    @property
    def settings(self):
        return self._settings

    def run(self, suite, ks=(1, 3, 5, 10)):  # pragma: no cover - not used here
        raise AssertionError("compare path must use run_labelled")

    def run_labelled(self, label, suite, ks=(1, 3, 5, 10)):
        mrr = 0.9 if label == "hybrid" else 0.6
        rep = EvalReport(
            hit_rate={1: 0.5, 5: 0.9 if label == "hybrid" else 0.8},
            mrr=mrr,
            queries=1,
            provider=label,
            per_query=(QueryOutcome("q", ("p.py",), True, 1, "p.py"),),
        )
        return rep, suite.kinds()


@pytest.fixture
def wired(tmp_path, monkeypatch):
    eval_dir = tmp_path / "eval"
    settings = Settings(eval_dir=eval_dir, corpus="default", backend="local")
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, env_file=".env": settings))
    monkeypatch.setattr(cli, "build_eval_runner", lambda s: _FakeRunner(s))
    add_case(eval_dir / "suite.toml", EvalCase("q", ("p.py",), "nl"))
    return eval_dir


def test_compare_two_engines_side_by_side(wired, capsys):
    code = cli.main(["eval", "run", "--compare", "baseline,hybrid"])
    out = capsys.readouterr().out
    assert code == 0
    assert "baseline" in out and "hybrid" in out
    assert "hit@5" in out
    assert "mrr" in out


def test_compare_emits_event_per_engine(wired, monkeypatch):
    # One `eval` event per evaluated config (metrics-only). Capture at the call site (the event
    # otherwise depends on SERTOR_OBSERVABILITY wiring the handler).
    emitted: list[str] = []
    import sertor_core.cli.__main__ as cli_mod

    orig = cli_mod.emit_eval_event
    monkeypatch.setattr(
        cli_mod, "emit_eval_event",
        lambda report, verdict: (emitted.append(report.provider), orig(report, verdict))[1],
    )
    cli.main(["eval", "run", "--compare", "baseline,hybrid"])
    assert set(emitted) == {"baseline", "hybrid"}
