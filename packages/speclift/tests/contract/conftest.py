"""Helper per i contract test: carica gli schemi JSON con risoluzione dei `$ref` incrociati."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "specs" / "001-speclift-mvp" / "contracts"


def _load(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


def _registry() -> Registry:
    bundle = _load("evidence-bundle.schema.json")
    output = _load("output.schema.json")
    return Registry().with_resources(
        [
            (bundle["$id"], Resource.from_contents(bundle)),
            (output["$id"], Resource.from_contents(output)),
            # alias relativo usato nei $ref di output.schema.json
            ("evidence-bundle.schema.json", Resource.from_contents(bundle)),
        ]
    )


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(_load(name), registry=_registry())


@pytest.fixture
def bundle_validator() -> Draft202012Validator:
    return _validator("evidence-bundle.schema.json")


@pytest.fixture
def output_validator() -> Draft202012Validator:
    return _validator("output.schema.json")
