"""Test del composition root — disaccoppiamento store ↔ provider di embeddings (Principio II/VIII).

Lo store del vettore (`store_backend`) è scelto indipendentemente dal provider di embeddings
(`backend`): si possono combinare embeddings Azure con store Chroma locale. Il naming della
collezione applica i vincoli di Azure Search **solo** quando lo store è Azure.
"""
from __future__ import annotations

from sertor_core.adapters.embeddings.azure import AzureEmbedder
from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.composition import build_embedder, build_store, collection_name
from sertor_core.config.settings import Settings
from tests.fixtures.mocks import FakeEmbedder


def test_azure_embeddings_with_local_store(monkeypatch):
    # Embeddings su Azure ma store Chroma locale: combinazione del prototipo (decoupling Princ. II).
    monkeypatch.setenv("RAG_BACKEND", "azure")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://x.openai.azure.com/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-large")
    settings = Settings.load(env_file=None)

    assert isinstance(build_embedder(settings), AzureEmbedder)
    assert isinstance(build_store(settings), ChromaStore)   # store locale nonostante backend=azure


def test_build_facade_wires_extra_corpora(monkeypatch):
    # I corpora extra (FR-007) diventano collezioni derivate col provider corrente (feature 010).
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
    assert expected.startswith("wiki__")          # namespaced per (corpus, provider)


def test_build_facade_without_extra_corpora_has_empty_map(monkeypatch):
    monkeypatch.delenv("SERTOR_EXTRA_CORPORA", raising=False)
    monkeypatch.setenv("RAG_BACKEND", "local")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    settings = Settings.load(env_file=None)

    from sertor_core.composition import build_facade

    assert build_facade(settings)._extra_collections == {}


def test_collection_name_keys_on_store_backend():
    emb = FakeEmbedder()  # .name == "fake:8" → sanitizzato "fake_8"

    # Store locale (Chroma): nessun vincolo di naming → preserva il case del corpus.
    local = collection_name(Settings(corpus="Sertor", store_backend="local"), emb)
    assert local == "Sertor__fake_8"

    # Store Azure: vincoli dell'index (minuscolo, niente cifra iniziale) → forzato lowercase.
    azure = collection_name(Settings(corpus="Sertor", store_backend="azure"), emb)
    assert azure == "sertor__fake_8"
