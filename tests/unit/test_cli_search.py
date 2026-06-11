"""Test US2 — CLI `sertor-rag search <query>` (FR-009..013, FR-015, SC-002).

Indice mock precostruito (`InMemoryStore` + `FakeEmbedder`) condiviso fra `BaselineEngine` (via
strict) e `RetrievalFacade` (filtri di tipo): nessuna rete (NFR-02).
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import EmbeddedChunk
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.services.retrieval import RetrievalFacade
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

COLL = "default__fake_8"


def _payload(text, path, doc_type):
    return {"text": text, "path": path, "doc_type": doc_type, "metadata": {"path": path}}


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    """Isola dal `.env` del repo (load_dotenv override muterebbe os.environ in modo persistente)."""
    _orig = Settings.load.__func__
    monkeypatch.setattr(
        Settings, "load", classmethod(lambda c, env_file=".env": _orig(c, env_file=None))
    )


@pytest.fixture
def populated(monkeypatch):
    """Indice in memoria popolato con hit code e doc; cabla CLI su engine/facade mock."""
    embedder = FakeEmbedder(dim=8)
    store = InMemoryStore()
    records = []
    for i, (text, path, dt) in enumerate(
        [
            ("def build_indexer(): pass", "src/composition.py", "code"),
            ("class RetrievalFacade: ...", "src/retrieval.py", "code"),
            ("L'hybrid search combina BM25 e dense. " * 20, "wiki/hybrid.md", "doc"),
            ("La composition root cabla gli adapter dal config.", "wiki/composition.md", "doc"),
        ]
    ):
        vec = embedder.embed([text])[0]
        records.append(
            EmbeddedChunk(chunk_id=f"{path}#{i}", vector=vec, payload=_payload(text, path, dt))
        )
    store.upsert(COLL, records)

    settings = Settings(corpus="default", default_k=5, preview_chars=240)

    def _engine(s):
        return BaselineEngine(embedder, store, COLL, s)

    def _facade(s):
        return RetrievalFacade(embedder, store, COLL, default_k=s.default_k)

    monkeypatch.setattr(cli, "build_baseline_engine", _engine)
    monkeypatch.setattr(cli, "build_facade", _facade)
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, env_file=".env": settings))
    return store, settings


def _run(argv):
    return cli.main(argv)


# --------------------------------------------------------------------- successo both
def test_search_both_human_output(populated, capsys):
    code = _run(["search", "composition"])
    out = capsys.readouterr().out
    assert code == 0
    assert "score=" in out
    assert "path=" in out
    assert "doc=" in out
    assert "chunk=" in out


def test_search_json_output_fields(populated, capsys):
    code = _run(["search", "composition", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    arr = json.loads(out)
    assert isinstance(arr, list) and arr
    for hit in arr:
        assert {"path", "doc_type", "chunk_id", "score", "preview"} <= hit.keys()


def test_search_full_returns_text_field(populated, capsys):
    code = _run(["search", "hybrid", "--json", "--full"])
    out = capsys.readouterr().out
    assert code == 0
    arr = json.loads(out)
    assert all("text" in h and "preview" not in h for h in arr)
    # nessuna ellissi nel testo integrale
    assert all("…" not in h["text"] for h in arr)


def test_search_truncates_preview(populated, capsys):
    code = _run(["search", "hybrid", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    arr = json.loads(out)
    # l'hit lungo deve risultare troncato con ellissi
    assert any(h["preview"].endswith("…") for h in arr)


# --------------------------------------------------------------------- -k e --type
def test_search_k_limits_results(populated, capsys):
    code = _run(["search", "composition", "-k", "2", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert len(json.loads(out)) <= 2


def test_search_type_code_only(populated, capsys):
    code = _run(["search", "composition", "--type", "code", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    arr = json.loads(out)
    assert arr and all(h["doc_type"] == "code" for h in arr)


def test_search_type_doc_only(populated, capsys):
    code = _run(["search", "composition", "--type", "doc", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    arr = json.loads(out)
    assert arr and all(h["doc_type"] == "doc" for h in arr)


# --------------------------------------------------------------------- indice assente (FR-012/D6)
@pytest.mark.parametrize("dtype", ["both", "code", "doc"])
def test_search_missing_index_exit_1(monkeypatch, capsys, dtype):
    embedder = FakeEmbedder(dim=8)
    store = InMemoryStore()  # vuoto
    settings = Settings(corpus="default", default_k=5)
    monkeypatch.setattr(cli, "build_baseline_engine",
                        lambda s: BaselineEngine(embedder, store, "vuota", s))
    monkeypatch.setattr(cli, "build_facade",
                        lambda s: RetrievalFacade(embedder, store, "vuota", default_k=5))
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, env_file=".env": settings))
    code = _run(["search", "x", "--type", dtype])
    err = capsys.readouterr().err
    assert code == 1
    assert "errore:" in err
    assert "inesistente" in err


# --------------------------------------------------------------------- query vuota (edge case)
def test_search_empty_query_exit_1(populated, capsys):
    code = _run(["search", "   "])
    err = capsys.readouterr().err
    assert code == 1
    assert "errore:" in err


# ------------------------------------------------------------- --corpus override (FR-009/D7)
def test_search_corpus_override_reaches_composition(monkeypatch, capsys):
    seen = {}

    class _Eng:
        def ensure_index(self):
            pass

        def query(self, q, k=None):
            return []

    def _engine(s):
        seen["corpus"] = s.corpus
        return _Eng()

    monkeypatch.setattr(cli, "build_baseline_engine", _engine)
    monkeypatch.setattr(
        cli, "build_facade",
        lambda s: RetrievalFacade(FakeEmbedder(dim=8), InMemoryStore(), "c", default_k=5),
    )
    monkeypatch.setattr(cli.Settings, "load",
                        classmethod(lambda c, env_file=".env": Settings(corpus="default")))
    _run(["search", "q", "--corpus", "altro"])
    capsys.readouterr()
    assert seen["corpus"] == "altro"
