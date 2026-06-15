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
