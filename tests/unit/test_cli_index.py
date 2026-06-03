"""Test US1 — comando `sertor index` (REQ-010..014, 060)."""
from __future__ import annotations

from sertor_cli.cli import main
from sertor_core.domain.errors import EmbeddingError
from sertor_core.services.indexing import IndexingService
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore


def _fake_indexer(settings):
    return IndexingService(FakeEmbedder(dim=8), InMemoryStore(), "cli-test", settings)


def test_index_reports_success(monkeypatch, sample_repo, capsys):
    monkeypatch.setattr("sertor_cli.commands.index_cmd.build_indexer", _fake_indexer)
    code = main(["index", str(sample_repo)])
    assert code == 0
    out = capsys.readouterr().out
    assert "chunk" in out.lower()


def test_index_json_output(monkeypatch, sample_repo, capsys):
    monkeypatch.setattr("sertor_cli.commands.index_cmd.build_indexer", _fake_indexer)
    code = main(["index", str(sample_repo), "--json"])
    assert code == 0
    import json

    data = json.loads(capsys.readouterr().out)
    assert data["chunks"] >= 1 and data["embedding_dim"] == 8


def test_index_missing_path_errors(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sertor_cli.commands.index_cmd.build_indexer", _fake_indexer)
    code = main(["index", str(tmp_path / "non-esiste")])
    assert code == 1                                  # exit non-zero (REQ-011)
    assert "errore" in capsys.readouterr().err.lower()


def test_index_provider_unavailable_aborts(monkeypatch, sample_repo, capsys):
    class _Boom(FakeEmbedder):
        def embed(self, texts):
            raise EmbeddingError("down", provider="fake", reason="net", retriable=True)

    monkeypatch.setattr(
        "sertor_cli.commands.index_cmd.build_indexer",
        lambda s: IndexingService(_Boom(dim=8), InMemoryStore(), "cli-test", s),
    )
    code = main(["index", str(sample_repo)])
    assert code == 1                                  # provider giù → bloccato (REQ-012/041)


def test_no_command_prints_help_and_nonzero(capsys):
    code = main([])                                   # install ≠ run: nessuna azione senza comando
    assert code == 1


def test_global_option_after_subcommand(monkeypatch, sample_repo):
    # regressione: le opzioni globali (-v) devono funzionare anche DOPO il sottocomando
    monkeypatch.setattr("sertor_cli.commands.index_cmd.build_indexer", _fake_indexer)
    assert main(["index", str(sample_repo), "-v"]) == 0
    assert main(["-v", "index", str(sample_repo)]) == 0  # e anche prima
