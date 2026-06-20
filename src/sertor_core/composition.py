"""Composition root for the core (Principio I/VIII).

This is the ONLY component that knows the concrete adapters and wires them from the configuration.
Services and the facade depend only on ports; which implementation to use is decided here based
on `Settings`. Extend here (not in services) to add providers/backends.

Consumer entry points (`build_*`): facade/indexer/engine/graph/memory, plus the ground-truth eval
vehicle (065): `build_eval_runner` (runs the suite against the configured engine) and
`build_indexed_docs` (the indexed paths from the manifest, for write-time path validation). The
CLI `eval` subcommand consumes these factories, never importing engines/manifest (Principio XI).
"""
from __future__ import annotations

from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError
from sertor_core.domain.ports import (
    EmbeddingProvider,
    LexicalIndex,
    Reranker,
    TranscriptCaptureAdapter,
    VectorStore,
)

_VALID_ENGINES = ("baseline", "hybrid")
_VALID_MEMORY_ADAPTERS = ("claude-code",)


def _validated_engine(settings: Settings) -> str:
    """Validated `Settings.engine` value: unknown → `ConfigError` with allowed values."""
    if settings.engine not in _VALID_ENGINES:
        raise ConfigError(
            f"unknown engine: {settings.engine!r} (allowed: {', '.join(_VALID_ENGINES)})",
            key="SERTOR_ENGINE",
        )
    return settings.engine


def _build_lexical(settings: Settings) -> LexicalIndex:
    """Lexical index for the hybrid engine: BM25 sidecar in the index directory (FEAT-004)."""
    from sertor_core.adapters.lexical.bm25 import Bm25LexicalIndex

    return Bm25LexicalIndex(settings.index_dir)


def _build_reranker(settings: Settings) -> Reranker | None:
    """Optional reranker (extra `rerank`, lazy): configured but missing → error (REQ-022)."""
    if not settings.rerank_enabled:
        return None
    try:
        from sertor_core.adapters.rerank.flashrank import FlashRankReranker

        return FlashRankReranker()
    except ImportError as exc:
        raise ConfigError(
            "reranking enabled but the extra is not installed: "
            'uv add "sertor-core[rerank]" (or SERTOR_RERANK=false)',
            key="SERTOR_RERANK",
        ) from exc


def build_embedder(
    settings: Settings | None = None, *, cache: bool = False
) -> EmbeddingProvider:
    """Build the embedding provider selected by the configuration (REQ-013/030).

    Wires the retry policy (018, REQ-H3) from `Settings`: transient provider failures are retried
    with exponential backoff + jitter. `embed_retry_attempts=1` disables retries (as before).

    With `cache=True` (019, REQ-H4) the provider is wrapped in a `CachingEmbedder` so re-indexing
    an unchanged corpus does not re-embed identical chunks. Only the indexing path opts in (the
    query path has low reuse): see `build_indexer`. Lazy import keeps the cache off the hot path.
    """
    from sertor_core.adapters.embeddings._retry import RetryPolicy

    settings = settings or Settings.load()
    retry = RetryPolicy(
        max_attempts=settings.embed_retry_attempts,
        base_backoff_s=settings.embed_retry_base_s,
    )
    if settings.embed_provider == "azure":
        from sertor_core.adapters.embeddings.azure import AzureEmbedder

        embedder: EmbeddingProvider = AzureEmbedder(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_embed_deployment,
            batch_size=settings.embed_batch_size,
            retry=retry,
        )
    else:
        from sertor_core.adapters.embeddings.ollama import OllamaEmbedder

        embedder = OllamaEmbedder(
            host=settings.ollama_host,
            model=settings.ollama_embed_model,
            batch_size=settings.embed_batch_size,
            retry=retry,
        )
    if cache:
        from sertor_core.adapters.embeddings.cache import CachingEmbedder, EmbeddingCache

        return CachingEmbedder(embedder, EmbeddingCache(settings.index_dir))
    return embedder


