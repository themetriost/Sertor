"""Test of the composition root — decoupling vector store ↔ embedding provider (Principio II/VIII).

The vector store (`store_backend`) is chosen independently from the embedding provider
(`backend`): Azure embeddings can be combined with a local Chroma store. Collection naming
applies Azure Search constraints **only** when the store is Azure.
"""
from __future__ import annotations

from sertor_core.adapters.embeddings.azure import AzureEmbedder
from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.composition import build_embedder, build_store, collection_name
from sertor_core.config.settings import Settings
from tests.fixtures.mocks import FakeEmbedder


def test_azure_embeddings_with_local_store(monkeypatch):
    # Azure embeddings but local Chroma store: prototype combination (decoupling Princ. II).
    monkeypatch.setenv("RAG_BACKEND", "azure")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://x.openai.azure.com/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-large")
    settings = Settings.load(env_file=None)

    assert isinstance(build_embedder(settings), AzureEmbedder)
    assert isinstance(build_store(settings), ChromaStore)   # local store despite backend=azure


def test_build_facade_wires_extra_corpora(monkeypatch):
    # Extra corpora (FR-007) become derived collections with the current provider (feature 010).
    monkeypatch.setenv("RAG_BACKEND", "local")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    monkeypatch.setenv("SERTOR_CORPUS", "sertor")
    monkeypatch.setenv("SERTOR_EXTRA_CORPORA", "wiki")
    settings = Settings.load(env_file=None)

    from dataclasses import replace

    from sertor_core.composition import build_facade

    facade = build_facade(settings)
    expected = collection_name(replace(settings, corpus="wiki"), facade._embedder)
    assert facade._extra_collections == {"wiki": expected}
    assert expected.startswith("wiki__")          # namespaced by (corpus, provider)


def test_build_facade_without_extra_corpora_has_empty_map(monkeypatch):
    monkeypatch.delenv("SERTOR_EXTRA_CORPORA", raising=False)
    monkeypatch.setenv("RAG_BACKEND", "local")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    settings = Settings.load(env_file=None)

    from sertor_core.composition import build_facade

    assert build_facade(settings)._extra_collections == {}


def test_collection_name_keys_on_store_backend():
    emb = FakeEmbedder()  # .name == "fake:8" → sanitized to "fake_8"

    # Local store (Chroma): no naming constraints → preserves corpus case.
    local = collection_name(Settings(corpus="Sertor", store_backend="local"), emb)
    assert local == "Sertor__fake_8"

    # Azure store: index constraints (lowercase, no leading digit) → forced lowercase.
    azure = collection_name(Settings(corpus="Sertor", store_backend="azure"), emb)
    assert azure == "sertor__fake_8"
