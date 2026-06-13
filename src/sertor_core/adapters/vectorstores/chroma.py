"""Vector store adapter on Chroma (local embedded backend, default — REQ-018/022).

Implements the `VectorStore` port: persistence on the local file system, namespaced collections,
document-type filtering on metadata (REQ-027, no separate indexes). Cosine similarity space.
A missing collection returns `[]` (REQ-028); a backend error is wrapped in
`VectorStoreError` (Principle IV, REQ-021), never a silent empty result.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sertor_core.domain.entities import DocType, EmbeddedChunk, RetrievalResult
from sertor_core.domain.errors import VectorStoreError
from sertor_core.observability.logging import log_event

_BACKEND = "chroma"
# Scalar metadata keys accepted by Chroma (no None, no sequences).
_META_KEYS = ("path", "doc_type", "chunker", "language", "qualname", "node_type",
              "start_line", "end_line", "heading_path")


def _raise_store_error(message: str, exc: Exception) -> None:
    """Emits the `store_error` event at the boundary (FR-020) and raises `VectorStoreError`.

    Used ONLY for genuine backend errors; a legitimately absent collection (→ `[]`, REQ-028)
    does NOT go through here and is not logged as ERROR (that would be a false positive).
    """
    reason = type(exc).__name__
    log_event(logging.ERROR, "store_error", backend=_BACKEND, reason=reason)
    raise VectorStoreError(message, backend=_BACKEND, reason=reason) from exc


def _clean_metadata(payload: dict) -> dict:
    meta = {}
    for k in _META_KEYS:
        v = payload.get(k)
        if v is None or v == "" or v == ():
            continue
        meta[k] = "/".join(v) if isinstance(v, (list, tuple)) else v
    return meta


class ChromaStore:
    """`VectorStore` on Chroma. `client` is injectable for tests (NFR-01)."""

    def __init__(self, persist_dir: Path | str = ".index", client=None):
        if client is not None:
            self._client = client
        else:
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=str(persist_dir))
            except Exception as exc:  # backend cannot be initialised
                _raise_store_error("unable to initialise vector store", exc)

    def upsert(self, collection: str, records: list[EmbeddedChunk]) -> None:
        if not records:
            return
        try:
            coll = self._client.get_or_create_collection(
                name=collection, metadata={"hnsw:space": "cosine"}
            )
            coll.upsert(
                ids=[r.chunk_id for r in records],
                embeddings=[r.vector for r in records],
                documents=[r.payload.get("text", "") for r in records],
                metadatas=[_clean_metadata(r.payload) for r in records],
            )
        except Exception as exc:
            _raise_store_error("error during vector store upsert", exc)

    def query(
        self, collection: str, vector: list[float], k: int, doc_type: str = "both"
    ) -> list[RetrievalResult]:
        if k <= 0:
            return []
        try:
            coll = self._client.get_collection(name=collection)
        except VectorStoreError:
            raise
        except Exception:
            return []  # collection absent/not initialised -> empty (REQ-028)

        where = None if doc_type == "both" else {"doc_type": doc_type}
        try:
            res = coll.query(query_embeddings=[vector], n_results=k, where=where)
        except Exception as exc:
            _raise_store_error("error during vector store query", exc)
        return _to_results(res)

    def delete(self, collection: str, ids: list[str]) -> None:
        if not ids:
            return
        try:
            coll = self._client.get_collection(name=collection)
        except Exception:
            return
        try:
            coll.delete(ids=ids)
        except Exception as exc:
            _raise_store_error("error during vector store delete", exc)

    def reset(self, collection: str) -> None:
        # Rebuild-from-scratch: delete the collection if it exists (idempotent: absent = no-op).
        try:
            self._client.delete_collection(name=collection)
        except Exception:
            return  # collection absent or already deleted: not an error

    def exists(self, collection: str) -> bool:
        try:
            coll = self._client.get_collection(name=collection)
        except Exception:
            return False
        try:
            return coll.count() > 0
        except Exception:
            return False

    def list_collections(self) -> list[str]:
        try:
            return sorted(c.name for c in self._client.list_collections())
        except Exception as exc:
            _raise_store_error("error while listing collections", exc)
            return []  # unreachable: _raise_store_error always raises (for the type checker)


def _to_results(res: dict) -> list[RetrievalResult]:
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    results: list[RetrievalResult] = []
    for i, cid in enumerate(ids):
        meta = metas[i] if i < len(metas) and metas[i] else {}
        distance = dists[i] if i < len(dists) else 0.0
        results.append(
            RetrievalResult(
                text=docs[i] if i < len(docs) else "",
                path=meta.get("path", ""),
                chunk_id=cid,
                doc_type=DocType(meta.get("doc_type", "code")),
                score=1.0 - float(distance),  # cosine space: similarity = 1 - distance
                metadata=meta or None,
            )
        )
    return results
