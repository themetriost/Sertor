"""Vie d'ingresso deterministiche al code-graph (118, FR-022/023/023a).

Funzioni pure: nessun I/O, nessun modello linguistico. I casi che contano di più sono quelli in cui
il sistema **NON deve agganciare**: un falso ingresso costa contesto dell'agente proprio dove il
beneficio è nullo.
"""
from __future__ import annotations

import pytest

from sertor_core.services.graph_entry import (
    extract_identifiers,
    match_symbol_table,
    resolve_entry_points,
    split_qualname,
)

SYMBOLS = [
    "CachingEmbedder",
    "EmbeddingCache",
    "IndexingService",
    "build_indexer",
    "Settings.load",
]


# --- extract_identifiers -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected",
    [
        ("come funziona CachingEmbedder?", ["CachingEmbedder"]),
        ("chi chiama build_indexer?", ["build_indexer"]),
        ("cosa fa Settings.load", ["Settings.load"]),
    ],
)
def test_identifier_shaped_tokens_are_extracted(query, expected):
    assert extract_identifiers(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "come funziona la cache degli embedding?",
        "perche abbiamo scelto questo approccio",
        "cosa fa il sistema quando la query non trova nulla",
    ],
)
def test_plain_prose_yields_nothing(query):
    """Parole comuni tutte minuscole NON sono identificatori: agganciarle sarebbe rumore."""
    assert extract_identifiers(query) == []


def test_duplicates_are_collapsed_preserving_order():
    assert extract_identifiers("build_indexer poi CachingEmbedder poi build_indexer") == [
        "build_indexer",
        "CachingEmbedder",
    ]


# --- split_qualname ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "qualname, parts",
    [
        ("CachingEmbedder", {"caching", "embedder"}),
        ("build_indexer", {"build", "indexer"}),
        ("Settings.load", {"settings", "load"}),
        ("HTTPSConnection", {"https", "connection"}),
    ],
)
def test_qualnames_split_into_lowercase_parts(qualname, parts):
    assert split_qualname(qualname) == parts


# --- match_symbol_table ------------------------------------------------------------------------


def test_concept_words_overlapping_the_name_parts_match():
    """Il caso che la via 2 esiste per coprire: si nomina il concetto, non l'identificatore."""
    found = match_symbol_table("la classe che fa caching degli embedding", SYMBOLS)

    assert set(found) == {"CachingEmbedder", "EmbeddingCache"}


def test_whole_name_present_in_the_question_always_matches():
    assert "CachingEmbedder" in match_symbol_table("parlami di CachingEmbedder", SYMBOLS)


def test_single_shared_part_is_below_the_threshold():
    """«cache» tocca una parte sola: sotto soglia, e giustamente — aggancerebbe troppo."""
    assert match_symbol_table("cosa fa la cache", SYMBOLS) == []


def test_lexical_gap_is_real_and_produces_nothing():
    """Domanda in italiano, identificatori in inglese: nessun ingresso.

    È il limite DICHIARATO della via lessicale. L'esito onesto è «non tentato» a costo zero, non un
    aggancio a caso.
    """
    assert match_symbol_table("come funziona l'indicizzazione dei documenti", SYMBOLS) == []


def test_ordering_is_deterministic():
    a = match_symbol_table("caching embedding cache", SYMBOLS)
    b = match_symbol_table("caching embedding cache", SYMBOLS)

    assert a == b


def test_threshold_is_configurable():
    permissive = match_symbol_table("cosa fa la cache", SYMBOLS, min_overlap=1)

    assert set(permissive) == {"CachingEmbedder", "EmbeddingCache"}


# --- resolve_entry_points ----------------------------------------------------------------------


def test_written_identifier_wins_over_lexical_match():
    """La provenienza conservata è la PIÙ AFFIDABILE, non la prima incontrata per caso."""
    points = resolve_entry_points("come funziona CachingEmbedder col caching embedding", SYMBOLS)

    by_symbol = {p.symbol: p.source for p in points}
    assert by_symbol["CachingEmbedder"] == "extracted_from_query"


def test_cap_is_respected():
    points = resolve_entry_points(
        "caching embedding indexing service build_indexer Settings.load", SYMBOLS, max_symbols=2
    )

    assert len(points) == 2


def test_no_duplicate_symbols():
    points = resolve_entry_points("CachingEmbedder caching embedder", SYMBOLS)

    assert len({p.symbol for p in points}) == len(points)


def test_prose_without_symbols_resolves_to_nothing():
    """L'esito che rende il costo auto-correlato: nessun ingresso ⇒ grafo non toccato."""
    assert resolve_entry_points("perche abbiamo preso questa decisione", SYMBOLS) == []


def test_identifier_absent_from_the_graph_is_not_an_entry_point():
    """Un token a forma di simbolo ma sconosciuto al grafo non produce un ingresso morto."""
    points = resolve_entry_points("come funziona NonEsisteQuesto", SYMBOLS)

    assert points == []


def test_same_input_same_output():
    args = ("la classe che fa caching degli embedding", SYMBOLS)

    assert resolve_entry_points(*args) == resolve_entry_points(*args)


def test_every_entry_point_declares_a_known_source():
    points = resolve_entry_points("caching embedding e build_indexer", SYMBOLS)

    assert points
    assert all(p.source in {"extracted_from_query", "symbol_table_match"} for p in points)
