"""Test US6 — configurazione centralizzata (REQ-030/032)."""
from __future__ import annotations

from sertor_core.config.settings import Settings


def test_defaults_are_centralized():
    s = Settings.load(env_file=None)
    assert s.backend == "local"
    assert s.default_k == 5
    assert s.chunk_size == 1600
    assert s.exclude_patterns  # default non vuoto, definito solo in Settings


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
    assert s.exclude_patterns == ("foo", "bar", "*.tmp")   # override configurabile (REQ-002/030)


def test_embed_provider_follows_backend(monkeypatch):
    monkeypatch.setenv("RAG_BACKEND", "local")
    assert Settings.load(env_file=None).embed_provider == "ollama"
    monkeypatch.setenv("RAG_BACKEND", "azure")
    assert Settings.load(env_file=None).embed_provider == "azure"


def test_store_backend_defaults_to_rag_backend(monkeypatch):
    # Retro-compatibile: senza SERTOR_STORE_BACKEND lo store segue il backend di embeddings.
    monkeypatch.delenv("SERTOR_STORE_BACKEND", raising=False)
    monkeypatch.setenv("RAG_BACKEND", "azure")
    assert Settings.load(env_file=None).store_backend == "azure"
    monkeypatch.setenv("RAG_BACKEND", "local")
    assert Settings.load(env_file=None).store_backend == "local"


def test_store_backend_decouples_from_embeddings(monkeypatch):
    # Embeddings Azure + store locale: combinazione abilitata da SERTOR_STORE_BACKEND (Princ. II).
    monkeypatch.setenv("RAG_BACKEND", "azure")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    s = Settings.load(env_file=None)
    assert s.embed_provider == "azure"   # provider di embeddings invariato
    assert s.store_backend == "local"    # store disaccoppiato dal backend di embeddings


def test_extra_corpora_default_empty(monkeypatch):
    # Senza SERTOR_EXTRA_CORPORA la ricerca combinata resta a singola collezione (FR-006).
    monkeypatch.delenv("SERTOR_EXTRA_CORPORA", raising=False)
    assert Settings.load(env_file=None).extra_corpora == ()


def test_extra_corpora_csv_with_spaces(monkeypatch):
    # CSV con spazi e voci vuote filtrate (FR-007, riusa _split_env).
    monkeypatch.setenv("SERTOR_EXTRA_CORPORA", " wiki , docs ,, ")
    assert Settings.load(env_file=None).extra_corpora == ("wiki", "docs")


def test_engine_knobs_defaults(monkeypatch):
    # Manopole del motore ibrido (FEAT-004): default SOLO in Settings (NFR-05).
    for var in ("SERTOR_ENGINE", "SERTOR_RRF_C", "SERTOR_RRF_POOL",
                "SERTOR_RERANK", "SERTOR_RERANK_POOL"):
        monkeypatch.delenv(var, raising=False)
    s = Settings.load(env_file=None)
    assert s.engine == "hybrid"        # il motore migliore è il default (D1/FR-015)
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
    # Parsing tollerante: true/1/yes/on → True; altro → False.
    for raw, expected in (("TRUE", True), ("1", True), ("yes", True), ("on", True),
                          ("false", False), ("0", False), ("nope", False), ("", False)):
        monkeypatch.setenv("SERTOR_RERANK", raw)
        assert Settings.load(env_file=None).rerank_enabled is expected, raw


def test_secrets_are_read_from_env_only(monkeypatch):
    # I segreti arrivano da env; Settings non li scrive da nessuna parte (REQ-032).
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "super-secret")
    s = Settings.load(env_file=None)
    assert s.azure_openai_api_key == "super-secret"
