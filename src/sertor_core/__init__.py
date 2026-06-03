"""sertor-core — nucleo di retrieval condiviso (FEAT-001).

API pubblica per i consumatori (motori RAG, skill wiki, layer CLI): la facade di retrieval e
l'orchestratore di indicizzazione si costruiscono dalla configurazione centralizzata tramite il
composition root, senza conoscere i dettagli di store/embeddings.
"""
from __future__ import annotations

from sertor_core.composition import (
    build_baseline_engine,
    build_embedder,
    build_facade,
    build_indexer,
    build_llm,
    build_store,
    collection_name,
)
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import (
    Chunk,
    ChunkMetadata,
    DocType,
    Document,
    EmbeddedChunk,
    IndexReport,
    RetrievalResult,
)
from sertor_core.domain.errors import (
    ConfigError,
    EmbeddingError,
    IndexNotFoundError,
    IngestionError,
    LLMNotConfiguredError,
    SertorError,
    VectorStoreError,
)
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.engines.evaluation import EvalReport, evaluate

__all__ = [
    "build_facade",
    "build_indexer",
    "build_baseline_engine",
    "build_llm",
    "build_embedder",
    "build_store",
    "collection_name",
    "Settings",
    "Document",
    "DocType",
    "Chunk",
    "ChunkMetadata",
    "EmbeddedChunk",
    "RetrievalResult",
    "IndexReport",
    "SertorError",
    "ConfigError",
    "IngestionError",
    "EmbeddingError",
    "VectorStoreError",
    "IndexNotFoundError",
    "LLMNotConfiguredError",
    "BaselineEngine",
    "evaluate",
    "EvalReport",
]
