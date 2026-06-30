"""Guard: distributed skill assets keep a clean, host-agnostic style (E10-FEAT-022).

The skill bodies are operating context handed to the host agent. Emphatic ALL-CAPS, orphan
wikilinks that resolve to nothing on the host, and rules duplicated between an inline step and a
trailing "What NOT to do" section are noise that this guard prevents from creeping back in. It
checks forma only (CS-1/CS-2/CS-4/CS-5) — the load-bearing rules are pinned, so a rewrite that
drops a rule fails loud.

Offline, no network, no `uv`:
  - `test_no_emphatic_allcaps`  (CS-1): zero `[A-Z]{4,}` outside code spans/fenced blocks and the
    allowlist of legitimate acronyms/keywords.
  - `test_no_orphan_wikilink`   (CS-4): no bare `[[` outside code spans (the didactic
    `` `[[page]]` `` examples stay in code spans).
  - `test_eval_skills_use_pointer` (US5/CS-2): the eval skills point to `sertor-cli-reference.md`
    and no longer carry the expanded inline "How to invoke" callout.
  - `test_semantic_pins`        (FR-012/CS-5): every load-bearing substring survives the cleanup.
  - meta tests: the ALL-CAPS and wikilink guards are non-vacuous.
"""
from __future__ import annotations

import re

import pytest

from sertor_installer.resources import read_asset_text

_IN_SCOPE = (
    "rag/skills/guided-setup/SKILL.md",
    "rag/skills/eval-suite-author/SKILL.md",
    "rag/skills/eval-feedback/SKILL.md",
    "claude/skills/wiki-author/wiki-playbook.md",
)
_ALLOW = frozenset({
    "RAG", "CLI", "MCP", "API", "JSON", "JSONL", "YAML", "TOML",
    "URL", "NL", "POSIX", "HTTP", "SDLC", "MRR", "STOP", "PASS", "FAIL", "PATH",
})
_EVAL = (
    "rag/skills/eval-suite-author/SKILL.md",
    "rag/skills/eval-feedback/SKILL.md",
)


def _strip_code(text: str) -> str:
    """Remove fenced blocks and inline spans before the ALL-CAPS grep (guard-contract G1)."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    return text


@pytest.mark.parametrize("asset", _IN_SCOPE)
def test_no_emphatic_allcaps(asset):
    """CS-1: zero emphatic ALL-CAPS (>=4 letters) outside the allowlist and code spans."""
    body = read_asset_text(asset)
    found = {m for m in re.findall(r"\b[A-Z]{4,}\b", _strip_code(body))} - _ALLOW
    assert not found, f"{asset}: residual emphatic ALL-CAPS: {sorted(found)}"


@pytest.mark.parametrize("asset", _IN_SCOPE)
def test_no_orphan_wikilink(asset):
    """CS-4: zero orphan wikilinks (no '[[' outside code spans) in the distributed assets."""
    body = read_asset_text(asset)
    assert "[[" not in _strip_code(body), (
        f"{asset}: contains an orphan wikilink outside a code span"
    )


@pytest.mark.parametrize("asset", _EVAL)
def test_eval_skills_use_pointer(asset):
    """US5/CS-2: the eval skills cite the reference and drop the expanded inline callout."""
    body = read_asset_text(asset)
    assert "`sertor-cli-reference.md`" in body, (
        f"{asset}: missing the pointer to sertor-cli-reference.md"
    )
    # The original callout carried this distinctive sentence — it must be gone:
    assert "is not on `PATH`. Invoke it via" not in body, (
        f"{asset}: still carries the expanded inline callout (must be a pointer)"
    )


_PINS: dict[str, list[str]] = {
    "rag/skills/guided-setup/SKILL.md": [
        "import the core", "build_*", "through a vehicle", "--assistant",
        "explicit confirmation", "configure --set", "never print", "green", "propose",
    ],
    "rag/skills/eval-suite-author/SKILL.md": [
        "import the core", "eval add-case", "approval", "validate-path",
        "graph-eval", "secrets", "sertor-cli-reference.md",
    ],
    "rag/skills/eval-feedback/SKILL.md": [
        "core library", "eval add-case", "explicit", "automatic mode",
        "secrets", "sertor-cli-reference.md",
    ],
    "claude/skills/wiki-author/wiki-playbook.md": [
        "wiki.config.toml", "sertor-wiki-tools", "append-log",
        "parity guard", "## Contents",
    ],
}


@pytest.mark.parametrize("asset,pins", list(_PINS.items()))
def test_semantic_pins(asset, pins):
    """FR-012/CS-5: every load-bearing pin is present in the body after the cleanup."""
    body = read_asset_text(asset)
    missing = [pin for pin in pins if pin not in body]
    assert not missing, f"{asset}: missing semantic pins: {missing}"


def test_guard_catches_reintroduced_allcaps():
    """Meta: the ALL-CAPS guard is non-vacuous (MANDATORY is not in the allowlist)."""
    assert {"MANDATORY"} - _ALLOW != set(), (
        "Guard bug: MANDATORY should not be in the allowlist"
    )


def test_guard_catches_reintroduced_wikilink():
    """Meta: the wikilink guard is non-vacuous."""
    assert "[[" in _strip_code("see [[x]] here"), (
        "Bug: _strip_code dropped a wikilink that is outside a code span"
    )
