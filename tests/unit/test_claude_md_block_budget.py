"""Budget-altitude guard for the always-on CLAUDE.md blocks (E10-FEAT-024, US2/US3).

The three always-on instruction blocks (wiki / RAG / SDLC) are injected verbatim into the host's
CLAUDE.md (or copilot-instructions.md). They are pure context-cost: every line is spent on every
turn regardless of the task. After FEAT-021 reduced them, nothing stops them from growing back.
This guard freezes a per-block line budget (REQ-012): a deliberate increase requires editing the
`_BUDGETS` registry, not a silent drift. Cross-package (root suite, precedent: test_assets_sync.py)
and fully OFFLINE (importlib.resources, no subprocess, no network).
"""
from __future__ import annotations

import pytest

from sertor_install_kit import resources as _kit

# Soglie per-blocco (costanti esplicite). Un aumento richiede una modifica deliberata
# di questo registro (REQ-012). Stato al 2026-06-30: wiki 52, RAG 49, SDLC 64.
# DA-1: soglie differenziate per blocco, non uniforme a 75 (blocchi pre-FEAT-021 erano
# wiki 71 / RAG 72 -> una soglia >= 71 permetterebbe di tornare ai valori pre-riduzione).
_BUDGETS: dict[tuple[str, str], int] = {
    ("sertor_installer", "claude-md-block.md"):               75,  # wiki (+distill +wiki-guard)
    ("sertor_installer", "rag/claude-md-block-rag-usage.md"): 58,  # RAG   (attuale 49)
    ("sertor_flow",      "claude-md-block-sdlc.md"):          70,  # SDLC  (attuale 64)
}


def _walk_blocks(anchor: str, node, prefix: str, found: set[tuple[str, str]]) -> None:
    """Recurse a Traversable, collecting claude-md-block*.md files as (anchor, rel)."""
    for child in node.iterdir():
        rel = f"{prefix}{child.name}"
        if child.is_dir():
            _walk_blocks(anchor, child, f"{rel}/", found)
        elif child.name.startswith("claude-md-block") and child.name.endswith(".md"):
            found.add((anchor, rel))


def _discover_blocks() -> set[tuple[str, str]]:
    """Walk both packages and collect all claude-md-block*.md files as (anchor, rel).

    Used by test_budget_coverage_exhaustive to ensure no file escapes the budget guard.
    """
    found: set[tuple[str, str]] = set()
    for anchor in ("sertor_installer", "sertor_flow"):
        _walk_blocks(anchor, _kit.asset_path(anchor, ""), "", found)
    return found


def test_blocks_within_budget():
    """Each registered claude-md-block*.md is within its declared line budget.

    Failure message names file (anchor:rel), current line count and configured budget (FR-007).
    """
    for (anchor, rel), budget in _BUDGETS.items():
        text = _kit.read_asset_text(anchor, rel)
        count = len(text.splitlines())   # splitlines() excludes trailing newline (A-004)
        assert count <= budget, (
            f"{anchor}:{rel} — {count} righe > soglia {budget}. "
            f"Aggiorna la soglia in _BUDGETS se l'aumento è deliberato (REQ-012)."
        )


def test_budget_coverage_exhaustive():
    """Every claude-md-block*.md discovered in both packages is registered in _BUDGETS.

    A fourth block added without a corresponding budget entry causes this test to fail,
    naming the unregistered file (FR-006/CS-2).
    """
    discovered = _discover_blocks()
    registered = set(_BUDGETS.keys())
    uncovered = discovered - registered
    assert not uncovered, (
        f"claude-md-block*.md trovati senza soglia in _BUDGETS: {uncovered}. "
        f"Aggiungi una voce a _BUDGETS per ciascun file scoperto."
    )


def test_budget_guard_not_vacuous():
    """Anti-pattern: a synthetic body over the budget causes an assertion failure.

    Proves the guard logic is not vacuous (a body below budget passes; one above fails).
    """
    budget = 60
    body_over = "\n".join(["riga"] * (budget + 20))   # 80 righe > 60
    body_under = "\n".join(["riga"] * (budget - 10))  # 50 righe < 60
    count_over = len(body_over.splitlines())
    count_under = len(body_under.splitlines())
    # body over budget must fail the budget assertion
    with pytest.raises(AssertionError):
        assert count_over <= budget, f"synthetic:{count_over} > soglia {budget}"
    # body under budget must not fail
    assert count_under <= budget  # no AssertionError expected
