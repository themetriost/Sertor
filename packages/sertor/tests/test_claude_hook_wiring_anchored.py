"""Guard: Claude hook wiring anchors its script path to ${CLAUDE_PROJECT_DIR} (E10-FEAT-029).

A `PreToolUse`/`SessionEnd`/… hook command with a BARE relative script path (`python
.claude/hooks/x.py`) breaks the moment the host's shell CWD is not the repo root — e.g. after the
agent runs a `cd` in a Bash tool, the relative path resolves from the wrong directory and the hook
hard-fails (on `PreToolUse` it blocks the tool). Claude Code substitutes `${CLAUDE_PROJECT_DIR}`
as a plain string BEFORE the shell (cross-platform, incl. Windows PowerShell), so anchoring the
path there makes the wiring CWD-robust.

This is the A-09 regression: the `.ps1`→`.py` hook migration dropped the `$env:CLAUDE_PROJECT_DIR`
anchoring the PowerShell hooks had, leaving bare relative paths. Sibling of
`test_assets_hook_cli_invocation` (which guards the script→CLI invocation) on the wiring→script
side. Offline: reads the bundled Claude settings assets, no host, no network.
"""
from __future__ import annotations

import json

from sertor_installer.resources import iter_asset_dir, read_asset_text

# The anchored form Claude Code substitutes cross-platform.
_ANCHOR = "${CLAUDE_PROJECT_DIR}/.claude/hooks/"
# The exact pre-fix bare form (the A-09 regression).
_BARE = "python .claude/hooks/"


def _settings_assets() -> list[tuple[str, str]]:
    """Every bundled Claude `settings*.json` wiring asset, as (rel, content)."""
    assets = [
        (rel, body)
        for rel, body in iter_asset_dir("rag")
        if rel.rsplit("/", 1)[-1].startswith("settings") and rel.endswith(".json")
    ]
    assets.append(("settings.hooks.json", read_asset_text("settings.hooks.json")))
    return assets


def _hook_commands(data: dict) -> list[str]:
    """All `command` strings in a Claude nested hook wiring dict."""
    cmds: list[str] = []
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for entry in group.get("hooks", []):
                cmd = entry.get("command")
                if cmd:
                    cmds.append(cmd)
    return cmds


def _claude_hook_commands() -> list[str]:
    cmds: list[str] = []
    for _rel, body in _settings_assets():
        cmds.extend(_hook_commands(json.loads(body)))
    return cmds


def test_claude_hook_commands_anchor_project_dir():
    """Every command running a `.claude/hooks/` script anchors it to ${CLAUDE_PROJECT_DIR}."""
    offenders = [c for c in _claude_hook_commands() if ".claude/hooks/" in c and _ANCHOR not in c]
    assert not offenders, f"bare relative hook path (must anchor to {_ANCHOR!r}): {offenders}"


def test_claude_hook_commands_have_no_bare_relative_path():
    """The exact pre-fix bare form `python .claude/hooks/…` (the A-09 regression) is banned."""
    offenders = [c for c in _claude_hook_commands() if _BARE in c]
    assert not offenders, f"bare `{_BARE}…` reintroduced: {offenders}"


def test_settings_assets_discovered():
    """Anti-vacuity: the guard sees the wiring it polices (≥7 commands hitting .claude/hooks/)."""
    hitting = [c for c in _claude_hook_commands() if ".claude/hooks/" in c]
    assert len(hitting) >= 7, hitting
