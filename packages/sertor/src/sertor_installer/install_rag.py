"""Orchestration of `sertor install rag` (data-model §4, plan 015) over the shared kit (037).

`build_rag_plan` enumerates artifacts in canonical order (DEPENDENCIES → ENV_MERGE → MCP_MERGE →
GITIGNORE_APPEND); execution delegates to the kit's generic `execute_plan` with **fail-fast
no-rollback**: on the first domain error it records the error outcome, sets `failed_step`, and
stops; already-written artifacts remain (a re-run will find them → skipped/merged).

**install ≠ run**: the DEPENDENCIES step only runs `uv init`/`uv add` (never indexing). The runtime
lives isolated in `<target>/.sertor/`; `.mcp.json` and `.gitignore` live in the host root. Thin
layer (Principio I): `uv` is behind the injectable `CommandRunner`. Errors are the kit's
`InstallerError` (037, D3): the executor catches them for fail-fast.
"""
from __future__ import annotations

import json
import logging

from sertor_install_kit import host_env
from sertor_install_kit.artifacts import LifecycleOp
from sertor_install_kit.assistant import AssistantId, AssistantProfile, Surface
from sertor_install_kit.claude_md import (
    remove_marker_block,
    update_marker_block,
    write_marker_block,
)
from sertor_install_kit.command_runner import CommandRunner
from sertor_install_kit.env_merge import merge_env
from sertor_install_kit.errors import ConfigError, InstallerError
from sertor_install_kit.executor import execute_plan as _kit_execute_plan
from sertor_install_kit.gitignore_append import (
    RUNTIME_IGNORES,
    append_gitignore,
    remove_gitignore_lines,
)
from sertor_install_kit.lifecycle import (
    SertorOwnedPaths,
    SharedEdit,
    SharedEditKind,
    deregister_mcp_client,
    project_removal,
    project_update,
    remove_path,
    update_file_if_changed,
)
from sertor_install_kit.lifecycle import (
    execute_lifecycle as _kit_execute_lifecycle,
)
from sertor_install_kit.mcp_merge import merge_mcp, remove_mcp_server
from sertor_install_kit.model_policy import resolve_model
from sertor_install_kit.observability import log_event
from sertor_install_kit.settings_merge import merge_settings, remove_settings_entries
from sertor_installer.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    Outcome,
    WriteStrategy,
)
from sertor_installer.rag_profile import RagHostProfile
from sertor_installer.report import InstallReport
from sertor_installer.resources import read_asset_text
from sertor_installer.surfaces import HookEntrySpec, render_copilot_hooks, render_custom_agent

_UV = "uv"
# `uv init` uses the folder name as the package name: `.sertor` is INVALID (starts with a dot) →
# use an explicit valid name for the host runtime project (never published).
_RUNTIME_NAME = "sertor-runtime"

_CLAUDE = "claude"
_SERVER_NAME = "sertor-rag"
# Human-readable sentinel (NOT a repo path): in local scope nothing is written to the repository
# (feature 016, F1 analyze). Passes `Artifact` validation (relative, no `..`).
_MCP_REGISTER_LABEL = "(mcp: client registry)"

# Group B (Principio XI, feature 042): host-facing RAG usage instruction block, routed per-assistant
# (feature 044: `CLAUDE.md` for Claude, `.github/copilot-instructions.md` for Copilot — the target
# comes from the `AssistantProfile`). Own marker pair, DISTINCT from the wiki (`SERTOR:WIKI-RITUAL`)
# and SDLC (`SERTOR:SDLC-RITUAL`) blocks so the three coexist, each idempotent on its own markers.
_RAG_USAGE_BLOCK = "rag/claude-md-block-rag-usage.md"
MARKER_START_RAG = "<!-- SERTOR:RAG-USAGE START -->"
MARKER_END_RAG = "<!-- SERTOR:RAG-USAGE END -->"

# E10-FEAT-021: the single source of truth for "How to invoke Sertor's commands" (the two-level CLI
# guidance + Windows note). The reduced RAG usage block and the guided-setup skill POINT here by
# name instead of repeating the section inline (one canonical copy → no drift). Deposited as a FILE
# in the shared runtime `.sertor/` (host-agnostic, identical on Claude and Copilot CLI), owned via
# the `.sertor` owned_dir (removed in block on uninstall, updated on upgrade). No new ArtifactKind.
_CLI_REFERENCE_ASSET = "rag/sertor-cli-reference.md"
_CLI_REFERENCE_TARGET = ".sertor/sertor-cli-reference.md"

# Group C (Principio XI, feature 042): host-specific PreToolUse hook (adapter of the trigger).
# Its absence MUST NOT break the RAG capability (Principio X).
_RAG_HOOK_ASSET = "rag/hooks/sertor-rag-usage-check.ps1"
_RAG_HOOK_TARGET = ".claude/hooks/sertor-rag-usage-check.ps1"
_RAG_USAGE_SETTINGS = "rag/settings.rag-usage.json"
_SETTINGS_TARGET = ".claude/settings.json"

# Ground-truth eval skills (065, FEAT-001): the eval-authoring/feedback skills travel with the RAG
# capability so the eval suite can be created/refined on the host ("feature complete only if
# installable", Principio X). Host-agnostic bodies (CLI vehicle only, no slash-commands, no model
# names) → byte-copied to each assistant's native skill container (`.claude/skills/` for Claude,
# `.github/skills/` for the Copilot CLI). Single-file skills (no cross-references → closure
# trivially satisfied). Source asset tree under `rag/skills/<name>/SKILL.md`.
_EVAL_SKILL_NAMES = ("eval-suite-author", "eval-feedback")
# Usability skills (E12): the guided-setup skill travels with the RAG capability so a host can be
# walked from "nothing configured" to "RAG verified" via the deterministic vehicles. Same byte-copy,
# host-agnostic native-skill mechanism as the eval skills (single-file, no cross-references).
_USABILITY_SKILL_NAMES = ("guided-setup",)
_CLAUDE_SKILLS_BASE = ".claude/skills"
_COPILOT_SKILLS_BASE = ".github/skills"

# Concierge agent (E12, anticipates FEAT-009): a real agent (model-pinned on Claude), distributed
# dual-target like sertor-flow's agents (`requirements-analyst`/`configuration-manager`). A thin
# single-branch dispatcher routing setup requests to the `guided-setup` skill. The body is host-
# agnostic; the `model:` pin is preserved on Claude and OMITTED on Copilot by `render_custom_agent`.
_CONCIERGE_AGENT_SRC = "rag/agents/concierge.md"


class DependencyError(InstallerError):
    """Dependency bootstrap failed: `uv` not found or `uv init`/`uv add` did not succeed."""


class McpRegistrationError(InstallerError):
    """MCP registration in `local` scope failed: `claude` not found or command failed."""


# Copilot rag surfaces (feature 044): host-facing artifacts under `.github/**` (script reused).
_RAG_HOOK_TARGET_COPILOT = ".github/hooks/sertor-rag-usage-check.ps1"
# FEAT-011: the Copilot PreToolUse wiring is GENERATED natively (render_copilot_hooks). The sentinel
# source marks the GENERATED rag wiring so the apply callback builds it instead of reading a file.
_COPILOT_RAG_WIRING_SENTINEL = "(generated: copilot rag-usage hooks)"
_COPILOT_HOOK_WIRING = ".github/hooks/sertor-hooks.json"
_PWSH = "pwsh -File"
_RAG_MATCHER = "Bash|Write|Edit|MultiEdit"


