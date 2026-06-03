"""Adapter di vector store su Azure AI Search (backend cloud, extra opzionale — REQ-018).

Implementa la porta `VectorStore` su un vector index di Azure AI Search. Le dipendenze
(`azure-search-documents`) sono un **extra opzionale** del pacchetto (NFR-04) e vengono importate
**lazy**: l'assenza dell'extra non rompe l'import del core. Una collezione corrisponde a un index;
il filtro per tipo agisce sul campo `doc_type`. Gli errori sono avvolti in `VectorStoreError`.

Nota: esercitato contro un servizio reale (test marcati `cloud`); la CI locale usa Chroma.
"""
from __future__ import annotations

from sertor_core.domain.entities import DocType, EmbeddedChunk, RetrievalResult
from sertor_core.domain.errors import VectorStoreError

_BACKEND = "azure_search"


def _require_sdk():
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient

        return SearchClient, AzureKeyCredential
    except ImportError as exc:
        raise VectorStoreError(
            "extra 'azure' non installato (pip install sertor-core[azure])",
            backend=_BACKEND,
            reason="ImportError",
        ) from exc


class AzureSearchStore:
    """`VectorStore` su Azure AI Search. Una `collection` mappa su un index."""

    def __init__(self, endpoint: str, api_key: str):
        if not endpoint or not api_key:
            raise VectorStoreError(
                "configurazione Azure AI Search incompleta",
                backend=_BACKEND,
                reason="endpoint/api_key mancanti",
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
            raise VectorStoreError(
                "errore durante l'upsert su Azure AI Search",
                backend=_BACKEND,
                reason=type(exc).__name__,
            ) from exc

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
            raise VectorStoreError(
                "errore durante la query su Azure AI Search",
                backend=_BACKEND,
                reason=type(exc).__name__,
            ) from exc

    def delete(self, collection: str, ids: list[str]) -> None:
        if not ids:
            return
        try:
            self._client(collection).delete_documents(documents=[{"id": i} for i in ids])
        except Exception as exc:
            raise VectorStoreError(
                "errore durante la delete su Azure AI Search",
                backend=_BACKEND,
                reason=type(exc).__name__,
            ) from exc

    def reset(self, collection: str) -> None:
        # Rebuild-from-scratch: svuota l'index eliminando tutti i documenti (idempotente).
        try:
            client = self._client(collection)
            ids = [d["id"] for d in client.search(search_text="*", select=["id"], top=100000)]
            if ids:
                client.delete_documents(documents=[{"id": i} for i in ids])
        except Exception:
            return  # index assente o vuoto: non è un errore

    def exists(self, collection: str) -> bool:
        try:
            return self._client(collection).get_document_count() > 0
        except Exception:
            return False
