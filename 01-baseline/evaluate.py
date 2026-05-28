"""Valutazione del baseline: hit-rate@k e MRR sui 3 provider di embedding.

Ground-truth in `eval_queries.json` (query -> sottostringhe di path attese).
Un risultato conta come rilevante se il suo path contiene una delle sottostringhe.

Uso: python 01-baseline/evaluate.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shared.embeddings import PROVIDERS  # noqa: E402

from search import search  # noqa: E402  (modulo locale)

HERE = pathlib.Path(__file__).resolve().parent
QUERIES = json.loads((HERE / "eval_queries.json").read_text(encoding="utf-8"))
K = 10


def first_relevant_rank(hits: list[dict], expected: list[str]) -> int | None:
    for rank, h in enumerate(hits, 1):
        path = h["path"].lower()
        if any(e.lower() in path for e in expected):
            return rank
    return None


def evaluate(provider: str) -> dict:
    ranks = [first_relevant_rank(search(q["query"], provider, K), q["expected"]) for q in QUERIES]
    n = len(ranks)
    hit_at = lambda kk: sum(1 for r in ranks if r and r <= kk) / n  # noqa: E731
    mrr = sum(1.0 / r for r in ranks if r) / n
    return {"hit@1": hit_at(1), "hit@3": hit_at(3), "hit@5": hit_at(5),
            "hit@10": hit_at(10), "mrr@10": mrr, "ranks": ranks}


def main() -> None:
    print(f"Query: {len(QUERIES)} | k={K}\n")
    header = f"{'provider':14} {'hit@1':>6} {'hit@3':>6} {'hit@5':>6} {'hit@10':>7} {'MRR@10':>7}"
    print(header)
    print("-" * len(header))
    for p in PROVIDERS:
        m = evaluate(p)
        print(f"{p:14} {m['hit@1']:6.2f} {m['hit@3']:6.2f} {m['hit@5']:6.2f} "
              f"{m['hit@10']:7.2f} {m['mrr@10']:7.3f}")


if __name__ == "__main__":
    main()
