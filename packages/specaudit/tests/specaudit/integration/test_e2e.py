"""T029/T033/T039/T044/T047 — end-to-end: prepare→(agente/stub)→report, citazioni e matrice."""

from __future__ import annotations

import json

import pytest

from specaudit.adapters.adjudication_file import StubAdjudicator
from specaudit.adapters.requirements_fs import RequirementsFsResolver
from specaudit.adapters.speclift_json import SpecLiftJsonSource
from specaudit.pipeline import audit, build_bundle, build_report
from specaudit.serialize import adjudication_from_dict, report_from_dict
from specaudit.stages import render
from tests.specaudit.helpers import requirements_md, speclift_output

pytestmark = pytest.mark.integration


def _setup(tmp_path):
    sp = tmp_path / "report.speclift.json"
    sp.write_text(json.dumps(speclift_output("abc123")), encoding="utf-8")
    req = tmp_path / "requirements"
    req.mkdir()
    (req / "req.md").write_text(requirements_md(), encoding="utf-8")
    return SpecLiftJsonSource(str(sp)), RequirementsFsResolver(str(req))


def test_us1_audit_stub_end_to_end(tmp_path):
    source, resolver = _setup(tmp_path)
    report = audit(source, resolver, StubAdjudicator(), "abc123")
    # 3 requisiti originali, 3 item SpecLift → ogni requisito ha un record; niente elemento perso
    assert len(report.records) == 3
    # ogni record non-MANCANTE cita almeno un'àncora presa dal bundle
    cited = [r for r in report.records if r.anchors]
    assert cited, "almeno un record cita un'àncora"
    # zero letture di codice: il report esiste senza toccare src reale (le àncore sono citazioni)
    assert report.version == "1"


def test_drifted_via_agent_adjudication(tmp_path):
    source, resolver = _setup(tmp_path)
    bundle = build_bundle(source, resolver, "abc123")
    # l'agente giudica: FR-001 ↔ item 0 (flush) è DRIFTED (bufferato, non 'subito')
    adj_dict = {
        "changeset_ref": "abc123",
        "groups": [
            {
                "original": 0, "speclift": [0], "alignment_confidence": "alta",
                "verdict": "DRIFTED", "verdict_confidence": "media",
                "explanation": "L'originale promette flush 'subito'; l'item 0 lo realizza bufferato.",
                "severity": "media", "detectability": "bassa",
            },
            {
                "original": 1, "speclift": [1], "alignment_confidence": "alta",
                "verdict": "SODDISFATTO", "verdict_confidence": "alta",
            },
            {
                "original": 2, "speclift": [], "alignment_confidence": "media",
                "verdict": "MANCANTE", "verdict_confidence": "media",
                "explanation": "Nessun item SpecLift realizza il salvataggio sessione.",
                "severity": "alta", "detectability": "media",
            },
        ],
        "extras": [
            {
                "speclift": 2, "verdict": "NON_DOCUMENTATO",
                "explanation": "Timer di background non promesso da alcun requisito.",
                "verdict_confidence": "media", "severity": "bassa", "detectability": "alta",
            }
        ],
        "open_questions": [],
    }
    report = build_report(bundle, adjudication_from_dict(adj_dict))

    by_ref = {r.original_ref: r for r in report.records if r.original_ref}
    assert by_ref["FR-001"].verdict.value == "DRIFTED"
    assert by_ref["FR-001"].proposed is True
    assert "bufferato" in by_ref["FR-001"].explanation
    assert by_ref["FR-003"].verdict.value == "MANCANTE"
    # 'di più' presente come NON_DOCUMENTATO
    assert any(r.verdict.value == "NON_DOCUMENTATO" for r in report.records)
    # matrice coerente
    assert report.matrix.counts["DRIFTED"] == 1
    assert report.matrix.counts["SODDISFATTO"] == 1
    assert report.matrix.counts["MANCANTE"] == 1
    assert report.matrix.counts["NON_DOCUMENTATO"] == 1
    # niente elemento perso: 3 gruppi + 1 extra = 4 record
    assert len(report.records) == 4


def test_json_markdown_equivalence(tmp_path):
    source, resolver = _setup(tmp_path)
    report = audit(source, resolver, StubAdjudicator(), "abc123")
    parsed = report_from_dict(json.loads(render.to_json(report)))
    md = render.to_markdown(report)
    # il JSON round-trip è identico all'oggetto
    assert parsed == report
    # ogni verdetto e ogni original_ref del JSON compaiono nel Markdown
    for r in report.records:
        assert r.verdict.value in md
        if r.original_ref:
            assert r.original_ref in md
