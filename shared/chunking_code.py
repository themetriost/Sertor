"""Chunking **code-aware** via tree-sitter: spezza il codice ai confini sintattici.

A differenza dello splitter ricorsivo (guidato dalla dimensione, può tagliare a metà
funzione), qui ogni **funzione/metodo/classe** diventa un chunk coerente, con decoratori e
docstring inclusi, e metadati strutturali (`symbol`, `symbol_kind`, `qualname`, righe).
I metodi portano in testa il contesto della classe; il codice a livello modulo (import,
costanti) è raggruppato in chunk propri (nulla va perso). Le unità troppo grandi vengono
sotto-divise per righe.

Repo-agnostico: la lingua è un parametro mappato sulla relativa grammatica `tree-sitter-<lang>`.
Ora attivo Python; per aggiungere una lingua basta installare la grammatica e registrarla in
`_GRAMMARS`. `code_chunks` ritorna `None` se la lingua non è supportata → il chiamante fa fallback.
"""
from __future__ import annotations

import importlib

DEFAULT_MAX_CHARS = 1600
_DEF_TYPES = ("function_definition", "class_definition")
# lingua -> modulo della grammatica tree-sitter (installabile a parte)
_GRAMMARS = {"python": "tree_sitter_python"}
_PARSERS: dict = {}


def _parser(language: str):
    if language not in _PARSERS:
        from tree_sitter import Language, Parser
        mod = importlib.import_module(_GRAMMARS[language])  # KeyError -> lingua non supportata
        _PARSERS[language] = Parser(Language(mod.language()))
    return _PARSERS[language]


def _text(node) -> str:
    t = node.text
    return t.decode("utf-8", "ignore") if isinstance(t, (bytes, bytearray)) else (t or "")


def _name(node) -> str | None:
    n = node.child_by_field_name("name")
    return _text(n) if n is not None else None


def _inner_def(node):
    """La definizione interna di un `decorated_definition` (o il nodo stesso)."""
    if node.type == "decorated_definition":
        for c in node.children:
            if c.type in _DEF_TYPES:
                return c
    return node


def _split_oversize(body: str, max_chars: int) -> list[str]:
    """Sotto-divide un blocco troppo grande per righe, in finestre <= max_chars."""
    lines = body.split("\n")
    parts, cur, size = [], [], 0
    for ln in lines:
        if cur and size + len(ln) + 1 > max_chars:
            parts.append("\n".join(cur))
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        parts.append("\n".join(cur))
    return parts or [body]


def code_chunks(text: str, language: str = "python",
                max_chars: int = DEFAULT_MAX_CHARS) -> list[dict] | None:
    """Spezza `text` ai confini sintattici. Ritorna chunk dict o `None` se lingua non supportata.

    Ogni chunk: {text, symbol, symbol_kind, qualname, start_line, end_line} (righe 1-based).
    """
    try:
        parser = _parser(language)
    except Exception:
        return None

    lines = text.split("\n")
    root = parser.parse(text.encode("utf-8")).root_node
    chunks: list[dict] = []
    pending: list[tuple[int, int]] = []  # righe (start,end) di statement a livello modulo

    def line_slice(a: int, b: int) -> str:
        return "\n".join(lines[a : b + 1])

    def emit(body: str, symbol, kind: str, qualname, a: int, b: int) -> None:
        if not body.strip():
            return
        parts = [body] if len(body) <= max_chars else _split_oversize(body, max_chars)
        multi = len(parts) > 1
        for j, part in enumerate(parts):
            ql = qualname if not multi else f"{qualname or symbol or kind} (parte {j + 1})"
            chunks.append({"text": part, "symbol": symbol, "symbol_kind": kind,
                           "qualname": ql, "start_line": a + 1, "end_line": b + 1})

    def flush_module() -> None:
        nonlocal pending
        if pending:
            emit(line_slice(pending[0][0], pending[-1][1]), None, "module", None,
                 pending[0][0], pending[-1][1])
            pending = []

    def handle_class(outer) -> None:
        cdef = _inner_def(outer)
        cname = _name(cdef)
        body = cdef.child_by_field_name("body")
        methods = [c for c in body.children if c.type in
                   ("function_definition", "decorated_definition")] if body else []
        h_start = outer.start_point[0]
        h_end = (methods[0].start_point[0] - 1) if methods else cdef.end_point[0]
        emit(line_slice(h_start, h_end), cname, "class", cname, h_start, max(h_start, h_end))
        sig = lines[cdef.start_point[0]].strip()  # riga `class Foo(...):` come contesto
        for m in methods:
            mdef = _inner_def(m)
            mname = _name(mdef)
            a, b = m.start_point[0], m.end_point[0]
            ctx = f"# metodo di {cname}\n{sig}\n"
            emit(ctx + line_slice(a, b), mname, "method", f"{cname}.{mname}", a, b)

    for node in root.children:
        if node.type == "class_definition" or (
            node.type == "decorated_definition" and _inner_def(node).type == "class_definition"
        ):
            flush_module()
            handle_class(node)
        elif node.type == "function_definition" or (
            node.type == "decorated_definition" and _inner_def(node).type == "function_definition"
        ):
            flush_module()
            fdef = _inner_def(node)
            a, b = node.start_point[0], node.end_point[0]
            emit(line_slice(a, b), _name(fdef), "function", _name(fdef), a, b)
        else:
            pending.append((node.start_point[0], node.end_point[0]))
    flush_module()
    return chunks
