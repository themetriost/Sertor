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
    Surface,
)
from sertor_install_kit.errors import ConfigError

# ---------------------------------------------------------------- AssistantId

def test_assistant_id_known_values():
    assert AssistantId.from_str("claude") is AssistantId.CLAUDE
    assert AssistantId.from_str("copilot") is AssistantId.COPILOT


def test_assistant_id_default_is_claude():
    # default applied when absent is `claude` (documented, FR-002)
    assert AssistantProfile.DEFAULT is AssistantId.CLAUDE


def test_assistant_id_unknown_raises_config_error():
    with pytest.raises(ConfigError):
        AssistantId.from_str("codex")
    with pytest.raises(ConfigError):
        AssistantId.from_str("bogus")


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


# ---------------------------------------------------------------- copilot mapping

def test_copilot_profile_targets():
    p = AssistantProfile.for_assistant(AssistantId.COPILOT)
    assert p.target_for(Surface.INSTRUCTION_BLOCK).target_rel == ".github/copilot-instructions.md"
    mcp = p.target_for(Surface.MCP_SERVER)
    assert mcp.target_rel == ".vscode/mcp.json"
    assert mcp.root_key == "servers"
    # hooks wiring file under .github/hooks/
    assert p.target_for(Surface.HOOK).target_rel.startswith(".github/hooks/")
    assert p.target_for(Surface.HOOK).target_rel.endswith(".json")


def test_copilot_render_paths_are_github():
    p = AssistantProfile.for_assistant(AssistantId.COPILOT)
    assert p.render_path(Surface.COMMAND, "wiki").endswith(".prompt.md")
    assert p.render_path(Surface.COMMAND, "wiki").startswith(".github/prompts/")
    assert p.render_path(Surface.AGENT, "wiki-curator").startswith(".github/agents/")
    assert p.render_path(Surface.AGENT, "wiki-curator").endswith(".agent.md")


# ------------------------------------------------------------ validity (Principio I / artifacts)

def test_targets_are_relative_no_traversal():
    for aid in (AssistantId.CLAUDE, AssistantId.COPILOT):
        p = AssistantProfile.for_assistant(aid)
        for surface in Surface:
            t = p.target_for(surface)
            if t is None:
                continue
            rel = t.target_rel.replace("\\", "/")
            assert not rel.startswith("/")
            assert ".." not in rel.split("/")
