"""Test the CLI `sertor-rag graph-eval` (066, TASK-A03): run/add-case/amend-case/validate-ref.

The graph-eval runner is monkeypatched (no real graph/index); the suite lives in a tmp eval_dir.
Exit codes follow the contract (0/1/2). The gate (SC-003) is exercised via the fake verdict.
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.services.eval.graph_eval import evaluate_graph_case
from sertor_core.services.eval.models import (
    GraphCase,
    GraphCaseResult,
    GraphEvalReport,
    GraphMetricDelta,
    GraphRegressionVerdict,
    RefValidation,
)
from sertor_core.services.eval.suite_io import add_graph_case, load_suite


def _report(f1=1.0, exact=True) -> GraphEvalReport:
    m = (
        evaluate_graph_case(frozenset({"a.py#A"}), frozenset({"a.py#A"}))
        if exact
        else evaluate_graph_case(frozenset({"a.py#A"}), frozenset({"a.py#A", "b.py#B"}))
    )
    return GraphEvalReport(
        cases=(GraphCaseResult("who_calls", "X", m),),
        mean_precision=m.precision,
        mean_recall=m.recall,
        mean_f1=m.f1,
        by_relation={"who_calls": m.f1},
        cases_count=1,
    )


def _empty_report() -> GraphEvalReport:
    return GraphEvalReport(cases=(), mean_precision=0.0, mean_recall=0.0,
                           mean_f1=0.0, by_relation={}, cases_count=0)


class _FakeRunner:
    def __init__(self, report, verdict, *, graph_built=True, unverifiable=()):
        self._report = report
        self._verdict = verdict
        self._graph_built = graph_built
        self._unverifiable = unverifiable
        self.graph = self  # the handler reads .graph; validate_refs is also monkeypatched

    def run(self, suite):
        from sertor_core.domain.errors import GraphNotFoundError
        if not self._graph_built:
            raise GraphNotFoundError("not built", corpus="default")
        if suite.graph_cases == ():
            return _empty_report(), self._verdict
        return self._report, self._verdict


@pytest.fixture
def wired(tmp_path, monkeypatch):
    eval_dir = tmp_path / "eval"
    settings = Settings(eval_dir=eval_dir, corpus="default", backend="local")
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, env_file=".env": settings))
    state = {
        "report": _report(),
        "verdict": GraphRegressionVerdict("pass", (), 0.0),
        "graph_built": True,
        "unverifiable": (),
    }

    def _factory(s, *, exact_gate=False):
        return _FakeRunner(
            state["report"], state["verdict"],
            graph_built=state["graph_built"], unverifiable=state["unverifiable"],
        )

    monkeypatch.setattr(cli, "build_graph_eval_runner", _factory)
    monkeypatch.setattr(
        cli, "validate_refs",
        lambda graph, rel, tgt, refs: RefValidation(
            checked=refs,
            unverifiable=state["unverifiable"] if state["graph_built"] else (),
            graph_available=state["graph_built"],
        ),
    )
    return settings, eval_dir, state


def _seed(eval_dir):
    add_graph_case(eval_dir / "suite.toml", GraphCase("who_calls", "X", ("a.py#A",)))


# ----------------------------------------------------------------- run
def test_run_with_suite_succeeds(wired, capsys):
    _s, eval_dir, _ = wired
    _seed(eval_dir)
    code = cli.main(["graph-eval", "run"])
    out = capsys.readouterr().out
    assert code == 0 and "mean_f1=1.00" in out


def test_run_without_suite_exit_1(wired, capsys):
    code = cli.main(["graph-eval", "run"])
    err = capsys.readouterr().err
    assert code == 1 and ("suite" in err.lower())


def test_run_no_graph_cases_exit_0(wired, capsys):
    _s, eval_dir, _ = wired
    # seed an IR-only suite (no graph_case)
    from sertor_core.services.eval.models import EvalCase, EvalSuite
    from sertor_core.services.eval.suite_io import write_suite
    write_suite(eval_dir / "suite.toml", EvalSuite(cases=(EvalCase("q", ("p.py",), None),)))
    code = cli.main(["graph-eval", "run"])
    err = capsys.readouterr().err
    assert code == 0 and "add-case" in err


def test_run_graph_not_built_exit_1(wired, capsys):
    _s, eval_dir, state = wired
    _seed(eval_dir)
    state["graph_built"] = False
    code = cli.main(["graph-eval", "run"])
    assert code == 1


def test_run_record_baseline_writes_file(wired, capsys):
    _s, eval_dir, _ = wired
    _seed(eval_dir)
    code = cli.main(["graph-eval", "run", "--record-baseline"])
    assert code == 0 and (eval_dir / "graph_baseline.toml").exists()


def test_run_regression_exit_1(wired, capsys):
    _s, eval_dir, state = wired
    _seed(eval_dir)
    state["verdict"] = GraphRegressionVerdict(
        "regressed", (GraphMetricDelta("mean_f1", 0.5, 0.8, -0.3, True),), 0.0
    )
    code = cli.main(["graph-eval", "run"])
    assert code == 1


def test_run_within_tolerance_exit_0(wired, capsys):
    _s, eval_dir, state = wired
    _seed(eval_dir)
    state["verdict"] = GraphRegressionVerdict(
        "pass", (GraphMetricDelta("mean_f1", 0.78, 0.80, -0.02, False),), 0.05
    )
    code = cli.main(["graph-eval", "run"])
    assert code == 0


def test_run_exact_gate_fails_on_non_exact(wired, capsys):
    _s, eval_dir, state = wired
    _seed(eval_dir)
    state["report"] = _report(f1=0.67, exact=False)
    code = cli.main(["graph-eval", "run", "--exact"])
    assert code == 1


# ----------------------------------------------------------------- add-case
def test_add_case_verified_ref_exit_0(wired, capsys):
    _s, eval_dir, _ = wired
    code = cli.main(
        ["graph-eval", "add-case", "--relation", "who_calls", "--target", "X",
         "--expected", "a.py#A"]
    )
    assert code == 0
    assert len(load_suite(eval_dir / "suite.toml").graph_cases) == 1


def test_add_case_unverifiable_without_confirm_exit_1(wired, capsys):
    _s, eval_dir, state = wired
    state["unverifiable"] = ("z.py#Z",)
    code = cli.main(
        ["graph-eval", "add-case", "--relation", "who_calls", "--target", "X",
         "--expected", "z.py#Z"]
    )
    err = capsys.readouterr().err
    assert code == 1 and "z.py#Z" in err


def test_add_case_unverifiable_with_confirm_exit_0(wired, capsys):
    _s, eval_dir, state = wired
    state["unverifiable"] = ("z.py#Z",)
    code = cli.main(
        ["graph-eval", "add-case", "--relation", "who_calls", "--target", "X",
         "--expected", "z.py#Z", "--confirm"]
    )
    assert code == 0
    assert len(load_suite(eval_dir / "suite.toml").graph_cases) == 1


# ----------------------------------------------------------------- amend-case
def test_amend_case_exit_0(wired, capsys):
    _s, eval_dir, _ = wired
    _seed(eval_dir)
    code = cli.main(
        ["graph-eval", "amend-case", "--relation", "who_calls", "--target", "X",
         "--expected", "a.py#A"]
    )
    assert code == 0


def test_amend_missing_case_exit_1(wired, capsys):
    _s, eval_dir, _ = wired
    code = cli.main(
        ["graph-eval", "amend-case", "--relation", "defines", "--target", "Nope",
         "--expected", "a.py#A"]
    )
    assert code == 1


# ----------------------------------------------------------------- validate-ref
def test_validate_ref_exit_0(wired, capsys):
    code = cli.main(
        ["graph-eval", "validate-ref", "--relation", "who_calls", "--target", "X", "a.py#A"]
    )
    assert code == 0


def test_validate_ref_json(wired, capsys):
    code = cli.main(
        ["graph-eval", "validate-ref", "--relation", "who_calls", "--target", "X",
         "a.py#A", "--json"]
    )
    out = capsys.readouterr().out
    assert code == 0 and json.loads(out)["graph_available"] is True


def test_no_subcommand_exit_2(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["graph-eval"])
    assert exc.value.code == 2