def _copilot_rag_hook_specs() -> list[HookEntrySpec]:
    """Logical PreToolUse entry for the Copilot rag-usage wiring (FEAT-011, FR-008).

    Fail-open by design: the script exits 0 always and emits no `deny` payload; the wiring just
    invokes it with `-Assistant copilot` on the tool matcher.
    """
    return [
        HookEntrySpec(
            "PreToolUse", "command",
            f"{_PWSH} {_RAG_HOOK_TARGET_COPILOT} -Assistant copilot", 10,
            matcher=_RAG_MATCHER,
        )
    ]


# Conversation-memory capture (FEAT-009, feature 071): the capture hook + SessionEnd wiring travel
# WITH the rag capability (shared runtime `.sertor/`, CLI `sertor-rag`, `.env`). The script body is
# REUSED IDENTICALLY across assistants (no `-Assistant`: it is already a silent, exit-0 SessionEnd
# wrapper); only the container/wiring is translated per assistant. Same FILE + SETTINGS_MERGE
# pattern as the rag-usage hook above (no new ArtifactKind). On Copilot the wiring is deposited and
# the Copilot capture adapter exists (E5-FEAT-008, 2026-06-22), but the installer does NOT yet
# distribute the adapter VALUE (`SERTOR_MEMORY_ADAPTER=copilot-cli`) in the `.env` template — that
# is FEAT-009 (memory-conversations epic). So out of the box the Copilot wiring fires with the
# default adapter and captures nothing useful; `execute_rag_plan` surfaces an honest note (018).
_MEMORY_HOOK_ASSET = "rag/hooks/memory-capture.ps1"
_MEMORY_HOOK_TARGET = ".claude/hooks/memory-capture.ps1"
_MEMORY_HOOK_TARGET_COPILOT = ".github/hooks/memory-capture.ps1"
_MEMORY_CAPTURE_SETTINGS = "rag/settings.memory-capture.json"
_COPILOT_MEMORY_WIRING_SENTINEL = "(generated: copilot memory-capture hooks)"

# E10-FEAT-018 (Nota B, contracts/install-notes.md): honest caveat emitted on every
# `install rag --assistant copilot-cli`, independent of the runtime `SERTOR_MEMORY` value
# (install-time does not know it — decision D-2). The memory-capture hook is wired but inert with
# the default adapter; capturing Copilot CLI sessions needs both env knobs set explicitly.
_COPILOT_MEMORY_NOTE = (
    "memory-capture is wired but requires SERTOR_MEMORY=true and an explicit Copilot adapter "
    "value for SERTOR_MEMORY_ADAPTER (=copilot-cli) to capture Copilot CLI sessions — with the "
    "default the hook fires but captures nothing useful. Out-of-the-box completion is planned "
    "(distribution of the adapter value in the .env template, tracked in the memory-conversations "
    "epic / FEAT-009)."
)


def _copilot_memory_hook_specs() -> list[HookEntrySpec]:
    """Logical SessionEnd entry for the Copilot memory-capture wiring (FEAT-009, FR-014).

    Non-blocking by design: the script is privacy-gated (no-op unless SERTOR_MEMORY is on) and
    always exits 0. The wiring just invokes it at session end (no matcher, native `sessionEnd`).
    """
    return [
        HookEntrySpec(
            "SessionEnd", "command",
            f"{_PWSH} {_MEMORY_HOOK_TARGET_COPILOT}", 15,
        )
    ]


# RAG freshness hook – SessionEnd (E10-FEAT-011): re-index + doctor + persist health state. Travels
# WITH the rag capability (shared runtime `.sertor/`, CLI `sertor-rag`). Same FILE + SETTINGS_MERGE
# pattern as memory-capture (no new ArtifactKind). The script body is host-agnostic, exits 0 always,
# and NEVER imports `sertor_core` (Principio XI) — it consumes the `sertor-rag` vehicles only.
_FRESHNESS_HOOK_ASSET = "rag/hooks/rag-freshness.ps1"
_FRESHNESS_HOOK_TARGET = ".claude/hooks/rag-freshness.ps1"
_FRESHNESS_HOOK_TARGET_COPILOT = ".github/hooks/rag-freshness.ps1"
_FRESHNESS_SETTINGS = "rag/settings.rag-freshness.json"
_COPILOT_FRESHNESS_END_WIRING_SENTINEL = "(generated: copilot freshness-end hooks)"

# RAG freshness signal – SessionStart (E10-FEAT-011): re-read the persisted state and INDUCE a fix
# when degraded. On Claude this is a dedicated script (`rag-freshness-start.ps1`); on Copilot CLI it
# is a NATIVE static prompt (no script deposited — W5 of the wiring contract).
_FRESHNESS_START_ASSET = "rag/hooks/rag-freshness-start.ps1"
_FRESHNESS_START_TARGET = ".claude/hooks/rag-freshness-start.ps1"
_FRESHNESS_START_SETTINGS = "rag/settings.rag-freshness-start.json"
_COPILOT_FRESHNESS_START_WIRING_SENTINEL = "(generated: copilot freshness-start hooks)"


def _copilot_freshness_end_specs() -> list[HookEntrySpec]:
    """Logical SessionEnd entry for the Copilot RAG-freshness wiring (E10-FEAT-011, W1).

    Native flat format (`version:1`/`timeoutSec`) via `render_copilot_hooks` — never the Claude
    nested form (lezione FEAT-011/049). Non-blocking: the script exits 0 always.
    """
    return [
        HookEntrySpec(
            # E10-FEAT-016 refinement: the foreground only spawns the detached worker (doctor AND
            # index run off the critical path), so the timeout only covers that spawn. Parity with
            # Claude `settings.rag-freshness.json` (15s).
            "SessionEnd", "command",
            f"{_PWSH} {_FRESHNESS_HOOK_TARGET_COPILOT}", 15,
        )
    ]


def _copilot_freshness_start_specs() -> list[HookEntrySpec]:
    """Logical SessionStart entry for the Copilot RAG-freshness signal (E10-FEAT-011, W5).

    A STATIC PROMPT (no script on Copilot CLI — A-005): the agent reads the persisted state and
    induces the fix. D<->N: the prompt induces, the agent executes the vehicles.
    """
    return [
        HookEntrySpec(
            "SessionStart", "prompt",
            "At startup: read .sertor/.rag-health.json. "
            "If verdict=degraded, surface the degradation (reason) and induce the fix "
            "— run `sertor-rag index .` and/or reconnect the MCP server — "
            "BEFORE starting work. If healthy/absent, proceed.",
            10,
        )
    ]


