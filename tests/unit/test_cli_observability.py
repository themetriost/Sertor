"""Test US4 — osservabilità configurabile (REQ-050..055)."""
from __future__ import annotations

import json
import logging

import pytest

from sertor_cli import observability
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import EmbeddingError
from sertor_core.observability.logging import log_event
from sertor_core.services.indexing import IndexingService
from tests.fixtures.mocks import FakeEmbedder, InMemoryStore

S = Settings.load(env_file=None)


def test_verbose_enables_info_handler():
    observability.configure(verbose=True)
    lg = logging.getLogger("sertor_core")
    assert lg.level == logging.INFO
    assert lg.handlers                                # almeno un handler (REQ-050)


def test_json_formatter_serializes_fields():
    observability.configure(log_json=True)
    fmt = logging.getLogger("sertor_core").handlers[0].formatter
    rec = logging.makeLogRecord(
        {"name": "sertor_core", "levelname": "INFO", "msg": "op=index", "operation": "index",
         "documents": 3}
    )
    data = json.loads(fmt.format(rec))                # REQ-051
    assert data["operation"] == "index" and data["documents"] == 3


def test_log_config_loads_external_handler(tmp_path):
    logf = tmp_path / "out.log"
    cfg = tmp_path / "log.yaml"
    cfg.write_text(
        "version: 1\n"
        "disable_existing_loggers: false\n"
        "handlers:\n"
        "  f:\n"
        "    class: logging.FileHandler\n"
        f"    filename: {json.dumps(str(logf))}\n"
        "loggers:\n"
        "  sertor_core:\n"
        "    level: INFO\n"
        "    handlers: [f]\n",
        encoding="utf-8",
    )
    observability.configure(log_config=str(cfg))      # REQ-052: appender esterno via dictConfig
    log_event(logging.INFO, "index", documents=1)
    for h in logging.getLogger("sertor_core").handlers:
        h.flush()
    assert "op=index" in logf.read_text(encoding="utf-8")


def test_boundary_error_emits_log_event(sample_repo):
    records: list[logging.LogRecord] = []

    class _Cap(logging.Handler):
        def emit(self, r):
            records.append(r)

    lg = logging.getLogger("sertor_core")
    lg.handlers = [_Cap()]
    lg.setLevel(logging.DEBUG)
    lg.propagate = False

    class _Boom(FakeEmbedder):
        def embed(self, texts):
            raise EmbeddingError("down", provider="fake", reason="net", retriable=True)

    svc = IndexingService(_Boom(dim=8), InMemoryStore(), "c", S)
    with pytest.raises(EmbeddingError):
        svc.index(sample_repo, rebuild=True)
    # REQ-053: il fallimento sul boundary è emesso come evento di log strutturato
    assert any(getattr(r, "operation", None) == "index" and r.levelno == logging.ERROR
               for r in records)


def test_logs_do_not_contain_secrets(capsys):
    records: list[logging.LogRecord] = []

    class _Cap(logging.Handler):
        def emit(self, r):
            records.append(r)

    lg = logging.getLogger("sertor_core")
    lg.handlers = [_Cap()]
    lg.setLevel(logging.INFO)
    log_event(logging.INFO, "index", api_key="s3cr3t")
    rec = records[-1]
    assert rec.api_key == "***"                        # REQ-055: nessun segreto nei log
