"""End-to-end smoke test of the fused eval run + non-regression gate (069, TASK-P01, not cloud).

Uses a real `RetrievalFacade` over an in-memory store indexed from a tiny synthetic corpus with
explicit `doc_type=CODE`/`doc_type=DOC` documents, driven through the CLI vehicle (`sertor-rag eval
run --fused`). Exercises the fused measure (fusion coverage in stdout), `--record-baseline` (writes
`[fused_baseline]` without touching `[baseline]`), the gate (degraded baseline → exit 1; high
tolerance → exit 0), determinism, no-baseline (exit 0), and additivity (plain `eval run` unchanged).
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import (
    Chunk,
    ChunkerKind,
    ChunkMetadata,
    DocType,
    EmbeddedChunk,
)
from sertor_core.services.eval import baseline_io
from sertor_core.services.eval.fused_runner import run_fused_evaluation
from sertor_core.services.eval.models import EvalCase
from sertor_core.services.eval.regression import compare_fused_to_baseline
from sertor_core.services.eval.suite_io import add_case
from sertor_core.services.retrieval import RetrievalFacade
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

pytestmark = pytest.mark.integration

_COLL = "fused-gate-coll"

# Synthetic corpus: a doc file and a code file, each one chunk; queries match the chunk text so the
# in-memory cosine retrieval is deterministic.
_DOC_PATH = "requirements/feature.md"
_CODE_PATH = "src/impl.py"
_DOC_TEXT = "the feature requires fusing documentation and source together"
_CODE_TEXT = "def fuse_results(doc, code):\n    return doc + code"


def _chunk(path: str, text: str, doc_type: DocType) -> Chunk:
    return Chunk(
        id=f"{path}#0",
        document_id=path,
        text=text,
        doc_type=doc_type,
        metadata=ChunkMetadata(path=path, chunker=ChunkerKind.SIZE_FALLBACK),
    )


def _build_facade() -> RetrievalFacade:
    """A real in-memory facade over a doc + a code chunk (deterministic, offline)."""
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    chunks = [
        _chunk(_DOC_PATH, _DOC_TEXT, DocType.DOC),
        _chunk(_CODE_PATH, _CODE_TEXT, DocType.CODE),
    ]
    vectors = emb.embed([c.text for c in chunks])
    embedded = [
        EmbeddedChunk(
            chunk_id=c.id,
            vector=v,
            payload={"text": c.text, "path": c.metadata.path, "doc_type": str(c.doc_type)},
        )
        for c, v in zip(chunks, vectors, strict=True)
    ]
    store.upsert(_COLL, embedded)
    return RetrievalFacade(emb, store, _COLL, default_k=5)


class _RealFusedRunner:
    """A real fused runner over the in-memory facade (the composition vehicle, mocked offline)."""

    def __init__(self, settings, facade):
        self._settings = settings
        self._facade = facade

    def run_fused(self, suite, ks=(1, 3, 5, 10)):
        report = run_fused_evaluation(
            self._facade, suite, ks, self._settings.eval_fusion_k
        )
        baseline = baseline_io.load_fused_baseline(
            self._settings.eval_dir / "baseline.toml"
        )
        verdict = compare_fused_to_baseline(
            report, baseline, self._settings.eval_tolerance
        )
        return report, verdict


@pytest.fixture
def wired(tmp_path, monkeypatch):
    eval_dir = tmp_path / "eval"
    settings = Settings(
        eval_dir=eval_dir, corpus="default", embed_provider="hash", index_dir=tmp_path
    )
    facade = _build_facade()

    indexed = frozenset({_DOC_PATH, _CODE_PATH})
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, e=".env": settings))
    monkeypatch.setattr(cli, "build_fused_eval_runner", lambda s: _RealFusedRunner(s, facade))
    monkeypatch.setattr(cli, "build_indexed_docs", lambda s: indexed)
    return settings, eval_dir


def _seed_fused_suite(eval_dir):
    add_case(eval_dir / "suite.toml", EvalCase(_CODE_TEXT, (_CODE_PATH,), "nl", "code"))
    add_case(eval_dir / "suite.toml", EvalCase(_DOC_TEXT, (_DOC_PATH,), "nl", "doc"))
    add_case(
        eval_dir / "suite.toml",
        EvalCase("fuse doc and code", (_DOC_PATH, _CODE_PATH), "nl", "both"),
    )


def test_fused_run_succeeds_with_coverage(wired, capsys):
    _settings, eval_dir = wired
    _seed_fused_suite(eval_dir)
    code = cli.main(["eval", "run", "--fused"])
    out = capsys.readouterr().out
    assert code == 0
    assert "fusion coverage" in out


def test_record_baseline_writes_fused_section_preserving_ir(wired, capsys):
    _settings, eval_dir = wired
    _seed_fused_suite(eval_dir)
    # an IR baseline pre-exists; the fused record must not touch it
    from sertor_core.services.eval.models import Baseline

    baseline_io.write_baseline(
        eval_dir / "baseline.toml",
        Baseline({1: 0.5}, 0.83, 1, "hash", baseline_io.now_iso_utc()),
    )
    code = cli.main(["eval", "run", "--fused", "--record-baseline"])
    assert code == 0
    assert baseline_io.load_fused_baseline(eval_dir / "baseline.toml") is not None
    assert baseline_io.load_baseline(eval_dir / "baseline.toml").mrr == 0.83  # IR untouched


def test_gate_fails_on_degraded_run(wired, capsys):
    _settings, eval_dir = wired
    # First record a clean baseline on the full suite (coverage 1.0).
    _seed_fused_suite(eval_dir)
    assert cli.main(["eval", "run", "--fused", "--record-baseline"]) == 0
    capsys.readouterr()
    # Then DEGRADE: add a `both` case whose expected paths are absent → never covered →
    # fusion coverage drops below the recorded baseline → gate fails at tolerance 0.0.
    add_case(
        eval_dir / "suite.toml",
        EvalCase("absent both query", ("requirements/absent.md", "src/absent.py"), "nl", "both"),
    )
    code = cli.main(["eval", "run", "--fused"])
    err = capsys.readouterr().err
    assert code == 1
    assert "gate FAILED" in err


def test_high_tolerance_passes(wired, monkeypatch, capsys):
    import dataclasses

    settings, eval_dir = wired
    _seed_fused_suite(eval_dir)
    assert cli.main(["eval", "run", "--fused", "--record-baseline"]) == 0
    capsys.readouterr()
    # degrade the run (absent `both` case → coverage drops) but allow it with a huge tolerance
    add_case(
        eval_dir / "suite.toml",
        EvalCase("absent both query", ("requirements/absent.md", "src/absent.py"), "nl", "both"),
    )
    tolerant = dataclasses.replace(settings, eval_tolerance=1.0)
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda c, e=".env": tolerant))
    monkeypatch.setattr(
        cli, "build_fused_eval_runner", lambda s: _RealFusedRunner(s, _build_facade())
    )
    code = cli.main(["eval", "run", "--fused"])
    assert code == 0


def test_determinism_two_runs_same_metrics(wired, capsys):
    _settings, eval_dir = wired
    _seed_fused_suite(eval_dir)
    cli.main(["eval", "run", "--fused", "--json"])
    first = json.loads(capsys.readouterr().out)
    cli.main(["eval", "run", "--fused", "--json"])
    second = json.loads(capsys.readouterr().out)
    assert first["fusion"]["coverage"] == second["fusion"]["coverage"]
    assert first["surfaces"] == second["surfaces"]


def test_no_baseline_exits_0(wired, capsys):
    _settings, eval_dir = wired
    _seed_fused_suite(eval_dir)
    assert cli.main(["eval", "run", "--fused"]) == 0


def test_plain_run_unaffected(wired, monkeypatch, capsys):
    _settings, eval_dir = wired
    _seed_fused_suite(eval_dir)

    class _IRRunner:
        def run(self, suite, ks=(1, 3, 5, 10)):
            from sertor_core.engines.evaluation import EvalReport
            return EvalReport({1: 0.5}, 0.5, len(suite.cases), "hash"), suite.kinds()

    monkeypatch.setattr(cli, "build_eval_runner", lambda s: _IRRunner())
    code = cli.main(["eval", "run"])  # no --fused
    out = capsys.readouterr().out
    assert code == 0
    assert "fusion coverage" not in out  # additivity: IR path carries no fusion


def test_add_case_intent_grows_suite_preserving_graph_case(wired, capsys):
    _settings, eval_dir = wired
    # seed a graph_case directly, then add an intent case → graph_case must survive
    from sertor_core.services.eval.models import GraphCase
    from sertor_core.services.eval.suite_io import add_graph_case, load_suite

    add_graph_case(eval_dir / "suite.toml", GraphCase("who_calls", "fuse", ("src/impl.py#fuse",)))
    code = cli.main(
        ["eval", "add-case", "--query", "Qx", "--expected", _CODE_PATH,
         "--intent", "both", "--kind", "nl", "--confirm"]
    )
    assert code == 0
    loaded = load_suite(eval_dir / "suite.toml")
    assert any(c.intent == "both" for c in loaded.cases)
    assert loaded.graph_cases  # preserved


def test_invalid_intent_in_suite_exits_1(wired, capsys):
    _settings, eval_dir = wired
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "suite.toml").write_text(
        '[[case]]\nquery = "Q"\nexpected = ["src/impl.py"]\nintent = "bogus"\n',
        encoding="utf-8",
    )
    code = cli.main(["eval", "run", "--fused"])
    assert code == 1
