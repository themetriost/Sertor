"""Test US1 — inizializzazione della struttura del wiki (REQ-001..006)."""
from __future__ import annotations

from sertor_core.wiki.conventions import THEMATIC_DIRS, Brief, page_relpath, render_page, slugify
from sertor_core.wiki.structure import create_wiki


def test_create_produces_structure(tmp_path):
    root = tmp_path / "wiki"
    res = create_wiki(root, today="2026-06-03")
    assert res.changed
    for d in THEMATIC_DIRS:                      # cartelle tematiche (REQ-001)
        assert (root / d).is_dir()
    assert (root / "index.md").exists()
    assert (root / "log.md").exists()


def test_create_is_non_destructive(tmp_path):
    root = tmp_path / "wiki"
    create_wiki(root, today="2026-06-03")
    (root / "index.md").write_text("CONTENUTO MIO\n", encoding="utf-8")
    res = create_wiki(root, today="2026-06-04")   # re-invoke
    assert res.changed is False                   # nulla creato
    # non sovrascritto (REQ-002)
    assert (root / "index.md").read_text(encoding="utf-8") == "CONTENUTO MIO\n"


def test_conventions_kebab_and_path():
    assert slugify("Decisione su X!") == "decisione-su-x"
    assert page_relpath("synthesis", "Mia Pagina") == "syntheses/mia-pagina.md"


def test_page_has_frontmatter_and_heading():
    page = render_page(
        Brief(title="Tema", kind="concept", body="corpo", tags=["a"], sources=["s"]),
        created="2026-06-03", updated="2026-06-03",
    )
    assert page.startswith("---\n")               # frontmatter YAML (REQ-003)
    assert "title: Tema" in page and "type: concept" in page
    assert "tags: [a]" in page and "sources: [s]" in page
    assert "# Tema" in page
