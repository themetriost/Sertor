"""Test US1 — BM25 lexical adapter with JSON sidecar (FR-001/002/005/032).

All on a temporary file system, no network (NFR-03). Covers: tokenizer (snake_case sub-tokens),
build/query/exists/reset/lookup, doc_type filter BEFORE cut, namespacing per collection,
atomic write and versioned format, tie-breaking determinism.
"""
from __future__ import annotations

import json

import pytest

from sertor_core.adapters.lexical.bm25 import Bm25LexicalIndex, tokenize
from sertor_core.domain.entities import LexicalEntry
from sertor_core.domain.errors import ConfigError

COLL = "demo__fake_8"


def _entries() -> list[LexicalEntry]:
    return [
        LexicalEntry("ports.py#0", "class EmbeddingProvider(Protocol): il provider di embeddings",
                     "code", "ports.py"),
        LexicalEntry("errors.py#0", "class IndexNotFoundError(SertorError): indice inesistente",
                     "code", "errors.py"),
        LexicalEntry("composition.py#0", "def collection_name(settings, embedder): nome namespaced",
                     "code", "composition.py"),
        LexicalEntry("guida.md#0", "la guida spiega il provider di embeddings e la collection",
                     "doc", "guida.md"),
    ]


def _index(tmp_path) -> Bm25LexicalIndex:
    idx = Bm25LexicalIndex(tmp_path)
    idx.build(COLL, _entries())
    return idx


# --- tokenizer (FR-001) -------------------------------------------------------------------------

def test_tokenize_preserves_identifiers_and_splits_snake_case():
    toks = tokenize("collection_name = EmbeddingProvider")
    assert "collection_name" in toks          # full identifier preserved
    assert "collection" in toks and "name" in toks  # snake_case sub-tokens
    assert "embeddingprovider" in toks        # lowercase, joined identifier


# --- build / query / exists / reset / lookup ----------------------------------------------------

def test_exact_symbol_query_ranks_defining_chunk_first(tmp_path):
    idx = _index(tmp_path)
    ids = idx.query(COLL, "IndexNotFoundError", k=3)
    assert ids and ids[0] == "errors.py#0"


def test_doc_type_filter_applies_before_cut(tmp_path):
    idx = _index(tmp_path)
    # "provider embeddings" matches both code (ports.py) and doc (guida.md): with k=1 and doc filter
    # must return the doc chunk even if code would have a higher score (research D5).
    ids = idx.query(COLL, "provider di embeddings", k=1, doc_type="doc")
    assert ids == ["guida.md#0"]


def test_k_zero_or_negative_returns_empty(tmp_path):
    idx = _index(tmp_path)
    assert idx.query(COLL, "provider", k=0) == []
    assert idx.query(COLL, "provider", k=-1) == []


def test_namespacing_isolates_collections(tmp_path):
    idx = _index(tmp_path)
    other = "altro__fake_8"
    idx.build(other, [LexicalEntry("x.py#0", "contenuto unico zeta", "code", "x.py")])
    assert idx.query(other, "zeta", k=5) == ["x.py#0"]
    assert idx.query(COLL, "zeta", k=5) == []          # never shared (FR-005)
    idx.reset(other)
    assert not idx.exists(other) and idx.exists(COLL)  # namespaced reset


def test_reset_is_idempotent(tmp_path):
    idx = _index(tmp_path)
    idx.reset(COLL)
    idx.reset(COLL)  # absent = no-op
    assert not idx.exists(COLL)


def test_lookup_returns_entries_in_order(tmp_path):
    idx = _index(tmp_path)
    got = idx.lookup(COLL, ["guida.md#0", "ports.py#0", "inesistente#0"])
    assert [e.chunk_id for e in got] == ["guida.md#0", "ports.py#0"]  # ordered, missing skipped
    assert got[0].text.startswith("la guida")


def test_build_replaces_integrally(tmp_path):
    idx = _index(tmp_path)
    idx.build(COLL, [LexicalEntry("solo.py#0", "nuovo contenuto", "code", "solo.py")])
    assert idx.query(COLL, "EmbeddingProvider", k=5) == []  # old set is gone
    assert idx.query(COLL, "nuovo contenuto", k=5) == ["solo.py#0"]


def test_empty_entries_build_valid_empty_index(tmp_path):
    idx = Bm25LexicalIndex(tmp_path)
    idx.build(COLL, [])
    assert idx.exists(COLL)
    assert idx.query(COLL, "qualunque", k=5) == []


# --- persistence: versioned and atomic sidecar (FR-032) ----------------------------------------

def test_sidecar_lives_in_lexical_dir_with_versioned_format(tmp_path):
    _index(tmp_path)
    sidecar = tmp_path / "lexical" / f"{COLL}.json"
    assert sidecar.exists()                    # in the namespaced index dir (REQ-072)
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert data["format"] == "sertor.lexical/1"
    assert data["collection"] == COLL
    assert len(data["entries"]) == 4


def test_unknown_format_raises_explicit_error(tmp_path):
    _index(tmp_path)
    sidecar = tmp_path / "lexical" / f"{COLL}.json"
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    data["format"] = "sconosciuto/9"
    sidecar.write_text(json.dumps(data), encoding="utf-8")
    fresh = Bm25LexicalIndex(tmp_path)         # no cache: forces re-read
    with pytest.raises(ConfigError):
        fresh.query(COLL, "provider", k=3)     # never silent partial parsing (Principio IV)


def test_corrupt_sidecar_raises_explicit_error(tmp_path):
    _index(tmp_path)
    (tmp_path / "lexical" / f"{COLL}.json").write_text("{ non-json", encoding="utf-8")
    fresh = Bm25LexicalIndex(tmp_path)
    with pytest.raises(ConfigError):
        fresh.query(COLL, "provider", k=3)


def test_no_tmp_leftovers_after_build(tmp_path):
    _index(tmp_path)
    leftovers = [p for p in (tmp_path / "lexical").iterdir() if p.suffix != ".json"]
    assert leftovers == []                     # atomic write: tmp+rename (Principio VI)


# --- determinism (FR-008/NFR-06) ----------------------------------------------------------------

def test_query_is_deterministic_and_ties_break_by_chunk_id(tmp_path):
    idx = Bm25LexicalIndex(tmp_path)
    idx.build(COLL, [
        LexicalEntry("b.py#0", "token raro identico", "code", "b.py"),
        LexicalEntry("a.py#0", "token raro identico", "code", "a.py"),
    ])
    first = idx.query(COLL, "token raro", k=5)
    assert first == idx.query(COLL, "token raro", k=5)   # same query → same order
    assert first == ["a.py#0", "b.py#0"]                 # tie broken by chunk_id
