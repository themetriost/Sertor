"""Unit tests for the incremental delta report + observability event (046, FEAT-009, T020).

The `IndexReport` carries the delta counts (added/updated/removed/unchanged/cache_hits) and `mode`;
the `index` log event surfaces the same fields (FR-015/016). No cloud: mock ports + on-disk repo.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import pytest

from sertor_core.config.settings import Settings
from sertor_core.services.index_manifest import IndexManifest
from sertor_core.services.indexing import IndexingService
from tests.fixtures.mocks import CountingEmbedder, InMemoryStore

COLL = "test__counting"


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).write_text(text, encoding="utf-8")


@pytest.fixture
def svc(tmp_path):
    repo = tmp_path / "repo"
    index_dir = tmp_path / "idx"
    repo.mkdir()
    settings = replace(
        Settings.load(env_file=None), index_dir=index_dir, corpus="test", index_incremental=True
    )
    service = IndexingService(
        CountingEmbedder(dim=8), InMemoryStore(), COLL, settings,
        manifest=IndexManifest(index_dir),
    )
    return service, repo


def test_full_report_marks_everything_added(svc):
    service, repo = svc
    _write(repo, "a.py", "def a(): pass\n")
    _write(repo, "b.py", "def b(): pass\n")
    report = service.index(repo)
    assert report.mode == "full"
    assert report.added == 2
    assert report.updated == 0 and report.removed == 0 and report.unchanged == 0


def test_incremental_report_counts_each_class(svc):
    service, repo = svc
    _write(repo, "a.py", "def a(): pass\n")
    _write(repo, "b.py", "def b(): pass\n")
    _write(repo, "c.py", "def c(): pass\n")
    service.index(repo)  # full seed
    _write(repo, "a.py", "def a(): return 1\n")   # modified
    (repo / "b.py").unlink()                       # deleted
    _write(repo, "d.py", "def d(): pass\n")        # added
    report = service.index(repo)
    assert report.mode == "incremental"
    assert report.added == 1       # d.py
    assert report.updated == 1     # a.py
    assert report.removed == 1     # b.py
    assert report.unchanged == 1   # c.py


def test_incremental_event_is_observable(svc, caplog):
    service, repo = svc
    _write(repo, "a.py", "def a(): pass\n")
    service.index(repo)  # full seed
    _write(repo, "a.py", "def a(): return 2\n")
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        service.index(repo)
    index_lines = [
        r.getMessage() for r in caplog.records if getattr(r, "operation", None) == "index"
    ]
    assert index_lines, "the index event must be emitted (FR-016)"
    last = index_lines[-1]
    assert "mode=incremental" in last
    assert "updated=1" in last
    assert "unchanged=0" in last
