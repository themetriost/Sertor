"""Options and host profile for `install rag` (data-model §3).

`compose_extras` is the pure backend→extras function (DA-3); `RagHostProfile` collects the host
specifics (target, `.sertor/`, corpus, extras, distribution url) to generate templates and the
`uv add` spec. No SDK imports (Principio I).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sertor_core.domain.errors import ConfigError

# Distribution URL of the Sertor PRODUCT (DA-4, interim git+url). NOT an assumption about the host
# (Principio X): varies with the Sertor project, not with the target repo.
DIST_URL = "https://github.com/themetriost/Sertor.git"

_BACKENDS = ("azure", "local")
_MCP_SCOPES = ("project", "local")  # project = .mcp.json in root · local = client ~/.claude.json


def sanitize_corpus(name: str) -> str:
    """Safe corpus name derived from a folder: lowercase, non-[a-z0-9._-] → '-'; fallback
    'corpus'."""
    slug = re.sub(r"[^a-z0-9._-]+", "-", name.strip().lower()).strip("-._")
    return slug or "corpus"


def compose_extras(backend: str, include_graph: bool, include_rerank: bool) -> list[str]:
    """Extras for `uv add` (DA-3): `mcp` always; `azure` only on azure; graph/rerank opt-out."""
    extras: list[str] = []
    if backend == "azure":
        extras.append("azure")
    extras.append("mcp")  # the primary use case is the assistant via the MCP server
    if include_graph:
        extras.append("graph")
    if include_rerank:
        extras.append("rerank")
    return extras


@dataclass(frozen=True)
class RagInstallOptions:
    """Normalized input for the `install rag` command (after argparse parsing)."""

    target_root: Path
    backend: str = "azure"
    corpus: str | None = None
    include_graph: bool = True
    include_rerank: bool = True
    with_deps: bool = True
    json_report: bool = False
    mcp_scope: str = "project"  # feature 016: project (.mcp.json root) | local (client, no file)

    def __post_init__(self) -> None:
        if self.backend not in _BACKENDS:
            raise ConfigError(f"invalid backend: {self.backend}", key="backend")
        if self.mcp_scope not in _MCP_SCOPES:
            raise ConfigError(f"invalid mcp-scope: {self.mcp_scope}", key="mcp_scope")

    def resolved_corpus(self) -> str:
        # Sanitize BOTH the explicit `--corpus` and the folder-name default (A-08 security review):
        # the corpus flows verbatim into `.sertor/.env` (`SERTOR_CORPUS=`) and the `.mcp.json`
        # template via `.format()`; an unsanitized newline/quote could inject extra env lines
        # (clobbering a secret) or break the MCP JSON. A corpus is a slug → normalising is safe.
        return sanitize_corpus(self.corpus or self.target_root.name)

    def extras(self) -> list[str]:
        return compose_extras(self.backend, self.include_graph, self.include_rerank)


@dataclass(frozen=True)
class RagHostProfile:
    """Host specifics for RAG, derived from the options."""

    target_root: Path
    backend: str
    corpus: str
    extras: list[str]
    dist_url: str = DIST_URL

    @property
    def sertor_dir(self) -> Path:
        return self.target_root / ".sertor"

    @classmethod
    def from_options(cls, opts: RagInstallOptions) -> RagHostProfile:
        return cls(
            target_root=opts.target_root,
            backend=opts.backend,
            corpus=opts.resolved_corpus(),
            extras=opts.extras(),
        )

    def dep_spec(self) -> str:
        """Spec for `uv add`: `sertor-core[<extras>] @ git+<url>`."""
        return f"sertor-core[{','.join(self.extras)}] @ git+{self.dist_url}"
