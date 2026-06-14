"""Test of the composition root — decoupling vector store ↔ embedding provider (Principio II/VIII).

The vector store (`store_backend`) is chosen independently from the embedding provider
(`backend`): Azure embeddings can be combined with a local Chroma store. Collection naming
applies Azure Search constraints **only** when the store is Azure.
"""
from __future__ import annotations

from pathlib import Path

import pytest

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


def test_memory_archiver_none_when_disabled(monkeypatch, tmp_path):
    # 031 (FR-002, D8): memory off → build_memory_archiver returns None.
    monkeypatch.delenv("SERTOR_MEMORY", raising=False)
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    from sertor_core.composition import build_memory_archiver
    assert build_memory_archiver(settings) is None


def test_memory_archiver_built_when_enabled(monkeypatch, tmp_path):
    # 031: memory on → a wired MemoryArchiveService (claude-code adapter, pointed at a tmp dir).
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.setenv("SERTOR_MEMORY_CLAUDE_PROJECTS_DIR", str(tmp_path / "projects"))
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    from sertor_core.composition import build_memory_archiver
    from sertor_core.services.memory_archive import MemoryArchiveService
    archiver = build_memory_archiver(settings)
    assert isinstance(archiver, MemoryArchiveService)


def test_memory_unknown_adapter_raises_configerror(monkeypatch, tmp_path):
    # 031 (FR-005): an unknown memory adapter → ConfigError listing the allowed values.
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.setenv("SERTOR_MEMORY_ADAPTER", "bogus")
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    from sertor_core.composition import build_memory_archiver
    from sertor_core.domain.errors import ConfigError
    with pytest.raises(ConfigError) as exc:
        build_memory_archiver(settings)
    assert "claude-code" in str(exc.value)


def test_composition_does_not_import_claude_code_at_module_level():
    # 031 (FR-002): the host-specific adapter is imported lazily inside the build_* function,
    # never at composition import time (zero overhead at flag off).
    import sertor_core.composition as comp
    source = Path(comp.__file__).read_text(encoding="utf-8")
    module_lines = [
        ln for ln in source.splitlines()
        if ln.lstrip().startswith(("from sertor_core.adapters.capture",
                                   "import sertor_core.adapters.capture"))
        and not ln.startswith((" ", "\t"))  # exclude the in-function (indented) lazy import
    ]
    assert module_lines == []  # only the in-function lazy import exists
