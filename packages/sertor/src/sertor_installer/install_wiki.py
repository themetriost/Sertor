"""Orchestration of `sertor install wiki`: `InstallPlan` + execution (data-model §3, D8).

`build_install_plan` enumerates bundled assets (NEVER fixed counts: the plan derives from the
bundle composition, F1/F8) producing the ordered list of `Artifact`. `execute_plan` executes
sequentially with fail-fast (REQ-125, D8): on the first `ERROR` it stops, `failed_step` is set,
already-written artifacts remain (no rollback). Thin **layer** (Principio I): delegates to
`claude_md`, `settings_merge`, `config_gen` and `sertor_core.wiki_tools` for structure.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_core.domain.errors import ConfigError, SertorError
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.structure import init_structure
from sertor_installer import claude_md, config_gen, settings_merge
from sertor_installer.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    Outcome,
    WriteStrategy,
)
from sertor_installer.config_gen import HostProfile
from sertor_installer.report import InstallReport
from sertor_installer.resources import iter_asset_dir, read_asset_text

# Special assets (non-FILE): names relative to `assets/`.
_SETTINGS_FRAGMENT = "settings.hooks.json"
_CLAUDE_MD_BLOCK = "claude-md-block.md"
_CONFIG_TEMPLATE = "wiki.config.toml.tmpl"

_SETTINGS_TARGET = ".claude/settings.json"
_CLAUDE_MD_TARGET = "CLAUDE.md"
# The wiki config lives INSIDE `wiki/` (feature 016, host root hygiene): keeps the host root clean.
# Tools locate it via the convention `--config wiki/wiki.config.toml --root .` or via
# CLI auto-discovery (`wiki_tools/__main__`).
_CONFIG_TARGET = "wiki/wiki.config.toml"


def build_install_plan() -> list[Artifact]:
    """Ordered list of `Artifact` (data-model §3). Enumerates FILE entries from `claude/` assets.

    Canonical order: FILE×N (skill/command/agent/hook) → SETTINGS_MERGE → MARKER_BLOCK → CONFIG →
    STRUCTURE. FILE entries are not hard-coded: they are discovered by walking `assets/claude/`
    (F1/F8).
    """
    plan: list[Artifact] = []

    # 1. FILE × N — all files under assets/claude/ → .claude/<...>
    for rel_path, _content in iter_asset_dir("claude"):
        plan.append(
            Artifact(
                kind=ArtifactKind.FILE,
                source=f"claude/{rel_path}",
                target_rel=f".claude/{rel_path}",
                strategy=WriteStrategy.CREATE_IF_ABSENT,
            )
        )

    # 2. SETTINGS_MERGE
    plan.append(
        Artifact(
            kind=ArtifactKind.SETTINGS_MERGE,
            source=_SETTINGS_FRAGMENT,
            target_rel=_SETTINGS_TARGET,
            strategy=WriteStrategy.MERGE_DEDUP,
        )
    )
    # 3. MARKER_BLOCK
    plan.append(
        Artifact(
            kind=ArtifactKind.MARKER_BLOCK,
            source=_CLAUDE_MD_BLOCK,
            target_rel=_CLAUDE_MD_TARGET,
            strategy=WriteStrategy.APPEND_BLOCK,
        )
    )
    # 4. CONFIG (generated from HostProfile, source = template)
    plan.append(
        Artifact(
            kind=ArtifactKind.CONFIG,
            source=_CONFIG_TEMPLATE,
            target_rel=_CONFIG_TARGET,
            strategy=WriteStrategy.GENERATE_CONFIG,
        )
    )
    # 5. STRUCTURE (delegates to init_structure; no source asset)
    plan.append(
        Artifact(
            kind=ArtifactKind.STRUCTURE,
            source=None,
            target_rel="wiki/",
            strategy=WriteStrategy.INIT_STRUCTURE,
        )
    )
    return plan


def _resolve(target_root: Path, target_rel: str) -> Path:
    """Resolves a `target_rel` under `target_root` (paths are already validated as relative)."""
    return target_root / target_rel


def _apply_file(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`CREATE_IF_ABSENT`: byte-for-byte copy of the asset; exists → skip (per-file)."""
    dest = _resolve(target_root, art.target_rel)
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "already present")
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert art.source is not None
    dest.write_text(read_asset_text(art.source), encoding="utf-8")
    return ArtifactOutcome(art.target_rel, Outcome.CREATED)


