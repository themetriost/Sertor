"""Costruisce un code knowledge graph leggero dal codice via AST (modulo `ast`).

Nodi: module, class, function, method, doc.
Archi: contains (struttura), imports (modulo->modulo), calls (func->func),
inherits (classe->base), mentions (doc->simbolo, per menzione del nome).

Risoluzione best-effort per nome (intra-progetto). Persistito in GraphML.

Uso: python 03-graphrag/build_graph.py
"""
from __future__ import annotations

import ast
import pathlib
import sys
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import networkx as nx  # noqa: E402

from shared.config import settings  # noqa: E402
from shared.loaders import load_code, load_docs  # noqa: E402

GRAPH_PATH = settings.graph_path  # corpus-aware: .index (fastapi) | .index-<corpus> (sertor)


def _import_roots() -> tuple[str, ...]:
    """Top-level package importabili del corpus (per risolvere gli archi `imports`)."""
    return ("fastapi",) if settings.corpus == "fastapi" else ("shared",)


def _pkg_prefixes() -> tuple[str, ...]:
    """Prefissi di path dei code-root del corpus (per filtrare i simboli 'di package')."""
    return ("fastapi",) if settings.corpus == "fastapi" else (
        "01-baseline", "02-hybrid-reranking", "03-graphrag", "04-agentic-rag", "shared")


def _name_of(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _module_candidates(path: str, node) -> list[str]:
    """Relpath candidati (senza estensione) per un import (best-effort, intra-fastapi)."""
    out: list[str] = []
    if isinstance(node, ast.ImportFrom):
        if node.level:  # relativo
            base = path.split("/")[:-1]
            up = node.level - 1
            base = base[: len(base) - up] if up <= len(base) else []
            mod = node.module.split(".") if node.module else []
            out.append("/".join(base + mod))
            out += ["/".join(base + mod + [a.name]) for a in node.names]
        elif node.module and node.module.split(".")[0] in _import_roots():
            mp = node.module.replace(".", "/")
            out.append(mp)
            out += [f"{mp}/{a.name}" for a in node.names]
    elif isinstance(node, ast.Import):
        out += [a.name.replace(".", "/") for a in node.names if a.name.split(".")[0] in _import_roots()]
    return out


def build() -> nx.DiGraph:
    G = nx.DiGraph()
    name_to_ids: dict[str, list[str]] = defaultdict(list)
    pending_calls: list[tuple[str, str]] = []
    pending_inherits: list[tuple[str, str]] = []
    pending_imports: list[tuple[str, ast.AST]] = []

    code_docs = load_code()
    module_paths = {d.metadata["path"] for d in code_docs}

    for d in code_docs:
        path = d.metadata["path"]
        try:
            tree = ast.parse(d.text, filename=path)
        except SyntaxError:
            continue
        G.add_node(path, kind="module", name=path.split("/")[-1], path=path)

        def rec(node, prefix: str, parent_id: str, enclosing: str | None):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    qual = prefix + child.name
                    sid = f"{path}::{qual}"
                    is_cls = isinstance(child, ast.ClassDef)
                    kind = "class" if is_cls else ("method" if prefix else "function")
                    G.add_node(sid, kind=kind, name=child.name, path=path,
                               lineno=child.lineno, qual=qual)
                    G.add_edge(parent_id, sid, type="contains")
                    name_to_ids[child.name].append(sid)
                    if is_cls:
                        for base in child.bases:
                            bn = _name_of(base)
                            if bn:
                                pending_inherits.append((sid, bn))
                    rec(child, qual + ".", sid, enclosing if is_cls else sid)
                else:
                    if isinstance(child, ast.Call) and enclosing:
                        cn = _name_of(child.func)
                        if cn:
                            pending_calls.append((enclosing, cn))
                    elif isinstance(child, (ast.Import, ast.ImportFrom)):
                        pending_imports.append((path, child))
                    rec(child, prefix, parent_id, enclosing)

        rec(tree, "", path, None)

    # archi inherits / calls (risoluzione per nome, intra-progetto)
    def resolve(name: str, kinds: tuple[str, ...]) -> list[str]:
        return [i for i in name_to_ids.get(name, []) if G.nodes[i]["kind"] in kinds]

    for cls_id, base in pending_inherits:
        for tgt in resolve(base, ("class",)):
            if tgt != cls_id:
                G.add_edge(cls_id, tgt, type="inherits")

    for caller, callee in pending_calls:
        tgts = resolve(callee, ("function", "method", "class"))
        if len(tgts) <= 2:  # evita nomi troppo ambigui
            for tgt in tgts:
                if tgt != caller:
                    G.add_edge(caller, tgt, type="calls")

    for path, node in pending_imports:
        for cand in _module_candidates(path, node):
            for tgt in (f"{cand}.py", f"{cand}/__init__.py"):
                if tgt in module_paths:
                    G.add_edge(path, tgt, type="imports")

    # mentions: doc -> simbolo del package, per menzione del nome (token distintivi)
    pkg_names: dict[str, list[str]] = defaultdict(list)
    for name, ids in name_to_ids.items():
        distinctive = len(name) >= 5 or any(c.isupper() for c in name[1:]) or "_" in name
        if not distinctive:
            continue
        pkg = [i for i in ids if i.split("/")[0] in _pkg_prefixes()]
        if pkg:
            pkg_names[name] = pkg

    import re
    tok = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    for d in load_docs():
        dpath = d.metadata["path"]
        G.add_node(dpath, kind="doc", name=dpath.split("/")[-1], path=dpath)
        for name in set(tok.findall(d.text)) & pkg_names.keys():
            for sid in pkg_names[name]:
                G.add_edge(dpath, sid, type="mentions")

    return G


def main() -> None:
    G = build()
    kinds = Counter(d["kind"] for _, d in G.nodes(data=True))
    etypes = Counter(d["type"] for *_, d in G.edges(data=True))
    print(f"nodi: {G.number_of_nodes()} | archi: {G.number_of_edges()}")
    print("nodi per tipo:", dict(kinds))
    print("archi per tipo:", dict(etypes))
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, GRAPH_PATH)
    print(f"salvato in {GRAPH_PATH.relative_to(settings.root)}")


if __name__ == "__main__":
    main()
