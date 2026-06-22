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


def _raise_store_error(message: str, exc: Exception) -> None:
    """Emits the `store_error` event at the boundary (FR-020) and raises `VectorStoreError`.

    Used ONLY for genuine backend errors; a legitimately absent collection (→ `[]`, REQ-028)
    does NOT go through here and is not logged as ERROR (that would be a false positive).
    """
    reason = type(exc).__name__
    log_event(logging.ERROR, "store_error", backend=_BACKEND, reason=reason)
    raise VectorStoreError(message, backend=_BACKEND, reason=reason) from exc


def _clean_metadata(payload: dict) -> dict:
    """Scalar metadata Chroma accepts, DERIVED from the payload (not a corpus-specific allow-list).

    Keeps every scalar value (str/int/float/bool), joins sequences with "/", and drops `None`/empty,
    the `text` field (it is the document — not duplicated into metadata) and any non-scalar value.
    Generic by design: the store must not hardcode one consumer's keys. The corpus payload yields
    exactly its former keys (path/doc_type/chunker/… — `_payload` carries only `text` + those), so
    corpus behaviour is unchanged; the conversation-memory payload (session_key/turn_index/
    captured_at/role) now round-trips too, instead of collapsing to `{}` which Chroma rejects with a
    `ValueError` (FEAT-004 fix — the old allow-list silently dropped every memory key).
    """
    meta: dict = {}
    for k, v in payload.items():
        if k == "text" or v is None or v == "" or v == ():
            continue
        if isinstance(v, (list, tuple)):
            meta[k] = "/".join(str(x) for x in v)
        elif isinstance(v, (str, int, float)):  # bool is an int subclass → accepted
            meta[k] = v
    return meta


class ChromaStore:
    """`VectorStore` on Chroma. `client` is injectable for tests (NFR-01)."""

    def __init__(self, persist_dir: Path | str = ".index", client=None, client_factory=None):
        # An OWNED client (default, or an injected `client_factory`) can be recreated to recover
        # from a store rewritten under a long-lived handle (see `query`). A bare injected `client`
        # (tests) is NOT refreshable: `_client_factory` stays None and a query failure just raises.
        self._persist_dir = Path(persist_dir)
        self._client_factory = client_factory
        if client_factory is not None:
            self._client = client_factory()
        elif client is not None:
            self._client = client
        else:
            self._client_factory = self._default_client_factory
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=str(persist_dir))
            except Exception as exc:  # backend cannot be initialised
                _raise_store_error("unable to initialise vector store", exc)

    def _default_client_factory(self):
        """Fresh Chroma client with the shared system cache cleared (new SQLite connection).

        Clearing the cache is the part that actually picks up a store rewritten on disk: recreating
        only the client wrapper would reuse the cached (stale) System/connection.
        """
        import chromadb
        from chromadb.api.shared_system_client import SharedSystemClient

        SharedSystemClient.clear_system_cache()
        return chromadb.PersistentClient(path=str(self._persist_dir))

    def _refresh_and_get(self, collection: str):
        """Recreate an OWNED client and return a fresh collection handle, or None if not possible.

        None for an injected (non-refreshable) client or a failed refresh → the caller surfaces the
        original error. The recreation is observable (`store_client_refreshed`).
        """
        if self._client_factory is None:
            return None
        try:
            self._client = self._client_factory()
            coll = self._client.get_collection(name=collection)
        except Exception:
            return None
        log_event(
            logging.WARNING, "store_client_refreshed", backend=_BACKEND,
            note="recreated client after query failure (store may have been rewritten on disk)",
        )
        return coll

    def _max_batch_size(self) -> int:
        """Records-per-upsert cap imposed by the Chroma backend.

        Chroma rejects a single upsert larger than its max batch size; the limit is read from the
        client when available and falls back conservatively. Keeps the rebuild correct as the corpus
        grows past the cap (a real defect surfaced by dogfooding once the corpus crossed ~5.5k
        chunks).
        """
        getter = getattr(self._client, "get_max_batch_size", None)
        if callable(getter):
            try:
                size = int(getter())
                if size > 0:
                    return size
            except Exception:
                pass
        size = getattr(self._client, "max_batch_size", None)
        try:
            return int(size) if size and int(size) > 0 else 5000
        except Exception:
            return 5000

    def upsert(self, collection: str, records: list[EmbeddedChunk]) -> None:
        if not records:
            return
        try:
            coll = self._client.get_or_create_collection(
                name=collection, metadata={"hnsw:space": "cosine"}
            )
            # Upsert in batches under the backend cap (Chroma rejects oversized single upserts).
            batch_size = self._max_batch_size()
            for start in range(0, len(records), batch_size):
                window = records[start:start + batch_size]
                coll.upsert(
                    ids=[r.chunk_id for r in window],
                    embeddings=[r.vector for r in window],
                    documents=[r.payload.get("text", "") for r in window],
                    metadatas=[_clean_metadata(r.payload) for r in window],
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
            # A query that fails on a collection we just fetched can mean the persisted store was
            # rewritten under this long-lived client (e.g. a re-index by another process): the stale
            # handle throws `InternalError` on the metadata filter while plain vector queries still
            # succeed (surfaced by dogfooding 2026-06-19). Recreate an owned client and retry ONCE
            # before surfacing the error; an injected (test) client is not refreshable.
            coll = self._refresh_and_get(collection)
            if coll is None:
                _raise_store_error("error during vector store query", exc)
            try:
                res = coll.query(query_embeddings=[vector], n_results=k, where=where)
            except Exception as exc2:
                _raise_store_error("error during vector store query", exc2)
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

    def contains_ids(self, collection: str, ids: list[str]) -> list[str]:
        """Return the subset of `ids` already present in `collection` (incrementality probe).

        Optional capability (not on the `VectorStore` port — Principio III) used by the memory
        semantic index to skip already-embedded turns (FEAT-004, NFR-009/REQ-030). Collection
        absent or no ids → `[]` (nothing indexed yet, every unit looks new). A real backend failure
        raises `VectorStoreError` so the caller can count it and degrade non-fatally.
        """
        if not ids:
            return []
        try:
            coll = self._client.get_collection(name=collection)
        except Exception:
            return []  # collection absent: nothing indexed yet
        try:
            res = coll.get(ids=ids)
        except Exception as exc:
            _raise_store_error("error during vector store id lookup", exc)
        return list(res.get("ids") or [])  # Chroma returns only the ids that exist

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
