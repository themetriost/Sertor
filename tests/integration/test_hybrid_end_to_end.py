"""Test US2 — end-to-end ibrido via composition root su un corpus fixture (FR-031, SC-002/007).

Wiring reale (composition → IndexingService → Chroma su tmp_path → facade con strategia), embedder
mock iniettato monkeypatchando la factory (l'unico punto che conosce i provider): nessuna rete.
Il corpus fixture su tmp_path È la verifica SC-007: un corpus diverso da sertor, zero adattamenti
del motore — solo configurazione.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from sertor_core import composition
from sertor_core.config.settings import Settings
from tests.fixtures.mocks import FakeEmbedder

pytestmark = pytest.mark.integration


@pytest.fixture()
def corpus(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text(
        "def collection_name(corpus, provider):\n"
        '    """Nome namespaced della collezione."""\n'
        "    return f'{corpus}__{provider}'\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Demo\n\nGuida del progetto demo: configurazione e avvio.\n", encoding="utf-8"
    )
    return root


@pytest.fixture()
def settings(tmp_path):
    return Settings(index_dir=tmp_path / ".index", corpus="e2e-demo")


@pytest.fixture(autouse=True)
def _fake_embedder(monkeypatch):
    emb = FakeEmbedder(dim=8)
    monkeypatch.setattr(composition, "build_embedder", lambda _s=None: emb)
    return emb


def test_index_then_search_through_facade(corpus, settings):
    report = composition.build_indexer(settings).index(corpus, rebuild=True)
    assert report.chunks > 0
    # Il re-index col default hybrid produce anche il sidecar lessicale (REQ-034 hint).
    sidecar_dir = settings.index_dir / "lexical"
    assert any(sidecar_dir.glob("e2e-demo__*.json"))

    facade = composition.build_facade(settings)
    hits = facade.search_code("collection_name", k=3)
    assert hits and hits[0].path == "app.py"          # simbolo esatto in cima via fusione
    assert facade.search_docs("guida del progetto", k=3)


def test_baseline_explicit_uses_legacy_dense_path(corpus, settings):
    composition.build_indexer(settings).index(corpus, rebuild=True)
    baseline = composition.build_facade(replace(settings, engine="baseline"))
    assert baseline._retriever is None                 # percorso attuale, identico a oggi (FR-031)
    hits = baseline.search_combined("configurazione", k=3)
    assert isinstance(hits, list)                      # funzionante senza strategia


def test_facade_stays_tolerant_when_collection_missing(settings):
    facade = composition.build_facade(settings)        # nessun index() eseguito
    assert facade.search_code("qualunque") == []       # policy tollerante INVARIATA (no eccezioni)
