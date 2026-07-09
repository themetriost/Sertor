"""SessionStart directive — loads the wiki/roadmap context at the start of a session. Portable (A-09).

Single source (FEAT-011): computes the latest log partition and emits the "load roadmap/index/log +
show the EXEC summary" directive. Rendered NATIVELY per assistant: claude → the directive on stdout
(harness uses it as SessionStart context); copilot → `{"additionalContext": <directive>}` JSON.
Exit 0 always; stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402


def _latest_log(root) -> str:
    log_dir = root / "wiki" / "log"
    if not log_dir.is_dir():
        return "log.md"
    partitions = sorted(
        p.name for p in log_dir.glob("*.md") if p.name != "index.md"
    )
    return partitions[-1] if partitions else "log.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assistant", default="claude")
    args, _ = parser.parse_known_args()
    _hooklib.read_event()  # drain stdin (stdin-guard)

    root = _hooklib.project_root()
    log = _latest_log(root)
    directive = "\n".join([
        "SESSION START - load the project context BEFORE replying to the user.",
        "Do this NOW, on your own initiative:",
        f"1. Read (the outputs enter the context in full): wiki/syntheses/roadmap.md ; wiki/log/{log} "
        "(the tail of the journal). Read wiki/index.md (the wiki catalog) ON DEMAND, only when you "
        "need to navigate the wiki.",
        "2. Then show the user the executive summary of the roadmap: the block between the markers "
        "<!-- EXEC:START --> and <!-- EXEC:END --> of wiki/syntheses/roadmap.md.",
        "Reminder: during project work delegate the wiki update to the wiki-curator agent (see the "
        "instructions, Wiki and documentation section).",
    ])

    if args.assistant == "copilot":
        print(json.dumps({"additionalContext": directive}))  # VS Code additionalContext
    else:
        print(directive)  # claude: stdout = SessionStart context


if __name__ == "__main__":
    _hooklib.run("wiki-session-start", main)
