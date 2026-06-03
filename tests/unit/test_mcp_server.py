"""Test del server MCP basato su sertor-core (tool registrati + formato risultati)."""
from __future__ import annotations

import asyncio

import sertor_mcp.server as srv
from sertor_core.domain.entities import EmbeddedChunk
from sertor_core.services.retrieval import RetrievalFacade
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

COLL = "mcp-test"


def _fake_facade(_settings=None):
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    store.upsert(COLL, [
        EmbeddedChunk("a.py#0", emb.embed(["alpha code"])[0],
                      {"text": "alpha → unità con àccénti", "path": "a.py", "doc_type": "code"}),
        EmbeddedChunk("b.md#0", emb.embed(["beta doc"])[0],
                      {"text": "beta doc", "path": "b.md", "doc_type": "doc"}),
    ])
    return RetrievalFacade(FakeEmbedder(dim=8), store, COLL, default_k=5)


def test_three_search_tools_registered():
    tools = asyncio.run(srv.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"search_code", "search_docs", "search_combined"} <= names


def test_tool_returns_formatted_dicts(monkeypatch):
    monkeypatch.setattr(srv, "build_facade", _fake_facade)
    srv._facade.cache_clear()
    try:
        out = srv.search_combined("alpha")
        assert out
        assert set(out[0]) == {"path", "source", "chunk", "score", "preview"}
        assert out[0]["source"] in {"code", "doc"}
    finally:
        srv._facade.cache_clear()


def test_tool_filters_by_type(monkeypatch):
    monkeypatch.setattr(srv, "build_facade", _fake_facade)
    srv._facade.cache_clear()
    try:
        assert all(r["source"] == "code" for r in srv.search_code("x"))
        assert all(r["source"] == "doc" for r in srv.search_docs("x"))
    finally:
        srv._facade.cache_clear()
