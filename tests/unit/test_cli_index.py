"""Test US1 — CLI `sertor-rag index <path>` (FR-001..009, FR-015, FR-023..024, SC-001/003..005).

All without network: the core's `build_indexer` is replaced (monkeypatch) with a real orchestrator
wired to `FakeEmbedder` + `InMemoryStore` (`tests/fixtures/mocks.py`).
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
    """Isolate tests from the repo's `.env`: `Settings.load()` must not read/inject the file.

    `load_dotenv(override=True)` would mutate `os.environ` in a way not restorable by monkeypatch,
    contaminating subsequent tests (e.g. `RAG_BACKEND=azure` from the local .env). Tests that need
    a specific config override `Settings.load` themselves after this fixture.
    """
    _orig = Settings.load.__func__
    monkeypatch.setattr(
        Settings, "load", classmethod(lambda c, env_file=".env": _orig(c, env_file=None))
    )


@pytest.fixture
def patched_indexer(monkeypatch):
    """Replace `build_indexer` in the CLI with a mock-backed orchestrator; exposes the embedder."""
    embedder = FakeEmbedder(dim=8)
    store = InMemoryStore()

    def _factory(settings: Settings):
        coll = f"{settings.corpus}__{embedder.name.replace(':', '_')}"
        return IndexingService(embedder, store, coll, settings)

    monkeypatch.setattr(cli, "build_indexer", _factory)
    return embedder, store


def test_index_wires_observability(tmp_path, patched_indexer, monkeypatch):
    """The index command must call enable_observability (else SERTOR_OBSERVABILITY is a no-op)."""
    calls: list[Settings] = []
    monkeypatch.setattr(cli, "enable_observability", lambda s: calls.append(s) or False)
    assert cli.main(["index", str(tmp_path)]) == 0
    assert len(calls) == 1


def _run(argv):
    return cli.main(argv)


# --------------------------------------------------------------------- success
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


# --------------------------------------------------------------------- path errors
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
    # Azure without credentials: blocks BEFORE building/using the indexer (FakeEmbedder never used)
    called = {"build": False}

    def _factory(settings):
        called["build"] = True
        raise AssertionError("build_indexer non deve essere chiamato su backend incompleto")

    monkeypatch.setattr(cli, "build_indexer", _factory)
    # incomplete azure config, injected without reading the repo's .env
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

    importlib.reload(pkg)  # re-import must not execute any RAG operation


# --------------------------------------------------------------------- repo-agnosticism (SC-005)
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
    # files of the two repositories have not been altered
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
