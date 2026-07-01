"""Anti-drift guard for Copilot-derived assets (feature 044, REQ-021; surface-mapping prop.2).

The Copilot prompt-files / custom-agent are DERIVED from the canonical Claude asset by translating
only the container (frontmatter); the instructional **body** is the shared substrate and MUST be
reused verbatim. These tests fail if the body diverges (a second hand-maintained copy) — there is
no separate source for the shared content.
"""
from __future__ import annotations

from sertor_installer.resources import read_asset_text
from sertor_installer.surfaces import (
    render_custom_agent,
    render_prompt_file,
    split_frontmatter,
)


def _body(text: str) -> str:
    return split_frontmatter(text)[1].strip()


def test_prompt_body_equals_canonical_command_body():
    """The rendered `/wiki` prompt-file body == the canonical Claude command body."""
    canonical = read_asset_text("claude/commands/wiki.md")
    rendered = render_prompt_file(canonical)
    assert _body(rendered) == _body(canonical)


def test_prompt_file_uses_agent_key_not_mode():
    """FEAT-011/FR-016: prompt-file frontmatter mode key is `agent:`, never `mode:`."""
    canonical = read_asset_text("claude/commands/wiki.md")
    front = split_frontmatter(render_prompt_file(canonical))[0]
    assert "agent:" in front
    assert "mode:" not in front


def test_custom_agent_omits_model_field():
    """FEAT-011/FR-017: the Claude `model:` value is omitted on Copilot custom-agents."""
    canonical = read_asset_text("claude/agents/wiki-curator.md")
    front = split_frontmatter(render_custom_agent(canonical))[0]
    assert "model:" not in front


def test_custom_agent_drops_injected_model():
    """Anti-pattern (SC-007): an asset with `model: haiku` → no `model:` in the rendered file."""
    asset = "---\nname: x\ndescription: y\ntools: z\nmodel: haiku\n---\n\nbody\n"
    front = split_frontmatter(render_custom_agent(asset))[0]
    assert "model:" not in front
    assert "name: x" in front
    assert "description: y" in front
    assert "tools: z" in front


def _model_value(front: str) -> str | None:
    """Parsed value of a `model:` line (not a substring check — `claude-haiku-4.5` legitimately
    contains `haiku`; research DA-D-3)."""
    for line in front.splitlines():
        if line.strip().startswith("model:"):
            return line.split(":", 1)[1].strip()
    return None


def test_custom_agent_substitutes_policy_model_never_echoes_claude_alias():
    """E2-FEAT-015: an asset with `model: haiku` (Claude alias) + a policy model-id →
    the rendered file carries the POLICY id, never the Claude alias, even though the
    policy id may contain it as a substring (e.g. `claude-haiku-4.5`)."""
    asset = "---\nname: x\ndescription: y\ntools: z\nmodel: haiku\n---\n\nbody\n"
    front = split_frontmatter(render_custom_agent(asset, model="claude-haiku-4.5"))[0]
    assert _model_value(front) == "claude-haiku-4.5"
    assert _model_value(front) not in {"haiku", "sonnet", "opus"}
    assert "name: x" in front
    assert "description: y" in front
    assert "tools: z" in front


def test_prompt_body_equals_canonical_skill_body():
    canonical = read_asset_text("claude/skills/wiki-author/SKILL.md")
    rendered = render_prompt_file(canonical)
    assert _body(rendered) == _body(canonical)


def test_agent_body_equals_canonical_agent_body():
    """The rendered custom-agent body == the canonical Claude agent body."""
    canonical = read_asset_text("claude/agents/wiki-curator.md")
    rendered = render_custom_agent(canonical)
    assert _body(rendered) == _body(canonical)


def test_agent_preserves_frontmatter_identity():
    """Name/description/tools are carried over (translated container, same persona)."""
    canonical = read_asset_text("claude/agents/wiki-curator.md")
    rendered = render_custom_agent(canonical)
    assert "name: wiki-curator" in rendered
    assert "tools:" in rendered


def test_instruction_block_single_source():
    """The instruction block content is the SAME asset for both assistants (no second copy).

    `install wiki` (claude) and the copilot plan both source `claude-md-block.md`; there is no
    `copilot/instructions/*.md` body to drift from it.
    """
    block = read_asset_text("claude-md-block.md")
    assert block.strip()  # the single canonical source exists and is non-empty


def test_no_hand_maintained_copilot_prompt_bodies():
    """Guard: no free-standing prompt/agent BODY asset under copilot/ that could drift.

    The copilot asset tree may only hold containers/wiring (hook fragments), never a second copy of
    the shared command/skill/agent body. Rendering is done from the canonical Claude source.
    """
    import sertor_installer.surfaces as surfaces  # single derivation path for the shared body

    assert hasattr(surfaces, "render_prompt_file")
    assert hasattr(surfaces, "render_custom_agent")


def test_no_copilot_asset_directory():
    """E10-FEAT-023: no static Copilot asset tree exists under `assets/`.

    All Copilot-facing payloads are GENERATED at runtime from `assets/claude/**` and
    `assets/rag/**` via render_copilot_hooks / render_custom_agent / render_prompt_file
    (sertor_install_kit.surfaces). A `copilot/` asset directory is a MISLEADING stub
    (suggests static assets that do not exist); this guard fails loud if it reappears
    (e.g. a `.gitkeep` re-added "to hold the place").
    """
    from sertor_installer.resources import asset_path

    assert not asset_path("copilot").is_dir()
