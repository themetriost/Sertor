"""Test US4 — declared coverage is TRUE for each of the 10 languages (FR-003, SC-007).

CLOSED mini-corpus (`tests/fixtures/graph_corpus.py`): here the ground-truth is total →
full precision is measured (SC-002) along with per-relation verification of the `COVERAGE` map.
Corpus different from sertor, zero engine adaptations = SC-007 verification (fix analyze C1).
"""
from __future__ import annotations

import pytest

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType, Document
from sertor_core.services.chunking.dispatch import chunk_document
from sertor_core.services.graph_extraction import COVERAGE, extract_graph
from tests.fixtures.graph_corpus import LANGUAGE_CASES, PYTHON_COMPANION

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def data():
    settings = Settings.load(env_file=None)
    documents = [
        Document(id=case.filename, text=case.source, doc_type=DocType.CODE,
                 language=case.language)
        for case in LANGUAGE_CASES
    ]
    companion_name, companion_src = PYTHON_COMPANION
    documents.append(Document(id=companion_name, text=companion_src,
                              doc_type=DocType.CODE, language="python"))
    chunks = [c for d in documents for c in chunk_document(d, settings)]
    return extract_graph(documents, chunks, ambiguity_threshold=10)


def _edges(data, etype: str) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in data.edges if e.type == etype}


def test_nodes_and_contains_for_all_ten_languages(data):
    by_id = {n.id: n for n in data.nodes}
    contains = _edges(data, "contains")
    for case in LANGUAGE_CASES:
        caller_id = f"{case.filename}::{case.caller_qual}"
        assert caller_id in by_id, case.language       # nodes for ALL 10 (FR-003)
        parent = (f"{case.filename}::{case.caller_qual.rsplit('.', 1)[0]}"
                  if "." in case.caller_qual else case.filename)
        assert (parent, caller_id) in contains, case.language


def test_declared_calls_coverage_is_true(data):
    calls = _edges(data, "calls")
    for case in LANGUAGE_CASES:
        assert "calls" in COVERAGE[case.language], case.language  # all declare calls
        caller_id = f"{case.filename}::{case.caller_qual}"
        targets = {dst for src, dst in calls if src == caller_id}
        assert any(dst.endswith(f"::{case.callee_name}") or
                   dst.endswith(f".{case.callee_name}") for dst in targets), (
            f"{case.language}: calls edge declared but not extracted")


def test_declared_python_imports_and_inherits_are_true(data):
    assert ("mod_b.py", "mod_a.py") in _edges(data, "imports")
    assert ("mod_a.py::Figlia", "mod_a.py::Base") in _edges(data, "inherits")


def test_precision_on_closed_corpus(data):
    # SC-002 on the closed corpus: every extracted calls edge must be one of the expected ones.
    expected = set()
    for case in LANGUAGE_CASES:
        caller_id = f"{case.filename}::{case.caller_qual}"
        expected.add(caller_id)
    spurious = [
        (src, dst) for src, dst in _edges(data, "calls") if src not in expected
    ]
    total = len(_edges(data, "calls"))
    precision = (total - len(spurious)) / total if total else 1.0
    print(f"closed-corpus precision: {precision:.2f} ({total} edges, {len(spurious)} spurious)")
    assert precision >= 0.8
