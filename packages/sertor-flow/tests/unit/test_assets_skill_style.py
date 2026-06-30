"""Guard: the sertor-flow `requirements` skill keeps a clean style (E10-FEAT-022, G2).

Style-only check on the Italian `requirements/SKILL.md`: no emphatic ALL-CAPS (the lone `SEMPRE`
became `sempre`) outside the allowlist. The language stays Italian (IT->EN is E12, out of scope);
`EARS`/`FEAT`/`REQ` are legitimate requirements-method tokens and are allowlisted. Package-local
read (no cross-package access), like the sertor-flow sync guard.
"""
from __future__ import annotations

import re

from sertor_install_kit import read_asset_text

_ALLOW_FLOW = frozenset({
    "RAG", "CLI", "MCP", "API", "JSON", "JSONL", "YAML", "TOML",
    "URL", "NL", "POSIX", "HTTP", "SDLC", "MRR", "STOP", "PASS", "FAIL", "PATH",
    "EARS", "FEAT", "REQ",  # extended allowlist for sertor-flow (guard-contract G2)
})


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    return text


def test_requirements_no_emphatic_allcaps():
    """CS-1 (A5): zero emphatic ALL-CAPS in requirements/SKILL.md outside the extended allowlist.

    Expected: `SEMPRE` removed -> empty set after strip and allowlist. `EARS` (x6) is allowlisted
    and must not be flagged.
    """
    body = read_asset_text("sertor_flow", "claude/skills/requirements/SKILL.md")
    found = {m for m in re.findall(r"\b[A-Z]{4,}\b", _strip_code(body))} - _ALLOW_FLOW
    assert not found, f"requirements/SKILL.md: residual emphatic ALL-CAPS: {sorted(found)}"
