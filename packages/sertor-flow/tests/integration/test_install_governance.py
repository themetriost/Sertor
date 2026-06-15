"""Integration test for governance install end-to-end (T009, feature 045).

After the launch-installer pivot, SpecKit is obtained by launching `specify init` (mocked here via a
fake `CommandRunner` that emits the Claude layout — NO network). This is the non-regression gate
(FR-012/SC-003): with the mock emitting the Claude layout, `install --assistant claude` produces
governance functionally equivalent to before (Sertor-authored surfaces, constitution, init files,
SDLC block), now plus the `.specify/**`/commands deposited by the launch.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_flow.install_governance import execute_governance_plan
from sertor_flow.profile import build_governance_profile


@pytest.fixture()
def installed(tmp_path: Path, fake_runner) -> Path:
    """Runs governance install on a clean repo with `specify` mocked; returns the target."""
    profile = build_governance_profile(tmp_path, assistant="claude")
    report = execute_governance_plan(profile, runner=fake_runner)
    assert report.exit_code() == 0
    return tmp_path


def test_install_deposits_speckit_command_via_launch(installed: Path):
    """SpecKit commands come from the (mocked) launch, not from a vendored asset."""
    assert (installed / ".claude/commands/speckit.specify.md").exists()


def test_install_deposits_requirements_analyst_agent(installed: Path):
    assert (installed / ".claude/agents/requirements-analyst.md").exists()


def test_install_deposits_configuration_manager_agent(installed: Path):
    assert (installed / ".claude/agents/configuration-manager.md").exists()


def test_install_deposits_requirements_skill(installed: Path):
    assert (installed / ".claude/skills/requirements/SKILL.md").exists()


def test_install_deposits_specify_templates_via_launch(installed: Path):
    """`.specify/**` is deposited by the launch, not vendored."""
    assert (installed / ".specify/templates/plan-template.md").exists()


def test_install_ships_both_shells_via_launch(installed: Path):
    assert (installed / ".specify/scripts/bash/check-prerequisites.sh").exists()
    assert (installed / ".specify/scripts/powershell/check-prerequisites.ps1").exists()


def test_install_deposits_constitution_starter(installed: Path):
    constitution = installed / ".specify/memory/constitution.md"
    assert constitution.exists()
    assert "Constitution" in constitution.read_text(encoding="utf-8")


def test_install_inserts_sdlc_block_in_claude_md(installed: Path):
    claude_md = installed / "CLAUDE.md"
    assert claude_md.exists()
    text = claude_md.read_text(encoding="utf-8")
    assert "<!-- SERTOR:SDLC-RITUAL START -->" in text
    assert "<!-- SERTOR:SDLC-RITUAL END -->" in text


def test_install_generates_init_options(installed: Path):
    import json

    init = installed / ".specify/init-options.json"
    assert init.exists()
    data = json.loads(init.read_text(encoding="utf-8"))
    assert data["integration"] == "claude"


def test_install_does_not_deposit_feature_json(installed: Path):
    """`.specify/feature.json` is runtime state, never installed (DA-e)."""
    assert not (installed / ".specify/feature.json").exists()


def test_install_does_not_run_any_phase(installed: Path):
    """install != run: no SDLC/git/index side effect (FR-003)."""
    assert not (installed / ".git").exists()
    assert not (installed / "specs").exists()
    assert not (installed / ".sertor").exists()


def test_install_report_assistant_and_created(tmp_path: Path, fake_runner):
    """The report records the target assistant and contains created outcomes."""
    profile = build_governance_profile(tmp_path, assistant="claude")
    report = execute_governance_plan(profile, runner=fake_runner)
    assert report.assistant == "claude"
    assert report.created > 0
    payload = report.render_json()
    import json

    data = json.loads(payload)
    assert data["assistant"] == "claude"


def test_idempotent_rerun_skips(tmp_path: Path):
    """Re-running the install on the same repo skips everything (idempotency)."""
    from tests.conftest import FakeSpecifyRunner

    profile = build_governance_profile(tmp_path, assistant="claude")
    execute_governance_plan(profile, runner=FakeSpecifyRunner())
    report2 = execute_governance_plan(profile, runner=FakeSpecifyRunner())
    assert report2.exit_code() == 0
    assert report2.created == 0
