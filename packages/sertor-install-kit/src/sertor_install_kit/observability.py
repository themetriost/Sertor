"""Structured logging for the install kit (Principio IX), stdlib-only.

Minimal `log_event` on the stdlib `logging` (no framework imposed on the caller, no dependency on
`sertor-core`): every install operation can emit a record with structured fields (operation,
outcomes, counts). Secrets are **redacted** before emission: the installer never writes secret
values anyway (templates leave them empty), but the redaction is a defence-in-depth net mirroring
the core's policy.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

_LOGGER_NAME = "sertor_install_kit"

# E2-FEAT-018: the inspectable install log lives beside the runtime, one JSON line per artifact.
INSTALL_LOG_NAME = ".install-log.jsonl"
INSTALL_EVENT_SCHEMA = "install.event/1"

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


def log_install_event(
    runtime_dir: Path,
    *,
    op: str,
    capability: str,
    target: str,
    outcome: str,
    reason: str | None = None,
    cmd: str | None = None,
    rev: str | None = None,
    dry_run: bool = False,
) -> None:
    """Append one `install.event/1` JSONL line to `<runtime_dir>/.install-log.jsonl` (E2-FEAT-018).

    The inspectable TRUTH of what the installer did, per artifact/step: the operation (`op`), the
    capability, the `target` artifact, the command run (if any), the outcome with its reason, and
    the resolved revision. Fields pass through `redact` (secret key-names → `***`; installer
    commands/specs carry no secret values). Best-effort and NON-fatal: a write failure is logged and
    swallowed — it MUST NOT abort the install (REQ-007). `dry_run` writes nothing (REQ-005).
    """
    if dry_run:
        return
    event = redact({
        "schema": INSTALL_EVENT_SCHEMA, "op": op, "capability": capability, "target": target,
        "outcome": outcome, "reason": reason, "cmd": cmd, "rev": rev,
    })
    event = {k: v for k, v in event.items() if v is not None}  # drop absent fields for compactness
    # The log lives IN the runtime dir — we never CREATE it just to log (that would leave `.sertor/`
    # behind on an early fail-fast before the runtime exists — "no partial state"). If the dir is
    # absent (nothing installed yet), the append below raises FileNotFoundError → swallowed below.
    try:
        with (runtime_dir / INSTALL_LOG_NAME).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as exc:  # fail-safe (REQ-007): the log is not worth aborting the install for
        get_logger().warning("install-log write failed: %s", exc)
