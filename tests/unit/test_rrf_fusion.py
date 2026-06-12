"""Test US1 — fusione Reciprocal Rank Fusion (FR-006/007/008).

Funzione pura: nessun mock necessario. Copre formula `1/(c+rank)`, pareggi per chunk_id,
contributo singolo per elementi in una sola lista, taglio a k, costante `c` configurabile.
"""
from __future__ import annotations

import pytest

from sertor_core.engines.hybrid import rrf


def test_score_formula_sums_reciprocal_ranks():
    # "x" è rank 1 in entrambe le liste: score = 2/(c+1).
    fused = rrf([["x", "y"], ["x", "z"]], k=10, c=60)
    scores = dict(fused)
    assert scores["x"] == pytest.approx(2 / 61)
    assert scores["y"] == pytest.approx(1 / 62)
    assert scores["z"] == pytest.approx(1 / 62)


def test_item_in_both_lists_outranks_single_list_items():
    fused = rrf([["a", "b", "c"], ["c", "d"]], k=10)
    assert fused[0][0] == "c" or fused[0][0] == "a"
    # "c" (rank 3 + rank 1) batte "b" (solo rank 2): 1/63+1/61 > 1/62
    order = [cid for cid, _ in fused]
    assert order.index("c") < order.index("b")


def test_single_source_item_is_included_with_single_contribution():
    fused = rrf([["solo_denso"], []], k=10)
    assert dict(fused)["solo_denso"] == pytest.approx(1 / 61)


def test_ties_break_by_chunk_id():
    # "b" e "a" hanno score identico (stesso rank in liste diverse): vince l'id minore.
    fused = rrf([["b"], ["a"]], k=10)
    assert [cid for cid, _ in fused] == ["a", "b"]


def test_k_cuts_the_fused_ranking():
    fused = rrf([["a", "b", "c", "d"]], k=2)
    assert len(fused) == 2


def test_c_constant_is_configurable():
    # Con c piccolo i rank alti pesano molto di più (FR-007).
    small_c = dict(rrf([["a", "b"]], k=2, c=1))
    big_c = dict(rrf([["a", "b"]], k=2, c=1000))
    assert small_c["a"] / small_c["b"] > big_c["a"] / big_c["b"]


def test_deterministic_output():
    rankings = [["m", "n", "o"], ["o", "m", "p"]]
    assert rrf(rankings, k=4) == rrf(rankings, k=4)
