"""Test US3 — structural lint; SC-004 (100% defects, 0 false positives) and SC-005 (offline)."""
from __future__ import annotations

import socket
from pathlib import Path

import pytest

from sertor_core.wiki_tools.lint import lint
from sertor_core.wiki_tools.profile import load_profile

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

_FM = "---\ntitle: {t}\ntype: concept\ntags: [x]\ncreated: 2026-01-01\nupdated: 2026-01-02\n---\n"


def _clean_wiki(tmp_path: Path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    wiki = tmp_path / "wiki"
    (wiki / "concepts").mkdir(parents=True)
    # index references both pages; pages link to each other → no orphans.
    (wiki / "index.md").write_text("# Index\n\n- [[rag]]\n- [[chunking]]\n", "utf-8")
    (wiki / "log.md").write_text("# log\n", "utf-8")
    (wiki / "concepts" / "rag.md").write_text(
        _FM.format(t="RAG") + "\nVedi [[chunking]].\n", "utf-8"
    )
    (wiki / "concepts" / "chunking.md").write_text(
        _FM.format(t="Chunking") + "\nTorna a [[rag]].\n", "utf-8"
    )
    return load_profile(cfg)


def test_sc004_clean_wiki_has_no_false_positives(tmp_path):
    res = lint(_clean_wiki(tmp_path))
    assert res.broken_links == []
    assert res.orphans == []
    assert res.missing_frontmatter == []


def test_sc004_detects_all_injected_defects(tmp_path):
    p = _clean_wiki(tmp_path)
    wiki = tmp_path / "wiki"
    # Defect 1: broken link to a non-existent page.
    (wiki / "concepts" / "rag.md").write_text(
        _FM.format(t="RAG") + "\nVedi [[chunking]] e [[inesistente]].\n", "utf-8"
    )
    # Defect 2: orphan page (not referenced by index or any other page).
    (wiki / "concepts" / "orfana.md").write_text(_FM.format(t="Orfana") + "\nsola.\n", "utf-8")
    # Defect 3: page without frontmatter (referenced to avoid also being an orphan).
    (wiki / "concepts" / "nudo.md").write_text("# Nudo\n\nNiente frontmatter.\n", "utf-8")
    idx = wiki / "index.md"
    idx.write_text(idx.read_text("utf-8") + "- [[nudo]]\n", "utf-8")

    res = lint(p)
    assert {b["target"] for b in res.broken_links} == {"inesistente"}
    assert "concepts/orfana.md" in res.orphans
    assert any(d["page"] == "concepts/nudo.md" for d in res.missing_frontmatter)


def test_sc005_lint_is_offline(tmp_path, monkeypatch):
    # SC-005: no network calls during lint (zero LLM / offline).
    def _no_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("lint must not open network connections")

    monkeypatch.setattr(socket, "socket", _no_network)
    res = lint(_clean_wiki(tmp_path))
    assert res.schema == "wiki.lint/1"


def test_empty_wiki_lints_cleanly(tmp_path):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)
    (tmp_path / "wiki" / "index.md").write_text("# Index\n", "utf-8")
    (tmp_path / "wiki" / "log.md").write_text("# log\n", "utf-8")
    res = lint(load_profile(cfg))
    assert res.broken_links == [] and res.orphans == [] and res.missing_frontmatter == []


@pytest.mark.parametrize("missing_root", [True])
def test_lint_no_wiki_dir_is_clean(tmp_path, missing_root):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    res = lint(load_profile(cfg))  # wiki/ absent: no pages
    assert res.orphans == []


def test_stub_is_wanted_not_broken_nor_orphan(tmp_path):
    # A forward-link resolved to a stub (status: stub) is intentional: the link is NOT broken, the
    # stub is NOT an orphan (linked by whoever motivated it), and appears in the `stubs` worklist.
    p = _clean_wiki(tmp_path)
    wiki = tmp_path / "wiki"
    # rag points forward to a node to be created, realized as a stub.
    (wiki / "concepts" / "rag.md").write_text(
        _FM.format(t="RAG") + "\nVedi [[chunking]] e [[futuro]].\n", "utf-8"
    )
    stub_fm = (
        "---\ntitle: Futuro\ntype: concept\ntags: [x]\n"
        "created: 2026-01-01\nupdated: 2026-01-02\nstatus: stub\n---\n"
    )
    (wiki / "concepts" / "futuro.md").write_text(stub_fm + "\n> 🚧 STUB\n", "utf-8")

    res = lint(p)
    assert res.broken_links == []  # [[futuro]] resolves to the stub
    assert "concepts/futuro.md" not in res.orphans  # linked from rag
    assert res.stubs == ["concepts/futuro.md"]  # worklist of nodes to fill in
    assert res.schema == "wiki.lint/1"  # additive, no bump
