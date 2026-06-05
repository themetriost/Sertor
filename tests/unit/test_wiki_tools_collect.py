"""Test US4 — enumerazione delle pagine + metadati (FR-007)."""
from __future__ import annotations

from pathlib import Path

from sertor_core.wiki_tools.collect import collect
from sertor_core.wiki_tools.profile import load_profile

_DOC_ONLY = Path(__file__).parents[1] / "fixtures" / "doc_only_host" / "wiki.config.toml"

_CONFIG = """\
profile = "code+doc"
language = "it"
root = "wiki"
index_file = "index.md"
log_file = "log.md"

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"
"""

_FM = (
    "---\ntitle: RAG\ntype: concept\ntags: [rag, x]\n"
    "created: 2026-01-01\nupdated: 2026-01-02\n---\n"
)


def test_collect_returns_expected_map(tmp_path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    wiki = tmp_path / "wiki"
    (wiki / "concepts").mkdir(parents=True)
    (wiki / "index.md").write_text("# i\n", "utf-8")
    (wiki / "log.md").write_text("# l\n", "utf-8")
    (wiki / "concepts" / "rag.md").write_text(_FM + "\nVedi [[chunking]].\n", "utf-8")

    res = collect(load_profile(cfg))
    assert res.schema == "wiki.collect/1"
    assert res.root == "wiki"
    # index e log esclusi: una sola pagina di contenuto.
    assert len(res.pages) == 1
    page = res.pages[0]
    assert page["rel_path"] == "concepts/rag.md"  # identità POSIX stabile
    assert page["area"] == "concepts"
    assert page["type"] == "concept"
    assert page["title"] == "RAG"
    assert page["tags"] == ["rag", "x"]
    assert page["frontmatter_present"] is True
    assert page["wikilinks"] == ["chunking"]
    assert "text" not in page and "body" not in page  # niente corpo (FR-007)


def test_collect_on_doc_only_host():
    # Stesso enumeratore sull'ospite doc-only: rel_path POSIX, due pagine note.
    res = collect(load_profile(_DOC_ONLY))
    rels = {p["rel_path"] for p in res.pages}
    assert rels == {"guides/getting-started.md", "reference/api-overview.md"}
    assert res.index == "index.md"
    assert res.log == "changelog.md"


def test_collect_is_deterministically_ordered(tmp_path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    wiki = tmp_path / "wiki" / "concepts"
    wiki.mkdir(parents=True)
    for name in ("zeta", "alpha", "mid"):
        (wiki / f"{name}.md").write_text(_FM + "x\n", "utf-8")
    res = collect(load_profile(cfg))
    rels = [p["rel_path"] for p in res.pages]
    assert rels == sorted(rels)
