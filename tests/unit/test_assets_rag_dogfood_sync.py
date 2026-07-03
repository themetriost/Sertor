"""Guard: byte-fidelity of the RAG byte-copied file assets dogfood↔bundle (E15-FEAT-002).

Replaces the former fixed 3-hook list. Enumerates **every** byte-copied RAG file asset
(`assets/rag/{hooks,skills,agents}/**`) via the same asset API the sync uses, and asserts its
dogfood copy under `.claude/{hooks,skills,agents}/` is byte-identical (modulo the documented
`uv run` allowlist). Exhaustive & **auto-derived**: a new byte-copied RAG asset is covered without
editing this file (the old 3-hook list left `sertor-rag-usage-check`, the `-start` hooks,
`guided-setup`, `concierge` unguarded — the silent drift this closes).

The **non-byte** RAG assets (env/mcp/settings templates, marker blocks, the `.sertor/`-dest
`sertor-cli-reference.md`) are NOT here — they are merged/generated/marker-deposited at install
(process-fidelity, E15-FEAT-001). `assets/claude/**` stays covered by `test_assets_sync.py`.

Offline (stdlib + the installer's asset API): normalized-text comparison.
"""
from __future__ import annotations

import pathlib

import pytest

from sertor_installer.resources import iter_asset_dir

# tests/unit/ → tests → repo root
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# Byte-copied RAG subtree → dogfood dest (mirror of `sertor_installer.sync._BYTE_MAPPING` minus
# `claude`, which `test_assets_sync.py` owns). Enumerating subtrees keeps the boundary robust.
_RAG_BYTE_MAPPING = (
    ("rag/hooks", ".claude/hooks"),
    ("rag/skills", ".claude/skills"),
    ("rag/agents", ".claude/agents"),
)


def _normalize(text: str) -> str:
    """Neutralize the permitted allowlist difference (dev may reintroduce `uv run`)."""
    return text.replace("uv run sertor-wiki-tools", "sertor-wiki-tools")


def _cases() -> list[tuple[str, pathlib.Path, str]]:
    cases: list[tuple[str, pathlib.Path, str]] = []
    for subtree, dest_rel in _RAG_BYTE_MAPPING:
        for rel_path, content in iter_asset_dir(subtree):
            label = f"{subtree}/{rel_path}"
            dogfood = REPO_ROOT / dest_rel / rel_path
            cases.append((label, dogfood, content))
    return cases


_CASES = _cases()


def test_rag_byte_assets_enumerated():
    """Sanity: the asset API yields RAG byte assets (guards against a vacuous parametrization)."""
    assert _CASES, "no RAG byte-copied assets enumerated — asset API/anchor broken?"


@pytest.mark.parametrize("label,dogfood,content", _CASES, ids=[c[0] for c in _CASES])
def test_rag_byte_asset_dogfood_sync(label: str, dogfood: pathlib.Path, content: str):
    assert dogfood.is_file(), (
        f"missing dogfood copy for byte asset '{label}' at {dogfood.relative_to(REPO_ROOT)}. "
        "Run `uv run python -m sertor_installer.sync`."
    )
    assert _normalize(dogfood.read_text(encoding="utf-8")) == _normalize(content), (
        f"Drift: bundled '{label}' != dogfood {dogfood.relative_to(REPO_ROOT)}. "
        "Run `uv run python -m sertor_installer.sync` to realign."
    )
