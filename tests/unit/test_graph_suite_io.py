"""Test suite_io extended for [[graph_case]] (066, TASK-F04): round-trip, dedup, validation.

Non-distruttività is the critical invariant: writing graph_cases must NOT drop the IR [[case]] and
vice versa (DA-d/RNF-4).
"""
from __future__ import annotations

import pytest

from sertor_core.domain.errors import GraphSuiteValidationError, SuiteWriteError
from sertor_core.services.eval.models import EvalCase, EvalSuite, GraphCase
from sertor_core.services.eval.suite_io import (
    add_graph_case,
    amend_graph_case,
    load_suite,
    write_suite,
)


def _suite() -> EvalSuite:
    return EvalSuite(
        cases=(EvalCase("EmbeddingProvider", ("src/ports.py",), "symbol"),),
        graph_cases=(
            GraphCase("who_calls", "build_facade", ("a.py#X", "b.py#Y")),
            GraphCase("defines", "build_facade", ("comp.py#build_facade",)),
        ),
    )


def test_round_trip_preserves_both_sections(tmp_path):
    path = tmp_path / "suite.toml"
    write_suite(path, _suite())
    loaded = load_suite(path)
    assert loaded.cases == _suite().cases
    assert loaded.graph_cases == _suite().graph_cases


def test_ir_only_suite_has_empty_graph_cases(tmp_path):
    path = tmp_path / "suite.toml"
    write_suite(path, EvalSuite(cases=(EvalCase("q", ("p.py",), None),)))
    loaded = load_suite(path)
    assert loaded.graph_cases == ()


def test_graph_only_suite_has_empty_cases(tmp_path):
    path = tmp_path / "suite.toml"
    write_suite(path, EvalSuite(graph_cases=(GraphCase("defines", "X", ("p.py#X",)),)))
    loaded = load_suite(path)
    assert loaded.cases == ()
    assert loaded.graph_cases == (GraphCase("defines", "X", ("p.py#X",)),)


def test_missing_relation_raises_named(tmp_path):
    path = tmp_path / "suite.toml"
    path.write_text('[[graph_case]]\ntarget = "X"\nexpected = []\n', encoding="utf-8")
    with pytest.raises(GraphSuiteValidationError) as exc:
        load_suite(path)
    assert "[0]" in str(exc.value)


def test_unsupported_relation_rejected(tmp_path):
    path = tmp_path / "suite.toml"
    path.write_text(
        '[[graph_case]]\nrelation = "related_docs"\ntarget = "X"\nexpected = []\n',
        encoding="utf-8",
    )
    with pytest.raises(GraphSuiteValidationError):
        load_suite(path)


def test_empty_expected_is_valid(tmp_path):
    path = tmp_path / "suite.toml"
    write_suite(path, EvalSuite(graph_cases=(GraphCase("who_calls", "lonely", ()),)))
    loaded = load_suite(path)
    assert loaded.graph_cases[0].expected == ()


def test_add_graph_case_idempotent(tmp_path):
    path = tmp_path / "suite.toml"
    case = GraphCase("who_calls", "X", ("p.py#A",))
    add_graph_case(path, case)
    add_graph_case(path, GraphCase("who_calls", "X", ("p.py#B",)))  # same (relation, target)
    loaded = load_suite(path)
    assert len(loaded.graph_cases) == 1


def test_add_graph_case_preserves_ir(tmp_path):
    path = tmp_path / "suite.toml"
    write_suite(path, EvalSuite(cases=(EvalCase("q", ("p.py",), None),)))
    add_graph_case(path, GraphCase("defines", "X", ("p.py#X",)))
    loaded = load_suite(path)
    assert loaded.cases == (EvalCase("q", ("p.py",), None),)
    assert len(loaded.graph_cases) == 1


def test_amend_graph_case_updates_expected(tmp_path):
    path = tmp_path / "suite.toml"
    add_graph_case(path, GraphCase("who_calls", "X", ("p.py#A",)))
    amend_graph_case(path, "who_calls", "X", ("p.py#A", "p.py#B"))
    loaded = load_suite(path)
    assert loaded.graph_cases[0].expected == ("p.py#A", "p.py#B")


def test_amend_missing_case_raises(tmp_path):
    path = tmp_path / "suite.toml"
    add_graph_case(path, GraphCase("who_calls", "X", ("p.py#A",)))
    with pytest.raises(GraphSuiteValidationError):
        amend_graph_case(path, "defines", "Y", ("p.py#Y",))


def test_write_round_trip_failure_raises(tmp_path, monkeypatch):
    path = tmp_path / "suite.toml"
    from sertor_core.domain.errors import SuiteValidationError
    from sertor_core.services.eval import suite_io

    def _boom(p):
        raise SuiteValidationError(-1, "forced")

    monkeypatch.setattr(suite_io, "load_suite", _boom)
    with pytest.raises(SuiteWriteError):
        write_suite(path, _suite())
