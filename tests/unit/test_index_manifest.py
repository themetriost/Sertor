"""Unit tests for the index manifest store (046, FEAT-009, T018).

Exercise `classify` (mtime pre-filter + hash confirm), `apply`/`write_full` atomicity, the
schema/collection compatibility gate of `load`, the unit reconstruction, and the logic-version
invalidation. No ports needed: the manifest is a concrete SQLite store (stdlib only).
"""
from __future__ import annotations

import sqlite3

import pytest

from sertor_core.domain.entities import Chunk, ChunkerKind, ChunkMetadata, DocType, Document
from sertor_core.services.index_manifest import (
    FileStat,
    IndexManifest,
    content_hash,
)

LOGIC = "logic/v1"
COLL = "corpus__provider"


def _doc(rel: str, text: str, doc_type: DocType = DocType.CODE) -> Document:
    return Document(id=rel, text=text, doc_type=doc_type, language="python")


def _chunks(rel: str, texts: list[str]) -> list[Chunk]:
    return [
        Chunk(
            id=f"{rel}#{i}",
            document_id=rel,
            text=t,
            doc_type=DocType.CODE,
            metadata=ChunkMetadata(path=rel, chunker=ChunkerKind.SIZE_FALLBACK, language="python"),
        )
        for i, t in enumerate(texts)
    ]


def _stat(rel: str, mtime: float, text: str) -> FileStat:
    return FileStat(path=rel, mtime=mtime, read_hash=lambda: content_hash(text))


def _entry(rel: str, mtime: float, text: str):
    doc = _doc(rel, text)
    return (doc, _chunks(rel, [text]), _stat(rel, mtime, text), content_hash(text))


def _seed(manifest: IndexManifest, files: list[tuple[str, float, str]]) -> None:
    manifest.write_full(COLL, LOGIC, [_entry(rel, mtime, text) for rel, mtime, text in files])


# --------------------------------------------------------------------- load / compatibility

def test_load_returns_none_when_empty(tmp_path):
    manifest = IndexManifest(tmp_path)
    assert manifest.load(COLL) is None


def test_load_returns_state_after_write_full(tmp_path):
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    state = manifest.load(COLL)
    assert state is not None
    assert state.collection == COLL
    assert state.logic_version == LOGIC
    assert set(state.files) == {"a.py"}


def test_load_other_collection_returns_none(tmp_path):
    """A manifest written for one collection does not apply to another (provider/corpus change)."""
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    assert manifest.load("different__provider") is None


def test_load_incompatible_schema_returns_none(tmp_path):
    """Schema version mismatch → None so the caller falls back to a full (FR-011)."""
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    conn = sqlite3.connect(tmp_path / "index_manifest.sqlite")
    conn.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", ("sertor.manifest/999",))
    conn.commit()
    conn.close()
    manifest2 = IndexManifest(tmp_path)
    assert manifest2.load(COLL) is None


# --------------------------------------------------------------------- classify

def test_classify_unchanged_when_mtime_and_hash_match(tmp_path):
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    state = manifest.load(COLL)
    cl = manifest.classify(state, [_stat("a.py", 1.0, "alpha")], LOGIC)
    assert cl.unchanged == ("a.py",)
    assert not cl.has_changes()


def test_classify_unchanged_when_mtime_changed_but_hash_equal(tmp_path):
    """A touched-but-identical file (mtime moved, content same) stays UNCHANGED (FR-002)."""
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    state = manifest.load(COLL)
    cl = manifest.classify(state, [_stat("a.py", 99.0, "alpha")], LOGIC)
    assert cl.unchanged == ("a.py",)
    assert cl.modified == ()


def test_classify_modified_when_hash_differs(tmp_path):
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    state = manifest.load(COLL)
    cl = manifest.classify(state, [_stat("a.py", 2.0, "BETA")], LOGIC)
    assert cl.modified == ("a.py",)
    assert cl.unchanged == ()
    assert cl.hashes["a.py"] == content_hash("BETA")


