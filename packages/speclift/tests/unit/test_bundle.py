"""T019 — bundle: costruisce un EvidenceBundle schema-valido e autoconsistente."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from speclift.domain.models import Anchor, EvidenceItem, Hunk, Symbol, TestRef
from speclift.serialize import bundle_to_dict
from speclift.stages.bundle import build_bundle

_CONTRACTS = Path(__file__).resolve().parents[2] / "specs" / "001-speclift-mvp" / "contracts"


@pytest.fixture
def bundle_validator():
    schema = json.loads((_CONTRACTS / "evidence-bundle.schema.json").read_text("utf-8"))
    registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    return Draft202012Validator(schema, registry=registry)


def _item():
    hunk = Hunk("calc.py", (5, 0), (5, 2), lines=["+def multiply():"], candidate_identifiers=["multiply"])
    anchor = Anchor(
        file="calc.py", lines=(5, 6), granularity="symbol", status="unverified", symbol="multiply",
        test=TestRef(name="test_calc", path="test_calc.py", covers_symbol="multiply"),
    )
    return EvidenceItem(
        hunk=hunk,
        anchor=anchor,
        granularity_used="symbol",
        symbols=[Symbol(name="multiply", path="calc.py", line=0)],
        tests=[TestRef(name="test_calc", path="test_calc.py", covers_symbol="multiply")],
    )


def test_bundle_is_schema_valid(bundle_validator):
    bundle = build_bundle("HEAD", [_item()], [])
    bundle_validator.validate(bundle_to_dict(bundle))


def test_bundle_carries_version_and_ref():
    bundle = build_bundle("main..HEAD", [], [])
    assert bundle.version == "1"
    assert bundle.changeset_ref == "main..HEAD"


def test_unresolved_hunks_are_schema_valid(bundle_validator):
    hunk = Hunk("x.py", (1, 1), (1, 0))
    bundle = build_bundle("HEAD", [], [hunk])
    bundle_validator.validate(bundle_to_dict(bundle))
