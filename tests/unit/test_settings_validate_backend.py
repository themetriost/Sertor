"""Test FEAT-011 — estensioni additive a Settings: validate_backend() e preview_chars (D3/D5).

Validazione **statica** dei parametri di backend (FR-015) e nuovo default centralizzato per
l'anteprima dei risultati CLI. Tutto senza rete (NFR-02).
"""
from __future__ import annotations

from dataclasses import replace

from sertor_core.config.settings import Settings


def _base(env, **over):
    """Settings caricate da un env controllato (mai dal .env del repo)."""
    for k in list(env):
        env.delenv(k, raising=False)
    return replace(Settings.load(env_file=None), **over)


# ----------------------------------------------------------------- validate_backend
def test_validate_backend_local_returns_empty():
    s = Settings(backend="local", store_backend="local")
    assert s.validate_backend() == []


def test_validate_backend_azure_embeddings_missing_endpoint():
    s = Settings(backend="azure", store_backend="local")
    missing = s.validate_backend()
    assert "AZURE_OPENAI_ENDPOINT" in missing
    assert "AZURE_OPENAI_API_KEY" in missing
    assert "AZURE_OPENAI_EMBED_DEPLOYMENT" in missing


def test_validate_backend_azure_store_missing_key():
    s = Settings(backend="local", store_backend="azure")
    missing = s.validate_backend()
    assert "AZURE_SEARCH_ENDPOINT" in missing
    assert "AZURE_SEARCH_API_KEY" in missing
    # lo store azure non richiede i campi degli embeddings azure
    assert "AZURE_OPENAI_ENDPOINT" not in missing


def test_validate_backend_azure_complete_returns_empty():
    s = Settings(
        backend="azure",
        store_backend="azure",
        azure_openai_endpoint="https://x",
        azure_openai_api_key="k",
        azure_openai_embed_deployment="d",
        azure_search_endpoint="https://s",
        azure_search_api_key="sk",
    )
    assert s.validate_backend() == []


# ----------------------------------------------------------------- preview_chars
def test_preview_chars_default_is_240():
    assert Settings().preview_chars == 240


def test_preview_chars_override_via_env(monkeypatch):
    monkeypatch.setenv("SERTOR_PREVIEW_CHARS", "80")
    s = Settings.load(env_file=None)
    assert s.preview_chars == 80
