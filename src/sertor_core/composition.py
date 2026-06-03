"""Composition root del nucleo (Principio I/VIII).

È l'UNICO componente che conosce gli adapter concreti e li cabla a partire dalla configurazione.
I servizi e la facade dipendono solo dalle porte; qui si decide quale implementazione usare in base
a `Settings`. Estendere qui (non nei servizi) per aggiungere provider/backend.
"""
from __future__ import annotations

from sertor_core.config.settings import Settings
from sertor_core.domain.ports import EmbeddingProvider, VectorStore


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
    """Costruisce il backend di vector store selezionato dalla configurazione (REQ-018/030)."""
    settings = settings or Settings.load()
    if settings.backend == "azure":
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
    if settings.backend == "azure":
        # Azure AI Search: gli index hanno vincoli di naming (minuscolo, lettera iniziale).
        base = base.lower().lstrip("0123456789_") or "sertor"
    # Chroma/Azure richiedono nomi di 3+ caratteri: garantisce la lunghezza minima.
    return base if len(base) >= 3 else f"{base}_idx"


def build_indexer(settings: Settings | None = None):
    """Costruisce l'orchestratore di indicizzazione cablato dalla configurazione (REQ-029)."""
    from sertor_core.services.indexing import IndexingService

    settings = settings or Settings.load()
    embedder = build_embedder(settings)
    store = build_store(settings)
    return IndexingService(embedder, store, collection_name(settings, embedder), settings)


def build_facade(settings: Settings | None = None):
    """Costruisce la facade di retrieval cablata dalla configurazione (REQ-029).

    Punto d'ingresso per i consumatori: importano e usano la facade senza conoscere
    store/embeddings.
    """
    from sertor_core.services.retrieval import RetrievalFacade

    settings = settings or Settings.load()
    embedder = build_embedder(settings)
    store = build_store(settings)
    return RetrievalFacade(
        embedder, store, collection_name(settings, embedder), default_k=settings.default_k
    )
