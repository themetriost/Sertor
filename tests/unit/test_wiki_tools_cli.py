"""Test della CLI `sertor-wiki-tools upsert-index` (feature 010, contracts/cli-upsert-index.md).

Esercita `main(argv)` end-to-end su un wiki fittizio in `tmp_path`: parsing → funzione pura →
output umano/JSON ed exit code. Nessuna rete; stdin simulato via monkeypatch.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

from sertor_core.wiki_tools.__main__ import main
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.structure import init_structure

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


def _wiki(tmp_path: Path) -> Path:
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    init_structure(load_profile(cfg))
    return cfg


def _run(cfg: Path, *extra: str) -> int:
    return main(["upsert-index", "--config", str(cfg), *extra])


def test_upsert_index_insert_then_noop(tmp_path, capsys):
    cfg = _wiki(tmp_path)
    assert _run(cfg, "--page", "concepts/rag.md", "--summary", "Sintesi RAG.") == 0
    assert "action=insert" in capsys.readouterr().out
    index = tmp_path / "wiki" / "index.md"
    assert "- [[concepts/rag.md]] — Sintesi RAG." in index.read_text("utf-8")

    snapshot = index.read_bytes()
    assert _run(cfg, "--page", "concepts/rag.md", "--summary", "Sintesi RAG.") == 0
    assert "action=noop" in capsys.readouterr().out
    assert index.read_bytes() == snapshot          # idempotenza byte-identica (FR-012)


def test_upsert_index_update_in_place(tmp_path, capsys):
    cfg = _wiki(tmp_path)
    _run(cfg, "--page", "concepts/rag.md", "--summary", "vecchio")
    capsys.readouterr()
    assert _run(cfg, "--page", "concepts/rag.md", "--summary", "nuovo") == 0
    assert "action=update" in capsys.readouterr().out
    content = (tmp_path / "wiki" / "index.md").read_text("utf-8")
    assert content.count("[[concepts/rag.md]]") == 1 and "vecchio" not in content


def test_upsert_index_json_contract(tmp_path, capsys):
    cfg = _wiki(tmp_path)
    assert _run(cfg, "--page", "concepts/rag.md", "--summary", "Sintesi.", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"written": True, "action": "insert",
                       "page": "concepts/rag.md", "schema": "wiki.upsert_index/1"}


def test_upsert_index_summary_from_stdin_utf8(tmp_path, capsys, monkeypatch):
    # FR-017: sommario da stdin scritto fedelmente (caratteri non-ASCII, no mojibake).
    cfg = _wiki(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("Schéma è già qui — übersicht\n"))
    assert _run(cfg, "--page", "concepts/intl.md") == 0
    assert "- [[concepts/intl.md]] — Schéma è già qui — übersicht" in \
        (tmp_path / "wiki" / "index.md").read_text("utf-8")


def test_upsert_index_requires_page_and_summary(tmp_path, capsys, monkeypatch):
    cfg = _wiki(tmp_path)
    assert _run(cfg, "--summary", "senza pagina") == 1            # --page mancante
    assert "error" in capsys.readouterr().err
    monkeypatch.setattr("sys.stdin", io.StringIO(""))             # niente summary, stdin vuoto
    assert _run(cfg, "--page", "concepts/x.md") == 1
    assert "error" in capsys.readouterr().err


def test_upsert_index_missing_index_fails_explicitly(tmp_path, capsys):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")                     # struttura NON inizializzata
    assert _run(cfg, "--page", "concepts/x.md", "--summary", "s") == 1   # FR-015
    assert "error" in capsys.readouterr().err


def test_upsert_index_rejects_empty_and_multiline(tmp_path, capsys):
    # FR-018: errore esplicito, exit 1, indice invariato in entrambi i casi.
    cfg = _wiki(tmp_path)
    index = tmp_path / "wiki" / "index.md"
    snapshot = index.read_bytes()
    assert _run(cfg, "--page", "concepts/x.md", "--summary", "   ") == 1
    assert _run(cfg, "--page", "concepts/x.md", "--summary", "riga 1\nriga 2") == 1
    capsys.readouterr()
    assert index.read_bytes() == snapshot