# Version-update check hook – SessionEnd (E2-FEAT-013): GET the remote `/VERSION`, compare with the
# install-time stamp, persist the verdict to `.sertor/.version-check.json`. Travels WITH the rag
# capability (shared runtime `.sertor/`). Same FILE + SETTINGS_MERGE pattern as rag-freshness (no
# new ArtifactKind). The script body is host-agnostic, exits 0 always, and NEVER imports
# `sertor_core` nor runs Python (Principio XI) — it does only HTTP+file (FR-014). Twin of
# rag-freshness but the check is HTTP+file, not a CLI vehicle.
_VERSION_CHECK_HOOK_ASSET = "rag/hooks/version-check.ps1"
_VERSION_CHECK_HOOK_TARGET = ".claude/hooks/version-check.ps1"
_VERSION_CHECK_HOOK_TARGET_COPILOT = ".github/hooks/version-check.ps1"
_VERSION_CHECK_SETTINGS = "rag/settings.version-check.json"
_COPILOT_VERSION_CHECK_END_WIRING_SENTINEL = "(generated: copilot version-check-end hooks)"

# Version-update check signal – SessionStart (E2-FEAT-013): read the persisted state and warn if
# behind. On Claude this is a dedicated script (`version-check-start.ps1`); on Copilot CLI it is a
# NATIVE static prompt (no script deposited — W5 of the wiring contract).
_VERSION_CHECK_START_ASSET = "rag/hooks/version-check-start.ps1"
_VERSION_CHECK_START_TARGET = ".claude/hooks/version-check-start.ps1"
_VERSION_CHECK_START_SETTINGS = "rag/settings.version-check-start.json"
_COPILOT_VERSION_CHECK_START_WIRING_SENTINEL = "(generated: copilot version-check-start hooks)"

# Install-time version stamp (E2-FEAT-013, D-3): the installer writes the installed version of the
# `sertor` package into `.sertor/.sertor-version` so the hook compares it WITHOUT running Python in
# the hot path. Rewritten on upgrade (closes the loop — INV-5/FR-013), removed with `.sertor/`.
_VERSION_STAMP_TARGET = ".sertor/.sertor-version"


def _copilot_version_check_end_specs() -> list[HookEntrySpec]:
    """Logical SessionEnd entry for the Copilot version-check wiring (E2-FEAT-013, W1).

    Native flat format (`version:1`/`timeoutSec`) via `render_copilot_hooks` — never the Claude
    nested form (lezione FEAT-011/049). Non-blocking: the script exits 0 always.
    """
    return [
        HookEntrySpec(
            "SessionEnd", "command",
            f"{_PWSH} {_VERSION_CHECK_HOOK_TARGET_COPILOT}", 15,
        )
    ]


def _copilot_version_check_start_specs() -> list[HookEntrySpec]:
    """Logical SessionStart entry for the Copilot version-check signal (E2-FEAT-013, W5).

    A STATIC PROMPT (no script on Copilot CLI — A-005): the agent reads the persisted state and
    relays the notice if behind. D<->N: the prompt induces, the agent only warns (never updates).
    """
    return [
        HookEntrySpec(
            "SessionStart", "prompt",
            "At startup: read .sertor/.version-check.json. "
            "If verdict=behind, surface the update notice (installed version, latest version, "
            "the update command `sertor upgrade` / `uvx --refresh ...`); "
            "if dimensions are present, name which dimensions are behind. "
            "Do not apply any update yourself. "
            "If up-to-date/ahead/unknown/absent, proceed without a notice.",
            10,
        )
    ]


def _write_version_stamp(profile: RagHostProfile) -> None:
    """Write the install-time version stamp `.sertor/.sertor-version` (E2-FEAT-013, D-3/R-4).

    The version is read IN-PROCESS at install/upgrade time via `importlib.metadata.version`
    — NEVER by the hook at runtime (Principio XI: no Python in the hot path). Non-fatal: a failure
    to resolve the version must not break the install (the hook degrades to `verdict: unknown`).
    """
    try:
        import importlib.metadata as _imeta

        version = _imeta.version("sertor")
    except Exception:  # pragma: no cover - version unresolvable (e.g. editable without metadata)
        return
    sertor_dir = profile.sertor_dir
    sertor_dir.mkdir(parents=True, exist_ok=True)
    (sertor_dir / ".sertor-version").write_text(version + "\n", encoding="utf-8")


def _skill_artifacts(names: tuple[str, ...], is_copilot: bool) -> list[Artifact]:
    """FILE artifacts for native skills, routed to each assistant's skill container (065, E12).

    Generalized from `_eval_skill_artifacts` (DRY, Principio III): the eval and usability skills
    share the byte-copy mechanism (single-file, host-agnostic native-skill bodies). `names` is the
    tuple of skill names to deposit under `{base}/<name>/SKILL.md`.
    """
    base = _COPILOT_SKILLS_BASE if is_copilot else _CLAUDE_SKILLS_BASE
    return [
        Artifact(
            ArtifactKind.FILE,
            f"rag/skills/{name}/SKILL.md",
            f"{base}/{name}/SKILL.md",
            WriteStrategy.CREATE_IF_ABSENT,
        )
        for name in names
    ]


def _concierge_artifact(assistant: AssistantId) -> Artifact:
    """FILE artifact for the `concierge` agent, routed per-assistant (E12, sertor-flow pattern).

    Replicates `install_governance.py`'s AGENT routing for a single surface: Claude keeps the
    `.claude/agents/concierge.md` byte-copy layout (the `model: sonnet` pin is preserved); Copilot
    renders `.github/agents/concierge.agent.md` via `render_custom_agent` (the `model:` field is
    OMITTED on Copilot — FEAT-011/049). Container resolved by `AssistantProfile.render_path`.
    """
    aprofile = AssistantProfile.for_assistant(assistant)
    name = "agents/concierge.md" if assistant is AssistantId.CLAUDE else "concierge"
    target_rel = aprofile.render_path(Surface.AGENT, name)
    return Artifact(
        ArtifactKind.FILE,
        _CONCIERGE_AGENT_SRC,
        target_rel,
        WriteStrategy.CREATE_IF_ABSENT,
    )


def _render_rag_file(art: Artifact) -> str:
    """Content for a rag FILE artifact: rendered for a Copilot custom-agent, byte-copy otherwise.

    Local render-aware helper (a `_render_for_target` twin of `install_wiki`/
    `install_governance`), NOT a new kit seam (`render_custom_agent` is already exported).
    The `.agent.md` branch maps the Claude frontmatter to the Copilot custom-agent shape,
    substituting the POLICY model-ID (E2-FEAT-015) — never echoing the Claude alias. Every
    other FILE (native skill `.md`, hook `.ps1`) is reused verbatim (byte-copy).
    """
    assert art.source is not None
    text = read_asset_text(art.source)
    if art.target_rel.endswith(".agent.md"):
        name = art.target_rel.rsplit("/", 1)[-1].removesuffix(".agent.md")
        return render_custom_agent(text, model=resolve_model(name))
    return text


