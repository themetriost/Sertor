"""Test US6 — observability: structured logs and secret redaction (REQ-031/032, SC-007)."""
from __future__ import annotations

import logging

from sertor_core.observability.logging import log_event, redact


def test_redact_masks_secret_fields():
    out = redact({"provider": "azure", "api_key": "abc", "authorization": "Bearer x", "k": 5})
    assert out["provider"] == "azure"
    assert out["k"] == 5
    assert out["api_key"] == "***"          # secret masked (REQ-032)
    assert out["authorization"] == "***"


def test_redact_keeps_empty_secret_as_is():
    out = redact({"api_key": ""})
    assert out["api_key"] == ""             # empty not masked (no secret to hide)


def test_log_event_emits_structured_fields(caplog):
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        log_event(logging.INFO, "index", backend="local", documents=3, chunks=12, api_key="s3cr3t")
    rec = caplog.records[-1]
    assert rec.operation == "index"
    assert rec.documents == 3
    assert rec.backend == "local"
    assert rec.api_key == "***"   # no secrets in logs (REQ-032)
    assert "s3cr3t" not in rec.getMessage()
