"""Regression pin: the distributed governance assets are host-agnostic (FEAT-010, Principle X).

`sertor-flow` is independent of the RAG/wiki packages (`test_no_core_dependency`), yet the
distributed agents/skill carried Sertor *project* coupling: the `requirements-analyst` hardcoded
`mcp__sertor-rag__*` tools (present only if the host ALSO installs `sertor install rag`), and the
`configuration-manager` named Sertor's prototype folders as commit-scope examples + framed itself as
a "workspace RAG". A generic host has none of that. These pins fail if such coupling returns.

This is NOT the broad project-coupling guard (out of scope); it targets the specific leaks removed.
Offline, pure asset reads.
"""
from __future__ import annotations

from sertor_install_kit import read_asset_text

_ANCHOR = "sertor_flow"
_GOVERNANCE_BODIES = (
    "claude/agents/configuration-manager.md",
    "claude/agents/requirements-analyst.md",
    "claude/skills/requirements/SKILL.md",
)

# Tokens that couple an asset to the Sertor PROJECT (not to an assistant): the RAG MCP server name,
# Sertor's prototype folder names, and the RAG-workspace framing. None belong in a generic host.
_PROJECT_COUPLING_TOKENS = (
    "mcp__sertor-rag",      # the RAG MCP tools (separate package, not a flow prerequisite)
    "01-baseline",          # Sertor prototype folder used as a commit-scope example
    "02-hybrid-reranking",
    "03-graphrag",
    "workspace RAG",        # Sertor-domain framing
)


def test_governance_assets_have_no_project_coupling():
    offenders: list[str] = []
    for rel in _GOVERNANCE_BODIES:
        text = read_asset_text(_ANCHOR, rel)
        for token in _PROJECT_COUPLING_TOKENS:
            if token in text:
                offenders.append(f"{rel} → {token!r}")
    assert not offenders, f"project-coupling leaked into distributed governance assets: {offenders}"


def test_requirements_analyst_tools_are_universal_only():
    """The agent's `tools:` frontmatter lists only universal tools — no `sertor-rag` MCP (RAG is
    optional, discovered at runtime, never a flow dependency)."""
    front = read_asset_text(_ANCHOR, "claude/agents/requirements-analyst.md").split("---", 2)[1]
    tools_line = next(ln for ln in front.splitlines() if ln.startswith("tools:"))
    assert "mcp__" not in tools_line, f"requirements-analyst hardcodes MCP tools: {tools_line}"


# --- E10-FEAT-021: the SDLC block stays standing-only (no 'How to invoke', DA-D-r3) --------------

_SDLC_BLOCK = "claude-md-block-sdlc.md"


def test_sdlc_block_has_no_invoke_section():
    """G1 twin: the SDLC block carries no 'How to invoke' section (it never did — DA-D-r3).

    The block is standing-directive only (SpecKit phases, constitution gate, error discipline,
    version control). This guard prevents the inline invocation section from creeping back in.
    """
    sdlc_body = read_asset_text(_ANCHOR, _SDLC_BLOCK)
    assert "How to invoke" not in sdlc_body, (
        "claude-md-block-sdlc.md contains 'How to invoke': it must not be present"
    )
    assert "pywin32_bootstrap" not in sdlc_body, (
        "claude-md-block-sdlc.md contains the Windows note: it must not be present"
    )


def test_sdlc_block_preserves_standing_content():
    """C3: the SDLC block keeps its minimal standing content (REQ-016, invariant)."""
    sdlc_body = read_asset_text(_ANCHOR, _SDLC_BLOCK)
    assert "SpecKit" in sdlc_body, "SpecKit phases missing from the SDLC block"
    assert "Constitution Check" in sdlc_body, "Constitution Check missing from the SDLC block"
    assert "fix, don't suppress" in sdlc_body, "Error discipline missing from the SDLC block"
    assert "Version control discipline" in sdlc_body, (
        "Version control discipline missing from the SDLC block"
    )
