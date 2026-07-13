"""Start-of-session version-update signal — reads the state and warns if behind. Portable (A-09).

SessionStart hook that reads `.sertor/.version-check.json` (written by `version-check` at the previous
SessionEnd) and, if the verdict is `behind`, emits on **stdout** an update notice the assistant
receives as session-start context (E2-FEAT-013, FR-003).

D<->N boundary: it does NOT apply any update (the user decides). ZERO network (the GET happened at
SessionEnd). Idempotent: absent state or verdict != `behind` → no-op. Always exit 0.
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
    _hooklib.read_event()  # drain stdin (stdin-guard)

    state_path = _hooklib.sertor_dir() / ".version-check.json"
    if not state_path.is_file():
        return  # no state yet → no-op (INV-1)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return  # malformed → no-op (non-fatal)
    if not isinstance(state, dict):
        return

    verdict = state.get("verdict")

    if verdict == "behind":
        installed = str(state.get("installed") or "unknown")
        latest = str(state.get("latest") or "unknown")
        dim_text = ""
        dimensions = state.get("dimensions")
        if isinstance(dimensions, dict) and dimensions:
            behind = ", ".join(f"{name} {value}" for name, value in dimensions.items())
            dim_text = f" Installed dimensions: {behind}."
        # Update notice (stdout = SessionStart context). Only WARNS; the user decides (FR-005/CS-4).
        print(
            f"SERTOR UPDATE AVAILABLE: installed {installed}, latest {latest}.{dim_text} "
            "To update, run `sertor upgrade` (or `uvx --refresh sertor` if installed via uvx). "
            "This is only a notice — no update is applied automatically."
        )
        return

    # E2-FEAT-017: honest ONE-TIME cue when the check could not verify (verdict `unknown`: the
    # /VERSION GET failed — offline, or the source repository is private). Without this the updater
    # is silently inert (SessionStart only spoke on `behind`) and the user never learns it cannot
    # verify. No nag: emit ONCE, then persist `unknown_notified` so it does not repeat while unknown.
    if verdict == "unknown" and not state.get("unknown_notified"):
        print(
            "SERTOR UPDATE CHECK UNAVAILABLE: could not verify whether a newer Sertor is available "
            "(the version endpoint was unreachable — offline, or the source repository is private). "
            "Sertor works normally; this notice appears once. To check manually, compare your "
            "installed version with the project's /VERSION, or run `uvx --refresh` on your install."
        )
        try:  # mark notified so it does not repeat every session (best-effort, non-fatal)
            state["unknown_notified"] = True
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception:
            pass
        return

    # up-to-date / ahead / unknown-already-notified / absent → no-op (INV-1)


if __name__ == "__main__":
    _hooklib.run("version-check-start", main)
