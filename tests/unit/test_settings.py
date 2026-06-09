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


def test_secrets_are_read_from_env_only(monkeypatch):
    # I segreti arrivano da env; Settings non li scrive da nessuna parte (REQ-032).
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "super-secret")
    s = Settings.load(env_file=None)
    assert s.azure_openai_api_key == "super-secret"
