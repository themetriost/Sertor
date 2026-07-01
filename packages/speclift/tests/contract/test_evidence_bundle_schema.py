"""T009 — contract: lo schema evidence-bundle accetta un bundle valido e rifiuta uno invalido."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract


def _valid_bundle() -> dict:
    return {
        "version": "1",
        "changeset_ref": "HEAD",
        "items": [
            {
                "hunk": {
                    "file_path": "src/app.py",
                    "old_range": [10, 3],
                    "new_range": [10, 5],
                    "candidate_identifiers": ["do_thing"],
                },
                "symbols": [
                    {"name": "do_thing", "path": "src/app.py", "line": 10, "kind": "function"}
                ],
                "tests": [
                    {
                        "name": "test_do_thing",
                        "path": "tests/test_app.py",
                        "covers_symbol": "do_thing",
                        "line": 4,
                    }
                ],
                "anchor": {
                    "file": "src/app.py",
                    "lines": [10, 14],
                    "symbol": "do_thing",
                    "granularity": "symbol",
                    "status": "verified",
                },
                "granularity_used": "symbol",
            }
        ],
        "unresolved": [],
    }


def test_valid_bundle_accepted(bundle_validator):
    bundle_validator.validate(_valid_bundle())


def test_missing_required_field_rejected(bundle_validator):
    bad = _valid_bundle()
    del bad["changeset_ref"]
    assert bundle_validator.iter_errors(bad), "manca changeset_ref → deve essere rifiutato"


def test_bad_granularity_rejected(bundle_validator):
    bad = _valid_bundle()
    bad["items"][0]["granularity_used"] = "module"  # non in enum
    assert list(bundle_validator.iter_errors(bad))


def test_additional_property_rejected(bundle_validator):
    bad = _valid_bundle()
    bad["surprise"] = True  # additionalProperties: false
    assert list(bundle_validator.iter_errors(bad))
