"""Runtime auto-localizzante di `Settings.load` (fix cwd/.env, feature lingua/igiene follow-up).

Il runtime installato vive in `.sertor/` col proprio venv: `sertor-rag`/`sertor-wiki-tools` devono
caricare `.sertor/.env` e ancorare l'indice in `.sertor/.index` **da qualsiasi cwd**, non solo
quando si lancia da dentro `.sertor/`. Qui si simula il layout con un finto `sys.prefix`.
"""
from __future__ import annotations

import os
from pathlib import Path

from sertor_core.config.settings import Settings, _resolve_env_path


def test_resolve_env_path_none_means_no_load():
    assert _resolve_env_path(None) is None


def test_env_file_none_keeps_relative_index(monkeypatch, tmp_path):
    """`env_file=None` (isolamento test) resta identico: nessun .env, indice relativo."""
    monkeypatch.chdir(tmp_path)
    s = Settings.load(env_file=None)
    assert s.index_dir == Path(".index")


def test_runtime_dotenv_loaded_from_any_cwd(monkeypatch, tmp_path):
    """cwd SENZA .env → carica `.sertor/.env` (accanto al venv) e ancora l'indice lì."""
    sertor_dir = tmp_path / ".sertor"
    (sertor_dir / ".venv").mkdir(parents=True)
    (sertor_dir / ".env").write_text(
        "RAG_BACKEND=azure\nAZURE_OPENAI_ENDPOINT=https://x\n"
        "AZURE_OPENAI_API_KEY=k\nAZURE_OPENAI_EMBED_DEPLOYMENT=d\nSERTOR_CORPUS=kaelen\n",
        encoding="utf-8",
    )
    other = tmp_path / "host-root"
    other.mkdir()
    monkeypatch.chdir(other)                          # cwd diverso, senza .env
    monkeypatch.setattr(os, "environ", dict(os.environ))  # isola le scritture di load_dotenv
    monkeypatch.delenv("RAG_BACKEND", raising=False)
    monkeypatch.setattr("sertor_core.config.settings.sys.prefix", str(sertor_dir / ".venv"))

    s = Settings.load()                               # default ".env": auto-localizza al runtime
    assert s.backend == "azure"
    assert s.corpus == "kaelen"
    assert s.index_dir == sertor_dir / ".index"       # ancorato a .sertor/, non al cwd


def test_cwd_dotenv_takes_precedence(monkeypatch, tmp_path):
    """Se il cwd ha un `.env`, vince su quello del runtime (esplicito > runtime)."""
    (tmp_path / ".env").write_text("RAG_BACKEND=local\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("RAG_BACKEND", raising=False)
    s = Settings.load()
    assert s.backend == "local"
    # `.env` del cwd è relativo → indice relativo `.index` (comportamento preservato, = cwd/.index)
    assert s.index_dir == Path(".index")
