"""Per-assistant targeting seam (feature 044, data-model §1/§2/§3).

The `AssistantProfile` is the ONLY place that knows the per-assistant conventions (Principio X:
the assistant is configured, not presumed in the body of the plan-builders). A `Surface` is the
logical category of a distributable artifact, independent of the assistant; the profile resolves,
for a given `AssistantId`, **where/how** each Surface materializes (container path + write
strategy + MCP root-key + per-file render path).

stdlib-only, frozen value objects (Principio I), coherent with `artifacts.py`. The kit owns this so
`sertor-flow`/FEAT-009 can reuse the same targeting.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sertor_install_kit.artifacts import WriteStrategy
from sertor_install_kit.errors import ConfigError


class AssistantId(Enum):
    """Target assistant of the installation (data-model §1)."""

    CLAUDE = "claude"
    COPILOT = "copilot"

    @classmethod
    def from_str(cls, value: str) -> AssistantId:
        """Parses an assistant id; unknown value → explicit `ConfigError` (Principio IV)."""
        try:
            return cls(value)
        except ValueError as exc:
            valid = ", ".join(a.value for a in cls)
            raise ConfigError(
                f"unknown assistant '{value}': valid values are {valid}", key="--assistant"
            ) from exc


class Surface(Enum):
    """Logical category of a distributable artifact, independent of the assistant (data-model §2).

    It is the parity pivot: every Surface has a rendering for each `AssistantId`.
    """

    INSTRUCTION_BLOCK = "instruction_block"  # marker-delimited ritual/usage text — wiki, rag
    MCP_SERVER = "mcp_server"                # `sertor-rag` server entry — rag
    COMMAND = "command"                      # command/skill body (`/wiki`, `wiki-author`) — wiki
    AGENT = "agent"                          # agent persona (`wiki-curator`) — wiki
    HOOK = "hook"                            # event→script wiring (script reused) — wiki, rag


@dataclass(frozen=True)
class SurfaceTarget:
    """Concrete container for a `Surface` on a given assistant (data-model §3).

    `target_rel` is the file the artifact writes to (validated relative, no `..`). `strategy` is the
    non-destructive write rule. `root_key` is meaningful only for `MCP_SERVER` (the JSON root that
    holds the servers map: `mcpServers` for Claude, `servers` for Copilot).
    """

    target_rel: str
    strategy: WriteStrategy
    root_key: str | None = None

    def __post_init__(self) -> None:
        rel = self.target_rel.replace("\\", "/")
        if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
            raise ConfigError("target_rel must be relative", key=self.target_rel)
        if ".." in rel.split("/"):
            raise ConfigError("target_rel must not ascend with '..'", key=self.target_rel)


@dataclass(frozen=True)
class AssistantProfile:
    """Resolves, for an `AssistantId`, the container of each `Surface` (data-model §3).

    Single-arity surfaces (`INSTRUCTION_BLOCK`/`MCP_SERVER`/`HOOK`) resolve to a fixed
    `SurfaceTarget` via `target_for`. Per-file surfaces (`COMMAND`/`AGENT`) map a logical name into
    the assistant-specific path via `render_path` (Claude keeps the `.claude/<rel>` layout;
    Copilot renders `.github/prompts/<name>.prompt.md` and `.github/agents/<name>.agent.md`).
    """

    assistant: AssistantId
    _targets: dict[Surface, SurfaceTarget]
    _command_dir: str
    _command_suffix: str
    _agent_dir: str
    _agent_suffix: str
    _file_prefix: str | None  # Claude: ".claude" (keep the historical layout); Copilot: None

    DEFAULT = AssistantId.CLAUDE  # documented default when `--assistant` is absent (FR-002)

    def target_for(self, surface: Surface) -> SurfaceTarget | None:
        """Fixed `SurfaceTarget` for a single-arity surface; `None` if not materialized (gap)."""
        return self._targets.get(surface)

    def render_path(self, surface: Surface, name: str) -> str:
        """Assistant-specific path for a per-file surface (`COMMAND`/`AGENT`).

        For Claude, `name` is the path relative to `.claude/` (e.g. `commands/wiki.md`) and is kept
        verbatim under the `.claude/` prefix (non-regression). For Copilot, `name` is the logical
        command/agent name and is rendered into the `.github/**` layout.
        """
        if surface is Surface.COMMAND:
            if self._file_prefix is not None:
                return f"{self._file_prefix}/{name}"
            return f"{self._command_dir}/{name}{self._command_suffix}"
        if surface is Surface.AGENT:
            if self._file_prefix is not None:
                return f"{self._file_prefix}/{name}"
            return f"{self._agent_dir}/{name}{self._agent_suffix}"
        raise ConfigError(f"render_path not defined for surface {surface}", key=surface.value)

    @classmethod
    def for_assistant(cls, assistant: AssistantId) -> AssistantProfile:
        """Builds the profile for an assistant (the per-assistant mapping of data-model §3)."""
        if assistant is AssistantId.CLAUDE:
            return cls(
                assistant=assistant,
                _targets={
                    Surface.INSTRUCTION_BLOCK: SurfaceTarget(
                        "CLAUDE.md", WriteStrategy.APPEND_BLOCK
                    ),
                    Surface.MCP_SERVER: SurfaceTarget(
                        ".mcp.json", WriteStrategy.MERGE_JSON, root_key="mcpServers"
                    ),
                    Surface.HOOK: SurfaceTarget(
                        ".claude/settings.json", WriteStrategy.MERGE_DEDUP
                    ),
                },
                _command_dir=".claude/commands",
                _command_suffix=".md",
                _agent_dir=".claude/agents",
                _agent_suffix=".md",
                _file_prefix=".claude",
            )
        if assistant is AssistantId.COPILOT:
            return cls(
                assistant=assistant,
                _targets={
                    Surface.INSTRUCTION_BLOCK: SurfaceTarget(
                        ".github/copilot-instructions.md", WriteStrategy.APPEND_BLOCK
                    ),
                    Surface.MCP_SERVER: SurfaceTarget(
                        ".vscode/mcp.json", WriteStrategy.MERGE_JSON, root_key="servers"
                    ),
                    Surface.HOOK: SurfaceTarget(
                        ".github/hooks/sertor-hooks.json", WriteStrategy.MERGE_DEDUP
                    ),
                },
                _command_dir=".github/prompts",
                _command_suffix=".prompt.md",
                _agent_dir=".github/agents",
                _agent_suffix=".agent.md",
                _file_prefix=None,
            )
        raise ConfigError(f"unsupported assistant: {assistant}")  # pragma: no cover
