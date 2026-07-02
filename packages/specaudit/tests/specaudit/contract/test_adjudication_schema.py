"""T010 — contract: lo schema adjudication accetta un'adjudication valida e rifiuta una invalida."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract


def _valid_adjudication() -> dict:
    return {
        "changeset_ref": "HEAD",
        "groups": [
            {
                "original": 0,
                "speclift": [0],
                "alignment_confidence": "alta",
                "verdict": "SODDISFATTO",
                "verdict_confidence": "alta",
            },
            {
                "original": 1,
                "speclift": [],
                "alignment_confidence": "media",
                "verdict": "MANCANTE",
                "verdict_confidence": "bassa",
                "explanation": "nessun item allineato",
                "severity": "alta",
                "detectability": "bassa",
            },
        ],
        "extras": [
            {
                "speclift": 1,
                "verdict": "NON_DOCUMENTATO",
                "explanation": "comportamento non promesso",
                "verdict_confidence": "media",
                "severity": "media",
                "detectability": "media",
            }
        ],
        "open_questions": [],
    }


def test_valid_adjudication_accepted(adjudication_validator):
    adjudication_validator.validate(_valid_adjudication())


def test_bad_verdict_rejected(adjudication_validator):
    bad = _valid_adjudication()
    bad["groups"][0]["verdict"] = "OK"
    assert list(adjudication_validator.iter_errors(bad))


def test_bad_level_rejected(adjudication_validator):
    bad = _valid_adjudication()
    bad["groups"][0]["alignment_confidence"] = "high"
    assert list(adjudication_validator.iter_errors(bad))


def test_extra_requires_explanation(adjudication_validator):
    bad = _valid_adjudication()
    del bad["extras"][0]["explanation"]
    assert list(adjudication_validator.iter_errors(bad))
