"""Confronto dense vs hybrid vs hybrid+rerank sui 3 provider.

Eval set esteso (`eval_queries.json`) con query in linguaggio naturale e a simboli esatti.
Metriche: hit-rate@k e MRR@10, complessive e sul solo sottoinsieme "symbol".

Uso: python 02-hybrid-reranking/evaluate.py
"""
from __future__ import annotations

import json
import logging
import pathlib
import sys

logging.getLogger("httpx").setLevel(logging.WARNING)  # silenzia il log per-richiesta

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from shared.embeddings import PROVIDERS  # noqa: E402

from hybrid import HybridIndex  # noqa: E402
from rerank import rerank  # noqa: E402

QUERIES = json.loads((HERE / "eval_queries.json").read_text(encoding="utf-8"))
K = 10
POOL = 30
MODES = ["dense", "hybrid", "hybrid+rerank"]


def first_rank(hits: list[dict], expected: list[str]) -> int | None:
    for r, h in enumerate(hits, 1):
        if any(e.lower() in h["path"].lower() for e in expected):
            return r
    return None


def metrics(ranks: list[int | None]) -> dict:
    n = len(ranks) or 1
    hit = lambda kk: sum(1 for r in ranks if r and r <= kk) / n  # noqa: E731
    return {"hit@1": hit(1), "hit@3": hit(3), "hit@5": hit(5),
            "hit@10": hit(10), "mrr": sum(1.0 / r for r in ranks if r) / n}


def run_query(idx: HybridIndex, q: dict, mode: str) -> int | None:
    if mode == "dense":
        hits = idx.search(q["query"], K, mode="dense")
    elif mode == "hybrid":
        hits = idx.search(q["query"], K, pool=POOL, mode="hybrid")
    else:  # hybrid+rerank
        hits = rerank(q["query"], idx.search(q["query"], POOL, pool=POOL, mode="hybrid"), K)
    return first_rank(hits, q["expected"])


def main() -> None:
    symbol_idx = [i for i, q in enumerate(QUERIES) if q["type"] == "symbol"]
    print(f"Query: {len(QUERIES)} (di cui symbol: {len(symbol_idx)}) | k={K}, pool={POOL}\n")
    head = f"{'provider':12} {'mode':14} {'hit@1':>6} {'hit@3':>6} {'hit@5':>6} {'hit@10':>7} {'MRR':>6} {'MRR(sym)':>9}"
    print(head)
    print("-" * len(head))
    for p in PROVIDERS:
        idx = HybridIndex(p)
        for mode in MODES:
            ranks = [run_query(idx, q, mode) for q in QUERIES]
            m = metrics(ranks)
            msym = metrics([ranks[i] for i in symbol_idx])
            print(f"{p:12} {mode:14} {m['hit@1']:6.2f} {m['hit@3']:6.2f} {m['hit@5']:6.2f} "
                  f"{m['hit@10']:7.2f} {m['mrr']:6.3f} {msym['mrr']:9.3f}")
        print()


if __name__ == "__main__":
    main()
