"""Test 140 — ASP.NET pages end-to-end: index → search → graph, on the fixture corpus (SC-001..006).

Real wiring (composition → IndexingService → Chroma on tmp_path → facade, graph artifact), mock
embedder injected at the factory as in `test_hybrid_end_to_end.py`: no network. The fixture corpus
is a copy of `tests/fixtures/aspnet` (Principio XIII: fixture plane, declared).
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from sertor_core import composition
from sertor_core.config.settings import Settings
from tests.fixtures.mocks import FakeEmbedder

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "aspnet"
PAGES = ("Default.aspx", "Menu.ascx", "Site.master", "Api.asmx", "Handler.ashx",
         "Index.cshtml", "Counter.razor")


@pytest.fixture()
def corpus(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(FIXTURES, root)
    return root


@pytest.fixture()
def settings(tmp_path):
    return Settings(index_dir=tmp_path / ".index", corpus="aspnet-e2e")


@pytest.fixture(autouse=True)
def _fake_embedder(monkeypatch):
    emb = FakeEmbedder(dim=8)
    monkeypatch.setattr(
        composition, "build_embedder",
        lambda _s=None, *, cache=False, allow_download=False: emb,
    )
    return emb


@pytest.fixture()
def indexed(corpus, settings, caplog):
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        report = composition.build_indexer(settings).index(corpus, rebuild=True)
    return report


def test_sc001_every_page_extension_is_in_the_corpus(indexed, settings):
    facade = composition.build_facade(settings)
    found = set()
    for page in PAGES:
        stem = page.split(".")[0]
        found |= {h.path for h in facade.search_code(stem, k=50)}
    assert set(PAGES) <= found


def test_sc002_inline_methods_are_found_at_the_real_line(indexed, settings):
    graph = composition.build_graph_service(settings)
    assert [(h.path, h.line) for h in graph.find_symbol("Secondo")] == [("Default.aspx", 18)]
    assert [(h.path, h.line) for h in graph.find_symbol("IncrementCount")] == [
        ("Counter.razor", 8)
    ]
    loads = {(h.path, h.line) for h in graph.find_symbol("Page_Load")}
    assert loads == {("Default.aspx", 5), ("Admin/Default.aspx", 3)}


def test_sc003_the_page_is_a_caller_of_the_code_behind(indexed, settings):
    graph = composition.build_graph_service(settings)
    assert ("Default.aspx", "Default.Page_Load") in {
        (h.path, h.qualname) for h in graph.who_calls("BindGrid")
    }
    assert "Default.aspx" in {h.path for h in graph.who_calls("FormatTitolo")}


def test_sc004_markup_only_text_is_found_in_the_top_5(indexed, settings):
    hits = composition.build_facade(settings).search_code("OrdiniGrid", k=5)
    assert "Default.aspx" in [h.path for h in hits]


def test_sc005_degraded_pages_are_in_the_corpus_and_reported(indexed, settings, caplog):
    events = [  # emitted while indexing, i.e. in the `indexed` fixture (setup phase)
        r for r in caplog.get_records("setup")
        if getattr(r, "operation", "") == "aspnet_page_degraded"
    ]
    assert sorted((r.path, r.reason) for r in events) == [
        ("Rotta.aspx", "parse_error"),
        ("Vecchia.aspx", "server_language"),
    ]
    facade = composition.build_facade(settings)
    assert "Vecchia.aspx" in {h.path for h in facade.search_code("Pagina legacy in VB", k=10)}
    assert "Rotta.aspx" in {h.path for h in facade.search_code("codice malformato", k=10)}


def test_fr014_incremental_reindex_is_stable_and_touches_only_the_changed_page(
    indexed, corpus, settings
):
    indexer = composition.build_indexer(settings)
    again = indexer.index(corpus)
    assert (again.added, again.updated, again.removed) == (0, 0, 0)

    page = corpus / "Menu.ascx"
    page.write_text(page.read_text(encoding="utf-8") + "<p>Nuova voce</p>\n", encoding="utf-8")
    changed = indexer.index(corpus)
    assert (changed.added, changed.updated, changed.removed) == (0, 1, 0)
