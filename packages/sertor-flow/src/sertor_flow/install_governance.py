"""Orchestration of `sertor-flow install`: launch + plan + execution over the shared kit.

Thin consumer (Principle I): `sertor-flow` does NOT duplicate the installer primitives — they all
come from `sertor_install_kit` (artifacts, executor, marker block, resources, report, renderer,
command runner). This module (a) LAUNCHES SpecKit for the target assistant (feature 045: the
launch-installer pivot replaces the vendored SpecKit assets), then (b) derives the governance plan
for the Sertor-authored surfaces + constitution + generated init files + SDLC block, routing each
per-assistant via the `AssistantProfile` (Principle X), and (c) dispatches each `kind` to a
per-artifact `apply`.

The SpecKit commands/agents and `.specify/**` are NO LONGER vendored: they come from
`specify init --ai <assistant>` (see `speckit_launch.py`). The Sertor-authored surfaces
(`requirements-analyst`, `configuration-manager`, skill `requirements`) and the SDLC ritual block
are rendered for the target assistant from a SINGLE canonical source (the kit renderer, anti-drift).

Marker block: `SERTOR:SDLC-RITUAL` markers (distinct from the wiki's `SERTOR:WIKI-RITUAL`) so the
two blocks coexist in the same instruction file (D4).
"""
from __future__ import annotations

from pathlib import Path

from sertor_flow import generate
from sertor_flow.profile import GovernanceProfile
from sertor_flow.speckit_launch import launch_speckit
from sertor_install_kit import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    AssistantId,
    AssistantProfile,
    CommandRunner,
    ConfigError,
    InstallerError,
    InstallReport,
    Outcome,
    Surface,
    WriteStrategy,
    read_asset_text,
    render_custom_agent,
    render_prompt_file,
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

# Targets on the host (assistant-agnostic).
_CONSTITUTION_TARGET = ".specify/memory/constitution.md"

# Sertor-authored surfaces rendered per-assistant from a single canonical source (feature 045).
# Each: (canonical asset under assets/, Surface, logical name).
#   - For Claude the logical name is the path relative to `.claude/` (kept verbatim).
#   - For Copilot the logical name is the bare command/agent name (rendered into `.github/**`).
_AGENT_REQUIREMENTS_ANALYST = "claude/agents/requirements-analyst.md"
_AGENT_CONFIGURATION_MANAGER = "claude/agents/configuration-manager.md"
_SKILL_REQUIREMENTS = "claude/skills/requirements/SKILL.md"

_SERTOR_AUTHORED: tuple[tuple[str, Surface, str, str], ...] = (
    # (canonical_source, surface, claude_name, copilot_name)
    (_AGENT_REQUIREMENTS_ANALYST, Surface.AGENT,
     "agents/requirements-analyst.md", "requirements-analyst"),
    (_AGENT_CONFIGURATION_MANAGER, Surface.AGENT,
     "agents/configuration-manager.md", "configuration-manager"),
    (_SKILL_REQUIREMENTS, Surface.COMMAND,
     "skills/requirements/SKILL.md", "requirements"),
)

# Render suffixes (Copilot) — the apply callback translates the container, never the body.
_RENDER_PROMPT_SUFFIX = ".prompt.md"
_RENDER_AGENT_SUFFIX = ".agent.md"

# Generated per-host init/integration files: (template asset, host target). Assistant-agnostic
# targets; the per-assistant value is injected from the profile by `generate`.
_GENERATED: tuple[tuple[str, str], ...] = (
    (generate.INIT_OPTIONS_TMPL, generate.INIT_OPTIONS_TARGET),
    (generate.INTEGRATION_TMPL, generate.INTEGRATION_TARGET),
    (generate.CLAUDE_MANIFEST_TMPL, generate.CLAUDE_MANIFEST_TARGET),
    (generate.SPECKIT_MANIFEST_TMPL, generate.SPECKIT_MANIFEST_TARGET),
)


