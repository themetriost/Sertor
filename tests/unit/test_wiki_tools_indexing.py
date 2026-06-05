"""Test US5 — orchestrazione indicizzazione (FR-010); no-op disabilitato + collezione separata.

Marker `not cloud`: nessun servizio cloud, nessuna rete. L'indexer è un fake che simula il
report del facade esistente (la chiamata agli embeddings è dietro l'adapter, non un giudizio LLM).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from sertor_core.wiki_tools.indexing import index_wiki
from sertor_core.wiki_tools.profile import load_profile

_BASE = """\
profile = "code+doc"
language = "it"
root = "wiki"
index_file = "index.md"
log_file = "log.md"

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"
"""


def _profile(tmp_path: Path, rag_block: str):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_BASE + rag_block, encoding="utf-8")
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)
    (tmp_path / "wiki" / "index.md").write_text("# i\n", "utf-8")
    (tmp_path / "wiki" / "log.md").write_text("# l\n", "utf-8")
    return load_profile(cfg)


@dataclass
class _FakeReport:
    collection: str
    documents: int


class _FakeIndexer:
    """Registra le chiamate per provare la separazione di collezione e la rigenerazione."""

    def __init__(self, collection: str):
        self.collection = collection
        self.calls: list[tuple[Path, bool]] = []

    def index(self, root, rebuild: bool = False):
        self.calls.append((Path(root), rebuild))
        return _FakeReport(collection=self.collection, documents=7)


@pytest.mark.cloud
def test_index_real_facade_marker_placeholder():
    # Segnaposto: il percorso col facade reale richiederebbe embeddings → marcato cloud.
    pytest.skip("percorso con facade reale escluso dalla CI locale")


def test_noop_when_rag_disabled(tmp_path):
    p = _profile(tmp_path, "\n[rag]\nenabled = false\n")
    res = index_wiki(p)
    assert res.schema == "wiki.index/1"
    assert res.collection is None
    assert res.documents == 0
    assert res.regenerated is False


def test_indexes_into_separate_collection(tmp_path):
    p = _profile(tmp_path, '\n[rag]\nenabled = true\ncorpus = "wiki"\n')
    fake = _FakeIndexer(collection="wiki__fake")

    res = index_wiki(p, indexer_factory=lambda settings: fake)
    assert res.collection == "wiki__fake"  # collezione separata dalle sorgenti
    assert res.documents == 7
    assert res.regenerated is True
    # Ha indicizzato la radice del wiki, in rebuild (rigenerazione indipendente).
    assert fake.calls == [(p.root_path, True)]


def test_regeneration_is_independent(tmp_path):
    # Rigenerare il wiki invoca l'indexer del solo corpus wiki: le sorgenti non sono toccate qui.
    p = _profile(tmp_path, '\n[rag]\nenabled = true\ncorpus = "wiki"\n')
    seen_corpus = {}

    def factory(settings):
        seen_corpus["corpus"] = settings.corpus
        return _FakeIndexer(collection=f"{settings.corpus}__fake")

    res = index_wiki(p, indexer_factory=factory)
    assert seen_corpus["corpus"] == "wiki"  # corpus override dalla config rag
    assert res.collection == "wiki__fake"
