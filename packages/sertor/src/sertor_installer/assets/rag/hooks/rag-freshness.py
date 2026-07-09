"""End-of-session RAG freshness — spawn a detached worker that re-indexes. Portable (A-09).

Two modes (SessionEnd, E10-FEAT-011):
  - FOREGROUND (default): resolve the project root, spawn THIS SAME SCRIPT **detached** in worker
    mode, return immediately (< 1-2s) so the session close is never blocked.
  - WORKER (`--worker`): health verdict via `sertor-rag doctor --json` → atomic write of
    `.sertor/.rag-health.json` → **unconditional** re-index via the vehicle. Breadcrumb on failure.

Cross-OS detach (FR-006): `subprocess.Popen` with `start_new_session` (POSIX) or
`DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` (Windows), stdio → DEVNULL. Always exit 0; consumes the
CLI vehicle only (Principle XI), never imports `sertor_core`.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _worker(root_str: str) -> None:
    """Detached worker body: doctor → verdict → atomic state write → unconditional re-index."""
    from pathlib import Path

    root = Path(root_str or ".")
    runtime = root / ".sertor"
    reason = ""
    try:
        # 1. health verdict via the vehicle (doctor --json)
        doctor_exit = 0
        doctor_out = ""
        try:
            proc = subprocess.run(
                ["uv", "run", "--project", str(runtime), "sertor-rag", "doctor", "--json"],
                cwd=str(root), capture_output=True, text=True, timeout=300,
            )
            doctor_out, doctor_exit = proc.stdout, proc.returncode
        except Exception:
            doctor_out, doctor_exit = "", 1

        # 2. derive verdict + reason + per-area map
        verdict, areas = "healthy", {}
        report = None
        if doctor_out and doctor_out.strip():
            try:
                report = json.loads(doctor_out)
            except Exception:
                report = None
        if isinstance(report, dict) and isinstance(report.get("areas"), list):
            for a in report["areas"]:
                name = a.get("name") or a.get("area")
                status = a.get("status")
                if name and status:
                    areas[str(name)] = str(status)
                    if status in ("fail", "warn"):
                        verdict = "degraded"
                        if not reason:
                            reason = f"{name} area: {status}"
        if doctor_exit != 0:
            verdict = "degraded"
            if not reason:
                reason = f"doctor reported failure (exit {doctor_exit})"

        # 3. persist the state under .sertor/ ATOMICALLY (temp + replace)
        runtime.mkdir(parents=True, exist_ok=True)
        state_path = runtime / ".rag-health.json"
        state = {
            "schema": "rag.health/1",
            "verdict": verdict,
            "timestamp": _now(),
            "reason": reason,
            "exit_code": doctor_exit,
        }
        if areas:
            state["areas"] = areas
        tmp = state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, state_path)

        if verdict == "degraded":
            print(f"[sertor-rag] RAG health DEGRADED: {reason}", file=sys.stderr)
            print("[sertor-rag] At next session start you will be prompted to run "
                  "'sertor-rag index .' and/or reconnect the MCP server.", file=sys.stderr)

        # 4. unconditional re-index via the vehicle (synchronous inside the worker)
        try:
            rc = subprocess.run(
                ["uv", "run", "--project", str(runtime), "sertor-rag", "index", "."],
                cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800,
            ).returncode
            if rc != 0:
                reason = "re-index failed after health write"
        except Exception:
            reason = "re-index failed after health write"

        if reason:
            _hooklib.write_breadcrumb("rag-freshness", reason)
    except Exception:
        _hooklib.write_breadcrumb("rag-freshness", "freshness worker crashed")


def _spawn_detached(argv: list[str], cwd: str) -> None:
    """Spawn `argv` fully detached from this process, cross-OS (POSIX/Windows)."""
    kwargs: dict = {
        "cwd": cwd,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(argv, **kwargs)  # noqa: S603 — fixed argv, no shell


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--root", default=None)
    parser.add_argument("--assistant", default="claude")
    args, _ = parser.parse_known_args()

    if args.worker:
        _worker(args.root or ".")
        return

    # FOREGROUND: resolve root, spawn the detached worker, return immediately.
    event = _hooklib.read_event()
    root = _hooklib.project_root()
    if not os.environ.get("CLAUDE_PROJECT_DIR") and isinstance(event.get("cwd"), str):
        from pathlib import Path

        root = Path(event["cwd"])
    try:
        _spawn_detached(
            [sys.executable, os.path.abspath(__file__), "--worker", "--root", str(root)], str(root)
        )
    except Exception:
        # No usable detached-process facility: skip the freshness work this time (never block/fatal).
        _hooklib.write_breadcrumb("rag-freshness", "failed to spawn freshness worker")


if __name__ == "__main__":
    _hooklib.run("rag-freshness", main)
