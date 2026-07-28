"""Test US2 — frontmatter and wikilink parsing (research D2)."""
from __future__ import annotations

from sertor_core.wiki_tools.frontmatter import (
    extract_wikilinks,
    has_frontmatter,
    missing_required,
    parse_frontmatter,
)

_PAGE = """---
title: RAG
type: concept
tags: [rag, retrieval]
created: 2026-06-01
updated: 2026-06-05
---

# RAG

Vedi [[chunking]] e [[embeddings|gli embedding]] e di nuovo [[chunking]].
"""

_BLOCK_LIST = """---
title: T
tags:
  - alpha
  - beta
---
corpo
"""


def test_parse_scalar_and_inline_list():
    fm = parse_frontmatter(_PAGE)
    assert fm["title"] == "RAG"
    assert fm["type"] == "concept"
    assert fm["tags"] == ["rag", "retrieval"]


def test_parse_block_list():
    fm = parse_frontmatter(_BLOCK_LIST)
    assert fm["tags"] == ["alpha", "beta"]


def test_has_frontmatter():
    assert has_frontmatter(_PAGE) is True
    assert has_frontmatter("# Nessun frontmatter\n") is False


def test_extract_wikilinks_dedup_and_alias():
    links = extract_wikilinks(_PAGE)
    assert links == ["chunking", "embeddings"]  # alias discarded, dedup preserving order


def test_wikilinks_ignore_frontmatter_block():
    text = "---\ntitle: [[non-un-link]]\n---\nCorpo con [[reale]].\n"
    assert extract_wikilinks(text) == ["reale"]


def test_missing_required_detects_absent_and_empty():
    fm = {"title": "X", "type": "", "tags": [], "created": "2026-01-01"}
    missing = missing_required(fm, ["title", "type", "tags", "created", "updated"])
    assert missing == ["type", "tags", "updated"]


def test_missing_required_empty_when_complete():
    fm = parse_frontmatter(_PAGE)
    assert missing_required(fm, ["title", "type", "tags", "created", "updated"]) == []

def test_wikilinks_ignore_fenced_code_block():
    """A TOML array-of-tables inside a fence is not a wikilink (real case: concepts/speclift.md)."""
    text = (
        "Il rendering EARS e' template puro:\n\n"
        "```toml\n"
        "[[requirement]]\n"
        'id = "REQ-001"\n'
        "```\n\n"
        "Vedi [[speclift]].\n"
    )
    assert extract_wikilinks(text) == ["speclift"]


def test_wikilinks_ignore_inline_code_span():
    """`[[x]]` named literally while explaining the syntax is not a link.

    Real cases: concepts/daily-distill-floor.md, experiments/feat-022-pulizia-stile-skill.md.
    """
    text = (
        "Rileva i wikilink orfani (`[[x]]` senza pagina) e zero orfani `[[wikilink]]`;"
        " vedi [[lint]].\n"
    )
    assert extract_wikilinks(text) == ["lint"]


def test_wikilinks_ignore_tilde_fence_and_multi_backtick_span():
    text = "~~~\n[[dentro-tilde]]\n~~~\n\nUno span doppio ``[[dentro-span]]`` e poi [[fuori]].\n"
    assert extract_wikilinks(text) == ["fuori"]


def test_wikilinks_unterminated_fence_stays_conservative():
    """An unterminated fence must NOT swallow the rest of the page (we prefer a false link)."""
    text = "```python\nprint('x')\n\nTesto dopo con [[reale]].\n"
    assert extract_wikilinks(text) == ["reale"]


def test_wikilinks_survive_around_code():
    """Links before and after code are still found (the strip must not eat real content)."""
    text = "Prima [[uno]].\n\n```\n[[finto]]\n```\n\nDopo [[due]] e `codice` finale.\n"
    assert extract_wikilinks(text) == ["uno", "due"]


def test_wikilinks_alias_pipe_escaped_in_table():
    r"""`[[target\|alias]]` — the Obsidian-compatible escape needed inside a Markdown table.

    Without stripping the trailing backslash every aliased link in a table reads as broken
    (real case: wiki/sources/archivio-processati.md).
    """
    text = r"| [[speclift-handoff-sinthari\|Handoff SpecLift]] | Sinthari | ok |" + "\n"
    assert extract_wikilinks(text) == ["speclift-handoff-sinthari"]
