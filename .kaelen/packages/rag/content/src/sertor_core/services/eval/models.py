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
    and optional, preserved and shown in the report. `intent` (069) ∈ `{"code","doc","both"}` or
    `None`: it decides which `search_*` surface measures the case and the expected types (fusion
    coverage). `intent` is DISTINCT from `kind` (they coexist: e.g. `kind="nl"`, `intent="both"`).
    Validation (non-empty query/expected/paths, intent in set) is done by the loader
    (`SuiteValidationError`/`FusedSuiteValidationError` naming the case), not in the constructor.
    """

    query: str
    expected: tuple[str, ...]
    kind: str | None = None
    intent: str | None = None     # 069: "code" | "doc" | "both" | None — surface + expected types


@dataclass(frozen=True)
class GraphCase:
    """One graph-navigation case (066, REQ-001/003): relation + target → expected set of refs.

    `relation` ∈ MVP set (`"who_calls"`/`"defines"`); `target` is a symbol NAME; `expected` is the
    expected SET of `ref` (`path#qualname`), stored as an ordered tuple for a diffable TOML (the
    order does not matter to the metric). `expected` may be EMPTY (expected «no callers») — a
    legitimate case, NOT a validation error (deliberate asymmetry vs `EvalCase`, which needs ≥1
    path). Validation (relation supported, target non-empty, expected well-formed) is done by the
    loader (`GraphSuiteValidationError` naming the case), not in the constructor.
    """

    relation: str
    target: str
    expected: tuple[str, ...]


@dataclass(frozen=True)
class SetMetric:
    """Set-based metric of one graph-navigation case (066, REQ-020/023).

    No rank, no @k (Won't): the navigation answer is a SET. Deterministic edge cases (REQ-015):
    both empty → P=R=F1=1.0, `exact=True`; `expected` empty & `got` non-empty → P=0/R=1/F1=0;
    `got` empty & `expected` non-empty → P=1/R=0/F1=0.
    """

    precision: float
    recall: float
    f1: float
    exact: bool
    got: tuple[str, ...]
    expected: tuple[str, ...]
    missing: tuple[str, ...]   # expected − got
    extra: tuple[str, ...]     # got − expected


@dataclass(frozen=True)
class GraphCaseResult:
    """Per-case outcome of a graph-navigation run (066)."""

    relation: str
    target: str
    metric: SetMetric


@dataclass(frozen=True)
class GraphEvalReport:
    """Outcome of a graph-navigation run (066, REQ-021/030).

    Rendered in a DISTINCT section from the IR `EvalReport` (hit@k/MRR). `mean_f1` is the gate
    metric (DA-a); `mean_recall`/`mean_precision` are secondary. An empty run (no graph_cases) →
    all means 0.0 and `cases_count=0` (honest empty report, exit 0).
    """

    cases: tuple[GraphCaseResult, ...]
    mean_precision: float
    mean_recall: float
    mean_f1: float
    by_relation: dict[str, float]
    cases_count: int


@dataclass(frozen=True)
class GraphBaseline:
    """Recorded reference metrics for the graph-navigation non-regression gate (066, REQ-031).

    Persisted as `eval/graph_baseline.toml` (versioned, DISTINCT from the IR `eval/baseline.toml`).
    Built from a current `GraphEvalReport` only on an explicit `--record-baseline` (REQ-044-twin).
    NEVER contains the cases' `expected` (the snapshot lives in `[[graph_case]]`, DA-c).
    `recorded_at` is informative (ISO-8601 UTC).
    """

    mean_f1: float
    mean_recall: float
    mean_precision: float
    cases: int
    recorded_at: str


@dataclass(frozen=True)
class GraphMetricDelta:
    """One graph metric's current-vs-baseline comparison (066, REQ-032).

    The gate fires ONLY on `mean_f1` (`regressed` may be True); `mean_recall`/`mean_precision` are
    informative deltas (`regressed=False` always — DA-a).
    """

    name: str
    current: float
    baseline: float
    delta: float          # current - baseline
    regressed: bool       # delta < -tolerance (only "mean_f1" gates)


@dataclass(frozen=True)
class GraphRegressionVerdict:
    """Outcome of the graph non-regression gate (066, REQ-032/033).

    `verdict` ∈ {`"pass"`, `"regressed"`, `"no-baseline"`}. `exit_code` is 0 for pass/no-baseline,
    1 when regressed. Twin of `RegressionVerdict` (IR).
    """

    verdict: str
    deltas: tuple[GraphMetricDelta, ...]
    tolerance: float

    def exit_code(self) -> int:
        return 1 if self.verdict == "regressed" else 0


@dataclass(frozen=True)
class RefValidation:
    """Write-time validation of expected `ref`s against the graph (066, REQ-042).

    Twin of `PathValidation` (065) but on the GRAPH: a `ref` is *verifiable* if it appears among the
    refs the graph derives for its `(relation, target)`. `graph_available` is False when the graph
    is not built — honest degradation, not a silent pass: the caller warns and requires `--confirm`.
    """

    checked: tuple[str, ...]
    unverifiable: tuple[str, ...]   # refs the graph does not confirm (named, not silently dropped)
    graph_available: bool


@dataclass(frozen=True)
class EvalSuite:
    """The evaluation suite as project data (REQ-001/002/006): an ordered set of cases.

    Hosts BOTH the IR `cases` (`[[case]]`) and the navigation `graph_cases` (`[[graph_case]]`, 066,
    DA-d). `graph_cases` is additive (default `()` → an IR-only suite is unchanged); the IR
    projections (`to_ground_truth`/`kinds`/`rebased`) operate only on `cases` and are invariant.
    """

    cases: tuple[EvalCase, ...] = ()
    graph_cases: tuple[GraphCase, ...] = ()

    def to_ground_truth(self) -> GroundTruth:
        """Project to the core `GroundTruth` shape `(query, list(expected))` for `evaluate`.

        `kind` is dropped here on purpose (the core does not classify): the parallel `kinds()` keeps
        it for the report, re-associated by index.
        """
        return [(c.query, list(c.expected)) for c in self.cases]

    def kinds(self) -> tuple[str | None, ...]:
        """The `kind` of each case, in the same order as `to_ground_truth` (for the report)."""
        return tuple(c.kind for c in self.cases)

    def cases_for_intent(self, intent: str) -> tuple[EvalCase, ...]:
        """The IR cases whose `intent` matches `intent` (069). Pure, additive — IR proj. intact."""
        return tuple(c for c in self.cases if c.intent == intent)

    def fusion_cases(self) -> tuple[EvalCase, ...]:
        """The cases that ARE the fusion category — `intent="both"` (069, REQ-002/020)."""
        return self.cases_for_intent("both")

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
                out.append(
                    EvalCase(query=c.query, expected=rebased, kind=c.kind, intent=c.intent)
                )
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
class FusionCaseResult:
    """Outcome of the fused union measure of one `intent="both"` case (070, REQ-020/022).

    The headline number is the UNION (OR), not the product (AND): `hit` = an expected path appears
    in the docs flow OR in the code flow. `has_doc`/`has_code` are kept ONLY as per-case informative
    detail — they show WHICH stream found the expected — and never enter the aggregate score. The OR
    fixes the wrong metric of 069/0d89bf8 (`covered = has_doc AND has_code`, the «multiplication»
    the user excluded): the fusion is the union of the two flows, not their intersection.
    """

    query: str
    expected: tuple[str, ...]
    has_doc: bool          # informative: an expected path is in the docs flow
    has_code: bool         # informative: an expected path is in the code flow
    hit: bool              # headline: has_doc OR has_code (union)


@dataclass(frozen=True)
class FusionReport:
    """Aggregate of the union hit-rate on the combined surface (070, REQ-021).

    Reported ACCANTO a hit@k/MRR (not instead). The primary number is the UNION (OR) hit-rate:
    `union_hit_rate` = (#cases with a union hit) / (#`both`-intent cases). `has_doc`/`has_code` stay
    per-case detail only (which stream found the expected), never aggregated. A run without
    `both`-intent cases → `union_hit_rate=0.0` and `cases_count=0` (honest empty report, exit 0).
    """

    cases: tuple[FusionCaseResult, ...]
    union_hit_rate: float  # hit_count / cases_count (0.0 if cases_count == 0)
    cases_count: int


@dataclass(frozen=True)
class SurfaceEvalReport:
    """The `EvalReport` of ONE surface + its label (069, REQ-010/013).

    `surface` ∈ {`"search_code"`,`"search_docs"`,`"search_combined"`}; `report` is produced by the
    INVARIANT `evaluate` on the cases pertinent to that surface (riuso, no behaviour change).
    """

    surface: str
    report: EvalReport


@dataclass(frozen=True)
class FusedEvalReport:
    """Complete outcome of a fused run (069): per-surface metrics + fusion coverage.

    Additive: the per-surface `EvalReport`s come from `evaluate` unchanged; `fusion` is the pure
    extra pass over the combined surface's `doc_type`s.
    """

    surfaces: tuple[SurfaceEvalReport, ...]
    fusion: FusionReport
    provider: str


@dataclass(frozen=True)
class SurfaceBaseline:
    """Recorded reference metrics for ONE surface (069, REQ-010)."""

    surface: str
    hit_rate: dict[int, float]
    mrr: float


@dataclass(frozen=True)
class FusedBaseline:
    """Per-surface + fusion-coverage baseline of a fused run (069, REQ-010).

    Persisted as the `[fused_baseline]` section of `eval/baseline.toml`, additive to the IR
    `Baseline` (sezioni distinte; il writer preserva entrambe, preserve-both di FEAT-011). Built
    from a current `FusedEvalReport` only on an explicit `--record-baseline`. `recorded_at` is
    informative (ISO-8601 UTC). The fusion floor is the UNION hit-rate (070), not the old AND
    coverage.
    """

    surfaces: tuple[SurfaceBaseline, ...]
    union_hit_rate: float
    queries: int
    provider: str
    recorded_at: str


@dataclass(frozen=True)
class FusedRegressionVerdict:
    """Outcome of the fused non-regression gate (069, REQ-040/R-3).

    `verdict` ∈ {`"pass"`,`"regressed"`,`"no-baseline"`}. ANY per-surface metric below baseline
    beyond tolerance, OR the fusion coverage below baseline beyond tolerance → `"regressed"`
    (exit 1). `exit_code` is 0 for pass/no-baseline, 1 when regressed. Reuses `MetricDelta` (IR).
    Twin of `RegressionVerdict`/`GraphRegressionVerdict`.
    """

    deltas: tuple[MetricDelta, ...]
    tolerance: float
    verdict: str

    def exit_code(self) -> int:
        return 1 if self.verdict == "regressed" else 0


@dataclass(frozen=True)
class PathValidation:
    """Write-time validation of expected paths against the index (REQ-012/DA-e).

    `index_available` is False when the manifest is absent/incompatible — an honest degradation, not
    a silent pass: the caller decides (warn + require `--confirm`).
    """

    checked: tuple[str, ...]
    missing: tuple[str, ...]
    index_available: bool
