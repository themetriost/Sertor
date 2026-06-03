"""Test US1 — ingestione repo-agnostica (REQ-001..005)."""
from __future__ import annotations

import logging

import pytest

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import DocType
from sertor_core.domain.errors import IngestionError
from sertor_core.services.ingestion import discover


def _by_id(docs):
    return {d.id: d for d in docs}


def test_discovers_code_and_markdown_with_stable_ids(sample_repo):
    docs = discover(sample_repo, Settings.load(env_file=None))
    by_id = _by_id(docs)

    # codice + markdown scoperti (REQ-001), id = path relativo POSIX (REQ-004)
    assert "app/calculator.py" in by_id
    assert "web/server.js" in by_id
    assert "svc/handler.go" in by_id
    assert "docs/guide.md" in by_id
    assert "legacy/deploy.ps1" in by_id

    # tipo e linguaggio rilevati (REQ-005)
    assert by_id["app/calculator.py"].doc_type is DocType.CODE
    assert by_id["app/calculator.py"].language == "python"
    assert by_id["docs/guide.md"].doc_type is DocType.DOC
    assert by_id["docs/guide.md"].language == "markdown"


def test_excludes_artifacts_and_secrets(sample_repo):
    docs = discover(sample_repo, Settings.load(env_file=None))
    ids = {d.id for d in docs}
    # .venv e *.key esclusi (REQ-002)
    assert not any(i.startswith(".venv") for i in ids)
    assert not any(i.endswith(".key") for i in ids)


def test_ids_are_stable_across_runs(sample_repo):
    a = {d.id for d in discover(sample_repo, Settings.load(env_file=None))}
    b = {d.id for d in discover(sample_repo, Settings.load(env_file=None))}
    assert a == b  # idempotenza degli id (REQ-004)


def test_skips_unreadable_file_with_warning(sample_repo, monkeypatch, caplog):
    # Forza un errore di lettura su un file specifico (REQ-003).
    import sertor_core.services.ingestion as ing

    real_read = ing._read_text

    def fake_read(path):
        if path.name == "calculator.py":
            raise PermissionError("permesso negato")
        return real_read(path)

    monkeypatch.setattr(ing, "_read_text", fake_read)
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        docs = discover(sample_repo, Settings.load(env_file=None))

    ids = {d.id for d in docs}
    assert "app/calculator.py" not in ids       # saltato, non incluso
    assert "web/server.js" in ids               # gli altri proseguono
    assert any("calculator.py" in r.message for r in caplog.records)


def test_empty_repo_returns_empty_without_error(tmp_path):
    (tmp_path / "empty").mkdir()
    docs = discover(tmp_path / "empty", Settings.load(env_file=None))
    assert docs == []


def test_missing_root_raises_ingestion_error(tmp_path):
    with pytest.raises(IngestionError):
        discover(tmp_path / "does-not-exist", Settings.load(env_file=None))