def build_store(settings: Settings | None = None) -> VectorStore:
    """Build the vector store backend selected by the configuration (REQ-018/030).

    The store backend is **decoupled** from the embedding provider (`store_backend`, not
    `backend`): Azure embeddings can be combined with a local Chroma store (or vice versa),
    staying true to local-first (Principio II). Default: see `Settings.store_backend`.
    """
    settings = settings or Settings.load()
    if settings.store_backend == "azure":
        from sertor_core.adapters.vectorstores.azure_search import AzureSearchStore

        return AzureSearchStore(
            endpoint=settings.azure_search_endpoint,
            api_key=settings.azure_search_api_key,
        )
    from sertor_core.adapters.vectorstores.chroma import ChromaStore

    return ChromaStore(persist_dir=settings.index_dir)


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name).strip("_")


def collection_name(settings: Settings, embedder: EmbeddingProvider) -> str:
    """Collection name namespaced by (corpus, provider): isolates corpora and providers (REQ-019).

    The provider (name+model) determines vector dimension: including it prevents mixing
    embeddings of different dimensions in the same collection.
    """
    base = f"{settings.corpus}__{_sanitize(embedder.name)}"
    if settings.store_backend == "azure":
        # Azure AI Search: index names have naming constraints (lowercase, letter-initial).
        base = base.lower().lstrip("0123456789_") or "sertor"
    # Chroma/Azure require names of 3+ characters: guarantees the minimum length.
    return base if len(base) >= 3 else f"{base}_idx"


def build_graph_service(settings: Settings | None = None):
    """Build the code graph service (FEAT-005) — ORTHOGONAL to `SERTOR_ENGINE` (REQ-013).

    Dedicated factory: the graph is structural navigation, not similarity retrieval; it does
    not go through the engine knob. The adapter builds the artifact WITHOUT the `graph` extra;
    navigation requires it (lazy imports in query methods, actionable error — DA-5).
    """
    from sertor_core.adapters.graph.networkx_graph import NetworkxCodeGraph

    settings = settings or Settings.load()
    _wire_runtime(settings)
    return NetworkxCodeGraph(
        settings.index_dir,
        settings.corpus,
        limits=(
            settings.graph_limit_definitions,
            settings.graph_limit_relations,
            settings.graph_limit_docs,
        ),
    )


def build_observability_store(settings: Settings | None = None):
    """Build the persistent observability store (feature 020) — the seam for FEAT-002.

    Returns the SQLite-backed `ObservabilityStore` at `<index_dir>/observability.sqlite`. Lazy
    import (stdlib only, no new mandatory dependency). The aggregation feature will read from here.
    """
    from sertor_core.observability.store import SqliteObservabilityStore

    settings = settings or Settings.load()
    return SqliteObservabilityStore(settings.index_dir)


def build_observability_reports(settings: Settings | None = None):
    """Build the observability reports service (feature 021) — the seam for the panel (F3/F4)/CLI.

    Reuses the F1 store (via `build_observability_store`) and produces the five report families with
    pure, deterministic aggregations. Lazy import (stdlib only).
    """
    from sertor_core.services.observability_report import ObservabilityReports

    settings = settings or Settings.load()
    return ObservabilityReports(
        build_observability_store(settings), default_bucket=settings.observability_bucket
    )


def _load_observability_app():
    """Import the Textual panel (extra `[tui]`). Isolated so the missing-extra path is testable."""
    from sertor_core.observability.tui import ObservabilityApp

    return ObservabilityApp


def run_observability_panel(settings: Settings | None = None) -> None:
    """Launch the live observability TUI panel (feature 022).

    Lazy import of the `[tui]` extra: missing → actionable `ConfigError` (like `rerank`/`graph`).
    The panel is read-only; with persistence off it shows an honest empty state (no crash).
    """
    settings = settings or Settings.load()
    try:
        app_cls = _load_observability_app()
    except ImportError as exc:
        raise ConfigError(
            'the live panel requires the extra: uv add "sertor-core[tui]" (textual)',
            key="tui",
        ) from exc
    app_cls(build_observability_reports(settings), refresh_s=settings.observability_refresh_s).run()


def enable_observability(settings: Settings | None = None) -> bool:
    """Attach the observability handlers to the `sertor_core` logger if enabled (020 + 061).

    Two INDEPENDENT, idempotent sinks on the same event stream:
    - `EventPersistenceHandler` (020) when `observability_enabled` → persists events to the store;
    - `OtelExportHandler` (061, FEAT-005) when `observability_otel_enabled` → exports events to an
      OTLP backend (IN ADDITION to the store, REQ-E4). Requires the `[otel]` extra → actionable
      `ConfigError` if missing.
    A no-op (returns False) when BOTH are off — no handler attached, no store created (FR-004).
    Consumers (CLI/MCP) call this once at startup; the observed operations stay untouched (FR-005).
    """
    settings = settings or Settings.load()
    if not (settings.observability_enabled or settings.observability_otel_enabled):
        return False

    import logging

    from sertor_core.observability.logging import get_logger

    logger = get_logger()
    # The logger gates record CREATION: by default it inherits WARNING, so INFO events (index,
    # embeddings, cache, retrieve) would never reach a handler. Lower the threshold to INFO so the
    # handlers can CAPTURE them. This adds no stderr noise on its own: whether INFO is DISPLAYED
    # still depends on the consumer's own (stderr) handler level.
    if logger.level == logging.NOTSET or logger.level > logging.INFO:
        logger.setLevel(logging.INFO)

    if settings.observability_enabled:
        from sertor_core.observability.capture import EventPersistenceHandler

        if not any(isinstance(h, EventPersistenceHandler) for h in logger.handlers):
            logger.addHandler(EventPersistenceHandler(build_observability_store(settings)))

    if settings.observability_otel_enabled:
        from sertor_core.observability.otel import OtelExportHandler, build_otel_handler

        if not any(isinstance(h, OtelExportHandler) for h in logger.handlers):
            logger.addHandler(build_otel_handler())

    return True


def _wire_runtime(settings: Settings) -> None:
    """Apply the cross-cutting concerns for any consumer entry path (Principio XI, feature 041).

    Today this activates observability (idempotent, no-op when disabled): a consumer entering via a
    `build_*` factory gets the same wiring as the CLI/MCP, closing the gap where a re-index via the
    library bypassed `enable_observability`. Single home for future cross-cutting wiring; keeps the
    dependencies pointing inward (the wiring lives in the composition root, not the services).
    """
    enable_observability(settings)


def build_indexer(settings: Settings | None = None):
    """Build the indexing orchestrator wired from the configuration (REQ-029).

    With `engine=hybrid` (default) the pipeline receives the lexical sink: each `index()` also
    writes the BM25 sidecar — this is what makes the hint «re-index enables hybrid» true (REQ-034).
    With `baseline` the pipeline is identical to before FEAT-004 (REQ-071).
    With `graph_enabled` (default) it also receives the code graph sink (FEAT-005, DA-2):
    a single command keeps both retrieval and graph up to date.
    """
    from sertor_core.services.index_manifest import IndexManifest
    from sertor_core.services.indexing import IndexingService

    settings = settings or Settings.load()
    _wire_runtime(settings)
    engine = _validated_engine(settings)
    # Cache opt-in on the indexing path only (019, REQ-H4): re-index skips re-embedding unchanged
    # chunks. Default off → today's full re-embed (FR-007/013).
    embedder = build_embedder(settings, cache=settings.embed_cache_enabled)
    store = build_store(settings)
    lexical = _build_lexical(settings) if engine == "hybrid" else None
    graph = build_graph_service(settings) if settings.graph_enabled else None
    # Incremental indexing manifest (046, FEAT-009): the memory of «what is already indexed» that
    # enables the default incremental path. The service falls back to full when it's absent/invalid.
    manifest = IndexManifest(settings.index_dir)
    return IndexingService(
        embedder, store, collection_name(settings, embedder), settings,
        lexical=lexical, graph=graph, manifest=manifest,
    )


