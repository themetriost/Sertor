"""Structured logging for the install kit (Principio IX), stdlib-only.

Minimal `log_event` on the stdlib `logging` (no framework imposed on the caller, no dependency on
`sertor-core`): every install operation can emit a record with structured fields (operation,
outcomes, counts). Secrets are **redacted** before emission: the installer never writes secret
values anyway (templates leave them empty), but the redaction is a defence-in-depth net mirroring
the core's policy.
"""
from __future__ import annotations

import logging
import re
from typing import Any

_LOGGER_NAME = "sertor_install_kit"

# Keys whose values must never appear in logs. Matched as WHOLE WORDS (not bare substrings): an
# auth `token` is a secret, a usage metric `tokens` is not, and `monkey` must not match `key`.
_SECRET_HINTS = ("key", "apikey", "token", "secret", "password", "authorization")
_WORD = re.compile(r"[a-z0-9]+")


def get_logger() -> logging.Logger:
    """Kit logger. The caller is free to configure handlers/levels."""
    return logging.getLogger(_LOGGER_NAME)


def _is_secret(field_name: str) -> bool:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", field_name).lower()
    return bool(set(_WORD.findall(spaced)) & set(_SECRET_HINTS))


def redact(fields: dict[str, Any]) -> dict[str, Any]:
    """Replace values of keys that look like secrets with a placeholder."""
    return {k: ("***" if _is_secret(k) and v not in (None, "") else v) for k, v in fields.items()}


def log_event(level: int, operation: str, **fields: Any) -> None:
    """Emit a structured record for `operation` with the given `fields` (secrets redacted).

    Example: `log_event(logging.INFO, "install", capability="governance", created=12)`.
    """
    safe = redact(fields)
    rendered = " ".join(f"{k}={v}" for k, v in safe.items())
    get_logger().log(level, "op=%s %s", operation, rendered, extra={"operation": operation, **safe})
