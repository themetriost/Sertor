"""Test US6 — centralized configuration (REQ-030/032)."""
from __future__ import annotations

from sertor_core.config.settings import Settings


def test_defaults_are_centralized():
    s = Settings.load(env_file=None)
    assert s.backend == "local"
    assert s.default_k == 5
    assert s.chunk_size == 1600
    assert s.exclude_patterns  # non-empty default, defined only in Settings


def test_all_choices_read_from_env(monkeypatch):
    monkeypatch.setenv("RAG_BACKEND", "azure")
    monkeypatch.setenv("SERTOR_CORPUS", "mio")
    monkeypatch.setenv("CHUNK_SIZE", "800")
    monkeypatch.setenv("CHUNK_OVERLAP", "50")
    monkeypatch.setenv("DEFAULT_K", "9")
    monkeypatch.setenv("EMBED_BATCH_SIZE", "16")
    monkeypatch.setenv("SERTOR_EXCLUDE_PATTERNS", "foo, bar, *.tmp")
    s = Settings.load(env_file=None)
    assert s.backend == "azure"
    assert s.corpus == "mio"
    assert s.chunk_size == 800
    assert s.chunk_overlap == 50
    assert s.default_k == 9
    assert s.embed_batch_size == 16
    assert s.exclude_patterns == ("foo", "bar", "*.tmp")   # configurable override (REQ-002/030)


def test_embed_provider_follows_backend(monkeypatch):
    monkeypatch.setenv("RAG_BACKEND", "local")
    assert Settings.load(env_file=None).embed_provider == "ollama"
    monkeypatch.setenv("RAG_BACKEND", "azure")
    assert Settings.load(env_file=None).embed_provider == "azure"


def test_store_backend_defaults_to_rag_backend(monkeypatch):
    # Backward-compatible: without SERTOR_STORE_BACKEND the store follows the embeddings backend.
    monkeypatch.delenv("SERTOR_STORE_BACKEND", raising=False)
    monkeypatch.setenv("RAG_BACKEND", "azure")
    assert Settings.load(env_file=None).store_backend == "azure"
    monkeypatch.setenv("RAG_BACKEND", "local")
    assert Settings.load(env_file=None).store_backend == "local"


def test_store_backend_decouples_from_embeddings(monkeypatch):
    # Azure embeddings + local store: combination enabled by SERTOR_STORE_BACKEND (Princ. II).
    monkeypatch.setenv("RAG_BACKEND", "azure")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    s = Settings.load(env_file=None)
    assert s.embed_provider == "azure"   # embeddings provider unchanged
    assert s.store_backend == "local"    # store decoupled from the embeddings backend


def test_extra_corpora_default_empty(monkeypatch):
    # Without SERTOR_EXTRA_CORPORA the combined search stays on a single collection (FR-006).
    monkeypatch.delenv("SERTOR_EXTRA_CORPORA", raising=False)
    assert Settings.load(env_file=None).extra_corpora == ()


def test_extra_corpora_csv_with_spaces(monkeypatch):
    # CSV with spaces and empty entries filtered out (FR-007, reuses _split_env).
    monkeypatch.setenv("SERTOR_EXTRA_CORPORA", " wiki , docs ,, ")
    assert Settings.load(env_file=None).extra_corpora == ("wiki", "docs")


def test_engine_knobs_defaults(monkeypatch):
    # Hybrid engine knobs (FEAT-004): defaults ONLY in Settings (NFR-05).
    for var in ("SERTOR_ENGINE", "SERTOR_RRF_C", "SERTOR_RRF_POOL",
                "SERTOR_RERANK", "SERTOR_RERANK_POOL"):
        monkeypatch.delenv(var, raising=False)
    s = Settings.load(env_file=None)
    assert s.engine == "hybrid"        # the best engine is the default (D1/FR-015)
    assert s.rrf_c == 60
    assert s.rrf_pool == 30
    assert s.rerank_enabled is False   # default off (R-3)
    assert s.rerank_pool == 15


def test_engine_knobs_from_env(monkeypatch):
    monkeypatch.setenv("SERTOR_ENGINE", "baseline")
    monkeypatch.setenv("SERTOR_RRF_C", "30")
    monkeypatch.setenv("SERTOR_RRF_POOL", "50")
    monkeypatch.setenv("SERTOR_RERANK", "true")
    monkeypatch.setenv("SERTOR_RERANK_POOL", "20")
    s = Settings.load(env_file=None)
    assert s.engine == "baseline"
    assert s.rrf_c == 30
    assert s.rrf_pool == 50
    assert s.rerank_enabled is True
    assert s.rerank_pool == 20


def test_rerank_bool_parsing(monkeypatch):
    # Lenient parsing: true/1/yes/on → True; anything else → False.
    for raw, expected in (("TRUE", True), ("1", True), ("yes", True), ("on", True),
                          ("false", False), ("0", False), ("nope", False), ("", False)):
        monkeypatch.setenv("SERTOR_RERANK", raw)
        assert Settings.load(env_file=None).rerank_enabled is expected, raw


def test_graph_knobs_defaults(monkeypatch):
    # Code-graph knobs (FEAT-005): defaults ONLY in Settings (Principio VIII).
    for var in ("SERTOR_GRAPH", "SERTOR_GRAPH_AMBIGUITY", "SERTOR_GRAPH_LIMIT_DEFS",
                "SERTOR_GRAPH_LIMIT_RELS", "SERTOR_GRAPH_LIMIT_DOCS"):
        monkeypatch.delenv(var, raising=False)
    s = Settings.load(env_file=None)
    assert s.graph_enabled is True        # build integrated into index() by default (DA-2)
    assert s.graph_ambiguity_threshold == 2
    assert (s.graph_limit_definitions, s.graph_limit_relations, s.graph_limit_docs) == (10, 8, 8)


def test_graph_knobs_from_env(monkeypatch):
    monkeypatch.setenv("SERTOR_GRAPH", "false")
    monkeypatch.setenv("SERTOR_GRAPH_AMBIGUITY", "5")
    monkeypatch.setenv("SERTOR_GRAPH_LIMIT_DEFS", "3")
    monkeypatch.setenv("SERTOR_GRAPH_LIMIT_RELS", "4")
    monkeypatch.setenv("SERTOR_GRAPH_LIMIT_DOCS", "2")
    s = Settings.load(env_file=None)
    assert s.graph_enabled is False
    assert s.graph_ambiguity_threshold == 5
    assert (s.graph_limit_definitions, s.graph_limit_relations, s.graph_limit_docs) == (3, 4, 2)


def test_secrets_are_read_from_env_only(monkeypatch):
    # Secrets come from env; Settings does not write them anywhere (REQ-032).
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "super-secret")
    s = Settings.load(env_file=None)
    assert s.azure_openai_api_key == "super-secret"