def build_governance_plan(profile: GovernanceProfile) -> list[Artifact]:
    """Ordered list of `Artifact` for the Sertor-authored surfaces (data-model §4, feature 045).

    SpecKit (commands/agents + `.specify/**`) is NOT in this plan: it is obtained by launching
    `specify init` before the plan runs (see `execute_governance_plan`). The plan covers only what
    Sertor authors and renders per-assistant via the `AssistantProfile` (Principle X):

    1. AGENT × N — `requirements-analyst`, `configuration-manager` → assistant-specific path
    2. COMMAND — skill `requirements` → assistant-specific path
    3. CONFIG — constitution-starter (assistant-agnostic, create-if-absent)
    4. CONFIG/GENERATE_CONFIG × M — generated init/integration files (assistant-agnostic targets)
    5. MARKER_BLOCK — SDLC ritual block → INSTRUCTION_BLOCK target of the assistant

    `claude` reproduces the historical Sertor-authored layout (`.claude/**` + `CLAUDE.md`);
    `copilot` renders the same content into `.github/**` (anti-drift: single canonical source).
    """
    aprofile = AssistantProfile.for_assistant(AssistantId.from_str(profile.assistant))
    plan: list[Artifact] = []

    # 1+2. Sertor-authored AGENT/COMMAND surfaces, routed per-assistant via the AssistantProfile.
    for source, surface, claude_name, copilot_name in _SERTOR_AUTHORED:
        name = claude_name if aprofile.assistant is AssistantId.CLAUDE else copilot_name
        target_rel = aprofile.render_path(surface, name)
        plan.append(
            Artifact(
                kind=ArtifactKind.FILE,
                source=source,
                target_rel=target_rel,
                strategy=WriteStrategy.CREATE_IF_ABSENT,
            )
        )

    # 3. CONFIG — constitution starter (assistant-agnostic, create-if-absent, FR-009/FR-014).
    plan.append(
        Artifact(
            kind=ArtifactKind.CONFIG,
            source=_CONSTITUTION_ASSET,
            target_rel=_CONSTITUTION_TARGET,
            strategy=WriteStrategy.CREATE_IF_ABSENT,
        )
    )

    # 4. CONFIG/GENERATE_CONFIG × M — generated init/integration files (D7, per-assistant values).
    for template_rel, target_rel in _GENERATED:
        plan.append(
            Artifact(
                kind=ArtifactKind.CONFIG,
                source=template_rel,
                target_rel=target_rel,
                strategy=WriteStrategy.GENERATE_CONFIG,
            )
        )

    # 5. MARKER_BLOCK — SDLC ritual block in the assistant's instruction file (D4, FR-008).
    instruction_target = aprofile.target_for(Surface.INSTRUCTION_BLOCK)
    assert instruction_target is not None  # both assistants materialize INSTRUCTION_BLOCK
    plan.append(
        Artifact(
            kind=ArtifactKind.MARKER_BLOCK,
            source=_SDLC_BLOCK_ASSET,
            target_rel=instruction_target.target_rel,
            strategy=WriteStrategy.APPEND_BLOCK,
        )
    )
    return plan


def _resolve(target_root: Path, target_rel: str) -> Path:
    """Resolves a `target_rel` under `target_root` (paths are validated as relative)."""
    return target_root / target_rel


def _render_for_target(art: Artifact) -> str:
    """Content for a FILE artifact: rendered for Copilot prompt/agent files, byte-copy otherwise.

    Rendered files (`*.prompt.md`/`*.agent.md`) are DERIVED from the canonical Claude asset
    (anti-drift): the body is reused verbatim, only the frontmatter/container is translated.
    """
    assert art.source is not None
    canonical = read_asset_text(_ANCHOR, art.source)
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
    """`APPEND_BLOCK`: idempotent SDLC marker block in the assistant's instruction file (D4).

    `block` when the block is written (even on a freshly created file); `skipped` only when the SDLC
    markers were already present.
    """
    dest = _resolve(target_root, art.target_rel)
    dest.parent.mkdir(parents=True, exist_ok=True)  # e.g. `.github/` for copilot-instructions.md
    assert art.source is not None
    block_content = read_asset_text(_ANCHOR, art.source)
    outcome = write_marker_block(dest, block_content, MARKER_START_SDLC, MARKER_END_SDLC)
    detail = "SDLC ritual block inserted" if outcome is Outcome.BLOCK else "block already present"
    return ArtifactOutcome(art.target_rel, outcome, detail)


def execute_governance_plan(
    profile: GovernanceProfile, runner: CommandRunner | None = None
) -> InstallReport:
    """Launches SpecKit then executes the governance plan via the kit's executor (fail-fast).

    Step 0 (feature 045): launch `specify init --ai <assistant>` (via `speckit_launch`, runner
    injected/mockable) to deposit the SpecKit commands/agents + `.specify/**`. Fail-fast: if the
    launch raises `InstallerError`, the report records it as an ERROR step and no Sertor-authored
    surface is applied (no partial state). Then the per-`kind` dispatch applies the Sertor-authored
    surfaces, constitution, generated init files and SDLC block. Returns an `InstallReport` with
    `capability="governance"` and the target assistant.
    """
    root = profile.target_root
    report = InstallReport(
        target=str(root), capability="governance", assistant=profile.assistant
    )

    # Step 0: obtain SpecKit by launching its installer (fail-fast on absence/failure/layout).
    try:
        launch_outcome = launch_speckit(profile, runner)
    except InstallerError as exc:
        report.add(ArtifactOutcome("specify init (speckit launch)", Outcome.ERROR, str(exc)))
        return report
    report.add(
        ArtifactOutcome(
            "specify init (speckit launch)",
            launch_outcome,
            f"assistant={profile.assistant}, version={profile.speckit_version}",
        )
    )

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

    plan_report = _kit_execute_plan(
        plan, apply, target=str(root), capability="governance", assistant=profile.assistant
    )
    # Merge the plan outcomes into the report that already carries the launch outcome.
    for outcome in plan_report.outcomes:
        report.add(outcome)
    return report
