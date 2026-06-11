"""Adapter di vector store su Chroma (backend locale embedded, default — REQ-018/022).

Implementa la porta `VectorStore`: persistenza su file system locale, collezioni namespaced,
filtro per tipo di documento sui metadati (REQ-027, niente indici separati). Spazio di similarità
coseno. Una collezione assente fa restituire `[]` (REQ-028); un errore del backend è avvolto in
`VectorStoreError` (Principio IV, REQ-021), mai un risultato vuoto silenzioso.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sertor_core.domain.entities import DocType, EmbeddedChunk, RetrievalResult
from sertor_core.domain.errors import VectorStoreError
from sertor_core.observability.logging import log_event

_BACKEND = "chroma"
# Chiavi di metadato scalari ammesse da Chroma (no None, no sequenze).
_META_KEYS = ("path", "doc_type", "chunker", "language", "qualname", "node_type",
              "start_line", "end_line", "heading_path")


def _raise_store_error(message: str, exc: Exception) -> None:
    """Emette l'evento `store_error` al boundary (FR-020) e solleva `VectorStoreError`.

    Usato SOLO per gli errori veri del backend; l'assenza lecita della collezione (→ `[]`, REQ-028)
    NON passa di qui e non viene loggata come ERROR (sarebbe un falso positivo).
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
    """`VectorStore` su Chroma. `client` è iniettabile per i test (NFR-01)."""

    def __init__(self, persist_dir: Path | str = ".index", client=None):
        if client is not None:
            self._client = client
        else:
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=str(persist_dir))
            except Exception as exc:  # backend non inizializzabile
                _raise_store_error("impossibile inizializzare il vector store", exc)

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
            _raise_store_error("errore durante l'upsert nel vector store", exc)

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
            return []  # collezione assente/non inizializzata -> vuoto (REQ-028)

        where = None if doc_type == "both" else {"doc_type": doc_type}
        try:
            res = coll.query(query_embeddings=[vector], n_results=k, where=where)
        except Exception as exc:
            _raise_store_error("errore durante la query nel vector store", exc)
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
            _raise_store_error("errore durante la delete nel vector store", exc)

    def reset(self, collection: str) -> None:
        # Rebuild-from-scratch: elimina la collezione se esiste (idempotente: assente = no-op).
        try:
            self._client.delete_collection(name=collection)
        except Exception:
            return  # collezione assente o già eliminata: non è un errore

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
            _raise_store_error("errore durante l'elenco delle collezioni", exc)
            return []  # irraggiungibile: _raise_store_error solleva sempre (per il type checker)


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
                score=1.0 - float(distance),  # spazio coseno: similarità = 1 - distanza
                metadata=meta or None,
            )
        )
    return results
