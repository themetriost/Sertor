"""Per-assistant rendering of FILE surfaces from a SINGLE canonical source (feature 044, US2/US3).

Anti-drift (REQ-021, Principio III/VI): the *content* of a command/skill (`/wiki`, `wiki-author`),
of the agent persona (`wiki-curator`) and of the instruction block has ONE source — the existing
`assets/claude/**` (and `assets/*.md`) used by Claude. The Copilot artifacts are **derived** from
that source by translating only the *container* (the frontmatter / file naming), never by keeping a
second hand-maintained copy. A guard test (`test_assets_copilot_guard.py`) fails on divergence.

Pure functions (stdlib-only): they take the canonical text and produce the rendered text. The body
below the frontmatter is preserved verbatim, so the shared substrate cannot drift.
"""
from __future__ import annotations

_FRONTMATTER_FENCE = "---"


def split_frontmatter(text: str) -> tuple[str, str]:
    """Splits a Markdown asset into `(frontmatter, body)`.

    Frontmatter is the leading `---`-fenced block (YAML). If absent, returns `("", text)`. The body
    is everything after the closing fence, kept byte-for-byte (the shared substrate).
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return "", text
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONTMATTER_FENCE:
            frontmatter = "".join(lines[1:i])
            body = "".join(lines[i + 1 :])
            return frontmatter, body
    # malformed (no closing fence) → treat all as body, no frontmatter
    return "", text


def render_prompt_file(canonical_text: str) -> str:
    """Renders a Copilot prompt-file (`*.prompt.md`) from the canonical command/skill asset.

    Copilot prompt-files use a minimal frontmatter (`mode: agent`); the instructional **body** is
    the shared substrate, reused verbatim from the Claude command/skill (anti-drift).
    """
    _front, body = split_frontmatter(canonical_text)
    header = f"{_FRONTMATTER_FENCE}\nmode: agent\n{_FRONTMATTER_FENCE}\n\n"
    return header + body.lstrip("\n")


def render_custom_agent(canonical_text: str) -> str:
    """Renders a Copilot custom-agent (`*.agent.md`) from the canonical agent asset.

    The persona **body** is the shared substrate (reused verbatim); the frontmatter is translated to
    the Copilot custom-agent shape (`name`/`description`/`tools` preserved when present).
    """
    front, body = split_frontmatter(canonical_text)
    fields = _parse_simple_frontmatter(front)
    lines = [_FRONTMATTER_FENCE]
    for key in ("name", "description", "tools", "model"):
        if key in fields:
            lines.append(f"{key}: {fields[key]}")
    lines.append(_FRONTMATTER_FENCE)
    lines.append("")
    return "\n".join(lines) + "\n" + body.lstrip("\n")


def _parse_simple_frontmatter(front: str) -> dict[str, str]:
    """Parses flat `key: value` lines of a frontmatter (no nesting needed for our assets)."""
    fields: dict[str, str] = {}
    for line in front.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields
