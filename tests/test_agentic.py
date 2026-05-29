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
    # provider esplicito ollama: il test resta gratuito anche con RAG_BACKEND=azure
    hits = retrieval.search_code("OAuth2 password bearer", k=3, provider="ollama")
    assert hits and all(h["source"] == "code" for h in hits)


def test_search_docs_filtra_doc(need_chroma, need_ollama):
    from shared import retrieval
    hits = retrieval.search_docs("how to declare a dependency", k=3, provider="ollama")
    assert hits and all(h["source"] == "doc" for h in hits)


def test_autogen_adapter_costruibile():
    """L'adattatore AutoGen importa, espone i 6 tool documentati e costruisce il client locale."""
    import pytest
    pytest.importorskip("autogen_agentchat")
    spec = importlib.util.spec_from_file_location("agentic_autogen", ROOT / "04-agentic-rag" / "autogen_app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert len(mod._TOOL_FNS) == 6
    assert all(fn.__doc__ for fn in mod._TOOL_FNS), "i tool AutoGen devono avere docstring (diventano lo schema)"
    assert mod._model_client() is not None  # client locale costruibile senza rete


def test_sk_adapter_costruibile():
    """L'adattatore Semantic Kernel importa, espone i 6 tool e costruisce il servizio."""
    import pytest
    pytest.importorskip("semantic_kernel")
    spec = importlib.util.spec_from_file_location("agentic_sk", ROOT / "04-agentic-rag" / "sk_app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from semantic_kernel.functions import kernel_function  # noqa: F401
    kf = [m for m in dir(mod.RagTools) if not m.startswith("_")]
    assert len(kf) == 6, f"attesi 6 kernel function, trovati {kf}"
    assert mod._service() is not None  # servizio costruibile senza rete
