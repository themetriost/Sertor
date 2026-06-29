"""Guard C: RAG hook dogfood copies stay byte-identical to the bundled canon (E10-FEAT-019, D-5).

`python -m sertor_installer.sync` only covers `assets/claude/**` → the three RAG hooks
(`memory-capture`, `rag-freshness`, `version-check`) live under `assets/rag/hooks/` and have NO sync
guard. Their dogfood copies in `.claude/hooks/` must be propagated by HAND after editing the canon;
this guard makes a forgotten copy a CI error (the drift the existing `test_assets_sync.py` cannot
see). `wiki-pending-check` (under `assets/claude/`) is already covered by the root sync guard.

Offline (stdlib `pathlib` only): byte comparison.
"""
from __future__ import annotations

import pathlib

import pytest

# tests/unit/ → tests → repo root
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

_RAG_HOOKS_IN_SCOPE = ("memory-capture.ps1", "rag-freshness.ps1", "version-check.ps1")


@pytest.mark.parametrize("name", _RAG_HOOKS_IN_SCOPE)
def test_rag_hook_dogfood_sync(name: str):
    """Each bundled RAG hook equals its `.claude/hooks/` dogfood copy, byte for byte."""
    bundled = REPO_ROOT / "packages/sertor/src/sertor_installer/assets/rag/hooks" / name
    dogfood = REPO_ROOT / ".claude/hooks" / name
    assert bundled.is_file(), f"missing bundled canon: {bundled}"
    assert dogfood.is_file(), f"missing dogfood copy: {dogfood}"
    assert bundled.read_bytes() == dogfood.read_bytes(), (
        f"Drift: bundled '{name}' != dogfood .claude/hooks/{name}. "
        "Copy the canonical asset by hand (quickstart §6)."
    )
