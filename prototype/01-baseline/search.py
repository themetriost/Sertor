"""Retrieval baseline: similarity search su una collection Chroma per provider.

Uso:
    python 01-baseline/search.py "come definisco una dependency?" --provider ollama -k 5
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import chromadb  # noqa: E402

from shared.config import settings  # noqa: E402
from shared.embeddings import get_embedder  # noqa: E402

from index import collection_name  # noqa: E402  (modulo locale)


def search(query: str, provider: str = "ollama", k: int = 5) -> list[dict]:
    client = chromadb.PersistentClient(path=str(settings.index_dir))
    coll = client.get_collection(collection_name(provider))
    qv = get_embedder(provider).embed_one(query)
    res = coll.query(query_embeddings=[qv], n_results=k)
    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append(
            {
                "path": meta["path"],
                "source": meta["source"],
                "kind": meta.get("kind"),
                "chunk": meta.get("chunk"),
                "distance": round(dist, 4),
                "preview": " ".join(doc.split())[:160],
            }
        )
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--provider", default="ollama")
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()
    for i, h in enumerate(search(args.query, args.provider, args.k), 1):
        print(f"{i}. [{h['source']}/{h['kind']}] {h['path']}#{h['chunk']}  (d={h['distance']})")
        print(f"   {h['preview']}")


if __name__ == "__main__":
    main()
