"""Orchestration of `sertor-flow install`: plan + execution over the shared kit.

Thin consumer (Principle I): `sertor-flow` does NOT duplicate the installer
primitives — they all come from `sertor_install_kit` (artifacts, executor, marker
block, resources, report). This module only (a) derives the governance plan from the
bundle composition and (b) dispatches each `kind` to a per-artifact `apply`.

`build_governance_plan` enumerates the bundled assets (NEVER fixed counts: the plan
derives from the bundle composition, FR-005) producing the ordered list of
`Artifact`. The runtime-only `.specify/feature.json` is NOT an asset and is excluded
from the plan (DA-e).

The init/integration files use the existing `CONFIG` kind with the `GENERATE_CONFIG`
strategy (generate-from-template, skip-if-present) — NO new `ArtifactKind` (F10/F12):
the kit's executor is not extended.

Marker block: `SERTOR:SDLC-RITUAL` markers (distinct from the wiki's
`SERTOR:WIKI-RITUAL`) so the two blocks coexist in the same `CLAUDE.md` (D4).
"""
from __future__ import annotations

from pathlib import Path

from sertor_flow import generate
from sertor_flow.profile import GovernanceProfile
from sertor_install_kit import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    ConfigError,
    InstallReport,
    Outcome,
    WriteStrategy,
    iter_asset_dir,
    read_asset_text,
    write_marker_block,
)
from sertor_install_kit import (
    execute_plan as _kit_execute_plan,
)

# Anchor of THIS package: the kit reads the bundled assets relative to it (D2).
_ANCHOR = "sertor_flow"

# SDLC ritual block markers — DISTINCT from the wiki markers (D4).
MARKER_START_SDLC = "<!-- SERTOR:SDLC-RITUAL START -->"
MARKER_END_SDLC = "<!-- SERTOR:SDLC-RITUAL END -->"

# Special (non-FILE) assets: names relative to `assets/`.
_CONSTITUTION_ASSET = "constitution-starter.md"
_SDLC_BLOCK_ASSET = "claude-md-block-sdlc.md"
_NOTICE_ASSET = "NOTICE"
_LICENSE_ASSET = "LICENSES/spec-kit-MIT.txt"

# Targets on the host.
_CONSTITUTION_TARGET = ".specify/memory/constitution.md"
_NOTICE_TARGET = ".specify/NOTICE"
_LICENSE_TARGET = ".specify/LICENSES/spec-kit-MIT.txt"
_CLAUDE_MD_TARGET = "CLAUDE.md"

# Generated per-host init/integration files: (template asset, host target).
_GENERATED: tuple[tuple[str, str], ...] = (
    (generate.INIT_OPTIONS_TMPL, generate.INIT_OPTIONS_TARGET),
    (generate.INTEGRATION_TMPL, generate.INTEGRATION_TARGET),
    (generate.CLAUDE_MANIFEST_TMPL, generate.CLAUDE_MANIFEST_TARGET),
    (generate.SPECKIT_MANIFEST_TMPL, generate.SPECKIT_MANIFEST_TARGET),
)


def build_governance_plan(profile: GovernanceProfile) -> list[Artifact]:
    """Ordered list of `Artifact` derived from the bundle composition (data-model §plan).

    Canonical order:
    1. FILE × N — `assets/claude/**` → `.claude/**`
    2. FILE × N — `assets/specify/**` → `.specify/**`
    3. CONFIG (constitution starter) → `.specify/memory/constitution.md`
    4. CONFIG/GENERATE_CONFIG × M — generated init/integration files
    5. FILE — NOTICE + license attribution
    6. MARKER_BLOCK — SDLC ritual block → `CLAUDE.md`

    The FILE entries are NOT hard-coded: they are discovered by walking the asset
    subtrees (FR-005). `.specify/feature.json` is runtime state, never an asset.
    """
    plan: list[Artifact] = []

    # 1. FILE × N — assets/claude/** → .claude/**
    for rel_path, _content in iter_asset_dir(_ANCHOR, "claude"):
        plan.append(
            Artifact(
                kind=ArtifactKind.FILE,
                source=f"claude/{rel_path}",
                target_rel=f".claude/{rel_path}",
                strategy=WriteStrategy.CREATE_IF_ABSENT,
            )
        )

    # 2. FILE × N — assets/specify/** → .specify/**
    for rel_path, _content in iter_asset_dir(_ANCHOR, "specify"):
        plan.append(
            Artifact(
                kind=ArtifactKind.FILE,
                source=f"specify/{rel_path}",
                target_rel=f".specify/{rel_path}",
                strategy=WriteStrategy.CREATE_IF_ABSENT,
            )
        )

    # 3. CONFIG — constitution starter (create-if-absent, FR-014)
    plan.append(
        Artifact(
            kind=ArtifactKind.CONFIG,
            source=_CONSTITUTION_ASSET,
            target_rel=_CONSTITUTION_TARGET,
            strategy=WriteStrategy.CREATE_IF_ABSENT,
        )
    )

    # 4. CONFIG/GENERATE_CONFIG × M — generated init/integration files (D7, F10/F12)
    for template_rel, target_rel in _GENERATED:
        plan.append(
            Artifact(
                kind=ArtifactKind.CONFIG,
                source=template_rel,
                target_rel=target_rel,
                strategy=WriteStrategy.GENERATE_CONFIG,
            )
        )

    # 5. FILE — attribution (NOTICE + MIT license), REQ-022
    plan.append(
        Artifact(
            kind=ArtifactKind.FILE,
            source=_NOTICE_ASSET,
            target_rel=_NOTICE_TARGET,
            strategy=WriteStrategy.CREATE_IF_ABSENT,
        )
    )
    plan.append(
        Artifact(
            kind=ArtifactKind.FILE,
            source=_LICENSE_ASSET,
            target_rel=_LICENSE_TARGET,
            strategy=WriteStrategy.CREATE_IF_ABSENT,
        )
    )

    # 6. MARKER_BLOCK — SDLC ritual block in CLAUDE.md (D4)
    plan.append(
        Artifact(
            kind=ArtifactKind.MARKER_BLOCK,
            source=_SDLC_BLOCK_ASSET,
            target_rel=_CLAUDE_MD_TARGET,
            strategy=WriteStrategy.APPEND_BLOCK,
        )
    )
    return plan


