"""Test US2 — size fallback (REQ-009) and Markdown chunking (REQ-008) via dispatcher."""
from __future__ import annotations

import dataclasses

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import ChunkerKind, DocType, Document
from sertor_core.services.chunking.dispatch import chunk_document
from sertor_core.services.chunking.fallback import size_chunks
from sertor_core.services.chunking.markdown import markdown_chunks

S = Settings.load(env_file=None)


def test_size_fallback_no_error_on_arbitrary_text():
    text = "\n".join(f"riga numero {i}" for i in range(200))
    chunks = size_chunks(text, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    assert all(c["text"] for c in chunks)
    assert all(c["start_line"] <= c["end_line"] for c in chunks)


def test_dispatch_uses_fallback_for_unsupported_language():
    doc = Document(
        id="legacy/deploy.ps1",
        text="function Deploy {\n  Write-Host 'x'\n}\n",
        doc_type=DocType.CODE,
        language="powershell",
    )
    chunks = chunk_document(doc, S)
    assert chunks  # no error, at least one chunk
    assert all(c.metadata.chunker is ChunkerKind.SIZE_FALLBACK for c in chunks)


def test_markdown_heading_hierarchy():
    md = (
        "# Guida\n\nintro\n\n"
        "## Installazione\n\ntesto\n\n"
        "### Prerequisiti\n\nservono cose\n\n"
        "## Uso\n\ncome si usa\n"
    )
    chunks = markdown_chunks(md)
    paths = [c["heading_path"] for c in chunks]
    assert ("Guida",) in paths
    assert ("Guida", "Installazione") in paths
    assert ("Guida", "Installazione", "Prerequisiti") in paths
    assert ("Guida", "Uso") in paths  # 'Uso' closes the 'Installazione' section (same level)


def test_dispatch_markdown_sets_markdown_chunker_and_path():
    doc = Document(
        id="docs/guide.md",
        text="# Titolo\n\ncorpo\n\n## Sezione\n\naltro\n",
        doc_type=DocType.DOC,
        language="markdown",
    )
    chunks = chunk_document(doc, S)
    assert all(c.metadata.chunker is ChunkerKind.MARKDOWN for c in chunks)
    assert any(c.metadata.heading_path == ("Titolo", "Sezione") for c in chunks)


def test_chunk_ids_are_stable_and_positional():
    doc = Document(
        id="app/calculator.py",
        text="def a():\n    return 1\n\ndef b():\n    return 2\n",
        doc_type=DocType.CODE,
        language="python",
    )
    first = chunk_document(doc, S)
    second = chunk_document(doc, S)
    assert [c.id for c in first] == [c.id for c in second]          # idempotent (REQ-010)
    assert first[0].id == "app/calculator.py#0"                      # positional id
    assert all(c.id.startswith("app/calculator.py#") for c in first)


# --- oversized chunk capping (robustness: embedders reject inputs over a token budget) -----------

_SMALL_CAP = dataclasses.replace(S, max_chunk_chars=120, chunk_overlap=20)


def test_oversized_markdown_section_is_capped():
    # A single heading section larger than the cap must be sub-split, not emitted whole.
    body = "\n".join(f"line {i} of a very long section" for i in range(60))
    doc = Document(id="docs/big.md", text=f"# Huge\n\n{body}\n", doc_type=DocType.DOC,
                   language="markdown")
    chunks = chunk_document(doc, _SMALL_CAP)
    assert len(chunks) > 1                                            # actually split
    assert all(len(c.text) <= _SMALL_CAP.max_chunk_chars for c in chunks)  # no chunk over the cap
    assert all(c.metadata.chunker is ChunkerKind.MARKDOWN for c in chunks)  # metadata preserved
    assert all(c.metadata.heading_path == ("Huge",) for c in chunks)        # heading inherited
    assert [c.id for c in chunks] == [f"docs/big.md#{i}" for i in range(len(chunks))]  # contiguous


def test_oversized_chunk_line_numbers_offset_onto_document():
    # Sub-pieces of an oversized section keep document-relative (not section-relative) line numbers.
    body = "\n".join(f"line {i}" for i in range(60))
    doc = Document(id="docs/big.md", text=f"# Huge\n\n{body}\n", doc_type=DocType.DOC,
                   language="markdown")
    chunks = chunk_document(doc, _SMALL_CAP)
    assert chunks[0].metadata.start_line == 1                     # section starts at the heading
    assert all(c.metadata.start_line <= c.metadata.end_line for c in chunks)
    assert chunks[-1].metadata.end_line <= doc.text.count("\n") + 1   # within the document


def test_small_chunks_unchanged_by_cap():
    # Regression: documents whose units are within the cap are not altered.
    doc = Document(id="docs/guide.md", text="# Titolo\n\ncorpo\n\n## Sezione\n\naltro\n",
                   doc_type=DocType.DOC, language="markdown")
    capped = chunk_document(doc, _SMALL_CAP)
    plain = chunk_document(doc, S)
    assert [c.text for c in capped] == [c.text for c in plain]         # untouched under the cap
