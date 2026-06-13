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
