"""Invarianti del routing per-kind della valutazione (118, FR-014/FR-015/FR-016).

Due proprietà **oggi vere ma finora non protette**, entrambe in `RoutedEvalEngine`:

1. **Instradamento esclusivo** — un caso `symbol` interroga SOLO il code-graph, un caso non-`symbol`
   SOLO il motore di similarità. Se l'instradamento smettesse di essere totale, gli hit di grafo
   (che portano un segnaposto al valore massimo) competerebbero con risultati di similarità nella
   stessa lista e ne domineresero l'ordinamento.
2. **Indipendenza dal segnaposto** — l'esito della valutazione non dipende dal valore di
   `_GRAPH_SCORE_SENTINEL`. È l'invariante che rende il segnaposto *cosmetico*: se un domani una
   metrica leggesse quello score, la valutazione misurerebbe una politica di fusione **che in
   produzione non esiste** — un difetto silenzioso, del tipo peggiore.

Offline, F.I.R.S.T.: doppi di test puri, nessun I/O.

NB: `RoutedEvalEngine.query` passa l'**intera query** a `find_symbol`, quindi le query di prova
DEVONO essere nomi di simbolo, com'è nella suite reale.
"""
from __future__ import annotations

import pytest

from sertor_core.domain.entities import GraphData, RetrievalResult, SymbolHit
from sertor_core.engines.evaluation import evaluate
from sertor_core.services.eval import runner as runner_mod
from sertor_core.services.eval.runner import RoutedEvalEngine

SYMBOL_QUERY = "build_indexer"
PROSE_QUERY = "come funziona la cache degli embeddings"


class ExplodingEngine:
    """Motore di similarità che FALLISCE il test se interrogato."""

    provider = "exploding"

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        pytest.fail(f"similarity engine invoked for a symbol case: {query!r}")


class RecordingEngine:
    """Motore di similarità che registra le query ricevute."""

    provider = "recording"

    def __init__(self, results: list[RetrievalResult] | None = None) -> None:
        self.seen: list[str] = []
        self._results = results or []

    def query(self, query: str, k: int | None = None) -> list[RetrievalResult]:
        self.seen.append(query)
        return list(self._results)


class ExplodingGraph:
    """Code-graph che FALLISCE il test se interrogato."""

    def build(self, corpus: str, data: GraphData) -> None: ...
    def who_calls(self, name: str) -> list[SymbolHit]: ...
    def related_docs(self, name: str) -> list[str]: ...
    def get_context(self, name: str): ...
    def exists(self, corpus: str) -> bool: return True
    def reset(self, corpus: str) -> None: ...
    def list_symbols(self) -> list[str]: return []

    def find_symbol(self, name: str) -> list[SymbolHit]:
        pytest.fail(f"code-graph invoked for a non-symbol case: {name!r}")


class StubGraph:
    """Code-graph che restituisce definizioni note e registra le richieste."""

    def __init__(self, hits: list[SymbolHit]) -> None:
        self.seen: list[str] = []
        self._hits = hits

    def build(self, corpus: str, data: GraphData) -> None: ...
    def who_calls(self, name: str) -> list[SymbolHit]: return []
    def related_docs(self, name: str) -> list[str]: return []
    def get_context(self, name: str): ...
    def exists(self, corpus: str) -> bool: return True
    def reset(self, corpus: str) -> None: ...
    def list_symbols(self) -> list[str]: return [h.qualname for h in self._hits]

    def find_symbol(self, name: str) -> list[SymbolHit]:
        self.seen.append(name)
        return list(self._hits)


def _hit(path: str, qualname: str, line: int = 10) -> SymbolHit:
    return SymbolHit(path=path, line=line, kind="function", qualname=qualname,
                     ref=f"{path}#{qualname}")


def _result(path: str, score: float = 0.5) -> RetrievalResult:
    from sertor_core.domain.entities import DocType

    return RetrievalResult(text="", path=path, chunk_id=f"{path}#0",
                           doc_type=DocType.CODE, score=score)