def build_facade(settings: Settings | None = None):
    """Build the retrieval facade wired from the configuration (REQ-029).

    Entry point for consumers: they import and use the facade without knowing the
    store/embeddings details. Extra corpora (`Settings.extra_corpora`, FR-007) become the
    corpus→collection map for the combined-search fan-out: the name is derived with the same
    `collection_name`, hence with the current embedding provider.
    """
    from dataclasses import replace

    from sertor_core.services.retrieval import RetrievalFacade

    settings = settings or Settings.load()
    _wire_runtime(settings)
    engine = _validated_engine(settings)
    embedder = build_embedder(settings)
    store = build_store(settings)
    extra = {
        corpus: collection_name(replace(settings, corpus=corpus), embedder)
        for corpus in settings.extra_corpora
    }
    retriever = None
    if engine == "hybrid":
        # Injected strategy (FR-017/018): same embedder/store as the facade, never duplicate
        # instances. The multi-collection fan-out remains dense-only (research D6).
        from sertor_core.engines.hybrid import HybridEngine

        retriever = HybridEngine(
            embedder,
            store,
            _build_lexical(settings),
            collection_name(settings, embedder),
            settings,
            reranker=_build_reranker(settings),
        )
    return RetrievalFacade(
        embedder,
        store,
        collection_name(settings, embedder),
        default_k=settings.default_k,
        extra_collections=extra,
        retriever=retriever,
        min_score=settings.retrieval_min_score,
        # RAG-demonstrability content (064): only when BOTH the store and the content opt-in are on.
        content_enabled=settings.observability_content_enabled and settings.observability_enabled,
    )


def build_baseline_engine(settings: Settings | None = None):
    """Build the baseline vector RAG engine wired from the configuration (REQ-012)."""
    from sertor_core.engines.baseline import BaselineEngine

    settings = settings or Settings.load()
    _wire_runtime(settings)
    embedder = build_embedder(settings)
    store = build_store(settings)
    return BaselineEngine(embedder, store, collection_name(settings, embedder), settings)


def build_capture_adapter(settings: Settings | None = None) -> TranscriptCaptureAdapter:
    """Build the transcript capture adapter selected by `Settings.memory_adapter` (031, FR-005).

    Single selection point (Principio I/X): `claude-code` → `ClaudeCodeCaptureAdapter`; unknown
    value → `ConfigError` with the allowed values (like `_validated_engine`). The import of the
    host-specific adapter is LAZY (inside this function), so it never runs at flag off (FR-002).
    """
    settings = settings or Settings.load()
    if settings.memory_adapter not in _VALID_MEMORY_ADAPTERS:
        raise ConfigError(
            f"unknown memory adapter: {settings.memory_adapter!r} "
            f"(allowed: {', '.join(_VALID_MEMORY_ADAPTERS)})",
            key="SERTOR_MEMORY_ADAPTER",
        )
    from sertor_core.adapters.capture.claude_code import (
        ClaudeCodeCaptureAdapter,
        encode_project_path,
    )

    project_id = str(Path.cwd())
    project_source_dir = settings.claude_projects_dir / encode_project_path(project_id)
    return ClaudeCodeCaptureAdapter(project_source_dir, project_id=project_id)


def build_memory_archive(settings: Settings | None = None):
    """Build the memory archive store (031): SQLite at `<index_dir>/memory.sqlite` (git-ignored)."""
    from sertor_core.adapters.memory.archive import MemoryArchive

    settings = settings or Settings.load()
    return MemoryArchive(settings.index_dir)


def build_memory_archiver(settings: Settings | None = None):
    """Build the transcript archiving service, or `None` when capture is off (031, FR-002, D8).

    Privacy-by-default gate: with `SERTOR_MEMORY=false` (default) this returns `None` WITHOUT
    importing the host-specific adapter — no adapter, no store, no file opened (SC-003). Only when
    opted in does it wire adapter + store + service.
    """
    from sertor_core.services.memory_archive import MemoryArchiveService

    settings = settings or Settings.load()
    if not settings.memory_enabled:
        return None
    return MemoryArchiveService(
        build_capture_adapter(settings), build_memory_archive(settings), settings
    )


def build_episodic_search(settings: Settings | None = None):
    """Build the episodic full-text search, or `None` when memory is off (033, FEAT-002).

    Same privacy-by-default gate as `build_memory_archiver`: with `SERTOR_MEMORY=false` (default)
    this returns `None` — no FTS index is created and no file is opened. Host-agnostic: the search
    receives only `settings.index_dir` (the archive location), never any host knowledge. The import
    of the service is LAZY (inside this function), consistent with the other `build_*`.
    """
    from sertor_core.services.episodic_search import EpisodicSearch

    settings = settings or Settings.load()
    if not settings.memory_enabled:
        return None
    return EpisodicSearch(settings.index_dir)