def build_rag_plan(
    profile: RagHostProfile,
    with_deps: bool = True,
    mcp_scope: str = "project",
    assistant: AssistantId = AssistantProfile.DEFAULT,
) -> list[Artifact]:
    """Ordered list of `Artifact`, parametric on the target `assistant`.

    `with_deps=False` skips DEPENDENCIES. `mcp_scope` (feature 016) selects how the MCP server is
    registered: `project` → merge into the assistant's MCP config; `local` → register in the client
    via the `claude` CLI (Claude only; NO file in the repo, `MCP_REGISTER` instead of `MCP_MERGE`).
    The host-facing surfaces (MCP config, instruction block, hook) route via the `AssistantProfile`
    (Principio X): `claude` reproduces the historical plan (non-regression); `copilot-cli` targets
    `.mcp.json`/`.github/**`.
    """
    aprofile = AssistantProfile.for_assistant(assistant)
    # The Copilot CLI shares the `.github/**` host-facing surfaces; its MCP container is `.mcp.json`
    # (mcpServers), resolved via the AssistantProfile.
    is_copilot = assistant is AssistantId.COPILOT_CLI
    if is_copilot:
        # Fail-loud BEFORE any artifact is written (FR-008/009, DA-D-4): this plan deposits a
        # single Copilot agent (`concierge`) — validate the policy covers it up front.
        resolve_model("concierge")

    plan: list[Artifact] = []
    if with_deps:
        plan.append(
            Artifact(ArtifactKind.DEPENDENCIES, None, ".sertor", WriteStrategy.BOOTSTRAP_DEPS)
        )
    # ENV / DEPENDENCIES / GITIGNORE are assistant-agnostic (runtime confined to `.sertor/`).
    plan.append(
        Artifact(
            ArtifactKind.ENV_MERGE,
            f"rag/env.{profile.backend}.tmpl",
            ".sertor/.env",
            WriteStrategy.MERGE_ENV,
        )
    )
    # MCP_SERVER: local scope (claude only) registers in the client; otherwise merge into the
    # assistant's MCP config (`.mcp.json`, `mcpServers`).
    if mcp_scope == "local" and not is_copilot:
        plan.append(
            Artifact(
                ArtifactKind.MCP_REGISTER,
                "rag/mcp.server.json.tmpl",
                _MCP_REGISTER_LABEL,
                WriteStrategy.REGISTER_CLI,
            )
        )
    else:
        mcp_target = aprofile.target_for(Surface.MCP_SERVER)
        plan.append(
            Artifact(
                ArtifactKind.MCP_MERGE,
                "rag/mcp.server.json.tmpl",
                mcp_target.target_rel,
                WriteStrategy.MERGE_JSON,
            )
        )
    plan.append(
        Artifact(ArtifactKind.GITIGNORE_APPEND, None, ".gitignore", WriteStrategy.APPEND_LINES)
    )
    # Group B (042): host-facing RAG usage instruction block (own markers), routed per-assistant.
    plan.append(
        Artifact(
            ArtifactKind.MARKER_BLOCK,
            _RAG_USAGE_BLOCK,
            aprofile.target_for(Surface.INSTRUCTION_BLOCK).target_rel,
            WriteStrategy.APPEND_BLOCK,
        )
    )
    # Group C (042): anti-bypass hook — script REUSED identically (FR-014), wiring per-assistant.
    # FEAT-011: the Copilot wiring is GENERATED natively (sentinel source), not a static asset.
    hook_target = _RAG_HOOK_TARGET_COPILOT if is_copilot else _RAG_HOOK_TARGET
    settings_source = _COPILOT_RAG_WIRING_SENTINEL if is_copilot else _RAG_USAGE_SETTINGS
    settings_target = _COPILOT_HOOK_WIRING if is_copilot else _SETTINGS_TARGET
    plan.append(
        Artifact(
            ArtifactKind.FILE,
            _RAG_HOOK_ASSET,
            hook_target,
            WriteStrategy.CREATE_IF_ABSENT,
        )
    )
    # Host-root line-ending policy: deposit `.gitattributes` (LF) so the install (and any later tool
    # that rewrites a file on Windows) produces a clean, review-able diff. CREATE_IF_ABSENT:
    # non-destructive — a host that already owns a `.gitattributes` keeps its own (Principio VI/X).
    plan.append(
        Artifact(
            ArtifactKind.FILE,
            "rag/gitattributes",
            ".gitattributes",
            WriteStrategy.CREATE_IF_ABSENT,
        )
    )
    plan.append(
        Artifact(
            ArtifactKind.SETTINGS_MERGE,
            settings_source,
            settings_target,
            WriteStrategy.MERGE_DEDUP,
        )
    )
    # E10-FEAT-021: the canonical "How to invoke" reference (`.sertor/sertor-cli-reference.md`),
    # pointed to by name from the reduced RAG usage block and the guided-setup skill. Assistant-
    # agnostic FILE byte-copy (same mechanism as the hooks/skills); owned via `.sertor` owned_dir.
    plan.append(
        Artifact(
            ArtifactKind.FILE,
            _CLI_REFERENCE_ASSET,
            _CLI_REFERENCE_TARGET,
            WriteStrategy.CREATE_IF_ABSENT,
        )
    )
    # Ground-truth eval skills (065): native skill bodies, byte-copied per-assistant (FILE).
    plan.extend(_skill_artifacts(_EVAL_SKILL_NAMES, is_copilot))
    # Usability skills + concierge agent (E12): the guided-setup skill (byte-copy) and the concierge
    # agent (model-pinned on Claude, rendered for Copilot). Order: eval → usability → agent.
    plan.extend(_skill_artifacts(_USABILITY_SKILL_NAMES, is_copilot))
    plan.append(_concierge_artifact(assistant))
    # Conversation-memory capture (FEAT-009): hook script (FILE) + SessionEnd wiring
    # (SETTINGS_MERGE), routed per-assistant — mirrors the rag-usage hook. Copilot wiring generated
    # (sentinel source); the Claude wiring is the static JSON asset.
    memory_hook_target = _MEMORY_HOOK_TARGET_COPILOT if is_copilot else _MEMORY_HOOK_TARGET
    memory_settings_source = (
        _COPILOT_MEMORY_WIRING_SENTINEL if is_copilot else _MEMORY_CAPTURE_SETTINGS
    )
    memory_settings_target = _COPILOT_HOOK_WIRING if is_copilot else _SETTINGS_TARGET
    plan.append(
        Artifact(
            ArtifactKind.FILE,
            _MEMORY_HOOK_ASSET,
            memory_hook_target,
            WriteStrategy.CREATE_IF_ABSENT,
        )
    )
    plan.append(
        Artifact(
            ArtifactKind.SETTINGS_MERGE,
            memory_settings_source,
            memory_settings_target,
            WriteStrategy.MERGE_DEDUP,
        )
    )
    # RAG freshness hook (E10-FEAT-011): SessionEnd script (FILE) + SessionEnd wiring + a
    # SessionStart signal. Mirrors the memory-capture pattern; the SessionStart Claude script is a
    # dedicated FILE, while on Copilot the SessionStart is a static prompt (no script — W5). All
    # artifacts are additive (appended in canonical order, pre-existing untouched — SC-010).
    freshness_hook_target = (
        _FRESHNESS_HOOK_TARGET_COPILOT if is_copilot else _FRESHNESS_HOOK_TARGET
    )
    freshness_end_source = (
        _COPILOT_FRESHNESS_END_WIRING_SENTINEL if is_copilot else _FRESHNESS_SETTINGS
    )
    freshness_settings_target = _COPILOT_HOOK_WIRING if is_copilot else _SETTINGS_TARGET
    plan.append(
        Artifact(
            ArtifactKind.FILE,
            _FRESHNESS_HOOK_ASSET,
            freshness_hook_target,
            WriteStrategy.CREATE_IF_ABSENT,
        )
    )
    plan.append(
        Artifact(
            ArtifactKind.SETTINGS_MERGE,
            freshness_end_source,
            freshness_settings_target,
            WriteStrategy.MERGE_DEDUP,
        )
    )
    # SessionStart signal: Claude deposits a dedicated script; Copilot deposits only the static
    # prompt wiring (no `.ps1` — W5 of the wiring contract, data-model §4 note (b)).
    if not is_copilot:
        plan.append(
            Artifact(
                ArtifactKind.FILE,
                _FRESHNESS_START_ASSET,
                _FRESHNESS_START_TARGET,
                WriteStrategy.CREATE_IF_ABSENT,
            )
        )
    freshness_start_source = (
        _COPILOT_FRESHNESS_START_WIRING_SENTINEL if is_copilot else _FRESHNESS_START_SETTINGS
    )
    plan.append(
        Artifact(
            ArtifactKind.SETTINGS_MERGE,
            freshness_start_source,
            freshness_settings_target,
            WriteStrategy.MERGE_DEDUP,
        )
    )
    # Version-update check hook (E2-FEAT-013): SessionEnd script (FILE) + SessionEnd wiring + a
    # SessionStart signal (Claude script / Copilot static prompt). Twin of rag-freshness but the
    # check is HTTP+file, never a vehicle. Additive (appended in canonical order — SC-010).
    version_check_target = (
        _VERSION_CHECK_HOOK_TARGET_COPILOT if is_copilot else _VERSION_CHECK_HOOK_TARGET
    )
    version_check_end_source = (
        _COPILOT_VERSION_CHECK_END_WIRING_SENTINEL if is_copilot else _VERSION_CHECK_SETTINGS
    )
    version_check_settings_target = _COPILOT_HOOK_WIRING if is_copilot else _SETTINGS_TARGET
    plan.append(
        Artifact(
            ArtifactKind.FILE,
            _VERSION_CHECK_HOOK_ASSET,
            version_check_target,
            WriteStrategy.CREATE_IF_ABSENT,
        )
    )
    plan.append(
        Artifact(
            ArtifactKind.SETTINGS_MERGE,
            version_check_end_source,
            version_check_settings_target,
            WriteStrategy.MERGE_DEDUP,
        )
    )
    # SessionStart signal: Claude deposits a dedicated script; Copilot deposits only the static
    # prompt wiring (no `.ps1` — W5 of the wiring contract, data-model §5 note (a)).
    if not is_copilot:
        plan.append(
            Artifact(
                ArtifactKind.FILE,
                _VERSION_CHECK_START_ASSET,
                _VERSION_CHECK_START_TARGET,
                WriteStrategy.CREATE_IF_ABSENT,
            )
        )
    version_check_start_source = (
        _COPILOT_VERSION_CHECK_START_WIRING_SENTINEL
        if is_copilot
        else _VERSION_CHECK_START_SETTINGS
    )
    plan.append(
        Artifact(
            ArtifactKind.SETTINGS_MERGE,
            version_check_start_source,
            version_check_settings_target,
            WriteStrategy.MERGE_DEDUP,
        )
    )
    return plan


