"""Polish — repo-agnosticità del motore baseline su 2 codebase distinte (SC-001)."""
from __future__ import annotations

from pathlib import Path

from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.config.settings import Settings
from sertor_core.engines.baseline import BaselineEngine
from tests.fixtures.mocks import FakeEmbedder

S = Settings.load(env_file=None)


def _second_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo2"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "util.py").write_text("def helper():\n    return 42\n", encoding="utf-8")
    (root / "README.md").write_text("# Repo Due\n\nsecondo repo\n", encoding="utf-8")
    return root


def test_two_distinct_codebases_indexed_and_isolated(sample_repo, tmp_path):
    store = ChromaStore(persist_dir=tmp_path / "shared")
    e1 = BaselineEngine(FakeEmbedder(dim=8), store, "corpus-uno", S)
    e2 = BaselineEngine(FakeEmbedder(dim=8), store, "corpus-due", S)

    e1.index(sample_repo)               # nessuna modifica al codice tra i due (SC-001)
    e2.index(_second_repo(tmp_path))

    paths2 = {h.path for h in e2.query("helper", k=50)}
    assert paths2                       # ha risultati
    assert all(p in {"pkg/util.py", "README.md"} for p in paths2)  # isolato dal primo corpus