def _resolve(target_root: Path, target_rel: str) -> Path:
    """Resolves a `target_rel` under `target_root` (paths are validated as relative)."""
    return target_root / target_rel


def _apply_file(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`CREATE_IF_ABSENT`: byte-for-byte copy of the asset; exists → skip (per-file)."""
    dest = _resolve(target_root, art.target_rel)
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "already present")
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert art.source is not None
    dest.write_text(read_asset_text(_ANCHOR, art.source), encoding="utf-8")
    return ArtifactOutcome(art.target_rel, Outcome.CREATED)


def _apply_config(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """Constitution starter (`CREATE_IF_ABSENT`): copy the starter; exists → skip (FR-014)."""
    dest = _resolve(target_root, art.target_rel)
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "already present")
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert art.source is not None
    dest.write_text(read_asset_text(_ANCHOR, art.source), encoding="utf-8")
    return ArtifactOutcome(art.target_rel, Outcome.CREATED, "constitution starter")


def _apply_generate_init(
    target_root: Path, art: Artifact, profile: GovernanceProfile
) -> ArtifactOutcome:
    """`GENERATE_CONFIG`: generate the init/integration file from template; exists → skip (D7)."""
    dest = _resolve(target_root, art.target_rel)
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "already present")
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert art.source is not None
    dest.write_text(generate.generate_file(art.source, profile), encoding="utf-8")
    detail = f"assistant={profile.assistant}, script={profile.script}"
    return ArtifactOutcome(art.target_rel, Outcome.CREATED, detail)


def _apply_marker(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`APPEND_BLOCK`: idempotent SDLC marker block in `CLAUDE.md` (D4).

    `block` when the block is written (even on a freshly created file); `skipped`
    only when the SDLC markers were already present.
    """
    dest = _resolve(target_root, art.target_rel)
    assert art.source is not None
    block_content = read_asset_text(_ANCHOR, art.source)
    outcome = write_marker_block(dest, block_content, MARKER_START_SDLC, MARKER_END_SDLC)
    detail = "SDLC ritual block inserted" if outcome is Outcome.BLOCK else "block already present"
    return ArtifactOutcome(art.target_rel, outcome, detail)


def execute_governance_plan(profile: GovernanceProfile) -> InstallReport:
    """Executes the governance plan via the kit's generic executor (fail-fast no-rollback).

    The per-`kind` dispatch is the `apply` callback; the kit catches `InstallerError`
    and stops on the first one. Returns an `InstallReport` with `capability="governance"`.
    """
    root = profile.target_root
    plan = build_governance_plan(profile)

    def apply(art: Artifact) -> ArtifactOutcome:
        if art.kind is ArtifactKind.FILE:
            return _apply_file(root, art)
        if art.kind is ArtifactKind.MARKER_BLOCK:
            return _apply_marker(root, art)
        if art.kind is ArtifactKind.CONFIG:
            if art.strategy is WriteStrategy.GENERATE_CONFIG:
                return _apply_generate_init(root, art, profile)
            return _apply_config(root, art)
        raise ConfigError(f"unhandled artifact kind: {art.kind}")  # pragma: no cover

    return _kit_execute_plan(plan, apply, target=str(root), capability="governance")