def _apply_deps(profile: RagHostProfile, runner: CommandRunner) -> ArtifactOutcome:
    """`BOOTSTRAP_DEPS`: `uv init --bare` (if pyproject is missing) + `uv add` inside `.sertor/`.

    Checks for `uv` BEFORE creating `.sertor/` (REQ-214: avoids partial state). Never indexes.
    """
    if not runner.is_available(_UV):
        raise DependencyError(
            "`uv` is not available on the PATH: install it (https://docs.astral.sh/uv/) and re-run"
        )
    sertor_dir = profile.sertor_dir
    sertor_dir.mkdir(parents=True, exist_ok=True)
    already = (sertor_dir / "pyproject.toml").exists()
    if not already:
        res = runner.run([_UV, "init", "--bare", "--name", _RUNTIME_NAME], cwd=sertor_dir)
        if not res.ok:
            raise DependencyError(f"`uv init` failed: {res.stderr.strip() or res.returncode}")
    spec = profile.dep_spec()
    res = runner.run([_UV, "add", spec], cwd=sertor_dir)
    if not res.ok:
        raise DependencyError(f"`uv add` failed: {res.stderr.strip() or res.returncode}")
    outcome = Outcome.SKIPPED if already else Outcome.CREATED
    return ArtifactOutcome(".sertor", outcome, f"uv add {spec}")


def _apply_env(profile: RagHostProfile) -> ArtifactOutcome:
    """`MERGE_ENV`: `.sertor/.env` from the backend template (empty secrets), additive merge.

    Also writes the install-time version stamp `.sertor/.sertor-version` (E2-FEAT-013, D-3): this
    step always runs (with or without DEPENDENCIES), so it is the reliable anchor for the stamp.
    Writing the stamp is non-fatal and does not alter the env outcome.
    """
    rendered = read_asset_text(f"rag/env.{profile.backend}.tmpl").format(corpus=profile.corpus)
    outcome, detail = merge_env(profile.sertor_dir / ".env", rendered)
    _write_version_stamp(profile)  # E2-FEAT-013: install-time stamp (in-process, never the hook)
    return ArtifactOutcome(".sertor/.env", outcome, detail)


def _apply_mcp(profile: RagHostProfile, art: Artifact) -> ArtifactOutcome:
    """`MERGE_JSON`: `sertor-rag` server in the MCP config, additive merge.

    Both supported targets use `.mcp.json` with the `mcpServers` root (Claude-standard; the Copilot
    CLI reads it too) — resolved via the assistant profile.
    """
    entry = json.loads(read_asset_text("rag/mcp.server.json.tmpl").format(corpus=profile.corpus))
    outcome, detail = merge_mcp(profile.target_root / art.target_rel, entry, root_key="mcpServers")
    return ArtifactOutcome(art.target_rel, outcome, detail)


def _apply_gitignore(profile: RagHostProfile) -> ArtifactOutcome:
    """`APPEND_LINES`: runtime entries in `.gitignore` (host root), dedup."""
    outcome, detail = append_gitignore(profile.target_root / ".gitignore")
    return ArtifactOutcome(".gitignore", outcome, detail)


def _apply_rag_usage_block(profile: RagHostProfile, art: Artifact) -> ArtifactOutcome:
    """`APPEND_BLOCK` (042, group B): RAG usage instruction block, routed per-assistant.

    Reuses the kit's `write_marker_block` with the OWN markers (`SERTOR:RAG-USAGE`), distinct from
    the wiki/SDLC blocks → the three coexist, each idempotent on its own markers. Target is the
    artifact's `target_rel` (`CLAUDE.md` for Claude, `.github/copilot-instructions.md` for Copilot).
    Existing content outside the markers is preserved byte-for-byte.
    """
    dest = profile.target_root / art.target_rel
    dest.parent.mkdir(parents=True, exist_ok=True)  # e.g. `.github/` for copilot-instructions.md
    content = read_asset_text(_RAG_USAGE_BLOCK)
    outcome = write_marker_block(dest, content, MARKER_START_RAG, MARKER_END_RAG)
    detail = "RAG-usage block inserted" if outcome is Outcome.BLOCK else "block already present"
    return ArtifactOutcome(art.target_rel, outcome, detail)


