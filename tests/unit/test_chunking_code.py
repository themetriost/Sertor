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
