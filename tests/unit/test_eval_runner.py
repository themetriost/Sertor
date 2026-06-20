"""Test the eval runner: run_evaluation reuse, validate_paths, eval event (065, TASK-012)."""
from __future__ import annotations

import logging

from sertor_core.config.settings import Settings
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.services.eval.models import EvalCase, EvalSuite, RegressionVerdict
from sertor_core.services.eval.runner import (
    emit_eval_event,
    run_evaluation,
    validate_paths,
)
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

S = Settings.load(env_file=None)
COLL = "eval-runner-coll"


def _engine(sample_repo):
    engine = BaselineEngine(FakeEmbedder(dim=8), InMemoryStore(), COLL, S)
    engine.index(sample_repo)
    return engine


def test_run_evaluation_returns_report_and_kinds(sample_repo):
    engine = _engine(sample_repo)
    suite = EvalSuite(
        cases=(
            EvalCase("def add(a, b):\n    return a + b", ("app/calculator.py",), "symbol"),
        )
    )
    report, kinds = run_evaluation(engine, suite)
    assert report.queries == 1
    assert kinds == ("symbol",)
    assert len(report.per_query) == 1


def test_validate_paths_no_index_is_unavailable():
    pv = validate_paths(("a.py", "b.py"), None)
    assert pv.index_available is False
    assert pv.missing == ()
    assert pv.checked == ("a.py", "b.py")


def test_validate_paths_reports_missing():
    indexed = frozenset({"a.py", "c.py"})
    pv = validate_paths(("a.py", "b.py"), indexed)
    assert pv.index_available is True
    assert pv.missing == ("b.py",)


def test_validate_paths_all_present():
    indexed = frozenset({"a.py", "b.py"})
    pv = validate_paths(("a.py", "b.py"), indexed)
    assert pv.missing == ()


def test_emit_eval_event_metrics_only(caplog):
    report, _ = run_evaluation(_make_empty_engine(), EvalSuite(cases=()))
    verdict = RegressionVerdict(verdict="pass", deltas=(), tolerance=0.0)
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        emit_eval_event(report, verdict)
    records = [r for r in caplog.records if getattr(r, "operation", None) == "eval"]
    assert records, "eval event not emitted"
    rec = records[0]
    # metrics-only: no query/expected/path fields on the record
    assert not hasattr(rec, "query")
    assert rec.regressed is False
    assert rec.tolerance == 0.0


def _make_empty_engine():
    return BaselineEngine(FakeEmbedder(dim=8), InMemoryStore(), "empty-coll", S)