def test_classify_new_when_absent_from_manifest(tmp_path):
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    state = manifest.load(COLL)
    cl = manifest.classify(state, [_stat("a.py", 1.0, "alpha"), _stat("b.py", 5.0, "bee")], LOGIC)
    assert cl.new == ("b.py",)
    assert cl.unchanged == ("a.py",)


def test_classify_deleted_when_gone_from_disk(tmp_path):
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha"), ("b.py", 2.0, "bee")])
    state = manifest.load(COLL)
    cl = manifest.classify(state, [_stat("a.py", 1.0, "alpha")], LOGIC)
    assert cl.deleted == ("b.py",)


def test_classify_logic_version_mismatch_is_modified(tmp_path):
    """Same content, different logic-version → MODIFIED (derived units would differ, FR-013)."""
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    state = manifest.load(COLL)
    cl = manifest.classify(state, [_stat("a.py", 1.0, "alpha")], "logic/v2")
    assert cl.modified == ("a.py",)
    assert cl.unchanged == ()


# --------------------------------------------------------------------- apply / units

def test_apply_adds_updates_removes(tmp_path):
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha"), ("b.py", 2.0, "bee")])
    manifest.apply(
        COLL,
        LOGIC,
        added=[_entry("c.py", 3.0, "gamma")],
        updated=[_entry("a.py", 4.0, "alpha2")],
        removed=["b.py"],
        reconcile_counter=1,
    )
    state = manifest.load(COLL)
    assert set(state.files) == {"a.py", "c.py"}
    assert state.files["a.py"][1] == content_hash("alpha2")
    assert state.reconcile_counter == 1


def test_apply_modified_drops_stale_chunks(tmp_path):
    """A modified file with fewer chunks must not leave stale chunk rows (prune correctness)."""
    manifest = IndexManifest(tmp_path)
    doc = _doc("a.py", "x")
    chunks3 = _chunks("a.py", ["one", "two", "three"])
    big = (doc, chunks3, _stat("a.py", 1.0, "x"), content_hash("x"))
    manifest.write_full(COLL, LOGIC, [big])
    assert len(manifest.chunk_ids_for(["a.py"])) == 3
    small_doc = _doc("a.py", "y")
    small = (small_doc, _chunks("a.py", ["only"]), _stat("a.py", 2.0, "y"), content_hash("y"))
    manifest.apply(COLL, LOGIC, added=[], updated=[small], removed=[], reconcile_counter=1)
    assert manifest.chunk_ids_for(["a.py"]) == ["a.py#0"]


def test_units_for_reconstructs_documents_and_chunks(tmp_path):
    manifest = IndexManifest(tmp_path)
    manifest.write_full(
        COLL, LOGIC,
        [(_doc("a.py", "alpha body"), _chunks("a.py", ["alpha body"]),
          _stat("a.py", 1.0, "alpha body"), content_hash("alpha body"))],
    )
    docs, chunks = manifest.units_for(["a.py"])
    assert len(docs) == 1 and docs[0].text == "alpha body"
    assert [c.id for c in chunks] == ["a.py#0"]
    assert chunks[0].metadata.language == "python"


def test_chunk_ids_for_returns_recorded_ids(tmp_path):
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    assert manifest.chunk_ids_for(["a.py"]) == ["a.py#0"]
    assert manifest.chunk_ids_for([]) == []


# --------------------------------------------------------------------- reconcile counter

def test_bump_reconcile_off_when_every_zero(tmp_path):
    manifest = IndexManifest(tmp_path)
    _seed(manifest, [("a.py", 1.0, "alpha")])
    state = manifest.load(COLL)
    assert manifest.bump_reconcile(state, 0) is False


@pytest.mark.parametrize("counter,every,expected", [(0, 3, False), (1, 3, False), (2, 3, True)])
def test_bump_reconcile_fires_on_multiple(tmp_path, counter, every, expected):
    manifest = IndexManifest(tmp_path)
    manifest.write_full(COLL, LOGIC, [_entry("a.py", 1.0, "alpha")])
    # advance the counter to `counter`
    for c in range(counter):
        manifest.apply(COLL, LOGIC, added=[], updated=[], removed=[], reconcile_counter=c + 1)
    state = manifest.load(COLL)
    assert manifest.bump_reconcile(state, every) is expected
