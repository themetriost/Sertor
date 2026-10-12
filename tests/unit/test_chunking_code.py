"""Test US2 — syntactic code-aware chunking (REQ-006/007/010/011)."""
from __future__ import annotations

from sertor_core.services.chunking.code import code_chunks

PY = (
    "PI = 3.14\n"
    "\n"
    "def add(a, b):\n"
    "    return a + b\n"
    "\n"
    "class Calculator:\n"
    "    def __init__(self):\n"
    "        self.value = 0\n"
    "\n"
    "    def add(self, n):\n"
    "        self.value += n\n"
    "        return self.value\n"
)

JS = (
    "const PORT = 8080;\n"
    "function startServer(port) {\n"
    "  return port;\n"
    "}\n"
    "function handleRequest(req) {\n"
    "  return 200;\n"
    "}\n"
)

GO = (
    "package svc\n"
    "func Greet(name string) string {\n"
    "\treturn name\n"
    "}\n"
    "func Add(a int, b int) int {\n"
    "\treturn a + b\n"
    "}\n"
)


def test_python_syntactic_chunks_with_metadata():
    chunks = code_chunks(PY, "python")
    assert chunks is not None
    quals = {c["qualname"] for c in chunks}
    kinds = {c["symbol_kind"] for c in chunks}
    assert "add" in quals                      # top-level function
    assert "Calculator" in quals               # class
    assert "Calculator.add" in quals           # method with nested qualname
    assert {"function", "class", "method"} <= kinds
    # structural metadata: consistent 1-based line numbers (REQ-007)
    for c in chunks:
        assert c["start_line"] >= 1
        assert c["end_line"] >= c["start_line"]


def test_javascript_functions_are_chunked():
    chunks = code_chunks(JS, "javascript")
    assert chunks is not None
    quals = {c["qualname"] for c in chunks}
    assert "startServer" in quals
    assert "handleRequest" in quals


def test_go_functions_are_chunked():
    chunks = code_chunks(GO, "go")
    assert chunks is not None
    quals = {c["qualname"] for c in chunks}
    assert "Greet" in quals
    assert "Add" in quals


def test_syntax_error_line_on_valid_and_broken_csharp():
    from sertor_core.services.chunking.code import syntax_error_line

    assert syntax_error_line("class A {\n    void F() { }\n}\n", "c_sharp") is None
    broken = "class A {\n    void F() { }\n    void G( {\n}\n"
    assert syntax_error_line(broken, "c_sharp") == 3


def test_syntax_error_line_points_at_the_innermost_error_not_the_enclosing_class():
    from sertor_core.services.chunking.code import syntax_error_line

    # The outer ERROR node starts at the class (line 2); the missing `)` is on line 3.
    view = "\nclass P {\n    void Rotto( {\n        Nulla(\n}\n"
    assert syntax_error_line(view, "c_sharp") == 3


def test_unsupported_language_returns_none():
    # powershell/sql: grammar not configured at 1st release -> None -> fallback (REQ-009)
    assert code_chunks("function Deploy {}", "powershell") is None
    assert code_chunks("SELECT 1", "sql") is None


def test_code_chunking_is_deterministic():
    a = code_chunks(PY, "python")
    b = code_chunks(PY, "python")
    assert [c["qualname"] for c in a] == [c["qualname"] for c in b]
    assert [(c["start_line"], c["end_line"]) for c in a] == [
        (c["start_line"], c["end_line"]) for c in b
    ]


# --- Transparent scopes (E10-FEAT-082): namespaces and `export` wrap definitions without being one.
# The chunker descends into them without adding to the qualname, exactly as the graph walk does.

def _quals(src: str, language: str) -> dict[str, tuple[int, int]]:
    return {
        c["qualname"]: (c["start_line"], c["end_line"])
        for c in code_chunks(src, language)
        if c["qualname"]
    }


def test_csharp_block_namespace_is_descended():
    src = (
        "using System;\n"
        "namespace Demo\n"
        "{\n"
        "    public partial class Default\n"
        "    {\n"
        "        void BindGrid() { }\n"
        "\n"
        "        string Titolo() { return \"x\"; }\n"
        "    }\n"
        "}\n"
    )
    quals = _quals(src, "c_sharp")
    assert quals["Default.BindGrid"] == (6, 6)
    assert quals["Default.Titolo"] == (8, 8)
    assert "Default" in quals
    module = [c for c in code_chunks(src, "c_sharp") if c["symbol_kind"] == "module"]
    assert len(module) == 1 and "namespace Demo" in module[0]["text"]


def test_csharp_nested_and_qualified_namespaces_stay_out_of_the_qualname():
    src = "namespace A.B\n{\n  namespace C {\n    class X { void M() {} }\n  }\n}\n"
    assert set(_quals(src, "c_sharp")) == {"X", "X.M"}


def test_csharp_file_scoped_namespace_is_unchanged():
    src = "namespace Demo;\nclass X\n{\n    void M() { }\n}\n"
    assert _quals(src, "c_sharp")["X.M"] == (4, 4)


def test_cpp_namespaces_and_extern_c_are_descended():
    src = (
        "namespace a {\n"
        "class X { void m() {} };\n"
        "int f() { return 1; }\n"
        "}\n"
        "namespace { int g() { return 0; } }\n"
        "extern \"C\" { int h() { return 0; } }\n"
    )
    chunks = code_chunks(src, "cpp")
    assert _quals(src, "cpp")["X"] == (2, 2)
    # C/C++ functions carry no `name` field (R-3: the graph names them from the declarator);
    # what matters here is that each one is its own chunk, at its own lines
    functions = [(c["start_line"], c["end_line"]) for c in chunks if c["symbol_kind"] == "function"]
    assert functions == [(3, 3), (5, 5), (6, 6)]


def test_php_braced_namespace_is_descended():
    src = "<?php\nnamespace Foo {\n  class X {\n    function m() {}\n  }\n}\n"
    assert _quals(src, "php")["X.m"] == (4, 4)


def test_typescript_export_and_namespace_are_descended():
    src = (
        "import x from 'y';\n"
        "export class Y {\n"
        "  m() {}\n"
        "}\n"
        "export function g() {}\n"
        "namespace N {\n"
        "  export class Z { n() {} }\n"
        "}\n"
    )
    quals = _quals(src, "typescript")
    assert quals["Y"][0] == 2 and quals["Y.m"] == (3, 3)
    assert quals["g"] == (5, 5)
    assert quals["Z.n"] == (7, 7)


def test_javascript_export_default_function_is_chunked():
    src = "export class Y {\n  m() {}\n}\nexport default function g() {}\n"
    quals = _quals(src, "javascript")
    assert quals["Y.m"] == (2, 2)
    assert quals["g"] == (4, 4)


def test_scope_signature_is_part_of_the_chunking_identity():
    from sertor_core.services.chunking.code import scope_signature

    sig = scope_signature()
    assert "c_sharp:namespace_declaration" in sig
    assert "typescript:" in sig and "export_statement" in sig


def test_logic_version_carries_the_scope_rules():
    """Changing the scope rules re-chunks unchanged files on the next incremental index."""
    from sertor_core.config.settings import Settings
    from sertor_core.services.chunking.code import scope_signature
    from sertor_core.services.indexing import _logic_version

    assert f"scopes={scope_signature()}" in _logic_version(Settings())
