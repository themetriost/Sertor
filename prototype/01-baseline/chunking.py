"""Chunking: code-aware (tree-sitter) per il codice, heading/markdown per i doc.

Per il codice il chunker è selezionabile via config (`CODE_CHUNKER`):
- `treesitter` (default): chunk allineati ai confini sintattici (funzioni/classi/metodi),
  con metadati strutturali (`symbol`, `symbol_kind`, `qualname`, righe). Vedi
  `shared/chunking_code.py`.
- `recursive`: splitter ricorsivo di LangChain (size-driven), fallback storico.

I documenti Markdown usano sempre lo splitter ricorsivo per heading.
"""
from __future__ import annotations

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from shared.chunking_code import code_chunks
from shared.config import settings

_code_splitter = RecursiveCharacterTextSplitter.from_language(
    Language.PYTHON, chunk_size=900, chunk_overlap=120
)
_md_splitter = RecursiveCharacterTextSplitter.from_language(
    Language.MARKDOWN, chunk_size=1200, chunk_overlap=150
)


def _recursive_code(doc) -> list[dict]:
    chunks = [c for c in _code_splitter.split_text(doc.text) if c.strip()]
    return [
        {"id": f"{doc.id}#{i}", "text": ch, "metadata": {**doc.metadata, "chunk": i}}
        for i, ch in enumerate(chunks)
    ]


def _treesitter_code(doc) -> list[dict] | None:
    """Chunk code-aware con metadati strutturali; None se la lingua non è supportata."""
    parts = code_chunks(doc.text, doc.metadata.get("language", "python"))
    if parts is None:
        return None
    out: list[dict] = []
    for i, p in enumerate(parts):
        # Chroma non accetta metadati None: includi solo i campi valorizzati.
        extra = {k: p[k] for k in ("symbol", "symbol_kind", "qualname", "start_line", "end_line")
                 if p.get(k) is not None}
        out.append({"id": f"{doc.id}#{i}", "text": p["text"],
                    "metadata": {**doc.metadata, "chunk": i, **extra}})
    return out


def chunk_doc(doc) -> list[dict]:
    """`doc` è uno shared.loaders.Doc. Ritorna chunk con id e metadata arricchiti."""
    if doc.metadata["source"] == "code":
        if settings.code_chunker == "treesitter":
            ts = _treesitter_code(doc)
            if ts is not None:
                return ts
        return _recursive_code(doc)
    # documentazione: splitter markdown
    chunks = [c for c in _md_splitter.split_text(doc.text) if c.strip()]
    return [
        {"id": f"{doc.id}#{i}", "text": ch, "metadata": {**doc.metadata, "chunk": i}}
        for i, ch in enumerate(chunks)
    ]


def build_chunks(docs) -> list[dict]:
    out: list[dict] = []
    for d in docs:
        out.extend(chunk_doc(d))
    return out
