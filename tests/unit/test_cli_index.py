"""Test US1 — CLI `sertor-rag index <path>` (FR-001..009, FR-015, FR-023..024, SC-001/003..005).

Tutto senza rete: il `build_indexer` del core è sostituito (monkeypatch) con un orchestratore reale
cablato su `FakeEmbedder` + `InMemoryStore` (`tests/fixtures/mocks.py`).
"""
from __future__ import annotations

import json

import pytest

from sertor_core.cli import __main__ as cli
from sertor_core.config.settings import Settings
from sertor_core.services.indexing import IndexingService
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    """Isola i test dal `.env` del repo: `Settings.load()` non deve leggere/iniettare il file.

    `load_dotenv(override=True)` muterebbe `os.environ` in modo non ripristinabile da monkeypatch,
    contaminando i test successivi (es. `RAG_BACKEND=azure` dal .env locale). I test che vogliono
    una config specifica sovrascrivono comunque `Settings.load` dopo questa fixture.
    """
    _orig = Settings.load.__func__
    monkeypatch.setattr(
        Settings, "load", classmethod(lambda c, env_file=".env": _orig(c, env_file=None))
    )


@pytest.fixture
def patched_indexer(monkeypatch):
    """Sostituisce `build_indexer` nella CLI con un orchestratore su mock; espone l'embedder."""
    embedder = FakeEmbedder(dim=8)
    store = InMemoryStore()

    def _factory(settings: Settings):
        coll = f"{settings.corpus}__{embedder.name.replace(':', '_')}"
        return IndexingService(embedder, store, coll, settings)

    monkeypatch.setattr(cli, "build_indexer", _factory)
    return embedder, store


def _run(argv):
    return cli.main(argv)


# --------------------------------------------------------------------- successo
def test_index_success_human_output(patched_indexer, sample_repo, capsys):
    code = _run(["index", str(sample_repo)])
    out = capsys.readouterr().out
    assert code == 0
    assert "chunks=" in out
    assert "embedding_dim=" in out
    assert "documents=" in out


def test_index_success_json_output(patched_indexer, sample_repo, capsys):
    code = _run(["index", str(sample_repo), "--json"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert {"collection", "documents", "chunks", "embedding_dim", "elapsed_ms"} <= payload.keys()
    assert payload["chunks"] >= 1
    assert payload["embedding_dim"] == 8


# --------------------------------------------------------------------- errori path
def test_index_nonexistent_path_exit_1(patched_indexer, tmp_path, capsys):
    code = _run(["index", str(tmp_path / "non-esiste")])
    err = capsys.readouterr().err
    assert code == 1
    assert "error:" in err


def test_index_path_is_file_exit_1(patched_indexer, tmp_path, capsys):
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    code = _run(["index", str(f)])
    err = capsys.readouterr().err
    assert code == 1
    assert "error:" in err


# ------------------------------------------------------------- backend incompleto (FR-015)
def test_index_incomplete_backend_blocks_before_embedding(monkeypatch, sample_repo, capsys):
    # Azure senza credenziali: blocca PRIMA di costruire/usare l'indexer (FakeEmbedder mai usato)
    called = {"build": False}

    def _factory(settings):
        called["build"] = True
        raise AssertionError("build_indexer non deve essere chiamato su backend incompleto")

    monkeypatch.setattr(cli, "build_indexer", _factory)
    # config azure incompleta, iniettata senza leggere il .env del repo
    monkeypatch.setattr(
        cli.Settings, "load",
        classmethod(lambda c, env_file=".env": c(backend="azure", store_backend="local")),
    )
    code = _run(["index", str(sample_repo)])
    err = capsys.readouterr().err
    assert code == 1
    assert "AZURE_OPENAI_ENDPOINT" in err
    assert called["build"] is False


# --------------------------------------------------------------------- install != run (FR-023)
def test_importing_cli_runs_nothing():
    import importlib

    import sertor_core.cli as pkg

    importlib.reload(pkg)  # re-import non deve eseguire alcuna operazione RAG


# --------------------------------------------------------------------- repo-agnosticità (SC-005)
def test_index_two_repos_namespaced(monkeypatch, tmp_path, capsys):
    embedder = FakeEmbedder(dim=8)
    store = InMemoryStore()

    def _factory(settings):
        coll = f"{settings.corpus}__{embedder.name.replace(':', '_')}"
        return IndexingService(embedder, store, coll, settings)

    monkeypatch.setattr(cli, "build_indexer", _factory)

    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    for r in (repo_a, repo_b):
        r.mkdir()
        (r / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    assert _run(["index", str(repo_a), "--corpus", "ca"]) == 0
    assert _run(["index", str(repo_b), "--corpus", "cb"]) == 0
    capsys.readouterr()
    cols = store.list_collections()
    assert any(c.startswith("ca__") for c in cols)
    assert any(c.startswith("cb__") for c in cols)
    # i file dei due repository non sono stati alterati
    assert (repo_a / "m.py").read_text(encoding="utf-8") == "def f():\n    return 1\n"
    assert (repo_b / "m.py").read_text(encoding="utf-8") == "def f():\n    return 1\n"


# ------------------------------------------------------------- --corpus override (FR-009/D7)
def test_index_corpus_override(patched_indexer, sample_repo, capsys):
    _, store = patched_indexer
    code = _run(["index", str(sample_repo), "--corpus", "myns"])
    capsys.readouterr()
    assert code == 0
    assert any(c.startswith("myns__") for c in store.list_collections())


# --------------------------------------------------------------------- exit code 2 (FR-003)
def test_unknown_subcommand_exit_2():
    with pytest.raises(SystemExit) as exc:
        _run(["unknown-cmd"])
    assert exc.value.code == 2


def test_index_without_path_exit_2():
    with pytest.raises(SystemExit) as exc:
        _run(["index"])
    assert exc.value.code == 2


def test_search_without_query_exit_2():
    with pytest.raises(SystemExit) as exc:
        _run(["search"])
    assert exc.value.code == 2


def test_search_invalid_type_exit_2():
    with pytest.raises(SystemExit) as exc:
        _run(["search", "q", "--type", "invalid"])
    assert exc.value.code == 2


def test_no_subcommand_exit_2():
    with pytest.raises(SystemExit) as exc:
        _run([])
    assert exc.value.code == 2
