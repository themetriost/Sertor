"""Test 140 — code-graph of ASP.NET pages: symbols, calls, module caller (US3), coverage (US5)."""
from __future__ import annotations

from pathlib import Path

from sertor_core.adapters.graph.networkx_graph import NetworkxCodeGraph
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType, Document
from sertor_core.services.chunking.aspnet import PAGE_SENTINEL, RAZOR, WEBFORMS
from sertor_core.services.chunking.dispatch import chunk_document
from sertor_core.services.graph_extraction import COVERAGE, extract_graph
from sertor_core.services.ingestion import discover

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "aspnet"
S = Settings.load(env_file=None)


def _graph(extra: list[Document] | None = None):
    documents = discover(FIXTURES, S) + (extra or [])
    chunks = [c for d in documents for c in chunk_document(d, S)]
    return extract_graph(documents, chunks, ambiguity_threshold=S.graph_ambiguity_threshold)


def _calls(data) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in data.edges if e.type == "calls"}


def _nodes(data) -> dict:
    return {n.id: n for n in data.nodes}


# --- US3: symbols and calls ----------------------------------------------------------------------


def test_inline_methods_are_nodes_with_the_real_line_and_no_sentinel():
    nodes = _nodes(_graph())
    assert nodes["Default.aspx::Default.Page_Load"].line == 5
    assert nodes["Default.aspx::Default.Secondo"].line == 18
    assert nodes["Counter.razor::Counter.IncrementCount"].line == 8
    assert not any(PAGE_SENTINEL in node_id for node_id in nodes)


def test_same_named_pages_are_two_distinct_nodes():
    nodes = _nodes(_graph())
    assert nodes["Default.aspx::Default.Page_Load"].qualname == "Default.Page_Load"
    assert nodes["Admin/Default.aspx::Default.Page_Load"].qualname == "Default.Page_Load"


def test_method_in_the_page_calls_the_code_behind():
    calls = _calls(_graph())
    assert ("Default.aspx::Default.Page_Load", "Default.aspx.cs::Default.BindGrid") in calls
    assert ("Default.aspx::Default.Secondo", "Default.aspx::Default.Helper") in calls


def test_calls_outside_a_method_belong_to_the_page_module():
    calls = _calls(_graph())
    assert ("Default.aspx", "Default.aspx.cs::Default.FormatTitolo") in calls   # <%= %>
    assert ("Default.aspx", "Default.aspx.cs::Default.CaricaRighe") in calls    # <% foreach %>


def test_degraded_pages_produce_no_edges_and_no_symbols():
    data = _graph()
    sources = {source for source, _ in _calls(data)}
    assert not any(s.startswith(("Vecchia.aspx", "Rotta.aspx")) for s in sources)
    nodes = _nodes(data)
    assert nodes["Vecchia.aspx"].kind == "module"
    assert not any(n.startswith(("Vecchia.aspx::", "Rotta.aspx::")) for n in nodes)


def test_a_malformed_expression_does_not_drop_the_other_edges():
    page = Document(
        id="Rotta-espressione.aspx",
        text=(
            '<%@ Page Language="C#" %>\n'
            '<script runat="server">\n    void Avvia() { BindGrid(); }\n</script>\n'
            "<p><%= FormatTitolo( %></p>\n"
        ),
        doc_type=DocType.CODE,
        language=WEBFORMS,
    )
    calls = _calls(_graph([page]))
    assert (
        "Rotta-espressione.aspx::Rotta-espressione.Avvia",
        "Default.aspx.cs::Default.BindGrid",
    ) in calls


def test_existing_languages_get_no_module_caller():
    """FR-015: attributing calls to the module is a page-only rule."""
    module = Document(id="script.py", text="print(len([1]))\n", doc_type=DocType.CODE,
                      language="python")
    data = extract_graph([module], chunk_document(module, S))
    assert not _calls(data)


def test_who_calls_returns_the_page_through_the_adapter(tmp_path):
    graph = NetworkxCodeGraph(tmp_path, "aspnet")
    graph.build("aspnet", _graph())
    callers = {(h.path, h.kind, h.qualname) for h in graph.who_calls("FormatTitolo")}
    assert ("Default.aspx", "module", "Default.aspx") in callers
    defined = graph.find_symbol("IncrementCount")
    assert [(h.path, h.line) for h in defined] == [("Counter.razor", 8)]


# --- US5: coverage -------------------------------------------------------------------------------


def test_page_coverage_is_derived_from_csharp():
    assert COVERAGE[WEBFORMS] == COVERAGE[RAZOR] == COVERAGE["c_sharp"]
    declared = dict(_graph().coverage)
    assert declared[WEBFORMS] == declared["c_sharp"]
    assert declared[RAZOR] == declared["c_sharp"]
