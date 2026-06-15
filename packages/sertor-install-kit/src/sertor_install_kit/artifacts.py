"""Installer domain entities: `Artifact` and `ArtifactOutcome` (data-model §1, §4).

Pure value objects, with no external SDK imports (Principio I). Each `Artifact` knows its own
**non-destructive rule** (the `WriteStrategy`); plan execution produces an `ArtifactOutcome` for
each artifact (more than one for `INIT_STRUCTURE`, aggregated).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sertor_install_kit.errors import ConfigError


class ArtifactKind(Enum):
    """Nature of the installable artifact (data-model §1)."""

    FILE = "file"
    SETTINGS_MERGE = "settings_merge"
    MARKER_BLOCK = "marker_block"
    STRUCTURE = "structure"
    CONFIG = "config"
    # `install rag` (feature 015): RAG runtime isolated in `.sertor/` + config scaffold in root.
    DEPENDENCIES = "dependencies"        # Python bootstrap in `.sertor/` (uv init + uv add)
    ENV_MERGE = "env_merge"              # `.sertor/.env` from template, additive per-key merge
    MCP_MERGE = "mcp_merge"             # `.mcp.json` in host root, additive server merge
    GITIGNORE_APPEND = "gitignore_append"  # `.gitignore` in root, dedup-append of lines
    # `install rag --mcp-scope local` (feature 016): register server in the client, no repo file.
    MCP_REGISTER = "mcp_register"        # `claude mcp add-json … --scope local` (outside the repo)


class WriteStrategy(Enum):
    """Non-destructive write rule associated with the `kind` (data-model §1)."""

    CREATE_IF_ABSENT = "create_if_absent"
    MERGE_DEDUP = "merge_dedup"
    APPEND_BLOCK = "append_block"
    INIT_STRUCTURE = "init_structure"
    GENERATE_CONFIG = "generate_config"
    # `install rag` (feature 015)
    BOOTSTRAP_DEPS = "bootstrap_deps"    # runs uv init/uv add (idempotent) via CommandRunner
    MERGE_ENV = "merge_env"              # additive merge of `.env` keys (never overwrites values)
    MERGE_JSON = "merge_json"            # additive merge of servers in `.mcp.json`
    APPEND_LINES = "append_lines"        # dedup-append of lines (`.gitignore`)
    REGISTER_CLI = "register_cli"        # register via the client CLI (idempotent, fail-fast)


class Outcome(Enum):
    """Outcome of a single artifact (data-model §4)."""

    CREATED = "created"
    SKIPPED = "skipped"
    MERGED = "merged"
    BLOCK = "block"
    ERROR = "error"


@dataclass(frozen=True)
class Artifact:
    """Unit that the installer deploys to the host.

    `target_rel` is ALWAYS relative to `--target` (never absolute, never ascending with `..`):
    validation in `__post_init__` prevents path-traversal (data-model §1, validity rules).
    """

    kind: ArtifactKind
    source: str | None
    target_rel: str
    strategy: WriteStrategy

    def __post_init__(self) -> None:
        rel = self.target_rel.replace("\\", "/")
        if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
            raise ConfigError("target_rel must be relative", key=self.target_rel)
        if ".." in rel.split("/"):
            raise ConfigError("target_rel must not ascend with '..'", key=self.target_rel)


@dataclass(frozen=True)
class ArtifactOutcome:
    """Per-artifact outcome: what happened to `target_rel` (data-model §4)."""

    target_rel: str
    outcome: Outcome
    detail: str | None = None
