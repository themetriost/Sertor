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

    `None` → no loading (test isolation). Otherwise, in order:
    1. the given file if it exists (default `./.env`, relative to cwd);
    2. `.sertor/.env` under the cwd — the host install layout, found from the project root even
       when the venv is **not** nested under `.sertor/` (e.g. the Sertor dogfood, whose venv is
       `./.venv`). This keeps development and host on the SAME `.sertor/` config+index layout
       (FEAT-013), instead of dev reading `./.env` while hosts read `.sertor/.env`;
    3. `.env` in the folder of the **project that owns the current venv**
       (`Path(sys.prefix).parent`) — for an installed runtime whose venv lives at `.sertor/.venv`
       this is `.sertor/`. This still loads `.sertor/.env` (and anchors the index there) from
       **any** cwd, not only when launched from inside `.sertor/`.
    """
    if env_file is None:
        return None
    explicit = Path(env_file)
    if explicit.exists():
        return explicit
    cwd_sertor_env = Path.cwd() / ".sertor" / ".env"
    if cwd_sertor_env.exists():
        return cwd_sertor_env
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

    # embeddings provider & store (068, FEAT-011): two INDEPENDENT knobs (RAG_BACKEND removed).
    # `embed_provider` selects the embedding provider; `store_backend` selects the vector store.
    embed_provider: str = "glove"          # glove | hash | ollama | azure (validated downstream)
    store_backend: str = "local"           # local | azure — VECTOR STORE backend (decoupled)
    glove_path: Path | None = None         # SERTOR_GLOVE_PATH — override of glove.6B.300d.txt
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
    # observability OTel export (061, FEAT-005): export the structured events ALSO to an external
    # OpenTelemetry backend (in addition to the local store). Default off; needs the optional extra
    # `[otel]`. Endpoint/transport come from the standard `OTEL_EXPORTER_OTLP_*` env vars.
    observability_otel_enabled: bool = False
    # observability CONTENT visibility (064, FEAT-015): opt-in raw-text (REQ-E9) for LOCAL RAG
    # demonstrability — when on (AND the store is enabled), retrieval/MCP events also carry the
    # query + a results preview + a top-1 snippet (all secret-scrubbed), so the TUI "RAG" tab shows
    # query · result · hit/miss. Default OFF (privacy-by-default preserved); never a host default.
    observability_content_enabled: bool = False

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
    # optional semantic search over the memory archive (072, FEAT-004). A SECOND opt-in, distinct
    # from `memory_enabled`: turning on capture must never turn on embedding (REQ-003). Default only
    # here (Principio VIII). Gated by `memory_enabled AND memory_semantic_enabled` in composition.
    memory_semantic_enabled: bool = False     # SERTOR_MEMORY_SEMANTIC — opt-in (default: off)
    memory_semantic_limit: int = 20           # SERTOR_MEMORY_SEMANTIC_LIMIT — max results (REQ-011)
    # session listing for distillation (036, FEAT-003). Max sessions returned by `memory list`,
    # overridable per-invocation by `-k/--limit`. Default only here (Principio VIII).
    memory_list_limit: int = 20               # SERTOR_MEMORY_LIST_LIMIT — max sessions (FR-002)
    # Source directory of the Claude Code projects (host-agnostic, testable): default
    # `~/.claude/projects`. The adapter resolves the per-project encoded subfolder from here.
    claude_projects_dir: Path = field(
        default_factory=lambda: Path.home() / ".claude" / "projects"
    )
    # Source directory of the GitHub Copilot CLI session-state (host-agnostic, testable): default
    # `~/.copilot/session-state`. The copilot-cli adapter enumerates the per-session UUID subfolders
    # from here (FEAT-008, mirror of `claude_projects_dir`).
    copilot_session_dir: Path = field(
        default_factory=lambda: Path.home() / ".copilot" / "session-state"
    )

    # vector store
    index_dir: Path = field(default_factory=lambda: Path(".index"))
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""

    # chunking
    chunk_size: int = 1600
    chunk_overlap: int = 200
    # Hard cap on a single chunk's size, in TOKENS. Structural chunkers (markdown by heading, code
    # symbol) can emit a unit far larger than `chunk_size`; embedding providers reject inputs over a
    # token budget (text-embedding-3-large: 8192 tokens → http 400). A chunk above this cap is
    # sub-split. Default 8191 uses (almost) the full large-model window — keeping coherent sections
    # whole instead of fragmenting them — while staying within the 8192-token limit. Token counting
    # uses tiktoken (extra `tokenizer`) when present, else a safe per-char estimate. Lower it for an
    # embedder with a smaller context window.
    max_chunk_tokens: int = 8191

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
    # query-time dedup of near-duplicate results before the top-k cut (E5-FEAT-003 / A-07).
    # Default on: it is a no-op on already-distinct results and un-buries canonical pages when the
    # same content lives in multiple paths. Reuses `rerank_pool` as the pre-cut pool size (D1).
    dedup_enabled: bool = True

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

    # ground-truth evaluation (065, FEAT-001): the eval suite + non-regression baseline live as
    # VERSIONED project data under `eval_dir` (NOT `.sertor/`, NOT the index). Default only here
    # (Principio VIII); a comando non invocato il costo è identico a oggi (additività, REQ-062).
    eval_dir: Path = field(default_factory=lambda: Path("eval"))  # SERTOR_EVAL_DIR
    eval_tolerance: float = 0.0        # SERTOR_EVAL_TOLERANCE — absolute gate tolerance (REQ-043)

    # graph-navigation evaluation (066, FEAT-011): set-based oracle over the code graph. The suite
    # `[[graph_case]]` and the navigation baseline live in `eval_dir` too (graph_baseline.toml).
    # Defaults only here (Principio VIII); a comando non invocato il costo è identico a oggi.
    graph_eval_tolerance: float = 0.0  # SERTOR_GRAPH_EVAL_TOLERANCE — mean_f1 gate tolerance
    graph_eval_exact: bool = False     # SERTOR_GRAPH_EVAL_EXACT — exact-set gate (got != expected)

    # fused code+doc evaluation (070, FEAT-003): top-k on which the union hit-rate of `both`-intent
    # cases is computed (a case «hits» when the top-k carries ≥1 relevant DOC OR ≥1 relevant CODE —
    # the union, not the product). `eval_tolerance` (above) is REUSED for the fused non-regression
    # gate (the tolerance is unique). Default only here (Principio VIII); a comando non invocato
    # costo uguale.
    eval_fusion_k: int = 5             # SERTOR_EVAL_FUSION_K — top-k for the union hit-rate (DA-c)

    # ingestione
    exclude_patterns: tuple[str, ...] = _DEFAULT_EXCLUDES

    def validate_backend(self) -> list[str]:
        """Names of required but missing environment variables for the selected provider/store (D3).

        **Static** validation (FR-015): does not contact services; returns only the list of
        empty configuration fields required by the chosen embedding provider/store. This is the ONLY
        source of the "which fields are needed for azure" map (Principio VIII): the CLI knows only
        the outcome. Local providers (`glove`/`hash`/Ollama, Chroma — valid defaults) are never
        blocked → empty list (068, REQ-005/007, DA-7).
        """
        missing: list[str] = []
        if self.embed_provider == "azure":
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
        if env_path is None and env_file is not None:
            # No configuration source (no `.env` in cwd nor next to the runtime): falling back to
            # defaults (provider `glove`, store `local`). Signalled to avoid the silent fallback
            # that causes confusion when a configured `.sertor/.env` was simply not loaded.
            from sertor_core.observability.logging import log_event
            log_event(
                logging.WARNING, "config_no_env_found",
                note="no .env found; using defaults (provider glove, store local)",
            )
        if os.getenv("RAG_BACKEND") is not None:
            # Fail loud, do not migrate silently (068, REQ-007, Principio XII): `RAG_BACKEND` is no
            # longer honoured. The value is NEITHER read NOR mapped — only signalled, naming the
            # replacement knobs so the host can migrate `.env` deliberately.
            from sertor_core.observability.logging import log_event
            log_event(
                logging.WARNING, "config_rag_backend_ignored",
                note=(
                    "RAG_BACKEND is no longer honoured; select the embedding provider with "
                    "SERTOR_EMBED_PROVIDER and the vector store with SERTOR_STORE_BACKEND"
                ),
            )
        # Index anchor: explicit > runtime home (folder of resolved `.env`) > cwd.
        if index_dir:
            resolved_index_dir = Path(index_dir)
        elif env_path is not None:
            resolved_index_dir = env_path.parent / ".index"
        else:
            resolved_index_dir = Path(".index")
        return cls(
            # Provider and store are INDEPENDENT knobs (068, DA-1): the embedding provider from
            # SERTOR_EMBED_PROVIDER (default glove), the vector store from SERTOR_STORE_BACKEND
            # (default local). Any combination is valid (e.g. Azure embeddings + local Chroma).
            embed_provider=os.getenv("SERTOR_EMBED_PROVIDER", "glove"),
            store_backend=os.getenv("SERTOR_STORE_BACKEND", "local"),
            glove_path=(
                Path(os.environ["SERTOR_GLOVE_PATH"])
                if os.getenv("SERTOR_GLOVE_PATH")
                else None
            ),
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
            observability_otel_enabled=_bool_env("SERTOR_OBSERVABILITY_OTEL", False),
            observability_content_enabled=_bool_env("SERTOR_OBSERVABILITY_CONTENT", False),
            memory_enabled=_bool_env("SERTOR_MEMORY", False),
            memory_adapter=os.getenv("SERTOR_MEMORY_ADAPTER", "claude-code"),
            memory_retention_days=_int_or_none_env("SERTOR_MEMORY_RETENTION_DAYS"),
            memory_scrub_patterns=tuple(_split_env("SERTOR_MEMORY_SCRUB_PATTERNS") or ()),
            episodic_limit=int(os.getenv("SERTOR_EPISODIC_LIMIT", "20")),
            episodic_snippet_tokens=int(os.getenv("SERTOR_EPISODIC_SNIPPET_TOKENS", "12")),
            memory_semantic_enabled=_bool_env("SERTOR_MEMORY_SEMANTIC", False),
            memory_semantic_limit=int(os.getenv("SERTOR_MEMORY_SEMANTIC_LIMIT", "20")),
            memory_list_limit=int(os.getenv("SERTOR_MEMORY_LIST_LIMIT", "20")),
            claude_projects_dir=(
                Path(os.environ["SERTOR_MEMORY_CLAUDE_PROJECTS_DIR"])
                if os.getenv("SERTOR_MEMORY_CLAUDE_PROJECTS_DIR")
                else Path.home() / ".claude" / "projects"
            ),
            copilot_session_dir=(
                Path(os.environ["SERTOR_MEMORY_COPILOT_SESSION_DIR"])
                if os.getenv("SERTOR_MEMORY_COPILOT_SESSION_DIR")
                else Path.home() / ".copilot" / "session-state"
            ),
            index_dir=resolved_index_dir,
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", ""),
            azure_search_api_key=os.getenv("AZURE_SEARCH_API_KEY", ""),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1600")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            max_chunk_tokens=int(os.getenv("SERTOR_MAX_CHUNK_TOKENS", "8191")),
            default_k=int(os.getenv("DEFAULT_K", "5")),
            preview_chars=int(os.getenv("SERTOR_PREVIEW_CHARS", "240")),
            retrieval_min_score=_float_or_none_env("SERTOR_MIN_SCORE"),
            engine=os.getenv("SERTOR_ENGINE", "hybrid"),
            rrf_c=int(os.getenv("SERTOR_RRF_C", "60")),
            rrf_pool=int(os.getenv("SERTOR_RRF_POOL", "30")),
            rerank_enabled=_bool_env("SERTOR_RERANK", False),
            rerank_pool=int(os.getenv("SERTOR_RERANK_POOL", "15")),
            dedup_enabled=_bool_env("SERTOR_DEDUP", True),
            graph_enabled=_bool_env("SERTOR_GRAPH", True),
            graph_ambiguity_threshold=int(os.getenv("SERTOR_GRAPH_AMBIGUITY", "2")),
            graph_limit_definitions=int(os.getenv("SERTOR_GRAPH_LIMIT_DEFS", "10")),
            graph_limit_relations=int(os.getenv("SERTOR_GRAPH_LIMIT_RELS", "8")),
            graph_limit_docs=int(os.getenv("SERTOR_GRAPH_LIMIT_DOCS", "8")),
            index_incremental=_bool_env("SERTOR_INDEX_INCREMENTAL", True),
            index_reconcile_every=int(os.getenv("SERTOR_INDEX_RECONCILE_EVERY", "0")),
            eval_dir=Path(os.getenv("SERTOR_EVAL_DIR", "eval")),
            eval_tolerance=float(os.getenv("SERTOR_EVAL_TOLERANCE", "0.0")),
            graph_eval_tolerance=float(os.getenv("SERTOR_GRAPH_EVAL_TOLERANCE", "0.0")),
            graph_eval_exact=_bool_env("SERTOR_GRAPH_EVAL_EXACT", False),
            eval_fusion_k=int(os.getenv("SERTOR_EVAL_FUSION_K", "5")),
            exclude_patterns=tuple(excludes) if excludes is not None else _DEFAULT_EXCLUDES,
        )
