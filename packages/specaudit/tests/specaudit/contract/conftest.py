"""Helper per i contract test SpecAudit: carica gli schemi con risoluzione dei `$ref` incrociati."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "specs" / "002-specaudit-mvp" / "contracts"


def _load(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


def _registry() -> Registry:
    bundle = _load("audit-bundle.schema.json")
    adjudication = _load("adjudication.schema.json")
    output = _load("output.schema.json")
    return Registry().with_resources(
        [
            (bundle["$id"], Resource.from_contents(bundle)),
            (adjudication["$id"], Resource.from_contents(adjudication)),
            (output["$id"], Resource.from_contents(output)),
            # alias relativo usato nei $ref di output.schema.json
            ("audit-bundle.schema.json", Resource.from_contents(bundle)),
        ]
    )


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(_load(name), registry=_registry())


@pytest.fixture
def bundle_validator() -> Draft202012Validator:
    return _validator("audit-bundle.schema.json")


@pytest.fixture
def adjudication_validator() -> Draft202012Validator:
    return _validator("adjudication.schema.json")


@pytest.fixture
def output_validator() -> Draft202012Validator:
    return _validator("output.schema.json")
