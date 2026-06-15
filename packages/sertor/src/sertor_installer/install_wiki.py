"""Orchestration of `sertor install wiki`: plan + execution over the shared kit (037, D8).

`build_install_plan` enumerates bundled assets (NEVER fixed counts: the plan derives from the
bundle composition, F1/F8) producing the ordered list of `Artifact`. Execution delegates to the
kit's generic `execute_plan` (fail-fast no-rollback), with a per-`kind` `apply` callback.

**Boundary wrapping (037, D3):** the only step that crosses into `sertor-core` is `_apply_structure`
(`load_profile`/`init_structure`). For the kit, `sertor-core` is a third party, and the kit's
`execute_plan` catches `InstallerError` (not `SertorError`). So this layer wraps any `SertorError`
raised by `sertor_core.wiki_tools` into `InstallerError` at the boundary — otherwise a core error
would escape the kit's fail-fast. Thin **layer** (Principio I).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_core.domain.errors import SertorError
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.structure import init_structure
from sertor_install_kit.assistant import AssistantId, AssistantProfile, Surface
from sertor_install_kit.errors import ConfigError, InstallerError
from sertor_install_kit.executor import execute_plan as _kit_execute_plan
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
from sertor_installer.surfaces import render_custom_agent, render_prompt_file

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

# --- Copilot wiki surfaces (feature 044, US2/US3) -------------------------------------------
# Single source of truth = the existing `assets/claude/**` (anti-drift, REQ-021). The Copilot
# plan reuses the SAME content; only the container (path/frontmatter) is translated.
_COPILOT_INSTRUCTIONS = ".github/copilot-instructions.md"
_COPILOT_HOOK_WIRING = ".github/hooks/sertor-hooks.json"
# Hook script is REUSED byte-for-byte from the Claude asset (FR-014); only the wiring differs.
_WIKI_HOOK_SCRIPT_SRC = "claude/hooks/wiki-pending-check.ps1"
_WIKI_HOOK_SCRIPT_DST = ".github/hooks/wiki-pending-check.ps1"
_COPILOT_HOOK_FRAGMENT = "copilot/hooks/wiki.hooks.json"
# Canonical command/skill + agent sources rendered into `.github/**` (FILE rendered).
_WIKI_COMMAND_SRC = "claude/commands/wiki.md"
_WIKI_COMMAND_DST = ".github/prompts/wiki.prompt.md"
_WIKI_SKILL_SRC = "claude/skills/wiki-author/SKILL.md"
_WIKI_SKILL_DST = ".github/prompts/wiki-author.prompt.md"
_WIKI_AGENT_SRC = "claude/agents/wiki-curator.md"
_WIKI_AGENT_DST = ".github/agents/wiki-curator.agent.md"
# Rendered-file sources are tagged so the apply callback knows to translate, not byte-copy.
_RENDER_PROMPT_SUFFIX = ".prompt.md"
_RENDER_AGENT_SUFFIX = ".agent.md"


def build_install_plan(assistant: AssistantId = AssistantProfile.DEFAULT) -> list[Artifact]:
    """Ordered list of `Artifact` (data-model §3), parametric on the target `assistant`.

    The plan-builder no longer hard-codes `.claude/...`: it asks the `AssistantProfile` for the
    container of each surface (Principio X). `claude` (default) reproduces the historical plan
    byte-for-byte (non-regression); `copilot` renders the FILE surfaces into `.github/**`.

    Canonical order: FILE×N (skill/command/agent/hook) → SETTINGS_MERGE → MARKER_BLOCK → CONFIG →
    STRUCTURE. FILE entries are not hard-coded: they are discovered by walking `assets/claude/`
    (F1/F8).
    """
    if assistant is AssistantId.COPILOT:
        return _build_copilot_wiki_plan()
    return _build_claude_wiki_plan()


def _build_claude_wiki_plan() -> list[Artifact]:
    """Historical Claude plan (non-regression): `.claude/**` + `CLAUDE.md` + wiki scaffold."""
    profile = AssistantProfile.for_assistant(AssistantId.CLAUDE)
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

    # 2. SETTINGS_MERGE (HOOK wiring)
    plan.append(
        Artifact(
            kind=ArtifactKind.SETTINGS_MERGE,
            source=_SETTINGS_FRAGMENT,
            target_rel=profile.target_for(Surface.HOOK).target_rel,
            strategy=WriteStrategy.MERGE_DEDUP,
        )
    )
    # 3. MARKER_BLOCK (INSTRUCTION_BLOCK)
    plan.append(
        Artifact(
            kind=ArtifactKind.MARKER_BLOCK,
            source=_CLAUDE_MD_BLOCK,
            target_rel=profile.target_for(Surface.INSTRUCTION_BLOCK).target_rel,
            strategy=WriteStrategy.APPEND_BLOCK,
        )
    )
    # 4. CONFIG (generated from HostProfile, source = template) — assistant-agnostic
    plan.append(
        Artifact(
            kind=ArtifactKind.CONFIG,
            source=_CONFIG_TEMPLATE,
            target_rel=_CONFIG_TARGET,
            strategy=WriteStrategy.GENERATE_CONFIG,
        )
    )
    # 5. STRUCTURE (delegates to init_structure; no source asset) — assistant-agnostic
    plan.append(
        Artifact(
            kind=ArtifactKind.STRUCTURE,
            source=None,
            target_rel="wiki/",
            strategy=WriteStrategy.INIT_STRUCTURE,
        )
    )
    return plan


def _build_copilot_wiki_plan() -> list[Artifact]:
    """Copilot wiki plan (feature 044): `.github/**` + `.vscode/**`, content reused from Claude.

    Surfaces: COMMAND (`/wiki`, `wiki-author` skill) → `.github/prompts/*.prompt.md`; AGENT
    (`wiki-curator`) → `.github/agents/*.agent.md`; HOOK script reused identically + wiring in
    `.github/hooks/*.json`; INSTRUCTION_BLOCK → `.github/copilot-instructions.md`; CONFIG/STRUCTURE
    are assistant-agnostic (the wiki scaffold lives in `wiki/`).
    """
    plan: list[Artifact] = []
    # COMMAND: render the command + skill body into prompt-files (anti-drift, single source).
    plan.append(
        Artifact(ArtifactKind.FILE, _WIKI_COMMAND_SRC, _WIKI_COMMAND_DST,
                 WriteStrategy.CREATE_IF_ABSENT)
    )
    plan.append(
        Artifact(ArtifactKind.FILE, _WIKI_SKILL_SRC, _WIKI_SKILL_DST,
                 WriteStrategy.CREATE_IF_ABSENT)
    )
    # AGENT: render the persona into a custom-agent file.
    plan.append(
        Artifact(ArtifactKind.FILE, _WIKI_AGENT_SRC, _WIKI_AGENT_DST,
                 WriteStrategy.CREATE_IF_ABSENT)
    )
    # HOOK: reuse the script byte-for-byte (FR-014) + wire the events.
    plan.append(
        Artifact(ArtifactKind.FILE, _WIKI_HOOK_SCRIPT_SRC, _WIKI_HOOK_SCRIPT_DST,
                 WriteStrategy.CREATE_IF_ABSENT)
    )
    plan.append(
        Artifact(ArtifactKind.SETTINGS_MERGE, _COPILOT_HOOK_FRAGMENT, _COPILOT_HOOK_WIRING,
                 WriteStrategy.MERGE_DEDUP)
    )
    # INSTRUCTION_BLOCK: ritual block in copilot-instructions (same content/markers).
    plan.append(
        Artifact(ArtifactKind.MARKER_BLOCK, _CLAUDE_MD_BLOCK, _COPILOT_INSTRUCTIONS,
                 WriteStrategy.APPEND_BLOCK)
    )
    # CONFIG + STRUCTURE: assistant-agnostic wiki scaffold (same as Claude).
    plan.append(
        Artifact(ArtifactKind.CONFIG, _CONFIG_TEMPLATE, _CONFIG_TARGET,
                 WriteStrategy.GENERATE_CONFIG)
    )
    plan.append(
        Artifact(ArtifactKind.STRUCTURE, None, "wiki/", WriteStrategy.INIT_STRUCTURE)
    )
    return plan


def _resolve(target_root: Path, target_rel: str) -> Path:
    """Resolves a `target_rel` under `target_root` (paths are already validated as relative)."""
    return target_root / target_rel


def _render_for_target(art: Artifact) -> str:
    """Content for a FILE artifact: rendered for Copilot prompt/agent files, byte-copy otherwise.

    Rendered files (`*.prompt.md`/`*.agent.md`) are DERIVED from the canonical Claude asset
    (anti-drift, REQ-021): the body is reused verbatim, only the frontmatter is translated.
    """
    assert art.source is not None
    canonical = read_asset_text(art.source)
    if art.target_rel.endswith(_RENDER_PROMPT_SUFFIX):
        return render_prompt_file(canonical)
    if art.target_rel.endswith(_RENDER_AGENT_SUFFIX):
        return render_custom_agent(canonical)
    return canonical


def _apply_file(target_root: Path, art: Artifact) -> ArtifactOutcome:
    """`CREATE_IF_ABSENT`: byte-for-byte copy (or rendered, for Copilot) of the asset; exists →
    skip."""
    dest = _resolve(target_root, art.target_rel)
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "already present")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_render_for_target(art), encoding="utf-8")
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
    dest.parent.mkdir(parents=True, exist_ok=True)  # e.g. `.github/` for copilot-instructions.md
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

    **Boundary wrapping (037, D3):** `load_profile`/`init_structure` belong to `sertor-core` (a
    third party for the kit) and may raise `SertorError`; we wrap it in `InstallerError` so the
    kit's `execute_plan` keeps its fail-fast.
    """
    config_path = _resolve(target_root, _CONFIG_TARGET)
    try:
        wiki_profile = load_profile(config_path, root_override=target_root)
        result = init_structure(wiki_profile)
    except SertorError as exc:
        raise InstallerError(f"wiki structure init failed: {exc}") from exc
    detail = f"{len(result.created)} created, {len(result.skipped_existing)} existing"
    outcome = Outcome.CREATED if result.created else Outcome.SKIPPED
    return ArtifactOutcome(art.target_rel, outcome, detail)


