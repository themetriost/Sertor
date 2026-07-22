"""SessionStart directive — loads the wiki context at the start of a session. Portable (A-09).

Host-agnostic (Principio X, E10-FEAT-029): every path is read from `wiki.config.toml` (`root`,
`index_file`, `log_dir` + the opt-in `[ritual].exec_page`), NEVER hardcoded — so a host with a
different `root`/layout gets the right paths. The directive **degrades**: it only orders the agent to
read files that actually exist (a fresh wiki has no roadmap yet → no failed read). The roadmap/EXEC
directive appears only when the host configures `[ritual].exec_page` (the dogfood does; a generic host
does not). Rendered NATIVELY per assistant: claude → the directive on stdout (SessionStart context);
copilot's SessionStart is a static prompt (see install_wiki.py), so this script targets Claude.
Exit 0 always; stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402


def _latest_log(root: Path, wroot: str, log_dir: str, log_file: str) -> str | None:
    """Repo-relative path of the newest log to read, or None if none exists (degradation)."""
    if not log_dir:  # single-file log
        return f"{wroot}/{log_file}" if (root / wroot / log_file).is_file() else None
    d = root / wroot / log_dir
    if not d.is_dir():
        return None
    parts = sorted(p.name for p in d.glob("*.md") if p.name != "index.md")
    return f"{wroot}/{log_dir}/{parts[-1]}" if parts else None


def _directive(root: Path, cfg: dict) -> str | None:
    """Build the SessionStart directive from CONFIG + only files that exist. None if nothing to read."""
    wroot = cfg["root"]
    reads: list[str] = []

    exec_page = cfg.get("exec_page")
    show_exec = bool(exec_page) and (root / wroot / exec_page).is_file()
    if show_exec:
        reads.append(f"{wroot}/{exec_page}")
    if (root / wroot / cfg["index_file"]).is_file():
        reads.append(f"{wroot}/{cfg['index_file']}")
    latest = _latest_log(root, wroot, cfg["log_dir"], cfg["log_file"])
    if latest:
        reads.append(latest)

    if not reads:
        return None  # nothing to load (empty/fresh wiki) → no directive, no failed read
    lines = [
        "SESSION START - load the project context BEFORE replying to the user.",
        "Do this NOW, on your own initiative:",
        f"1. Read (the outputs enter the context in full): {' ; '.join(reads)}.",
    ]
    if show_exec:
        lines.append(
            "2. Then show the user the executive summary of the roadmap: the block between the markers "
            f"<!-- EXEC:START --> and <!-- EXEC:END --> of {wroot}/{exec_page}."
        )
    lines.append(
        "Reminder: during project work delegate the wiki update to the wiki-curator agent (see the "
        "instructions, Wiki and documentation section)."
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assistant", default="claude")
    args, _ = parser.parse_known_args()
    _hooklib.read_event()  # drain stdin (stdin-guard)

    root = _hooklib.project_root()
    try:
        root = root.resolve()
    except Exception:
        pass
    cfg = _hooklib.wiki_config(root)
    if cfg is None:
        return  # no host wiki config → nothing to load (fail-safe)
    directive = _directive(root, cfg)
    if not directive:
        return  # empty/fresh wiki → no failed read

    if args.assistant == "copilot":
        print(json.dumps({"additionalContext": directive}))  # VS Code additionalContext
    else:
        print(directive)  # claude: stdout = SessionStart context


if __name__ == "__main__":
    _hooklib.run("wiki-session-start", main)
