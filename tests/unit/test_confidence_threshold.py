"""Test 018 US2 — confidence signal: score threshold + abstention (REQ-H1/H2).

Offline F.I.R.S.T. (in-memory store doubles with controlled scores). Covers SC-003/004/005/006
and FR-010..015. The threshold is a cosine-similarity threshold; below-threshold results are
excluded and, when that empties the set, a structured `low_confidence` event is emitted.
"""
from __future__ import annotations

import logging

import pytest

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType, RetrievalResult
from sertor_core.domain.errors import IndexNotFoundError
from sertor_core.engines.baseline import BaselineEngine
from sertor_core.engines.hybrid import HybridEngine
from sertor_core.services.retrieval import RetrievalFacade, apply_min_score
from tests.fixtures.mocks import FakeEmbedder, InMemoryLexicalIndex


def _r(score: float, cid: str = "c#0", doc_type: DocType = DocType.CODE) -> RetrievalResult:
    return RetrievalResult(text="t", path="p.py", chunk_id=cid, doc_type=doc_type, score=score)


class _ScoreStore:
    """Vector store double returning preset results with explicit scores."""

    def __init__(self, results: list[RetrievalResult], *, exists: bool = True):
        self._results = results
        self._exists = exists

    def exists(self, collection: str) -> bool:
        return self._exists

    def query(self, collection, vector, k, doc_type="both"):
        return list(self._results)[: max(0, k)]

    def list_collections(self):
        return ["main__fake", "other__fake"]


# --- apply_min_score (pure) ------------------------------------------------------------------

def test_apply_min_score_none_is_passthrough():
    items = [_r(0.1), _r(0.9)]
    out, low = apply_min_score(items, None)
    assert out == items and low is False        # FR-013: disabled = no change


def test_apply_min_score_filters_below_threshold():
    out, low = apply_min_score([_r(0.9, "a"), _r(0.2, "b")], 0.5)
    assert [r.chunk_id for r in out] == ["a"] and low is False


def test_apply_min_score_low_confidence_when_all_below():
    out, low = apply_min_score([_r(0.2, "a"), _r(0.1, "b")], 0.5)
    assert out == [] and low is True            # candidates existed, none passed (FR-011)


def test_apply_min_score_empty_input_not_low():
    out, low = apply_min_score([], 0.5)
    assert out == [] and low is False           # no candidates ≠ low confidence


# --- facade ----------------------------------------------------------------------------------

def _facade(results, *, min_score, extra=None):
    return RetrievalFacade(
        FakeEmbedder(), _ScoreStore(results), "main__fake",
        extra_collections=extra, min_score=min_score,
    )


def test_facade_in_domain_returns_results():
    facade = _facade([_r(0.8, "a"), _r(0.7, "b")], min_score=0.5)
    assert [r.chunk_id for r in facade.search_code("q")] == ["a", "b"]


def test_facade_out_of_domain_returns_empty_and_logs(caplog):
    facade = _facade([_r(0.3, "a"), _r(0.1, "b")], min_score=0.5)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        out = facade.search_code("q")
    assert out == []                            # SC-003: no spurious context
    assert "low_confidence" in caplog.text


def test_facade_no_threshold_is_regression(caplog):
    facade = _facade([_r(0.3, "a"), _r(0.1, "b")], min_score=None)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        out = facade.search_code("q")
    assert [r.chunk_id for r in out] == ["a", "b"]   # SC-004: identical to today
    assert "low_confidence" not in caplog.text


def test_facade_multi_collection_applies_threshold(caplog):
    facade = _facade([_r(0.2, "a")], min_score=0.5, extra={"other": "other__fake"})
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        out = facade.search_combined("q")
    assert out == []
    assert "low_confidence" in caplog.text


# --- baseline engine -------------------------------------------------------------------------

def _settings(min_score):
    return Settings(retrieval_min_score=min_score)


def test_baseline_filters_on_existing_index(caplog):
    engine = BaselineEngine(
        FakeEmbedder(), _ScoreStore([_r(0.2, "a")]), "main__fake", _settings(0.5)
    )
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        assert engine.query("q") == []
    assert "low_confidence" in caplog.text


def test_baseline_strict_policy_unchanged():
    # FR-015: a missing index still raises IndexNotFoundError (threshold is a result filter only).
    engine = BaselineEngine(
        FakeEmbedder(), _ScoreStore([], exists=False), "main__fake", _settings(0.5)
    )
    with pytest.raises(IndexNotFoundError):
        engine.query("q")


def test_baseline_no_threshold_regression():
    engine = BaselineEngine(
        FakeEmbedder(), _ScoreStore([_r(0.2, "a")]), "main__fake", _settings(None)
    )
    assert [r.chunk_id for r in engine.query("q")] == ["a"]


# --- hybrid engine ---------------------------------------------------------------------------

def _hybrid(dense, *, min_score, lexical_entries=None):
    lex = InMemoryLexicalIndex()
    from sertor_core.domain.entities import LexicalEntry
    entries = lexical_entries if lexical_entries is not None else [
        LexicalEntry(chunk_id=r.chunk_id, text=r.text, doc_type=str(r.doc_type), path=r.path)
        for r in dense
    ]
    lex.build("main__fake", entries)
    return HybridEngine(
        FakeEmbedder(), _ScoreStore(dense), lex, "main__fake", _settings(min_score)
    )


def test_hybrid_abstains_when_dense_leg_below_threshold(caplog):
    engine = _hybrid([_r(0.2, "a"), _r(0.1, "b")], min_score=0.5)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        assert engine.retrieve("zzz", 5, "both") == []   # dense gate empties → abstain (D4)
    assert "low_confidence" in caplog.text


def test_hybrid_keeps_strong_dense_hits():
    # Dense filtered to the strong hit; lexical returns nothing for "zzz" → only the strong hit.
    engine = _hybrid([_r(0.9, "hi#0"), _r(0.1, "lo#0")], min_score=0.5)
    out = engine.retrieve("zzz", 5, "both")
    assert [r.chunk_id for r in out] == ["hi#0"]


def test_hybrid_no_threshold_regression():
    engine = _hybrid([_r(0.2, "a"), _r(0.1, "b")], min_score=None)
    out = engine.retrieve("zzz", 5, "both")
    assert {r.chunk_id for r in out} == {"a", "b"}        # SC-004: nothing filtered