def execute_plan(
    plan: list[Artifact], profile: HostProfile,
    assistant: AssistantId = AssistantProfile.DEFAULT,
) -> InstallReport:
    """Executes the plan with fail-fast no-rollback via the kit's generic executor (037).

    The per-`kind` dispatch is the `apply` callback; the kit catches `InstallerError` and stops on
    the first one. Errors crossing the `sertor-core` boundary are wrapped in `_apply_structure`.
    The `assistant` is recorded in the report (informative, Principio IX); the apply handlers are
    assistant-agnostic (paths come from `art.target_rel`, already resolved by the plan-builder).
    """
    root = profile.target_root

    def apply(art: Artifact) -> ArtifactOutcome:
        if art.kind is ArtifactKind.FILE:
            return _apply_file(root, art)
        if art.kind is ArtifactKind.SETTINGS_MERGE:
            return _apply_settings(root, art)
        if art.kind is ArtifactKind.MARKER_BLOCK:
            return _apply_marker(root, art)
        if art.kind is ArtifactKind.CONFIG:
            return _apply_config(root, art, profile)
        if art.kind is ArtifactKind.STRUCTURE:
            return _apply_structure(root, art)
        raise ConfigError(f"unhandled artifact kind: {art.kind}")  # pragma: no cover

    return _kit_execute_plan(
        plan, apply, target=str(root), capability="wiki", assistant=assistant.value
    )
