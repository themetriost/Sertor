"""Test US4 — valutazione della pertinenza: hit-rate@k e MRR@10 (REQ-011)."""
from __future__ import annotations

from sertor_core.config.settings import Settings
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.engines.evaluation import evaluate
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

S = Settings.load(env_file=None)
COLL = "eval-coll"


def _engine(sample_repo):
    engine = BaselineEngine(FakeEmbedder(dim=8), InMemoryStore(), COLL, S)
    engine.index(sample_repo)
    return engine


def test_evaluate_reports_metrics(sample_repo):
    engine = _engine(sample_repo)
    # query = testo di un chunk noto → il suo file deve essere fra i top risultati
    gt = [("def add(a, b):\n    return a + b", ["app/calculator.py"])]
    report = evaluate(engine, gt)
    assert report.queries == 1
    assert set(report.hit_rate.keys()) == {1, 3, 5, 10}
    assert 0.0 <= report.mrr <= 1.0
    assert report.hit_rate[10] >= report.hit_rate[1]   # monotonia in k


def test_evaluate_perfect_hit_at_1():
    # match esatto come primo risultato (FakeEmbedder deterministico)
    from sertor_core.domain.entities import EmbeddedChunk

    emb = FakeEmbedder(dim=8)
    store = InMemoryStore()
    text = "contenuto unico alpha"
    store.upsert(COLL, [
        EmbeddedChunk(
            "a#0", emb.embed([text])[0],
            {"text": text, "path": "a.py", "doc_type": "code"},
        ),
        EmbeddedChunk(
            "b#0", emb.embed(["altro beta"])[0],
            {"text": "altro beta", "path": "b.py", "doc_type": "code"},
        ),
    ])
    engine = BaselineEngine(emb, store, COLL, S)
    report = evaluate(engine, [(text, ["a.py"])])
    assert report.hit_rate[1] == 1.0
    assert report.mrr == 1.0


def test_evaluate_empty_ground_truth_is_zero(sample_repo):
    engine = _engine(sample_repo)
    report = evaluate(engine, [])
    assert report.queries == 0
    assert report.mrr == 0.0
    assert all(v == 0.0 for v in report.hit_rate.values())   # nessun errore su input vuoto
