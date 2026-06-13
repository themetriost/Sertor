"""Polish — host-agnosticity: indexing of 2 distinct codebases without code changes (SC-001).

Two different repositories go into two namespaced collections on the same store, without
interference (REQ-019). Offline test with `FakeEmbedder` + `ChromaStore` on temp dir.
"""
from __future__ import annotations

from pathlib import Path

from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.config.settings import Settings
from sertor_core.services.indexing import IndexingService
from tests.fixtures.mocks import FakeEmbedder

S = Settings.load(env_file=None)


def _second_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo2"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "util.py").write_text(
        "def helper():\n    return 42\n", encoding="utf-8"
    )
    (root / "README.md").write_text("# Repo Due\n\nsecondo repository di test\n", encoding="utf-8")
    return root


def test_two_distinct_repos_indexed_without_code_changes(sample_repo, tmp_path):
    store = ChromaStore(persist_dir=tmp_path / "shared-index")

    repo2 = _second_repo(tmp_path)
    IndexingService(FakeEmbedder(dim=8), store, "corpus-uno", S).index(sample_repo)
    IndexingService(FakeEmbedder(dim=8), store, "corpus-due", S).index(repo2)

    assert store.exists("corpus-uno")
    assert store.exists("corpus-due")

    # The two collections are isolated: a query on corpus-due finds only its own paths (REQ-019).
    qvec = FakeEmbedder(dim=8).embed(["helper"])[0]
    hits = store.query("corpus-due", qvec, k=20)
    paths = {h.path for h in hits}
    assert paths  # has results
    assert all(p in {"pkg/util.py", "README.md"} for p in paths)  # no paths from the first repo
