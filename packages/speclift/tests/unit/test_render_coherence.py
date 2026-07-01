"""T039 — US4: la vista Markdown deriva dal JSON; equivalenza biunivoca di requisiti e àncore."""

from __future__ import annotations

import json
import re

from speclift.domain.models import (
    Anchor,
    DriftFlag,
    EarsRequirement,
    Quota,
    SpecLiftReport,
    TestRef,
)
from speclift.stages.render import render_json, render_markdown


def _report():
    a1 = Anchor(file="calc.py", lines=(5, 6), granularity="symbol", symbol="multiply",
                test=TestRef(name="t", path="test_calc.py", covers_symbol="multiply"))
    a2 = Anchor(file="util.py", lines=(1, 3), granularity="hunk")
    return SpecLiftReport(
        version="1",
        changeset_ref="HEAD",
        requirements=[
            EarsRequirement(id="REQ-A", quota=Quota.IMPLEMENTATION, statement="impl", anchor=a1),
            EarsRequirement(id="REQ-B", quota=Quota.BEHAVIOUR, statement="beh", anchor=a2),
        ],
        drifts=[DriftFlag(description="uncovered", anchor=a2)],
    )


def _md_requirement_ids(md: str) -> set[str]:
    return set(re.findall(r"^## (REQ-\S+) ·", md, flags=re.MULTILINE))


def _md_anchor_labels(md: str) -> set[str]:
    return set(re.findall(r"\*\*Àncora\*\*: `([^`]+)`", md))


def test_markdown_requirement_ids_match_json():
    report = _report()
    md = render_markdown(report)
    payload = json.loads(render_json(report))
    json_ids = {r["id"] for r in payload["requirements"]}
    assert _md_requirement_ids(md) == json_ids


def test_markdown_anchors_match_json():
    report = _report()
    md = render_markdown(report)
    payload = json.loads(render_json(report))
    json_anchor_files = {r["anchor"]["file"] for r in payload["requirements"]}
    md_files = {label.split(":")[0] for label in _md_anchor_labels(md)}
    assert md_files == json_anchor_files


def test_no_extra_requirements_in_markdown():
    report = _report()
    md = render_markdown(report)
    # zero divergenze: esattamente i requisiti del report, niente in più.
    assert len(_md_requirement_ids(md)) == len(report.requirements)
