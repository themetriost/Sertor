"""`sertor-install-kit`: motore di installazione condiviso (stdlib-only, no `sertor-core`).

Espone il *meccanismo* di installazione non distruttivo riusato dai bundle (wiki/rag/governance):
tipi `Artifact`, errori di dominio, `InstallReport`, merge additivi, blocco a marker generalizzato,
esecutore di piano a callback, accesso alle risorse bundled, `CommandRunner`, `log_event`.
Contratto: `contracts/install-kit-api.md` (`install-kit/1`).
"""
from __future__ import annotations

from sertor_install_kit.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    Outcome,
    WriteStrategy,
)
from sertor_install_kit.assistant import (
    AssistantId,
    AssistantProfile,
    Surface,
    SurfaceTarget,
)
from sertor_install_kit.claude_md import write_marker_block
from sertor_install_kit.command_runner import CommandResult, CommandRunner, SubprocessRunner
from sertor_install_kit.env_merge import merge_env
from sertor_install_kit.errors import ConfigError, InstallerError
from sertor_install_kit.executor import execute_plan
from sertor_install_kit.gitignore_append import RUNTIME_IGNORES, append_gitignore
from sertor_install_kit.mcp_merge import merge_mcp
from sertor_install_kit.observability import log_event
from sertor_install_kit.report import InstallReport
from sertor_install_kit.resources import asset_path, iter_asset_dir, read_asset_text
from sertor_install_kit.settings_merge import merge_settings
from sertor_install_kit.surfaces import (
    render_custom_agent,
    render_prompt_file,
    split_frontmatter,
)
from sertor_install_kit.sync import sync_assets, sync_subtree

__all__ = [
    # artifacts
    "Artifact",
    "ArtifactKind",
    "ArtifactOutcome",
    "Outcome",
    "WriteStrategy",
    # assistant targeting (feature 044)
    "AssistantId",
    "AssistantProfile",
    "Surface",
    "SurfaceTarget",
    # errors
    "InstallerError",
    "ConfigError",
    # report
    "InstallReport",
    # marker block
    "write_marker_block",
    # merge primitives
    "merge_settings",
    "merge_env",
    "merge_mcp",
    "append_gitignore",
    "RUNTIME_IGNORES",
    # executor
    "execute_plan",
    # resources
    "asset_path",
    "read_asset_text",
    "iter_asset_dir",
    # command runner
    "CommandRunner",
    "CommandResult",
    "SubprocessRunner",
    # observability
    "log_event",
    # surfaces renderer (feature 045: shared sertor/sertor-flow)
    "render_prompt_file",
    "render_custom_agent",
    "split_frontmatter",
    # sync
    "sync_assets",
    "sync_subtree",
]
