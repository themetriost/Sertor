"""Composition root: wira i port agli adapter ed esegue il sandwich.

`prepare` (deterministico) → [agente/stub] → `report` (deterministico). `audit` è il monolite
offline che usa lo `StubAdjudicator`.
"""

from __future__ import annotations

from .config import DEFAULT_CONFIG, Config
from .domain.models import Adjudication, AuditBundle, AuditReport
from .domain.ports import Adjudicator, OriginalSourceResolver, SpecLiftSource
from .stages.assemble import assemble
from .stages.prepare import prepare


def build_bundle(
    speclift_source: SpecLiftSource,
    original_resolver: OriginalSourceResolver,
    changeset_ref: str | None = None,
    extra_gaps: list[str] | None = None,
    config: Config = DEFAULT_CONFIG,
) -> AuditBundle:
    """Marcia 1 (FEAT-001)."""

    return prepare(speclift_source, original_resolver, changeset_ref, extra_gaps, config)


def build_report(bundle: AuditBundle, adj: Adjudication, config: Config = DEFAULT_CONFIG) -> AuditReport:
    """Marcia 2 (FEAT-004): valida, attacca àncore, matrice, scoring, gap."""

    records, matrix, declared_gaps, open_questions = assemble(bundle, adj, config)
    return AuditReport(
        version=config.report_version,
        changeset_ref=bundle.changeset_ref,
        records=records,
        matrix=matrix,
        declared_gaps=declared_gaps,
        open_questions=open_questions,
    )


def audit(
    speclift_source: SpecLiftSource,
    original_resolver: OriginalSourceResolver,
    adjudicator: Adjudicator,
    changeset_ref: str | None = None,
    config: Config = DEFAULT_CONFIG,
) -> AuditReport:
    """Monolite: prepare → adjudicator → report. Con lo stub è offline/test (verdetti placeholder)."""

    bundle = build_bundle(speclift_source, original_resolver, changeset_ref, config=config)
    adj = adjudicator.adjudicate(bundle)
    return build_report(bundle, adj, config)
