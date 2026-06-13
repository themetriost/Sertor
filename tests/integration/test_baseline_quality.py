"""STRICT quality tests — baseline vs hybrid on the sertor corpus ground-truth (REQ-051/052).

Former `xfail` (US4 of FEAT-002): completed by FEAT-004. Indexes `src/sertor_core/` without network
(FakeEmbedder + InMemoryStore + real BM25 lexical index): the fake dense path is ~arbitrary,
the lexical one is real — the comparison demonstrates the value of hybrid in local CI, the same
phenomenon measured by prototype 02 (MRR 0.13→0.94 with a weak embedder).

Thresholds (REQ-052): hybrid hit@5 ≥ baseline and hybrid MRR ≥ baseline; LSC-1: on the subset
of symbol queries, hybrid hit@5 ≥ baseline + 10 percentage points.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.adapters.lexical.bm25 import Bm25LexicalIndex
from sertor_core.config.settings import Settings
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.engines.evaluation import EvalReport, evaluate
from sertor_core.engines.hybrid import HybridEngine
from sertor_core.services.indexing import IndexingService
from tests.fixtures.ground_truth import relative_to
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

pytestmark = pytest.mark.integration

_CORPUS_ROOT = Path(__file__).resolve().parents[2] / "src" / "sertor_core"
_COLL = "quality-gt"
_GT = relative_to("src/sertor_core")  # paths rebased to the indexed root


@pytest.fixture(scope="module")
def engines(tmp_path_factory):
    """Indexes the core ONCE and builds both engines on the same index."""
    tmp = tmp_path_factory.mktemp("gt-index")
    settings = Settings(index_dir=tmp, corpus="quality")
    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    lexical = Bm25LexicalIndex(tmp)
    IndexingService(emb, store, _COLL, settings, lexical=lexical).index(
        _CORPUS_ROOT, rebuild=True
    )
    baseline = BaselineEngine(emb, store, _COLL, settings)
    hybrid = HybridEngine(emb, store, lexical, _COLL, settings)
    return baseline, hybrid


def _report(engine, gt) -> EvalReport:
    return evaluate(engine, [(q, paths) for q, paths, _ in gt])


def test_ground_truth_has_at_least_ten_mixed_pairs():
    # FR-023: ≥10 pairs, both kinds present.
    assert len(_GT) >= 10
    kinds = {kind for _, _, kind in _GT}
    assert kinds == {"symbol", "nl"}


def test_hybrid_meets_baseline_on_hit5_and_mrr(engines):
    baseline, hybrid = engines
    base, hyb = _report(baseline, _GT), _report(hybrid, _GT)
    # Comparative report (REQ-051) — visible with `pytest -s` or on failure.
    for name, rep in (("baseline", base), ("hybrid", hyb)):
        print(f"{name}: hit@k={rep.hit_rate} MRR@10={rep.mrr:.3f} ({rep.queries} query)")
    assert hyb.hit_rate[5] >= base.hit_rate[5]         # REQ-052: never worse than baseline
    assert hyb.mrr >= base.mrr


def test_hybrid_beats_baseline_by_10pp_on_symbol_queries(engines):
    baseline, hybrid = engines
    symbols = [(q, p, k) for q, p, k in _GT if k == "symbol"]
    base, hyb = _report(baseline, symbols), _report(hybrid, symbols)
    print(f"symbol subset: baseline hit@5={base.hit_rate[5]:.2f} "
          f"hybrid hit@5={hyb.hit_rate[5]:.2f}")
    assert hyb.hit_rate[5] >= base.hit_rate[5] + 0.10  # LSC-1/SC-001: +10 percentage points
