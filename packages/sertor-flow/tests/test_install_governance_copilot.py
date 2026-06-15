"""US2 — Sertor-authored governance surfaces rendered for Copilot (T015, feature 045).

With `specify` mocked (emitting the Copilot layout), `install --assistant copilot` routes the
Sertor-authored agents to `.github/agents/*.agent.md`, the `requirements` skill to
`.github/prompts/*.prompt.md`, the SDLC block to `.github/copilot-instructions.md` (marker,
idempotent), and the constitution-starter identical to Claude (FR-007/008/009).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_flow.install_governance import (
    MARKER_END_SDLC,
    MARKER_START_SDLC,
    execute_governance_plan,
)
from sertor_flow.profile import build_governance_profile
from tests.conftest import FakeSpecifyRunner


@pytest.fixture()
def installed_copilot(tmp_path: Path) -> Path:
    profile = build_governance_profile(tmp_path, assistant="copilot")
    report = execute_governance_plan(profile, runner=FakeSpecifyRunner())
    assert report.exit_code() == 0
    return tmp_path


def test_requirements_analyst_is_custom_agent(installed_copilot: Path):
    assert (installed_copilot / ".github/agents/requirements-analyst.agent.md").exists()


def test_configuration_manager_is_custom_agent(installed_copilot: Path):
    assert (installed_copilot / ".github/agents/configuration-manager.agent.md").exists()


def test_requirements_skill_is_prompt_file(installed_copilot: Path):
    assert (installed_copilot / ".github/prompts/requirements.prompt.md").exists()


def test_no_claude_dir_for_sertor_authored(installed_copilot: Path):
    """Copilot install does not write Sertor-authored agents/skill under `.claude/`."""
    assert not (installed_copilot / ".claude/agents/requirements-analyst.md").exists()
    assert not (installed_copilot / ".claude/skills/requirements/SKILL.md").exists()


def test_sdlc_block_in_copilot_instructions(installed_copilot: Path):
    instructions = installed_copilot / ".github/copilot-instructions.md"
    assert instructions.exists()
    text = instructions.read_text(encoding="utf-8")
    assert MARKER_START_SDLC in text
    assert MARKER_END_SDLC in text


def test_sdlc_block_idempotent_on_rerun(tmp_path: Path):
    profile = build_governance_profile(tmp_path, assistant="copilot")
    execute_governance_plan(profile, runner=FakeSpecifyRunner())
    execute_governance_plan(profile, runner=FakeSpecifyRunner())
    text = (tmp_path / ".github/copilot-instructions.md").read_text(encoding="utf-8")
    assert text.count(MARKER_START_SDLC) == 1


def test_constitution_identical_to_claude(tmp_path: Path):
    """The constitution-starter is assistant-agnostic: identical bytes for both (FR-009)."""
    claude_root = tmp_path / "claude"
    copilot_root = tmp_path / "copilot"
    claude_root.mkdir()
    copilot_root.mkdir()
    execute_governance_plan(
        build_governance_profile(claude_root, assistant="claude"), runner=FakeSpecifyRunner()
    )
    execute_governance_plan(
        build_governance_profile(copilot_root, assistant="copilot"), runner=FakeSpecifyRunner()
    )
    c_claude = (claude_root / ".specify/memory/constitution.md").read_text(encoding="utf-8")
    c_copilot = (copilot_root / ".specify/memory/constitution.md").read_text(encoding="utf-8")
    assert c_claude == c_copilot


def test_specify_launched_with_copilot(tmp_path: Path):
    """The launch is invoked with `--ai copilot` (SpecKit commands land under `.github/`)."""
    profile = build_governance_profile(tmp_path, assistant="copilot")
    runner = FakeSpecifyRunner()
    execute_governance_plan(profile, runner=runner)
    cmd, _ = runner.calls[0]
    assert "--ai" in cmd and "copilot" in cmd
    assert (tmp_path / ".github/prompts/speckit.specify.prompt.md").exists()


def test_copilot_agent_body_reused_from_canonical(installed_copilot: Path):
    """The rendered custom-agent body equals the canonical Claude agent body (anti-drift)."""
    from sertor_install_kit import read_asset_text, split_frontmatter

    rendered = (
        installed_copilot / ".github/agents/requirements-analyst.agent.md"
    ).read_text(encoding="utf-8")
    canonical = read_asset_text("sertor_flow", "claude/agents/requirements-analyst.md")
    assert split_frontmatter(rendered)[1].strip() == split_frontmatter(canonical)[1].strip()
