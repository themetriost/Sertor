"""Chunking code-aware via tree-sitter (REQ-006/007/011).

Spezza il codice ai confini sintattici: ogni funzione/metodo/classe diventa un chunk coerente con
metadati strutturali (qualname, tipo di nodo, righe); il codice a livello modulo (import,
costanti) è raggruppato in chunk propri. Le unità troppo grandi sono sotto-divise per righe.

Repo-agnostico: la lingua è mappata sui tipi di nodo della relativa grammatica. Solo i linguaggi
in `_LANG` (node-type validati) sono chunkati sintatticamente; per gli altri `code_chunks`
ritorna `None` e il chiamante fa il fallback dimensionale (REQ-009). PowerShell e i dialetti SQL,
pur avendo una grammatica nel pack, sono volutamente esclusi al 1° rilascio (R-N2): andranno in
fallback finché i loro node-type non sono validati — estensione incrementale (REQ-011).

Il binding fornito da `tree-sitter-language-pack` espone l'API come metodi (`kind()`,
`byte_range()`, `start_position()`); `_Node` la avvolge in un'interfaccia leggibile.
"""
from __future__ import annotations

DEFAULT_MAX_CHARS = 1600

# linguaggio Sertor -> nome grammatica nel pack
_TS_NAME: dict[str, str] = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "c_sharp": "csharp",
    "go": "go",
    "c": "c",
    "cpp": "cpp",
    "php": "php",
    "ruby": "ruby",
}

# linguaggio -> tipi di nodo per definizioni (funzioni/metodi) e contenitori (classi)
_LANG: dict[str, dict[str, set[str]]] = {
    "python": {
        "def": {"function_definition"},
        "class": {"class_definition"},
    },
    "javascript": {
        "def": {"function_declaration", "method_definition", "generator_function_declaration"},
        "class": {"class_declaration"},
    },
    "typescript": {
        "def": {"function_declaration", "method_definition"},
        "class": {"class_declaration", "interface_declaration"},
    },
    "java": {
        "def": {"method_declaration", "constructor_declaration"},
        "class": {"class_declaration", "interface_declaration", "enum_declaration"},
    },
    "c_sharp": {
        "def": {"method_declaration", "constructor_declaration"},
        "class": {"class_declaration", "interface_declaration", "struct_declaration"},
    },
    "go": {
        "def": {"function_declaration", "method_declaration"},
        "class": {"type_declaration"},
    },
    "c": {"def": {"function_definition"}, "class": set()},
    "cpp": {"def": {"function_definition"}, "class": {"class_specifier", "struct_specifier"}},
    "php": {
        "def": {"function_definition", "method_declaration"},
        "class": {"class_declaration", "interface_declaration", "trait_declaration"},
    },
    "ruby": {"def": {"method", "singleton_method"}, "class": {"class", "module"}},
}

_BODY_FIELDS = ("body", "declaration_list")


class _Node:
    """Wrapper leggibile sul nodo del binding (API a metodi)."""

    __slots__ = ("n", "src")

    def __init__(self, node, src: bytes):
        self.n = node
        self.src = src

    @property
    def kind(self) -> str:
        return self.n.kind()

    @property
    def start_row(self) -> int:
        return self.n.start_position().row

    @property
    def end_row(self) -> int:
        return self.n.end_position().row

    def field(self, name: str) -> _Node | None:
        c = self.n.child_by_field_name(name)
        return _Node(c, self.src) if c is not None else None

    def named_children(self) -> list[_Node]:
        return [_Node(self.n.named_child(i), self.src) for i in range(self.n.named_child_count())]

    def name(self) -> str | None:
        f = self.field("name")
        return f.text() if f is not None else None

    def text(self) -> str:
        br = self.n.byte_range()
        return self.src[br.start : br.end].decode("utf-8", "ignore")

    def body(self) -> _Node | None:
        for fld in _BODY_FIELDS:
            b = self.field(fld)
            if b is not None:
                return b
        return None


def _split_oversize(body: str, max_chars: int) -> list[str]:
    """Sotto-divide un blocco troppo grande per righe, in finestre <= max_chars."""
    lines = body.split("\n")
    parts: list[str] = []
    cur: list[str] = []
    size = 0
    for ln in lines:
        if cur and size + len(ln) + 1 > max_chars:
            parts.append("\n".join(cur))
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        parts.append("\n".join(cur))
    return parts or [body]


def _effective(node: _Node) -> _Node:
    """Per i nodi 'decorati' (es. decorated_definition) ritorna la definizione interna."""
    if node.kind == "decorated_definition":
        for c in node.named_children():
            if c.kind.endswith("definition") or c.kind.endswith("declaration"):
                return c
    return node


def code_chunks(
    text: str, language: str = "python", max_chars: int = DEFAULT_MAX_CHARS
) -> list[dict] | None:
    """Spezza `text` ai confini sintattici. `None` se la lingua non è chunkabile sintatticamente.

    Ogni chunk: {text, symbol, symbol_kind, qualname, start_line, end_line} (righe 1-based).
    """
    cfg = _LANG.get(language)
    if cfg is None:
        return None
    try:
        from tree_sitter_language_pack import get_parser

        parser = get_parser(_TS_NAME.get(language, language))
        root = _Node(parser.parse(text).root_node(), text.encode("utf-8"))
    except Exception:
        return None

    lines = text.split("\n")
    chunks: list[dict] = []
    pending: list[tuple[int, int]] = []

    def line_slice(a: int, b: int) -> str:
        return "\n".join(lines[a : b + 1])

    def emit(symbol, kind, qualname, a: int, b: int) -> None:
        body = line_slice(a, b)
        if not body.strip():
            return
        parts = [body] if len(body) <= max_chars else _split_oversize(body, max_chars)
        multi = len(parts) > 1
        for j, part in enumerate(parts):
            ql = qualname if not multi else f"{qualname or symbol or kind} (parte {j + 1})"
            chunks.append(
                {
                    "text": part,
                    "symbol": symbol,
                    "symbol_kind": kind,
                    "qualname": ql,
                    "start_line": a + 1,
                    "end_line": b + 1,
                }
            )

    def flush_module() -> None:
        nonlocal pending
        if pending:
            emit(None, "module", None, pending[0][0], pending[-1][1])
            pending = []

    def handle_class(outer: _Node, context: str) -> None:
        eff = _effective(outer)
        cname = eff.name()
        qual = ".".join(p for p in (context, cname) if p) or cname
        body = eff.body()
        members = (
            [c for c in body.named_children() if _effective(c).kind in cfg["def"] | cfg["class"]]
            if body is not None
            else []
        )
        h_start = outer.start_row
        h_end = (members[0].start_row - 1) if members else eff.end_row
        emit(cname, "class", qual, h_start, max(h_start, h_end))
        for m in members:
            mk = _effective(m)
            if mk.kind in cfg["class"]:
                handle_class(m, qual)
            else:
                mname = mk.name()
                mqual = ".".join(p for p in (qual, mname) if p) or mname
                emit(mname, "method", mqual, m.start_row, m.end_row)

    for node in root.named_children():
        eff = _effective(node)
        if eff.kind in cfg["class"]:
            flush_module()
            handle_class(node, "")
        elif eff.kind in cfg["def"]:
            flush_module()
            name = eff.name()
            emit(name, "function", name, node.start_row, node.end_row)
        else:
            pending.append((node.start_row, node.end_row))
    flush_module()
    return chunks
