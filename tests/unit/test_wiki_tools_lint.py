"""Test US3 — lint strutturale; SC-004 (100% difetti, 0 falsi positivi) e SC-005 (offline)."""
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
    # index referenzia entrambe le pagine; le pagine si linkano tra loro → nessun orfano.
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
    # Difetto 1: link rotto verso pagina inesistente.
    (wiki / "concepts" / "rag.md").write_text(
        _FM.format(t="RAG") + "\nVedi [[chunking]] e [[inesistente]].\n", "utf-8"
    )
    # Difetto 2: pagina orfana (non referenziata da index né da altre pagine).
    (wiki / "concepts" / "orfana.md").write_text(_FM.format(t="Orfana") + "\nsola.\n", "utf-8")
    # Difetto 3: pagina senza frontmatter (e referenziata per non essere anche orfana).
    (wiki / "concepts" / "nudo.md").write_text("# Nudo\n\nNiente frontmatter.\n", "utf-8")
    idx = wiki / "index.md"
    idx.write_text(idx.read_text("utf-8") + "- [[nudo]]\n", "utf-8")

    res = lint(p)
    assert {b["target"] for b in res.broken_links} == {"inesistente"}
    assert "concepts/orfana.md" in res.orphans
    assert any(d["page"] == "concepts/nudo.md" for d in res.missing_frontmatter)


def test_sc005_lint_is_offline(tmp_path, monkeypatch):
    # SC-005: nessuna chiamata di rete durante il lint (zero LLM / offline).
    def _no_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("il lint non deve aprire connessioni di rete")

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
    res = lint(load_profile(cfg))  # wiki/ assente: nessuna pagina
    assert res.orphans == []


def test_stub_is_wanted_not_broken_nor_orphan(tmp_path):
    # Un forward-link risolto a uno stub (status: stub) è intenzionale: il link NON è broken, lo
    # stub NON è orfano (lo linka chi l'ha motivato), e compare nella worklist `stubs`.
    p = _clean_wiki(tmp_path)
    wiki = tmp_path / "wiki"
    # rag punta in avanti a un nodo da creare, realizzato come stub.
    (wiki / "concepts" / "rag.md").write_text(
        _FM.format(t="RAG") + "\nVedi [[chunking]] e [[futuro]].\n", "utf-8"
    )
    stub_fm = (
        "---\ntitle: Futuro\ntype: concept\ntags: [x]\n"
        "created: 2026-01-01\nupdated: 2026-01-02\nstatus: stub\n---\n"
    )
    (wiki / "concepts" / "futuro.md").write_text(stub_fm + "\n> 🚧 STUB\n", "utf-8")

    res = lint(p)
    assert res.broken_links == []  # [[futuro]] risolve allo stub
    assert "concepts/futuro.md" not in res.orphans  # linkato da rag
    assert res.stubs == ["concepts/futuro.md"]  # worklist dei nodi da riempire
    assert res.schema == "wiki.lint/1"  # additivo, nessun bump
