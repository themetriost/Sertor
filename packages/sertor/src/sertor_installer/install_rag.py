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

from sertor_install_kit.assistant import AssistantId, AssistantProfile, Surface
from sertor_install_kit.claude_md import write_marker_block
from sertor_install_kit.command_runner import CommandRunner
from sertor_install_kit.env_merge import merge_env
from sertor_install_kit.errors import ConfigError, InstallerError
from sertor_install_kit.executor import execute_plan as _kit_execute_plan
from sertor_install_kit.gitignore_append import append_gitignore
from sertor_install_kit.mcp_merge import merge_mcp
from sertor_install_kit.observability import log_event
from sertor_install_kit.settings_merge import merge_settings
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

# Group C (Principio XI, feature 042): host-specific PreToolUse hook (adapter of the trigger).
# Its absence MUST NOT break the RAG capability (Principio X).
_RAG_HOOK_ASSET = "rag/hooks/sertor-rag-usage-check.ps1"
_RAG_HOOK_TARGET = ".claude/hooks/sertor-rag-usage-check.ps1"
_RAG_USAGE_SETTINGS = "rag/settings.rag-usage.json"
_SETTINGS_TARGET = ".claude/settings.json"


class DependencyError(InstallerError):
    """Dependency bootstrap failed: `uv` not found or `uv init`/`uv add` did not succeed."""


class McpRegistrationError(InstallerError):
    """MCP registration in `local` scope failed: `claude` not found or command failed."""


# Copilot rag surfaces (feature 044): host-facing artifacts under `.github/**` (script reused).
_RAG_HOOK_TARGET_COPILOT = ".github/hooks/sertor-rag-usage-check.ps1"
_RAG_USAGE_SETTINGS_COPILOT = "copilot/hooks/rag-usage.hooks.json"
_COPILOT_HOOK_WIRING = ".github/hooks/sertor-hooks.json"


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
    (Principio X): `claude` reproduces the historical plan (non-regression); `copilot` targets
    `.vscode/mcp.json`/`.github/**`.
    """
    aprofile = AssistantProfile.for_assistant(assistant)
    is_copilot = assistant is AssistantId.COPILOT

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
    # assistant's MCP config (`.mcp.json` / `.vscode/mcp.json`).
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
    hook_target = _RAG_HOOK_TARGET_COPILOT if is_copilot else _RAG_HOOK_TARGET
    settings_source = _RAG_USAGE_SETTINGS_COPILOT if is_copilot else _RAG_USAGE_SETTINGS
    settings_target = _COPILOT_HOOK_WIRING if is_copilot else _SETTINGS_TARGET
    plan.append(
        Artifact(
            ArtifactKind.FILE,
            _RAG_HOOK_ASSET,
            hook_target,
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
    """`MERGE_ENV`: `.sertor/.env` from the backend template (empty secrets), additive merge."""
    rendered = read_asset_text(f"rag/env.{profile.backend}.tmpl").format(corpus=profile.corpus)
    outcome, detail = merge_env(profile.sertor_dir / ".env", rendered)
    return ArtifactOutcome(".sertor/.env", outcome, detail)


def _apply_mcp(profile: RagHostProfile, art: Artifact) -> ArtifactOutcome:
    """`MERGE_JSON`: `sertor-rag` server in the MCP config, additive merge.

    Target + root-key come from the artifact/assistant profile: Claude → `.mcp.json` (`mcpServers`);
    Copilot → `.vscode/mcp.json` (`servers`).
    """
    entry = json.loads(read_asset_text("rag/mcp.server.json.tmpl").format(corpus=profile.corpus))
    is_vscode = art.target_rel.replace("\\", "/") == ".vscode/mcp.json"
    root_key = "servers" if is_vscode else "mcpServers"
    outcome, detail = merge_mcp(profile.target_root / art.target_rel, entry, root_key=root_key)
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


def _apply_rag_hook_file(profile: RagHostProfile, art: Artifact) -> ArtifactOutcome:
    """`CREATE_IF_ABSENT` (042, group C): byte-for-byte copy of the hook script; exists → skip."""
    dest = profile.target_root / art.target_rel
    if dest.exists():
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED, "already present")
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert art.source is not None
    dest.write_text(read_asset_text(art.source), encoding="utf-8")
    return ArtifactOutcome(art.target_rel, Outcome.CREATED)


def _apply_rag_settings(profile: RagHostProfile, art: Artifact) -> ArtifactOutcome:
    """`MERGE_DEDUP` (042, group C): additive merge of the PreToolUse hook entry into
    `.claude/settings.json` (dedup by command → preserves the user's existing hooks)."""
    dest = profile.target_root / art.target_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert art.source is not None
    fragment = json.loads(read_asset_text(art.source))
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

    def apply(art: Artifact) -> ArtifactOutcome:
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
            return _apply_rag_hook_file(profile, art)
        if art.kind is ArtifactKind.SETTINGS_MERGE:
            return _apply_rag_settings(profile, art)
        raise ConfigError(f"unhandled artifact kind: {art.kind}")  # pragma: no cover

    return _kit_execute_plan(
        plan, apply, target=str(profile.target_root), capability="rag", assistant=assistant.value
    )
