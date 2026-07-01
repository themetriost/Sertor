"""Observability (Constitution X): log strutturati per stadio, **mai** segreti né contenuto del diff.

Si loggano solo metadati di esito (ref, conteggi, esiti) — utili per "ha funzionato?" senza esporre
codice sorgente, chiavi o testo delle query. Il report stesso resta l'osservabilità primaria.
"""

from __future__ import annotations

import logging

_LOGGER_NAME = "speclift"


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def configure(*, verbose: bool) -> None:
    """Configura il logging della CLI: INFO se verbose, altrimenti silenzioso (solo WARNING+)."""
    logger = get_logger()
    if logger.handlers:
        logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("speclift %(levelname)s [%(stage)s] %(message)s"))
    handler.addFilter(_DefaultStageFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO if verbose else logging.WARNING)


class _DefaultStageFilter(logging.Filter):
    """Garantisce che il campo `stage` sia sempre presente nel record (default '-')."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "stage"):
            record.stage = "-"
        return True


def stage_event(stage: str, message: str) -> None:
    get_logger().info(message, extra={"stage": stage})
