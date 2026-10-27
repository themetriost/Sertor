"""Deterministic graph-navigation runner + ref validation + event (066, data-model §4).

`run_graph_evaluation` navigates each `[[graph_case]]` via the `CodeGraph` port and scores it with
the pure set-based oracle (`graph_eval`); the observability event `graph_eval` is emitted SEPARATELY
by `emit_graph_eval_event` (after the comparison, so `regressed`/`tolerance` are known): metrics-
only, no free text (RNF-3/Principio IX, contract event-graph-eval.md). `validate_refs` is a pure
graph↔ref comparison for the write-time check. No composition/adapter imports here.
"""
from __future__ import annotations

import logging

from sertor_core.domain.errors import GraphNotFoundError
from sertor_core.domain.ports import CodeGraph
from sertor_core.observability.logging import log_event
from sertor_core.services.eval.graph_eval import (
    evaluate_graph_case,
    evaluate_graph_suite,
    navigate,
)
from sertor_core.services.eval.models import (
    EvalSuite,
    GraphCaseResult,
    GraphEvalReport,
    GraphRegressionVerdict,
    RefValidation,
)


def run_graph_evaluation(graph: CodeGraph, suite: EvalSuite) -> GraphEvalReport:
    """Run the suite's `[[graph_case]]` against `graph` → `GraphEvalReport` (REQ-010/015).

    For each case: navigate (`who_calls`→callers, `defines`→definitions) → set of `ref`, score vs
    the expected set. A target absent from the graph yields an empty navigated set, scored without
    error (REQ-014). The graph not being built propagates `GraphNotFoundError` from the port
    (REQ-013). A suite without graph_cases → an empty report (honest, exit 0 — not an error here).
    Deterministic: the suite order + the adapter's ref sorting fix the output (REQ-015).
    """
    results: list[GraphCaseResult] = []
    for case in suite.graph_cases:
        navigated = navigate(graph, case.relation, case.target)
        metric = evaluate_graph_case(navigated, frozenset(case.expected))
        results.append(
            GraphCaseResult(relation=case.relation, target=case.target, metric=metric)
        )
    return evaluate_graph_suite(results)


def emit_graph_eval_event(
    report: GraphEvalReport, verdict: GraphRegressionVerdict, exact_gate: bool
) -> None:
    """Emit the `graph_eval` event — metrics-only (RNF-3, contract event-graph-eval.md).

    NEVER `target`/`ref`/`missing`/`extra` or any free text/path. `relations` is a closed-card.
    count per relation (`who_calls`/`defines`). `tolerance` is null for `no-baseline`.
    """
    relations: dict[str, int] = {}
    for r in report.cases:
        relations[r.relation] = relations.get(r.relation, 0) + 1
    log_event(
        logging.INFO,
        "graph_eval",
        cases=report.cases_count,
        relations=relations,
        mean_precision=report.mean_precision,
        mean_recall=report.mean_recall,
        mean_f1=report.mean_f1,
        regressed=verdict.verdict == "regressed",
        tolerance=verdict.tolerance if verdict.verdict != "no-baseline" else None,
        exact_gate=exact_gate,
    )


def validate_refs(
    graph: CodeGraph, relation: str, target: str, refs: tuple[str, ...]
) -> RefValidation:
    """Pure graph↔ref comparison for the write-time check (REQ-042). Exit 0 always (a check).

    Graph not built → `RefValidation(checked=refs, unverifiable=(), graph_available=False)`
    (honest degradation, not a crash). Otherwise navigate `(relation, target)` for the real refs;
    `unverifiable` = the requested refs the graph does not confirm (named, not silently dropped).
    """
    try:
        real_refs = navigate(graph, relation, target)
    except GraphNotFoundError:
        return RefValidation(checked=refs, unverifiable=(), graph_available=False)
    unverifiable = tuple(r for r in refs if r not in real_refs)
    return RefValidation(checked=refs, unverifiable=unverifiable, graph_available=True)
