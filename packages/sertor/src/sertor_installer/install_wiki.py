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
from sertor_install_kit import host_env
from sertor_install_kit.artifacts import LifecycleOp
from sertor_install_kit.assistant import AssistantId, AssistantProfile, Surface
from sertor_install_kit.claude_md import remove_marker_block, update_marker_block
from sertor_install_kit.errors import ConfigError, InstallerError
from sertor_install_kit.executor import execute_plan as _kit_execute_plan
from sertor_install_kit.lifecycle import (
    SertorOwnedPaths,
    SharedEdit,
    SharedEditKind,
    project_removal,
    project_update,
    remove_path,
    update_file_if_changed,
)
from sertor_install_kit.lifecycle import (
    execute_lifecycle as _kit_execute_lifecycle,
)
from sertor_install_kit.model_policy import resolve_model
from sertor_install_kit.settings_merge import remove_settings_entries
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
from sertor_installer.surfaces import (
    HookEntrySpec,
    render_copilot_hooks,
    render_custom_agent,
    render_native_skill,
    render_prompt_file,
)

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
# Hook scripts are REUSED byte-for-byte from the Claude asset (FR-014); only the wiring differs.
_WIKI_HOOK_SCRIPT_SRC = "claude/hooks/wiki-pending-check.ps1"
_WIKI_HOOK_SCRIPT_DST = ".github/hooks/wiki-pending-check.ps1"
# FEAT-011: the Copilot hook wiring is GENERATED natively (render_copilot_hooks), no longer read
# from a static Claude-format asset. The sentinel source marks the GENERATED-wiki wiring so the
# apply callback builds it instead of reading a file (no new ArtifactKind, data-model §4).
_COPILOT_WIKI_WIRING_SENTINEL = "(generated: copilot wiki hooks)"
# Canonical sources for the wiki surfaces (single source = `assets/claude/**`).
# FEAT-001 (056, parità Copilot — NATIVE agent-skills): the wiki capability on Copilot is a SINGLE
# NATIVE agent-skill. The whole skill tree is deposited under `.github/skills/wiki-author/` and
# Copilot auto-discovers all its files (incl. `ops/`). Its `SKILL.md` is the DISPATCHER (the 8 wiki
# operations) rendered from the canonical command body (`commands/wiki.md`): Copilot CLI has no
# custom slash-commands, so the native skill ABSORBS the `/wiki` command role (it is both
# user-invocable via `/skills` and model-invocable). The support payload (playbook, ops/, craft) is
# byte-copied; the bodies reference it with RELATIVE co-located paths that resolve identically on
# both hosts (parallel containers `.claude/skills/wiki-author/` ↔ `.github/skills/wiki-author/`).
_WIKI_COMMAND_SRC = "claude/commands/wiki.md"          # → Copilot native SKILL.md (dispatcher)
_WIKI_SKILL_NAME = "wiki-author"
_WIKI_SKILL_SUPPORT_SRC = "claude/skills/wiki-author"  # payload tree (byte-copied)
_WIKI_AGENT_SRC = "claude/agents/wiki-curator.md"
_WIKI_AGENT_DST = ".github/agents/wiki-curator.agent.md"
_COPILOT_SKILL_DIR = ".github/skills/wiki-author"      # native skill container (Copilot)
_COPILOT_SKILL_MD = f"{_COPILOT_SKILL_DIR}/SKILL.md"   # the dispatcher SKILL.md target
# Rendered-file sources are tagged so the apply callback knows to translate, not byte-copy.
_RENDER_PROMPT_SUFFIX = ".prompt.md"
_RENDER_AGENT_SUFFIX = ".agent.md"

# Native Copilot hook commands (the script invocation; `-Assistant copilot` selects the native
# output). `pwsh -File` is the portable interpreter; the path is relative to the host root.
_PWSH = "pwsh -File"


def _copilot_wiki_hook_specs(assistant: AssistantId) -> list[HookEntrySpec]:
    """Logical hook entries for the Copilot CLI wiki wiring (FEAT-011, US3).

    SessionStart is a static `prompt` (Q1=b): the directive IS the prompt — no script to run.
    Stop/SessionEnd reuse the shared `wiki-pending-check.ps1` with `-Assistant copilot` (native
    agentStop/sessionEnd output).
    """
    stop = HookEntrySpec(
        "Stop", "command",
        f"{_PWSH} {_WIKI_HOOK_SCRIPT_DST} -Mode Stop -Assistant copilot", 10,
    )
    session_end = HookEntrySpec(
        "SessionEnd", "command",
        f"{_PWSH} {_WIKI_HOOK_SCRIPT_DST} -Mode SessionEnd -Assistant copilot", 10,
    )
    # CLI: SessionStart is a static prompt (the directive). No script invocation.
    session_start = HookEntrySpec(
        "SessionStart", "prompt",
        "SESSION START - load the project context BEFORE replying: read "
        "wiki/syntheses/roadmap.md, wiki/index.md and the latest file in wiki/log/, then show "
        "the user the executive summary between the markers <!-- EXEC:START --> and "
        "<!-- EXEC:END -->.",
        15,
    )
    return [session_start, stop, session_end]


