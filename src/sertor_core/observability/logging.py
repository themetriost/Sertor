"""Logging strutturato del nucleo (Principio IX, REQ-031).

Usa la `logging` della stdlib (nessun framework imposto al chiamante): ogni operazione a runtime
emette un record con campi strutturati (operazione, provider/backend, conteggi, dimensione
embedding, tempi, errori). I segreti vengono **redatti** prima dell'emissione (REQ-032).
"""
from __future__ import annotations

import logging
from typing import Any

_LOGGER_NAME = "sertor_core"

# Chiavi i cui valori non devono mai comparire nei log (REQ-032).
_SECRET_HINTS = ("key", "api_key", "apikey", "token", "secret", "password", "authorization")


def get_logger() -> logging.Logger:
    """Logger del nucleo. Il chiamante è libero di configurare handler/livelli."""
    return logging.getLogger(_LOGGER_NAME)


def _is_secret(field_name: str) -> bool:
    low = field_name.lower()
    return any(hint in low for hint in _SECRET_HINTS)


def redact(fields: dict[str, Any]) -> dict[str, Any]:
    """Sostituisce i valori delle chiavi che sembrano segreti con un placeholder."""
    return {k: ("***" if _is_secret(k) and v not in (None, "") else v) for k, v in fields.items()}


def log_event(level: int, operation: str, **fields: Any) -> None:
    """Emette un record strutturato per `operation` con i `fields` (segreti redatti).

    Esempio: `log_event(logging.INFO, "index", backend="local", documents=12, chunks=240)`.
    """
    safe = redact(fields)
    rendered = " ".join(f"{k}={v}" for k, v in safe.items())
    get_logger().log(level, "op=%s %s", operation, rendered, extra={"operation": operation, **safe})


def log_error(operation: str, exc: BaseException, **fields: Any) -> None:
    """Emette un evento di log strutturato per un fallimento su un boundary, prima del raise.

    Completa l'osservabilità (Principio IX): l'errore è sia un'eccezione esplicita (Principio IV)
    sia un evento di log diagnosticabile. I segreti restano redatti (via `log_event`).
    """
    log_event(logging.ERROR, operation, error=type(exc).__name__, reason=str(exc), **fields)
