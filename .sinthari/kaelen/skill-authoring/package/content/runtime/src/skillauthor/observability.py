"""Observability (Constitution X): log strutturati e leveled per comando; mai segreti.

L'esito di ogni comando (`--json`) resta la fonte primaria di osservabilità.
"""

from __future__ import annotations

import logging

_LOGGER_NAME = "skillauthor"


def get_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s skillauthor.%(command)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
    return logger


def log_command(command: str, message: str, level: int = logging.INFO) -> None:
    get_logger().log(level, message, extra={"command": command})
