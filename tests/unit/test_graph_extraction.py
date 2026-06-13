"""Test US1 — pure code-graph extraction (FR-001..004, FR-008).

No networkx, no network: extraction is a pure service over Document/Chunk.
"""
from __future__ import annotations

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType, Document
from sertor_core.services.chunking.dispatch import chunk_document
from sertor_core.services.graph_extraction import COVERAGE, extract_graph

MOD_UNO = '''"""Modulo uno."""


class Base:
    def greet(self):
        return "hi"


class Greeter(Base):
    def salute(self):
        return formato_speciale(self.greet())


def formato_speciale(testo):
    return testo.upper()
'''

MOD_DUE = '''import mod_uno
from mod_uno import formato_speciale


def main():
    return formato_speciale("x")
'''

GUIDA = "# Guida\n\nLa funzione formato_speciale normalizza il testo della demo.\n"


def _document(doc_id: str, text: str, doc_type: DocType, language: str) -> Document:
    return Document(id=doc_id, text=text, doc_type=doc_type, language=language)


def _corpus() -> tuple[list[Document], list]:
    settings = Settings.load(env_file=None)
    documents = [
        _document("mod_uno.py", MOD_UNO, DocType.CODE, "python"),
        _document("mod_due.py", MOD_DUE, DocType.CODE, "python"),
        _document("guida.md", GUIDA, DocType.DOC, "markdown"),
    ]
    chunks = [c for d in documents for c in chunk_document(d, settings)]
    return documents, chunks


def _extract(threshold: int = 2):
    documents, chunks = _corpus()
    return extract_graph(documents, chunks, ambiguity_threshold=threshold)


def _edges(data, etype: str) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in data.edges if e.type == etype}


# --- nodes (FR-001/FR-002) ------------------------------------------------------------------

def test_nodes_cover_modules_symbols_and_docs():
    data = _extract()
    by_id = {n.id: n for n in data.nodes}
    assert by_id["mod_uno.py"].kind == "module"
    assert by_id["guida.md"].kind == "doc"
    assert by_id["mod_uno.py::Greeter"].kind == "class"
    assert by_id["mod_uno.py::Greeter.salute"].kind == "method"
    assert by_id["mod_uno.py::formato_speciale"].kind == "function"
    assert by_id["mod_uno.py::formato_speciale"].line is not None  # line from chunker (FR-002)


def test_contains_follows_qualname_hierarchy():
    data = _extract()
    contains = _edges(data, "contains")
    assert ("mod_uno.py", "mod_uno.py::Greeter") in contains          # module → top-level symbol
    assert ("mod_uno.py::Greeter", "mod_uno.py::Greeter.salute") in contains  # class → method
    assert ("mod_due.py", "mod_due.py::main") in contains


# --- relational Python edges (FR-001, prototype parity) --------------------------------------

def test_calls_edges_resolved_by_name():
    data = _extract()
    calls = _edges(data, "calls")
    assert ("mod_uno.py::Greeter.salute", "mod_uno.py::formato_speciale") in calls
    assert ("mod_due.py::main", "mod_uno.py::formato_speciale") in calls
    # attribute call: self.greet() → Base.greet (single candidate)
    assert ("mod_uno.py::Greeter.salute", "mod_uno.py::Base.greet") in calls


def test_inherits_edges_for_python_classes():
    data = _extract()
    assert ("mod_uno.py::Greeter", "mod_uno.py::Base") in _edges(data, "inherits")


def test_imports_edges_intra_corpus():
    data = _extract()
    assert ("mod_due.py", "mod_uno.py") in _edges(data, "imports")


def test_ambiguous_names_do_not_generate_calls(monkeypatch):
    # Three homonymous definitions: with threshold 2 the calls edges to "dup" are OMITTED (FR-004).
    settings = Settings.load(env_file=None)
    documents = [
        _document(f"m{i}.py", "def dup():\n    return 1\n", DocType.CODE, "python")
        for i in range(3)
    ]
    documents.append(_document(
        "caller.py", "def chi_chiama():\n    return dup()\n", DocType.CODE, "python"))
    chunks = [c for d in documents for c in chunk_document(d, settings)]
    strict = extract_graph(documents, chunks, ambiguity_threshold=2)
    assert not [e for e in strict.edges if e.type == "calls" and e.target.endswith("::dup")]
    loose = extract_graph(documents, chunks, ambiguity_threshold=5)
    assert [e for e in loose.edges if e.type == "calls" and e.target.endswith("::dup")]


# --- mentions (FR-001) -------------------------------------------------------------------------

def test_docs_mention_distinctive_symbols():
    data = _extract()
    mentions = _edges(data, "mentions")
    assert ("guida.md", "mod_uno.py::formato_speciale") in mentions   # underscore → distinctive
    # "Base" is not distinctive (short, only initial uppercase): no spurious mention
    assert not [t for s, t in mentions if t.endswith("::Base")]


# --- determinism and declared coverage (FR-003/FR-008) ----------------------------------------

def test_extraction_is_deterministic():
    assert _extract() == _extract()


def test_coverage_declares_all_ten_languages():
    assert set(COVERAGE) == {"python", "javascript", "typescript", "java", "c_sharp",
                             "go", "c", "cpp", "php", "ruby"}
    assert set(COVERAGE["python"]) >= {"calls", "imports", "inherits"}
    for lang, kinds in COVERAGE.items():
        assert isinstance(kinds, tuple), lang   # explicit declaration, never silent absence


def test_coverage_is_persisted_in_graph_data():
    data = _extract()
    assert dict(data.coverage) == {lang: tuple(kinds) for lang, kinds in COVERAGE.items()}
