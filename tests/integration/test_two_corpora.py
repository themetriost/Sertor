"""Polish — repo-agnosticità: indicizzazione di 2 codebase distinte senza modifiche (SC-001).

Due repository diversi vanno in due collezioni namespaced sullo stesso store, senza interferenze
(REQ-019). Test offline con `FakeEmbedder` + `ChromaStore` su temp dir.
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

    # Le due collezioni sono isolate: una query su corpus-due trova solo i suoi path (REQ-019).
    qvec = FakeEmbedder(dim=8).embed(["helper"])[0]
    hits = store.query("corpus-due", qvec, k=20)
    paths = {h.path for h in hits}
    assert paths  # ha risultati
    assert all(p in {"pkg/util.py", "README.md"} for p in paths)  # nessun path del primo repo
