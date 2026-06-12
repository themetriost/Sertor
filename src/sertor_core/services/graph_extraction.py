"""Estrazione pura del code-graph strutturale (FEAT-005, gruppo A).

Servizio deterministico e locale: dai `Document`/`Chunk` del corpus produce `GraphData`
(nodi + archi + copertura dichiarata). NESSUN import di librerie di grafi (research G1):
la persistenza/navigazione è dell'adapter dietro la porta `CodeGraph`.

- **Nodi** (FR-002, DRY): i simboli derivano dai metadati già prodotti dal chunker sintattico
  (`symbol`/`qualname`/`node_type`/`start_line`); i `module` dai Document di codice, i `doc`
  dai Document Markdown. Gli archi `contains` derivano dalla gerarchia dei qualname:
  language-agnostic per tutti i 10 linguaggi.
- **Archi relazionali** (FR-001/003): passaggio tree-sitter dedicato (i chunk sono spezzati e
  non bastano per le chiamate), guidato dalla mappa `_REL` per-linguaggio. `COVERAGE` (derivata
  da `_REL`) è la dichiarazione unica di cosa è supportato per linguaggio (DA-3): ciò che non
  è in mappa non esiste in modo DICHIARATO, mai silenzioso.
- **Risoluzione best-effort intra-corpus per nome** (FR-004): i nomi più ambigui della soglia
  non generano archi `calls` (precisione > completezza, come il prototipo 03).
"""
from __future__ import annotations

import re

from sertor_core.domain.entities import (
    Chunk,
    DocType,
    Document,
    GraphData,
    GraphEdge,
    GraphNode,
)

# Riuso deliberato della conoscenza sintattica del chunker (stesso layer services, DRY):
# kinds di definizione/classe per linguaggio, mapping grammatiche, wrapper del nodo.
from sertor_core.services.chunking.code import _LANG, _TS_NAME, _effective, _Node

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PART_SUFFIX = re.compile(r"\s*\(parte \d+\)$")
_IMPORT_MODULE = re.compile(r"(?:from|import)\s+([.\w]+)")

_SYMBOL_KINDS = ("class", "function", "method")

# Mappa di relazione per-linguaggio: i node-type tree-sitter delle invocazioni e (dove
# validato) di import/ereditarietà. È LA dichiarazione di copertura (FR-003, DA-3).
_REL: dict[str, dict] = {
    "python": {
        "calls": {"call"},
        "imports": {"import_statement", "import_from_statement"},
        "inherits": True,  # via field `superclasses` di class_definition
    },
    "javascript": {"calls": {"call_expression"}},
    "typescript": {"calls": {"call_expression"}},
    "java": {"calls": {"method_invocation"}},
    "c_sharp": {"calls": {"invocation_expression"}},
    "go": {"calls": {"call_expression"}},
    "c": {"calls": {"call_expression"}},
    "cpp": {"calls": {"call_expression"}},
    "php": {"calls": {"function_call_expression", "member_call_expression"}},
    "ruby": {"calls": {"call"}},
}

#: Copertura dichiarata per linguaggio (consumata da build/doc/test — FR-003).
COVERAGE: dict[str, tuple[str, ...]] = {
    lang: tuple(sorted(kind for kind in ("calls", "imports", "inherits") if rel.get(kind)))
    for lang, rel in _REL.items()
}


