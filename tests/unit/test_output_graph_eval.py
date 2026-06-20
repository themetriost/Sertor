"""Test the graph-eval output formatters (066, TASK-A02): pure, human/JSON equivalence."""
from __future__ import annotations

import json

from sertor_core.cli import output
from sertor_core.services.eval.graph_eval import evaluate_graph_case
from sertor_core.services.eval.models import (
    GraphCaseResult,
    GraphEvalReport,
    GraphMetricDelta,
    GraphRegressionVerdict,
    RefValidation,
)


def _report() -> GraphEvalReport:
    exact = GraphCaseResult(
        "defines", "build_facade",
        evaluate_graph_case(frozenset({"c.py#build_facade"}), frozenset({"c.py#build_facade"})),
    )
    part = GraphCaseResult(
        "who_calls", "build_graph_service",
        evaluate_graph_case(frozenset({"a.py#A", "x.py#Y"}), frozenset({"a.py#A"})),
    )
    miss = GraphCaseResult(
        "who_calls", "EmbeddingProvider",
        evaluate_graph_case(frozenset({"a.py#A"}), frozenset({"a.py#A", "z.py#W"})),
    )
    return GraphEvalReport(
        cases=(exact, part, miss),
        mean_precision=0.79,
        mean_recall=0.90,
        mean_f1=0.83,
        by_relation={"who_calls": 0.81, "defines": 1.0},
        cases_count=3,
    )


def _verdict() -> GraphRegressionVerdict:
    return GraphRegressionVerdict(verdict="pass", deltas=(), tolerance=0.0)


def test_human_report_contains_tags_and_means():
    out = output.format_graph_eval_report(_report(), _verdict(), json=False)
    assert "mean_f1=0.83" in out
    assert "[exact]" in out and "[part ]" in out and "[miss ]" in out
    assert "+extra: x.py#Y" in out
    assert "-missing: z.py#W" in out
    assert "by-relation:" in out


def test_json_report_valid():
    out = output.format_graph_eval_report(_report(), _verdict(), json=True)
    data = json.loads(out)
    assert data["cases"] == 3 and data["mean_f1"] == 0.83
    assert data["non_regression"]["verdict"] == "pass"
    assert len(data["per_case"]) == 3


def test_format_graph_regression_regressed():
    v = GraphRegressionVerdict(
        verdict="regressed",
        deltas=(GraphMetricDelta("mean_f1", 0.50, 0.80, -0.30, True),),
        tolerance=0.0,
    )
    out = output.format_graph_regression(v, json=False)
    assert "REGRESSED" in out and "mean_f1" in out


def test_format_ref_validation_warns_unverifiable():
    rv = RefValidation(checked=("a.py#A", "z.py#Z"), unverifiable=("z.py#Z",), graph_available=True)
    out = output.format_ref_validation(rv, json=False)
    assert "z.py#Z" in out and "NOT confirmed" in out


def test_format_ref_validation_graph_unavailable():
    rv = RefValidation(checked=("a.py#A",), unverifiable=(), graph_available=False)
    out = output.format_ref_validation(rv, json=False)
    assert "graph not available" in out
