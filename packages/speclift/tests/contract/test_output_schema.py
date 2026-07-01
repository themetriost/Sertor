"""T010 — contract: lo schema output accetta un report valido e rifiuta uno invalido."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract


def _valid_report() -> dict:
    anchor = {
        "file": "src/app.py",
        "lines": [10, 14],
        "symbol": "do_thing",
        "granularity": "symbol",
        "status": "verified",
    }
    return {
        "version": "1",
        "changeset_ref": "HEAD",
        "requirements": [
            {
                "id": "REQ-001",
                "quota": "implementation",
                "statement": "When X, the system shall Y.",
                "anchor": anchor,
                "source_item": "item-0",
            }
        ],
        "drifts": [
            {"description": "comportamento non coperto", "anchor": anchor, "status": "proposed"}
        ],
        "excluded": [{"statement": "req scartato", "reason": "àncora non verificabile"}],
        "open_questions": ["stesura EARS demandata a Sertor"],
    }


def test_valid_report_accepted(output_validator):
    output_validator.validate(_valid_report())


def test_bad_quota_rejected(output_validator):
    bad = _valid_report()
    bad["requirements"][0]["quota"] = "USER_CAPABILITY"  # deve essere lower_snake
    assert list(output_validator.iter_errors(bad))


def test_drift_status_must_be_proposed(output_validator):
    bad = _valid_report()
    bad["drifts"][0]["status"] = "confirmed"  # const: proposed
    assert list(output_validator.iter_errors(bad))


def test_missing_open_questions_rejected(output_validator):
    bad = _valid_report()
    del bad["open_questions"]
    assert list(output_validator.iter_errors(bad))
