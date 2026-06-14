"""Test 020 US1/US2/US3 — event capture handler + composition wiring. Offline.

Exercises the real wiring (`enable_observability`): the handler captures the structured events that
`log_event` already emits, additively. Covers FR-002/004/005/007/008/009 and SC-003/004/006.
"""
from __future__ import annotations

import logging

import pytest

from sertor_core import composition
from sertor_core.config.settings import Settings
from sertor_core.observability.capture import EventPersistenceHandler
from sertor_core.observability.logging import get_logger, log_event


@pytest.fixture
def clean_logger():
    """Restore the `sertor_core` logger (handlers + level) so observability does not leak."""
    logger = get_logger()
    before_handlers = list(logger.handlers)
    before_level = logger.level
    yield logger
    for handler in list(logger.handlers):
        if handler not in before_handlers:
            logger.removeHandler(handler)
    logger.setLevel(before_level)


def _settings(tmp_path, *, on: bool) -> Settings:
    return Settings(index_dir=tmp_path, observability_enabled=on)


def test_capture_end_to_end(tmp_path, clean_logger):
    # SC-001: an emitted event is captured with its operation, fields and a timestamp.
    settings = _settings(tmp_path, on=True)
    assert composition.enable_observability(settings) is True
    log_event(logging.INFO, "index", documents=3, chunks=12)
    events = composition.build_observability_store(settings).query_events("index", None, None)
    assert len(events) == 1
    assert events[0].fields == {"documents": 3, "chunks": 12}
    assert events[0].ts > 0


def test_ignores_unstructured_logs(tmp_path, clean_logger):
    # Only structured events (with `operation`) are persisted; plain logs are ignored.
    settings = _settings(tmp_path, on=True)
    composition.enable_observability(settings)
    clean_logger.warning("plain message")
    assert composition.build_observability_store(settings).query_events(None, None, None) == []


def test_secrets_redacted_in_store(tmp_path, clean_logger):
    # FR-008/009 + SC-006: fields are already redacted upstream → no secret reaches the store.
    settings = _settings(tmp_path, on=True)
    composition.enable_observability(settings)
    log_event(logging.INFO, "x", api_key="s3cr3t", n=1)
    event = composition.build_observability_store(settings).query_events("x", None, None)[0]
    assert event.fields["api_key"] == "***"
    assert event.fields["n"] == 1
    assert "s3cr3t" not in str(event.fields)


def test_default_off_no_handler_no_store(tmp_path, clean_logger):
    # FR-004 / SC-003: disabled (default) → no handler attached, no store file created.
    settings = _settings(tmp_path, on=False)
    assert composition.enable_observability(settings) is False
    log_event(logging.WARNING, "index", documents=3)
    assert not (tmp_path / "observability.sqlite").exists()
    assert not any(isinstance(h, EventPersistenceHandler) for h in clean_logger.handlers)


def test_enable_is_idempotent(tmp_path, clean_logger):
    settings = _settings(tmp_path, on=True)
    composition.enable_observability(settings)
    composition.enable_observability(settings)
    attached = [h for h in clean_logger.handlers if isinstance(h, EventPersistenceHandler)]
    assert len(attached) == 1


def test_resilient_to_corrupt_store(tmp_path, clean_logger, caplog):
    # FR-007 / SC-004: a corrupt store during emit → the operation completes, only a warning.
    (tmp_path / "observability.sqlite").write_bytes(b"not a database")
    settings = _settings(tmp_path, on=True)
    composition.enable_observability(settings)
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        log_event(logging.INFO, "index", documents=3)  # must not raise
    assert any(
        getattr(r, "operation", None) == "observability_store_unavailable" for r in caplog.records
    )
