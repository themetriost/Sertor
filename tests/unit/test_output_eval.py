"""Test the eval output formatters (065, TASK-013): pure, human + JSON equivalence."""
from __future__ import annotations

import json

from sertor_core.cli import output
from sertor_core.engines.evaluation import EvalReport, QueryOutcome
from sertor_core.services.eval.models import (
    MetricDelta,
    PathValidation,
    RegressionVerdict,
)


def _report() -> EvalReport:
    return EvalReport(
        hit_rate={1: 0.5, 5: 0.9, 10: 1.0},
        mrr=0.75,
        queries=2,
        provider="ollama:nomic",
        per_query=(
            QueryOutcome("EmbeddingProvider", ("src/ports.py",), True, 1, "src/ports.py"),
            QueryOutcome("missing thing", ("src/x.py",), False, None, "src/other.py"),
        ),
    )


def test_eval_report_human_has_metrics_and_per_query():
    out = output.format_eval_report(_report(), ("symbol", "nl"), None, json=False)
    assert "hit@1=0.50" in out
    assert "mrr=0.75" in out
    assert "[hit ]" in out
    assert "[miss]" in out
    assert "symbol" in out
    assert "rank=1" in out


def test_eval_report_json_has_same_fields():
    out = output.format_eval_report(_report(), ("symbol", "nl"), None, json=True)
    obj = json.loads(out)
    assert obj["provider"] == "ollama:nomic"
    assert obj["mrr"] == 0.75
    assert obj["hit_rate"]["1"] == 0.5
    assert len(obj["per_query"]) == 2
    assert obj["per_query"][0]["kind"] == "symbol"
    assert obj["per_query"][1]["hit"] is False


def test_eval_report_with_verdict_shows_non_regression():
    verdict = RegressionVerdict(
        verdict="pass",
        deltas=(MetricDelta("mrr", 0.75, 0.74, 0.01, False),),
        tolerance=0.0,
    )
    out = output.format_eval_report(_report(), ("symbol", "nl"), verdict, json=False)
    assert "non-regression: PASS" in out
    assert "mrr Δ=+0.01" in out


def test_comparison_human_has_columns():
    base = EvalReport({1: 0.4, 5: 0.8}, 0.6, 2, "base")
    hyb = EvalReport({1: 0.5, 5: 0.9}, 0.7, 2, "hyb")
    out = output.format_comparison((("baseline", base), ("hybrid", hyb)), json=False)
    assert "baseline" in out and "hybrid" in out
    assert "hit@5" in out
    assert "mrr" in out


def test_comparison_json():
    base = EvalReport({5: 0.8}, 0.6, 2, "base")
    out = output.format_comparison((("baseline", base),), json=True)
    obj = json.loads(out)
    assert obj["baseline"]["mrr"] == 0.6


def test_path_validation_missing_warns():
    pv = PathValidation(checked=("a.py", "b.py"), missing=("b.py",), index_available=True)
    out = output.format_path_validation(pv, json=False)
    assert "warning" in out.lower()
    assert "b.py" in out


def test_path_validation_index_unavailable():
    pv = PathValidation(checked=("a.py",), missing=(), index_available=False)
    out = output.format_path_validation(pv, json=False)
    assert "not available" in out.lower()


def test_path_validation_json():
    pv = PathValidation(checked=("a.py",), missing=(), index_available=True)
    obj = json.loads(output.format_path_validation(pv, json=True))
    assert obj["checked"] == ["a.py"]
    assert obj["index_available"] is True
