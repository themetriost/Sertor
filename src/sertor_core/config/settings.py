"""Centralised configuration for the core (Principio VIII, REQ-030).

Single source of truth for operational choices: provider, backend, paths, chunking parameters,
`k`, batch size, exclusions. Defaults live ONLY here — components hardcode nothing.
Loaded from environment variables and a `.env` file (not versioned). Secrets (API keys)
come only from env/`.env` and are never written to versioned paths (REQ-032).
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Default exclusion patterns for ingestion (REQ-002): environments, artifacts, VCS, secrets.
# This is an overridable default via config, not a hardcoded list in components.
_DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".git", ".hg", ".svn",
    ".venv", "venv", "env", "node_modules", "__pycache__",
    ".pytest_cache", ".ruff_cache", ".mypy_cache",
    "dist", "build", "target", "bin", "obj", "out",
    ".index", "chroma", ".idea", ".vscode",
    "*.key", "*.pem", ".env",
)


def _resolve_env_path(env_file: str | os.PathLike[str] | None) -> Path | None:
    """Which `.env` to load — self-locating runtime (host-agnostic).

    `None` → no loading (test isolation). Otherwise, in order: the given file if it exists
    (default `./.env`, relative to cwd); then `.env` in the folder of the **project that owns
    the current venv** (`Path(sys.prefix).parent`) — for an installed runtime this is `.sertor/`,
    in development it is the repo root. This way the CLI loads `.sertor/.env` (and anchors the
    index there) from **any** cwd, not only when launched from inside `.sertor/`.
    """
    if env_file is None:
        return None
    explicit = Path(env_file)
    if explicit.exists():
        return explicit
    runtime_env = Path(sys.prefix).parent / ".env"
    if runtime_env.exists():
        return runtime_env
    return None


def _split_env(name: str) -> list[str] | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


def _bool_env(name: str, default: bool) -> bool:
    """Tolerant boolean parsing: true/1/yes/on (case-insensitive) → True."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("true", "1", "yes", "on")


def _float_or_none_env(name: str) -> float | None:
    """Float from env, or `None` when the variable is absent/blank (018, REQ-H1/H13).

    Distinguishes "unset" (feature disabled, today's behaviour) from an explicit `0.0`.
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return float(raw)


def _int_or_none_env(name: str) -> int | None:
    """Int from env, or `None` when the variable is absent/blank (031, FR-021).

    Twin of `_float_or_none_env`: distinguishes "unset" (no retention hint, default) from an
    explicit integer. Used by `memory_retention_days` (a hook recorded but never enforced here).
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return int(raw)