def build_install_plan(assistant: AssistantId = AssistantProfile.DEFAULT) -> list[Artifact]:
    """Ordered list of `Artifact` (data-model §3), parametric on the target `assistant`.

    The plan-builder no longer hard-codes `.claude/...`: it asks the `AssistantProfile` for the
    container of each surface (Principio X). `claude` (default) reproduces the historical plan
    byte-for-byte (non-regression); `copilot-cli` renders the FILE surfaces into `.github/**`.

    Canonical order: FILE×N (skill/command/agent/hook) → SETTINGS_MERGE → MARKER_BLOCK → CONFIG →
    STRUCTURE. FILE entries are not hard-coded: they are discovered by walking `assets/claude/`
    (F1/F8).
    """
    # Copilot CLI reads the `.github/**` surfaces; the COMMAND vehicle is a custom-agent and the
    # SessionStart wiring is a native prompt — so the plan is parametric on the assistant.
    if assistant is AssistantId.COPILOT_CLI:
        return _build_copilot_wiki_plan(assistant)
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


def _build_copilot_wiki_plan(assistant: AssistantId) -> list[Artifact]:
    """Copilot CLI wiki plan (feature 044 + FEAT-001/056): NATIVE agent-skill + `.github/**`.

    Surfaces:
      - SKILL (`wiki-author`): a NATIVE agent-skill under `.github/skills/wiki-author/` — `SKILL.md`
        is the DISPATCHER rendered from the canonical command body (it absorbs the `/wiki` command,
        which has no native vehicle on the CLI), and the support payload (playbook/ops/craft) is
        byte-copied. Copilot auto-discovers the whole folder; bodies use relative co-located refs.
      - AGENT (`wiki-curator`): `.github/agents/wiki-curator.agent.md` (custom-agent with the
        policy `model:`, E2-FEAT-015).
      - HOOK: reuse `wiki-pending-check.ps1` byte-for-byte + GENERATED native wiring
        (`render_copilot_hooks`); SessionStart is a native prompt (no script).
      - INSTRUCTION_BLOCK → `.github/copilot-instructions.md`.
      - CONFIG/STRUCTURE: assistant-agnostic (the wiki scaffold lives in `wiki/`).
    """
    # Fail-loud BEFORE any artifact is written (FR-008/009, DA-D-4): this plan deposits a
    # single Copilot agent (`wiki-curator`) — validate the policy covers it up front.
    resolve_model("wiki-curator")

    plan: list[Artifact] = []

    # SKILL (native): the dispatcher SKILL.md (rendered from the command) + the byte-copied support
    # payload (playbook/ops/craft) together form one self-contained, auto-discovered agent-skill.
    plan.append(
        Artifact(ArtifactKind.FILE, _WIKI_COMMAND_SRC, _COPILOT_SKILL_MD,
                 WriteStrategy.CREATE_IF_ABSENT)
    )
    for rel_path, _content in iter_asset_dir(_WIKI_SKILL_SUPPORT_SRC):
        if rel_path == "SKILL.md":
            continue  # the native SKILL.md is the dispatcher rendered from the command (above)
        plan.append(
            Artifact(
                ArtifactKind.FILE,
                f"{_WIKI_SKILL_SUPPORT_SRC}/{rel_path}",
                f"{_COPILOT_SKILL_DIR}/{rel_path}",
                WriteStrategy.CREATE_IF_ABSENT,
            )
        )
    # AGENT: render the persona into a custom-agent file (policy model:, E2-FEAT-015).
    plan.append(
        Artifact(ArtifactKind.FILE, _WIKI_AGENT_SRC, _WIKI_AGENT_DST,
                 WriteStrategy.CREATE_IF_ABSENT)
    )
    # HOOK scripts: reuse byte-for-byte (FR-014). The CLI SessionStart is a static prompt, so no
    # session-start script is installed — only the Stop/SessionEnd check script.
    plan.append(
        Artifact(ArtifactKind.FILE, _WIKI_HOOK_SCRIPT_SRC, _WIKI_HOOK_SCRIPT_DST,
                 WriteStrategy.CREATE_IF_ABSENT)
    )
    # HOOK wiring: GENERATED natively (sentinel source → apply builds it via render_copilot_hooks).
    plan.append(
        Artifact(ArtifactKind.SETTINGS_MERGE, _COPILOT_WIKI_WIRING_SENTINEL, _COPILOT_HOOK_WIRING,
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
    """Content for a FILE artifact: rendered for Copilot skill/agent files, byte-copy otherwise.

    Derived files are translated from the canonical Claude asset (anti-drift, REQ-021): the body is
    reused verbatim, only the frontmatter is translated.
      - the Copilot native skill `SKILL.md` is the DISPATCHER rendered from the command body
        (`render_native_skill`) — the skill absorbs the `/wiki` command (FEAT-001/056);
      - a `*.agent.md` is a custom-agent (`render_custom_agent`); a `*.prompt.md` a prompt-file.
    Everything else (the byte-copied skill payload) is returned verbatim.
    """
    assert art.source is not None
    canonical = read_asset_text(art.source)
    if art.target_rel == _COPILOT_SKILL_MD and art.source == _WIKI_COMMAND_SRC:
        return render_native_skill(canonical, _WIKI_SKILL_NAME)
    if art.target_rel.endswith(_RENDER_PROMPT_SUFFIX):
        return render_prompt_file(canonical)
    if art.target_rel.endswith(_RENDER_AGENT_SUFFIX):
        name = art.target_rel.rsplit("/", 1)[-1].removesuffix(_RENDER_AGENT_SUFFIX)
        return render_custom_agent(canonical, model=resolve_model(name))
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


def _wiki_hook_fragment(art: Artifact, assistant: AssistantId) -> dict:
    """The hook wiring fragment for the settings merge/remove (single source for install/uninstall).

    FEAT-011: the Copilot wiring is GENERATED natively via `render_copilot_hooks` (sentinel source);
    the Claude wiring is read from the static `settings.hooks.json` asset (unchanged).
    """
    if art.source == _COPILOT_WIKI_WIRING_SENTINEL:
        return render_copilot_hooks(_copilot_wiki_hook_specs(assistant))
    assert art.source is not None
    return json.loads(read_asset_text(art.source))


def _apply_settings(
    target_root: Path, art: Artifact, assistant: AssistantId = AssistantProfile.DEFAULT
) -> ArtifactOutcome:
    """`MERGE_DEDUP`: additive merge of the hook fragment (D5). Copilot wiring is generated."""
    dest = _resolve(target_root, art.target_rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fragment = _wiki_hook_fragment(art, assistant)
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
    apply = make_wiki_apply(profile, assistant)
    report = _kit_execute_plan(
        plan, apply, target=str(root), capability="wiki", assistant=assistant.value
    )
    # E10-FEAT-018: honest, non-fatal pwsh guard for the deposited `.ps1` lifecycle hooks on
    # non-Windows hosts without PowerShell Core. Detect+report only; no wiring is rewritten (D-3).
    hook_surfaces = [a.target_rel for a in plan if a.target_rel.endswith(".ps1")]
    host_env.maybe_note_pwsh(report, hook_surfaces)
    return report


# --- feature 048: lifecycle (upgrade/uninstall) -------------------------------------------------


def sertor_owned_paths(assistant: AssistantId = AssistantProfile.DEFAULT) -> SertorOwnedPaths:
    """Static Sertor-owned paths for the `wiki` capability + assistant (D3, FR-017).

    Derived from the SAME plan-builder + profile (no separate hard-coded list): the standalone FILE
    artifacts (skill/command/agent/hook) and the generated config become `owned_files`; the wiki
    scaffold dir `wiki/` (removed ONLY with `--purge-wiki`, FR-027) and the `wiki-author` skill dir
    are `owned_dirs`; the marker block + hook wiring are `shared_edits`. A coverage test asserts the
    plan's `target_rel`s ⊆ these (the manifest replacement).
    """
    plan = build_install_plan(assistant)
    owned_files = tuple(
        a.target_rel
        for a in plan
        if a.kind in (ArtifactKind.FILE, ArtifactKind.CONFIG)
        and a.target_rel != "wiki/"
    )
    aprofile = AssistantProfile.for_assistant(assistant)
    instruction_target = aprofile.target_for(Surface.INSTRUCTION_BLOCK).target_rel
    settings_target = aprofile.target_for(Surface.HOOK).target_rel
    # The wiki scaffold dir is owned but removed only under --purge-wiki (gate lives in the CLI).
    # The wiki-author skill is a NATIVE skill on BOTH hosts (FEAT-001/056) → its whole tree is a
    # Sertor-owned dir, removed/upgraded in block: `.claude/skills/wiki-author` on Claude,
    # `.github/skills/wiki-author` on Copilot. The `wiki-curator` custom-agent
    # (`.github/agents/wiki-curator.agent.md`) is a standalone owned_file.
    owned_dirs: tuple[str, ...] = ("wiki",)
    if assistant is AssistantId.CLAUDE:
        owned_dirs = ("wiki", ".claude/skills/wiki-author")
    else:  # copilot-cli
        owned_dirs = ("wiki", _COPILOT_SKILL_DIR)
    return SertorOwnedPaths(
        owned_dirs=owned_dirs,
        owned_files=owned_files,
        shared_edits=(
            SharedEdit(instruction_target, SharedEditKind.MARKER, "SERTOR:WIKI-RITUAL"),
            SharedEdit(settings_target, SharedEditKind.SETTINGS, _SETTINGS_FRAGMENT),
        ),
    )


def _apply_wiki_uninstall(
    target_root: Path, art: Artifact, dry_run: bool = False,
    assistant: AssistantId = AssistantProfile.DEFAULT,
) -> ArtifactOutcome:
    """Inverse dispatch for `op=UNINSTALL` (data-model §3). `dry_run` projects without mutating.

    The `wiki/` scaffold (STRUCTURE) is NOT removed here: the dir is preserved by default and only
    removed by the CLI under `--purge-wiki` (FR-027). All other artifacts (files, marker block,
    settings) are removed.
    """
    if art.kind is ArtifactKind.STRUCTURE:
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "wiki dir preserved")
    if art.kind in (ArtifactKind.FILE, ArtifactKind.CONFIG):
        dest = _resolve(target_root, art.target_rel)
        outcome = project_removal(dest) if dry_run else remove_path(dest)
        detail = "wiki config" if art.kind is ArtifactKind.CONFIG else "wiki asset"
        return ArtifactOutcome(art.target_rel, outcome, detail)
    if art.kind is ArtifactKind.MARKER_BLOCK:
        dest = _resolve(target_root, art.target_rel)
        if dry_run:
            return ArtifactOutcome(art.target_rel, project_removal(dest), "WIKI-RITUAL block")
        outcome = remove_marker_block(dest, claude_md.MARKER_START, claude_md.MARKER_END)
        return ArtifactOutcome(art.target_rel, outcome, "WIKI-RITUAL block stripped")
    if art.kind is ArtifactKind.SETTINGS_MERGE:
        dest = _resolve(target_root, art.target_rel)
        if dry_run:
            return ArtifactOutcome(art.target_rel, project_removal(dest), "hook entries")
        fragment = _wiki_hook_fragment(art, assistant)
        # The Copilot dedicated hooks file (`sertor-hooks.json`) is entirely Sertor-owned: if it is
        # left empty after removal, delete it (don't leave a `{"version":1}` shell). The shared
        # Claude `.claude/settings.json` keeps the user's content → never delete-if-empty.
        outcome, detail = remove_settings_entries(
            dest, fragment, delete_if_empty=(dest.name == "sertor-hooks.json")
        )
        return ArtifactOutcome(art.target_rel, outcome, detail)
    raise ConfigError(f"unhandled artifact kind: {art.kind}")  # pragma: no cover


def _apply_wiki_upgrade(
    target_root: Path, art: Artifact, profile: HostProfile, dry_run: bool = False,
    assistant: AssistantId = AssistantProfile.DEFAULT,
) -> ArtifactOutcome:
    """Inverse-aware dispatch for `op=UPGRADE` (data-model §3); `dry_run` projects, no mutation."""
    if art.kind is ArtifactKind.FILE:
        dest = _resolve(target_root, art.target_rel)
        content = _render_for_target(art)
        outcome = (
            project_update(dest, content) if dry_run
            else update_file_if_changed(dest, content)
        )
        return ArtifactOutcome(art.target_rel, outcome, "wiki asset")
    if art.kind is ArtifactKind.MARKER_BLOCK:
        assert art.source is not None
        dest = _resolve(target_root, art.target_rel)
        content = read_asset_text(art.source)
        if dry_run:
            return ArtifactOutcome(art.target_rel, _project_wiki_marker(dest, content), "block")
        outcome = update_marker_block(
            dest, content, claude_md.MARKER_START, claude_md.MARKER_END
        )
        return ArtifactOutcome(art.target_rel, outcome, "WIKI-RITUAL block")
    if art.kind is ArtifactKind.STRUCTURE:
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "wiki scaffold present")
    if dry_run:
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "idempotent")
    if art.kind is ArtifactKind.CONFIG:
        return _apply_config(target_root, art, profile)  # create-if-absent, preserves user config
    if art.kind is ArtifactKind.SETTINGS_MERGE:
        return _apply_settings(target_root, art, assistant)  # additive idempotent
    raise ConfigError(f"unhandled artifact kind: {art.kind}")  # pragma: no cover


