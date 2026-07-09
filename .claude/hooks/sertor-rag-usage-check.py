"""Sertor RAG usage check — non-blocking PreToolUse hook (Principle XI, host-facing). Portable (A-09).

Detects direct use of the `sertor_core` library outside the supported vehicles (CLI / MCP) and
outside tests, and emits a NON-BLOCKING warning (on **stderr**) reminding the agent to use the
`sertor-rag` CLI or the MCP tools instead.

Fail-open contract (FR-004): **exit 0 ALWAYS** and emit NO stdout payload the assistant could read as
a `deny` decision (on Copilot `preToolUse` is fail-closed) — the warning goes ONLY to stderr.
`--assistant` is accepted for wiring symmetry; the contract is identical for both.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402

_TEXT_FIELDS = ("command", "content", "new_string", "new_str")
_PATH_FIELDS = ("file_path", "path", "notebook_path")
_IMPORT = re.compile(r"(?:import\s+sertor_core|from\s+sertor_core)")
_TEST = re.compile(r"\btests?\b", re.IGNORECASE)

_WARNING = (
    "Sertor RAG: direct use of `sertor_core` detected outside the vehicles/tests. "
    "Use the `sertor-rag` CLI or the MCP tools instead of importing the library "
    "(see CLAUDE.md, SERTOR:RAG-USAGE)."
)


def main() -> None:
    argparse.ArgumentParser().parse_known_args()  # accept/ignore --assistant for wiring symmetry
    event = _hooklib.read_event()
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return  # unknown context → fail-open

    text = "\n".join(str(tool_input[f]) for f in _TEXT_FIELDS if tool_input.get(f))
    path = next((str(tool_input[f]) for f in _PATH_FIELDS if tool_input.get(f)), "")
    if not text and not path:
        return  # nothing to inspect → fail-open

    if not _IMPORT.search(text):
        return  # no direct import → fail-open
    if _TEST.search(path + "\n" + text):
        return  # test path/content is legitimate (Principle I/XI)

    print(_WARNING, file=sys.stderr)  # non-blocking: stderr only, exit 0


if __name__ == "__main__":
    _hooklib.run("sertor-rag-usage-check", main)
