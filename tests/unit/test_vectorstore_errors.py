"""Test US4 — errori di backend del vector store (REQ-021): mai vuoto silenzioso."""
from __future__ import annotations

import pytest

from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.domain.entities import EmbeddedChunk
from sertor_core.domain.errors import VectorStoreError


class _BoomClient:
    """Client stub che fallisce: simula un backend non disponibile."""

    def get_or_create_collection(self, **_):
        raise RuntimeError("backend down")

    def get_collection(self, **_):
        raise RuntimeError("backend down")


def test_upsert_raises_vector_store_error_on_backend_failure():
    store = ChromaStore(client=_BoomClient())
    rec = EmbeddedChunk(chunk_id="a#0", vector=[1.0], payload={"text": "a", "doc_type": "code"})
    with pytest.raises(VectorStoreError) as ei:
        store.upsert("c", [rec])
    assert ei.value.backend == "chroma"


def test_query_on_missing_collection_is_empty_not_error():
    # get_collection che fallisce con 'assente' -> [] (non un errore di backend) (REQ-028)
    store = ChromaStore(client=_BoomClient())
    assert store.query("c", [1.0], k=3) == []


def test_init_failure_raises_vector_store_error(tmp_path):
    # Forza un fallimento di inizializzazione passando un path non valido (un file, non una dir).
    bad = tmp_path / "afile"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(VectorStoreError):
        ChromaStore(persist_dir=bad)
