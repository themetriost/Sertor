"""Test US2 — hybrid end-to-end via composition root on a fixture corpus (FR-031, SC-002/007).

Real wiring (composition → IndexingService → Chroma on tmp_path → facade with strategy), mock
embedder injected by monkeypatching the factory (the only place that knows the providers): no net.
The fixture corpus on tmp_path IS the SC-007 verification: a corpus different from sertor, zero
engine adaptations — configuration only.
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
    monkeypatch.setattr(
        composition, "build_embedder",
        lambda _s=None, *, cache=False, allow_download=False: emb,
    )
    return emb


def test_index_then_search_through_facade(corpus, settings):
    report = composition.build_indexer(settings).index(corpus, rebuild=True)
    assert report.chunks > 0
    # Re-indexing with the default hybrid also produces the lexical sidecar (REQ-034 hint).
    sidecar_dir = settings.index_dir / "lexical"
    assert any(sidecar_dir.glob("e2e-demo__*.json"))

    facade = composition.build_facade(settings)
    hits = facade.search_code("collection_name", k=3)
    assert hits and hits[0].path == "app.py"          # exact symbol on top via fusion
    assert facade.search_docs("guida del progetto", k=3)


def test_baseline_explicit_uses_legacy_dense_path(corpus, settings):
    composition.build_indexer(settings).index(corpus, rebuild=True)
    baseline = composition.build_facade(replace(settings, engine="baseline"))
    assert baseline._retriever is None                 # current path, identical to today (FR-031)
    fused = baseline.search_combined("configurazione", k=3)  # 070: FusedResults
    assert isinstance(fused.flatten(), list)           # functional without strategy


def test_facade_stays_tolerant_when_collection_missing(settings):
    facade = composition.build_facade(settings)        # no index() executed
    assert facade.search_code("qualunque") == []       # tolerant policy UNCHANGED (no exceptions)
