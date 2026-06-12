"""Test di qualità STRICT — baseline vs ibrido sul ground-truth del corpus sertor (REQ-051/052).

Ex `xfail` (US4 di FEAT-002): completato dalla FEAT-004. Indicizza `src/sertor_core/` senza rete
(FakeEmbedder + InMemoryStore + indice lessicale BM25 reale): la via densa finta è ~arbitraria,
quella lessicale è vera — il confronto dimostra il valore dell'ibrido in CI locale, lo stesso
fenomeno misurato dal prototipo 02 (MRR 0.13→0.94 con embedder debole).

Soglie (REQ-052): hit@5 ibrido ≥ baseline e MRR ibrido ≥ baseline; LSC-1: sul sottoinsieme
delle query a simbolo, hit@5 ibrido ≥ baseline + 10 punti percentuali.
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
_GT = relative_to("src/sertor_core")  # path ricondotti alla radice indicizzata


@pytest.fixture(scope="module")
def engines(tmp_path_factory):
    """Indicizza il nucleo UNA volta e costruisce i due motori sullo stesso indice."""
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
    # FR-023: ≥10 coppie, entrambe le nature presenti.
    assert len(_GT) >= 10
    kinds = {kind for _, _, kind in _GT}
    assert kinds == {"symbol", "nl"}


def test_hybrid_meets_baseline_on_hit5_and_mrr(engines):
    baseline, hybrid = engines
    base, hyb = _report(baseline, _GT), _report(hybrid, _GT)
    # Report comparativo (REQ-051) — visibile con `pytest -s` o al fallimento.
    for name, rep in (("baseline", base), ("hybrid", hyb)):
        print(f"{name}: hit@k={rep.hit_rate} MRR@10={rep.mrr:.3f} ({rep.queries} query)")
    assert hyb.hit_rate[5] >= base.hit_rate[5]         # REQ-052: mai peggio del baseline
    assert hyb.mrr >= base.mrr


def test_hybrid_beats_baseline_by_10pp_on_symbol_queries(engines):
    baseline, hybrid = engines
    symbols = [(q, p, k) for q, p, k in _GT if k == "symbol"]
    base, hyb = _report(baseline, symbols), _report(hybrid, symbols)
    print(f"symbol subset: baseline hit@5={base.hit_rate[5]:.2f} "
          f"hybrid hit@5={hyb.hit_rate[5]:.2f}")
    assert hyb.hit_rate[5] >= base.hit_rate[5] + 0.10  # LSC-1/SC-001: +10 punti percentuali
