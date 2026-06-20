"""Test the CLI `sertor-rag eval` (065, TASK-013): run/add-case/validate-path with core mocked.

The eval runner and the indexed-docs vehicle are monkeypatched (no real engine/index); the suite
lives in a tmp `eval_dir`. Exit codes follow the contract (0/1/2). Gate (SC-004) is exercised with a
fixed suite + baseline.
"""
from __future__ import annotations

import dataclasses
import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.engines.evaluation import EvalReport, QueryOutcome
from sertor_core.services.eval import baseline_io
from sertor_core.services.eval.models import Baseline, EvalCase
from sertor_core.services.eval.suite_io import add_case


class _FakeRunner:
    """Stand-in for the composition `_EvalRunner`: returns a fixed report (no engine)."""

    def __init__(self, settings, report: EvalReport):
        self._settings = settings
        self._report = report

    @property
    def settings(self):
        return self._settings

    def run(self, suite, ks=(1, 3, 5, 10)):
        return self._report, suite.kinds()

    def run_labelled(self, label, suite, ks=(1, 3, 5, 10)):
        # distinct mrr per label so the comparison columns differ
        mrr = 0.9 if label == "hybrid" else 0.6
        rep = dataclasses.replace(self._report, mrr=mrr, provider=label)
        return rep, suite.kinds()


def _report(mrr=0.83) -> EvalReport:
    return EvalReport(
        hit_rate={1: 0.55, 3: 0.82, 5: 0.91, 10: 1.0},
        mrr=mrr,
        queries=1,
        provider="ollama:nomic",
        per_query=(
            QueryOutcome("EmbeddingProvider", ("src/ports.py",), True, 1, "src/ports.py"),
        ),
    )


@pytest.fixture
def wired(tmp_path, monkeypatch):
    """Wire the CLI eval to a tmp eval_dir + a fake runner + a fixed indexed-docs set."""
    eval_dir = tmp_path / "eval"
    settings = Settings(eval_dir=eval_dir, eval_tolerance=0.0, corpus="default", backend="local")
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, env_file=".env": settings))

    state = {"report": _report(), "indexed": frozenset({"src/ports.py"})}
    monkeypatch.setattr(cli, "build_eval_runner", lambda s: _FakeRunner(s, state["report"]))
    monkeypatch.setattr(cli, "build_indexed_docs", lambda s: state["indexed"])
    return settings, eval_dir, state


def _seed_suite(eval_dir):
    add_case(eval_dir / "suite.toml", EvalCase("EmbeddingProvider", ("src/ports.py",), "symbol"))


# --------------------------------------------------------------------- run
def test_run_with_suite_succeeds(wired, capsys):
    _settings, eval_dir, _ = wired
    _seed_suite(eval_dir)
    code = cli.main(["eval", "run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "mrr=0.83" in out
    assert "hit@1" in out


def test_run_without_suite_exits_1_actionable(wired, capsys):
    code = cli.main(["eval", "run"])
    err = capsys.readouterr().err
    assert code == 1
    assert "add-case" in err


def test_run_record_baseline_writes_file(wired, capsys):
    _settings, eval_dir, _ = wired
    _seed_suite(eval_dir)
    code = cli.main(["eval", "run", "--record-baseline"])
    assert code == 0
    assert (eval_dir / "baseline.toml").exists()
    loaded = baseline_io.load_baseline(eval_dir / "baseline.toml")
    assert loaded is not None and loaded.mrr == 0.83


def test_run_regression_exits_1(wired, capsys):
    _settings, eval_dir, state = wired
    _seed_suite(eval_dir)
    # record a strong baseline, then degrade the report → gate fails
    baseline_io.write_baseline(
        eval_dir / "baseline.toml",
        Baseline(
            hit_rate={1: 0.55, 3: 0.82, 5: 0.91, 10: 1.0},
            mrr=0.83, queries=1, provider="ollama:nomic",
            recorded_at=baseline_io.now_iso_utc(),
        ),
    )
    state["report"] = _report(mrr=0.40)
    code = cli.main(["eval", "run"])
    err = capsys.readouterr().err
    assert code == 1
    assert "non-regression gate FAILED" in err


def test_run_within_tolerance_exits_0(wired, monkeypatch, capsys):
    settings, eval_dir, state = wired
    _seed_suite(eval_dir)
    baseline_io.write_baseline(
        eval_dir / "baseline.toml",
        Baseline(
            hit_rate={1: 0.55, 3: 0.82, 5: 0.91, 10: 1.0},
            mrr=0.83, queries=1, provider="ollama:nomic",
            recorded_at=baseline_io.now_iso_utc(),
        ),
    )
    tolerant = dataclasses.replace(settings, eval_tolerance=0.05)
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, env_file=".env": tolerant))
    state["report"] = _report(mrr=0.80)  # within 0.05 of 0.83
    code = cli.main(["eval", "run"])
    assert code == 0


def test_run_compare_two_configs(wired, capsys):
    _settings, eval_dir, _ = wired
    _seed_suite(eval_dir)
    code = cli.main(["eval", "run", "--compare", "baseline,hybrid"])
    out = capsys.readouterr().out
    assert code == 0
    assert "baseline" in out and "hybrid" in out


# --------------------------------------------------------------------- add-case
def test_add_case_path_in_index_succeeds(wired, capsys):
    _settings, eval_dir, _ = wired
    code = cli.main(["eval", "add-case", "--query", "Q", "--expected", "src/ports.py"])
    assert code == 0
    from sertor_core.services.eval.suite_io import load_suite
    assert load_suite(eval_dir / "suite.toml").cases[0].query == "Q"


def test_add_case_missing_path_without_confirm_exits_1(wired, capsys):
    _settings, eval_dir, _ = wired
    code = cli.main(["eval", "add-case", "--query", "Q", "--expected", "src/absent.py"])
    err = capsys.readouterr().err
    assert code == 1
    assert "confirm" in err.lower()
    assert not (eval_dir / "suite.toml").exists()  # nothing written


def test_add_case_missing_path_with_confirm_succeeds(wired, capsys):
    _settings, eval_dir, _ = wired
    code = cli.main(
        ["eval", "add-case", "--query", "Q", "--expected", "src/absent.py", "--confirm"]
    )
    assert code == 0
    from sertor_core.services.eval.suite_io import load_suite
    assert load_suite(eval_dir / "suite.toml").cases[0].expected == ("src/absent.py",)


# --------------------------------------------------------------------- validate-path
def test_validate_path_always_exit_0(wired, capsys):
    code = cli.main(["eval", "validate-path", "src/ports.py", "src/absent.py"])
    assert code == 0


def test_validate_path_json(wired, capsys):
    code = cli.main(["eval", "validate-path", "src/ports.py", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    obj = json.loads(out)
    assert obj["checked"] == ["src/ports.py"]
    assert obj["index_available"] is True


# --------------------------------------------------------------------- usage
def test_eval_without_subcommand_exits_2():
    with pytest.raises(SystemExit) as exc:
        cli.main(["eval"])
    assert exc.value.code == 2
