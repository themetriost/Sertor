"""T011 — contract: lo schema output accetta un report valido e rifiuta uno invalido."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract


def _anchor() -> dict:
    return {
        "file": "src/a.py",
        "lines": [1, 5],
        "symbol": "do_x",
        "test": None,
        "granularity": "symbol",
        "status": "verified",
    }


def _valid_report() -> dict:
    return {
        "version": "1",
        "changeset_ref": "HEAD",
        "records": [
            {
                "original_ref": "FR-001",
                "speclift_refs": ["do_x (src/a.py:1-5)"],
                "verdict": "DRIFTED",
                "explanation": "diverge nella tempistica",
                "verdict_confidence": "media",
                "alignment_confidence": "alta",
                "anchors": [_anchor()],
                "risk": {"severity": "alta", "detectability": "bassa", "risk": "alta"},
                "proposed": True,
                "notes": [],
            },
            {
                "original_ref": "FR-002",
                "speclift_refs": ["do_y (src/b.py:2-3)"],
                "verdict": "SODDISFATTO",
                "explanation": None,
                "verdict_confidence": "alta",
                "alignment_confidence": "alta",
                "anchors": [_anchor()],
                "risk": None,
                "proposed": False,
                "notes": [],
            },
        ],
        "matrix": {
            "counts": {"SODDISFATTO": 1, "PARZIALE": 0, "MANCANTE": 0, "DRIFTED": 1, "NON_DOCUMENTATO": 0},
            "records_by_verdict": {"DRIFTED": ["FR-001"], "SODDISFATTO": ["FR-002"]},
        },
        "declared_gaps": [],
        "open_questions": [],
    }


def test_valid_report_accepted(output_validator):
    output_validator.validate(_valid_report())


def test_bad_verdict_rejected(output_validator):
    bad = _valid_report()
    bad["records"][0]["verdict"] = "OK"
    assert list(output_validator.iter_errors(bad))


def test_missing_matrix_counts_rejected(output_validator):
    bad = _valid_report()
    del bad["matrix"]["counts"]["DRIFTED"]
    assert list(output_validator.iter_errors(bad))


def test_missing_proposed_rejected(output_validator):
    bad = _valid_report()
    del bad["records"][0]["proposed"]
    assert list(output_validator.iter_errors(bad))