# --- 1. Instradamento esclusivo (FR-014) ------------------------------------------------------


def test_symbol_case_never_touches_the_similarity_engine():
    """Un caso `symbol` va SOLO al grafo: il motore fallisce il test se invocato."""
    graph = StubGraph([_hit("src/composition.py", "build_indexer")])
    routed = RoutedEvalEngine(ExplodingEngine(), graph, {SYMBOL_QUERY: "symbol"})

    results = routed.query(SYMBOL_QUERY)

    assert [r.path for r in results] == ["src/composition.py"]
    assert graph.seen == [SYMBOL_QUERY]


def test_non_symbol_case_never_touches_the_graph():
    """Un caso non-`symbol` va SOLO al motore: il grafo fallisce il test se invocato."""
    engine = RecordingEngine([_result("wiki/concepts/retrieval-core.md")])
    routed = RoutedEvalEngine(engine, ExplodingGraph(), {PROSE_QUERY: "nl"})

    results = routed.query(PROSE_QUERY)

    assert [r.path for r in results] == ["wiki/concepts/retrieval-core.md"]
    assert engine.seen == [PROSE_QUERY]


def test_query_absent_from_the_kind_map_goes_to_the_similarity_engine():
    """Nessun kind noto → motore di similarità (il grafo resta intatto)."""
    engine = RecordingEngine([_result("a.py")])
    routed = RoutedEvalEngine(engine, ExplodingGraph(), {})

    routed.query("qualunque cosa")

    assert engine.seen == ["qualunque cosa"]


# --- 2. Indipendenza dal segnaposto (FR-015/FR-016) -------------------------------------------


def _run_with_sentinel(monkeypatch: pytest.MonkeyPatch, value: float):
    """Esegue la stessa valutazione con il segnaposto sostituito da `value`."""
    monkeypatch.setattr(runner_mod, "_GRAPH_SCORE_SENTINEL", value)
    graph = StubGraph([
        _hit("src/composition.py", "build_indexer"),
        _hit("src/other.py", "build_indexer"),
    ])
    routed = RoutedEvalEngine(RecordingEngine(), graph, {SYMBOL_QUERY: "symbol"})
    return evaluate(routed, [(SYMBOL_QUERY, ["src/composition.py"])])


def test_evaluation_is_identical_whatever_the_sentinel_value(monkeypatch):
    """FR-015: il report non dipende dal segnaposto — campo per campo.

    Se questo test rompe, una metrica ha iniziato a leggere lo score dei risultati di grafo, e la
    valutazione sta misurando un ordinamento che in produzione non esiste.
    """
    baseline = _run_with_sentinel(monkeypatch, 1.0)
    altered = _run_with_sentinel(monkeypatch, 0.123)

    assert baseline == altered, "l'esito della valutazione dipende dal segnaposto"
    assert baseline.hit_rate == altered.hit_rate
    assert baseline.mrr == altered.mrr
    assert baseline.per_query == altered.per_query


def test_sentinel_extremes_do_not_change_the_outcome(monkeypatch):
    """Anche valori estremi (0.0 e un valore assurdo) lasciano il report invariato."""
    zero = _run_with_sentinel(monkeypatch, 0.0)
    huge = _run_with_sentinel(monkeypatch, 999.0)

    assert zero == huge


def test_graph_results_carry_the_named_sentinel_not_a_literal():
    """Il valore trasportato è la costante nominata.

    Un letterale sparso nel codice sarebbe insensibile al test di indipendenza qui sopra.
    """
    graph = StubGraph([_hit("src/composition.py", "build_indexer")])
    routed = RoutedEvalEngine(RecordingEngine(), graph, {SYMBOL_QUERY: "symbol"})

    results = routed.query(SYMBOL_QUERY)

    assert all(r.score == runner_mod._GRAPH_SCORE_SENTINEL for r in results)
