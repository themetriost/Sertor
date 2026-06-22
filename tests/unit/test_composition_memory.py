"""Two-layer privacy gate for the semantic memory index (072, FEAT-004).

Covers TASK-US1-01 (factory gated + injection), TASK-US2-01 (gate two layers), TASK-US2-02
(distinct knob, default off). Offline: `Settings.load(env_file=None)` + monkeypatched env; the
factory is exercised down to "does it build an instance?" without touching real adapters where the
gate is off (the gate-off paths never construct embedder/store).
"""
from __future__ import annotations

from sertor_core.composition import build_memory_archiver, build_memory_semantic_index
from sertor_core.config.settings import Settings
from sertor_core.services.memory_semantic import MemorySemanticIndex


def _settings(monkeypatch, memory: bool, semantic: bool) -> Settings:
    if memory:
        monkeypatch.setenv("SERTOR_MEMORY", "true")
    else:
        monkeypatch.delenv("SERTOR_MEMORY", raising=False)
    if semantic:
        monkeypatch.setenv("SERTOR_MEMORY_SEMANTIC", "true")
    else:
        monkeypatch.delenv("SERTOR_MEMORY_SEMANTIC", raising=False)
    return Settings.load(env_file=None)


def test_gate_capture_off_semantic_on_returns_none(monkeypatch):
    """REQ-001/002/US2-AC1: SERTOR_MEMORY off → None even with SERTOR_MEMORY_SEMANTIC on."""
    settings = _settings(monkeypatch, memory=False, semantic=True)
    assert build_memory_semantic_index(settings) is None


def test_gate_capture_on_semantic_off_returns_none(monkeypatch):
    """REQ-005/US2-AC1: SERTOR_MEMORY on but SERTOR_MEMORY_SEMANTIC off → None (additive)."""
    settings = _settings(monkeypatch, memory=True, semantic=False)
    assert build_memory_semantic_index(settings) is None


def test_gate_both_on_returns_instance(monkeypatch, tmp_path):
    """US2-AC3: both knobs on → a MemorySemanticIndex instance (provider local/hash, no network)."""
    monkeypatch.setenv("SERTOR_EMBED_PROVIDER", "hash")  # local, no data file/network
    settings = _settings(monkeypatch, memory=True, semantic=True)
    object.__setattr__(settings, "index_dir", tmp_path)
    index = build_memory_semantic_index(settings)
    assert isinstance(index, MemorySemanticIndex)


def test_archiver_without_semantic_index_behaves_like_feat001(monkeypatch, tmp_path):
    """REQ-005/RNF-005: archiver with semantic_index=None → no semantic side-effect."""
    settings = _settings(monkeypatch, memory=True, semantic=False)
    object.__setattr__(settings, "index_dir", tmp_path)
    # build_memory_semantic_index returns None (gate off) → archiver gets no index.
    archiver = build_memory_archiver(settings, semantic_index=build_memory_semantic_index(settings))
    assert archiver is not None
    assert archiver._semantic_index is None


def test_memory_collection_isolated_from_corpus(monkeypatch, tmp_path):
    """REQ-017/SC-009: the memory collection is namespaced apart from the project corpus."""
    monkeypatch.setenv("SERTOR_EMBED_PROVIDER", "hash")
    monkeypatch.setenv("SERTOR_CORPUS", "myproj")
    settings = _settings(monkeypatch, memory=True, semantic=True)
    object.__setattr__(settings, "index_dir", tmp_path)
    index = build_memory_semantic_index(settings)
    assert index is not None
    assert index._collection.startswith("memory__myproj")
    assert "myproj" in index._collection
    # The plain corpus collection name does NOT carry the memory namespace.
    assert not index._collection.startswith("myproj__")


# --- TASK-US2-02: distinct knob, default off ----------------------------------------------------


def test_semantic_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SERTOR_MEMORY_SEMANTIC", raising=False)
    assert Settings.load(env_file=None).memory_semantic_enabled is False


def test_capture_on_does_not_enable_semantic(monkeypatch):
    """US2-AC3/SC-002: turning on capture does NOT turn on embedding."""
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.delenv("SERTOR_MEMORY_SEMANTIC", raising=False)
    s = Settings.load(env_file=None)
    assert s.memory_enabled is True
    assert s.memory_semantic_enabled is False


def test_semantic_limit_default(monkeypatch):
    monkeypatch.delenv("SERTOR_MEMORY_SEMANTIC_LIMIT", raising=False)
    assert Settings.load(env_file=None).memory_semantic_limit == 20


def test_semantic_knobs_are_distinct_fields():
    """No aliasing/derivation: the two fields are independent (data-model §Manopole)."""
    s = Settings(memory_enabled=True, memory_semantic_enabled=False)
    assert s.memory_enabled is True
    assert s.memory_semantic_enabled is False
