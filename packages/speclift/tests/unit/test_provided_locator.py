"""ProvidedEvidenceLocator: EvidenceLocator alternativo alimentato da evidenza pre-localizzata
(l'agente, coi propri tool MCP — vedi feedback Sertor 2026-07-01), mai da un subprocess.

Stessa forma dei test di `SertorRagLocator` (tests/unit/test_rag_sertor.py) dove il comportamento
deve combaciare (dedup, cap G6, degrado onesto); diverge dove l'adapter è intrinsecamente diverso
(nessun filtro path-based su `locate_tests`: l'agente decide già cosa è un test).
"""

from __future__ import annotations

from speclift.adapters.provided_locator import ProvidedEvidenceLocator
from speclift.config import Config
from speclift.domain.models import Symbol


def _sym(path: str, line: int = 0, name: str = "multiply") -> dict:
    return {"name": name, "path": path, "line": line, "provenance": f"{path}#{line}"}


def test_locate_symbols_maps_results():
    loc = ProvidedEvidenceLocator(
        {"symbols": {"calc.py::multiply": [_sym("calc.py", 5), _sym("other.py", 9)]}}
    )
    syms = loc.locate_symbols("calc.py", ["multiply"], "def multiply(a, b):")
    names = {(s.name, s.path) for s in syms}
    assert ("multiply", "calc.py") in names
    assert ("multiply", "other.py") in names  # evidenza cross-layer mantenuta


def test_missing_key_degrades_to_empty():
    loc = ProvidedEvidenceLocator({"symbols": {}})
    assert loc.locate_symbols("calc.py", ["multiply"], "") == []


def test_query_cap_respected():
    payload = {
        "symbols": {
            "calc.py::a": [_sym("calc.py", name="a")],
            "calc.py::e": [_sym("calc.py", name="e")],
        }
    }
    loc = ProvidedEvidenceLocator(payload, config=Config(max_queries_per_symbol=2))
    syms = loc.locate_symbols("calc.py", ["a", "b", "c", "d", "e"], "snippet")
    names = {s.name for s in syms}
    assert names == {"a"}  # "e" è oltre il cap: mai cercato, quindi mai matchato


def test_locate_symbols_dedups_same_name_and_path():
    loc = ProvidedEvidenceLocator(
        {"symbols": {"calc.py::multiply": [_sym("calc.py", 5), _sym("calc.py", 5)]}}
    )
    syms = loc.locate_symbols("calc.py", ["multiply"], "")
    assert len([s for s in syms if s.path == "calc.py"]) == 1


def test_g6_no_query_from_non_identifier_snippet():
    loc = ProvidedEvidenceLocator({"symbols": {"calc.py::helper": [_sym("calc.py", name="helper")]}})
    syms = loc.locate_symbols("calc.py", [], "# just a comment line")
    assert syms == []


def test_g6_identifier_snippet_used_as_fallback():
    loc = ProvidedEvidenceLocator({"symbols": {"calc.py::helper": [_sym("calc.py", name="helper")]}})
    syms = loc.locate_symbols("calc.py", [], "helper")
    assert any(s.name == "helper" for s in syms)


def test_locate_tests_maps_by_symbol_name():
    loc = ProvidedEvidenceLocator(
        {
            "tests": {
                "multiply": [
                    {"name": "test_multiply", "path": "test_calc.py", "covers_symbol": "multiply"}
                ]
            }
        }
    )
    tests = loc.locate_tests(Symbol(name="multiply", path="calc.py", line=0))
    assert [t.path for t in tests] == ["test_calc.py"]


def test_locate_tests_missing_symbol_degrades_to_empty():
    loc = ProvidedEvidenceLocator({"tests": {}})
    assert loc.locate_tests(Symbol(name="multiply", path="calc.py", line=0)) == []