def extract_graph(
    documents: list[Document],
    chunks: list[Chunk],
    *,
    ambiguity_threshold: int = 2,
) -> GraphData:
    """Estrae il code-graph dal corpus. Puro e deterministico (FR-008)."""
    nodes: dict[str, GraphNode] = {}
    edges: set[tuple[str, str, str]] = set()

    # --- nodi module/doc dai Document -----------------------------------------------------------
    code_documents = [d for d in documents if d.doc_type is DocType.CODE]
    doc_documents = [d for d in documents if d.doc_type is DocType.DOC]
    module_paths = {d.path for d in code_documents}
    for doc in code_documents:
        nodes[doc.path] = GraphNode(doc.path, "module", doc.path.split("/")[-1], doc.path)
    for doc in doc_documents:
        nodes[doc.path] = GraphNode(doc.path, "doc", doc.path.split("/")[-1], doc.path)

    # --- nodi simbolo dai metadati del chunker (FR-002) ------------------------------------------
    for chunk in chunks:
        meta = chunk.metadata
        if not meta.symbol or meta.node_type not in _SYMBOL_KINDS:
            continue
        qual = _PART_SUFFIX.sub("", meta.qualname or meta.symbol)
        node_id = f"{meta.path}::{qual}"
        if node_id not in nodes:
            nodes[node_id] = GraphNode(
                node_id, meta.node_type, meta.symbol, meta.path, meta.start_line, qual
            )

    # --- archi relazionali via tree-sitter (per-linguaggio, FR-001/003/004) ----------------------
    # Il walk raccoglie anche i simboli che il chunker non ha saputo nominare (es. C/C++:
    # `function_definition` senza field `name` → fallback sul `declarator`, rischio R-3):
    # nodi supplementari, mai in conflitto con quelli del chunker (stesso id).
    pending_calls: list[tuple[str, str]] = []
    pending_inherits: list[tuple[str, str]] = []
    discovered: dict[str, GraphNode] = {}
    for doc in code_documents:
        rel = _REL.get(doc.language)
        lang_cfg = _LANG.get(doc.language)
        if not rel or not lang_cfg:
            continue  # copertura dichiarata: il linguaggio resta a soli nodi+contains
        root = _parse(doc)
        if root is None:
            continue
        _walk_relations(
            root, doc.path, lang_cfg, rel, "", None,
            pending_calls, pending_inherits, edges, module_paths, discovered,
        )
    for node_id, node in discovered.items():
        nodes.setdefault(node_id, node)

    # --- contains dalla gerarchia dei qualname (language-agnostic) -------------------------------
    for node in list(nodes.values()):
        if node.kind not in _SYMBOL_KINDS or not node.qualname:
            continue
        if "." in node.qualname:
            parent_id = f"{node.path}::{node.qualname.rsplit('.', 1)[0]}"
            parent_id = parent_id if parent_id in nodes else node.path
        else:
            parent_id = node.path
        if parent_id in nodes:
            edges.add((parent_id, node.id, "contains"))

    # indice nome → id dei simboli (per risoluzione calls/inherits e mentions)
    name_index: dict[str, list[str]] = {}
    for node in nodes.values():
        if node.kind in _SYMBOL_KINDS:
            name_index.setdefault(node.name, []).append(node.id)
    for ids in name_index.values():
        ids.sort()

    def _resolve(name: str, kinds: tuple[str, ...]) -> list[str]:
        return [nid for nid in name_index.get(name, ())
                if nodes[nid].kind in kinds]

    for caller_id, callee_name in pending_calls:
        targets = _resolve(callee_name, _SYMBOL_KINDS)
        if 1 <= len(targets) <= ambiguity_threshold:  # ambigui → omessi (FR-004)
            for target in targets:
                if target != caller_id:
                    edges.add((caller_id, target, "calls"))

    for class_id, base_name in pending_inherits:
        for target in _resolve(base_name, ("class",)):
            if target != class_id:
                edges.add((class_id, target, "inherits"))

    # --- mentions: doc → simboli distintivi (FR-001) ---------------------------------------------
    distinctive = {
        name: ids for name, ids in name_index.items()
        if len(name) >= 5 or any(c.isupper() for c in name[1:]) or "_" in name
    }
    for doc in doc_documents:
        found = set(_IDENT.findall(doc.text)) & distinctive.keys()
        for name in found:
            for target in distinctive[name]:
                edges.add((doc.path, target, "mentions"))

    return GraphData(
        nodes=tuple(sorted(nodes.values(), key=lambda n: n.id)),
        edges=tuple(
            GraphEdge(src, dst, etype)
            for src, dst, etype in sorted(edges, key=lambda e: (e[2], e[0], e[1]))
        ),
        coverage=tuple(sorted((lang, kinds) for lang, kinds in COVERAGE.items())),
    )


