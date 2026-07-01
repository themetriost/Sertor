"""Unit tests for `render_custom_agent`'s `model` parameter (E2-FEAT-015, contract C2).

Pure/offline, kit-level (where the function is defined) — complements the package-level
guard suites in `sertor`'s tests.
"""
from __future__ import annotations

from sertor_install_kit.surfaces import render_custom_agent, split_frontmatter

_ASSET_WITH_CLAUDE_ALIAS = (
    "---\nname: x\ndescription: y\ntools: z\nmodel: haiku\n---\n\npersona body\n"
)


def _model_value(front: str) -> str | None:
    for line in front.splitlines():
        if line.strip().startswith("model:"):
            return line.split(":", 1)[1].strip()
    return None


def test_r6_omits_model_by_default():
    front = split_frontmatter(render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS))[0]
    assert _model_value(front) is None


def test_r7_substitutes_policy_model_over_canonical_alias():
    front = split_frontmatter(
        render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS, model="claude-haiku-4.5")
    )[0]
    assert _model_value(front) == "claude-haiku-4.5"


def test_r8_no_bare_claude_alias_leak_even_though_id_contains_substring():
    """A policy id like `claude-haiku-4.5` legitimately CONTAINS the substring `haiku` — the
    anti-pattern is a BARE alias (`haiku`/`sonnet`/`opus`), not the substring (research DA-D-3).
    """
    front = split_frontmatter(
        render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS, model="claude-haiku-4.5")
    )[0]
    value = _model_value(front)
    assert value not in {"haiku", "sonnet", "opus"}
    assert value is not None and "haiku" in value  # sanity: substring IS present, by design


def test_r9_persona_identity_preserved_with_model():
    rendered = render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS, model="claude-haiku-4.5")
    front, body = split_frontmatter(rendered)
    assert "name: x" in front
    assert "description: y" in front
    assert "tools: z" in front
    assert body.strip() == "persona body"


def test_model_none_matches_pre_feat015_omission_byte_for_byte():
    """Anti-drift on the signature change: `model=None` (new default) omits identically to the
    pre-FEAT-015 `include_model=False` behaviour."""
    front_explicit = split_frontmatter(render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS, model=None))[0]
    front_default = split_frontmatter(render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS))[0]
    assert front_explicit == front_default
    assert "model:" not in front_default
