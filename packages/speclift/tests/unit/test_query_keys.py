"""Helper condiviso `build_identifier_queries` (G6): stessa regola per entrambi gli adapter
`EvidenceLocator` (CLI-vehicle e agente/MCP) — vedi `domain/query_keys.py`.
"""

from __future__ import annotations

from speclift.domain.query_keys import build_identifier_queries


def test_dedups_and_filters_empty():
    queries = build_identifier_queries(["a", "", "b", "a"], "", max_queries=10)
    assert queries == ["a", "b"]


def test_cap_respected():
    queries = build_identifier_queries(["a", "b", "c", "d"], "", max_queries=2)
    assert queries == ["a", "b"]


def test_no_fallback_for_non_identifier_snippet():
    assert build_identifier_queries([], "# just a comment line", max_queries=4) == []


def test_fallback_to_single_identifier_snippet_line():
    assert build_identifier_queries([], "helper", max_queries=4) == ["helper"]


def test_no_fallback_when_identifiers_present():
    queries = build_identifier_queries(["foo"], "not an identifier line", max_queries=4)
    assert queries == ["foo"]
