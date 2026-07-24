"""Invarianti delle entità del contesto reso all'agente (118, FR-025..031).

La proprietà che questi test difendono: **lo stato non può mentire sui propri sotto-stati**. È il
motivo per cui `GraphBranch.status` è una property derivata e non un campo — un campo impostabile a
mano può divergere dal riassunto che dovrebbe fare, e quel giorno l'agente riceve un'informazione
falsa presentata come fondata.

Entità pure: nessun I/O.
"""
from __future__ import annotations

from sertor_core.domain.agent_context import (
    EntryPoint,
    GraphBranch,
    RelationBlock,
    SymbolContext,
)
from sertor_core.domain.entities import SymbolHit


def _hit(name: str = "X") -> SymbolHit:
    return SymbolHit(path="a.py", line=1, kind="class", qualname=name, ref=f"a.py#{name}")


def _entry(name: str = "X") -> EntryPoint:
    return EntryPoint(symbol=name, source="extracted_from_query")


# --- RelationBlock -------------------------------------------------------------------------------


def test_block_with_items_is_ok():
    block = RelationBlock.of((_hit(),), total=1)

    assert block.status == "ok"
    assert block.shown == 1
    assert not block.truncated


def test_block_without_items_is_empty_and_has_no_reason():
    """`empty` è una conclusione LEGITTIMA di assenza, non un guasto: niente causa."""
    block = RelationBlock.of((), total=0)

    assert block.status == "empty"
    assert block.reason is None


def test_unavailable_always_carries_a_reason():
    """Un'indisponibilità senza causa è un vuoto muto — esattamente ciò che FR-027 vieta."""
    block = RelationBlock.unavailable("graph_not_built")

    assert block.status == "unavailable"
    assert block.reason == "graph_not_built"


def test_shown_always_matches_the_items():
    block = RelationBlock.of((_hit("A"), _hit("B")), total=9)

    assert block.shown == len(block.items) == 2


def test_truncated_is_derived_from_shown_versus_total():
    assert RelationBlock.of((_hit(),), total=47).truncated
    assert not RelationBlock.of((_hit(),), total=1).truncated


# --- GraphBranch: lo stato derivato --------------------------------------------------------------


def test_unavailable_wins_over_everything():
    branch = GraphBranch.unavailable("navigation_library_missing", entry_points=(_entry(),))

    assert branch.status == "unavailable"


def test_no_entry_points_means_not_attempted():
    assert GraphBranch.not_attempted().status == "not_attempted"


def test_all_blocks_ok_means_ok():
    symbol = SymbolContext(
        qualname="X",
        definitions=RelationBlock.of((_hit(),), total=1),
        callers=RelationBlock.of((_hit("C"),), total=1),
        callees=RelationBlock.of((_hit("D"),), total=1),
        docs=RelationBlock.of((_hit("E"),), total=1),
    )
    branch = GraphBranch(entry_points=(_entry(),), symbols=(symbol,))

    assert branch.status == "ok"


def test_one_non_ok_block_makes_the_whole_partial():
    """Il caso misto è la NORMA: un blocco riuscito e uno no non possono collassare in «ok»."""
    symbol = SymbolContext(
        qualname="X",
        definitions=RelationBlock.of((_hit(),), total=1),
        callers=RelationBlock.of((), total=0),          # empty
        callees=RelationBlock.unavailable("graph_artifact_unusable"),
        docs=RelationBlock.of((_hit("E"),), total=1),
    )
    branch = GraphBranch(entry_points=(_entry(),), symbols=(symbol,))

    assert branch.status == "partial"


def test_not_attempted_if_and_only_if_no_entry_points():
    """FR-029, vera per COSTRUZIONE: non essendoci un campo, non può divergere dai sotto-stati."""
    without = GraphBranch()
    with_entries = GraphBranch(entry_points=(_entry(),), symbols=())

    assert (without.status == "not_attempted") is (without.entry_points == ())
    assert (with_entries.status == "not_attempted") is (with_entries.entry_points == ())


def test_status_cannot_be_set_by_hand():
    """La property è di sola lettura: nessuno dichiara uno stato che i blocchi contraddicono."""
    import pytest

    branch = GraphBranch()
    with pytest.raises(AttributeError):
        branch.status = "ok"  # type: ignore[misc]


def test_entry_points_survive_an_unavailable_graph():
    """Distinguere «non sapevo cosa cercare» da «sapevo cosa cercare ma lo strumento è rotto»."""
    branch = GraphBranch.unavailable("graph_not_built", entry_points=(_entry("CachingEmbedder"),))

    assert branch.entry_points[0].symbol == "CachingEmbedder"
    assert branch.status == "unavailable"


def test_every_entry_point_declares_its_provenance():
    entry = _entry()

    assert entry.source in {"extracted_from_query", "symbol_table_match"}
