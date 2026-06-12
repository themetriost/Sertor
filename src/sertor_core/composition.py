"""Composition root del nucleo (Principio I/VIII).

È l'UNICO componente che conosce gli adapter concreti e li cabla a partire dalla configurazione.
I servizi e la facade dipendono solo dalle porte; qui si decide quale implementazione usare in base
a `Settings`. Estendere qui (non nei servizi) per aggiungere provider/backend.
"""
from __future__ import annotations

from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError
from sertor_core.domain.ports import EmbeddingProvider, LexicalIndex, Reranker, VectorStore

_VALID_ENGINES = ("baseline", "hybrid")


def _validated_engine(settings: Settings) -> str:
    """Valore di `Settings.engine` validato: sconosciuto → `ConfigError` coi valori ammessi."""
    if settings.engine not in _VALID_ENGINES:
        raise ConfigError(
            f"motore sconosciuto: {settings.engine!r} (ammessi: {', '.join(_VALID_ENGINES)})",
            key="SERTOR_ENGINE",
        )
    return settings.engine


def _build_lexical(settings: Settings) -> LexicalIndex:
    """Indice lessicale del motore ibrido: sidecar BM25 nella dir indici (FEAT-004)."""
    from sertor_core.adapters.lexical.bm25 import Bm25LexicalIndex

    return Bm25LexicalIndex(settings.index_dir)


def _build_reranker(settings: Settings) -> Reranker | None:
    """Reranker opzionale (extra `rerank`, lazy): configurato ma assente → errore (REQ-022)."""
    if not settings.rerank_enabled:
        return None
    try:
        from sertor_core.adapters.rerank.flashrank import FlashRankReranker

        return FlashRankReranker()
    except ImportError as exc:
        raise ConfigError(
            "reranking abilitato ma l'extra non è installato: "
            'uv add "sertor-core[rerank]" (oppure SERTOR_RERANK=false)',
            key="SERTOR_RERANK",
        ) from exc


def build_embedder(settings: Settings | None = None) -> EmbeddingProvider:
    """Costruisce il provider di embeddings selezionato dalla configurazione (REQ-013/030)."""
    settings = settings or Settings.load()
    if settings.embed_provider == "azure":
        from sertor_core.adapters.embeddings.azure import AzureEmbedder

        return AzureEmbedder(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_embed_deployment,
            batch_size=settings.embed_batch_size,
        )
    from sertor_core.adapters.embeddings.ollama import OllamaEmbedder

    return OllamaEmbedder(
        host=settings.ollama_host,
        model=settings.ollama_embed_model,
        batch_size=settings.embed_batch_size,
    )


def build_store(settings: Settings | None = None) -> VectorStore:
    """Costruisce il backend di vector store selezionato dalla configurazione (REQ-018/030).

    Il backend dello store è **disaccoppiato** dal provider di embeddings (`store_backend`, non
    `backend`): si possono combinare embeddings Azure con store Chroma locale (o viceversa),
    restando fedeli al local-first (Principio II). Default: vedi `Settings.store_backend`.
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
    """Nome di collezione namespaced per (corpus, provider): isola corpora e provider (REQ-019).

    Il provider (nome+modello) determina la dimensione dei vettori: includerlo evita di mescolare
    embedding di dimensioni diverse nella stessa collezione.
    """
    base = f"{settings.corpus}__{_sanitize(embedder.name)}"
    if settings.store_backend == "azure":
        # Azure AI Search: gli index hanno vincoli di naming (minuscolo, lettera iniziale).
        base = base.lower().lstrip("0123456789_") or "sertor"
    # Chroma/Azure richiedono nomi di 3+ caratteri: garantisce la lunghezza minima.
    return base if len(base) >= 3 else f"{base}_idx"


def build_graph_service(settings: Settings | None = None):
    """Costruisce il servizio di code-graph (FEAT-005) — ORTOGONALE a `SERTOR_ENGINE` (REQ-013).

    Factory dedicata: il grafo è navigazione strutturale, non retrieval per similarità; non
    passa dalla manopola dei motori. L'adapter costruisce l'artefatto SENZA l'extra `graph`;
    la navigazione lo richiede (import lazy nei metodi di query, errore azionabile — DA-5).
    """
    from sertor_core.adapters.graph.networkx_graph import NetworkxCodeGraph

    settings = settings or Settings.load()
    return NetworkxCodeGraph(
        settings.index_dir,
        settings.corpus,
        limits=(
            settings.graph_limit_definitions,
            settings.graph_limit_relations,
            settings.graph_limit_docs,
        ),
    )


def build_indexer(settings: Settings | None = None):
    """Costruisce l'orchestratore di indicizzazione cablato dalla configurazione (REQ-029).

    Con `engine=hybrid` (default) la pipeline riceve il sink lessicale: ogni `index()` scrive
    anche il sidecar BM25 — è ciò che rende vero l'hint «re-index abilita l'ibrido» (REQ-034).
    Con `baseline` la pipeline è identica a prima della FEAT-004 (REQ-071).
    Con `graph_enabled` (default) riceve anche il sink del code-graph (FEAT-005, DA-2):
    un solo comando tiene freschi retrieval e grafo.
    """
    from sertor_core.services.indexing import IndexingService

    settings = settings or Settings.load()
    engine = _validated_engine(settings)
    embedder = build_embedder(settings)
    store = build_store(settings)
    lexical = _build_lexical(settings) if engine == "hybrid" else None
    graph = build_graph_service(settings) if settings.graph_enabled else None
    return IndexingService(
        embedder, store, collection_name(settings, embedder), settings,
        lexical=lexical, graph=graph,
    )


def build_facade(settings: Settings | None = None):
    """Costruisce la facade di retrieval cablata dalla configurazione (REQ-029).

    Punto d'ingresso per i consumatori: importano e usano la facade senza conoscere
    store/embeddings. I corpora extra (`Settings.extra_corpora`, FR-007) diventano la mappa
    corpus→collezione del fan-out della ricerca combinata: il nome è derivato con la stessa
    `collection_name`, quindi con il provider di embeddings corrente.
    """
    from dataclasses import replace

    from sertor_core.services.retrieval import RetrievalFacade

    settings = settings or Settings.load()
    engine = _validated_engine(settings)
    embedder = build_embedder(settings)
    store = build_store(settings)
    extra = {
        corpus: collection_name(replace(settings, corpus=corpus), embedder)
        for corpus in settings.extra_corpora
    }
    retriever = None
    if engine == "hybrid":
        # Strategia iniettata (FR-017/018): stesso embedder/store della facade, mai istanze
        # duplicate. Il fan-out multi-collezione resta dense-only (research D6).
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
    )


def build_baseline_engine(settings: Settings | None = None):
    """Costruisce il motore RAG vettoriale baseline cablato dalla configurazione (REQ-012)."""
    from sertor_core.engines.baseline import BaselineEngine

    settings = settings or Settings.load()
    embedder = build_embedder(settings)
    store = build_store(settings)
    return BaselineEngine(embedder, store, collection_name(settings, embedder), settings)


def build_engine(settings: Settings | None = None):
    """Costruisce il motore RAG selezionato da `Settings.engine` (FEAT-004, REQ-030/031).

    UNICO punto di scelta del motore (Principio I): `baseline` → `BaselineEngine` (identico a
    oggi), `hybrid` (default) → `HybridEngine`; valore sconosciuto → `ConfigError`.
    """
    settings = settings or Settings.load()
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
