"""Guard for the neutral constitution distribution (FEAT-009, feature 058).

`specify init` scaffolds a spec-kit PLACEHOLDER `.specify/memory/constitution.md`; a plain
create-if-absent then SKIPPED our curated neutral starter forever (the host got the empty
`[PROJECT_NAME]` template). The fix is **replace-if-placeholder**: overwrite the placeholder with
the starter, preserve a real host constitution. These tests pin that behavior + the starter content.
Offline (NFR-04): pure functions + filesystem in tmp, no launch, no network.
"""
from __future__ import annotations

from pathlib import Path

from sertor_flow.install_governance import (
    _ANCHOR,
    _CONSTITUTION_ASSET,
    _CONSTITUTION_TARGET,
    _apply_config,
    _apply_constitution,
    _is_speckit_placeholder,
)
from sertor_install_kit import Artifact, ArtifactKind, Outcome, WriteStrategy, read_asset_text

# The spec-kit placeholder template (what `specify init` deposits) — carries bracketed sentinels.
_PLACEHOLDER = (
    "# [PROJECT_NAME] Constitution\n\n### [PRINCIPLE_1_NAME]\n[PRINCIPLE_1_DESCRIPTION]\n"
    "**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE]\n"
)
# A real, already-personalized host constitution (no template sentinels).
_REAL = "# Acme Constitution\n\n### I. Ship Daily\nWe deploy small and often.\n\n**Version**: 3.1\n"


def _starter() -> str:
    return read_asset_text(_ANCHOR, _CONSTITUTION_ASSET)


# --- _is_speckit_placeholder (T003) ---


def test_is_speckit_placeholder_detects_template():
    assert _is_speckit_placeholder(_PLACEHOLDER)


def test_is_speckit_placeholder_rejects_starter_and_real():
    assert not _is_speckit_placeholder(_starter())
    assert not _is_speckit_placeholder(_REAL)


# --- _apply_constitution (T001/T002) ---


def _constitution(tmp_path: Path) -> Path:
    return tmp_path / _CONSTITUTION_TARGET


def test_absent_creates_starter(tmp_path: Path):
    dest = _constitution(tmp_path)
    outcome = _apply_constitution(dest, _CONSTITUTION_TARGET, _starter())
    assert outcome.outcome is Outcome.CREATED
    assert dest.read_text(encoding="utf-8") == _starter()


def test_placeholder_replaced_by_starter(tmp_path: Path):
    """T001 / SC-001: a spec-kit placeholder is replaced by the neutral starter."""
    dest = _constitution(tmp_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_PLACEHOLDER, encoding="utf-8")
    outcome = _apply_constitution(dest, _CONSTITUTION_TARGET, _starter())
    assert outcome.outcome is Outcome.UPDATED
    assert dest.read_text(encoding="utf-8") == _starter()
    assert "[PROJECT_NAME]" not in dest.read_text(encoding="utf-8")


def test_real_constitution_preserved(tmp_path: Path):
    """T002 / SC-002: a real host constitution is preserved byte-for-byte."""
    dest = _constitution(tmp_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_REAL, encoding="utf-8")
    outcome = _apply_constitution(dest, _CONSTITUTION_TARGET, _starter())
    assert outcome.outcome is Outcome.SKIPPED
    assert dest.read_text(encoding="utf-8") == _REAL


def test_replace_is_idempotent(tmp_path: Path):
    """A second run sees the starter (no sentinels) → preserved, no further change (NFR-02)."""
    dest = _constitution(tmp_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_PLACEHOLDER, encoding="utf-8")
    _apply_constitution(dest, _CONSTITUTION_TARGET, _starter())
    again = _apply_constitution(dest, _CONSTITUTION_TARGET, _starter())
    assert again.outcome is Outcome.SKIPPED
    assert dest.read_text(encoding="utf-8") == _starter()


def test_dry_run_does_not_write(tmp_path: Path):
    dest = _constitution(tmp_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_PLACEHOLDER, encoding="utf-8")
    outcome = _apply_constitution(dest, _CONSTITUTION_TARGET, _starter(), dry_run=True)
    assert outcome.outcome is Outcome.UPDATED  # projected
    assert dest.read_text(encoding="utf-8") == _PLACEHOLDER  # but not written


def test_apply_config_install_path_replaces_placeholder(tmp_path: Path):
    """The install dispatch (`_apply_config`) wires replace-if-placeholder."""
    dest = _constitution(tmp_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_PLACEHOLDER, encoding="utf-8")
    art = Artifact(
        kind=ArtifactKind.CONFIG,
        source=_CONSTITUTION_ASSET,
        target_rel=_CONSTITUTION_TARGET,
        strategy=WriteStrategy.CREATE_IF_ABSENT,
    )
    outcome = _apply_config(tmp_path, art)
    assert outcome.outcome is Outcome.UPDATED
    assert dest.read_text(encoding="utf-8") == _starter()


# --- starter content (T021/SC-003) ---


def test_starter_has_new_generic_principles():
    text = _starter()
    assert "Replaceable Details" in text
    assert "Consume Through Stable Interfaces" in text


def test_starter_has_no_placeholder_sentinels():
    text = _starter()
    assert "[PROJECT_NAME]" not in text
    assert "[PRINCIPLE_1_NAME]" not in text


def test_starter_has_no_sertor_or_rag_specifics():
    """The starter PRINCIPLES are generic — no Sertor/RAG-specific terms (SC-003).

    The intro note legitimately names `sertor-flow` (the installer) and `speckit-constitution`; the
    check scopes to the principles body (after the `## Core Principles` heading)."""
    body = _starter().split("## Core Principles", 1)[1].lower()
    for term in ("sertor", "hit@k", "mrr", "retrieval", "embedding", "host-agnostic"):
        assert term not in body, f"starter principles leaked a Sertor/RAG-specific term: {term!r}"


def test_starter_version_bumped():
    assert "0.4.0" in _starter()
