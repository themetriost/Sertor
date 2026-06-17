"""Tests for the assistant-targeting seam (feature 044, data-model §1/§2/§3).

`AssistantId`/`Surface` enums + `AssistantProfile.target_for(Surface)` resolution for the two
supported assistants. The profile is the ONLY place that knows the per-assistant conventions
(Principio X): the plan-builders ask it, they do not hard-code `.claude/...`.
"""
from __future__ import annotations

import pytest

from sertor_install_kit.assistant import (
    AssistantId,
    AssistantProfile,
    CommandVehicle,
    Surface,
)
from sertor_install_kit.errors import ConfigError

# ---------------------------------------------------------------- AssistantId

def test_assistant_id_known_values():
    # FEAT-012: exactly two targets remain after the VS Code consolidation.
    assert AssistantId.from_str("claude") is AssistantId.CLAUDE
    assert AssistantId.from_str("copilot-cli") is AssistantId.COPILOT_CLI
    assert len(list(AssistantId)) == 2
    assert {a.value for a in AssistantId} == {"claude", "copilot-cli"}


def test_assistant_id_default_is_claude():
    # default applied when absent is `claude` (documented, FR-002)
    assert AssistantProfile.DEFAULT is AssistantId.CLAUDE


def test_assistant_id_unknown_raises_config_error():
    with pytest.raises(ConfigError):
        AssistantId.from_str("codex")
    with pytest.raises(ConfigError):
        AssistantId.from_str("bogus")


def test_copilot_legacy_value_raises():
    """FEAT-012 (FR-001, C1.1, SC-001): the legacy VS Code value `copilot` is gone — `from_str`
    raises and the message names the correct value `copilot-cli`."""
    with pytest.raises(ConfigError) as exc:
        AssistantId.from_str("copilot")
    assert "copilot-cli" in str(exc.value)


# ---------------------------------------------------------------- claude mapping (non-regression)

def test_claude_profile_targets():
    p = AssistantProfile.for_assistant(AssistantId.CLAUDE)
    assert p.target_for(Surface.INSTRUCTION_BLOCK).target_rel == "CLAUDE.md"
    mcp = p.target_for(Surface.MCP_SERVER)
    assert mcp.target_rel == ".mcp.json"
    assert mcp.root_key == "mcpServers"
    assert p.target_for(Surface.HOOK).target_rel == ".claude/settings.json"
    # per-file surfaces map under .claude/
    assert p.render_path(Surface.COMMAND, "commands/wiki.md") == ".claude/commands/wiki.md"
    assert (
        p.render_path(Surface.AGENT, "agents/wiki-curator.md")
        == ".claude/agents/wiki-curator.md"
    )


# ---------------------------------------------------------------- copilot-cli mapping

def test_copilot_cli_mcp_uses_dot_mcp_json_mcpservers():
    # The Copilot CLI does NOT read `.vscode/mcp.json` (`servers`); it reads `.mcp.json` with the
    # `mcpServers` root (the Claude-standard format). This is the whole point of the CLI target.
    p = AssistantProfile.for_assistant(AssistantId.COPILOT_CLI)
    mcp = p.target_for(Surface.MCP_SERVER)
    assert mcp.target_rel == ".mcp.json"
    assert mcp.root_key == "mcpServers"


def test_copilot_cli_profile_mcp_target():
    """FEAT-012 (FR-008, C2.1): for `copilot-cli`, MCP resolves to `.mcp.json`/`mcpServers`."""
    p = AssistantProfile.for_assistant(AssistantId.COPILOT_CLI)
    mcp = p.target_for(Surface.MCP_SERVER)
    assert mcp.target_rel == ".mcp.json"
    assert mcp.root_key == "mcpServers"


def test_copilot_cli_no_vscode_mcp():
    """FEAT-012 (FR-002, SC-004): no `.vscode/**` path exists in the `copilot-cli` profile."""
    p = AssistantProfile.for_assistant(AssistantId.COPILOT_CLI)
    for surface in Surface:
        t = p.target_for(surface)
        if t is None:
            continue
        assert not t.target_rel.replace("\\", "/").startswith(".vscode/")
    assert not p.render_path(Surface.COMMAND, "wiki").startswith(".vscode/")
    assert not p.render_path(Surface.AGENT, "wiki-curator").startswith(".vscode/")


def test_copilot_cli_reuses_github_surfaces():
    p = AssistantProfile.for_assistant(AssistantId.COPILOT_CLI)
    assert p.target_for(Surface.INSTRUCTION_BLOCK).target_rel == ".github/copilot-instructions.md"
    assert p.target_for(Surface.HOOK).target_rel.startswith(".github/hooks/")
    assert p.render_path(Surface.AGENT, "wiki-curator").startswith(".github/agents/")


# ----------------------------------------------- FEAT-011: COMMAND vehicle per target (Q2=c)

def test_command_vehicle_per_target():
    """The COMMAND vehicle is explicit: prompt-file for claude, custom-agent for the CLI."""
    assert (
        AssistantProfile.for_assistant(AssistantId.CLAUDE).command_vehicle
        is CommandVehicle.PROMPT_FILE
    )
    assert (
        AssistantProfile.for_assistant(AssistantId.COPILOT_CLI).command_vehicle
        is CommandVehicle.CUSTOM_AGENT
    )


def test_copilot_cli_command_is_custom_agent_path():
    """FEAT-011: the COMMAND surface on the CLI renders to a custom-agent (`.agent.md`), not a
    prompt-file — a prompt-file is not CLI-invocable (audit 🔴)."""
    p = AssistantProfile.for_assistant(AssistantId.COPILOT_CLI)
    path = p.render_path(Surface.COMMAND, "wiki")
    assert path == ".github/agents/wiki.agent.md"
    assert not path.endswith(".prompt.md")


def test_claude_command_path_unchanged():
    """Non-regression: Claude COMMAND path is byte-for-byte the historical `.claude/<rel>`."""
    p = AssistantProfile.for_assistant(AssistantId.CLAUDE)
    assert p.render_path(Surface.COMMAND, "commands/wiki.md") == ".claude/commands/wiki.md"


def test_claude_profile_invariant_after_refactor():
    """FEAT-012 (C4.1, FR-016, SC-005): the Claude profile is byte-for-byte unchanged by the
    VS Code removal — same command dir, vehicle and MCP target."""
    p = AssistantProfile.for_assistant(AssistantId.CLAUDE)
    assert p._command_dir == ".claude/commands"
    assert p.command_vehicle is CommandVehicle.PROMPT_FILE
    mcp = p.target_for(Surface.MCP_SERVER)
    assert mcp.target_rel == ".mcp.json"
    assert mcp.root_key == "mcpServers"


# ------------------------------------------------------------ validity (Principio I / artifacts)

def test_targets_are_relative_no_traversal():
    for aid in (AssistantId.CLAUDE, AssistantId.COPILOT_CLI):
        p = AssistantProfile.for_assistant(aid)
        for surface in Surface:
            t = p.target_for(surface)
            if t is None:
                continue
            rel = t.target_rel.replace("\\", "/")
            assert not rel.startswith("/")
            assert ".." not in rel.split("/")
