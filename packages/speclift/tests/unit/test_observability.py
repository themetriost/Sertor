"""Test observability: log per stadio, livello controllato da verbose, niente contenuto/segreti."""

from __future__ import annotations

import logging

from speclift.observability import configure, get_logger, stage_event


def test_verbose_emits_info(caplog):
    configure(verbose=True)
    with caplog.at_level(logging.INFO, logger="speclift"):
        stage_event("ingest", "ref=HEAD kind=commit")
    assert any("ref=HEAD" in r.message for r in caplog.records)
    assert any(getattr(r, "stage", None) == "ingest" for r in caplog.records)


def test_non_verbose_suppresses_info(caplog):
    configure(verbose=False)
    with caplog.at_level(logging.INFO, logger="speclift"):
        stage_event("ingest", "ref=HEAD")
    # Sotto verbose il logger è a WARNING: gli INFO non passano.
    assert get_logger().level == logging.WARNING
