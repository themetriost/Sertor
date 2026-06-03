"""Test US2 — comando `sertor search` (REQ-020..023)."""
from __future__ import annotations

import json

from sertor_cli.cli import main
from sertor_core.domain.entities import EmbeddedChunk
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

COLL = "cli-test"


def _populated_store() -> InMemoryStore:
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    store.upsert(COLL, [
        EmbeddedChunk("a.py#0", emb.embed(["alpha code"])[0],
                      {"text": "alpha code", "path": "a.py", "doc_type": "code"}),
        EmbeddedChunk("b.md#0", emb.embed(["beta doc"])[0],
                      {"text": "beta doc", "path": "b.md", "doc_type": "doc"}),
    ])
    return store


def _patch(monkeypatch, store):
    monkeypatch.setattr("sertor_cli.commands.search_cmd.build_embedder",
                        lambda s: FakeEmbedder(dim=8))
    monkeypatch.setattr("sertor_cli.commands.search_cmd.build_store", lambda s: store)
    monkeypatch.setattr("sertor_cli.commands.search_cmd.collection_name", lambda s, e: COLL)


def test_search_returns_results_text(monkeypatch, capsys):
    _patch(monkeypatch, _populated_store())
    code = main(["search", "alpha"])
    assert code == 0
    out = capsys.readouterr().out
    assert "a.py" in out or "b.md" in out


def test_search_json_output(monkeypatch, capsys):
    _patch(monkeypatch, _populated_store())
    code = main(["search", "alpha", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    expected = {"path", "doc_type", "chunk_id", "score", "preview"}
    assert isinstance(data, list) and expected <= set(data[0])


def test_search_type_filter(monkeypatch, capsys):
    _patch(monkeypatch, _populated_store())
    code = main(["search", "x", "--type", "doc", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert all(r["doc_type"] == "doc" for r in data)


def test_search_output_handles_non_ascii(monkeypatch, capsys):
    # regressione: testo con caratteri non-ASCII (es. `→`, accenti) non deve far crashare l'output
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    store.upsert(COLL, [
        EmbeddedChunk("a.py#0", emb.embed(["x"])[0],
                      {"text": "language -> tipo → unità con àccénti", "path": "a.py",
                       "doc_type": "code"}),
    ])
    _patch(monkeypatch, store)
    assert main(["search", "x"]) == 0
    assert "→" in capsys.readouterr().out


def test_search_missing_index_errors(monkeypatch, capsys):
    _patch(monkeypatch, InMemoryStore())             # store vuoto → collezione assente
    code = main(["search", "x"])
    assert code == 1                                  # errore esplicito (REQ-022)
    assert "indice" in capsys.readouterr().err.lower()
