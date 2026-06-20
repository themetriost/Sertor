"""Test the pure non-regression comparison (065, TASK-012)."""
from __future__ import annotations

from sertor_core.engines.evaluation import EvalReport
from sertor_core.services.eval.models import Baseline
from sertor_core.services.eval.regression import compare_to_baseline


def _report(mrr=0.83, hit=None) -> EvalReport:
    return EvalReport(
        hit_rate=hit or {1: 0.55, 5: 0.91, 10: 1.0},
        mrr=mrr,
        queries=11,
        provider="p",
    )


def _baseline(mrr=0.83, hit=None) -> Baseline:
    return Baseline(
        hit_rate=hit or {1: 0.55, 5: 0.91, 10: 1.0},
        mrr=mrr,
        queries=11,
        provider="p",
        recorded_at="2026-06-20T00:00:00Z",
    )


def test_no_baseline_is_no_baseline_verdict():
    v = compare_to_baseline(_report(), None, 0.0)
    assert v.verdict == "no-baseline"
    assert v.exit_code() == 0
    assert v.deltas == ()


def test_equal_metrics_pass():
    v = compare_to_baseline(_report(), _baseline(), 0.0)
    assert v.verdict == "pass"
    assert v.exit_code() == 0


def test_regression_beyond_tolerance_flagged():
    v = compare_to_baseline(_report(mrr=0.70), _baseline(mrr=0.83), 0.0)
    assert v.verdict == "regressed"
    assert v.exit_code() == 1
    mrr_delta = next(d for d in v.deltas if d.name == "mrr")
    assert mrr_delta.regressed
    assert mrr_delta.delta < 0


def test_within_tolerance_passes():
    v = compare_to_baseline(_report(mrr=0.82), _baseline(mrr=0.83), 0.02)
    assert v.verdict == "pass"
    assert v.exit_code() == 0


def test_only_common_metrics_compared():
    report = _report(hit={1: 0.5, 5: 0.9})
    baseline = _baseline(hit={1: 0.5, 5: 0.9, 10: 1.0})
    v = compare_to_baseline(report, baseline, 0.0)
    names = {d.name for d in v.deltas}
    assert "hit@10" not in names  # not in the report → not compared
    assert names == {"mrr", "hit@1", "hit@5"}


def test_deterministic_same_input_same_output():
    a = compare_to_baseline(_report(mrr=0.70), _baseline(), 0.0)
    b = compare_to_baseline(_report(mrr=0.70), _baseline(), 0.0)
    assert a == b
