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



# --- Principle XIV: preserved is not the same as silent ------------------------------------------
#
# A host constitution is never overwritten — it is theirs to personalize. But the preserve branch
# used to say only "host constitution preserved", so a host holding a copy older than an amendment
# had no way to learn one existed: the starter version is written INSIDE the file, and nothing
# compared it. That is the class Principle XIV forbids — a value duplicated onto the host and never
# reconciled. The tool still writes nothing: it declares, the host's agent integrates.

from sertor_flow.install_governance import starter_version  # noqa: E402

_HOST_BODY = "# Our Own Constitution\n\n### I. Ours\n\nText.\n\n## Governance\n\n"


def _host_constitution(tmp_path: Path, version: str | None) -> Path:
    """A REAL host constitution (no spec-kit sentinels), optionally declaring a starter version."""
    dest = _constitution(tmp_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = _HOST_BODY
    if version is not None:
        body += f"**Version**: {version} | **Ratified**: 2026-01-01\n"
    dest.write_text(body, encoding="utf-8")
    return dest


def _starter_at(version: str) -> str:
    return (
        "# Project Constitution\n\n## Amendments\n\n"
        f"- **{version}** - something\n\n"
        f"**Version**: {version} | **Ratified**: TODO\n"
    )


def test_behind_host_is_told_which_version_it_holds_and_what_ships(tmp_path: Path):
    dest = _host_constitution(tmp_path, "0.4.0")
    before = dest.read_text(encoding="utf-8")

    outcome = _apply_constitution(dest, "c.md", _starter_at("0.5.0"))

    assert outcome.outcome is Outcome.SKIPPED, "the host constitution is still preserved"
    assert "0.4.0" in outcome.detail and "0.5.0" in outcome.detail
    assert "Amendments" in outcome.detail, "point at what it missed, not just at a number"
    assert dest.read_text(encoding="utf-8") == before, "declaring must not write"


def test_current_host_gets_no_noise(tmp_path: Path):
    dest = _host_constitution(tmp_path, "0.5.0")
    outcome = _apply_constitution(dest, "c.md", _starter_at("0.5.0"))
    assert outcome.outcome is Outcome.SKIPPED
    assert outcome.detail == "host constitution preserved"


def test_ahead_host_is_not_told_to_go_back(tmp_path: Path):
    """A host may amend beyond the starter — that is not a gap."""
    dest = _host_constitution(tmp_path, "0.9.0")
    outcome = _apply_constitution(dest, "c.md", _starter_at("0.5.0"))
    assert outcome.detail == "host constitution preserved"


def test_unknown_version_is_not_guessed(tmp_path: Path):
    """A personalized constitution without the version line: unknown, never claimed to be behind."""
    dest = _host_constitution(tmp_path, None)
    outcome = _apply_constitution(dest, "c.md", _starter_at("0.5.0"))
    assert outcome.detail == "host constitution preserved"


def test_placeholder_still_wins_over_the_version_comparison(tmp_path: Path):
    """The spec-kit placeholder is replaced, not "preserved but behind" (ordering matters)."""
    dest = _constitution(tmp_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_PLACEHOLDER, encoding="utf-8")
    outcome = _apply_constitution(dest, "c.md", _starter_at("0.5.0"))
    assert outcome.outcome is Outcome.UPDATED


def test_starter_version_is_read_from_the_document_itself():
    assert starter_version("**Version**: 1.2.3 | **Ratified**: TODO") == "1.2.3"
    assert starter_version("no version line here") is None


def test_shipped_starter_declares_a_version_and_lists_amendments():
    """The reconciler is worthless if the shipped asset stops declaring what it is (XIV)."""
    from sertor_flow.install_governance import _ANCHOR
    from sertor_install_kit import read_asset_text

    body = read_asset_text(_ANCHOR, "constitution-starter.md")
    assert starter_version(body) is not None, "the starter must declare its own version"
    assert "## Amendments" in body, "a host behind needs the list of what it missed"
