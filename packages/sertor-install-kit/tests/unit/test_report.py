"""Tests for `InstallReport` (T009): required capability (F4), render_json name (F1), counts."""
from __future__ import annotations

import json

from sertor_install_kit.artifacts import ArtifactOutcome, Outcome
from sertor_install_kit.report import InstallReport


def test_capability_is_required_and_in_title():
    report = InstallReport(target="/tmp/x", capability="governance")
    assert "governance" in report.render_human()


def test_render_json_method_name_preserved():
    """F1: the JSON method is `render_json()` (not `to_json()`)."""
    report = InstallReport(target="/tmp/x", capability="wiki")
    assert hasattr(report, "render_json")
    assert not hasattr(report, "to_json")


def test_counts_and_failed_step():
    report = InstallReport(target="/tmp/x", capability="rag")
    report.add(ArtifactOutcome("a", Outcome.CREATED))
    report.add(ArtifactOutcome("b", Outcome.SKIPPED))
    report.add(ArtifactOutcome("c", Outcome.MERGED))
    report.add(ArtifactOutcome("d", Outcome.BLOCK))
    report.add(ArtifactOutcome("e", Outcome.ERROR, "boom"))
    assert report.created == 1
    assert report.skipped == 1
    assert report.merged == 1
    assert report.block == 1
    assert report.errors == 1
    assert report.failed_step == "e"
    assert report.exit_code() == 1


def test_render_json_schema():
    report = InstallReport(target="/tmp/x", capability="governance")
    report.add(ArtifactOutcome("a", Outcome.CREATED))
    payload = json.loads(report.render_json())
    assert payload["schema"] == "install.report/1"
    assert payload["target"] == "/tmp/x"
    assert payload["summary"]["created"] == 1
    assert payload["outcomes"][0]["target_rel"] == "a"
