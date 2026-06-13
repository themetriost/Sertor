"""Orchestration of `sertor install rag` (data-model §4, plan 015).

`build_rag_plan` enumerates artifacts in canonical order (DEPENDENCIES → ENV_MERGE → MCP_MERGE →
GITIGNORE_APPEND); `execute_rag_plan` executes sequentially with **fail-fast no-rollback** (same as
`install_wiki.execute_plan`): on the first domain error it records the error outcome, sets
`failed_step`, and stops; already-written artifacts remain (a re-run will find them →
skipped/merged).

**install ≠ run**: the DEPENDENCIES step only runs `uv init`/`uv add` (never indexing). The runtime
lives isolated in `<target>/.sertor/`; `.mcp.json` and `.gitignore` live in the host root. Thin
layer (Principio I): `uv` is behind the injectable `CommandRunner`.
"""
from __future__ import annotations

import json
import logging

from sertor_core.domain.errors import ConfigError, SertorError
from sertor_core.observability.logging import log_event
from sertor_installer.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    Outcome,
    WriteStrategy,
)
from sertor_installer.command_runner import CommandRunner
from sertor_installer.env_merge import merge_env
from sertor_installer.gitignore_append import append_gitignore
from sertor_installer.mcp_merge import merge_mcp
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


class DependencyError(SertorError):
    """Dependency bootstrap failed: `uv` not found or `uv init`/`uv add` did not succeed."""


class McpRegistrationError(SertorError):
    """MCP registration in `local` scope failed: `claude` not found or command failed."""


def build_rag_plan(
    profile: RagHostProfile, with_deps: bool = True, mcp_scope: str = "project"
) -> list[Artifact]:
    """Ordered list of `Artifact`.

    `with_deps=False` skips DEPENDENCIES. `mcp_scope` (feature 016) selects how the MCP server is
    registered: `project` → merge into `.mcp.json` in the root; `local` → register in the client
    via the `claude` CLI (NO file in the repo, `MCP_REGISTER` instead of `MCP_MERGE`).
    """
    plan: list[Artifact] = []
    if with_deps:
        plan.append(
            Artifact(ArtifactKind.DEPENDENCIES, None, ".sertor", WriteStrategy.BOOTSTRAP_DEPS)
        )
    plan.append(
        Artifact(
            ArtifactKind.ENV_MERGE,
            f"rag/env.{profile.backend}.tmpl",
            ".sertor/.env",
            WriteStrategy.MERGE_ENV,
        )
    )
    if mcp_scope == "local":
        plan.append(
            Artifact(
                ArtifactKind.MCP_REGISTER,
                "rag/mcp.server.json.tmpl",
                _MCP_REGISTER_LABEL,
                WriteStrategy.REGISTER_CLI,
            )
        )
    else:
        plan.append(
            Artifact(
                ArtifactKind.MCP_MERGE,
                "rag/mcp.server.json.tmpl",
                ".mcp.json",
                WriteStrategy.MERGE_JSON,
            )
        )
    plan.append(
        Artifact(ArtifactKind.GITIGNORE_APPEND, None, ".gitignore", WriteStrategy.APPEND_LINES)
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


def _apply_mcp(profile: RagHostProfile) -> ArtifactOutcome:
    """`MERGE_JSON`: `sertor-rag` server in `.mcp.json` (host root), additive merge."""
    entry = json.loads(read_asset_text("rag/mcp.server.json.tmpl").format(corpus=profile.corpus))
    outcome, detail = merge_mcp(profile.target_root / ".mcp.json", entry)
    return ArtifactOutcome(".mcp.json", outcome, detail)


def _apply_gitignore(profile: RagHostProfile) -> ArtifactOutcome:
    """`APPEND_LINES`: runtime entries in `.gitignore` (host root), dedup."""
    outcome, detail = append_gitignore(profile.target_root / ".gitignore")
    return ArtifactOutcome(".gitignore", outcome, detail)


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
    plan: list[Artifact], profile: RagHostProfile, runner: CommandRunner
) -> InstallReport:
    """Executes the plan with fail-fast no-rollback. Returns the `InstallReport`
    (capability=rag)."""
    report = InstallReport(target=str(profile.target_root), capability="rag")
    for art in plan:
        try:
            if art.kind is ArtifactKind.DEPENDENCIES:
                outcome = _apply_deps(profile, runner)
            elif art.kind is ArtifactKind.ENV_MERGE:
                outcome = _apply_env(profile)
            elif art.kind is ArtifactKind.MCP_MERGE:
                outcome = _apply_mcp(profile)
            elif art.kind is ArtifactKind.MCP_REGISTER:
                outcome = _apply_mcp_register(profile, runner)
            elif art.kind is ArtifactKind.GITIGNORE_APPEND:
                outcome = _apply_gitignore(profile)
            else:  # pragma: no cover — unknown kind is a bug, not user input
                raise ConfigError(f"unhandled artifact kind: {art.kind}")
        except SertorError as exc:
            report.add(ArtifactOutcome(art.target_rel, Outcome.ERROR, str(exc)))
            break  # fail-fast: stop on the first domain error (no rollback)
        report.add(outcome)
    return report
