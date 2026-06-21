"""Test `compare_fused_to_baseline` (069, TASK-B02): pure non-regression gate.

Zero I/O. Covers no-baseline, per-surface MRR regression, fusion coverage regression (R-3), the
tolerance window, the «better MRR but worse coverage» case, and determinism.
"""
from __future__ import annotations

from sertor_core.engines.evaluation import EvalReport
from sertor_core.services.eval.models import (
    FusedBaseline,
    FusedEvalReport,
    FusionReport,
    SurfaceBaseline,
    SurfaceEvalReport,
)
from sertor_core.services.eval.regression import compare_fused_to_baseline


def _report(combined_mrr: float = 0.69, coverage: float = 0.5) -> FusedEvalReport:
    def surf(name, mrr):
        return SurfaceEvalReport(
            name, EvalReport({3: 0.8}, mrr, 1, "hash")
        )

    return FusedEvalReport(
        surfaces=(
            surf("search_code", 0.64),
            surf("search_docs", 0.73),
            surf("search_combined", combined_mrr),
        ),
        fusion=FusionReport(cases=(), coverage=coverage, cases_count=1, hit_but_not_covered=0),
        provider="hash",
    )


def _baseline(combined_mrr: float = 0.69, coverage: float = 0.5) -> FusedBaseline:
    return FusedBaseline(
        surfaces=(
            SurfaceBaseline("search_code", {3: 0.8}, 0.64),
            SurfaceBaseline("search_docs", {3: 0.8}, 0.73),
            SurfaceBaseline("search_combined", {3: 0.8}, combined_mrr),
        ),
        fusion_coverage=coverage,
        queries=1,
        provider="hash",
        recorded_at="2026-06-21T00:00:00Z",
    )


def test_no_baseline_passes():
    v = compare_fused_to_baseline(_report(), None, 0.0)
    assert v.verdict == "no-baseline"
    assert v.exit_code() == 0


def test_surface_mrr_regression():
    v = compare_fused_to_baseline(_report(combined_mrr=0.40), _baseline(combined_mrr=0.69), 0.0)
    assert v.verdict == "regressed"
    assert v.exit_code() == 1


def test_fusion_coverage_regression():
    v = compare_fused_to_baseline(_report(coverage=0.2), _baseline(coverage=0.5), 0.0)
    assert v.verdict == "regressed"
    assert any(d.name == "fusion_coverage" and d.regressed for d in v.deltas)


def test_within_tolerance_passes():
    v = compare_fused_to_baseline(_report(combined_mrr=0.66), _baseline(combined_mrr=0.69), 0.05)
    assert v.verdict == "pass"
    assert v.exit_code() == 0


def test_all_within_tolerance_passes():
    v = compare_fused_to_baseline(_report(), _baseline(), 0.0)
    assert v.verdict == "pass"


def test_better_mrr_worse_coverage_regresses():
    # combined MRR up, fusion coverage down past tolerance → still regressed (R-3)
    v = compare_fused_to_baseline(
        _report(combined_mrr=0.90, coverage=0.2), _baseline(combined_mrr=0.69, coverage=0.5), 0.0
    )
    assert v.verdict == "regressed"


def test_deterministic():
    r, b = _report(), _baseline()
    assert compare_fused_to_baseline(r, b, 0.0) == compare_fused_to_baseline(r, b, 0.0)


def test_fusion_coverage_delta_separate_from_mrr():
    v = compare_fused_to_baseline(_report(), _baseline(), 0.0)
    names = {d.name for d in v.deltas}
    assert "fusion_coverage" in names
    assert "search_combined mrr" in names
