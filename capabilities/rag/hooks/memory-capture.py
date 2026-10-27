"""Sertor RAG — conversation memory capture at session end (Kaelen package).

Runs with the capability's own interpreter (`runtime = true`) and calls the host-agnostic CLI
vehicle `sertor-rag memory archive` — never the library. The command itself does nothing unless
`SERTOR_MEMORY=true` in `.sertor/.env`, so this hook needs no configuration of its own.

Non-blocking by contract: a session end must never fail because of memory. Any failure is reported
on stderr (visible in the assistant's hook log) and the hook still exits 0.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    for name in ("CLAUDE_PROJECT_DIR", "COPILOT_PROJECT_DIR"):
        value = os.environ.get(name)
        if value and Path(value).is_dir():
            return Path(value)
    return Path.cwd()


def main() -> int:
    try:
        sys.stdin.read()  # drain the event payload: the assistant waits for it to be consumed
    except (OSError, ValueError):
        pass
    try:
        rc = subprocess.run(
            [sys.executable, "-m", "sertor_core.cli", "memory", "archive"],
            cwd=str(_project_root()), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=120, text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[sertor-rag] memory capture did not run: {exc}", file=sys.stderr)
        return 0
    if rc.returncode != 0:
        print(f"[sertor-rag] memory capture exited {rc.returncode}: {rc.stderr.strip()[-300:]}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
