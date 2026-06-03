"""Polish — modalità local-only: nessun componente o chiamata cloud (SC-006, REQ-014/016/022).

Con `RAG_BACKEND=local` il composition root istanzia solo componenti locali (Ollama + Chroma);
nessun adapter cloud viene creato. La garanzia a livello di rete (0 chiamate cloud durante embed)
è verificata nei contract test degli embeddings (`test_local_only_contacts_only_local_host`).
"""
from __future__ import annotations

from sertor_core.adapters.embeddings.ollama import OllamaEmbedder
from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.composition import build_embedder, build_store
from sertor_core.config.settings import Settings


def test_local_backend_builds_only_local_components(monkeypatch):
    monkeypatch.setenv("RAG_BACKEND", "local")
    settings = Settings.load(env_file=None)

    embedder = build_embedder(settings)
    assert isinstance(embedder, OllamaEmbedder)
    assert embedder.name.startswith("ollama:")

    store = build_store(settings)
    assert isinstance(store, ChromaStore)        # backend locale, nessun client cloud


def test_local_embedder_targets_local_host(monkeypatch):
    monkeypatch.setenv("RAG_BACKEND", "local")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    embedder = build_embedder(Settings.load(env_file=None))
    assert "localhost" in embedder._host       # nessun endpoint cloud (REQ-016)


def test_store_backend_decoupled_from_embeddings(monkeypatch, tmp_path):
    # embeddings su Azure ma store locale (Chroma) = combinazione del prototipo
    monkeypatch.setenv("RAG_BACKEND", "azure")
    monkeypatch.setenv("SERTOR_INDEX_DIR", str(tmp_path / "idx"))
    # store_backend non impostato → default 'local'
    settings = Settings.load(env_file=None)
    assert settings.backend == "azure" and settings.store_backend == "local"
    store = build_store(settings)
    assert isinstance(store, ChromaStore)        # store locale anche con embeddings Azure