def _project_wiki_marker(dest: Path, content: str) -> Outcome:
    """Read-only projection of `update_marker_block` for the wiki markers (`--dry-run`)."""
    if not dest.exists():
        return Outcome.BLOCK
    existing = dest.read_text(encoding="utf-8")
    start = existing.find(claude_md.MARKER_START)
    if start == -1:
        return Outcome.BLOCK
    end = existing.find(claude_md.MARKER_END, start)
    if end == -1:
        return Outcome.BLOCK
    end += len(claude_md.MARKER_END)
    new_region = f"{claude_md.MARKER_START}\n{content.rstrip()}\n{claude_md.MARKER_END}"
    return Outcome.SKIPPED if existing[start:end] == new_region else Outcome.UPDATED


def make_wiki_apply(profile: HostProfile, assistant: AssistantId, dry_run: bool = False):
    """Builds the verb-aware `apply(artifact, op)` for the `wiki` capability (feature 048)."""
    root = profile.target_root

    def apply(art: Artifact, op: LifecycleOp = LifecycleOp.INSTALL) -> ArtifactOutcome:
        if op is LifecycleOp.UNINSTALL:
            return _apply_wiki_uninstall(root, art, dry_run, assistant)
        if op is LifecycleOp.UPGRADE:
            return _apply_wiki_upgrade(root, art, profile, dry_run, assistant)
        if art.kind is ArtifactKind.FILE:
            return _apply_file(root, art)
        if art.kind is ArtifactKind.SETTINGS_MERGE:
            return _apply_settings(root, art, assistant)
        if art.kind is ArtifactKind.MARKER_BLOCK:
            return _apply_marker(root, art)
        if art.kind is ArtifactKind.CONFIG:
            return _apply_config(root, art, profile)
        if art.kind is ArtifactKind.STRUCTURE:
            return _apply_structure(root, art)
        raise ConfigError(f"unhandled artifact kind: {art.kind}")  # pragma: no cover

    return apply


