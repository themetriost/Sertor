"""Test del setup del wiki (FEAT-010, US1): struttura, binding del trigger, idempotenza + CLI."""
from __future__ import annotations

from pathlib import Path

from sertor_cli.cli import main
from sertor_core.services.wiki_setup import init_wiki, trigger_binding_path
from sertor_core.wiki.conventions import INGESTED_SOURCES_DIR, THEMATIC_DIRS


def test_init_creates_structure(tmp_path: Path):
    root = tmp_path / "wiki"
    report = init_wiki(root, install_binding=False)

    assert report.created is True
    assert (root / "index.md").exists()
    assert (root / "log.md").exists()
    for d in THEMATIC_DIRS:
        assert (root / d).is_dir()


def test_install_binding_marks_trigger(tmp_path: Path):
    root = tmp_path / "wiki"
    report = init_wiki(root, install_binding=True)

    assert report.binding_installed is True
    assert trigger_binding_path(root).exists()


def test_init_is_idempotent(tmp_path: Path):
    root = tmp_path / "wiki"
    init_wiki(root, install_binding=True)
    first = (root / "index.md").read_text(encoding="utf-8")

    report2 = init_wiki(root, install_binding=True)  # re-run

    assert report2.created is False
    assert report2.binding_installed is False  # già installato: no-op
    assert (root / "index.md").read_text(encoding="utf-8") == first  # invariato


def test_initial_ingest_copies_into_ingested_sources(tmp_path: Path):
    root = tmp_path / "wiki"
    src = tmp_path / "doc.md"
    src.write_text("# Doc esterna\n", encoding="utf-8")

    report = init_wiki(root, initial_ingest=src)

    assert report.ingested == 1
    assert (root / INGESTED_SOURCES_DIR / "doc.md").exists()


def test_cli_wiki_init(tmp_path: Path, capsys):
    root = tmp_path / "wiki"
    code = main(["wiki", "init", str(root)])

    assert code == 0
    assert (root / "index.md").exists()
    assert trigger_binding_path(root).exists()
