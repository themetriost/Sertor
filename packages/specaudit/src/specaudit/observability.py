"""Observability (Constitution X): log strutturati e leveled per stadio; mai segreti.

Minimale e senza dipendenze: un logger nominato per SpecAudit; il report resta la fonte primaria
di osservabilità (verdetti + gap dichiarati ispezionabili senza side effect).
"""

from __future__ import annotations

import logging

_LOGGER_NAME = "specaudit"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s specaudit.%(stage)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
    return logger


def log_stage(stage: str, message: str, level: int = logging.INFO) -> None:
    """Emette un log associato a uno stadio della pipeline."""

    get_logger().log(level, message, extra={"stage": stage})
