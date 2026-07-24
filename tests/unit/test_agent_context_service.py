"""Il ramo strutturale reso all'agente (118, FR-020..035).

Il nucleo dei test è **l'assenza tipizzata**. Un blocco vuoto non dice nulla di per sé: può voler
dire «guardato, non c'è» (conclusione legittima) oppure «non ho potuto guardare» (nessuna
le due cose sono indistinguibili, il contratto fa affermare all'agente qualcosa di falso — ed è il
fallimento peggiore che un sistema di retrieval possa produrre.

Offline, porte mockate.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import ContextBundle, DocType, RetrievalResult, SymbolHit
from sertor_core.domain.errors import ConfigError, GraphNotFoundError
from sertor_core.services.agent_context import AgentContextService, mark_corroboration

SYMBOLS = ["CachingEmbedder", "build_indexer"]


def _hit(path: str, qualname: str) -> SymbolHit:
    return SymbolHit(path=path, line=1, kind="class", qualname=qualname, ref=f"{path}#{qualname}")


def _result(path: str, chunk: str | None = None) -> RetrievalResult:
    return RetrievalResult(text="x", path=path, chunk_id=chunk or f"{path}#0",
                           doc_type=DocType.CODE, score=0.5)


class FakeFacade:
    def __init__(self, docs=(), code=()):
        self._docs, self._code = list(docs), list(code)

    def search_combined(self, query, k=None):
        return list(self._docs), list(self._code)


class FakeGraph:
    """Grafo controllabile: si può far fallire `list_symbols` o `get_context` a piacere."""

    def __init__(self, bundle=None, list_error=None, context_error=None, symbols=None):
        self._bundle = bundle or ContextBundle()
        self._list_error = list_error
        self._context_error = context_error
        self._symbols = SYMBOLS if symbols is None else symbols
        self.context_calls: list[str] = []

    def list_symbols(self):
        if self._list_error:
            raise self._list_error
        return list(self._symbols)

    def get_context(self, name):
        self.context_calls.append(name)
        if self._context_error:
            raise self._context_error
        return self._bundle


@pytest.fixture
def settings() -> Settings:
    return replace(Settings.load(), combined_graph_max_symbols=3, combined_match_min_overlap=2)


# --- le tre indisponibilità, distinte -----------------------------------------------------------


@pytest.mark.parametrize(
    "error, expected_reason",
    [
        (GraphNotFoundError("grafo assente", corpus="sertor"), "graph_not_built"),
        (ConfigError("extra mancante", key="graph"), "navigation_library_missing"),
        (ConfigError("artefatto corrotto"), "graph_artifact_unusable"),
    ],
)
def test_the_three_causes_are_distinguished(settings, error, expected_reason):
    """Tre cause con RIMEDI DIVERSI — indicizzare, installare l'extra, re-indicizzare.

    Conflatarle renderebbe il messaggio inutile per chi deve rimediare.
    """
    service = AgentContextService(FakeFacade(), FakeGraph(list_error=error), settings)

    context = service.search("come funziona CachingEmbedder")

    assert context.graph.status == "unavailable"
    assert context.graph.unavailable_reason == expected_reason


def test_unavailable_never_looks_like_an_empty_result(settings):
    """FR-027: un insieme vuoto AFFERMA un'assenza. Se non abbiamo guardato, non possiamo."""
    service = AgentContextService(
        FakeFacade(),
        FakeGraph(list_error=GraphNotFoundError("grafo assente", corpus="sertor")),
        settings,
    )

    context = service.search("come funziona CachingEmbedder")

    assert context.graph.status != "ok"
    assert context.graph.symbols == ()
    assert context.graph.unavailable_reason is not None, "un vuoto senza causa è un vuoto muto"