def _apply_settings(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`MERGE_DEDUP`: additive merge of the hook fragment (D5)."""
    dest = _resolve(target_root, art.target_rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert art.source is not None
    fragment = json.loads(read_asset_text(art.source))
    outcome, detail = settings_merge.merge_settings(dest, fragment)
    return ArtifactOutcome(art.target_rel, outcome, detail)


def _apply_marker(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`APPEND_BLOCK`: idempotent marker-delimited block in `CLAUDE.md` (D4).

    The outcome for CLAUDE.md is ALWAYS `block` when the block is written, even if the file is
    created from scratch (F11); `skipped` only if the block was already present.
    """
    dest = _resolve(target_root, art.target_rel)
    assert art.source is not None
    block_content = read_asset_text(art.source)
    outcome = claude_md.write_ritual_block(dest, block_content)
    detail = "step-ritual section inserted" if outcome is Outcome.BLOCK else "block already present"
    return ArtifactOutcome(art.target_rel, outcome, detail)


def _apply_config(target_root: Path, art: Artifact, profile: HostProfile) -> ArtifactOutcome:
    """`GENERATE_CONFIG`: generates `wiki.config.toml` from template + HostProfile; exists →
    skip."""
    dest = _resolve(target_root, art.target_rel)
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "already present")
    dest.parent.mkdir(parents=True, exist_ok=True)  # `wiki/` may not exist yet (feature 016)
    dest.write_text(config_gen.generate_wiki_config(profile), encoding="utf-8")
    detail = f"language={profile.language}, source_dirs={','.join(profile.source_dirs)}"
    return ArtifactOutcome(art.target_rel, Outcome.CREATED, detail)


def _apply_structure(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`INIT_STRUCTURE`: delegates to core `init_structure` (idempotent). Requires the config.

    With the config in `wiki/` (feature 016) the relative paths (`root="wiki"`, `source_dirs`) must
    be resolved from the host root, not from the config directory → `root_override=target_root`.
    """
    config_path = _resolve(target_root, _CONFIG_TARGET)
    wiki_profile = load_profile(config_path, root_override=target_root)
    result = init_structure(wiki_profile)
    detail = f"{len(result.created)} created, {len(result.skipped_existing)} existing"
    outcome = Outcome.CREATED if result.created else Outcome.SKIPPED
    return ArtifactOutcome(art.target_rel, outcome, detail)


def execute_plan(plan: list[Artifact], profile: HostProfile) -> InstallReport:
    """Executes the plan sequentially with fail-fast (REQ-125, D8).

    On the first `ERROR` (domain exception raised by a step) it records the error outcome, sets
    `failed_step`, and stops: already-written artifacts remain (no rollback).
    """
    report = InstallReport(target=str(profile.target_root))
    root = profile.target_root

    for art in plan:
        try:
            if art.kind is ArtifactKind.FILE:
                outcome = _apply_file(root, art)
            elif art.kind is ArtifactKind.SETTINGS_MERGE:
                outcome = _apply_settings(root, art)
            elif art.kind is ArtifactKind.MARKER_BLOCK:
                outcome = _apply_marker(root, art)
            elif art.kind is ArtifactKind.CONFIG:
                outcome = _apply_config(root, art, profile)
            elif art.kind is ArtifactKind.STRUCTURE:
                outcome = _apply_structure(root, art)
            else:  # pragma: no cover — unknown kind is a bug, not user input
                raise ConfigError(f"unhandled artifact kind: {art.kind}")
        except SertorError as exc:
            report.add(ArtifactOutcome(art.target_rel, Outcome.ERROR, str(exc)))
            break  # fail-fast: stop on the first domain error
        report.add(outcome)

    return report
