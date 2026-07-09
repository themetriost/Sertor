"""Shared helpers for the portable Sertor hooks (A-09 / E2).

Portable across Windows/macOS/Linux, **stdlib only**. Each hook is invoked via
`uv run --no-project python <root>/.claude/hooks/<name>.py` and imports this module from its own
directory (all hooks are byte-copied side-by-side into `.claude/hooks/`):

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _hooklib

The helpers reproduce the invariants of the former PowerShell hooks: read the event JSON from stdin
without hanging (stdin-guard), resolve the project root from `CLAUDE_PROJECT_DIR`, write the
secret-free fail-loud breadcrumb, and wrap every hook in a fail-safe runner that **always exits 0**.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


def project_root() -> Path:
    """Host project root: `CLAUDE_PROJECT_DIR` if set, else the current directory."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".")


def sertor_dir() -> Path:
    """The `.sertor/` runtime directory under the project root."""
    return project_root() / ".sertor"


def read_event() -> dict:
    """Read the hook event JSON from stdin. Returns `{}` on absent/redirected/invalid input.

    Stdin-guard (FR-005): never block waiting for input — if stdin is a TTY (interactive, no piped
    event) return `{}` immediately instead of hanging.
    """
    stream = sys.stdin
    if stream is None:
        return {}
    try:
        if stream.isatty():
            return {}
    except Exception:
        pass
    try:
        raw = stream.read()
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def write_breadcrumb(hook: str, reason: str) -> None:
    """Write the fail-loud breadcrumb `.sertor/.last-hook-error` (schema `hook.error/1`).

    Secret-free by construction (E10-FEAT-019): `reason` MUST be a fixed hook-local string or an
    exception *type* name — never raw exception messages, tool input, or `.env` content. Best-effort
    (swallows its own errors); never raises.
    """
    try:
        target_dir = sertor_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "hook.error/1",
            "hook": hook,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reason": reason,
        }
        (target_dir / ".last-hook-error").write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
    except Exception:
        pass


def run(hook_name: str, main: Callable[[], None]) -> None:
    """Fail-safe runner: execute `main()`, always `exit 0`; on error write the breadcrumb.

    The breadcrumb `reason` is the exception *type* (secret-free). This is the single place that
    enforces «exit 0 always, never block the session» (FR-004) with a visible signal (FR-007, XII).
    """
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — fail-safe boundary by design
        write_breadcrumb(hook_name, f"unexpected: {type(exc).__name__}")
    sys.exit(0)
