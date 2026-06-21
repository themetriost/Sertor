"""Deterministic fused (per-surface + fusion coverage) runner + event (070, data-model §3/§4).

`run_fused_evaluation` measures the TWO mono-type retrieval surfaces (`search_code`/`search_docs`)
by wrapping the `RetrievalFacade` in thin `_SurfaceEngine` adapters and reusing the INVARIANT
`evaluate`; it then computes the pure union hit-rate on the `both`-intent cases via
`facade.search_combined` (which now returns the tuple `(docs, code)` — the two labelled flows).
The fused surface `search_combined` is NO LONGER measured as an IR-ranked surface (its cross-type
ranking was the wrong metric on incommensurable scores, 070 root-cause fix): the union hit-rate IS
the measure of the fused surface. The observability event `fused_eval` is emitted SEPARATELY by
`emit_fused_eval_event` (after the comparison, so `regressed`/`tolerance` are known): metrics-only,
no free text (RNF-3/Principio IX, contract event-fused-eval.md). No composition/adapter imports here
— the facade is the vehicle (Principio XI).
"""
from __future__ import annotations

import logging

from sertor_core.domain.entities import RetrievalResult
from sertor_core.engines.evaluation import evaluate
from sertor_core.observability.logging import log_event
from sertor_core.services.eval.fusion import INTENT_SURFACE, union_hit_rate
from sertor_core.services.eval.models import (
    EvalSuite,
    FusedEvalReport,
    FusedRegressionVerdict,
    SurfaceEvalReport,
)
from sertor_core.services.retrieval import RetrievalFacade

# The IR-ranked surfaces measured by a fused run, in stable order (code, docs). `search_combined` is
# NOT here (070): the fused surface is measured exclusively by the fusion coverage, not by an
# IR-ranked metric over a cross-type list (that ranking on incommensurable scores was the wrong
# measure — Principio XII, fix the cause).
_SURFACES: tuple[str, ...] = ("search_code", "search_docs")


class _SurfaceEngine:
    """A `QueryableEngine` (structural typing — NO inheritance) routing query → `facade.<surface>`.

    `evaluate` uses only `provider` + `query`; two instances (code/docs) measure the two mono-type
    surfaces with the SAME `evaluate` machine (invariant). `surface` is the name of the facade
    method (`search_code`/`search_docs`). It does NOT wrap `search_combined` (070): that surface
    returns the tuple `(docs, code)`, not a single ranked list, and is measured only by the union
    hit-rate.
    """

    def __init__(self, facade: RetrievalFacade, surface: str, provider: str):
        self._facade = facade
        self._surface = surface
        self._provider = provider

    @property
    def provider(self) -> str:
        return self._provider

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        return getattr(self._facade, self._surface)(query, k)


def run_fused_evaluation(
    facade: RetrievalFacade,
    suite: EvalSuite,
    ks: tuple[int, ...],
    fusion_k: int,
) -> FusedEvalReport:
    """Measure the two mono-type surfaces + union hit-rate → `FusedEvalReport` (070, REQ-010/020).

    For each surface: select the suite cases of the matching `intent` (via `INTENT_SURFACE`), rebase
    them to a per-surface `EvalSuite`, project to `GroundTruth`, and run the INVARIANT `evaluate`.
    The union hit-rate is computed on the `both`-intent cases via `facade.search_combined` (which
    now returns the tuple `(docs, code)`). A surface with no cases of its intent yields an empty
    `EvalReport` (honest, exit 0). A suite with no intent-typed cases → empty surfaces + an empty
    `FusionReport` (`cases_count=0`); the actionable message comes from the CLI. Deterministic
    (REQ-041).
    """
    provider = facade.provider
    surface_to_intent = {v: k for k, v in INTENT_SURFACE.items()}
    surfaces: list[SurfaceEvalReport] = []
    for surface in _SURFACES:
        intent = surface_to_intent[surface]
        engine = _SurfaceEngine(facade, surface, provider)
        cases = EvalSuite(cases=suite.cases_for_intent(intent))
        report = evaluate(engine, cases.to_ground_truth(), ks)
        surfaces.append(SurfaceEvalReport(surface=surface, report=report))
    fusion = union_hit_rate(suite.fusion_cases(), facade.search_combined, fusion_k)
    return FusedEvalReport(surfaces=tuple(surfaces), fusion=fusion, provider=provider)


def emit_fused_eval_event(
    report: FusedEvalReport, verdict: FusedRegressionVerdict
) -> None:
    """Emit the `fused_eval` event — metrics-only (RNF-3, contract event-fused-eval.md).

    NEVER `query`/`expected`/path/symbol or any free text. `cases` is a closed-card. count per
    intent; `surface_mrr`/`surface_hit3` are keyed by the closed surface set. `tolerance` is null
    for `no-baseline`.
    """
    by_surface = {s.surface: s.report for s in report.surfaces}
    cases = {
        "code": by_surface["search_code"].queries if "search_code" in by_surface else 0,
        "doc": by_surface["search_docs"].queries if "search_docs" in by_surface else 0,
        "both": report.fusion.cases_count,
    }
    surface_mrr = {s.surface: s.report.mrr for s in report.surfaces}
    surface_hit3 = {s.surface: s.report.hit_rate.get(3, 0.0) for s in report.surfaces}
    log_event(
        logging.INFO,
        "fused_eval",
        provider=report.provider,
        cases=cases,
        surface_mrr=surface_mrr,
        surface_hit3=surface_hit3,
        union_hit_rate=report.fusion.union_hit_rate,
        regressed=verdict.verdict == "regressed",
        tolerance=verdict.tolerance if verdict.verdict != "no-baseline" else None,
    )
