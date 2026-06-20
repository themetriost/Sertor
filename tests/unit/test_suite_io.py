"""Test eval suite I/O (065, TASK-012): load/write/add/amend with round-trip + escaping."""
from __future__ import annotations

import pytest

from sertor_core.domain.errors import (
    SuiteNotFoundError,
    SuiteValidationError,
    SuiteWriteError,
)
from sertor_core.services.eval import suite_io
from sertor_core.services.eval.models import EvalCase, EvalSuite


def test_load_missing_suite_raises(tmp_path):
    with pytest.raises(SuiteNotFoundError):
        suite_io.load_suite(tmp_path / "suite.toml")


def test_write_then_read_round_trip(tmp_path):
    path = tmp_path / "suite.toml"
    suite = EvalSuite(
        cases=(
            EvalCase("EmbeddingProvider", ("src/ports.py",), "symbol"),
            EvalCase("where adapters are wired", ("src/composition.py",), "nl"),
        )
    )
    suite_io.write_suite(path, suite)
    assert suite_io.load_suite(path).cases == suite.cases


def test_escapes_quotes_and_backslashes(tmp_path):
    path = tmp_path / "suite.toml"
    tricky = 'a "quoted" path\\with\\backslash'
    suite = EvalSuite(cases=(EvalCase(tricky, ("p.py",), None),))
    suite_io.write_suite(path, suite)
    assert suite_io.load_suite(path).cases[0].query == tricky


def test_multiline_query_round_trips(tmp_path):
    path = tmp_path / "suite.toml"
    multi = "def add(a, b):\n    return a + b"
    suite = EvalSuite(cases=(EvalCase(multi, ("calc.py",), None),))
    suite_io.write_suite(path, suite)
    assert suite_io.load_suite(path).cases[0].query == multi


def test_validation_error_on_missing_expected(tmp_path):
    path = tmp_path / "suite.toml"
    path.write_text('[[case]]\nquery = "x"\n', encoding="utf-8")
    with pytest.raises(SuiteValidationError) as exc:
        suite_io.load_suite(path)
    assert exc.value.case_index == 0


def test_validation_error_on_empty_expected(tmp_path):
    path = tmp_path / "suite.toml"
    path.write_text('[[case]]\nquery = "x"\nexpected = []\n', encoding="utf-8")
    with pytest.raises(SuiteValidationError):
        suite_io.load_suite(path)


def test_write_error_on_round_trip_failure(tmp_path, monkeypatch):
    path = tmp_path / "suite.toml"
    # Force the round-trip to fail: make the re-read return a different suite.
    monkeypatch.setattr(
        suite_io, "load_suite", lambda p: EvalSuite(cases=())
    )
    with pytest.raises(SuiteWriteError):
        suite_io.write_suite(path, EvalSuite(cases=(EvalCase("q", ("p.py",), None),)))


def test_add_case_idempotent_on_duplicate_query(tmp_path):
    path = tmp_path / "suite.toml"
    case = EvalCase("EmbeddingProvider", ("src/ports.py",), "symbol")
    suite_io.add_case(path, case)
    suite_io.add_case(path, case)  # second add must be a no-op
    assert len(suite_io.load_suite(path).cases) == 1


def test_add_case_creates_suite_when_absent(tmp_path):
    path = tmp_path / "suite.toml"
    suite_io.add_case(path, EvalCase("q", ("p.py",), None))
    assert path.exists()
    assert suite_io.load_suite(path).cases[0].query == "q"


def test_add_case_preserves_order(tmp_path):
    path = tmp_path / "suite.toml"
    suite_io.add_case(path, EvalCase("first", ("a.py",), None))
    suite_io.add_case(path, EvalCase("second", ("b.py",), None))
    queries = [c.query for c in suite_io.load_suite(path).cases]
    assert queries == ["first", "second"]


def test_amend_case_updates_expected(tmp_path):
    path = tmp_path / "suite.toml"
    suite_io.add_case(path, EvalCase("q", ("old.py",), "symbol"))
    suite_io.amend_case(path, "q", expected=("new.py", "also.py"))
    case = suite_io.load_suite(path).cases[0]
    assert case.expected == ("new.py", "also.py")
    assert case.kind == "symbol"  # preserved


def test_amend_unknown_query_raises(tmp_path):
    path = tmp_path / "suite.toml"
    suite_io.add_case(path, EvalCase("q", ("p.py",), None))
    with pytest.raises(SuiteValidationError):
        suite_io.amend_case(path, "absent", expected=("x.py",))
