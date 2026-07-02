"""T021/T030/T034/T035/T037/T031a/T040/T042 — assemble: il moat strutturale + scoring + matrice."""

from __future__ import annotations

import pytest

from specaudit.domain.errors import (
    DanglingReferenceError,
    IncompleteAdjudicationError,
    InvalidAdjudicationError,
)
from specaudit.domain.models import (
    Adjudication,
    AlignedGroup,
    Anchor,
    AuditBundle,
    ExtraItem,
    Level,
    OriginalRequirement,
    SpecLiftItem,
    VerdictKind,
)
from specaudit.stages.assemble import assemble


def _bundle(n_orig=2, n_spec=2, spec_status="verified"):
    return AuditBundle(
        version="1",
        changeset_ref="ref",
        original=[OriginalRequirement(i, f"FR-{i}", "t", "p") for i in range(n_orig)],
        speclift=[
            SpecLiftItem(
                i,
                "requirement",
                f"s{i}",
                Anchor(f"f{i}.py", (1 + i, 2 + i), "symbol", spec_status, symbol=f"sym{i}"),
            )
            for i in range(n_spec)
        ],
        declared_gaps=["original_source: present-but-empty"],
        source_provenance={"original": "requirements/", "speclift": "speclift-output"},
    )


def _adj(groups, extras=None, ref="ref"):
    return Adjudication(changeset_ref=ref, groups=groups, extras=extras or [], open_questions=[])


def test_citation_copies_anchors_from_bundle():
    bundle = _bundle(1, 1)
    adj = _adj([AlignedGroup(0, [0], Level.ALTA, VerdictKind.SODDISFATTO, Level.ALTA)])
    records, *_ = assemble(bundle, adj)
    assert records[0].anchors[0] is bundle.speclift[0].anchor  # copiata verbatim dal bundle
    assert records[0].original_ref == "FR-0"
    assert records[0].speclift_refs == ["sym0 (f0.py:1-2)"]


def test_dangling_reference_fails_loud():
    bundle = _bundle(1, 1)
    adj = _adj([AlignedGroup(0, [5], Level.ALTA, VerdictKind.SODDISFATTO, Level.ALTA)])
    with pytest.raises(DanglingReferenceError):
        assemble(bundle, adj)


def test_incomplete_coverage_fails_loud():
    bundle = _bundle(2, 1)
    # copre solo original 0 → original 1 scoperto
    adj = _adj([AlignedGroup(0, [0], Level.ALTA, VerdictKind.SODDISFATTO, Level.ALTA)])
    with pytest.raises(IncompleteAdjudicationError):
        assemble(bundle, adj)


def test_speclift_double_coverage_fails_loud():
    bundle = _bundle(2, 1)
    # speclift 0 in due gruppi
    adj = _adj(
        [
            AlignedGroup(0, [0], Level.ALTA, VerdictKind.SODDISFATTO, Level.ALTA),
            AlignedGroup(1, [0], Level.ALTA, VerdictKind.SODDISFATTO, Level.ALTA),
        ]
    )
    with pytest.raises(IncompleteAdjudicationError):
        assemble(bundle, adj)


def test_non_soddisfatto_requires_explanation():
    bundle = _bundle(1, 1)
    adj = _adj(
        [
            AlignedGroup(
                0, [0], Level.ALTA, VerdictKind.DRIFTED, Level.ALTA,
                severity=Level.ALTA, detectability=Level.BASSA,
            )
        ]
    )
    with pytest.raises(InvalidAdjudicationError):
        assemble(bundle, adj)


def test_drifted_marked_proposed():
    bundle = _bundle(1, 1)
    adj = _adj(
        [
            AlignedGroup(
                0, [0], Level.ALTA, VerdictKind.DRIFTED, Level.ALTA,
                explanation="diverge nella tempistica", severity=Level.ALTA, detectability=Level.BASSA,
            )
        ]
    )
    records, *_ = assemble(bundle, adj)
    assert records[0].proposed is True


