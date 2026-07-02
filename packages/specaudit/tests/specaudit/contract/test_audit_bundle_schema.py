"""T009 — contract: lo schema audit-bundle accetta un bundle valido e rifiuta uno invalido."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract


def _valid_bundle() -> dict:
    return {
        "version": "1",
        "changeset_ref": "HEAD",
        "original": [
            {"index": 0, "id": "FR-001", "text": "the system shall X", "provenance": "requirements/a.md"}
        ],
        "speclift": [
            {
                "index": 0,
                "origin": "requirement",
                "quota": "behaviour",
                "statement": "WHEN Y the system SHALL X.",
                "anchor": {
                    "file": "src/a.py",
                    "lines": [1, 5],
                    "symbol": "do_x",
                    "test": None,
                    "granularity": "symbol",
                    "status": "verified",
                },
            }
        ],
        "declared_gaps": [],
        "source_provenance": {"original": "requirements/", "speclift": "speclift-output"},
    }


def test_valid_bundle_accepted(bundle_validator):
    bundle_validator.validate(_valid_bundle())


def test_missing_source_provenance_rejected(bundle_validator):
    bad = _valid_bundle()
    del bad["source_provenance"]
    assert list(bundle_validator.iter_errors(bad))


def test_bad_granularity_rejected(bundle_validator):
    bad = _valid_bundle()
    bad["speclift"][0]["anchor"]["granularity"] = "line"
    assert list(bundle_validator.iter_errors(bad))
