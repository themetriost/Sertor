"""US3 — fail-fast no-rollback di `sertor-flow install` (T042, FR-019).

Quando un passo del piano fallisce con un `InstallerError`, l'esecuzione si ferma:
il `failed_step` è nominato nel report, l'exit code è 1, e gli artefatti già
depositati PRIMA del passo fallito restano in posto (no rollback).
"""
from __future__ import annotations

from pathlib import Path

import sertor_flow.install_governance as ig
from sertor_flow.install_governance import execute_governance_plan
from sertor_flow.profile import build_governance_profile
from sertor_install_kit import InstallerError
from tests.conftest import FakeSpecifyRunner


def test_fail_fast_stops_and_names_failed_step(tmp_path: Path, monkeypatch):
    """A failing step (constitution apply) aborts; failed_step is named, prior files remain."""

    def _boom(target_root: Path, art):  # noqa: ANN001
        raise InstallerError("simulated write failure (destination not writable)")

    # The constitution starter is applied AFTER the launch (SpecKit) and the Sertor-authored
    # agents, so failing it proves both fail-fast (stop) and no-rollback (prior files remain).
    monkeypatch.setattr(ig, "_apply_config", _boom)

    profile = build_governance_profile(tmp_path)
    report = execute_governance_plan(profile, runner=FakeSpecifyRunner())

    assert report.exit_code() == 1
    assert report.errors == 1
    assert report.failed_step == ig._CONSTITUTION_TARGET
    # No-rollback: artifacts written before the failing step survive on disk.
    assert (tmp_path / ".claude/skills/speckit-specify/SKILL.md").exists()  # from launch
    assert (tmp_path / ".specify/templates/plan-template.md").exists()  # from launch
    assert (tmp_path / ".claude/agents/requirements-analyst.md").exists()  # Sertor-authored
    # The failing step and everything after it were NOT applied.
    assert not (tmp_path / "CLAUDE.md").exists()


def test_launch_failure_aborts_before_any_surface(tmp_path: Path):
    """If the SpecKit launch fails, no Sertor-authored surface is applied (no partial state)."""
    profile = build_governance_profile(tmp_path)
    runner = FakeSpecifyRunner(returncode=1)  # `specify init` fails
    report = execute_governance_plan(profile, runner=runner)

    assert report.exit_code() == 1
    assert report.errors == 1
    assert "speckit launch" in report.failed_step.lower()
    # Nothing from the plan was applied.
    assert not (tmp_path / ".claude/agents/requirements-analyst.md").exists()
    assert not (tmp_path / ".specify/memory/constitution.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_cli_returns_1_on_failed_step(tmp_path: Path, monkeypatch, capsys):
    """The CLI surfaces the failure: exit 1 and the failed step in the human report."""
    from sertor_flow.__main__ import main

    def _boom(target_root: Path, art):  # noqa: ANN001
        raise InstallerError("simulated write failure")

    monkeypatch.setattr(ig, "_apply_config", _boom)
    rc = main(["install", "--target", str(tmp_path)], runner=FakeSpecifyRunner())
    assert rc == 1
    out = capsys.readouterr().out
    assert ig._CONSTITUTION_TARGET in out
