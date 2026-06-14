"""Structured logging for the core (Principio IX, REQ-031).

Uses the stdlib `logging` (no framework imposed on the caller): every runtime operation emits
a record with structured fields (operation, provider/backend, counts, embedding dimension,
timings, errors). Secrets are **redacted** before emission (REQ-032).
"""
from __future__ import annotations

import logging
import re
from typing import Any

_LOGGER_NAME = "sertor_core"

# Keys whose values must never appear in logs (REQ-032). Matched as WHOLE WORDS, not bare
# substrings: an auth `token` is a secret, but a usage metric `tokens` (cost signal, REQ-H5) is
# not — and `monkey` must not match `key`. `key` covers `api_key`; `apikey` covers the joined form.
_SECRET_HINTS = ("key", "apikey", "token", "secret", "password", "authorization")
_WORD = re.compile(r"[a-z0-9]+")


def get_logger() -> logging.Logger:
    """Core logger. The caller is free to configure handlers/levels."""
    return logging.getLogger(_LOGGER_NAME)


def _is_secret(field_name: str) -> bool:
    # Split snake_case and camelCase into words, then match whole hints (see _SECRET_HINTS note).
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", field_name).lower()
    return bool(set(_WORD.findall(spaced)) & set(_SECRET_HINTS))


def redact(fields: dict[str, Any]) -> dict[str, Any]:
    """Replace values of keys that look like secrets with a placeholder."""
    return {k: ("***" if _is_secret(k) and v not in (None, "") else v) for k, v in fields.items()}


def log_event(level: int, operation: str, **fields: Any) -> None:
    """Emit a structured record for `operation` with the given `fields` (secrets redacted).

    Example: `log_event(logging.INFO, "index", backend="local", documents=12, chunks=240)`.
    """
    safe = redact(fields)
    rendered = " ".join(f"{k}={v}" for k, v in safe.items())
    get_logger().log(level, "op=%s %s", operation, rendered, extra={"operation": operation, **safe})
