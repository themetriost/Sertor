"""Set-based oracle for graph navigation (066, data-model §4).

PURE measure of the code graph's relational power, PARALLEL to `engines/evaluation.py::evaluate`
(NOT inside `RoutedEvalEngine`, NOT inside `evaluate`): navigation answers are SETS, not ranked
lists, so the metric is precision/recall/F1 over sets — no rank, no @k (Won't). `navigate` is the
only function that touches the graph, and only through the `CodeGraph` PORT (`domain/ports.py`),
never a concrete adapter (Principio I). The MVP relation set is the single source of truth here.
"""
from __future__ import annotations

from sertor_core.domain.errors import GraphSuiteValidationError
from sertor_core.domain.ports import CodeGraph
from sertor_core.services.eval.models import GraphCaseResult, GraphEvalReport, SetMetric

# Unique source of the MVP relation set (N2 research). `who_calls`→callers, `defines`→definitions.
# `related_docs` is Could (DA-b): the schema is type-agnostic, so it can join later unchanged.
_SUPPORTED_RELATIONS: frozenset[str] = frozenset({"who_calls", "defines"})


def evaluate_graph_case(navigated: frozenset[str], expected: frozenset[str]) -> SetMetric:
    """Pure set-based metric of one case (REQ-020/023). Zero I/O, deterministic (REQ-015).

    Edge-case conventions (REQ-015): both empty → P=R=F1=1.0, exact; `expected` empty & `got`
    non-empty → P=0/R=1/F1=0; `got` empty & `expected` non-empty → P=1/R=0/F1=0.
    """
    intersection = navigated & expected
    # got empty: nothing wrong is retrieved → P=1.0 (both-empty and got-empty&expected-nonempty).
    precision = 1.0 if not navigated else len(intersection) / len(navigated)
    recall = 1.0 if not expected else len(intersection) / len(expected)
    f1 = 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)
    return SetMetric(
        precision=precision,
        recall=recall,
        f1=f1,
        exact=navigated == expected,
        got=tuple(sorted(navigated)),
        expected=tuple(sorted(expected)),
        missing=tuple(sorted(expected - navigated)),
        extra=tuple(sorted(navigated - expected)),
    )


def navigate(graph: CodeGraph, relation: str, target: str) -> frozenset[str]:
    """Navigate `relation` from `target` → the SET of `ref` (REQ-011/012/014).

    `who_calls`→`graph.who_calls(target)`; `defines`→`graph.find_symbol(target)`; both → the set of
    `SymbolHit.ref` (`path#qualname`). A symbol absent from the graph yields an empty list from the
    port → `frozenset()` (REQ-014, legitimate absence, not an error). The graph not being built
    propagates `GraphNotFoundError` from the port (REQ-013). A relation outside the MVP set →
    `GraphSuiteValidationError` (defence in depth: the loader already rejected the suite).
    """
    if relation == "who_calls":
        hits = graph.who_calls(target)
    elif relation == "defines":
        hits = graph.find_symbol(target)
    else:
        raise GraphSuiteValidationError(-1, f"unsupported relation: {relation!r}")
    return frozenset(hit.ref for hit in hits)


def evaluate_graph_suite(results: list[GraphCaseResult]) -> GraphEvalReport:
    """Aggregate per-case results into a run report (REQ-021). Pure, deterministic.

    Empty results → a report with all means 0.0 and `cases_count=0` (honest empty run).
    """
    if not results:
        return GraphEvalReport(
            cases=(),
            mean_precision=0.0,
            mean_recall=0.0,
            mean_f1=0.0,
            by_relation={},
            cases_count=0,
        )
    mean_precision = sum(r.metric.precision for r in results) / len(results)
    mean_recall = sum(r.metric.recall for r in results) / len(results)
    mean_f1 = sum(r.metric.f1 for r in results) / len(results)
    by_relation: dict[str, float] = {}
    for rel in sorted({r.relation for r in results}):
        rel_f1 = [r.metric.f1 for r in results if r.relation == rel]
        by_relation[rel] = sum(rel_f1) / len(rel_f1)
    return GraphEvalReport(
        cases=tuple(results),
        mean_precision=mean_precision,
        mean_recall=mean_recall,
        mean_f1=mean_f1,
        by_relation=by_relation,
        cases_count=len(results),
    )