def _parse(doc: Document) -> _Node | None:
    try:
        from tree_sitter_language_pack import get_parser

        parser = get_parser(_TS_NAME.get(doc.language, doc.language))
        # Il binding del pack accetta `str` e indicizza in byte: stesso uso del chunker (code.py).
        return _Node(parser.parse(doc.text).root_node(), doc.text.encode("utf-8"))
    except Exception:
        return None  # sorgente non parsabile: restano nodi+contains dal chunker


def _definition_name(eff: _Node) -> str | None:
    """Nome di una definizione: field `name`, con fallback sul `declarator` (C/C++, R-3)."""
    name = eff.name()
    if name:
        return name
    declarator = eff.field("declarator")
    if declarator is not None:
        idents = _IDENT.findall(declarator.text())
        return idents[0] if idents else None
    return None


def _walk_relations(
    node: _Node,
    path: str,
    lang_cfg: dict,
    rel: dict,
    qual_prefix: str,
    enclosing_id: str | None,
    pending_calls: list[tuple[str, str]],
    pending_inherits: list[tuple[str, str]],
    edges: set[tuple[str, str, str]],
    module_paths: set[str],
    discovered: dict[str, GraphNode],
) -> None:
    """Percorre l'AST tracciando il simbolo che racchiude (per attribuire le chiamate)."""
    for child in node.named_children():
        eff = _effective(child)
        kind = eff.kind
        if kind in lang_cfg["def"] | lang_cfg["class"]:
            name = _definition_name(eff)
            if not name:
                continue
            qual = f"{qual_prefix}.{name}" if qual_prefix else name
            symbol_id = f"{path}::{qual}"
            is_class = kind in lang_cfg["class"]
            node_kind = "class" if is_class else ("method" if qual_prefix else "function")
            discovered.setdefault(symbol_id, GraphNode(
                symbol_id, node_kind, name, path, eff.start_row + 1, qual))
            if is_class and rel.get("inherits"):
                supers = eff.field("superclasses")
                if supers is not None:
                    idents = _IDENT.findall(supers.text())
                    pending_inherits.extend((symbol_id, base) for base in idents)
            _walk_relations(
                eff, path, lang_cfg, rel, qual,
                enclosing_id if is_class else symbol_id,
                pending_calls, pending_inherits, edges, module_paths, discovered,
            )
        else:
            if kind in rel.get("calls", ()) and enclosing_id:
                target = _call_target(child)
                if target:
                    pending_calls.append((enclosing_id, target))
            elif kind in rel.get("imports", ()):
                for module in _import_candidates(path, child.text()):
                    for candidate in (f"{module}.py", f"{module}/__init__.py"):
                        if candidate in module_paths:
                            edges.add((path, candidate, "imports"))
            _walk_relations(
                child, path, lang_cfg, rel, qual_prefix, enclosing_id,
                pending_calls, pending_inherits, edges, module_paths, discovered,
            )


def _call_target(call_node: _Node) -> str | None:
    """Nome del simbolo invocato: ultimo identificatore del campo funzione/nome/metodo."""
    for field in ("function", "name", "method"):
        target = call_node.field(field)
        if target is not None:
            idents = _IDENT.findall(target.text())
            return idents[-1] if idents else None
    return None


def _import_candidates(path: str, statement: str) -> list[str]:
    """Relpath candidati (senza estensione) per gli import, intra-corpus best-effort."""
    out: list[str] = []
    for dotted in _IMPORT_MODULE.findall(statement):
        level = len(dotted) - len(dotted.lstrip("."))
        module = dotted.lstrip(".")
        parts = module.split(".") if module else []
        if level:  # import relativo: risolto dalla cartella del file
            base = path.split("/")[:-1]
            up = level - 1
            base = base[: len(base) - up] if up <= len(base) else []
            out.append("/".join(base + parts))
        else:
            out.append("/".join(parts))
    return [candidate for candidate in out if candidate]
