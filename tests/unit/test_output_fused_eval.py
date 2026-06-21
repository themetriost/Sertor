"""Test the fused output formatters (069, TASK-A06): pure, human↔JSON equivalence.

Zero I/O. Builds report/verdict entities directly.
"""
from __future__ import annotations

import json

from sertor_core.cli.output import format_fused_eval_report, format_fused_regression
from sertor_core.engines.evaluation import EvalReport
from sertor_core.services.eval.models import (
    FusedEvalReport,
    FusedRegressionVerdict,
    FusionCaseResult,
    FusionReport,
    MetricDelta,
    SurfaceEvalReport,
)


def _surface(name: str, mrr: float) -> SurfaceEvalReport:
    return SurfaceEvalReport(
        surface=name,
        report=EvalReport(hit_rate={1: 0.5, 3: 0.8, 5: 0.9}, mrr=mrr, queries=2, provider="hash"),
    )


def _report() -> FusedEvalReport:
    fusion = FusionReport(
        cases=(
            FusionCaseResult("req+impl", ("r.md", "x.py"), True, True, True, True),
            FusionCaseResult("doc only", ("r.md", "x.py"), True, False, False, True),
        ),
        coverage=0.5,
        cases_count=2,
        hit_but_not_covered=1,
    )
    return FusedEvalReport(
        surfaces=(
            _surface("search_code", 0.64),
            _surface("search_docs", 0.73),
            _surface("search_combined", 0.69),
        ),
        fusion=fusion,
        provider="hash",
    )


def _pass_verdict() -> FusedRegressionVerdict:
    return FusedRegressionVerdict(
        deltas=(MetricDelta("fusion_coverage", 0.5, 0.47, 0.03, False),),
        tolerance=0.0,
        verdict="pass",
    )


def test_human_output_has_all_blocks():
    out = format_fused_eval_report(_report(), _pass_verdict(), json=False)
    assert "fusion coverage" in out
    assert "[covered]" in out
    assert "[GAP    ]" in out
    assert "MRR=0.64" in out
    assert "non-regression: PASS" in out
    assert "missing CODE" in out  # GAP detail for the doc-only case


def test_json_output_is_valid_and_equivalent():
    out = format_fused_eval_report(_report(), _pass_verdict(), json=True)
    obj = json.loads(out)
    assert obj["provider"] == "hash"
    assert obj["cases"] == {"code": 2, "doc": 2, "both": 2}
    assert obj["fusion"]["coverage"] == 0.5
    assert obj["fusion"]["hit_but_not_covered"] == 1
    assert obj["non_regression"]["verdict"] == "pass"
    assert len(obj["surfaces"]) == 3


def test_format_fused_regression_regressed():
    verdict = FusedRegressionVerdict(
        deltas=(
            MetricDelta("search_code mrr", 0.4, 0.64, -0.24, True),
            MetricDelta("fusion_coverage", 0.3, 0.5, -0.2, True),
        ),
        tolerance=0.0,
        verdict="regressed",
    )
    out = format_fused_regression(verdict, json=False)
    assert "REGRESSED" in out
    assert "search_code mrr" in out
    assert "fusion_coverage" in out


def test_empty_report_does_not_crash():
    empty = FusedEvalReport(
        surfaces=(
            _surface("search_code", 0.0),
            _surface("search_docs", 0.0),
            _surface("search_combined", 0.0),
        ),
        fusion=FusionReport(cases=(), coverage=0.0, cases_count=0, hit_but_not_covered=0),
        provider="hash",
    )
    verdict = FusedRegressionVerdict(deltas=(), tolerance=0.0, verdict="no-baseline")
    out = format_fused_eval_report(empty, verdict, json=False)
    assert "fusion coverage: 0.00" in out
    assert "no baseline" in out
