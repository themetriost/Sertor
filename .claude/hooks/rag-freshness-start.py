"""Start-of-session RAG freshness signal — re-reads the health state and INDUCES a fix. Portable (A-09).

SessionStart hook that reads `.sertor/.rag-health.json` (written by `rag-freshness` at the previous
SessionEnd) and, if the verdict is `degraded`, emits on **stdout** a directive the assistant receives
as session-start context (E10-FEAT-011, FR-012..015).

D<->N boundary (FR-014): it does NOT run the correction — it only INDUCES; the agent decides. No LLM.
Idempotent (NFR-6): absent state or `healthy`/unknown verdict → no-op (no output). Always exit 0.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402


def main() -> None:
    argparse.ArgumentParser().parse_known_args()  # accept/ignore --assistant (wiring symmetry)
    _hooklib.read_event()  # drain stdin (stdin-guard); this hook reads state from disk, not the event

    state_path = _hooklib.sertor_dir() / ".rag-health.json"
    if not state_path.is_file():
        return  # no state yet → no-op (FR-015)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return  # malformed → no-op (non-fatal, FR-017)
    if not isinstance(state, dict) or state.get("verdict") != "degraded":
        return  # healthy/unknown → no-op (INV-1, NFR-6)

    reason = str(state.get("reason") or "unknown cause")
    # Inducement directive: stdout = SessionStart context for the agent (FR-013, D<->N FR-014).
    print(
        f"RAG HEALTH DEGRADED ({reason}). Before starting work: run `sertor-rag index .` "
        "and/or reconnect the MCP server to restore retrieval freshness. Do not proceed on "
        "potentially stale context."
    )


if __name__ == "__main__":
    _hooklib.run("rag-freshness-start", main)
