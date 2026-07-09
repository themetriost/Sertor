"""Automatic (non-blocking) trigger for wiki maintenance — thin wrapper around the CLI. Portable (A-09).

Delegates to the deterministic core: `sertor-wiki-tools scan --config <root>/wiki/wiki.config.toml
--root <root> --json` and maps the `wiki.scan/1` contract (`pending`, `message`) to the hook format.
Output rendered NATIVELY per assistant/mode (FEAT-011):
  - claude → `{"systemMessage": msg}` (both Stop and SessionEnd);
  - copilot + Stop (agentStop) → `{"decision": "allow", "reason": msg}` (non-blocking);
  - copilot + SessionEnd → message on stderr.
No pending / CLI unavailable → no output, exit 0 (breadcrumb on CLI error).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402


def _scan(root, config: str) -> dict | None:
    """Run `sertor-wiki-tools scan --json`; return the parsed last line or raise if the CLI is absent."""
    sertor_dir = root / ".sertor"
    if sertor_dir.is_dir():
        cmd = ["uv", "run", "--project", str(sertor_dir), "sertor-wiki-tools",
               "scan", "--config", config, "--root", str(root), "--json"]
    else:
        cmd = ["sertor-wiki-tools", "scan", "--config", config, "--root", str(root), "--json"]
    out = subprocess.run(
        cmd, cwd=str(root), capture_output=True, text=True, timeout=60
    ).stdout
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="Stop", choices=["Stop", "SessionEnd"])
    parser.add_argument("--assistant", default="claude")
    args, _ = parser.parse_known_args()
    event = _hooklib.read_event()

    # anti-loop: if Claude is already in a Stop hook cycle, let it finish.
    if args.mode == "Stop" and event.get("stop_hook_active"):
        return

    root = _hooklib.project_root()
    if not os.environ.get("CLAUDE_PROJECT_DIR") and isinstance(event.get("cwd"), str):
        from pathlib import Path

        root = Path(event["cwd"])
    try:
        root = root.resolve()
    except Exception:
        pass

    config = root / "wiki" / "wiki.config.toml"
    if not config.is_file():
        legacy = root / "wiki.config.toml"
        if not legacy.is_file():
            return  # no host config → nothing to do
        config = legacy

    try:
        scan = _scan(root, str(config))
    except Exception:
        _hooklib.write_breadcrumb("wiki-pending-check", "sertor-wiki-tools scan unavailable or failed")
        return

    if not scan or scan.get("schema") != "wiki.scan/1" or int(scan.get("pending", 0)) <= 0:
        return

    pending = int(scan["pending"])
    if args.mode == "Stop":
        msg = (f"{scan.get('message', '')} Per the golden rule: consider delegating to the "
               "wiki-curator agent (record operation) or triggering a wiki consolidation.")
    else:
        msg = (f"Wiki: {pending} modified files are not yet recorded. At the next session, delegate "
               "to the wiki-curator agent (record) or trigger a wiki consolidation.")

    if args.assistant == "copilot":
        if args.mode == "Stop":
            print(json.dumps({"decision": "allow", "reason": msg}))  # non-blocking agentStop
        else:
            print(msg, file=sys.stderr)  # sessionEnd: stderr
        return

    print(json.dumps({"systemMessage": msg}))  # claude: top-level systemMessage


if __name__ == "__main__":
    _hooklib.run("wiki-pending-check", main)
