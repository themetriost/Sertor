"""sertor-core — shared retrieval core (FEAT-001).

Public API for consumers (RAG engines, wiki skill, CLI layer): the retrieval facade and the
indexing orchestrator are built from the centralised configuration via the composition root,
without knowing the store/embeddings details.
"""
from __future__ import annotations

from sertor_core.composition import (
    build_baseline_engine,
    build_embedder,
    build_engine,
    build_facade,
    build_graph_service,
    build_indexer,
    build_observability_reports,
    build_observability_store,
    build_store,
    collection_name,
    enable_observability,
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
    SertorError,
    VectorStoreError,
)
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.engines.evaluation import EvalReport, evaluate

__all__ = [
    "build_facade",
    "build_indexer",
    "build_engine",
    "build_baseline_engine",
    "build_graph_service",
    "build_embedder",
    "build_store",
    "build_observability_store",
    "build_observability_reports",
    "enable_observability",
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
    "BaselineEngine",
    "evaluate",
    "EvalReport",
]
