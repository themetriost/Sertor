"""Test del retrieval su collezioni separate (FEAT-010, US4).

Indicizza SOLO il wiki generato in una collezione dedicata; `manual_edited/` e `ingested_sources/`
NON sono indicizzati. Verifica anche che wiki e codice vivano in collezioni distinte (query
congiunta = due collezioni interrogabili). Solo InMemoryStore + FakeEmbedder (nessuna rete).
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from sertor_core.config.settings import Settings
from sertor_core.services.indexing import IndexingService
from sertor_core.wiki import indexing as wiki_indexing
from sertor_core.wiki.conventions import INGESTED_SOURCES_DIR, MANUAL_EDITED_DIR
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore


def _seed_wiki(root: Path) -> None:
    (root / "concepts").mkdir(parents=True, exist_ok=True)
    (root / "concepts" / "gen.md").write_text(
        "---\ntitle: Gen\ntype: concept\ntags: []\n"
        "created: 2026-06-03\nupdated: 2026-06-03\nsources: []\n---\n\n"
        "# Gen\n\nPagina generata indicizzabile.\n",
        encoding="utf-8",
    )
    manual = root / MANUAL_EDITED_DIR
    manual.mkdir(parents=True, exist_ok=True)
    (manual / "human.md").write_text("# Umano\n\nNon deve essere indicizzato.\n", encoding="utf-8")
    ingested = root / INGESTED_SOURCES_DIR
    ingested.mkdir(parents=True, exist_ok=True)
    (ingested / "ext.md").write_text("# Esterno\n\nNon indicizzare.\n", encoding="utf-8")


def test_only_generated_pages_indexed(wiki_sandbox: Path, monkeypatch):
    _seed_wiki(wiki_sandbox)
    store = InMemoryStore()
    embedder = FakeEmbedder(dim=8)
    monkeypatch.setattr(wiki_indexing, "build_embedder", lambda s: embedder)
    monkeypatch.setattr(wiki_indexing, "build_store", lambda s: store)

    settings = replace(Settings(), wiki_collection="wiki")
    report = wiki_indexing.index_wiki_generated(wiki_sandbox, settings)

    # Raccoglie tutti i path indicizzati dalla collezione del wiki.
    indexed = {
        payload.get("path", "")
        for coll in store._data.values()
        for _vec, payload in coll.values()
    }
    assert any("concepts/gen.md" in p for p in indexed)
    assert not any(MANUAL_EDITED_DIR in p for p in indexed)
    assert not any(INGESTED_SOURCES_DIR in p for p in indexed)
    assert report.chunks > 0


def test_wiki_and_code_are_separate_collections(wiki_sandbox: Path, monkeypatch):
    _seed_wiki(wiki_sandbox)
    store = InMemoryStore()
    embedder = FakeEmbedder(dim=8)
    monkeypatch.setattr(wiki_indexing, "build_embedder", lambda s: embedder)
    monkeypatch.setattr(wiki_indexing, "build_store", lambda s: store)

    settings = replace(Settings(), wiki_collection="wiki", code_collection="code")
    wiki_report = wiki_indexing.index_wiki_generated(wiki_sandbox, settings)

    # Indicizza separatamente del codice in una collezione "code" distinta.
    IndexingService(embedder, store, "code__fake_8", settings).index(wiki_sandbox, rebuild=True)

    collections = set(store._data.keys())
    assert wiki_report.collection in collections
    assert "code__fake_8" in collections
    assert wiki_report.collection != "code__fake_8"  # collezioni separate
