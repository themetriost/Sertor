"""Test US3 — CLI runtime observability (FR-017..022, SC-006, LSC-7).

Verifies the `-v`/`--log-json`/`--log-config` levers, structured events at core boundaries, and
secret redaction. No network (NFR-02).
"""
from __future__ import annotations

import json
import logging
from argparse import Namespace

import pytest

from sertor_core.adapters.embeddings.ollama import OllamaEmbedder
from sertor_core.cli.logging_setup import JsonLogFormatter, setup_logging
from sertor_core.domain.errors import ConfigError, EmbeddingError
from sertor_core.observability.logging import log_event


@pytest.fixture(autouse=True)
def _clean_logger():
    """Restore the sertor_core logger between tests (handlers would otherwise accumulate)."""
    logger = logging.getLogger("sertor_core")
    before = list(logger.handlers)
    level = logger.level
    yield
    logger.handlers[:] = before
    logger.setLevel(level)


def _args(**kw):
    base = {"verbose": False, "log_json": False, "log_config": None}
    base.update(kw)
    return Namespace(**base)


# --------------------------------------------------------------------- -v (FR-017)
def test_verbose_sets_info_level_with_handler():
    setup_logging(_args(verbose=True))
    logger = logging.getLogger("sertor_core")
    assert logger.level == logging.INFO
    assert logger.handlers


def test_default_is_warning_no_handler_added():
    logger = logging.getLogger("sertor_core")
    n_before = len(logger.handlers)
    setup_logging(_args())
    assert logger.level == logging.WARNING
    assert len(logger.handlers) == n_before


# --------------------------------------------------------------------- --log-json (FR-018)
def test_log_json_emits_valid_json_with_operation(capsys):
    setup_logging(_args(log_json=True))
    log_event(logging.INFO, "index", collection="c", documents=3)
    err = capsys.readouterr().err.strip().splitlines()
    assert err
    rec = json.loads(err[-1])
    assert rec["operation"] == "index"
    assert rec["collection"] == "c"


def test_json_formatter_serializes_extra_fields():
    rec = logging.makeLogRecord({"msg": "x", "operation": "retrieve", "k": 5, "results": 2})
    out = json.loads(JsonLogFormatter().format(rec))
    assert out["operation"] == "retrieve"
    assert out["k"] == 5 and out["results"] == 2


# --------------------------------------------------------------------- --log-config (FR-019)
def test_log_config_json_loaded(tmp_path):
    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"null": {"class": "logging.NullHandler"}},
        "loggers": {"sertor_core": {"handlers": ["null"], "level": "INFO"}},
    }
    f = tmp_path / "log.json"
    f.write_text(json.dumps(cfg), encoding="utf-8")
    setup_logging(_args(log_config=str(f)))
    assert logging.getLogger("sertor_core").level == logging.INFO


def test_log_config_missing_file_raises_config_error(tmp_path):
    with pytest.raises(ConfigError) as exc:
        setup_logging(_args(log_config=str(tmp_path / "non-esiste.json")))
    assert "not found" in str(exc.value)


def test_log_config_invalid_json_raises_config_error(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        setup_logging(_args(log_config=str(f)))


def test_log_config_yaml_without_pyyaml_degrades(tmp_path, monkeypatch):
    f = tmp_path / "cfg.yaml"
    f.write_text("version: 1\n", encoding="utf-8")
    # simulate absence of pyyaml
    import builtins

    real_import = builtins.__import__

    def _no_yaml(name, *a, **k):
        if name == "yaml":
            raise ImportError("no yaml")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _no_yaml)
    with pytest.raises(ConfigError) as exc:
        setup_logging(_args(log_config=str(f)))
    assert "pyyaml" in str(exc.value)


# --------------------------------------------------------------------- no secrets (FR-022)
def test_no_secrets_in_log_records(capsys):
    setup_logging(_args(log_json=True))
    log_event(logging.INFO, "index", provider="azure", api_key="super-secret", token="tok")
    rec = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert rec["api_key"] == "***"
    assert rec["token"] == "***"
    assert rec["provider"] == "azure"


# --------------------------------------------------------------------- boundary event (FR-020)
def test_embeddings_error_event_at_boundary(caplog):
    import httpx

    class _Client:
        def post(self, *a, **k):
            raise httpx.ConnectError("down")

    emb = OllamaEmbedder("http://x", "m", client=_Client())
    with caplog.at_level(logging.ERROR, logger="sertor_core"):
        with pytest.raises(EmbeddingError):
            emb.embed(["q"])
    events = [r for r in caplog.records if getattr(r, "operation", None) == "embeddings_error"]
    assert events
    assert getattr(events[0], "provider", "") == "ollama:m"
