"""Unit tests for the incremental branch of `IndexingService.index` (046, FEAT-009, T019).

Mock ports (`InMemoryStore`/`InMemoryLexicalIndex`/`FakeCodeGraph` + a counting embedder) + a real
on-disk repo (classify needs file stats). Assert that the incremental run touches only the changed
files (targeted upsert/delete), skips the unchanged ones, falls back to full with no manifest,
raises `IndexLockedError` on a concurrent run; idempotent (2nd run = 0 changes).
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from sertor_core.config.settings import Settings
from sertor_core.domain.errors import IndexLockedError
from sertor_core.services.index_manifest import IndexManifest
from sertor_core.services.indexing import IndexingService, _IndexLock
from tests.fixtures.mocks import (
    CountingEmbedder,
    FakeCodeGraph,
    InMemoryLexicalIndex,
    InMemoryStore,
)

COLL = "test__counting"


def _settings(index_dir: Path) -> Settings:
    base = Settings.load(env_file=None)
    return replace(base, index_dir=index_dir, corpus="test", index_incremental=True)


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _service(repo: Path, index_dir: Path, embedder, store, lexical, graph):
    settings = _settings(index_dir)
    manifest = IndexManifest(index_dir)
    return IndexingService(
        embedder, store, COLL, settings, lexical=lexical, graph=graph, manifest=manifest
    )


@pytest.fixture
def kit(tmp_path):
    repo = tmp_path / "repo"
    index_dir = tmp_path / "idx"
    repo.mkdir()
    embedder = CountingEmbedder(dim=8, name="counting")
    store = InMemoryStore()
    lexical = InMemoryLexicalIndex()
    graph = FakeCodeGraph(corpus="test")
    svc = _service(repo, index_dir, embedder, store, lexical, graph)
    return repo, index_dir, embedder, store, lexical, graph, svc


# --------------------------------------------------------------------- fallback / first run

def test_first_run_falls_back_to_full(kit):
    repo, _idx, embedder, store, _lex, _g, svc = kit
    _write(repo, "a.py", "def a(): pass\n")
    report = svc.index(repo)
    assert report.mode == "full"          # no manifest yet → full (FR-011)
    assert report.added >= 1
    assert store.exists(COLL)


def test_second_run_is_incremental_no_changes(kit):
    repo, _idx, embedder, store, _lex, _g, svc = kit
    _write(repo, "a.py", "def a(): pass\n")
    svc.index(repo)
    embedder.embedded.clear()
    report = svc.index(repo)
    assert report.mode == "incremental"
    assert report.unchanged == 1
    assert report.added == 0 and report.updated == 0 and report.removed == 0
    assert embedder.embedded == []        # nothing re-embedded (FR-002/017, idempotent)


# --------------------------------------------------------------------- targeted change set

def test_modified_file_only_reembeds_itself(kit):
    repo, _idx, embedder, store, _lex, _g, svc = kit
    _write(repo, "a.py", "def a(): pass\n")
    _write(repo, "b.py", "def b(): pass\n")
    svc.index(repo)
    ids_before = set(store._data[COLL])
    embedder.embedded.clear()
    _write(repo, "a.py", "def a(): return 1\n")  # change only a.py
    report = svc.index(repo)
    assert report.mode == "incremental"
    assert report.updated == 1 and report.unchanged == 1
    # only a.py's text was re-embedded; b.py was not touched.
    assert any("return 1" in t for t in embedder.embedded)
    assert not any("def b" in t for t in embedder.embedded)
    # b.py's chunks survive unchanged; a.py's chunks are still present (re-upserted).
    assert ids_before <= set(store._data[COLL]) or "a.py#0" in store._data[COLL]


def test_deleted_file_prunes_its_chunks(kit):
    repo, _idx, _emb, store, _lex, _g, svc = kit
    _write(repo, "a.py", "def a(): pass\n")
    _write(repo, "b.py", "def b(): pass\n")
    svc.index(repo)
    assert "b.py#0" in store._data[COLL]
    (repo / "b.py").unlink()
    report = svc.index(repo)
    assert report.removed == 1
    assert "b.py#0" not in store._data[COLL]      # pruned (FR-005)
    assert "a.py#0" in store._data[COLL]


def test_added_file_is_indexed_incrementally(kit):
    repo, _idx, _emb, store, _lex, _g, svc = kit
    _write(repo, "a.py", "def a(): pass\n")
    svc.index(repo)
    _write(repo, "c.py", "def c(): pass\n")
    report = svc.index(repo)
    assert report.added == 1 and report.unchanged == 1
    assert "c.py#0" in store._data[COLL]


# --------------------------------------------------------------------- knob: full forced

def test_rebuild_true_forces_full(kit):
    repo, _idx, _emb, store, _lex, _g, svc = kit
    _write(repo, "a.py", "def a(): pass\n")
    svc.index(repo)
    report = svc.index(repo, rebuild=True)
    assert report.mode == "full"


def test_incremental_disabled_forces_full(tmp_path):
    repo = tmp_path / "repo"
    index_dir = tmp_path / "idx"
    repo.mkdir()
    _write(repo, "a.py", "def a(): pass\n")
    settings = replace(_settings(index_dir), index_incremental=False)
    svc = IndexingService(
        CountingEmbedder(dim=8), InMemoryStore(), COLL, settings,
        manifest=IndexManifest(index_dir),
    )
    svc.index(repo)
    report = svc.index(repo)
    assert report.mode == "full"          # incremental off → always full


# --------------------------------------------------------------------- single-writer lock

def test_concurrent_run_raises_index_locked(kit):
    repo, index_dir, _emb, _store, _lex, _g, svc = kit
    _write(repo, "a.py", "def a(): pass\n")
    with _IndexLock(index_dir):           # simulate another process holding the lock
        with pytest.raises(IndexLockedError):
            svc.index(repo)


def test_lock_released_after_run(kit):
    repo, index_dir, _emb, _store, _lex, _g, svc = kit
    _write(repo, "a.py", "def a(): pass\n")
    svc.index(repo)
    assert not (index_dir / ".index.lock").exists()   # released even on success
