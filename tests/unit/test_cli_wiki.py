"""Test US3 — comando `sertor wiki index` (REQ-030/031)."""
from __future__ import annotations

from sertor_cli.cli import main
from sertor_core.domain.entities import IndexReport


def test_wiki_index_reports_documents(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        "sertor_cli.commands.wiki_cmd.index_wiki",
        lambda w, s: IndexReport(collection="c", documents=2, chunks=5, embedding_dim=8),
    )
    code = main(["wiki", "index", str(tmp_path)])
    assert code == 0
    assert "2" in capsys.readouterr().out


def test_wiki_index_empty_root_warns(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        "sertor_cli.commands.wiki_cmd.index_wiki",
        lambda w, s: IndexReport(collection="", documents=0, chunks=0),
    )
    code = main(["wiki", "index", str(tmp_path)])
    assert code == 0                                  # radice vuota → warning, non errore (REQ-031)
    assert "Nessuna" in capsys.readouterr().out
