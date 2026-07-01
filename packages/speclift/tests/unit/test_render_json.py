"""T027 — render JSON conforme a output.schema.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from speclift.domain.models import (
    Anchor,
    DriftFlag,
    EarsRequirement,
    ExcludedRequirement,
    Quota,
    SpecLiftReport,
)
from speclift.stages.render import render_json, render_markdown

_CONTRACTS = Path(__file__).resolve().parents[2] / "specs" / "001-speclift-mvp" / "contracts"


@pytest.fixture
def output_validator():
    bundle = json.loads((_CONTRACTS / "evidence-bundle.schema.json").read_text("utf-8"))
    output = json.loads((_CONTRACTS / "output.schema.json").read_text("utf-8"))
    registry = Registry().with_resources(
        [
            (bundle["$id"], Resource.from_contents(bundle)),
            ("evidence-bundle.schema.json", Resource.from_contents(bundle)),
            (output["$id"], Resource.from_contents(output)),
        ]
    )
    return Draft202012Validator(output, registry=registry)


def _report():
    anchor = Anchor(file="calc.py", lines=(5, 6), granularity="symbol", symbol="multiply")
    return SpecLiftReport(
        version="1",
        changeset_ref="HEAD",
        requirements=[
            EarsRequirement(id="REQ-000", quota=Quota.IMPLEMENTATION, statement="s", anchor=anchor)
        ],
        drifts=[DriftFlag(description="d", anchor=anchor)],
        excluded=[ExcludedRequirement(statement="x", reason="r")],
        open_questions=["q"],
    )


def test_render_json_is_schema_valid(output_validator):
    payload = json.loads(render_json(_report()))
    output_validator.validate(payload)


def test_render_json_quota_is_lower_snake():
    payload = json.loads(render_json(_report()))
    assert payload["requirements"][0]["quota"] == "implementation"


def test_render_json_is_deterministic():
    assert render_json(_report()) == render_json(_report())


def test_render_markdown_mentions_requirement_and_anchor():
    md = render_markdown(_report())
    assert "REQ-000" in md
    assert "calc.py:5-6" in md
    assert "multiply" in md


def test_drift_is_distinct_from_requirements_json_and_md():
    report = _report()
    payload = json.loads(render_json(report))
    # JSON: drift in un array separato dai requisiti.
    assert "drifts" in payload and "requirements" in payload
    assert payload["drifts"][0]["status"] == "proposed"
    drift_descrs = {d["description"] for d in payload["drifts"]}
    req_statements = {r["statement"] for r in payload["requirements"]}
    assert drift_descrs.isdisjoint(req_statements)
    # Markdown: sezione dedicata e marcatura "proposed".
    md = render_markdown(report)
    assert "Drift proposti" in md
    assert "_(proposed)_" in md
