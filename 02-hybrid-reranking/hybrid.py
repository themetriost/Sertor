"""Hybrid retrieval: dense (Chroma) + sparse (BM25) fusi con Reciprocal Rank Fusion.

Riusa le collection indicizzate dalla Tappa 1 (`01-baseline/.index`). BM25 è costruito
sui documenti della collection con un tokenizer che preserva gli identificatori (utile
per le query a simboli esatti del codice).

Uso:
    python 02-hybrid-reranking/hybrid.py "OAuth2PasswordBearer" --provider ollama --mode hybrid -k 5
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import chromadb  # noqa: E402
from rank_bm25 import BM25Okapi  # noqa: E402

from shared.config import settings  # noqa: E402
from shared.embeddings import get_embedder  # noqa: E402

_WORD = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    """Token lowercase; per gli snake_case aggiunge anche i sotto-token."""
    out: list[str] = []
    for w in _WORD.findall(text.lower()):
        out.append(w)
        if "_" in w:
            out.extend(p for p in w.split("_") if p)
    return out


def rrf(rankings: list[list[str]], k: int = 10, c: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (c + rank)
    return [i for i, _ in sorted(scores.items(), key=lambda x: -x[1])[:k]]


def collection_name(provider: str) -> str:
    return "baseline_" + provider.replace("-", "_")


class HybridIndex:
    def __init__(self, provider: str = "ollama"):
        self.provider = provider
        client = chromadb.PersistentClient(path=str(settings.index_dir))
        self.coll = client.get_collection(collection_name(provider))
        data = self.coll.get(include=["documents", "metadatas"])
        self.ids = data["ids"]
        self.by_id = {i: (d, m) for i, d, m in zip(self.ids, data["documents"], data["metadatas"])}
        self._bm25 = BM25Okapi([tokenize(d) for d in data["documents"]])
        self.embedder = get_embedder(provider)

    def dense_rank(self, query: str, k: int, source: str | None = None) -> list[str]:
        qv = self.embedder.embed_one(query)
        kw = {"where": {"source": source}} if source else {}
        return self.coll.query(query_embeddings=[qv], n_results=k, **kw)["ids"][0]

    def sparse_rank(self, query: str, k: int, source: str | None = None) -> list[str]:
        scores = self._bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        ids = [self.ids[i] for i in order]
        if source:
            ids = [i for i in ids if self.by_id[i][1].get("source") == source]
        return ids[:k]

    def search(self, query: str, k: int = 10, pool: int = 30, mode: str = "hybrid",
               source: str | None = None) -> list[dict]:
        """`source` opzionale (`code` | `doc`) filtra il corpus: abilita la fusione mirata."""
        if mode == "dense":
            ids = self.dense_rank(query, k, source)
        elif mode == "sparse":
            ids = self.sparse_rank(query, k, source)
        else:
            ids = rrf([self.dense_rank(query, pool, source), self.sparse_rank(query, pool, source)], k)
        return [self._hit(i) for i in ids]

    def _hit(self, doc_id: str) -> dict:
        doc, meta = self.by_id[doc_id]
        return {
            "id": doc_id, "path": meta["path"], "source": meta["source"],
            "kind": meta.get("kind"), "chunk": meta.get("chunk"),
            "text": doc, "preview": " ".join(doc.split())[:160],
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--provider", default="ollama")
    ap.add_argument("--mode", choices=["dense", "sparse", "hybrid"], default="hybrid")
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()
    idx = HybridIndex(args.provider)
    for i, h in enumerate(idx.search(args.query, args.k, mode=args.mode), 1):
        print(f"{i}. [{h['source']}/{h['kind']}] {h['path']}#{h['chunk']}")
        print(f"   {h['preview']}")


if __name__ == "__main__":
    main()
