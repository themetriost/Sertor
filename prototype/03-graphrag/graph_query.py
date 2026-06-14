"""Query strutturali sul code graph: definizione, chiamanti, doc collegati, contesto multi-hop.

Uso:
    python 03-graphrag/graph_query.py def OAuth2PasswordBearer
    python 03-graphrag/graph_query.py callers get_current_user
    python 03-graphrag/graph_query.py docs APIRouter
    python 03-graphrag/graph_query.py context OAuth2PasswordBearer
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import networkx as nx  # noqa: E402
from build_graph import GRAPH_PATH  # noqa: E402

SYMBOL_KINDS = ("class", "function", "method")


class CodeGraph:
    def __init__(self, path: pathlib.Path = GRAPH_PATH):
        if not path.exists():
            raise SystemExit("Grafo assente: esegui prima `python 03-graphrag/build_graph.py`.")
        self.G = nx.read_graphml(path)

    def ids_by_name(self, name: str, kinds=SYMBOL_KINDS) -> list[str]:
        return [n for n, d in self.G.nodes(data=True)
                if d.get("name") == name and d.get("kind") in kinds]

    def _in(self, node: str, etype: str) -> list[str]:
        return [u for u, _, d in self.G.in_edges(node, data=True) if d.get("type") == etype]

    def _out(self, node: str, etype: str) -> list[str]:
        return [v for _, v, d in self.G.out_edges(node, data=True) if d.get("type") == etype]

    def label(self, node: str) -> str:
        d = self.G.nodes[node]
        if d.get("kind") in SYMBOL_KINDS:
            return f"{d['path']}:{d.get('lineno','?')}  {d['kind']} {d.get('qual', d['name'])}"
        return f"{d.get('path', node)}  ({d.get('kind')})"

    def definitions(self, name: str) -> list[str]:
        return self.ids_by_name(name)

    def callers(self, name: str) -> list[str]:
        out: list[str] = []
        for sid in self.ids_by_name(name):
            out += self._in(sid, "calls")
        return sorted(set(out))

    def callees(self, name: str) -> list[str]:
        out: list[str] = []
        for sid in self.ids_by_name(name):
            out += self._out(sid, "calls")
        return sorted(set(out))

    def related_docs(self, name: str) -> list[str]:
        out: list[str] = []
        for sid in self.ids_by_name(name):
            out += self._in(sid, "mentions")
        return sorted(set(out))

    def bases(self, name: str) -> list[str]:
        out: list[str] = []
        for sid in self.ids_by_name(name, ("class",)):
            out += self._out(sid, "inherits")
        return sorted(set(out))


def _print(graph: CodeGraph, nodes: list[str], limit: int = 10) -> None:
    for n in nodes[:limit]:
        print("   -", graph.label(n))
    if len(nodes) > limit:
        print(f"   ... (+{len(nodes) - limit})")
    if not nodes:
        print("   (nessuno)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["def", "callers", "callees", "docs", "context"])
    ap.add_argument("name")
    args = ap.parse_args()
    g = CodeGraph()

    if args.command == "def":
        print(f"Definizioni di {args.name!r}:"); _print(g, g.definitions(args.name))
    elif args.command == "callers":
        print(f"Chi chiama {args.name!r}:"); _print(g, g.callers(args.name))
    elif args.command == "callees":
        print(f"Cosa chiama {args.name!r}:"); _print(g, g.callees(args.name))
    elif args.command == "docs":
        print(f"Doc che menzionano {args.name!r}:"); _print(g, g.related_docs(args.name))
    else:  # context (multi-hop)
        print(f"== Contesto multi-hop per {args.name!r} ==")
        print("Definizione:"); _print(g, g.definitions(args.name))
        print("Classi base:"); _print(g, g.bases(args.name), 5)
        print("Chiamanti:"); _print(g, g.callers(args.name), 8)
        print("Chiamate uscenti:"); _print(g, g.callees(args.name), 8)
        print("Doc collegati:"); _print(g, g.related_docs(args.name), 8)


if __name__ == "__main__":
    main()
