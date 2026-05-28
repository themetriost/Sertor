"""Indicizzazione baseline su Chroma: una collection per provider di embedding.

Uso:
    python 01-baseline/index.py --provider ollama       # un provider
    python 01-baseline/index.py --provider all          # tutti e 3
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import chromadb  # noqa: E402

import chunking  # noqa: E402  (modulo locale)
from shared.config import settings  # noqa: E402
from shared.embeddings import PROVIDERS, get_embedder  # noqa: E402
from shared.loaders import load_code, load_docs  # noqa: E402


def collection_name(provider: str) -> str:
    return "baseline_" + provider.replace("-", "_")


def index_provider(provider: str, chunks: list[dict], client) -> tuple[int, int | None]:
    name = collection_name(provider)
    try:
        client.delete_collection(name)  # idempotenza: ricrea da zero
    except Exception:
        pass
    coll = client.create_collection(name, metadata={"hnsw:space": "cosine"})
    emb = get_embedder(provider)
    vectors = emb.embed([c["text"] for c in chunks])
    # add a batch per non superare i limiti interni di Chroma
    B = 1000
    for i in range(0, len(chunks), B):
        sl = chunks[i : i + B]
        coll.add(
            ids=[c["id"] for c in sl],
            embeddings=vectors[i : i + B],
            documents=[c["text"] for c in sl],
            metadatas=[c["metadata"] for c in sl],
        )
    return coll.count(), emb.dim


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=[*PROVIDERS, "all"], default="ollama")
    args = ap.parse_args()
    providers = PROVIDERS if args.provider == "all" else [args.provider]

    docs = load_code() + load_docs()
    chunks = chunking.build_chunks(docs)
    print(f"documenti: {len(docs)} | chunk: {len(chunks)}")

    client = chromadb.PersistentClient(path=str(settings.index_dir))
    for p in providers:
        t = time.time()
        n, dim = index_provider(p, chunks, client)
        print(f"[{p}] {n} chunk indicizzati (dim={dim}) in {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
