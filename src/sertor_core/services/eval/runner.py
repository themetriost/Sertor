"""Deterministic evaluation runner + path validation (065, data-model §4).

`run_evaluation` REUSES the core `evaluate` (it does not re-implement the metrics): it returns the
`EvalReport` plus the parallel `kinds` for the report. The observability event `eval` is emitted
SEPARATELY by `emit_eval_event` (after the comparison, so `regressed`/`tolerance` are known):
metrics-only, no free text (RNF-3/Principio IX, contract event-eval.md). `validate_paths` is a pure
path↔index comparison. No composition/adapter imports here (those live in the factories).
"""
from __future__ import annotations

import logging

from sertor_core.engines.evaluation import EvalReport, QueryableEngine, evaluate
from sertor_core.observability.logging import log_event
from sertor_core.services.eval.models import EvalSuite, PathValidation, RegressionVerdict


def run_evaluation(
    engine: QueryableEngine,
    suite: EvalSuite,
    ks: tuple[int, ...] = (1, 3, 5, 10),
) -> tuple[EvalReport, tuple[str | None, ...]]:
    """Run the suite against `engine` → `(EvalReport, kinds)` (REQ-031/033).

    Reuses `evaluate` (the deterministic measure). The parallel `kinds` lets the report show the
    per-case `kind` (which the core report does not carry — Principio I/III).
    """
    report = evaluate(engine, suite.to_ground_truth(), ks)
    return report, suite.kinds()


def emit_eval_event(report: EvalReport, verdict: RegressionVerdict | None) -> None:
    """Emit the `eval` observability event — metrics-only (RNF-3, contract event-eval.md).

    NEVER any free text: no query, no expected/path. `regressed`/`tolerance` come from the verdict
    (None → no comparison done: `regressed=False`, `tolerance=null`). Captured by the store only
    when `SERTOR_OBSERVABILITY=true` (the caller already wired `enable_observability`).
    """
    log_event(
        logging.INFO,
        "eval",
        provider=report.provider,
        queries=report.queries,
        hit_rate=report.hit_rate,
        mrr=report.mrr,
        regressed=verdict.verdict == "regressed" if verdict is not None else False,
        tolerance=verdict.tolerance if verdict is not None else None,
    )


def validate_paths(
    paths: tuple[str, ...], indexed_paths: frozenset[str] | None
) -> PathValidation:
    """Pure path↔index comparison (REQ-012/DA-e).

    `indexed_paths is None` (manifest absent/incompatible) → honest degradation: `index_available`
    False, no `missing` claimed (cannot verify). Otherwise `missing` = paths not in the index.
    """
    if indexed_paths is None:
        return PathValidation(checked=paths, missing=(), index_available=False)
    missing = tuple(p for p in paths if p not in indexed_paths)
    return PathValidation(checked=paths, missing=missing, index_available=True)