def _wiki_union_owned(assistants: tuple[AssistantId, ...]) -> SertorOwnedPaths:
    """Union of the wiki Sertor-owned paths across assistants (cross-assistant obsoletes)."""
    dirs: set[str] = set()
    files: set[str] = set()
    edits: list[SharedEdit] = []
    seen: set[str] = set()
    for a in assistants:
        owned = sertor_owned_paths(a)
        dirs |= set(owned.owned_dirs)
        files |= set(owned.owned_files)
        for e in owned.shared_edits:
            if e.target_rel not in seen:
                seen.add(e.target_rel)
                edits.append(e)
    # `wiki/` is purge-gated; never an automatic obsolete (handled by the CLI). Drop it from the
    # obsolete scope so an upgrade never removes the user's wiki content.
    dirs.discard("wiki")
    return SertorOwnedPaths(
        owned_dirs=tuple(sorted(dirs)), owned_files=tuple(sorted(files)), shared_edits=tuple(edits)
    )


def execute_wiki_lifecycle(
    plan: list[Artifact],
    profile: HostProfile,
    op: LifecycleOp,
    assistant: AssistantId = AssistantProfile.DEFAULT,
    dry_run: bool = False,
) -> InstallReport:
    """Executes the `wiki` plan with the lifecycle verb `op` via the kit orchestrator (feature 048).

    UNINSTALL preserves `wiki/` by default (FR-027 — the `--purge-wiki` gate lives in the CLI).
    UPGRADE scans cross-assistant owned paths for obsoletes (excluding `wiki/`). `dry_run` projects.
    """
    apply = make_wiki_apply(profile, assistant, dry_run=dry_run)
    owned = sertor_owned_paths(assistant)
    obsolete = _wiki_union_owned(tuple(AssistantId)) if op is LifecycleOp.UPGRADE else None
    # Owned dirs other than `wiki/` (purge-gated) are removed in block on uninstall (e.g. the
    # `.claude/skills/wiki-author` tree); `wiki/` is preserved unless --purge-wiki (handled in CLI).
    block_dirs = tuple(d for d in owned.owned_dirs if d != "wiki")
    return _kit_execute_lifecycle(
        plan, owned, apply, op=op, target=str(profile.target_root),
        capability="wiki", assistant=assistant.value, dry_run=dry_run,
        obsolete_owned=obsolete, uninstall_dirs_in_block=block_dirs,
    )
