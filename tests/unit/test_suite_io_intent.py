"""Test suite_io with the `intent` field (069, TASK-A05): round-trip + preserve-both + validation.

stdlib only; a tmp suite file. Verifies the writer preserves `[[case]]` (with/without intent) AND
`[[graph_case]]` (preserve-both, DA-d), and that an invalid intent names the case.
"""
from __future__ import annotations

import tomllib

import pytest

from sertor_core.domain.errors import (
    FusedSuiteValidationError,
    SuiteValidationError,
    SuiteWriteError,
)
from sertor_core.services.eval.models import EvalCase, EvalSuite, GraphCase
from sertor_core.services.eval.suite_io import (
    add_case,
    amend_case,
    load_suite,
    write_suite,
)


def _mixed_suite() -> EvalSuite:
    return EvalSuite(
        cases=(
            EvalCase("symbol Q", ("src/ports.py",), "symbol", None),
            EvalCase("nl code Q", ("src/impl.py",), "nl", "code"),
            EvalCase("nl both Q", ("requirements/r.md", "src/impl.py"), "nl", "both"),
        ),
        graph_cases=(GraphCase("who_calls", "evaluate", ("src/eval.py#evaluate",)),),
    )


def test_round_trip_preserves_all_sections(tmp_path):
    path = tmp_path / "suite.toml"
    suite = _mixed_suite()
    write_suite(path, suite)
    loaded = load_suite(path)
    assert loaded.cases == suite.cases
    assert loaded.graph_cases == suite.graph_cases
    # the case without intent round-trips to None
    assert loaded.cases[0].intent is None
    assert loaded.cases[1].intent == "code"
    assert loaded.cases[2].intent == "both"


def test_load_case_without_intent_is_none(tmp_path):
    path = tmp_path / "suite.toml"
    path.write_text(
        '[[case]]\nquery = "Q"\nexpected = ["src/x.py"]\nkind = "symbol"\n', encoding="utf-8"
    )
    loaded = load_suite(path)
    assert loaded.cases[0].intent is None


def test_invalid_intent_raises_naming_the_case(tmp_path):
    path = tmp_path / "suite.toml"
    path.write_text(
        '[[case]]\nquery = "Bad Q"\nexpected = ["src/x.py"]\nintent = "invalid"\n',
        encoding="utf-8",
    )
    with pytest.raises(FusedSuiteValidationError) as exc:
        load_suite(path)
    assert "Bad Q" in str(exc.value)
    assert "invalid" in str(exc.value)


def test_empty_intent_string_raises(tmp_path):
    path = tmp_path / "suite.toml"
    path.write_text(
        '[[case]]\nquery = "Q"\nexpected = ["src/x.py"]\nintent = ""\n', encoding="utf-8"
    )
    with pytest.raises(FusedSuiteValidationError):
        load_suite(path)


def test_add_case_idempotent_on_query(tmp_path):
    path = tmp_path / "suite.toml"
    add_case(path, EvalCase("Q", ("src/x.py",), "nl", "both"))
    add_case(path, EvalCase("Q", ("src/x.py",), "nl", "both"))  # no-op
    assert len(load_suite(path).cases) == 1


def test_add_case_same_query_different_intent_errors(tmp_path):
    path = tmp_path / "suite.toml"
    add_case(path, EvalCase("Q", ("src/x.py",), "nl", "code"))
    with pytest.raises(SuiteValidationError) as exc:
        add_case(path, EvalCase("Q", ("src/x.py",), "nl", "doc"))
    assert "amend-case" in str(exc.value)


def test_add_case_preserves_graph_cases(tmp_path):
    path = tmp_path / "suite.toml"
    write_suite(
        path,
        EvalSuite(
            cases=(),
            graph_cases=(GraphCase("who_calls", "f", ("a.py#f",)),),
        ),
    )
    add_case(path, EvalCase("Q", ("src/x.py",), "nl", "both"))
    loaded = load_suite(path)
    assert loaded.graph_cases == (GraphCase("who_calls", "f", ("a.py#f",)),)
    assert loaded.cases[0].intent == "both"


def test_amend_case_updates_intent(tmp_path):
    path = tmp_path / "suite.toml"
    add_case(path, EvalCase("Q", ("src/x.py",), "nl", "code"))
    amend_case(path, "Q", intent="both")
    assert load_suite(path).cases[0].intent == "both"


def test_amend_case_without_intent_leaves_it(tmp_path):
    path = tmp_path / "suite.toml"
    add_case(path, EvalCase("Q", ("src/x.py",), "nl", "code"))
    amend_case(path, "Q", expected=("src/y.py",))
    loaded = load_suite(path)
    assert loaded.cases[0].intent == "code"  # unchanged
    assert loaded.cases[0].expected == ("src/y.py",)


def test_amend_case_invalid_intent_errors(tmp_path):
    path = tmp_path / "suite.toml"
    add_case(path, EvalCase("Q", ("src/x.py",), "nl", "code"))
    with pytest.raises(FusedSuiteValidationError):
        amend_case(path, "Q", intent="nope")


def test_write_suite_round_trip_failure_raises(tmp_path, monkeypatch):
    path = tmp_path / "suite.toml"
    suite = EvalSuite(cases=(EvalCase("Q", ("src/x.py",), "nl", "both"),))

    def _boom(*a, **k):
        raise tomllib.TOMLDecodeError("boom", "", 0)

    monkeypatch.setattr("sertor_core.services.eval.suite_io.tomllib.load", _boom)
    with pytest.raises(SuiteWriteError):
        write_suite(path, suite)
