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


def test_collection_name_keys_on_store_backend():
    emb = FakeEmbedder()  # .name == "fake:8" → sanitizzato "fake_8"

    # Store locale (Chroma): nessun vincolo di naming → preserva il case del corpus.
    local = collection_name(Settings(corpus="Sertor", store_backend="local"), emb)
    assert local == "Sertor__fake_8"

    # Store Azure: vincoli dell'index (minuscolo, niente cifra iniziale) → forzato lowercase.
    azure = collection_name(Settings(corpus="Sertor", store_backend="azure"), emb)
    assert azure == "sertor__fake_8"