def test_missing_group_is_candidato_mancante():
    bundle = _bundle(1, 0)  # un originale, nessun item
    adj = _adj(
        [
            AlignedGroup(
                0, [], Level.MEDIA, VerdictKind.MANCANTE, Level.BASSA,
                explanation="nessun item allineato", severity=Level.ALTA, detectability=Level.BASSA,
            )
        ]
    )
    records, *_ = assemble(bundle, adj)
    assert records[0].verdict == VerdictKind.MANCANTE
    assert records[0].anchors == []
    assert records[0].original_ref == "FR-0"


def test_extra_is_non_documentato():
    bundle = _bundle(0, 1)
    adj = _adj(
        [],
        extras=[ExtraItem(0, VerdictKind.NON_DOCUMENTATO, "di più", Level.BASSA, Level.BASSA, Level.MEDIA)],
    )
    records, *_ = assemble(bundle, adj)
    assert records[0].verdict == VerdictKind.NON_DOCUMENTATO
    assert records[0].original_ref is None
    assert records[0].anchors[0] is bundle.speclift[0].anchor


def test_confidence_guard_clamps_when_alignment_low():
    bundle = _bundle(1, 1)
    adj = _adj(
        [
            AlignedGroup(
                0, [0], Level.BASSA, VerdictKind.DRIFTED, Level.ALTA,
                explanation="diverge", severity=Level.MEDIA, detectability=Level.MEDIA,
            )
        ]
    )
    records, *_ = assemble(bundle, adj)
    assert records[0].verdict_confidence == Level.BASSA
    assert any("ridotta" in n for n in records[0].notes)


def test_risk_scoring_high_when_severe_and_hidden():
    bundle = _bundle(1, 1)
    adj = _adj(
        [
            AlignedGroup(
                0, [0], Level.ALTA, VerdictKind.PARZIALE, Level.ALTA,
                explanation="parziale", severity=Level.ALTA, detectability=Level.BASSA,
            )
        ]
    )
    records, *_ = assemble(bundle, adj)
    assert records[0].risk is not None
    assert records[0].risk.risk == Level.ALTA


def test_soddisfatto_has_no_risk():
    bundle = _bundle(1, 1)
    adj = _adj([AlignedGroup(0, [0], Level.ALTA, VerdictKind.SODDISFATTO, Level.ALTA)])
    records, *_ = assemble(bundle, adj)
    assert records[0].risk is None


def test_non_soddisfatto_without_severity_fails_loud():
    bundle = _bundle(1, 1)
    adj = _adj(
        [AlignedGroup(0, [0], Level.ALTA, VerdictKind.PARZIALE, Level.ALTA, explanation="p")]
    )
    with pytest.raises(InvalidAdjudicationError):
        assemble(bundle, adj)


def test_matrix_counts_and_traceability():
    bundle = _bundle(2, 2)
    adj = _adj(
        [
            AlignedGroup(0, [0], Level.ALTA, VerdictKind.SODDISFATTO, Level.ALTA),
            AlignedGroup(
                1, [1], Level.ALTA, VerdictKind.DRIFTED, Level.ALTA,
                explanation="diverge", severity=Level.ALTA, detectability=Level.BASSA,
            ),
        ]
    )
    records, matrix, gaps, _ = assemble(bundle, adj)
    assert matrix.counts["SODDISFATTO"] == 1
    assert matrix.counts["DRIFTED"] == 1
    assert matrix.records_by_verdict["DRIFTED"] == ["FR-1"]
    # gap del bundle propagato
    assert "original_source: present-but-empty" in gaps
    # ordinamento: DRIFTED (a rischio) prima di SODDISFATTO
    assert records[0].verdict == VerdictKind.DRIFTED


def test_unverified_anchor_noted():
    bundle = _bundle(1, 1, spec_status="unverified")
    adj = _adj([AlignedGroup(0, [0], Level.ALTA, VerdictKind.SODDISFATTO, Level.ALTA)])
    records, *_ = assemble(bundle, adj)
    assert any("non verificata" in n for n in records[0].notes)
