"""Wiki freshness guard — BLOCK stopping until the session's work is recorded + judged (E10-FEAT-040).

The step ritual (record + distill + semantic lint) is judgment and was silently skippable — the
non-blocking Stop nudge (`wiki-pending-check`) got ignored. This hook is the Stop-time sibling of the
merge-time `distill-floor` (FEAT-039): at the end of a turn, if the session did indexed work that is
NOT yet recorded in the wiki, it **blocks** the stop and tells the agent to close the ritual first.

Detection is REUSED, not reinvented: `sertor-wiki-tools scan` (contract `wiki.scan/1`) already computes
`pending` (modified `src`/`specs`/`requirements`/`.claude` files newer than the last log entry). The hook
never records or judges (D↔N, Principio XI) — it only DEMANDS it, with a SPECIFIC reason so the agent
resolves in one turn (there is no documented consecutive-block cap; specificity is the real defense).

Native per assistant, SAME shape: `{"decision": "block", "reason": ...}` — Claude (top-level Stop
decision) and Copilot (`agentStop`) both force another turn. Read-only / question sessions (`pending` 0)
close normally. Anti-loop via `stop_hook_active`. FAILS OPEN (no config / scan unavailable → never trap
the turn). Exit 0 always; stdlib only; breadcrumb on scan error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402


def _scan(root: Path, config: str) -> dict | None:
    """Run `sertor-wiki-tools scan --json`; return the parsed last line (or `None`).

    Prefers the `.sertor/` runtime CLI (host layout) and falls back to a bare `sertor-wiki-tools`.
    Raises if the CLI is absent/fails — the caller treats that as fail-open (never trap the turn).
    """
    sertor_dir = root / ".sertor"
    if sertor_dir.is_dir():
        cmd = ["uv", "run", "--project", str(sertor_dir), "sertor-wiki-tools",
               "scan", "--config", config, "--root", str(root), "--json"]
    else:
        cmd = ["sertor-wiki-tools", "scan", "--config", config, "--root", str(root), "--json"]
    out = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=60).stdout
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except Exception:
        return None


def _reason(pending: int, message: str) -> str:
    """The block reason: specific enough to resolve the ritual in ONE turn (record + distill + lint)."""
    lead = message.strip() or (
        f"{pending} modified file(s) from this session are not yet recorded in the wiki."
    )
    return (
        f"BLOCKED: the wiki was not updated for this session's work. {lead} Before stopping, CLOSE the "
        "step ritual for what changed: (a) RECORD it in the wiki — create/update the impacted pages "
        "with backlinks, refresh the index, and append a dated log entry (delegatable to the "
        "wiki-curator agent); (b) DISTILL any durable entity into its own concepts/tech page, or log a "
        "reasoned 'no' that NAMES the candidates considered; (c) run the SEMANTIC LINT — verify the wiki "
        "matches the code/spec/requirements you changed and fix every claim the repo now contradicts. "
        "These are main-flow judgment (D↔N): do them, then stop again."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="Stop", choices=["Stop"])
    parser.add_argument("--assistant", default="claude")
    parser.parse_known_args()
    event = _hooklib.read_event()

    # anti-loop: if already inside a Stop hook cycle, let it finish (never trap the turn).
    if event.get("stop_hook_active"):
        return

    root = _hooklib.project_root()
    if not os.environ.get("CLAUDE_PROJECT_DIR") and isinstance(event.get("cwd"), str):
        root = Path(event["cwd"])
    try:
        root = root.resolve()
    except Exception:
        pass

    config = root / "wiki" / "wiki.config.toml"
    if not config.is_file():
        legacy = root / "wiki.config.toml"
        if not legacy.is_file():
            return  # no host wiki config → nothing to enforce (fail open)
        config = legacy

    try:
        scan = _scan(root, str(config))
    except Exception:
        _hooklib.write_breadcrumb("wiki-guard", "sertor-wiki-tools scan unavailable or failed")
        return  # fail open

    if not scan or scan.get("schema") != "wiki.scan/1" or int(scan.get("pending", 0)) <= 0:
        return  # nothing pending (read-only / question session) → do not block

    reason = _reason(int(scan["pending"]), str(scan.get("message", "")))
    # Same shape on both assistants: Claude top-level Stop decision + Copilot agentStop both continue.
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    _hooklib.run("wiki-guard", main)
