"""US2/US3 — Sertor-authored governance surfaces rendered for Copilot CLI (FEAT-012).

With `specify` mocked (emitting the Copilot layout), `install --assistant copilot-cli` routes the
Sertor-authored agents to `.github/agents/*.agent.md`, the `requirements` skill to a custom-agent
`.github/agents/requirements.agent.md` (NOT a prompt-file — the only CLI-invocable form), the SDLC
block to `.github/copilot-instructions.md` (marker, idempotent), and the constitution-starter
identical to Claude (FR-007/008/009). The VS Code (`copilot`) target was removed (FEAT-012).
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
def installed_copilot_cli(tmp_path: Path) -> Path:
    profile = build_governance_profile(tmp_path, assistant="copilot-cli")
    report = execute_governance_plan(profile, runner=FakeSpecifyRunner())
    assert report.exit_code() == 0
    return tmp_path


def test_requirements_analyst_is_custom_agent(installed_copilot_cli: Path):
    assert (installed_copilot_cli / ".github/agents/requirements-analyst.agent.md").exists()


def test_configuration_manager_is_custom_agent(installed_copilot_cli: Path):
    assert (installed_copilot_cli / ".github/agents/configuration-manager.agent.md").exists()


def test_no_claude_dir_for_sertor_authored(installed_copilot_cli: Path):
    """Copilot CLI install does not write Sertor-authored agents/skill under `.claude/`."""
    assert not (installed_copilot_cli / ".claude/agents/requirements-analyst.md").exists()
    assert not (installed_copilot_cli / ".claude/skills/requirements/SKILL.md").exists()


def test_sdlc_block_in_copilot_instructions(installed_copilot_cli: Path):
    instructions = installed_copilot_cli / ".github/copilot-instructions.md"
    assert instructions.exists()
    text = instructions.read_text(encoding="utf-8")
    assert MARKER_START_SDLC in text
    assert MARKER_END_SDLC in text


def test_sdlc_block_idempotent_on_rerun(tmp_path: Path):
    profile = build_governance_profile(tmp_path, assistant="copilot-cli")
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
        build_governance_profile(copilot_root, assistant="copilot-cli"), runner=FakeSpecifyRunner()
    )
    c_claude = (claude_root / ".specify/memory/constitution.md").read_text(encoding="utf-8")
    c_copilot = (copilot_root / ".specify/memory/constitution.md").read_text(encoding="utf-8")
    assert c_claude == c_copilot


def test_specify_launched_with_copilot_cli(tmp_path: Path):
    """FEAT-012 (FR-013, SC-006): with `copilot-cli` the launch passes `--ai copilot` (NOT
    `copilot-cli`) — spec-kit 0.8.18 has no `copilot-cli` (the Copilot layout lands under
    `.github/`)."""
    profile = build_governance_profile(tmp_path, assistant="copilot-cli")
    runner = FakeSpecifyRunner()
    execute_governance_plan(profile, runner=runner)
    cmd, _ = runner.calls[0]
    assert "--ai" in cmd
    assert cmd[cmd.index("--ai") + 1] == "copilot"
    assert "copilot-cli" not in cmd
    assert (tmp_path / ".github/prompts/speckit.specify.prompt.md").exists()


def test_legacy_copilot_rejected_by_sertor_flow(tmp_path: Path, capsys):
    """FEAT-012 (FR-001, SC-001): the legacy VS Code value `copilot` is rejected with exit 2
    (argparse `choices`), and the message names `copilot-cli`."""
    from sertor_flow.__main__ import main

    with pytest.raises(SystemExit) as exc:
        main(["install", "--assistant", "copilot", "--target", str(tmp_path)])
    assert exc.value.code == 2
    assert "copilot-cli" in capsys.readouterr().err


def test_copilot_agent_body_reused_from_canonical(installed_copilot_cli: Path):
    """The rendered custom-agent body equals the canonical Claude agent body (anti-drift)."""
    from sertor_install_kit import read_asset_text, split_frontmatter

    rendered = (
        installed_copilot_cli / ".github/agents/requirements-analyst.agent.md"
    ).read_text(encoding="utf-8")
    canonical = read_asset_text("sertor_flow", "claude/agents/requirements-analyst.md")
    assert split_frontmatter(rendered)[1].strip() == split_frontmatter(canonical)[1].strip()


# --- FEAT-011/FEAT-012: COMMAND on copilot-cli is a custom-agent (FR-009/010/011, SC-003) --------


def test_cli_requirements_command_is_custom_agent(installed_copilot_cli: Path):
    """FR-009/010: on the CLI the `requirements` COMMAND is a custom-agent (CLI-invocable), never a
    bare prompt-file (audit 🔴)."""
    assert (installed_copilot_cli / ".github/agents/requirements.agent.md").exists()
    assert not (installed_copilot_cli / ".github/prompts/requirements.prompt.md").exists()


def test_cli_custom_agent_has_policy_model(installed_copilot_cli: Path):
    """E2-FEAT-015 (was FR-017): the CLI custom-agent for the COMMAND carries the POLICY
    model-id, never the omitted/Claude-alias state of FEAT-011/049."""
    from sertor_install_kit import split_frontmatter
    from sertor_install_kit.model_policy import resolve_model

    text = (installed_copilot_cli / ".github/agents/requirements.agent.md").read_text(
        encoding="utf-8"
    )
    front = split_frontmatter(text)[0]
    assert f"model: {resolve_model('requirements')}" in front


def test_cli_command_body_reused_from_canonical(installed_copilot_cli: Path):
    """Anti-drift (FR-011): the CLI custom-agent body equals the canonical skill body."""
    from sertor_install_kit import read_asset_text, split_frontmatter

    rendered = (
        installed_copilot_cli / ".github/agents/requirements.agent.md"
    ).read_text(encoding="utf-8")
    canonical = read_asset_text("sertor_flow", "claude/skills/requirements/SKILL.md")
    assert split_frontmatter(rendered)[1].strip() == split_frontmatter(canonical)[1].strip()