def _apply_rag_file(profile: RagHostProfile, art: Artifact) -> ArtifactOutcome:
    """`CREATE_IF_ABSENT`: render-aware copy of a FILE asset; exists → skip.

    Render-aware (W4, E12): a Copilot custom-agent (`.agent.md`) is rendered via `_render_rag_file`
    (frontmatter translated, `model:` omitted); every other FILE (hook `.ps1`, native skill `.md`,
    Claude agent `.md`) is byte-copied. The `.ps1`/`.md` targets never end in `.agent.md` → no
    regression on the hook scripts or the eval skills.
    """
    dest = profile.target_root / art.target_rel
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "already present")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_render_rag_file(art), encoding="utf-8")
    return ArtifactOutcome(art.target_rel, Outcome.CREATED)


def _rag_hook_fragment(art: Artifact) -> dict:
    """The PreToolUse hook fragment for the settings merge/remove (single source).

    FEAT-011: the Copilot wiring is GENERATED natively via `render_copilot_hooks` (sentinel source);
    the Claude wiring is read from the static JSON asset. Art-aware: it serves BOTH the rag-usage
    (PreToolUse) and the memory-capture (SessionEnd, FEAT-009) wirings from the same dispatch.
    """
    if art.source == _COPILOT_RAG_WIRING_SENTINEL:
        return render_copilot_hooks(_copilot_rag_hook_specs())
    if art.source == _COPILOT_MEMORY_WIRING_SENTINEL:
        return render_copilot_hooks(_copilot_memory_hook_specs())
    if art.source == _COPILOT_FRESHNESS_END_WIRING_SENTINEL:
        return render_copilot_hooks(_copilot_freshness_end_specs())
    if art.source == _COPILOT_FRESHNESS_START_WIRING_SENTINEL:
        return render_copilot_hooks(_copilot_freshness_start_specs())
    if art.source == _COPILOT_VERSION_CHECK_END_WIRING_SENTINEL:
        return render_copilot_hooks(_copilot_version_check_end_specs())
    if art.source == _COPILOT_VERSION_CHECK_START_WIRING_SENTINEL:
        return render_copilot_hooks(_copilot_version_check_start_specs())
    assert art.source is not None
    return json.loads(read_asset_text(art.source))


def _apply_rag_settings(profile: RagHostProfile, art: Artifact) -> ArtifactOutcome:
    """`MERGE_DEDUP` (042, group C): additive merge of the PreToolUse hook entry into the wiring
    file (dedup by command → preserves the user's existing hooks). Copilot wiring is generated."""
    dest = profile.target_root / art.target_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    fragment = _rag_hook_fragment(art)
    outcome, detail = merge_settings(dest, fragment)
    return ArtifactOutcome(art.target_rel, outcome, detail)


def _server_entry_json(profile: RagHostProfile) -> str:
    """Compact JSON entry for the server for `claude mcp add-json` — same template as MCP_MERGE."""
    entry = json.loads(read_asset_text("rag/mcp.server.json.tmpl").format(corpus=profile.corpus))
    return json.dumps(entry, ensure_ascii=False)


def _apply_mcp_register(profile: RagHostProfile, runner: CommandRunner) -> ArtifactOutcome:
    """`REGISTER_CLI` (local scope): registers `sertor-rag` in the client, NO file in the repo.

    Idempotent: if the server is already registered (`claude mcp get`) → SKIPPED. Fail-fast
    (REQ-305): `claude` not found or `add-json` failed → `McpRegistrationError` with manual
    command; nothing is written in the root (the `.mcp.json` artifact is not in the plan in local
    scope).
    """
    entry_json = _server_entry_json(profile)
    manual = f"claude mcp add-json {_SERVER_NAME} '{entry_json}' --scope local"
    if not runner.is_available(_CLAUDE):
        raise McpRegistrationError(
            "`claude` is not available on the PATH: cannot register the server in local scope. "
            f"Install Claude Code or register manually: {manual}"
        )
    # idempotency: server already registered → skip (no second registration)
    if runner.run([_CLAUDE, "mcp", "get", _SERVER_NAME], cwd=profile.target_root).ok:
        log_event(logging.INFO, "mcp_register", server=_SERVER_NAME, scope="local",
                  outcome="skipped")
        return ArtifactOutcome(
            _MCP_REGISTER_LABEL, Outcome.SKIPPED, f"{_SERVER_NAME} already registered"
        )
    res = runner.run(
        [_CLAUDE, "mcp", "add-json", _SERVER_NAME, entry_json, "--scope", "local"],
        cwd=profile.target_root,
    )
    if not res.ok:
        raise McpRegistrationError(
            f"`claude mcp add-json` failed: {res.stderr.strip() or res.returncode}. "
            f"Manual command: {manual}"
        )
    log_event(logging.INFO, "mcp_register", server=_SERVER_NAME, scope="local", outcome="created")
    return ArtifactOutcome(_MCP_REGISTER_LABEL, Outcome.CREATED, f"{_SERVER_NAME} (scope local)")


def execute_rag_plan(
    plan: list[Artifact], profile: RagHostProfile, runner: CommandRunner,
    assistant: AssistantId = AssistantProfile.DEFAULT,
) -> InstallReport:
    """Executes the plan with fail-fast no-rollback via the kit's executor (capability=rag).

    The `assistant` is recorded in the report (informative, Principio IX); the apply handlers are
    assistant-agnostic (targets come from `art.target_rel`, resolved by the plan-builder).
    """

    apply = make_rag_apply(profile, runner, assistant)
    report = _kit_execute_plan(
        plan, apply, target=str(profile.target_root), capability="rag", assistant=assistant.value
    )
    # E10-FEAT-018: honest, non-fatal install-time notes (Principio XII). The pwsh guard surfaces
    # the non-Windows-without-`pwsh` gap for the deposited `.ps1` hooks; the Copilot note declares
    # the `memory-capture` adapter caveat. Both detect+report only — no wiring is rewritten (D-3).
    hook_surfaces = [a.target_rel for a in plan if a.target_rel.endswith(".ps1")]
    host_env.maybe_note_pwsh(report, hook_surfaces)
    if assistant is AssistantId.COPILOT_CLI:
        report.note(_COPILOT_MEMORY_NOTE)
    return report


# --- feature 048: lifecycle (upgrade/uninstall) -------------------------------------------------


