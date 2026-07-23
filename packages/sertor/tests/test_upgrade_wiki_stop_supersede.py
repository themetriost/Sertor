"""E10-FEAT-041: `upgrade` strips the SUPERSEDED wiki-pending-check Stop entry (SessionEnd kept).

wiki-guard (FEAT-040) takes over the Stop role from wiki-pending-check. The additive stem-merge on
upgrade appends wiki-guard but cannot know the OLD wiki-pending-check Stop entry (a different script
stem) is now obsolete → without this fix BOTH would fire at stop. The upgrade must strip ONLY that
Stop entry, leaving the SessionEnd wiring (still wiki-pending-check's job) intact.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import LifecycleOp
from sertor_install_kit.assistant import AssistantId
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_wiki import (
    build_install_plan,
    execute_plan,
    execute_wiki_lifecycle,
)

_SETTINGS = ".claude/settings.json"


def _pending_check_stop_entry() -> dict:
    """The pre-FEAT-040 wiring: wiki-pending-check ran the Stop hook (now wiki-guard's job)."""
    return {"hooks": [{
        "type": "command", "timeout": 10, "statusMessage": "Verifico lo stato del wiki",
        "command": ("uv run --no-project python "
                    '"${CLAUDE_PROJECT_DIR}/.claude/hooks/wiki-pending-check.py" '
                    "--mode Stop --assistant claude"),
    }]}


def _seed_old_host(target: Path) -> None:
    """Make a freshly-installed host look pre-FEAT-040: wiki-pending-check owns the Stop slot."""
    settings_path = target / _SETTINGS
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["hooks"]["Stop"] = [_pending_check_stop_entry()]  # old wiring, not wiki-guard
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def _cmds(target: Path, event: str) -> list[str]:
    settings = json.loads((target / _SETTINGS).read_text(encoding="utf-8"))
    return [h["command"] for e in settings["hooks"].get(event, []) for h in e.get("hooks", [])]


def test_upgrade_supersedes_pending_check_stop_with_wiki_guard(tmp_path: Path):
    profile = build_host_profile(tmp_path)
    execute_plan(build_install_plan(), profile)
    _seed_old_host(tmp_path)

    # pre-upgrade: the old host has wiki-pending-check at Stop, no wiki-guard.
    stop_before = _cmds(tmp_path, "Stop")
    assert any("wiki-pending-check.py" in c and "--mode Stop" in c for c in stop_before)
    assert not any("wiki-guard.py" in c for c in stop_before)

    execute_wiki_lifecycle(
        build_install_plan(AssistantId.CLAUDE), profile,
        op=LifecycleOp.UPGRADE, assistant=AssistantId.CLAUDE,
    )

    # post-upgrade: the superseded Stop entry is gone; wiki-guard is the sole Stop hook.
    stop_after = _cmds(tmp_path, "Stop")
    assert any("wiki-guard.py" in c and "--mode Stop" in c for c in stop_after)
    assert not any("wiki-pending-check.py" in c for c in stop_after), (
        "FEAT-041: the superseded wiki-pending-check Stop entry must be removed on upgrade"
    )
    # its SessionEnd wiring survives (targeted removal, not a blanket wiki-pending-check purge).
    assert any("wiki-pending-check.py" in c and "--mode SessionEnd" in c
               for c in _cmds(tmp_path, "SessionEnd"))
