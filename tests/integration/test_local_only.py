"""Polish — local-only mode: no cloud components or cloud calls (SC-006, REQ-014/016/022).

With `SERTOR_EMBED_PROVIDER=ollama` the composition root instantiates only local components
(Ollama + Chroma); no cloud adapter is created. The network-level guarantee (0 cloud calls during
embed) is verified in the embeddings contract tests (`test_local_only_contacts_only_local_host`).
"""
from __future__ import annotations

from sertor_core.adapters.embeddings.ollama import OllamaEmbedder
from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.composition import build_embedder, build_store
from sertor_core.config.settings import Settings


def test_local_backend_builds_only_local_components(monkeypatch):
    monkeypatch.setenv("SERTOR_EMBED_PROVIDER", "ollama")
    settings = Settings.load(env_file=None)

    embedder = build_embedder(settings)
    assert isinstance(embedder, OllamaEmbedder)
    assert embedder.name.startswith("ollama:")

    store = build_store(settings)
    assert isinstance(store, ChromaStore)        # local backend, no cloud client


def test_local_embedder_targets_local_host(monkeypatch):
    monkeypatch.setenv("SERTOR_EMBED_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    embedder = build_embedder(Settings.load(env_file=None))
    assert "localhost" in embedder._host       # no cloud endpoint (REQ-016)
