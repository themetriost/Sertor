"""Source-level no-dual-field guard for the wiki-pending-check hook (FEAT-011, US2 / SC-008).

The former pwsh-execution cases in this file (running the `.ps1` hooks via `pwsh` and checking the
per-assistant native output + exit 0) are now covered by `test_portable_hooks_parity.py`, which runs
the portable Python hooks per assistant and asserts the same contract offline:
  - `test_wiki_session_start_claude_directive` / `test_wiki_session_start_copilot_json`
    (claude plain directive vs copilot `additionalContext`);
  - `test_wiki_pending_check_noop_without_config` (exit 0, no output on the no-config path, for both
    the Stop/claude and SessionEnd/copilot invocations);
  - `test_usage_check_fail_open_on_empty_and_garbage` (rag-usage fail-open on malformed/empty stdin,
    exit 0, NO stdout payload).

What parity does NOT cover is the source-level dual-field invariant below (no single line emits both
a Claude field and a Copilot field), so it is PORTED here, retargeted to the portable `.py` hook.
This guard runs ALWAYS, offline, with no `pwsh` installed.
"""
from __future__ import annotations

from sertor_installer.resources import asset_path

_WIKI_SCRIPT = asset_path("claude/hooks/wiki-pending-check.py")


def test_no_dual_field_in_pending_check_source():
    """SC-008: the hook never emits both `systemMessage` and `decision`/`additionalContext` in one
    branch. The copilot Stop branch uses `decision`/`reason`; claude uses `systemMessage`.
    They are mutually exclusive branches — assert no single line carries both a Claude and a Copilot
    field."""
    src = _WIKI_SCRIPT.read_text(encoding="utf-8")
    for line in src.splitlines():
        has_claude = "systemMessage" in line
        has_copilot = "decision" in line or "additionalContext" in line
        assert not (has_claude and has_copilot), f"dual-field line: {line.strip()}"
