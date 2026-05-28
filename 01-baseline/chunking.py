"""Chunking baseline: language-aware per il codice, heading/markdown per i doc.

Baseline volutamente semplice (splitter ricorsivi di LangChain). Il chunking
code-aware via tree-sitter/AST è uno step di rifinitura successivo.
"""
from __future__ import annotations

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

_code_splitter = RecursiveCharacterTextSplitter.from_language(
    Language.PYTHON, chunk_size=900, chunk_overlap=120
)
_md_splitter = RecursiveCharacterTextSplitter.from_language(
    Language.MARKDOWN, chunk_size=1200, chunk_overlap=150
)


def chunk_doc(doc) -> list[dict]:
    """`doc` è uno shared.loaders.Doc. Ritorna chunk con id e metadata arricchiti."""
    splitter = _code_splitter if doc.metadata["source"] == "code" else _md_splitter
    chunks = [c for c in splitter.split_text(doc.text) if c.strip()]
    return [
        {"id": f"{doc.id}#{i}", "text": ch, "metadata": {**doc.metadata, "chunk": i}}
        for i, ch in enumerate(chunks)
    ]


def build_chunks(docs) -> list[dict]:
    out: list[dict] = []
    for d in docs:
        out.extend(chunk_doc(d))
    return out
