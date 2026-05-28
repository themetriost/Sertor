"""Valutazione del code graph sulle query a simbolo: la definizione trovata e' nel file
atteso? e quanto contesto multi-hop offre (chiamanti, doc collegati)?

Riusa le query "symbol" dell'eval set della Tappa 2. Il grafo non gestisce le query NL
(nessuna ricerca semantica): e' complementare, non sostitutivo, del retrieval vettoriale.

Uso: python 03-graphrag/evaluate.py
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from graph_query import CodeGraph  # noqa: E402

SYMBOL_QUERIES = [
    q for q in json.loads(
        (HERE.parent / "02-hybrid-reranking" / "eval_queries.json").read_text(encoding="utf-8")
    ) if q["type"] == "symbol"
]


def matches(path: str, expected: list[str]) -> bool:
    return any(e.lower() in path.lower() for e in expected)


def main() -> None:
    g = CodeGraph()
    print(f"Query a simbolo: {len(SYMBOL_QUERIES)}\n")
    print(f"{'simbolo':28} {'def@1':>5} {'#def':>4} {'#callers':>8} {'#docs':>5}")
    print("-" * 56)
    def_at_1 = found = 0
    for q in SYMBOL_QUERIES:
        name = q["query"]
        defs = g.definitions(name)
        callers = g.callers(name)
        docs = g.related_docs(name)
        hit1 = bool(defs) and matches(g.G.nodes[defs[0]]["path"], q["expected"])
        any_hit = any(matches(g.G.nodes[d]["path"], q["expected"]) for d in defs)
        def_at_1 += hit1
        found += any_hit
        print(f"{name:28} {('OK' if hit1 else '-'):>5} {len(defs):>4} {len(callers):>8} {len(docs):>5}")
    n = len(SYMBOL_QUERIES)
    print("-" * 56)
    print(f"\ndefinizione corretta al rank 1: {def_at_1}/{n} = {def_at_1 / n:.2f}")
    print(f"definizione corretta tra i risultati: {found}/{n} = {found / n:.2f}")


if __name__ == "__main__":
    main()
