"""Smoke test — Tappa 3A: code graph AST (gratis, deterministico, nessun backend)."""
from __future__ import annotations

from conftest import run


def test_definizione_simbolo(need_ast_graph):
    """`def OAuth2PasswordBearer` trova la definizione nel file giusto."""
    r = run(["03-graphrag/graph_query.py", "def", "OAuth2PasswordBearer"])
    assert r.returncode == 0, r.stderr
    assert "oauth2.py" in r.stdout.lower()


def test_callers_httpexception(need_ast_graph):
    """`callers HTTPException` trova molti chiamanti (hub del call-graph)."""
    r = run(["03-graphrag/graph_query.py", "callers", "HTTPException"])
    assert r.returncode == 0, r.stderr
    assert "(nessuno)" not in r.stdout
    # almeno qualche chiamante elencato (righe "   - ...")
    assert r.stdout.count("\n   - ") >= 5


def test_docs_collegati_apirouter(need_ast_graph):
    """`docs APIRouter` collega la classe ai documenti Markdown che la menzionano."""
    r = run(["03-graphrag/graph_query.py", "docs", "APIRouter"])
    assert r.returncode == 0, r.stderr
    assert ".md" in r.stdout
