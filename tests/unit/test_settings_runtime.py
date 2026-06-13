"""Self-localizing runtime of `Settings.load` (cwd/.env fix, language/hygiene follow-up feature).

The installed runtime lives in `.sertor/` with its own venv: `sertor-rag`/`sertor-wiki-tools` must
load `.sertor/.env` and anchor the index at `.sertor/.index` **from any cwd**, not only when
launched from inside `.sertor/`. The layout is simulated here with a fake `sys.prefix`.
"""
from __future__ import annotations

import os
from pathlib import Path

from sertor_core.config.settings import Settings, _resolve_env_path


def test_resolve_env_path_none_means_no_load():
    assert _resolve_env_path(None) is None


def test_env_file_none_keeps_relative_index(monkeypatch, tmp_path):
    """`env_file=None` (test isolation) remains unchanged: no .env, relative index."""
    monkeypatch.chdir(tmp_path)
    s = Settings.load(env_file=None)
    assert s.index_dir == Path(".index")


def test_runtime_dotenv_loaded_from_any_cwd(monkeypatch, tmp_path):
    """cwd WITHOUT .env → loads `.sertor/.env` (next to the venv) and anchors the index there."""
    sertor_dir = tmp_path / ".sertor"
    (sertor_dir / ".venv").mkdir(parents=True)
    (sertor_dir / ".env").write_text(
        "RAG_BACKEND=azure\nAZURE_OPENAI_ENDPOINT=https://x\n"
        "AZURE_OPENAI_API_KEY=k\nAZURE_OPENAI_EMBED_DEPLOYMENT=d\nSERTOR_CORPUS=kaelen\n",
        encoding="utf-8",
    )
    other = tmp_path / "host-root"
    other.mkdir()
    monkeypatch.chdir(other)                          # different cwd, without .env
    monkeypatch.setattr(os, "environ", dict(os.environ))  # isolate load_dotenv writes
    monkeypatch.delenv("RAG_BACKEND", raising=False)
    monkeypatch.setattr("sertor_core.config.settings.sys.prefix", str(sertor_dir / ".venv"))

    s = Settings.load()                               # default ".env": auto-localizes to runtime
    assert s.backend == "azure"
    assert s.corpus == "kaelen"
    assert s.index_dir == sertor_dir / ".index"       # anchored to .sertor/, not to cwd


def test_cwd_dotenv_takes_precedence(monkeypatch, tmp_path):
    """If the cwd has a `.env`, it wins over the runtime one (explicit > runtime)."""
    (tmp_path / ".env").write_text("RAG_BACKEND=local\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("RAG_BACKEND", raising=False)
    s = Settings.load()
    assert s.backend == "local"
    # cwd `.env` is relative → relative index `.index` (preserved behavior, = cwd/.index)
    assert s.index_dir == Path(".index")