def sertor_owned_paths(assistant: AssistantId = AssistantProfile.DEFAULT) -> SertorOwnedPaths:
    """Static Sertor-owned paths for the `rag` capability + assistant (D3, FR-017).

    Derived from the SAME constants/profile the plan-builder uses (no separate hard-coded values):
    the runtime tree `.sertor/` (type A, removed in block, FR-030), the standalone hook script
    (type B, per-assistant), and the shared edits (CLAUDE.md/copilot-instructions block,
    settings/hook wiring, `.gitignore`, MCP config entry). A coverage test asserts that the plan's
    `target_rel`s are a subset of these (the manifest replacement).
    """
    aprofile = AssistantProfile.for_assistant(assistant)
    is_copilot = assistant is AssistantId.COPILOT_CLI

    hook_target = _RAG_HOOK_TARGET_COPILOT if is_copilot else _RAG_HOOK_TARGET
    # Memory-capture hook (FEAT-009): standalone owned FILE, per-assistant. The SessionEnd wiring
    # lands in the SAME settings file as the rag-usage hook → already covered by the shared edit
    # below (no second shared_edit needed).
    memory_hook_target = _MEMORY_HOOK_TARGET_COPILOT if is_copilot else _MEMORY_HOOK_TARGET
    # RAG freshness hooks (E10-FEAT-011): SessionEnd script (both assistants) + SessionStart script
    # (Claude only — the Copilot SessionStart is a generated static prompt, no `.ps1`, W5). Owned
    # FILEs: removed on uninstall, updated on upgrade (FR-023). Their SessionEnd/SessionStart wiring
    # lands in the SAME settings file as the other hooks → covered by the shared edit below.
    freshness_hook_target = (
        _FRESHNESS_HOOK_TARGET_COPILOT if is_copilot else _FRESHNESS_HOOK_TARGET
    )
    settings_target = _COPILOT_HOOK_WIRING if is_copilot else _SETTINGS_TARGET
    instruction_target = aprofile.target_for(Surface.INSTRUCTION_BLOCK).target_rel
    mcp_target = aprofile.target_for(Surface.MCP_SERVER)
    mcp_root_key = mcp_target.root_key or "mcpServers"

    # Eval + usability skill folders (065, E12): each skill is a Sertor-owned dir (removed/upgraded
    # in block). The concierge agent (E12) is a single owned FILE in the shared `agents/` container
    # (sertor-flow lifecycle pattern: a per-file agent is owned_files, not owned_dir).
    skills_base = _COPILOT_SKILLS_BASE if is_copilot else _CLAUDE_SKILLS_BASE
    skill_dirs = tuple(
        f"{skills_base}/{name}" for name in (*_EVAL_SKILL_NAMES, *_USABILITY_SKILL_NAMES)
    )
    concierge_name = "agents/concierge.md" if not is_copilot else "concierge"
    concierge_target = aprofile.render_path(Surface.AGENT, concierge_name)

    # RAG freshness owned scripts: SessionEnd for both; SessionStart only for Claude (W5).
    freshness_files = (
        (freshness_hook_target,)
        if is_copilot
        else (freshness_hook_target, _FRESHNESS_START_TARGET)
    )
    # Version-update check owned scripts (E2-FEAT-013): SessionEnd for both; SessionStart only for
    # Claude (W5 — the Copilot SessionStart is a generated static prompt, no `.ps1`). The stamp
    # `.sertor/.sertor-version` is removed with `.sertor/` (owned_dir), so it needs no entry here.
    version_check_hook_target = (
        _VERSION_CHECK_HOOK_TARGET_COPILOT if is_copilot else _VERSION_CHECK_HOOK_TARGET
    )
    version_check_files = (
        (version_check_hook_target,)
        if is_copilot
        else (version_check_hook_target, _VERSION_CHECK_START_TARGET)
    )

    return SertorOwnedPaths(
        owned_dirs=(".sertor", *skill_dirs),
        owned_files=(
            hook_target, memory_hook_target, concierge_target,
            *freshness_files, *version_check_files,
            ".gitattributes",  # host-root LF policy (FEAT-010), CREATE_IF_ABSENT → owned FILE
        ),
        shared_edits=(
            SharedEdit(instruction_target, SharedEditKind.MARKER, "SERTOR:RAG-USAGE"),
            SharedEdit(settings_target, SharedEditKind.SETTINGS, _RAG_USAGE_SETTINGS),
            SharedEdit(".gitignore", SharedEditKind.GITIGNORE, "RUNTIME_IGNORES"),
            SharedEdit(mcp_target.target_rel, SharedEditKind.MCP_ENTRY, mcp_root_key),
        ),
    )


def _apply_rag_uninstall(
    profile: RagHostProfile, art: Artifact, runner: CommandRunner, is_copilot: bool,
    dry_run: bool = False,
) -> ArtifactOutcome:
    """Inverse dispatch for `op=UNINSTALL` (data-model §3). `dry_run` projects without mutating."""
    root = profile.target_root
    if art.kind is ArtifactKind.DEPENDENCIES:
        # `.sertor/` is removed in block as an owned_dir → here it is a no-op (skip).
        return ArtifactOutcome(".sertor", Outcome.SKIPPED, "removed as runtime block")
    if art.kind is ArtifactKind.ENV_MERGE:
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "removed with .sertor")
    if art.kind is ArtifactKind.GITIGNORE_APPEND:
        gi = root / ".gitignore"
        if dry_run:
            return ArtifactOutcome(".gitignore", project_removal(gi), "RUNTIME_IGNORES")
        outcome, detail = remove_gitignore_lines(gi, RUNTIME_IGNORES)
        return ArtifactOutcome(".gitignore", outcome, detail)
    if art.kind is ArtifactKind.MARKER_BLOCK:
        dest = root / art.target_rel
        if dry_run:
            return ArtifactOutcome(art.target_rel, project_removal(dest), "RAG-usage block")
        outcome = remove_marker_block(dest, MARKER_START_RAG, MARKER_END_RAG)
        return ArtifactOutcome(art.target_rel, outcome, "RAG-usage block stripped")
    if art.kind is ArtifactKind.FILE:
        dest = root / art.target_rel
        outcome = project_removal(dest) if dry_run else remove_path(dest)
        return ArtifactOutcome(art.target_rel, outcome, "standalone hook")
    if art.kind is ArtifactKind.SETTINGS_MERGE:
        dest = root / art.target_rel
        if dry_run:
            return ArtifactOutcome(art.target_rel, project_removal(dest), "hook entries")
        # Art-aware fragment (FEAT-009): same source dispatch as install → removes exactly the
        # entries this artifact added (rag-usage PreToolUse OR memory SessionEnd), not another's.
        fragment = _rag_hook_fragment(art)
        # Copilot dedicated hooks file (`sertor-hooks.json`): delete if left empty after removal;
        # the shared Claude `.claude/settings.json` is preserved (never delete-if-empty).
        outcome, detail = remove_settings_entries(
            dest, fragment, delete_if_empty=(dest.name == "sertor-hooks.json")
        )
        return ArtifactOutcome(art.target_rel, outcome, detail)
    if art.kind is ArtifactKind.MCP_MERGE:
        dest = root / art.target_rel
        if dry_run:
            return ArtifactOutcome(art.target_rel, project_removal(dest), f"server {_SERVER_NAME}")
        outcome, detail = remove_mcp_server(dest, _SERVER_NAME, "mcpServers")
        return ArtifactOutcome(art.target_rel, outcome, detail)
    if art.kind is ArtifactKind.MCP_REGISTER:
        if dry_run:
            return ArtifactOutcome(
                _MCP_REGISTER_LABEL, Outcome.REMOVED, f"{_SERVER_NAME} (scope local)"
            )
        outcome = deregister_mcp_client(runner, _SERVER_NAME)
        return ArtifactOutcome(_MCP_REGISTER_LABEL, outcome, f"{_SERVER_NAME} (scope local)")
    raise ConfigError(f"unhandled artifact kind: {art.kind}")  # pragma: no cover