def build_memory_reader(settings: Settings | None = None):
    """Build the read surface of the archive, or `None` when memory is off (036, FEAT-003, D2).

    Same privacy-by-default gate as `build_memory_archiver`/`build_episodic_search`: with
    `SERTOR_MEMORY=false` (default) this returns `None` — no file is opened. Abilitata, returns the
    concrete `MemoryArchive` (reuses `build_memory_archive`): no new port, no wrapper (single
    consumer — YAGNI, Principio III). The CLI consumes the `None` as an actionable `ConfigError`.
    """
    settings = settings or Settings.load()
    if not settings.memory_enabled:
        return None
    return build_memory_archive(settings)


def build_engine(settings: Settings | None = None):
    """Build the RAG engine selected by `Settings.engine` (FEAT-004, REQ-030/031).

    SINGLE engine selection point (Principio I): `baseline` → `BaselineEngine` (unchanged),
    `hybrid` (default) → `HybridEngine`; unknown value → `ConfigError`.
    """
    settings = settings or Settings.load()
    _wire_runtime(settings)
    if _validated_engine(settings) == "baseline":
        return build_baseline_engine(settings)
    from sertor_core.engines.hybrid import HybridEngine

    embedder = build_embedder(settings)
    store = build_store(settings)
    return HybridEngine(
        embedder,
        store,
        _build_lexical(settings),
        collection_name(settings, embedder),
        settings,
        reranker=_build_reranker(settings),
    )


def build_engine_for(settings: Settings, label: str):
    """Build the engine named by `label` (`baseline`/`hybrid`) for the eval `--compare` (065).

    The label overrides `Settings.engine` for THIS engine only (the comparison evaluates ≥2 configs
    on the same suite, REQ-034); unknown label → `ConfigError` via `build_engine`'s validation.
    """
    from dataclasses import replace

    return build_engine(replace(settings, engine=label))


def build_eval_runner(settings: Settings | None = None):
    """Build the eval runner — the vehicle for `sertor-rag eval` (065, Principio XI).

    Returns a thin object that constructs the engine via `build_engine`/`build_engine_for` and runs
    the deterministic measure (`run_evaluation`). The run has NO privacy gate (it is a local measure
    over the index). Wires observability like the other consumer entry paths (feature 041).
    """
    settings = settings or Settings.load()
    _wire_runtime(settings)
    return _EvalRunner(settings)


class _EvalRunner:
    """Vehicle that runs the eval suite against the configured (or labelled) engine (065).

    Lives in the composition root: the ONLY place that knows how to build the concrete engine
    (Principio I/XI). The CLI consumes it, never importing engines/manifest directly.
    """

    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def settings(self) -> Settings:
        return self._settings

    def run(self, suite, ks: tuple[int, ...] = (1, 3, 5, 10)):
        """Evaluate `suite` against the current engine → `(EvalReport, kinds)`."""
        from sertor_core.services.eval.runner import run_evaluation

        engine = build_engine(self._settings)
        engine.ensure_index()
        return run_evaluation(engine, suite, ks)

    def run_labelled(self, label: str, suite, ks: tuple[int, ...] = (1, 3, 5, 10)):
        """Evaluate `suite` against the engine named `label` → `(EvalReport, kinds)` (REQ-034)."""
        from sertor_core.services.eval.runner import run_evaluation

        engine = build_engine_for(self._settings, label)
        engine.ensure_index()
        return run_evaluation(engine, suite, ks)


def build_indexed_docs(settings: Settings | None = None) -> frozenset[str] | None:
    """Indexed document paths from the manifest, or `None` if absent/incompatible (065, DA-e).

    Reuses `IndexManifest.load(collection_name(...))` for the current `(corpus, provider)`: the
    manifest's `files` keys are the indexed source paths (POSIX, relative to the indexing root). A
    missing/incompatible manifest → `None` (honest degradation, Principio IV) so the caller can warn
    «cannot verify» instead of pretending the index is empty. The vehicle for `validate_paths`.
    """
    from sertor_core.services.index_manifest import IndexManifest

    settings = settings or Settings.load()
    embedder = build_embedder(settings)
    collection = collection_name(settings, embedder)
    state = IndexManifest(settings.index_dir).load(collection)
    if state is None:
        return None
    return frozenset(state.files.keys())
