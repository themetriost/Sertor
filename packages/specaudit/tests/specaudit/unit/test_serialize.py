"""T012 — serialize: round-trip dict<->model per i tre contratti."""

from __future__ import annotations

from specaudit.domain.models import (
    Adjudication,
    AlignedGroup,
    Anchor,
    AuditBundle,
    AuditRecord,
    AuditReport,
    ExtraItem,
    Level,
    Matrix,
    OriginalRequirement,
    RiskScore,
    SpecLiftItem,
    VerdictKind,
)
from specaudit.serialize import (
    adjudication_from_dict,
    adjudication_to_dict,
    bundle_from_dict,
    bundle_to_dict,
    report_from_dict,
    report_to_dict,
)


def _anchor() -> Anchor:
    return Anchor(file="src/a.py", lines=(1, 5), granularity="symbol", status="verified", symbol="do_x")


def test_bundle_round_trip():
    bundle = AuditBundle(
        version="1",
        changeset_ref="HEAD",
        original=[OriginalRequirement(0, "FR-001", "the system shall X", "requirements/a.md")],
        speclift=[SpecLiftItem(0, "requirement", "WHEN Y SHALL X.", _anchor(), quota="behaviour")],
        declared_gaps=["original_source: absent"],
        source_provenance={"original": "absent", "speclift": "speclift-output"},
    )
    assert bundle_from_dict(bundle_to_dict(bundle)) == bundle


def test_adjudication_round_trip():
    adj = Adjudication(
        changeset_ref="HEAD",
        groups=[
            AlignedGroup(0, [0], Level.ALTA, VerdictKind.SODDISFATTO, Level.ALTA),
            AlignedGroup(
                1, [], Level.MEDIA, VerdictKind.MANCANTE, Level.BASSA,
                explanation="assente", severity=Level.ALTA, detectability=Level.BASSA,
            ),
        ],
        extras=[ExtraItem(1, VerdictKind.NON_DOCUMENTATO, "di più", Level.BASSA, Level.BASSA, Level.MEDIA)],
        open_questions=["q"],
    )
    assert adjudication_from_dict(adjudication_to_dict(adj)) == adj


def test_report_round_trip():
    rep = AuditReport(
        version="1",
        changeset_ref="HEAD",
        records=[
            AuditRecord(
                verdict=VerdictKind.DRIFTED,
                verdict_confidence=Level.MEDIA,
                anchors=[_anchor()],
                proposed=True,
                speclift_refs=["do_x (src/a.py:1-5)"],
                original_ref="FR-001",
                explanation="diverge",
                alignment_confidence=Level.ALTA,
                risk=RiskScore(Level.ALTA, Level.BASSA, Level.ALTA),
                notes=["n"],
            )
        ],
        matrix=Matrix(
            counts={"SODDISFATTO": 0, "PARZIALE": 0, "MANCANTE": 0, "DRIFTED": 1, "NON_DOCUMENTATO": 0},
            records_by_verdict={"DRIFTED": ["FR-001"]},
        ),
        declared_gaps=[],
        open_questions=[],
    )
    assert report_from_dict(report_to_dict(rep)) == rep
