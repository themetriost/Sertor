"""Test US4 — structural ground-truth on the REAL corpus `src/sertor_core` (FR-023..025).

Extraction + build + navigation without network or embeddings (LSC-5/LSC-8). Metric
robust to churn (fix analyze U1): recall ≥80% of expected — new legitimate callers do not
break the test; full precision lives in `test_graph_languages.py` (closed corpus).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.adapters.graph.networkx_graph import NetworkxCodeGraph
from sertor_core.config.settings import Settings
from sertor_core.services.chunking.dispatch import chunk_document
from sertor_core.services.graph_extraction import extract_graph
from sertor_core.services.ingestion import discover
from tests.fixtures.graph_ground_truth import GROUND_TRUTH

pytestmark = pytest.mark.integration

_CORPUS_ROOT = Path(__file__).resolve().parents[2] / "src" / "sertor_core"
CORPUS = "graph-gt"


@pytest.fixture(scope="module")
def graph(tmp_path_factory) -> NetworkxCodeGraph:
    settings = Settings.load(env_file=None)
    documents = discover(_CORPUS_ROOT, settings)
    chunks = [c for d in documents for c in chunk_document(d, settings)]
    data = extract_graph(documents, chunks,
                         ambiguity_threshold=settings.graph_ambiguity_threshold)
    service = NetworkxCodeGraph(tmp_path_factory.mktemp("gt-graph"), CORPUS)
    service.build(CORPUS, data)
    return service


def test_definitions_are_exact(graph):
    # LSC-1: definition with correct path and line, in a single lookup.
    for truth in GROUND_TRUTH:
        hits = graph.find_symbol(truth.name)
        paths = {h.path for h in hits}
        assert truth.definition_path in paths, truth.name
        assert all(isinstance(h.line, int) and h.line >= 1 for h in hits), truth.name


def test_caller_recall_meets_threshold(graph):
    # LSC-2 (anti-churn variant, fix U1): recall ≥80% of expected callers.
    expected_total = 0
    found_total = 0
    for truth in GROUND_TRUTH:
        if not truth.expected_callers:
            continue
        found = {h.qualname for h in graph.who_calls(truth.name)}
        expected_total += len(truth.expected_callers)
        found_total += len(set(truth.expected_callers) & found)
    recall = found_total / expected_total
    print(f"caller recall: {found_total}/{expected_total} = {recall:.2f}")
    assert recall >= 0.8


def test_doc_recall_meets_threshold(graph):
    # LSC-3: recall ≥80% of expected documents that mention the symbol.
    expected_total = 0
    found_total = 0
    for truth in GROUND_TRUTH:
        if not truth.expected_docs:
            continue
        found = set(graph.related_docs(truth.name))
        expected_total += len(truth.expected_docs)
        found_total += len(set(truth.expected_docs) & found)
    recall = found_total / expected_total
    print(f"doc recall: {found_total}/{expected_total} = {recall:.2f}")
    assert recall >= 0.8


def test_get_context_bundles_real_symbol(graph):
    bundle = graph.get_context("collection_name")
    assert bundle.definitions and bundle.definitions[0].path == "composition.py"
    assert any(h.qualname == "build_facade" for h in bundle.callers)


def test_ground_truth_has_at_least_five_symbols():
    assert len(GROUND_TRUTH) >= 5                       # FR-023
    assert all("\\" not in t.definition_path for t in GROUND_TRUTH)  # POSIX paths (FR-025)
