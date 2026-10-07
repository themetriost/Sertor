"""Test FEAT-011 — additive extensions to Settings: validate_backend() and preview_chars (D3/D5).

**Static** validation of backend parameters (FR-015) and new centralized default for
the CLI results preview. All without network access (NFR-02).
"""
from __future__ import annotations

from dataclasses import replace

from sertor_core.config.settings import Settings


def _base(env, **over):
    """Settings loaded from a controlled env (never from the repo .env)."""
    for k in list(env):
        env.delenv(k, raising=False)
    return replace(Settings.load(env_file=None), **over)


# ----------------------------------------------------------------- validate_backend
def test_validate_backend_local_returns_empty():
    s = Settings(embed_provider="glove", store_backend="local")
    assert s.validate_backend() == []


def test_validate_backend_azure_embeddings_missing_endpoint():
    s = Settings(embed_provider="azure", store_backend="local")
    missing = s.validate_backend()
    assert "AZURE_OPENAI_ENDPOINT" in missing
    assert "AZURE_OPENAI_API_KEY" in missing
    assert "AZURE_OPENAI_EMBED_DEPLOYMENT" in missing


def test_validate_backend_azure_store_missing_key():
    s = Settings(embed_provider="glove", store_backend="azure")
    missing = s.validate_backend()
    assert "AZURE_SEARCH_ENDPOINT" in missing
    assert "AZURE_SEARCH_API_KEY" in missing
    # the azure store does not require the azure embeddings fields
    assert "AZURE_OPENAI_ENDPOINT" not in missing


def test_validate_backend_azure_complete_returns_empty():
    s = Settings(
        embed_provider="azure",
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


# ----------------------------------------------------------------- 137: provider openai
def test_validate_backend_openai_missing_key():
    s = Settings(embed_provider="openai", store_backend="local")
    assert s.validate_backend() == ["OPENAI_API_KEY"]


def test_validate_backend_openai_complete():
    s = Settings(embed_provider="openai", store_backend="local", openai_api_key="sk-x")
    assert s.validate_backend() == []


def test_validate_backend_openai_needs_no_azure_embeddings_keys():
    missing = Settings(embed_provider="openai").validate_backend()
    assert not any(k.startswith("AZURE_OPENAI_") for k in missing)


def test_missing_provider_keys_excludes_store_keys():
    s = Settings(embed_provider="openai", store_backend="azure")
    assert s.missing_provider_keys() == ["OPENAI_API_KEY"]
    assert s.validate_backend() == [
        "OPENAI_API_KEY", "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY",
    ]


def test_missing_provider_keys_azure_and_local():
    assert Settings(embed_provider="azure").missing_provider_keys() == [
        "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_EMBED_DEPLOYMENT",
    ]
    for provider in ("glove", "hash", "ollama"):
        settings = Settings(embed_provider=provider, store_backend="azure")
        assert settings.missing_provider_keys() == []
