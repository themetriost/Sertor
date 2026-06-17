"""Suite di validità-schema offline del frontmatter Copilot (FEAT-011, US7 / gruppo G / SC-007).

Prompt-file con chiave `agent:` (mai `mode:`), custom-agent senza `model:`, e COMMAND su CLI mai
solo-prompt-file. Per ogni difetto dell'audit un test anti-pattern che fallisce se reintrodotto.
Tutto OFFLINE: render in-memory + ispezione dei piani/artefatti su `tmp_path`.
"""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.assistant import AssistantId
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_wiki import build_install_plan, execute_plan
from sertor_installer.surfaces import (
    render_custom_agent,
    render_prompt_file,
    split_frontmatter,
)

_PROMPT_ASSET = "---\nmode: agent\n---\n\nthe body\n"
_AGENT_ASSET = "---\nname: x\ndescription: y\ntools: a, b\nmodel: haiku\n---\n\npersona\n"


# --- prompt-file: agent: not mode: (F1 / SC-006) ----------------------------------------------


def test_prompt_file_has_agent_key():
    front = split_frontmatter(render_prompt_file(_PROMPT_ASSET))[0]
    assert "agent:" in front


def test_anti_pattern_prompt_file_never_uses_mode():
    """SC-007: a prompt-file rendered by the kit never carries the invalid `mode:` key."""
    front = split_frontmatter(render_prompt_file(_PROMPT_ASSET))[0]
    assert "mode:" not in front


def test_prompt_body_verbatim():
    rendered = render_prompt_file(_PROMPT_ASSET)
    assert split_frontmatter(rendered)[1].strip() == "the body"


# --- custom-agent: no model: (A1 / SC-005) ----------------------------------------------------


def test_custom_agent_has_no_model():
    front = split_frontmatter(render_custom_agent(_AGENT_ASSET))[0]
    assert "model:" not in front


def test_anti_pattern_custom_agent_drops_claude_model():
    """SC-007: an asset carrying `model: haiku` → the rendered custom-agent has no `model:`."""
    rendered = render_custom_agent(_AGENT_ASSET)
    front = split_frontmatter(rendered)[0]
    assert "model:" not in front
    assert "haiku" not in front


def test_custom_agent_preserves_identity():
    front = split_frontmatter(render_custom_agent(_AGENT_ASSET))[0]
    assert "name: x" in front
    assert "description: y" in front
    assert "tools: a, b" in front


def test_custom_agent_include_model_opt_in_for_completeness():
    """The omission is a caller decision: `include_model=True` would keep it (Claude path n/a)."""
    front = split_frontmatter(render_custom_agent(_AGENT_ASSET, include_model=True))[0]
    assert "model: haiku" in front


# --- custom-agent: a description with a colon must be YAML-quoted (regression 2026-06-17) -------

_AGENT_ASSET_COLON = (
    "---\nname: wiki\n"
    "description: Consolidates work: record/distill/lint (operations)\n"
    "tools: a, b\n---\n\npersona\n"
)


def test_custom_agent_description_with_colon_is_quoted():
    """A `description` containing ': ' must be emitted as a quoted scalar. Unquoted, Copilot rejects
    the whole frontmatter ("mapping values are not allowed", Copilot CLI 1.0.63) and the agent is
    silently dropped (wiki/log/2026-06-17)."""
    front = split_frontmatter(render_custom_agent(_AGENT_ASSET_COLON))[0]
    assert 'description: "Consolidates work: record/distill/lint (operations)"' in front


def _frontmatter_values_are_yaml_safe(front: str) -> bool:
    """True if no flat `key: value` line carries an UNQUOTED ': ' in its value (which would parse as
    a nested mapping). Mirrors the Copilot frontmatter constraint without a YAML dependency."""
    for line in front.splitlines():
        if not line or line.startswith((" ", "\t")) or ":" not in line:
            continue
        _key, _, value = line.partition(":")
        value = value.strip()
        if value[:1] in ('"', "'", "[", "{"):
            continue
        if ": " in value or value.endswith(":"):
            return False
    return True


def test_real_cli_agents_have_yaml_safe_frontmatter(tmp_path: Path):
    """SC-007 (real-asset guard): every custom-agent the CLI install actually writes must have
    YAML-safe frontmatter. This would have caught the `wiki-author` defect of 2026-06-17 (its
    canonical description contains a colon)."""
    profile = build_host_profile(tmp_path)
    plan = build_install_plan(AssistantId.COPILOT_CLI)
    execute_plan(plan, profile, AssistantId.COPILOT_CLI)
    for name in ("wiki", "wiki-author", "wiki-curator"):
        agent = tmp_path / f".github/agents/{name}.agent.md"
        front = split_frontmatter(agent.read_text(encoding="utf-8"))[0]
        assert _frontmatter_values_are_yaml_safe(front), f"{name}.agent.md unsafe frontmatter:\n{front}"


# --- COMMAND on CLI is a custom-agent, never only a prompt-file (C1/C3 / SC-004) ---------------


def test_cli_wiki_command_is_agent_not_prompt(tmp_path: Path):
    profile = build_host_profile(tmp_path)
    plan = build_install_plan(AssistantId.COPILOT_CLI)
    execute_plan(plan, profile, AssistantId.COPILOT_CLI)
    assert (tmp_path / ".github/agents/wiki.agent.md").is_file()
    assert not (tmp_path / ".github/prompts/wiki.prompt.md").exists()


def test_anti_pattern_cli_plan_has_no_command_only_prompt_file():
    """SC-007 scenario 5: in the CLI plan no COMMAND target is a `.prompt.md` (must be `.agent.md`).

    The COMMAND surfaces (`wiki`, `wiki-author`) are derived from the canonical command/skill
    assets; on the CLI their plan targets must be custom-agents. Reintroducing a prompt-file target
    for a COMMAND on the CLI would make this fail.
    """
    plan = build_install_plan(AssistantId.COPILOT_CLI)
    command_targets = [
        a.target_rel for a in plan
        if a.target_rel.startswith(".github/")
        and (a.target_rel.endswith(".prompt.md") or a.target_rel.endswith(".agent.md"))
    ]
    # the wiki + wiki-author COMMANDs resolve to .agent.md on the CLI
    assert ".github/agents/wiki.agent.md" in command_targets
    assert ".github/agents/wiki-author.agent.md" in command_targets
    # no COMMAND prompt-file on the CLI plan
    assert not any(t.startswith(".github/prompts/") for t in command_targets)
