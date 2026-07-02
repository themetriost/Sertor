"""T023/T045 — render: JSON round-trip valido + coerenza JSON↔Markdown (SC-006)."""

from __future__ import annotations

import json

from specaudit.domain.models import (
    Anchor,
    AuditRecord,
    AuditReport,
    Level,
    Matrix,
    RiskScore,
    VerdictKind,
)
from specaudit.serialize import report_from_dict
from specaudit.stages import render


def _report():
    a = Anchor("src/a.py", (1, 5), "symbol", "verified", symbol="do_x")
    records = [
        AuditRecord(
            verdict=VerdictKind.DRIFTED,
            verdict_confidence=Level.MEDIA,
            anchors=[a],
            proposed=True,
            speclift_refs=["do_x (src/a.py:1-5)"],
            original_ref="FR-001",
            explanation="diverge nella tempistica",
            alignment_confidence=Level.ALTA,
            risk=RiskScore(Level.ALTA, Level.BASSA, Level.ALTA),
            notes=[],
        ),
        AuditRecord(
            verdict=VerdictKind.SODDISFATTO,
            verdict_confidence=Level.ALTA,
            anchors=[a],
            proposed=False,
            speclift_refs=["do_x (src/a.py:1-5)"],
            original_ref="FR-002",
            explanation=None,
            alignment_confidence=Level.ALTA,
            risk=None,
            notes=[],
        ),
    ]
    return AuditReport(
        version="1",
        changeset_ref="HEAD",
        records=records,
        matrix=Matrix(
            counts={"SODDISFATTO": 1, "PARZIALE": 0, "MANCANTE": 0, "DRIFTED": 1, "NON_DOCUMENTATO": 0},
            records_by_verdict={"DRIFTED": ["FR-001"], "SODDISFATTO": ["FR-002"]},
        ),
        declared_gaps=["original_source: present-but-empty"],
        open_questions=[],
    )


def test_json_round_trips():
    rep = _report()
    parsed = json.loads(render.to_json(rep))
    assert report_from_dict(parsed) == rep


def test_markdown_contains_verdicts_and_citations():
    rep = _report()
    md = render.to_markdown(rep)
    assert "DRIFTED" in md
    assert "SODDISFATTO" in md
    assert "FR-001" in md
    assert "src/a.py:1-5" in md
    assert "_(proposto)_" in md  # DRIFTED marcato proposto


def test_markdown_matches_json_verdict_set():
    rep = _report()
    parsed = json.loads(render.to_json(rep))
    md = render.to_markdown(rep)
    for rec in parsed["records"]:
        # ogni verdetto del JSON compare nel Markdown (coerenza SC-006)
        ref = rec["original_ref"] or ""
        assert rec["verdict"] in md
        if ref:
            assert ref in md


def test_gaps_surfaced_in_markdown():
    rep = _report()
    md = render.to_markdown(rep)
    assert "original_source: present-but-empty" in md
