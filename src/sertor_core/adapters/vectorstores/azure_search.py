"""Vector store adapter on Azure AI Search (cloud backend, optional extra — REQ-018).

Implements the `VectorStore` port on an Azure AI Search vector index. Dependencies
(`azure-search-documents`) are an **optional extra** of the package (NFR-04) and are imported
**lazily**: the absence of the extra does not break the core import. A collection maps to an index;
the type filter acts on the `doc_type` field. Errors are wrapped in `VectorStoreError`.

Note: exercised against a real service (tests marked `cloud`); local CI uses Chroma.
"""
from __future__ import annotations

import logging

from sertor_core.domain.entities import DocType, EmbeddedChunk, RetrievalResult
from sertor_core.domain.errors import VectorStoreError
from sertor_core.observability.logging import log_event

_BACKEND = "azure_search"


def _raise_store_error(message: str, exc: Exception) -> None:
    """Emits the `store_error` event at the boundary (FR-020) and raises `VectorStoreError`."""
    reason = type(exc).__name__
    log_event(logging.ERROR, "store_error", backend=_BACKEND, reason=reason)
    raise VectorStoreError(message, backend=_BACKEND, reason=reason) from exc


def _require_sdk():
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        return SearchClient, AzureKeyCredential
    except ImportError as exc:
        raise VectorStoreError(
            "extra 'azure' not installed (pip install sertor-core[azure])",
            backend=_BACKEND,
            reason="ImportError",
        ) from exc


class AzureSearchStore:
    """`VectorStore` on Azure AI Search. A `collection` maps to an index."""

    def __init__(self, endpoint: str, api_key: str):
        if not endpoint or not api_key:
            raise VectorStoreError(
                "incomplete Azure AI Search configuration",
                backend=_BACKEND,
                reason="endpoint/api_key missing",
            )
        self._SearchClient, self._Credential = _require_sdk()
        self._endpoint = endpoint
        self._api_key = api_key

    def _client(self, collection: str):
        return self._SearchClient(
            endpoint=self._endpoint,
            index_name=collection,
            credential=self._Credential(self._api_key),
        )

    def upsert(self, collection: str, records: list[EmbeddedChunk]) -> None:
        if not records:
            return
        docs = [
            {
                "id": r.chunk_id,
                "vector": r.vector,
                "text": r.payload.get("text", ""),
                "path": r.payload.get("path", ""),
                "doc_type": r.payload.get("doc_type", "code"),
            }
            for r in records
        ]
        try:
            self._client(collection).upload_documents(documents=docs)
        except Exception as exc:
            _raise_store_error("error during upsert on Azure AI Search", exc)

    def query(
        self, collection: str, vector: list[float], k: int, doc_type: str = "both"
    ) -> list[RetrievalResult]:
        if k <= 0:
            return []
        from azure.search.documents.models import VectorizedQuery

        flt = None if doc_type == "both" else f"doc_type eq '{doc_type}'"
        try:
            res = self._client(collection).search(
                search_text=None,
                vector_queries=[
                    VectorizedQuery(vector=vector, k_nearest_neighbors=k, fields="vector")
                ],
                filter=flt,
                top=k,
            )
            return [
                RetrievalResult(
                    text=d.get("text", ""),
                    path=d.get("path", ""),
                    chunk_id=d.get("id", ""),
                    doc_type=DocType(d.get("doc_type", "code")),
                    score=float(d.get("@search.score", 0.0)),
                    metadata={"path": d.get("path", "")},
                )
                for d in res
            ]
        except Exception as exc:
            _raise_store_error("error during query on Azure AI Search", exc)
            return []  # unreachable: _raise_store_error always raises

    def delete(self, collection: str, ids: list[str]) -> None:
        if not ids:
            return
        try:
            self._client(collection).delete_documents(documents=[{"id": i} for i in ids])
        except Exception as exc:
            _raise_store_error("error during delete on Azure AI Search", exc)

    def reset(self, collection: str) -> None:
        # Rebuild-from-scratch: empty the index by deleting all documents (idempotent).
        try:
            client = self._client(collection)
            ids = [d["id"] for d in client.search(search_text="*", select=["id"], top=100000)]
            if ids:
                client.delete_documents(documents=[{"id": i} for i in ids])
        except Exception:
            return  # index absent or empty: not an error

    def exists(self, collection: str) -> bool:
        try:
            return self._client(collection).get_document_count() > 0
        except Exception:
            return False

    def list_collections(self) -> list[str]:
        from azure.search.documents.indexes import SearchIndexClient

        try:
            client = SearchIndexClient(
                endpoint=self._endpoint, credential=self._Credential(self._api_key)
            )
            return sorted(client.list_index_names())
        except Exception as exc:
            _raise_store_error("error while listing indexes on Azure AI Search", exc)
            return []  # unreachable: _raise_store_error always raises
