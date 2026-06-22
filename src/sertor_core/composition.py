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

import logging
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
from sertor_core.observability.logging import log_event

_VALID_ENGINES = ("baseline", "hybrid")
_VALID_MEMORY_ADAPTERS = ("claude-code", "copilot-cli")


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


_VALID_EMBED_PROVIDERS = ("glove", "hash", "ollama", "azure")


def build_embedder(
    settings: Settings | None = None, *, cache: bool = False, allow_download: bool = False
) -> EmbeddingProvider:
    """Build the embedding provider selected by `Settings.embed_provider` (068, REQ-001/003).

    FOUR branches with a lazy import per branch (Principio I — no new adapter imported at module
    top): `glove` (default, static NL vectors), `hash` (airgapped/CI lexical floor), `ollama`,
    `azure`. An unknown value → `ConfigError(key="SERTOR_EMBED_PROVIDER")` naming allowed values.

    Wires the retry policy (018, REQ-H3) for the cloud/Ollama providers; the local providers
    (`glove`/`hash`) need none. `allow_download` (068, REQ-034) is passed `True` only by the
    indexing path: it lets `glove` acquire its data file on-demand; query paths pass `False`.

    With `cache=True` (019, REQ-H4) the provider is wrapped in a `CachingEmbedder`.
    """
    from sertor_core.adapters.embeddings._retry import RetryPolicy

    settings = settings or Settings.load()
    provider = settings.embed_provider
    retry = RetryPolicy(
        max_attempts=settings.embed_retry_attempts,
        base_backoff_s=settings.embed_retry_base_s,
    )
    if provider == "glove":
        from sertor_core.adapters.embeddings.glove import GloveEmbedder
        from sertor_core.adapters.embeddings.glove_cache import resolve_glove_file

        glove_file = resolve_glove_file(settings, allow_download=allow_download)
        embedder: EmbeddingProvider = GloveEmbedder(
            glove_file, batch_size=settings.embed_batch_size
        )
        log_event(logging.INFO, "embeddings_provider_selected", provider=provider)
    elif provider == "hash":
        from sertor_core.adapters.embeddings.hashing import HashingEmbedder

        embedder = HashingEmbedder(batch_size=settings.embed_batch_size)
        log_event(logging.INFO, "embeddings_provider_selected", provider=provider)
        log_event(
            logging.WARNING, "embeddings_lexical_only",
            note=(
                "the 'hash' provider gives lexical signal only; NL semantic search is limited; "
                "configure glove/ollama/azure for semantic retrieval"
            ),
        )
    elif provider == "ollama":
        from sertor_core.adapters.embeddings.ollama import OllamaEmbedder

        embedder = OllamaEmbedder(
            host=settings.ollama_host,
            model=settings.ollama_embed_model,
            batch_size=settings.embed_batch_size,
            retry=retry,
        )
    elif provider == "azure":
        from sertor_core.adapters.embeddings.azure import AzureEmbedder

        embedder = AzureEmbedder(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_embed_deployment,
            batch_size=settings.embed_batch_size,
            retry=retry,
        )
    else:
        raise ConfigError(
            f"unknown embedding provider: {provider!r} "
            f"(allowed: {', '.join(_VALID_EMBED_PROVIDERS)})",
            key="SERTOR_EMBED_PROVIDER",
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
    # chunks. Default off → today's full re-embed (FR-007/013). `allow_download=True` (068, REQ-034)
    # makes the indexing path the ONLY one allowed to acquire the GloVe data file on-demand.
    embedder = build_embedder(
        settings, cache=settings.embed_cache_enabled, allow_download=True
    )
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

    Single selection point (Principio I/X): `claude-code` → `ClaudeCodeCaptureAdapter`,
    `copilot-cli` → `CopilotCliCaptureAdapter` (FEAT-008); unknown value → `ConfigError` with values
    (like `_validated_engine`). The import of each host-specific adapter is LAZY (inside this
    function), so it never runs at flag off / for the unselected adapter (FR-002, RNF-3).
    """
    settings = settings or Settings.load()
    if settings.memory_adapter not in _VALID_MEMORY_ADAPTERS:
        raise ConfigError(
            f"unknown memory adapter: {settings.memory_adapter!r} "
            f"(allowed: {', '.join(_VALID_MEMORY_ADAPTERS)})",
            key="SERTOR_MEMORY_ADAPTER",
        )
    project_id = str(Path.cwd())
    if settings.memory_adapter == "claude-code":
        from sertor_core.adapters.capture.claude_code import (
            ClaudeCodeCaptureAdapter,
            encode_project_path,
        )

        project_source_dir = settings.claude_projects_dir / encode_project_path(project_id)
        return ClaudeCodeCaptureAdapter(project_source_dir, project_id=project_id)

    # settings.memory_adapter == "copilot-cli"
    from sertor_core.adapters.capture.copilot_cli import CopilotCliCaptureAdapter  # LAZY (RNF-3)

    return CopilotCliCaptureAdapter(settings.copilot_session_dir, project_id=project_id)


def build_memory_archive(settings: Settings | None = None):
    """Build the memory archive store (031): SQLite at `<index_dir>/memory.sqlite` (git-ignored)."""
    from sertor_core.adapters.memory.archive import MemoryArchive

    settings = settings or Settings.load()
    return MemoryArchive(settings.index_dir)


def build_memory_semantic_index(settings: Settings | None = None, *, allow_download: bool = False):
    """Build the optional semantic index over the memory archive, or `None` (072, FEAT-004).

    Two-layer privacy gate (REQ-001/002/003): returns `None` unless BOTH `memory_enabled` AND
    `memory_semantic_enabled` are on — turning on capture (`SERTOR_MEMORY`) NEVER turns on
    embedding (`SERTOR_MEMORY_SEMANTIC`). With the gate off it builds NEITHER embedder NOR store and
    imports no semantic path (additivity, RNF-005/SC-011).

    With the gate on it REUSES ONLY the core primitives (Principio I/III, REQ-016): `build_embedder`
    (provider from `SERTOR_EMBED_PROVIDER`, no new selector — REQ-018), `build_store`, and
    `collection_name` over a memory-namespaced `Settings` (`corpus = f"memory__{corpus}"`) so the
    memory collection NEVER coincides with the project corpus (isolation, REQ-017/SC-009). A
    provider change → a different `embedder.name` → a different collection → an implicit rebuild
    (REQ-032).

    `allow_download` mirrors `build_indexer`: only the indexing path passes `True` (GloVe may
    acquire its data file); query paths pass `False`. When `memory_semantic_enabled` is on but
    `memory_enabled` is off, a warning names the missing `SERTOR_MEMORY` dependency (REQ-002).
    """
    from dataclasses import replace

    from sertor_core.services.memory_semantic import MemorySemanticIndex

    settings = settings or Settings.load()
    if not settings.memory_semantic_enabled:
        return None
    if not settings.memory_enabled:
        log_event(
            logging.WARNING, "memory_semantic_unavailable", reason="capture_disabled",
            note="SERTOR_MEMORY_SEMANTIC=true requires SERTOR_MEMORY=true (capture)",
        )
        return None
    embedder = build_embedder(settings, allow_download=allow_download)
    store = build_store(settings)
    memory_settings = replace(settings, corpus=f"memory__{settings.corpus}")
    collection = collection_name(memory_settings, embedder)
    return MemorySemanticIndex(embedder, store, collection, settings)


def build_memory_archiver(
    settings: Settings | None = None,
    semantic_index=None,
):
    """Build the transcript archiving service, or `None` when capture is off (031, FR-002, D8).

    Privacy-by-default gate: with `SERTOR_MEMORY=false` (default) this returns `None` WITHOUT
    importing the host-specific adapter — no adapter, no store, no file opened (SC-003). Only when
    opted in does it wire adapter + store + service.

    `semantic_index` (072, FEAT-004): an optional `MemorySemanticIndex` injected for the auto-index
    at end-of-session (REQ-004). When `None` (default — leva spenta or simply not passed), the
    service behaves exactly as FEAT-001 (REQ-005/RNF-005). The injection happens ONLY here
    (composition is the single place that knows the concrete adapters, Principio I).
    """
    from sertor_core.services.memory_archive import MemoryArchiveService

    settings = settings or Settings.load()
    if not settings.memory_enabled:
        return None
    return MemoryArchiveService(
        build_capture_adapter(settings), build_memory_archive(settings), settings,
        semantic_index=semantic_index,
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

    def run_by_kind(self, suite, ks: tuple[int, ...] = (1, 3, 5, 10)):
        """Evaluate routing each case by KIND: `symbol`→code-graph, else→engine (065 follow-up).

        Honest measure of the COMPOSITE system (relevance + graph), not one leg: a `symbol` lookup
        is a definition question answered by `find_symbol`, the rest by the relevance engine. Builds
        both vehicles (Principio XI) and wraps them in `RoutedEvalEngine`. Requires the code graph.
        """
        from sertor_core.domain.errors import ConfigError
        from sertor_core.services.eval.runner import RoutedEvalEngine, run_evaluation

        engine = build_engine(self._settings)
        engine.ensure_index()
        graph = build_graph_service(self._settings)
        if not graph.exists(self._settings.corpus):
            raise ConfigError(
                "eval --by-kind requires the code graph; re-index with SERTOR_GRAPH=true",
                key="SERTOR_GRAPH",
            )
        kind_by_query = {c.query: c.kind for c in suite.cases if c.kind}
        routed = RoutedEvalEngine(engine, graph, kind_by_query)
        return run_evaluation(routed, suite, ks)


def build_graph_eval_runner(settings: Settings | None = None, *, exact_gate: bool = False):
    """Build the graph-navigation eval runner — the vehicle for `sertor-rag graph-eval` (066).

    REUSES `build_graph_service` to navigate (Principio XI — the ONLY place that knows the concrete
    `NetworkxCodeGraph` for this path) and the `services/eval/graph_*` modules for the set-based
    measure. Wires observability like the other consumer entry paths (feature 041). `exact_gate`
    comes from the CLI flag or `Settings.graph_eval_exact`.
    """
    settings = settings or Settings.load()
    _wire_runtime(settings)
    graph = build_graph_service(settings)
    return _GraphEvalRunner(graph, settings, exact_gate=exact_gate)


class _GraphEvalRunner:
    """Vehicle that runs the graph-navigation suite against the built code graph (066).

    Lives in the composition root: the ONLY place that knows the concrete graph adapter for this
    path (Principio I/XI). The CLI consumes it, never importing the graph/navigation directly.
    """

    def __init__(self, graph, settings: Settings, *, exact_gate: bool = False):
        self._graph = graph
        self._settings = settings
        self._exact_gate = exact_gate

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def graph(self):
        return self._graph

    def run(self, suite):
        """Navigate + score the suite → `(GraphEvalReport, GraphRegressionVerdict)` (REQ-013/032).

        Requires the graph to be built (`graph.exists(corpus)` → else `GraphNotFoundError`,
        actionable). Compares against `eval/graph_baseline.toml` (absent → `None`, gate passes) and
        emits the metrics-only `graph_eval` event.
        """
        from sertor_core.domain.errors import GraphNotFoundError
        from sertor_core.services.eval.graph_baseline_io import load_graph_baseline
        from sertor_core.services.eval.graph_regression import compare_graph_to_baseline
        from sertor_core.services.eval.graph_runner import (
            emit_graph_eval_event,
            run_graph_evaluation,
        )

        if not self._graph.exists(self._settings.corpus):
            raise GraphNotFoundError(
                "graph-eval requires the code graph; re-index with SERTOR_GRAPH=true",
                corpus=self._settings.corpus,
            )
        report = run_graph_evaluation(self._graph, suite)
        baseline = load_graph_baseline(self._settings.eval_dir / "graph_baseline.toml")
        verdict = compare_graph_to_baseline(
            report, baseline, self._settings.graph_eval_tolerance
        )
        emit_graph_eval_event(report, verdict, self._exact_gate)
        return report, verdict


def build_fused_eval_runner(settings: Settings | None = None):
    """Build the fused (code+doc) eval runner — the vehicle for `sertor-rag eval --fused` (069).

    REUSES `build_facade` to retrieve (Principio XI — the facade is the vehicle; the ONLY place that
    knows the concrete embedder/store for this path) and the `services/eval/fused_*`/`fusion`
    modules for the per-surface + fusion-coverage measure. Wires observability like the other
    consumer entry paths (feature 041). Returns a thin runner exposing `run_fused(suite)`.
    """
    settings = settings or Settings.load()
    _wire_runtime(settings)
    return _FusedEvalRunner(settings)


class _FusedEvalRunner:
    """Vehicle that runs the fused eval suite against the configured retrieval facade (069).

    Lives in the composition root: the ONLY place that knows how to build the concrete facade for
    this path (Principio I/XI). The CLI consumes it, never importing the facade/engines directly.
    """

    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def settings(self) -> Settings:
        return self._settings

    def run_fused(self, suite, ks: tuple[int, ...] = (1, 3, 5, 10)):
        """Measure per-surface + fusion coverage and gate → `(FusedEvalReport, verdict)` (069).

        Builds the facade (vehicle), runs the deterministic measure, compares against the
        `[fused_baseline]` section of `eval/baseline.toml` (absent → `None`, gate passes with
        `no-baseline`), and emits the metrics-only `fused_eval` event.
        """
        from sertor_core.services.eval.baseline_io import load_fused_baseline
        from sertor_core.services.eval.fused_runner import (
            emit_fused_eval_event,
            run_fused_evaluation,
        )
        from sertor_core.services.eval.regression import compare_fused_to_baseline

        facade = build_facade(self._settings)
        report = run_fused_evaluation(facade, suite, ks, self._settings.eval_fusion_k)
        baseline = load_fused_baseline(self._settings.eval_dir / "baseline.toml")
        verdict = compare_fused_to_baseline(
            report, baseline, self._settings.eval_tolerance
        )
        emit_fused_eval_event(report, verdict)
        return report, verdict


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
