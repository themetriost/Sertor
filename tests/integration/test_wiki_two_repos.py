"""Polish — repo-agnosticità della skill su 2 wiki distinti (SC-005)."""
from __future__ import annotations

from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.config.settings import Settings
from sertor_core.services.indexing import IndexingService
from sertor_core.wiki.conventions import Brief
from sertor_core.wiki.operations import record
from sertor_core.wiki.structure import create_wiki
from tests.fixtures.mocks import FakeEmbedder

S = Settings.load(env_file=None)
T = "2026-06-03"


def test_skill_works_on_two_distinct_wikis(tmp_path):
    store = ChromaStore(persist_dir=tmp_path / "idx")
    for name in ("alpha", "beta"):
        root = tmp_path / name / "wiki"
        create_wiki(root, today=T)                       # stessa skill, repo diversi
        record(root, Brief(f"Pagina {name}", "concept", f"corpo {name}"), today=T)
        svc = IndexingService(FakeEmbedder(dim=8), store, f"wiki-{name}", S)
        report = svc.index(root, rebuild=True)
        assert report.documents >= 1
        assert store.exists(f"wiki-{name}")