def test_a_failure_on_one_symbol_does_not_poison_the_flow(settings):
    """Il fallimento parziale è il caso NORMALE: i blocchi hanno stati indipendenti."""
    graph = FakeGraph(context_error=ConfigError("rotto"))
    service = AgentContextService(FakeFacade(), graph, settings)

    context = service.search("come funziona CachingEmbedder")

    assert context.graph.status == "partial"
    assert context.graph.entry_points, "gli ingressi restano: sapevamo cosa cercare"
    assert all(b.status == "unavailable" for s in context.graph.symbols for b in s.blocks)


# --- non tentato: il costo auto-correlato alla rilevanza ---------------------------------------


def test_prose_without_symbols_never_touches_the_graph(settings):
    """Nessun ingresso ⇒ `not_attempted` ⇒ il grafo NON viene interrogato: costo zero."""
    graph = FakeGraph()
    service = AgentContextService(FakeFacade(), graph, settings)

    context = service.search("perche abbiamo preso questa decisione")

    assert context.graph.status == "not_attempted"
    assert context.graph.entry_points == ()
    assert graph.context_calls == [], "il grafo è stato interrogato senza ingressi"


def test_not_attempted_iff_no_entry_points(settings):
    """L'invariante di FR-029, garantita dalla property derivata."""
    service = AgentContextService(FakeFacade(), FakeGraph(), settings)

    empty = service.search("perche abbiamo preso questa decisione").graph
    filled = service.search("come funziona CachingEmbedder").graph

    assert (empty.status == "not_attempted") is (empty.entry_points == ())
    assert (filled.status == "not_attempted") is (filled.entry_points == ())


# --- troncamento --------------------------------------------------------------------------------


def test_truncation_is_declared_with_the_real_total(settings):
    """Mostrarne 2 di 47 senza dirlo fa affermare all'agente che i chiamanti sono due."""
    bundle = ContextBundle(
        definitions=(_hit("a.py", "CachingEmbedder"),),
        callers=(_hit("b.py", "x"), _hit("c.py", "y")),
        totals=(("definitions", 1), ("callers", 47)),
    )
    service = AgentContextService(FakeFacade(), FakeGraph(bundle=bundle), settings)

    symbol = service.search("come funziona CachingEmbedder").graph.symbols[0]

    assert symbol.callers.shown == 2
    assert symbol.callers.total == 47
    assert symbol.callers.truncated


def test_empty_is_a_legitimate_outcome_not_a_failure(settings):
    bundle = ContextBundle(definitions=(_hit("a.py", "CachingEmbedder"),),
                           totals=(("definitions", 1), ("callers", 0)))
    service = AgentContextService(FakeFacade(), FakeGraph(bundle=bundle), settings)

    symbol = service.search("come funziona CachingEmbedder").graph.symbols[0]

    assert symbol.callers.status == "empty"
    assert symbol.callers.reason is None, "un vuoto legittimo non ha una causa di guasto"


# --- corroborazione -----------------------------------------------------------------------------


def test_corroboration_is_marked_and_nothing_is_deduplicated(settings):
    """FR-033: la convergenza di due metodi indipendenti è un SEGNALE, non una ridondanza."""
    bundle = ContextBundle(definitions=(_hit("src/cache.py", "CachingEmbedder"),),
                           totals=(("definitions", 1),))
    facade = FakeFacade(code=[_result("src/cache.py"), _result("src/other.py")])
    service = AgentContextService(facade, FakeGraph(bundle=bundle), settings)

    context = service.search("come funziona CachingEmbedder")

    assert len(context.code) == 2, "nessun risultato è stato rimosso"
    marked = [r for r in context.code if (r.metadata or {}).get("corroborated_by")]
    assert [r.path for r in marked] == ["src/cache.py"]
    assert marked[0].metadata["corroborated_by"] == ["CachingEmbedder"]


def test_no_corroboration_leaves_results_untouched():
    from sertor_core.domain.agent_context import GraphBranch

    docs = (_result("a.md"),)
    out_docs, out_code, branch = mark_corroboration(docs, (), GraphBranch.not_attempted())

    assert out_docs == docs
    assert out_code == ()
