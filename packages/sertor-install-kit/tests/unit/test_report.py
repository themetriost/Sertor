"""Tests for `InstallReport` (T009): required capability (F4), render_json name (F1), counts."""
from __future__ import annotations

import json

from sertor_install_kit.artifacts import ArtifactOutcome, LifecycleOp, Outcome
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


# --- feature 048: extended report (updated/removed, verb title) ---------------------------------


def test_install_report_zero_updated_removed_retrocompat():
    """A plain install report carries 0 for the two new counters (NFR-06)."""
    report = InstallReport(target="/tmp/x", capability="rag")
    report.add(ArtifactOutcome("a", Outcome.CREATED))
    payload = json.loads(report.render_json())
    assert payload["schema"] == "install.report/1"
    summary = payload["summary"]
    assert set(summary.keys()) == {
        "created", "skipped", "merged", "block", "updated", "removed", "errors"
    }
    assert summary["updated"] == 0
    assert summary["removed"] == 0


def test_add_updated_and_removed_increment_counters():
    report = InstallReport(target="/tmp/x", capability="rag")
    report.add(ArtifactOutcome("a", Outcome.UPDATED))
    report.add(ArtifactOutcome("b", Outcome.UPDATED))
    report.add(ArtifactOutcome("c", Outcome.REMOVED))
    assert report.updated == 2
    assert report.removed == 1
    assert report.exit_code() == 0  # removals/updates are not errors


def test_render_human_and_json_with_updated_removed():
    report = InstallReport(
        target="/tmp/x", capability="rag", op=LifecycleOp.UPGRADE, updated=2, removed=1
    )
    human = report.render_human()
    assert "sertor upgrade rag" in human
    assert "2 updated" in human
    assert "1 removed" in human

    payload = json.loads(report.render_json())
    assert payload["summary"]["updated"] == 2
    assert payload["summary"]["removed"] == 1


def test_uninstall_title_reflects_verb():
    report = InstallReport(target="/tmp/x", capability="wiki", op=LifecycleOp.UNINSTALL)
    assert report.render_human().startswith("sertor uninstall wiki")
