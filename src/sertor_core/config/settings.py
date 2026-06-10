"""Configurazione centralizzata del nucleo (Principio VIII, REQ-030).

UNICA fonte di verità per le scelte operative: provider, backend, percorsi, parametri di
chunking, `k`, batch, esclusioni. I default vivono SOLO qui — i componenti non hardcodano nulla.
Caricata da variabili d'ambiente e da un file `.env` (non versionato). I segreti (chiavi API)
provengono solo da env/`.env` e non vengono mai scritti su path versionati (REQ-032).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Pattern di esclusione di default per l'ingestione (REQ-002): ambienti, artefatti, VCS, segreti.
# È un default sovrascrivibile via config, non una lista hardcoded nei componenti.
_DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".git", ".hg", ".svn",
    ".venv", "venv", "env", "node_modules", "__pycache__",
    ".pytest_cache", ".ruff_cache", ".mypy_cache",
    "dist", "build", "target", "bin", "obj", "out",
    ".index", "chroma", ".idea", ".vscode",
    "*.key", "*.pem", ".env",
)


def _split_env(name: str) -> list[str] | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


@dataclass(frozen=True)
class Settings:
    """Settaggi del nucleo. Istanziare via `Settings.load()` per leggere env/`.env`."""

    # backend & corpus
    backend: str = "local"                 # local | azure — provider di EMBEDDINGS
    store_backend: str = "local"           # local | azure — backend VECTOR STORE (disaccoppiato)
    corpus: str = "default"                # namespace logico della collezione
    extra_corpora: tuple[str, ...] = ()    # corpora aggiuntivi per la ricerca combinata (FR-007)

    # embeddings: locale (Ollama)
    ollama_host: str = "http://localhost:11434"
    ollama_embed_model: str = "nomic-embed-text"
    # embeddings: cloud (Azure OpenAI)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_embed_deployment: str = ""
    embed_batch_size: int = 64

    # vector store
    index_dir: Path = field(default_factory=lambda: Path(".index"))
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""

    # chunking
    chunk_size: int = 1600
    chunk_overlap: int = 200

    # retrieval
    default_k: int = 5

    # ingestione
    exclude_patterns: tuple[str, ...] = _DEFAULT_EXCLUDES

    @property
    def embed_provider(self) -> str:
        """Provider di embeddings coerente col backend: azure in cloud, ollama in locale."""
        return "azure" if self.backend == "azure" else "ollama"

    @classmethod
    def load(cls, env_file: str | os.PathLike[str] | None = ".env") -> Settings:
        """Costruisce i settaggi da variabili d'ambiente + file `.env` (se presente).

        Il file `.env` è autoritativo (override) per evitare che variabili di sistema
        spurie rompano la config; i valori assenti ricadono sui default di questa classe.
        """
        if env_file is not None and Path(env_file).exists():
            load_dotenv(env_file, override=True)

        excludes = _split_env("SERTOR_EXCLUDE_PATTERNS")
        extra_corpora = _split_env("SERTOR_EXTRA_CORPORA")
        index_dir = os.getenv("SERTOR_INDEX_DIR")
        backend = os.getenv("RAG_BACKEND", "local")
        return cls(
            backend=backend,
            # Lo store è disaccoppiato dal provider di embeddings: default = `RAG_BACKEND` (retro-
            # compatibile), si sovrascrive con `SERTOR_STORE_BACKEND` per combinare, es., embeddings
            # Azure con store Chroma locale.
            store_backend=os.getenv("SERTOR_STORE_BACKEND", backend),
            corpus=os.getenv("SERTOR_CORPUS", "default"),
            extra_corpora=tuple(extra_corpora) if extra_corpora is not None else (),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_openai_embed_deployment=os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", ""),
            embed_batch_size=int(os.getenv("EMBED_BATCH_SIZE", "64")),
            index_dir=Path(index_dir) if index_dir else Path(".index"),
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", ""),
            azure_search_api_key=os.getenv("AZURE_SEARCH_API_KEY", ""),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1600")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            default_k=int(os.getenv("DEFAULT_K", "5")),
            exclude_patterns=tuple(excludes) if excludes is not None else _DEFAULT_EXCLUDES,
        )
