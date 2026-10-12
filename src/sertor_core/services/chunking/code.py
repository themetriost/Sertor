"""Code-aware chunking via tree-sitter (REQ-006/007/011).

Splits code at syntactic boundaries: each function/method/class becomes a coherent chunk with
structural metadata (qualname, node type, lines); module-level code (imports, constants) is
grouped into its own chunks. Oversized units are sub-divided by lines.

Repo-agnostic: the language is mapped to the node types of the corresponding grammar. Only the
languages in `_LANG` (validated node-types) are chunked syntactically; for the others
`code_chunks` returns `None` and the caller applies the size-based fallback (REQ-009). PowerShell
and SQL dialects, despite having a grammar in the pack, are intentionally excluded in the first
release (R-N2): they fall back until their node-types are validated — incremental extension
(REQ-011).

The binding provided by `tree-sitter-language-pack` exposes the API as methods (`kind()`,
`byte_range()`, `start_position()`); `_Node` wraps it in a readable interface.
"""
from __future__ import annotations

DEFAULT_MAX_CHARS = 1600

# Sertor language -> grammar name in the pack
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

# language -> node types for definitions (functions/methods) and containers (classes)
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

# language -> TRANSPARENT scopes: nodes that wrap definitions without being one (namespaces,
# `export`, `extern "C"`). The chunker descends into them and they never enter the qualname,
# exactly as the graph walk does (E10-FEAT-082: before, `namespace Demo { class X … }` became one
# `module` chunk). Measured on the grammars with a probe; a language absent here has none.
_SCOPES: dict[str, set[str]] = {
    "c_sharp": {"namespace_declaration"},
    "cpp": {"namespace_definition", "linkage_specification"},
    "php": {"namespace_definition"},
    "javascript": {"export_statement"},
    # `namespace N { }` at top level parses as expression_statement > internal_module
    "typescript": {"export_statement", "internal_module", "expression_statement"},
}

_BODY_FIELDS = ("body", "declaration_list")


def scope_signature() -> str:
    """Identity of the transparent-scope rules, part of the indexing logic-version: changing them
    changes the chunks of unchanged files, which must then be re-chunked."""
    return ";".join(f"{lang}:{','.join(sorted(kinds))}" for lang, kinds in sorted(_SCOPES.items()))


class _Node:
    """Readable wrapper around a binding node (method-based API)."""

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
    """Sub-divides an oversized block by lines, into windows <= max_chars."""
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
    """For 'decorated' nodes (e.g. decorated_definition) returns the inner definition."""
    if node.kind == "decorated_definition":
        for c in node.named_children():
            if c.kind.endswith("definition") or c.kind.endswith("declaration"):
                return c
    return node


def _scope_children(node: _Node, language: str) -> list[_Node] | None:
    """Children of `node` if it is a transparent scope for `language`, else `None`.

    An `expression_statement` counts only when it wraps a TypeScript namespace: any other
    expression stays module-level code.
    """
    if node.kind not in _SCOPES.get(language, ()):
        return None
    if node.kind == "expression_statement":
        inner = node.named_children()
        return inner if len(inner) == 1 and inner[0].kind == "internal_module" else None
    body = node.body()
    return (body if body is not None else node).named_children()


def syntax_error_line(text: str, language: str) -> int | None:
    """1-based line of the first syntax error in `text`, or `None` if it parses cleanly.

    Used where a parse that merely *recovers* is not good enough (ASP.NET pages, 140): the caller
    needs to know the source is broken and where, to report it instead of indexing a damaged tree.
    A grammar that cannot be loaded counts as an error at line 1 — never as a clean parse.
    """
    try:
        from tree_sitter_language_pack import get_parser

        root = get_parser(_TS_NAME.get(language, language)).parse(text).root_node()
    except Exception:
        return 1
    if not root.has_error():
        return None
    rows = _innermost_error_rows(root)
    return min(rows, default=root.start_position().row) + 1


def _innermost_error_rows(node) -> list[int]:
    """Rows of the error/missing nodes that contain no other error.

    An outer ERROR node often starts at the enclosing construct (a class), far from the broken line;
    the innermost one points at what actually broke (e.g. a missing `)`).
    """
    rows: list[int] = []
    for i in range(node.child_count()):
        rows.extend(_innermost_error_rows(node.child(i)))
    if not rows and (node.is_error() or node.is_missing()):
        rows.append(node.start_position().row)
    return rows


def code_chunks(
    text: str, language: str = "python", max_chars: int = DEFAULT_MAX_CHARS
) -> list[dict] | None:
    """Splits `text` at syntactic boundaries. `None` if the language cannot be chunked
    syntactically.

    Each chunk: {text, symbol, symbol_kind, qualname, start_line, end_line} (1-based lines).
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
            ql = qualname if not multi else f"{qualname or symbol or kind} (part {j + 1})"
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

    def walk(nodes: list[_Node]) -> None:
        for node in nodes:
            eff = _effective(node)
            if eff.kind in cfg["class"]:
                flush_module()
                handle_class(node, "")
            elif eff.kind in cfg["def"]:
                flush_module()
                name = eff.name()
                emit(name, "function", name, node.start_row, node.end_row)
            elif (inner := _scope_children(node, language)) is not None:
                # the scope's header (`namespace Demo {`) stays module-level text; its closing
                # brace carries nothing worth a chunk
                first = inner[0].start_row if inner else node.end_row + 1
                if first > node.start_row:
                    pending.append((node.start_row, first - 1))
                walk(inner)
            else:
                pending.append((node.start_row, node.end_row))

    walk(root.named_children())
    flush_module()
    return chunks
