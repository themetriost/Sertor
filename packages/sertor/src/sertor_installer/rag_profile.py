"""Opzioni e profilo dell'ospite per `install rag` (data-model §3).

`compose_extras` è la funzione pura backend→extra (DA-3); `RagHostProfile` raccoglie la specificità
dell'ospite (target, `.sertor/`, corpus, extra, url di distribuzione) per generare i template e la
spec di `uv add`. Nessun import di SDK (Principio I).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sertor_core.domain.errors import ConfigError

# URL di distribuzione del PRODOTTO Sertor (DA-4, interim git+url). NON è un'assunzione sull'ospite
# (Principio X): varia col progetto Sertor, non col repo target.
DIST_URL = "https://github.com/themetriost/Sertor.git"

_BACKENDS = ("azure", "local")


def sanitize_corpus(name: str) -> str:
    """Nome corpus sicuro da una cartella: minuscolo, non [a-z0-9._-] → '-'; fallback 'corpus'."""
    slug = re.sub(r"[^a-z0-9._-]+", "-", name.strip().lower()).strip("-._")
    return slug or "corpus"


def compose_extras(backend: str, include_graph: bool, include_rerank: bool) -> list[str]:
    """Extra per `uv add` (DA-3): `mcp` sempre; `azure` solo su azure; graph/rerank opt-out."""
    extras: list[str] = []
    if backend == "azure":
        extras.append("azure")
    extras.append("mcp")  # il caso d'uso primario è l'assistente via server MCP
    if include_graph:
        extras.append("graph")
    if include_rerank:
        extras.append("rerank")
    return extras


@dataclass(frozen=True)
class RagInstallOptions:
    """Input normalizzato del comando `install rag` (dopo il parsing argparse)."""

    target_root: Path
    backend: str = "azure"
    corpus: str | None = None
    include_graph: bool = True
    include_rerank: bool = True
    with_deps: bool = True
    json_report: bool = False

    def __post_init__(self) -> None:
        if self.backend not in _BACKENDS:
            raise ConfigError(f"backend non valido: {self.backend}", key="backend")

    def resolved_corpus(self) -> str:
        return self.corpus or sanitize_corpus(self.target_root.name)

    def extras(self) -> list[str]:
        return compose_extras(self.backend, self.include_graph, self.include_rerank)


@dataclass(frozen=True)
class RagHostProfile:
    """Specificità dell'ospite per il RAG, derivata dalle opzioni."""

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
        """Spec per `uv add`: `sertor-core[<extras>] @ git+<url>`."""
        return f"sertor-core[{','.join(self.extras)}] @ git+{self.dist_url}"
