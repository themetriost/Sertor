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
        "SERTOR_EMBED_PROVIDER=azure\nAZURE_OPENAI_ENDPOINT=https://x\n"
        "AZURE_OPENAI_API_KEY=k\nAZURE_OPENAI_EMBED_DEPLOYMENT=d\nSERTOR_CORPUS=kaelen\n",
        encoding="utf-8",
    )
    other = tmp_path / "host-root"
    other.mkdir()
    monkeypatch.chdir(other)                          # different cwd, without .env
    monkeypatch.setattr(os, "environ", dict(os.environ))  # isolate load_dotenv writes
    monkeypatch.delenv("SERTOR_EMBED_PROVIDER", raising=False)
    monkeypatch.setattr("sertor_core.config.settings.sys.prefix", str(sertor_dir / ".venv"))

    s = Settings.load()                               # default ".env": auto-localizes to runtime
    assert s.embed_provider == "azure"
    assert s.corpus == "kaelen"
    assert s.index_dir == sertor_dir / ".index"       # anchored to .sertor/, not to cwd


def test_cwd_sertor_dotenv_resolved_when_venv_not_nested(monkeypatch, tmp_path):
    """cwd has `.sertor/.env` but the venv is NOT nested under it (the dogfood layout, FEAT-013).

    Resolution must find `./.sertor/.env` and anchor the index at `./.sertor/.index`, so the
    dogfood exercises the SAME `.sertor/` layout it ships to hosts even though its venv is
    `./.venv` (not nested under `.sertor/`).
    """
    sertor_dir = tmp_path / ".sertor"
    sertor_dir.mkdir()
    (sertor_dir / ".env").write_text(
        "SERTOR_EMBED_PROVIDER=hash\nSERTOR_CORPUS=dogfood\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)                            # cwd has .sertor/.env but no ./.env
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("SERTOR_EMBED_PROVIDER", raising=False)
    # venv NOT under .sertor/ → runtime branch misses it; the cwd `.sertor/.env` branch catches it.
    monkeypatch.setattr("sertor_core.config.settings.sys.prefix", str(tmp_path / ".venv"))

    s = Settings.load()
    assert s.embed_provider == "hash"
    assert s.corpus == "dogfood"
    assert s.index_dir == sertor_dir / ".index"           # anchored next to `.sertor/.env`


def test_cwd_dotenv_takes_precedence(monkeypatch, tmp_path):
    """If the cwd has a `.env`, it wins over the runtime one (explicit > runtime)."""
    (tmp_path / ".env").write_text("SERTOR_EMBED_PROVIDER=hash\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("SERTOR_EMBED_PROVIDER", raising=False)
    s = Settings.load()
    assert s.embed_provider == "hash"
    # cwd `.env` is relative → relative index `.index` (preserved behavior, = cwd/.index)
    assert s.index_dir == Path(".index")


def test_rag_backend_residual_warns(monkeypatch, tmp_path, caplog):
    """A residual `RAG_BACKEND` in `.env` is signalled, not honoured (068, REQ-007)."""
    import logging

    (tmp_path / ".env").write_text(
        "RAG_BACKEND=azure\nSERTOR_EMBED_PROVIDER=glove\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("RAG_BACKEND", raising=False)
    monkeypatch.delenv("SERTOR_EMBED_PROVIDER", raising=False)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        s = Settings.load()
    assert s.embed_provider == "glove"  # unchanged
    assert any("config_rag_backend_ignored" in r.getMessage() for r in caplog.records)


# --- E10-FEAT-038: project root anchored to `.sertor/`, CWD-independent ---------------------------


def test_project_root_anchored_from_any_cwd(monkeypatch, tmp_path):
    """`project_root` is the parent of `.sertor/`, resolved from the runtime — NOT the cwd.

    Same self-location as the index: run from a deep subfolder, the root is still the project root.
    """
    sertor_dir = tmp_path / ".sertor"
    (sertor_dir / ".venv").mkdir(parents=True)
    (sertor_dir / ".env").write_text("SERTOR_EMBED_PROVIDER=hash\n", encoding="utf-8")
    sub = tmp_path / "src" / "sertor_core"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)                                 # deep subfolder, NOT the project root
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("SERTOR_EMBED_PROVIDER", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setattr("sertor_core.config.settings.sys.prefix", str(sertor_dir / ".venv"))

    s = Settings.load()
    assert s.index_dir == sertor_dir / ".index"
    assert s.project_root == tmp_path.resolve()            # parent of `.sertor/`, cwd-independent


def test_project_root_claude_project_dir_wins(monkeypatch, tmp_path):
    """`CLAUDE_PROJECT_DIR` (parity with the hooks) overrides the `.sertor/` derivation."""
    sertor_dir = tmp_path / ".sertor"
    (sertor_dir / ".venv").mkdir(parents=True)
    (sertor_dir / ".env").write_text("SERTOR_EMBED_PROVIDER=hash\n", encoding="utf-8")
    explicit = tmp_path / "explicit-root"
    explicit.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("SERTOR_EMBED_PROVIDER", raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(explicit))
    monkeypatch.setattr("sertor_core.config.settings.sys.prefix", str(sertor_dir / ".venv"))

    s = Settings.load()
    assert s.project_root == explicit.resolve()            # env override beats the derivation


def test_project_root_none_without_sertor_layout(monkeypatch, tmp_path):
    """No `.sertor/` anchor and no `CLAUDE_PROJECT_DIR` → `None` (caller fails loud)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    s = Settings.load(env_file=None)                       # no .env → relative `.index`, no anchor
    assert s.index_dir == Path(".index")
    assert s.project_root is None
