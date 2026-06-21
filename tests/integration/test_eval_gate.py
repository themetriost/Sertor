"""End-to-end smoke test of the eval run + non-regression gate (065, TASK-022, not cloud).

Uses a real `BaselineEngine` over an in-memory store indexed from the sample repo (no network),
driven through the CLI vehicle (`sertor-rag eval ...`). Exercises SC-001 (determinism: two identical
runs → same metrics), SC-004 (the gate fails on a degraded suite), SC-003 (add-case grows the
suite), and SC-010 (a missing suite → exit 1, actionable).
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.services.eval.runner import run_evaluation
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

pytestmark = pytest.mark.integration

_COLL = "eval-gate-coll"


class _RealRunner:
    """A real eval runner over an in-memory index (the composition vehicle, mocked offline)."""

    def __init__(self, settings, engine):
        self._settings = settings
        self._engine = engine

    @property
    def settings(self):
        return self._settings

    def run(self, suite, ks=(1, 3, 5, 10)):
        return run_evaluation(self._engine, suite, ks)

    def run_labelled(self, label, suite, ks=(1, 3, 5, 10)):
        return run_evaluation(self._engine, suite, ks)


@pytest.fixture
def wired(tmp_path, sample_repo, monkeypatch):
    """Index the sample repo into an in-memory engine and wire the CLI eval to it."""
    eval_dir = tmp_path / "eval"
    settings = Settings(
        eval_dir=eval_dir, corpus="default", embed_provider="hash", index_dir=tmp_path
    )
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    engine = BaselineEngine(emb, store, _COLL, settings)
    engine.index(sample_repo)

    indexed = frozenset(
        {"app/calculator.py", "docs/guide.md", "svc/handler.go", "web/server.js"}
    )
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, e=".env": settings))
    monkeypatch.setattr(cli, "build_eval_runner", lambda s: _RealRunner(s, engine))
    monkeypatch.setattr(cli, "build_indexed_docs", lambda s: indexed)
    return settings, eval_dir


def _seed_real_suite(eval_dir):
    """A 2-case suite whose queries are exact chunk text → deterministic hits."""
    from sertor_core.services.eval.models import EvalCase
    from sertor_core.services.eval.suite_io import add_case

    add_case(eval_dir / "suite.toml",
             EvalCase("def add(a, b):\n    return a + b", ("app/calculator.py",), "symbol"))


def test_run_succeeds_with_metrics(wired, capsys):
    _settings, eval_dir = wired
    _seed_real_suite(eval_dir)
    code = cli.main(["eval", "run", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    obj = json.loads(out)
    assert "hit_rate" in obj and "mrr" in obj
    assert obj["queries"] == 1


def test_determinism_two_runs_same_metrics(wired, capsys):
    _settings, eval_dir = wired
    _seed_real_suite(eval_dir)
    cli.main(["eval", "run", "--json"])
    first = json.loads(capsys.readouterr().out)
    cli.main(["eval", "run", "--json"])
    second = json.loads(capsys.readouterr().out)
    assert first["hit_rate"] == second["hit_rate"]
    assert first["mrr"] == second["mrr"]


def test_gate_passes_on_recorded_baseline(wired, capsys):
    _settings, eval_dir = wired
    _seed_real_suite(eval_dir)
    assert cli.main(["eval", "run", "--record-baseline"]) == 0
    capsys.readouterr()
    assert (eval_dir / "baseline.toml").exists()
    # a re-run against the just-recorded baseline must PASS (exit 0)
    assert cli.main(["eval", "run"]) == 0


def test_gate_fails_on_degraded_suite(wired, capsys):
    settings, eval_dir = wired
    _seed_real_suite(eval_dir)
    cli.main(["eval", "run", "--record-baseline"])
    capsys.readouterr()
    # Degrade: add a case that will MISS (query unrelated to any chunk) → metrics drop → gate fails.
    from sertor_core.services.eval.models import EvalCase
    from sertor_core.services.eval.suite_io import add_case
    add_case(eval_dir / "suite.toml",
             EvalCase("zzz totally unrelated query nonexistent", ("app/none.py",), "nl"))
    code = cli.main(["eval", "run"])
    err = capsys.readouterr().err
    assert code == 1
    assert "non-regression gate FAILED" in err


def test_missing_suite_exits_1(wired, capsys):
    code = cli.main(["eval", "run"])
    err = capsys.readouterr().err
    assert code == 1
    assert "add-case" in err


def test_add_case_grows_suite(wired, capsys):
    _settings, eval_dir = wired
    code = cli.main(["eval", "add-case", "--query", "Q", "--expected", "app/calculator.py"])
    assert code == 0
    from sertor_core.services.eval.suite_io import load_suite
    assert len(load_suite(eval_dir / "suite.toml").cases) == 1


def test_validate_path_reports_presence(wired, capsys):
    code = cli.main(["eval", "validate-path", "app/calculator.py", "app/absent.py", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    obj = json.loads(out)
    assert "app/absent.py" in obj["missing"]
    assert "app/calculator.py" not in obj["missing"]
