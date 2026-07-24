"""La superficie MCP del fan-out strutturale (118, FR-017..021, FR-031).

Due proprietà, di peso diverso:

- **additività** — a interruttore spento la risposta è quella di sempre. È ciò che rende la consegna
  sicura mentre il gate non è ancora stato misurato, e va **asserito**, non assunto;
- **forma** — a interruttore acceso il payload rispetta `contracts/agent-context.md`, incluso il
  requisito NEGATIVO che i flussi di somiglianza NON dichiarino un totale (per una classifica il
  taglio top-k è costitutivo e non finge esaustività).
"""
from __future__ import annotations

import pytest

from sertor_core.domain.agent_context import (
    AgentContext,
    EntryPoint,
    GraphBranch,
    RelationBlock,
    SymbolContext,
)
from sertor_core.domain.entities import DocType, RetrievalResult, SymbolHit
from sertor_mcp import server


def _result(path: str) -> RetrievalResult:
    return RetrievalResult(text="testo", path=path, chunk_id=f"{path}#0",
                           doc_type=DocType.CODE, score=0.42)


def _branch() -> GraphBranch:
    hit = SymbolHit(path="src/cache.py", line=98, kind="class",
                    qualname="CachingEmbedder", ref="src/cache.py#CachingEmbedder")
    symbol = SymbolContext(
        qualname="CachingEmbedder",
        definitions=RelationBlock.of((hit,), total=1),
        callers=RelationBlock.of((hit,), total=47),
        callees=RelationBlock.of((), total=0),
        docs=RelationBlock.unavailable("graph_artifact_unusable"),
    )
    return GraphBranch(
        entry_points=(EntryPoint(symbol="CachingEmbedder", source="symbol_table_match"),),
        symbols=(symbol,),
    )


class _Facade:
    def search_combined(self, query, k=None):
        return [_result("wiki/a.md")], [_result("src/cache.py")]


class _Context:
    def search(self, query, k=None):
        return AgentContext(
            docs=(_result("wiki/a.md"),), code=(_result("src/cache.py"),), graph=_branch()
        )


def _pin_switch(monkeypatch, enabled: bool) -> None:
    """Fissa l'interruttore, che è memoizzato e non va riletto a ogni query."""
    monkeypatch.setattr(server, "_fan_out_enabled", lambda: enabled)


@pytest.fixture
def off(monkeypatch):
    _pin_switch(monkeypatch, False)
    monkeypatch.setattr(server, "_facade", lambda: _Facade())


@pytest.fixture
def on(monkeypatch):
    _pin_switch(monkeypatch, True)
    monkeypatch.setattr(server, "_agent_context", lambda: _Context())


# --- additività (SC-007) -------------------------------------------------------------------------


def test_switch_off_returns_exactly_the_two_existing_flows(off):
    out = server.search_combined("qualunque domanda")

    assert set(out) == {"docs", "code"}, "a interruttore spento la forma non cambia"


def test_switch_off_marks_nothing(off):
    out = server.search_combined("qualunque domanda")

    assert all("corroborated_by" not in item for item in out["code"])


# --- forma a interruttore acceso -----------------------------------------------------------------


def test_switch_on_adds_the_graph_flow(on):
    out = server.search_combined("come funziona CachingEmbedder")

    assert set(out) == {"docs", "code", "graph"}


def test_entry_points_declare_their_provenance(on):
    graph = server.search_combined("come funziona CachingEmbedder")["graph"]

    assert graph["entry_points"] == [
        {"symbol": "CachingEmbedder", "source": "symbol_table_match"}
    ]


def test_status_is_partial_when_a_block_is_not_ok(on):
    graph = server.search_combined("come funziona CachingEmbedder")["graph"]

    assert graph["status"] == "partial"


def test_truncation_is_declared_on_graph_relations(on):
    symbol = server.search_combined("come funziona CachingEmbedder")["graph"]["symbols"][0]

    assert symbol["callers"]["shown"] == 1
    assert symbol["callers"]["total"] == 47


def test_unavailable_block_carries_its_reason(on):
    symbol = server.search_combined("come funziona CachingEmbedder")["graph"]["symbols"][0]

    assert symbol["docs"]["status"] == "unavailable"
    assert symbol["docs"]["reason"] == "graph_artifact_unusable"


def test_empty_block_carries_no_reason(on):
    """`empty` è una conclusione legittima: allegarle una causa la farebbe sembrare un guasto."""
    symbol = server.search_combined("come funziona CachingEmbedder")["graph"]["symbols"][0]

    assert symbol["callees"]["status"] == "empty"
    assert "reason" not in symbol["callees"]


def test_similarity_flows_never_declare_a_total(on):
    """FR-031, requisito NEGATIVO: per una classifica il top-k è costitutivo, non un troncamento.

    Su un corpus intero ogni documento ha una similarità: «totale» non ha senso insiemistico, e
    dichiararlo suggerirebbe un'esaustività che la lista non pretende.
    """
    out = server.search_combined("come funziona CachingEmbedder")

    for flow in ("docs", "code"):
        for item in out[flow]:
            assert "total" not in item
            assert "shown" not in item
