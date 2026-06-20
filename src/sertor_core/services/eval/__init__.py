"""Deterministic ground-truth evaluation service (065, FEAT-001).

Promotes the test-only evaluation harness (`engines/evaluation.py`) to a host-side capability: a
VERSIONED eval suite (`eval/suite.toml`), a deterministic run (`run_evaluation`, reusing the core
`evaluate`), a non-regression gate against a recorded baseline (`compare_to_baseline`), and the
write-time path validation against the index. Suite/baseline are DATA, not ports (single consumer,
same pattern as `IndexManifest`/`EmbeddingCache` — Principio III/YAGNI). stdlib only.
"""
from __future__ import annotations

from sertor_core.services.eval.baseline_io import load_baseline, write_baseline
from sertor_core.services.eval.models import (
    Baseline,
    ComparisonReport,
    EvalCase,
    EvalSuite,
    MetricDelta,
    PathValidation,
    RegressionVerdict,
)
from sertor_core.services.eval.regression import compare_to_baseline
from sertor_core.services.eval.runner import (
    emit_eval_event,
    run_evaluation,
    validate_paths,
)
from sertor_core.services.eval.suite_io import (
    add_case,
    amend_case,
    load_suite,
    write_suite,
)

__all__ = [
    "Baseline",
    "ComparisonReport",
    "EvalCase",
    "EvalSuite",
    "MetricDelta",
    "PathValidation",
    "RegressionVerdict",
    "add_case",
    "amend_case",
    "compare_to_baseline",
    "emit_eval_event",
    "load_baseline",
    "load_suite",
    "run_evaluation",
    "validate_paths",
    "write_baseline",
    "write_suite",
]
