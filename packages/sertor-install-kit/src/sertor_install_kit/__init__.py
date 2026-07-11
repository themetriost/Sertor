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
    LifecycleOp,
    Outcome,
    WriteStrategy,
)
from sertor_install_kit.assistant import (
    AssistantId,
    AssistantProfile,
    CommandVehicle,
    Surface,
    SurfaceTarget,
    select_for,
)
from sertor_install_kit.claude_md import (
    remove_marker_block,
    update_marker_block,
    write_marker_block,
)
from sertor_install_kit.command_runner import CommandResult, CommandRunner, SubprocessRunner
from sertor_install_kit.env_merge import merge_env
from sertor_install_kit.errors import ConfigError, InstallerError, ModelPolicyError
from sertor_install_kit.executor import execute_plan
from sertor_install_kit.gitignore_append import (
    RUNTIME_IGNORES,
    append_gitignore,
    remove_gitignore_lines,
)
from sertor_install_kit.lifecycle import (
    McpRegistrationError,
    SertorOwnedPaths,
    SharedEdit,
    SharedEditKind,
    deregister_mcp_client,
    execute_lifecycle,
    project_removal,
    project_update,
    prune_empty_dirs,
    remove_file_if_owned,
    remove_path,
    update_file_if_changed,
)
from sertor_install_kit.mcp_merge import merge_mcp, remove_mcp_server
from sertor_install_kit.model_policy import IN_SCOPE_AGENTS, MODEL_POLICY_VERSION, resolve_model
from sertor_install_kit.observability import log_event
from sertor_install_kit.report import InstallReport
from sertor_install_kit.resources import asset_path, iter_asset_dir, read_asset_text
from sertor_install_kit.settings_merge import merge_settings, remove_settings_entries
from sertor_install_kit.surfaces import (
    HookEntrySpec,
    render_copilot_hooks,
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
    "LifecycleOp",
    "Outcome",
    "WriteStrategy",
    # assistant targeting (feature 044; FEAT-011 CommandVehicle)
    "AssistantId",
    "AssistantProfile",
    "select_for",
    "CommandVehicle",
    "Surface",
    "SurfaceTarget",
    # errors
    "InstallerError",
    "ConfigError",
    "ModelPolicyError",
    "McpRegistrationError",
    # report
    "InstallReport",
    # marker block
    "write_marker_block",
    "remove_marker_block",
    "update_marker_block",
    # merge primitives
    "merge_settings",
    "remove_settings_entries",
    "merge_env",
    "merge_mcp",
    "remove_mcp_server",
    "append_gitignore",
    "remove_gitignore_lines",
    "RUNTIME_IGNORES",
    # lifecycle primitives (feature 048)
    "SertorOwnedPaths",
    "SharedEdit",
    "SharedEditKind",
    "update_file_if_changed",
    "prune_empty_dirs",
    "remove_file_if_owned",
    "remove_path",
    "deregister_mcp_client",
    "project_removal",
    "project_update",
    "execute_lifecycle",
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
    # surfaces renderer (feature 045: shared sertor/sertor-flow; FEAT-011 copilot hooks)
    "render_prompt_file",
    "render_custom_agent",
    "split_frontmatter",
    "HookEntrySpec",
    "render_copilot_hooks",
    # sync
    "sync_assets",
    "sync_subtree",
    # model policy (E2-FEAT-015)
    "resolve_model",
    "MODEL_POLICY_VERSION",
    "IN_SCOPE_AGENTS",
]