def _apply_rag_upgrade(
    profile: RagHostProfile, art: Artifact, runner: CommandRunner, is_copilot: bool,
    dry_run: bool = False,
) -> ArtifactOutcome:
    """Inverse-aware dispatch for `op=UPGRADE` (data-model §3).

    FILE → `update_file_if_changed`; MARKER_BLOCK → `update_marker_block`; the additive merges
    (settings/gitignore/mcp/env) and DEPENDENCIES are idempotent (re-apply, never overwriting env
    values, NFR-05). `dry_run` projects the FILE/MARKER updates without mutating; the idempotent
    additive steps are projected as `SKIPPED` (a re-applied install adds nothing on aligned hosts).
    """
    root = profile.target_root
    if art.kind is ArtifactKind.FILE:
        # Render-aware (W7, E12): a Copilot concierge `.agent.md` is upgraded with the translated
        # frontmatter (not the raw Claude source); hooks/skills stay byte-copy (no `.agent.md`).
        content = _render_rag_file(art)
        dest = root / art.target_rel
        outcome = (
            project_update(dest, content) if dry_run
            else update_file_if_changed(dest, content)
        )
        return ArtifactOutcome(art.target_rel, outcome, "rag asset")
    if art.kind is ArtifactKind.MARKER_BLOCK:
        content = read_asset_text(_RAG_USAGE_BLOCK)
        dest = root / art.target_rel
        if dry_run:
            # project: present block that differs → UPDATED; equal/absent handled conservatively.
            return ArtifactOutcome(
                art.target_rel, _project_marker(dest, content), "RAG-usage block"
            )
        outcome = update_marker_block(dest, content, MARKER_START_RAG, MARKER_END_RAG)
        return ArtifactOutcome(art.target_rel, outcome, "RAG-usage block")
    if dry_run:
        # Idempotent additive steps: on an aligned host a re-apply changes nothing.
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "idempotent")
    # Everything else: re-run the additive install handler (idempotent).
    if art.kind is ArtifactKind.DEPENDENCIES:
        return _apply_deps(profile, runner)
    if art.kind is ArtifactKind.ENV_MERGE:
        return _apply_env(profile)
    if art.kind is ArtifactKind.MCP_MERGE:
        return _apply_mcp(profile, art)
    if art.kind is ArtifactKind.MCP_REGISTER:
        return _apply_mcp_register(profile, runner)
    if art.kind is ArtifactKind.GITIGNORE_APPEND:
        return _apply_gitignore(profile)
    if art.kind is ArtifactKind.SETTINGS_MERGE:
        return _apply_rag_settings(profile, art)
    raise ConfigError(f"unhandled artifact kind: {art.kind}")  # pragma: no cover


def _project_marker(dest, content: str) -> Outcome:
    """Read-only projection of `update_marker_block` for `--dry-run`."""
    if not dest.exists():
        return Outcome.BLOCK
    existing = dest.read_text(encoding="utf-8")
    if MARKER_START_RAG not in existing:
        return Outcome.BLOCK
    start = existing.find(MARKER_START_RAG)
    end = existing.find(MARKER_END_RAG, start)
    if end == -1:
        return Outcome.BLOCK
    end += len(MARKER_END_RAG)
    new_region = f"{MARKER_START_RAG}\n{content.rstrip()}\n{MARKER_END_RAG}"
    return Outcome.SKIPPED if existing[start:end] == new_region else Outcome.UPDATED


def make_rag_apply(
    profile: RagHostProfile, runner: CommandRunner, assistant: AssistantId,
    dry_run: bool = False,
):
    """Builds the verb-aware `apply(artifact, op)` for the `rag` capability (feature 048).

    INSTALL keeps the historical behaviour (non-regression, NFR-3); UNINSTALL/UPGRADE dispatch to
    the inverse/idempotent handlers above. `dry_run` makes the inverse handlers project (no write).
    The same callback drives all three verbs through the kit's `execute_plan`/`execute_lifecycle`.
    """
    is_copilot = assistant is AssistantId.COPILOT_CLI

    def apply(art: Artifact, op: LifecycleOp = LifecycleOp.INSTALL) -> ArtifactOutcome:
        if op is LifecycleOp.UNINSTALL:
            return _apply_rag_uninstall(profile, art, runner, is_copilot, dry_run)
        if op is LifecycleOp.UPGRADE:
            return _apply_rag_upgrade(profile, art, runner, is_copilot, dry_run)
        if art.kind is ArtifactKind.DEPENDENCIES:
            return _apply_deps(profile, runner)
        if art.kind is ArtifactKind.ENV_MERGE:
            return _apply_env(profile)
        if art.kind is ArtifactKind.MCP_MERGE:
            return _apply_mcp(profile, art)
        if art.kind is ArtifactKind.MCP_REGISTER:
            return _apply_mcp_register(profile, runner)
        if art.kind is ArtifactKind.GITIGNORE_APPEND:
            return _apply_gitignore(profile)
        if art.kind is ArtifactKind.MARKER_BLOCK:
            return _apply_rag_usage_block(profile, art)
        if art.kind is ArtifactKind.FILE:
            return _apply_rag_file(profile, art)
        if art.kind is ArtifactKind.SETTINGS_MERGE:
            return _apply_rag_settings(profile, art)
        raise ConfigError(f"unhandled artifact kind: {art.kind}")  # pragma: no cover

    return apply


def _union_owned(assistants: tuple[AssistantId, ...]) -> SertorOwnedPaths:
    """Union of the Sertor-owned paths of several assistants (cross-assistant obsoletes, FR-016)."""
    dirs: set[str] = set()
    files: set[str] = set()
    edits: list[SharedEdit] = []
    seen_edits: set[str] = set()
    for a in assistants:
        owned = sertor_owned_paths(a)
        dirs |= set(owned.owned_dirs)
        files |= set(owned.owned_files)
        for e in owned.shared_edits:
            if e.target_rel not in seen_edits:
                seen_edits.add(e.target_rel)
                edits.append(e)
    return SertorOwnedPaths(
        owned_dirs=tuple(sorted(dirs)),
        owned_files=tuple(sorted(files)),
        shared_edits=tuple(edits),
    )


def execute_rag_lifecycle(
    plan: list[Artifact],
    profile: RagHostProfile,
    runner: CommandRunner,
    op: LifecycleOp,
    assistant: AssistantId = AssistantProfile.DEFAULT,
    dry_run: bool = False,
    obsolete_assistants: tuple[AssistantId, ...] | None = None,
) -> InstallReport:
    """Executes the `rag` plan with the lifecycle verb `op` via the kit orchestrator (feature 048).

    For UPGRADE the obsolete phase scans the owned paths of `obsolete_assistants` (default: ALL
    assistants) and removes those absent from the current plan. The CLI narrows this scope to avoid
    the cross-assistant footgun (A-01): a *bare* `upgrade` passes only the NOT-installed assistants
    (cruft sweep, a coexisting install is preserved); an *explicit* `--assistant` switch passes
    `None` → all assistants (the deliberate, consented consolidation, FR-016). UNINSTALL applies the
    inverse of every plan artifact. `dry_run` projects without writing.
    """
    apply = make_rag_apply(profile, runner, assistant, dry_run=dry_run)
    owned = sertor_owned_paths(assistant)
    if op is LifecycleOp.UPGRADE:
        scope = obsolete_assistants if obsolete_assistants is not None else tuple(AssistantId)
        obsolete = _union_owned(scope)
    else:
        obsolete = None
    # `.sertor/` is removed in block on uninstall (FR-030), not per-sub-artifact.
    return _kit_execute_lifecycle(
        plan, owned, apply, op=op, target=str(profile.target_root),
        capability="rag", assistant=assistant.value, dry_run=dry_run,
        obsolete_owned=obsolete, uninstall_dirs_in_block=(".sertor",),
    )
