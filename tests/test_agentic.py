"""Smoke test della Tappa 04 (Agentic RAG): facade di retrieval + registry dei tool.

Free: coerenza del registry tool e tool di grafo (gated su artefatto). Gated (Ollama):
i filtri `source=code|doc` della facade. Il loop LLM end-to-end non è in pytest (lento e
dipendente dal modello): si verifica a mano via `04-agentic-rag/agent.py` (vedi DEMOS.md).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_tools():
    spec = importlib.util.spec_from_file_location("agentic_tools", ROOT / "04-agentic-rag" / "tools.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registry_coerente():
    """Ogni schema-tool ha un dispatch e viceversa (nessun tool orfano)."""
    t = _load_tools()
    schema_names = {f["function"]["name"] for f in t.TOOLS}
    assert schema_names == set(t._DISPATCH), "schemi e dispatch devono combaciare 1:1"


def test_call_tool_sconosciuto():
    t = _load_tools()
    assert "sconosciuto" in t.call_tool("non_esiste", {})


def test_graph_tools(need_ast_graph):
    from shared import retrieval
    defs = retrieval.find_symbol("OAuth2PasswordBearer")
    assert any("oauth2.py" in d for d in defs)
    assert isinstance(retrieval.who_calls("HTTPException"), list)


def test_search_code_filtra_codice(need_chroma, need_ollama):
    from shared import retrieval
    hits = retrieval.search_code("OAuth2 password bearer", k=3)
    assert hits and all(h["source"] == "code" for h in hits)


def test_search_docs_filtra_doc(need_chroma, need_ollama):
    from shared import retrieval
    hits = retrieval.search_docs("how to declare a dependency", k=3)
    assert hits and all(h["source"] == "doc" for h in hits)