@dataclass(frozen=True)
class Settings:
    """Core settings. Instantiate via `Settings.load()` to read env/`.env`."""

    # backend & corpus
    backend: str = "local"                 # local | azure — EMBEDDINGS provider
    store_backend: str = "local"           # local | azure — VECTOR STORE backend (decoupled)
    corpus: str = "default"                # logical namespace for the collection
    extra_corpora: tuple[str, ...] = ()    # additional corpora for combined search (FR-007)

    # embeddings: locale (Ollama)
    ollama_host: str = "http://localhost:11434"
    ollama_embed_model: str = "nomic-embed-text"
    # embeddings: cloud (Azure OpenAI)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_embed_deployment: str = ""
    embed_batch_size: int = 64
    # embedding resilience (018, REQ-H3): retry transient provider failures (429/5xx/network).
    embed_retry_attempts: int = 3          # total attempts per batch; 1 = no retry
    embed_retry_base_s: float = 0.5        # base of the exponential backoff (seconds)
    # embedding cache (019, REQ-H4): content-hash cache so re-indexing an unchanged corpus does
    # not re-embed identical chunks. Default off = today's behaviour (full re-embed on rebuild).
    embed_cache_enabled: bool = False
    # observability persistence (020): keep the structured events that the core already emits in a
    # local queryable store (enables historical reports). Default off = today's behaviour (ephemeral
    # stderr logging only). The store lives at `<index_dir>/observability.sqlite` (git-ignored).
    observability_enabled: bool = False
    # observability reports (021): default time-bucket granularity for the aggregation reports.
    observability_bucket: str = "day"     # day | hour
    # observability live panel (022): refresh interval of the TUI panel, in seconds.
    observability_refresh_s: float = 2.0

    # conversation memory — capture & archive (031, FEAT-001). Privacy-by-default: OFF unless the
    # host opts in. With it off no adapter/store is built and no file is opened (SC-003).
    memory_enabled: bool = False                       # SERTOR_MEMORY — opt-in (default: off)
    memory_adapter: str = "claude-code"                # SERTOR_MEMORY_ADAPTER — capture source
    memory_retention_days: int | None = None           # SERTOR_MEMORY_RETENTION_DAYS — hook only
    memory_scrub_patterns: tuple[str, ...] = ()        # SERTOR_MEMORY_SCRUB_PATTERNS — extra regex
    # episodic full-text search over the memory archive (033, FEAT-002). Defaults only here
    # (Principio VIII); components hardcode nothing. Gated by `memory_enabled` (same opt-in).
    episodic_limit: int = 20                  # SERTOR_EPISODIC_LIMIT — max results (FR-010)
    episodic_snippet_tokens: int = 12         # SERTOR_EPISODIC_SNIPPET_TOKENS — snippet length
    # session listing for distillation (036, FEAT-003). Max sessions returned by `memory list`,
    # overridable per-invocation by `-k/--limit`. Default only here (Principio VIII).
    memory_list_limit: int = 20               # SERTOR_MEMORY_LIST_LIMIT — max sessions (FR-002)
    # Source directory of the Claude Code projects (host-agnostic, testable): default
    # `~/.claude/projects`. The adapter resolves the per-project encoded subfolder from here.
    claude_projects_dir: Path = field(
        default_factory=lambda: Path.home() / ".claude" / "projects"
    )

    # vector store
    index_dir: Path = field(default_factory=lambda: Path(".index"))
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""

    # chunking
    chunk_size: int = 1600
    chunk_overlap: int = 200
    # Hard cap on a single chunk's size (chars). Structural chunkers (markdown by heading, code by
    # symbol) can emit a unit far larger than `chunk_size`; embedding providers reject inputs over a
    # token budget (e.g. text-embedding-3-large: 8192 tokens → http 400). A chunk above this cap is
    # sub-split on line boundaries. Default 8000 chars stays under 8192 tokens even at ~1 char/token
    # (worst case), while only triggering for genuinely oversized sections (5× `chunk_size`).
    max_chunk_chars: int = 8000

    # retrieval
    default_k: int = 5
    preview_chars: int = 240               # preview length in CLI results (FEAT-011, D5)
    # confidence signal (018, REQ-H1/H2): cosine-similarity threshold; None = disabled (today's
    # behaviour). Below-threshold results are excluded so the consumer can abstain (grounding).
    retrieval_min_score: float | None = None

    # RAG engine (FEAT-004): selection + parameters for hybrid fusion and reranking
    engine: str = "hybrid"                 # baseline | hybrid — best is the default (D1)
    rrf_c: int = 60                        # RRF constant (Cormack et al., REQ-011)
    rrf_pool: int = 30                     # candidates per source before fusion (REQ-011)
    rerank_enabled: bool = False           # second cross-encoder stage (default off, R-3)
    rerank_pool: int = 15                  # fused pool passed to the reranker (~3×k, REQ-024)

    # structural code graph (FEAT-005): build integrated in index() + navigation
    graph_enabled: bool = True             # build graph inside index() (DA-2)
    # names more ambiguous than this → no calls edges (FR-004)
    graph_ambiguity_threshold: int = 2
    graph_limit_definitions: int = 10      # per-section limits for get_context (FR-016)
    graph_limit_relations: int = 8
    graph_limit_docs: int = 8

    # incremental indexing (046, FEAT-009): refresh only the changed files instead of rebuilding
    # from scratch. Default ON — when a valid manifest exists `index()` runs incrementally; `--full`
    # (rebuild=True) or `index_incremental=False` forces the full path; a missing/incompatible
    # manifest falls back to full automatically (FR-011). Reconciliation full is OFF by default.
    index_incremental: bool = True     # SERTOR_INDEX_INCREMENTAL — incremental default (FR-002)
    index_reconcile_every: int = 0     # SERTOR_INDEX_RECONCILE_EVERY — full every N runs (FR-019)

    # ingestione
    exclude_patterns: tuple[str, ...] = _DEFAULT_EXCLUDES

    @property
    def embed_provider(self) -> str:
        """Embedding provider consistent with the backend: azure in cloud, ollama locally."""
        return "azure" if self.backend == "azure" else "ollama"

    def validate_backend(self) -> list[str]:
        """Names of required but missing environment variables for the selected backend (D3).

        **Static** validation (FR-015): does not contact services; returns only the list of
        empty configuration fields required by the chosen backend/store. This is the ONLY source
        of the "which fields are needed for azure" map (Principio VIII): the CLI knows only the
        outcome. `local` (Ollama/Chroma, valid defaults) is never blocked → empty list.
        """
        missing: list[str] = []
        if self.backend == "azure":
            if not self.azure_openai_endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not self.azure_openai_api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            if not self.azure_openai_embed_deployment:
                missing.append("AZURE_OPENAI_EMBED_DEPLOYMENT")
        if self.store_backend == "azure":
            if not self.azure_search_endpoint:
                missing.append("AZURE_SEARCH_ENDPOINT")
            if not self.azure_search_api_key:
                missing.append("AZURE_SEARCH_API_KEY")
        return missing

    @classmethod
    def load(cls, env_file: str | os.PathLike[str] | None = ".env") -> Settings:
        """Build settings from environment variables + `.env` file (if present).

        The `.env` file is authoritative (override) to prevent spurious system variables from
        breaking the configuration; missing values fall back to this class's defaults.
        `.env` resolution is **self-locating** (`_resolve_env_path`): if not found in cwd,
        uses the one next to the runtime venv (`.sertor/.env`), and the index is anchored there.
        """
        env_path = _resolve_env_path(env_file)
        if env_path is not None:
            load_dotenv(env_path, override=True)

        excludes = _split_env("SERTOR_EXCLUDE_PATTERNS")
        extra_corpora = _split_env("SERTOR_EXTRA_CORPORA")
        index_dir = os.getenv("SERTOR_INDEX_DIR")
        backend = os.getenv("RAG_BACKEND", "local")
        if env_path is None and env_file is not None and os.getenv("RAG_BACKEND") is None:
            # No configuration source (neither `.env` in cwd/next to the runtime, nor
            # `RAG_BACKEND` in the environment): falling back to defaults (backend `local`/Ollama).
            # Signalled to avoid the silent fallback that causes confusion (e.g. "ollama
            # unreachable" when Azure was intended but `.sertor/.env` was not loaded).
            from sertor_core.observability.logging import log_event
            log_event(
                logging.WARNING, "config_no_env_found",
                note="no .env found and RAG_BACKEND not set; using defaults (local)",
            )
        # Index anchor: explicit > runtime home (folder of resolved `.env`) > cwd.
        if index_dir:
            resolved_index_dir = Path(index_dir)
        elif env_path is not None:
            resolved_index_dir = env_path.parent / ".index"
        else:
            resolved_index_dir = Path(".index")
        return cls(
            backend=backend,
            # The store is decoupled from the embedding provider: default = `RAG_BACKEND`
            # (backward-compatible), overridable with `SERTOR_STORE_BACKEND` to combine, e.g.,
            # Azure embeddings with a local Chroma store.
            store_backend=os.getenv("SERTOR_STORE_BACKEND", backend),
            corpus=os.getenv("SERTOR_CORPUS", "default"),
            extra_corpora=tuple(extra_corpora) if extra_corpora is not None else (),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_openai_embed_deployment=os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", ""),
            embed_batch_size=int(os.getenv("EMBED_BATCH_SIZE", "64")),
            embed_retry_attempts=int(os.getenv("SERTOR_EMBED_RETRY_ATTEMPTS", "3")),
            embed_retry_base_s=float(os.getenv("SERTOR_EMBED_RETRY_BASE", "0.5")),
            embed_cache_enabled=_bool_env("SERTOR_EMBED_CACHE", False),
            observability_enabled=_bool_env("SERTOR_OBSERVABILITY", False),
            observability_bucket=os.getenv("SERTOR_OBSERVABILITY_BUCKET", "day"),
            observability_refresh_s=float(os.getenv("SERTOR_OBSERVABILITY_REFRESH", "2.0")),
            memory_enabled=_bool_env("SERTOR_MEMORY", False),
            memory_adapter=os.getenv("SERTOR_MEMORY_ADAPTER", "claude-code"),
            memory_retention_days=_int_or_none_env("SERTOR_MEMORY_RETENTION_DAYS"),
            memory_scrub_patterns=tuple(_split_env("SERTOR_MEMORY_SCRUB_PATTERNS") or ()),
            episodic_limit=int(os.getenv("SERTOR_EPISODIC_LIMIT", "20")),
            episodic_snippet_tokens=int(os.getenv("SERTOR_EPISODIC_SNIPPET_TOKENS", "12")),
            memory_list_limit=int(os.getenv("SERTOR_MEMORY_LIST_LIMIT", "20")),
            claude_projects_dir=(
                Path(os.environ["SERTOR_MEMORY_CLAUDE_PROJECTS_DIR"])
                if os.getenv("SERTOR_MEMORY_CLAUDE_PROJECTS_DIR")
                else Path.home() / ".claude" / "projects"
            ),
            index_dir=resolved_index_dir,
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", ""),
            azure_search_api_key=os.getenv("AZURE_SEARCH_API_KEY", ""),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1600")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            max_chunk_chars=int(os.getenv("SERTOR_MAX_CHUNK_CHARS", "8000")),
            default_k=int(os.getenv("DEFAULT_K", "5")),
            preview_chars=int(os.getenv("SERTOR_PREVIEW_CHARS", "240")),
            retrieval_min_score=_float_or_none_env("SERTOR_MIN_SCORE"),
            engine=os.getenv("SERTOR_ENGINE", "hybrid"),
            rrf_c=int(os.getenv("SERTOR_RRF_C", "60")),
            rrf_pool=int(os.getenv("SERTOR_RRF_POOL", "30")),
            rerank_enabled=_bool_env("SERTOR_RERANK", False),
            rerank_pool=int(os.getenv("SERTOR_RERANK_POOL", "15")),
            graph_enabled=_bool_env("SERTOR_GRAPH", True),
            graph_ambiguity_threshold=int(os.getenv("SERTOR_GRAPH_AMBIGUITY", "2")),
            graph_limit_definitions=int(os.getenv("SERTOR_GRAPH_LIMIT_DEFS", "10")),
            graph_limit_relations=int(os.getenv("SERTOR_GRAPH_LIMIT_RELS", "8")),
            graph_limit_docs=int(os.getenv("SERTOR_GRAPH_LIMIT_DOCS", "8")),
            index_incremental=_bool_env("SERTOR_INDEX_INCREMENTAL", True),
            index_reconcile_every=int(os.getenv("SERTOR_INDEX_RECONCILE_EVERY", "0")),
            exclude_patterns=tuple(excludes) if excludes is not None else _DEFAULT_EXCLUDES,
        )
