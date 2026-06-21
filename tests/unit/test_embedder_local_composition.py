"""Composition tests for the local embedder providers (068, TASK-A06/C02).

Default provider, hash warning, ollama/azure invariance, unknown value, observability events,
RAG_BACKEND residual warning, store orthogonality. All offline, no cloud.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from sertor_core.composition import build_embedder
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError

FIXTURE = Path(__file__).parent.parent / "fixtures" / "glove_mini.txt"


def test_default_provider_builds_glove():
    from sertor_core.adapters.embeddings.glove import GloveEmbedder

    # Settings() default → glove; override path so no download happens (REQ-002/SC-001).
    settings = Settings(glove_path=FIXTURE)
    assert settings.embed_provider == "glove"
    assert isinstance(build_embedder(settings), GloveEmbedder)


def test_hash_provider_warns_nl_limited(caplog):
    from sertor_core.adapters.embeddings.hashing import HashingEmbedder

    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        embedder = build_embedder(Settings(embed_provider="hash"))
    assert isinstance(embedder, HashingEmbedder)
    assert any("embeddings_lexical_only" in r.getMessage() for r in caplog.records)


def test_hash_warning_emitted_once_per_build(caplog):
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        build_embedder(Settings(embed_provider="hash"))
    warnings = [r for r in caplog.records if "embeddings_lexical_only" in r.getMessage()]
    assert len(warnings) == 1


def test_ollama_provider_invariant():
    from sertor_core.adapters.embeddings.ollama import OllamaEmbedder

    embedder = build_embedder(Settings(embed_provider="ollama"))
    assert isinstance(embedder, OllamaEmbedder)


def test_ollama_provider_does_not_import_numpy():
    """Selecting ollama does not import numpy (verified in a clean subprocess — RNF-4/REQ-052)."""
    import subprocess
    import sys

    code = (
        "import sys;"
        "from sertor_core.composition import build_embedder;"
        "from sertor_core.config.settings import Settings;"
        "build_embedder(Settings(embed_provider='ollama'));"
        "print('numpy' in sys.modules)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False"


def test_azure_provider_invariant():
    from sertor_core.adapters.embeddings.azure import AzureEmbedder

    settings = Settings(
        embed_provider="azure",
        azure_openai_endpoint="https://x.openai.azure.com/openai/v1",
        azure_openai_api_key="k",
        azure_openai_embed_deployment="dep",
    )
    assert isinstance(build_embedder(settings), AzureEmbedder)


def test_unknown_provider_raises_configerror():
    with pytest.raises(ConfigError) as exc:
        build_embedder(Settings(embed_provider="bogus"))
    msg = str(exc.value)
    assert "SERTOR_EMBED_PROVIDER" in msg
    for value in ("glove", "hash", "ollama", "azure"):
        assert value in msg


def test_provider_selected_event_local_only(caplog):
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        build_embedder(Settings(glove_path=FIXTURE))
    glove_events = [
        r for r in caplog.records if "embeddings_provider_selected" in r.getMessage()
    ]
    assert glove_events
    assert "provider=glove" in glove_events[0].getMessage()


def test_provider_selected_event_not_for_cloud(caplog):
    settings = Settings(
        embed_provider="azure",
        azure_openai_endpoint="https://x.openai.azure.com/openai/v1",
        azure_openai_api_key="k",
        azure_openai_embed_deployment="dep",
    )
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        build_embedder(settings)
    assert not any(
        "embeddings_provider_selected" in r.getMessage() for r in caplog.records
    )


def test_rag_backend_residual_still_builds_glove(monkeypatch, caplog):
    monkeypatch.setenv("RAG_BACKEND", "azure")
    monkeypatch.setenv("SERTOR_EMBED_PROVIDER", "glove")
    monkeypatch.setenv("SERTOR_GLOVE_PATH", str(FIXTURE))
    from sertor_core.adapters.embeddings.glove import GloveEmbedder

    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        settings = Settings.load(env_file=None)
        embedder = build_embedder(settings)
    assert isinstance(embedder, GloveEmbedder)  # RAG_BACKEND=azure ignored, glove honoured
    assert any("config_rag_backend_ignored" in r.getMessage() for r in caplog.records)


def test_store_orthogonal_to_provider(monkeypatch):
    monkeypatch.setenv("SERTOR_EMBED_PROVIDER", "glove")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "azure")
    settings = Settings.load(env_file=None)
    assert settings.embed_provider == "glove"
    assert settings.store_backend == "azure"
