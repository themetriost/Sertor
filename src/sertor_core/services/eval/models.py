"""Entities of the eval service (065, data-model §2/§3).

Frozen dataclasses — pure data, no I/O. The suite/baseline are VERSIONED project data (never
secrets, never rigenerabile output); the comparison/validation entities are derived projections.
The case `kind` lives HERE (the artifact metadata), not in the core `evaluate` (Principio I/III).
"""
from __future__ import annotations

from dataclasses import dataclass

from sertor_core.engines.evaluation import EvalReport, GroundTruth


@dataclass(frozen=True)
class EvalCase:
    """One evaluation case: a query and the path(s) that should be retrieved for it (REQ-001/003).

    `expected` paths are POSIX, relative to the indexed root. `kind` (`"symbol"`/`"nl"`/…) is free
    and optional, preserved and shown in the report. Validation (non-empty query/expected/paths) is
    done by the loader (`SuiteValidationError` naming the case), not in the constructor.
    """

    query: str
    expected: tuple[str, ...]
    kind: str | None = None


@dataclass(frozen=True)
class EvalSuite:
    """The evaluation suite as project data (REQ-001/002/006): an ordered set of cases."""

    cases: tuple[EvalCase, ...]

    def to_ground_truth(self) -> GroundTruth:
        """Project to the core `GroundTruth` shape `(query, list(expected))` for `evaluate`.

        `kind` is dropped here on purpose (the core does not classify): the parallel `kinds()` keeps
        it for the report, re-associated by index.
        """
        return [(c.query, list(c.expected)) for c in self.cases]

    def kinds(self) -> tuple[str | None, ...]:
        """The `kind` of each case, in the same order as `to_ground_truth` (for the report)."""
        return tuple(c.kind for c in self.cases)

    def rebased(self, prefix: str) -> EvalSuite:
        """Suite with `expected` paths rebased to an indexing root different from the repo root.

        Inherits the `relative_to` logic of the dogfood fixture (REQ-005): a case whose expected
        paths ALL fall outside `prefix` is dropped (it cannot be measured against that index).
        """
        norm = prefix.rstrip("/") + "/"
        out: list[EvalCase] = []
        for c in self.cases:
            rebased = tuple(p[len(norm):] for p in c.expected if p.startswith(norm))
            if rebased:
                out.append(EvalCase(query=c.query, expected=rebased, kind=c.kind))
        return EvalSuite(cases=tuple(out))


@dataclass(frozen=True)
class Baseline:
    """The recorded reference metrics for the non-regression gate (REQ-041).

    Persisted as `eval/baseline.toml` (versioned). Built from a current `EvalReport` only on an
    explicit `--record-baseline` (REQ-040/044). `recorded_at` is informative (ISO-8601 UTC).
    """

    hit_rate: dict[int, float]
    mrr: float
    queries: int
    provider: str
    recorded_at: str


@dataclass(frozen=True)
class MetricDelta:
    """One metric's current-vs-baseline comparison (REQ-042)."""

    name: str
    current: float
    baseline: float
    delta: float          # current - baseline
    regressed: bool       # delta < -tolerance


@dataclass(frozen=True)
class RegressionVerdict:
    """Outcome of the non-regression gate (REQ-042/043).

    `verdict` ∈ {`"pass"`, `"regressed"`, `"no-baseline"`}. `exit_code` is 0 for pass/no-baseline
    (the gate does not fail when there is nothing to compare to), 1 when regressed.
    """

    verdict: str
    deltas: tuple[MetricDelta, ...]
    tolerance: float

    def exit_code(self) -> int:
        return 1 if self.verdict == "regressed" else 0


@dataclass(frozen=True)
class ComparisonReport:
    """Side-by-side comparison of ≥2 local configs on the same suite (REQ-034)."""

    reports: tuple[tuple[str, EvalReport], ...]  # [(label, report), …]


@dataclass(frozen=True)
class PathValidation:
    """Write-time validation of expected paths against the index (REQ-012/DA-e).

    `index_available` is False when the manifest is absent/incompatible — an honest degradation, not
    a silent pass: the caller decides (warn + require `--confirm`).
    """

    checked: tuple[str, ...]
    missing: tuple[str, ...]
    index_available: bool
