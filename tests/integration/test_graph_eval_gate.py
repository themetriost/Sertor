"""End-to-end smoke test of the graph-eval run + non-regression gate (066, TASK-P01, not cloud).

Drives the real set-based oracle + suite_io/baseline_io through the CLI vehicle (`sertor-rag
graph-eval ...`). The code graph is the offline `FakeCodeGraph` (structural typing, no networkx, no
network) populated from a tiny synthetic `GraphData` — only the graph ADAPTER is faked; the runner,
metrics, gate, TOML IO and CLI are real. Exercises determinism (SC-001/REQ-015), the gate (SC-003),
add-case/validate-ref, and the no-baseline pass (REQ-033).
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import GraphData, GraphEdge, GraphNode
from sertor_core.services.eval.graph_baseline_io import (
    load_graph_baseline,
    write_graph_baseline,
)
from sertor_core.services.eval.graph_regression import compare_graph_to_baseline
from sertor_core.services.eval.graph_runner import (
    emit_graph_eval_event,
    run_graph_evaluation,
)
from sertor_core.services.eval.models import GraphBaseline
from tests.fixtures.mocks import FakeCodeGraph

pytestmark = pytest.mark.integration

_CORPUS = "default"

# Synthetic corpus: `caller_a` and `caller_b` both call `target_fn`; `target_fn` is defined once.
_GRAPH = GraphData(
    nodes=(
        GraphNode(id="t.py::target_fn", kind="function", name="target_fn",
                  path="t.py", line=1, qualname="target_fn"),
        GraphNode(id="a.py::caller_a", kind="function", name="caller_a",
                  path="a.py", line=1, qualname="caller_a"),
        GraphNode(id="b.py::caller_b", kind="function", name="caller_b",
                  path="b.py", line=1, qualname="caller_b"),
        GraphNode(id="lonely.py::lonely_fn", kind="function", name="lonely_fn",
                  path="lonely.py", line=1, qualname="lonely_fn"),
    ),
    edges=(
        GraphEdge(source="a.py::caller_a", target="t.py::target_fn", type="calls"),
        GraphEdge(source="b.py::caller_b", target="t.py::target_fn", type="calls"),
    ),
)

_TARGET_CALLERS = ("a.py#caller_a", "b.py#caller_b")
_TARGET_DEF = "t.py#target_fn"


class _RealGraphRunner:
    """The composition `_GraphEvalRunner` over the offline FakeCodeGraph (real measure + gate)."""

    def __init__(self, settings, graph, *, exact_gate=False):
        self._settings = settings
        self.graph = graph
        self._exact_gate = exact_gate

    def run(self, suite):
        from sertor_core.domain.errors import GraphNotFoundError
        if not self.graph.exists(self._settings.corpus):
            raise GraphNotFoundError("not built", corpus=self._settings.corpus)
        report = run_graph_evaluation(self.graph, suite)
        baseline = load_graph_baseline(self._settings.eval_dir / "graph_baseline.toml")
        verdict = compare_graph_to_baseline(
            report, baseline, self._settings.graph_eval_tolerance
        )
        emit_graph_eval_event(report, verdict, self._exact_gate)
        return report, verdict


@pytest.fixture
def wired(tmp_path, monkeypatch):
    eval_dir = tmp_path / "eval"
    state = {"tolerance": 0.0}

    def _settings():
        return Settings(
            eval_dir=eval_dir, corpus=_CORPUS, backend="local", index_dir=tmp_path,
            graph_eval_tolerance=state["tolerance"],
        )

    graph = FakeCodeGraph(corpus=_CORPUS)
    graph.build(_CORPUS, _GRAPH)

    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, e=".env": _settings()))

    def _factory(s, *, exact_gate=False):
        return _RealGraphRunner(_settings(), graph, exact_gate=exact_gate)

    monkeypatch.setattr(cli, "build_graph_eval_runner", _factory)
    monkeypatch.setattr(
        cli, "validate_refs",
        lambda g, rel, tgt, refs: __import__(
            "sertor_core.services.eval.graph_runner", fromlist=["validate_refs"]
        ).validate_refs(graph, rel, tgt, refs),
    )
    return eval_dir, state


def _seed(eval_dir):
    from sertor_core.services.eval.models import GraphCase
    from sertor_core.services.eval.suite_io import add_graph_case

    add_graph_case(eval_dir / "suite.toml",
                   GraphCase("who_calls", "target_fn", _TARGET_CALLERS))
    add_graph_case(eval_dir / "suite.toml",
                   GraphCase("defines", "target_fn", (_TARGET_DEF,)))
    add_graph_case(eval_dir / "suite.toml",
                   GraphCase("who_calls", "lonely_fn", ()))  # empty expected (no callers)


def test_run_succeeds_with_perfect_metrics(wired, capsys):
    eval_dir, _ = wired
    _seed(eval_dir)
    code = cli.main(["graph-eval", "run", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    obj = json.loads(out)
    assert obj["cases"] == 3 and obj["mean_f1"] == 1.0


def test_determinism_two_runs(wired, capsys):
    eval_dir, _ = wired
    _seed(eval_dir)
    cli.main(["graph-eval", "run", "--json"])
    first = json.loads(capsys.readouterr().out)
    cli.main(["graph-eval", "run", "--json"])
    second = json.loads(capsys.readouterr().out)
    assert first["mean_f1"] == second["mean_f1"]
    assert first["per_case"] == second["per_case"]


def test_record_baseline_then_pass(wired, capsys):
    eval_dir, _ = wired
    _seed(eval_dir)
    assert cli.main(["graph-eval", "run", "--record-baseline"]) == 0
    capsys.readouterr()
    assert (eval_dir / "graph_baseline.toml").exists()
    assert cli.main(["graph-eval", "run"]) == 0


def test_gate_fails_on_degraded_suite(wired, capsys):
    eval_dir, _ = wired
    _seed(eval_dir)
    # Record a high baseline by hand, then degrade the suite so mean_f1 drops below it.
    write_graph_baseline(
        eval_dir / "graph_baseline.toml",
        GraphBaseline(mean_f1=1.0, mean_recall=1.0, mean_precision=1.0,
                      cases=3, recorded_at="t"),
    )
    from sertor_core.services.eval.models import GraphCase
    from sertor_core.services.eval.suite_io import add_graph_case
    # Impossible expected set → recall 0 on this case → mean_f1 drops.
    add_graph_case(eval_dir / "suite.toml",
                   GraphCase("who_calls", "target_fn_typo", ("nope.py#X",)))
    code = cli.main(["graph-eval", "run"])
    err = capsys.readouterr().err
    assert code == 1 and "graph non-regression gate FAILED" in err


def test_high_tolerance_passes(wired, capsys):
    eval_dir, state = wired
    _seed(eval_dir)
    write_graph_baseline(
        eval_dir / "graph_baseline.toml",
        GraphBaseline(mean_f1=1.0, mean_recall=1.0, mean_precision=1.0,
                      cases=3, recorded_at="t"),
    )
    from sertor_core.services.eval.models import GraphCase
    from sertor_core.services.eval.suite_io import add_graph_case
    add_graph_case(eval_dir / "suite.toml",
                   GraphCase("who_calls", "target_fn_typo", ("nope.py#X",)))
    state["tolerance"] = 1.0
    assert cli.main(["graph-eval", "run"]) == 0


def test_no_baseline_passes(wired, capsys):
    eval_dir, _ = wired
    _seed(eval_dir)
    code = cli.main(["graph-eval", "run", "--json"])
    obj = json.loads(capsys.readouterr().out)
    assert code == 0 and obj["non_regression"]["verdict"] == "no-baseline"


def test_add_case_with_navigable_refs(wired, capsys):
    eval_dir, _ = wired
    code = cli.main(
        ["graph-eval", "add-case", "--relation", "who_calls", "--target", "target_fn",
         "--expected", ",".join(_TARGET_CALLERS)]
    )
    assert code == 0
    from sertor_core.services.eval.suite_io import load_suite
    assert len(load_suite(eval_dir / "suite.toml").graph_cases) == 1


def test_add_case_unverifiable_without_confirm(wired, capsys):
    eval_dir, _ = wired
    code = cli.main(
        ["graph-eval", "add-case", "--relation", "who_calls", "--target", "target_fn",
         "--expected", "ghost.py#G"]
    )
    err = capsys.readouterr().err
    assert code == 1 and "ghost.py#G" in err


def test_validate_ref_exit_0_json(wired, capsys):
    code = cli.main(
        ["graph-eval", "validate-ref", "--relation", "who_calls", "--target", "target_fn",
         *_TARGET_CALLERS, "--json"]
    )
    out = capsys.readouterr().out
    assert code == 0
    obj = json.loads(out)
    assert obj["graph_available"] is True and obj["unverifiable"] == []
