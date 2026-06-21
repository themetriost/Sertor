"""Test the CLI `sertor-rag eval run --fused` / `add-case --intent` / `amend-case` (069, TASK-A06).

The fused runner is monkeypatched; the suite lives in a tmp eval_dir. Exit codes follow the contract
(0/1/2). The `--fused` flag must not perturb the non-fused path (additivity).
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.engines.evaluation import EvalReport
from sertor_core.services.eval import baseline_io
from sertor_core.services.eval.models import (
    EvalCase,
    FusedBaseline,
    FusedEvalReport,
    FusionCaseResult,
    FusionReport,
    SurfaceBaseline,
    SurfaceEvalReport,
)
from sertor_core.services.eval.regression import compare_fused_to_baseline
from sertor_core.services.eval.suite_io import add_case, load_suite


def _surface(name: str, mrr: float = 0.7) -> SurfaceEvalReport:
    return SurfaceEvalReport(
        surface=name,
        report=EvalReport(hit_rate={1: 0.5, 3: 0.8, 5: 0.9}, mrr=mrr, queries=1, provider="hash"),
    )


def _fused_report(coverage: float = 1.0) -> FusedEvalReport:
    fusion = FusionReport(
        cases=(FusionCaseResult("both Q", ("r.md", "x.py"), True, True, coverage >= 1.0, True),),
        coverage=coverage,
        cases_count=1,
        hit_but_not_covered=0 if coverage >= 1.0 else 1,
    )
    return FusedEvalReport(
        surfaces=(_surface("search_code"), _surface("search_docs"), _surface("search_combined")),
        fusion=fusion,
        provider="hash",
    )


class _FakeFusedRunner:
    """Stand-in for `_FusedEvalRunner`: applies the real gate against the on-disk baseline."""

    def __init__(self, settings, report: FusedEvalReport):
        self._settings = settings
        self._report = report

    def run_fused(self, suite, ks=(1, 3, 5, 10)):
        baseline = baseline_io.load_fused_baseline(self._settings.eval_dir / "baseline.toml")
        verdict = compare_fused_to_baseline(
            self._report, baseline, self._settings.eval_tolerance
        )
        return self._report, verdict


@pytest.fixture
def wired(tmp_path, monkeypatch):
    eval_dir = tmp_path / "eval"
    settings = Settings(
        eval_dir=eval_dir, eval_tolerance=0.0, corpus="default", embed_provider="hash"
    )
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, env_file=".env": settings))
    state = {"report": _fused_report(), "indexed": frozenset({"r.md", "x.py"})}
    monkeypatch.setattr(
        cli, "build_fused_eval_runner", lambda s: _FakeFusedRunner(s, state["report"])
    )
    monkeypatch.setattr(cli, "build_indexed_docs", lambda s: state["indexed"])
    return settings, eval_dir, state


def _seed_intent_suite(eval_dir):
    add_case(eval_dir / "suite.toml", EvalCase("both Q", ("r.md", "x.py"), "nl", "both"))


# --------------------------------------------------------------------- run --fused
def test_fused_run_succeeds(wired, capsys):
    _s, eval_dir, _ = wired
    _seed_intent_suite(eval_dir)
    code = cli.main(["eval", "run", "--fused"])
    out = capsys.readouterr().out
    assert code == 0
    assert "fusion coverage" in out


def test_fused_run_without_suite_exits_1(wired, capsys):
    code = cli.main(["eval", "run", "--fused"])
    err = capsys.readouterr().err
    assert code == 1
    assert "add-case" in err


def test_fused_run_no_intent_cases_exits_0(wired, capsys):
    _s, eval_dir, _ = wired
    add_case(eval_dir / "suite.toml", EvalCase("sym Q", ("x.py",), "symbol", None))
    code = cli.main(["eval", "run", "--fused"])
    err = capsys.readouterr().err
    assert code == 0  # honest empty report, not a gate failure
    assert "intent-typed" in err


def test_fused_run_invalid_intent_exits_1(wired, capsys):
    _s, eval_dir, _ = wired
    (eval_dir).mkdir(parents=True, exist_ok=True)
    (eval_dir / "suite.toml").write_text(
        '[[case]]\nquery = "Q"\nexpected = ["x.py"]\nintent = "bad"\n', encoding="utf-8"
    )
    code = cli.main(["eval", "run", "--fused"])
    assert code == 1


def test_fused_run_record_baseline_writes_section(wired, capsys):
    _s, eval_dir, _ = wired
    _seed_intent_suite(eval_dir)
    code = cli.main(["eval", "run", "--fused", "--record-baseline"])
    assert code == 0
    loaded = baseline_io.load_fused_baseline(eval_dir / "baseline.toml")
    assert loaded is not None and loaded.fusion_coverage == 1.0


def test_fused_run_record_baseline_preserves_ir(wired, capsys):
    _s, eval_dir, _ = wired
    _seed_intent_suite(eval_dir)
    from sertor_core.services.eval.models import Baseline

    baseline_io.write_baseline(
        eval_dir / "baseline.toml",
        Baseline({1: 0.5}, 0.83, 1, "hash", baseline_io.now_iso_utc()),
    )
    code = cli.main(["eval", "run", "--fused", "--record-baseline"])
    assert code == 0
    assert baseline_io.load_baseline(eval_dir / "baseline.toml").mrr == 0.83  # IR untouched
    assert baseline_io.load_fused_baseline(eval_dir / "baseline.toml") is not None


def test_fused_run_regression_exits_1(wired, capsys):
    _s, eval_dir, state = wired
    _seed_intent_suite(eval_dir)
    baseline_io.write_fused_baseline(
        eval_dir / "baseline.toml",
        FusedBaseline(
            surfaces=(SurfaceBaseline("search_combined", {3: 0.8}, 0.9),),
            fusion_coverage=1.0,
            queries=1,
            provider="hash",
            recorded_at=baseline_io.now_iso_utc(),
        ),
    )
    state["report"] = _fused_report(coverage=0.0)  # coverage collapsed → regression
    code = cli.main(["eval", "run", "--fused"])
    err = capsys.readouterr().err
    assert code == 1
    assert "gate FAILED" in err


def test_fused_run_within_tolerance_exits_0(wired, monkeypatch, capsys):
    settings, eval_dir, state = wired
    _seed_intent_suite(eval_dir)
    import dataclasses

    tolerant = dataclasses.replace(settings, eval_tolerance=1.0)
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, env_file=".env": tolerant))
    monkeypatch.setattr(
        cli, "build_fused_eval_runner", lambda s: _FakeFusedRunner(s, state["report"])
    )
    baseline_io.write_fused_baseline(
        eval_dir / "baseline.toml",
        FusedBaseline(
            surfaces=(SurfaceBaseline("search_combined", {3: 0.8}, 0.9),),
            fusion_coverage=1.0,
            queries=1,
            provider="hash",
            recorded_at=baseline_io.now_iso_utc(),
        ),
    )
    state["report"] = _fused_report(coverage=0.0)
    code = cli.main(["eval", "run", "--fused"])
    assert code == 0


def test_fused_run_no_baseline_exits_0(wired, capsys):
    _s, eval_dir, _ = wired
    _seed_intent_suite(eval_dir)
    code = cli.main(["eval", "run", "--fused"])
    assert code == 0  # no baseline → no-baseline verdict


# --------------------------------------------------------------------- additivity
def test_run_without_fused_does_not_invoke_fused(wired, monkeypatch, capsys):
    _s, eval_dir, _ = wired
    _seed_intent_suite(eval_dir)

    def _boom(_s):
        raise AssertionError("fused runner must not be built without --fused")

    monkeypatch.setattr(cli, "build_fused_eval_runner", _boom)

    class _IRRunner:
        def run(self, suite, ks=(1, 3, 5, 10)):
            return EvalReport({1: 0.5}, 0.5, 1, "hash"), suite.kinds()

    monkeypatch.setattr(cli, "build_eval_runner", lambda s: _IRRunner())
    code = cli.main(["eval", "run"])
    assert code == 0


# --------------------------------------------------------------------- add-case --intent
def test_add_case_intent_persists(wired, capsys):
    _s, eval_dir, _ = wired
    code = cli.main(
        ["eval", "add-case", "--query", "Q", "--expected", "x.py", "--intent", "code"]
    )
    assert code == 0
    assert load_suite(eval_dir / "suite.toml").cases[0].intent == "code"


def test_add_case_invalid_intent_exits_2(wired):
    with pytest.raises(SystemExit) as exc:
        cli.main(["eval", "add-case", "--query", "Q", "--expected", "x.py", "--intent", "nope"])
    assert exc.value.code == 2


# --------------------------------------------------------------------- amend-case --intent
def test_amend_case_intent_updates(wired, capsys):
    _s, eval_dir, _ = wired
    cli.main(["eval", "add-case", "--query", "Q", "--expected", "x.py", "--intent", "code"])
    code = cli.main(["eval", "amend-case", "--query", "Q", "--intent", "both"])
    assert code == 0
    assert load_suite(eval_dir / "suite.toml").cases[0].intent == "both"


def test_amend_case_without_intent_leaves_it(wired, capsys):
    _s, eval_dir, _ = wired
    cli.main(["eval", "add-case", "--query", "Q", "--expected", "x.py", "--intent", "code"])
    code = cli.main(["eval", "amend-case", "--query", "Q", "--expected", "x.py"])
    assert code == 0
    assert load_suite(eval_dir / "suite.toml").cases[0].intent == "code"


def test_fused_run_json(wired, capsys):
    _s, eval_dir, _ = wired
    _seed_intent_suite(eval_dir)
    code = cli.main(["eval", "run", "--fused", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    obj = json.loads(out)
    assert obj["fusion"]["coverage"] == 1.0
