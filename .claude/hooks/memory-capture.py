"""Automatic (non-blocking, non-fatal) end-of-session capture — thin wrapper around the CLI. Portable (A-09).

SessionEnd hook that adapts the host event to the host-agnostic command `sertor-rag memory archive`
(feature 035). Contains NO archiving logic — delegated to the core via the CLI vehicle (Principle XI).

Discipline: privacy gate (no-op unless `SERTOR_MEMORY` enabled); non-fatal (CLI outcome absorbed,
always exit 0); non-blocking (local, no network). A "ran but failed" archive, or a missing `uv`/CLI,
leaves an inspectable breadcrumb (E10-FEAT-019) — never fatal.
"""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402


def _archive(cmd: list[str], cwd) -> int:
    """Run an archive command, suppress its output, return its exit code (raises if the exe is absent)."""
    return subprocess.run(
        cmd, cwd=str(cwd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120
    ).returncode


def main() -> None:
    _hooklib.read_event()  # drain stdin (stdin-guard)
    if not _hooklib.memory_enabled():
        return  # memory off → silent no-op (privacy, FR-015)

    root = _hooklib.project_root().resolve()
    sertor_dir = root / ".sertor"
    reason: str | None = None
    try:
        if sertor_dir.is_dir():
            rc = _archive(["uv", "run", "--project", str(sertor_dir), "sertor-rag", "memory", "archive"], root)
        else:
            rc = _archive(["sertor-rag", "memory", "archive"], root)
        if rc != 0:
            reason = f"sertor-rag memory archive exited {rc}"
    except Exception:
        # `uv`/CLI missing: fall back to the venv executable (PATH-independent), Windows or POSIX.
        venv_cli = sertor_dir / ".venv" / "Scripts" / "sertor-rag.exe"
        if not venv_cli.exists():
            venv_cli = sertor_dir / ".venv" / "bin" / "sertor-rag"
        try:
            if venv_cli.exists():
                rc = _archive([str(venv_cli), "memory", "archive"], root)
                reason = f"venv sertor-rag exited {rc}" if rc != 0 else None
            else:
                reason = "uv and venv sertor-rag both unavailable"
        except Exception:
            reason = reason or "uv and venv sertor-rag both unavailable"

    if reason:
        _hooklib.write_breadcrumb("memory-capture", reason)


if __name__ == "__main__":
    _hooklib.run("memory-capture", main)
