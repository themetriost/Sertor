"""T018 — adapter SertorRagLocator con runner finto: mapping, dedup multi-search, fail-loud."""

from __future__ import annotations

import json

import pytest

from speclift.adapters.rag_sertor import SertorRagLocator
from speclift.config import Config
from speclift.domain.errors import RagUnavailableError
from speclift.domain.models import Symbol


class FakeRunner:
    """Simula `sertor-rag search --json`: ritorna risultati per query, registra le chiamate."""

    def __init__(self, by_query: dict[str, list[dict]] | None = None, *, fail: bool = False) -> None:
        self.by_query = by_query or {}
        self.fail = fail
        self.queries: list[str] = []

    def __call__(self, args: list[str]) -> str:
        # args: ["search", <query>, "--type", "code", "--json", "-k", N]
        query = args[1]
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("backend unreachable")
        return json.dumps(self.by_query.get(query, []))


def _hit(path: str, chunk: int = 1) -> dict:
    return {"path": path, "doc_type": "code", "chunk_id": f"{path}#{chunk}", "score": 0.5}


def test_locate_symbols_maps_results():
    runner = FakeRunner({"multiply": [_hit("calc.py"), _hit("other.py")]})
    loc = SertorRagLocator(runner=runner)
    syms = loc.locate_symbols("calc.py", ["multiply"], "def multiply(a, b):")
    names = {(s.name, s.path) for s in syms}
    assert ("multiply", "calc.py") in names
    assert ("multiply", "other.py") in names  # evidenza cross-layer mantenuta


def test_query_cap_respected():
    runner = FakeRunner({})
    loc = SertorRagLocator(runner=runner, config=Config(max_queries_per_symbol=2))
    loc.locate_symbols("calc.py", ["a", "b", "c", "d", "e"], "snippet")
    assert len(runner.queries) <= 2


def test_locate_symbols_dedups_same_hit():
    runner = FakeRunner({"multiply": [_hit("calc.py", 1), _hit("calc.py", 1)]})
    loc = SertorRagLocator(runner=runner)
    syms = loc.locate_symbols("calc.py", ["multiply"], "")
    assert len([s for s in syms if s.path == "calc.py"]) == 1


def test_locate_tests_filters_test_paths():
    runner = FakeRunner(
        {"multiply": [_hit("calc.py"), _hit("test_calc.py"), _hit("tests/test_more.py")]}
    )
    loc = SertorRagLocator(runner=runner)
    tests = loc.locate_tests(Symbol(name="multiply", path="calc.py", line=0))
    paths = {t.path for t in tests}
    assert "test_calc.py" in paths
    assert "tests/test_more.py" in paths
    assert "calc.py" not in paths  # non è un test


def test_g6_no_query_from_non_identifier_snippet():
    """G6: senza identificatori, una riga non-identificatore (commento/statement) NON diventa query."""
    runner = FakeRunner({})
    loc = SertorRagLocator(runner=runner)
    loc.locate_symbols("calc.py", [], "# just a comment line")
    assert runner.queries == []


def test_g6_identifier_snippet_used_as_fallback():
    """G6: senza identificatori, una prima riga che È un identificatore valido è usata come query."""
    runner = FakeRunner({"helper": [_hit("calc.py")]})
    loc = SertorRagLocator(runner=runner)
    syms = loc.locate_symbols("calc.py", [], "helper")
    assert runner.queries == ["helper"]
    assert any(s.name == "helper" for s in syms)


def test_runner_failure_is_fail_loud():
    loc = SertorRagLocator(runner=FakeRunner(fail=True))
    with pytest.raises(RagUnavailableError):
        loc.locate_symbols("calc.py", ["x"], "")


def test_non_json_output_is_fail_loud():
    def bad_runner(args):
        return "ERROR: index not found, run `sertor-rag index .`"

    loc = SertorRagLocator(runner=bad_runner)
    with pytest.raises(RagUnavailableError):
        loc.locate_symbols("calc.py", ["x"], "")
