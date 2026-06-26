"""Guard: hook scripts invoke the CLI the robust, cwd-independent way (E10-FEAT-017, ISSUE-03).

A SessionEnd/Stop hook can be fired by the host from a working directory that is **not** the project
root. A *bare* `uv run sertor-rag …` then resolves the project/venv from the CWD, so it
either picks the wrong project (a parent/sibling `.sertor`) or fails. Being non-fatal,
the failure is silent (the capture/freshness work never happens). The cure, already used by
`wiki-pending-check.ps1` and `rag-freshness.ps1`, is to pin the runtime explicitly:
`uv run --project <root>/.sertor <cli> …` (PATH- and cwd-independent), with a fallback to the CLI
executable inside that venv.

This suite asserts, offline (no `uv`, no network), over the bundled hook assets
(`assets/rag/hooks/*.ps1`):

  - **scoped absence** of any bare `uv run` in CODE — every `uv run` *invocation* MUST be
    followed by `--project`. Comments are stripped first, so prose that merely *mentions* "a bare
    `uv run`" (as these hooks' own docstrings do) is not mistaken for an invocation.

Includes positive/negative meta-tests (incl. a comment mention) so the guard is neither vacuous nor
over-eager.
"""
from __future__ import annotations

import re

from sertor_installer.resources import iter_asset_dir

# `uv run` not immediately followed by `--project`: the banned, cwd-fragile form.
_BARE_UV_RUN = re.compile(r"\buv\s+run\b(?!\s+--project\b)")
# PowerShell block comment `<# … #>` (may span lines).
_BLOCK_COMMENT = re.compile(r"<#.*?#>", re.DOTALL)

_HOOK_DIR = "rag/hooks"


def _hook_assets() -> list[tuple[str, str]]:
    """The bundled RAG hook scripts (rel_path, content) — `.ps1` only."""
    return [(rel, body) for rel, body in iter_asset_dir(_HOOK_DIR) if rel.endswith(".ps1")]


def _code_lines(body: str) -> list[str]:
    """Code only: drop `<# … #>` blocks and whole-line `#` comments, so prose mentioning
    'uv run' is not mistaken for an invocation."""
    without_block = _BLOCK_COMMENT.sub("", body)
    return [ln for ln in without_block.splitlines() if not ln.strip().startswith("#")]


def _bare_uv_run_offenders(body: str) -> list[str]:
    """Code lines carrying a bare `uv run` (not `uv run --project …`)."""
    return [ln.strip() for ln in _code_lines(body) if _BARE_UV_RUN.search(ln)]


def test_hook_assets_have_no_bare_uv_run():
    """No hook script invokes `uv run` without pinning the runtime via `--project`."""
    found = {rel: o for rel, body in _hook_assets() if (o := _bare_uv_run_offenders(body))}
    assert not found, f"bare `uv run` (must be `uv run --project <root>/.sertor …`): {found}"


def test_hook_assets_are_discovered():
    """Sanity: the guard sees the hook scripts it is meant to police (anti-vacuity)."""
    rels = {rel for rel, _ in _hook_assets()}
    assert "memory-capture.ps1" in rels, rels
    assert "rag-freshness.ps1" in rels, rels


# --- meta: the ban is neither vacuous nor over-eager ------------------------------------------


def test_bare_uv_run_regex_catches_a_bare_call():
    """Positive: a bare `uv run sertor-rag …` is flagged (the guard is not vacuous)."""
    assert _bare_uv_run_offenders("    uv run sertor-rag memory archive 2>$null")


def test_bare_uv_run_passes_robust_form_and_comments():
    """Negative: the robust form passes; a comment/prose mention of 'uv run' is NOT flagged."""
    assert not _bare_uv_run_offenders("    uv run --project $runtimeDir sertor-rag memory archive")
    assert not _bare_uv_run_offenders("# never use a bare `uv run` here")
    assert not _bare_uv_run_offenders("<#\n  a bare `uv run` in the docstring\n#>")
