"""E10-FEAT-032: hook identity is the SCRIPT, not the command string.

These tests cover the hole every previous guard missed: they assert the OUTCOME ON A HOST THAT
UPGRADES (an existing wiring in an older rendering → the new one), not the shape of the bundled
asset. The FEAT-031 guards checked that the asset DECLARES an anchored command and were green while
every upgrading host silently ended up with the hook wired twice — the stale copy still firing.

The three renderings Sertor has actually shipped for the SAME hook:
  - PowerShell           `pwsh -File .github/hooks/rag-freshness.ps1`            (pre A-09)
  - portable, relative   `uv run --no-project python .claude/hooks/x.py`         (A-09 → FEAT-031)
  - portable, anchored   `uv run --no-project python "${CLAUDE_PROJECT_DIR}/…"`  (FEAT-031 →)
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.settings_merge import merge_settings

_HOOK = "rag-freshness"
_RELATIVE = f"uv run --no-project python .claude/hooks/{_HOOK}.py --assistant claude"
_ANCHORED = (
    f'uv run --no-project python "${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{_HOOK}.py" '
    "--assistant claude"
)
_PS1 = f"& (Join-Path $d 'hooks/{_HOOK}.ps1')"


def _claude(command: str) -> dict:
    return {"hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": command}]}]}}


def _commands(p: Path) -> list[str]:
    data = json.loads(p.read_text(encoding="utf-8"))
    return [
        inner["command"]
        for entries in data["hooks"].values()
        for e in entries
        for inner in e.get("hooks", [])
    ]


def _write(p: Path, fragment: dict) -> None:
    p.write_text(json.dumps(fragment, indent=2) + "\n", encoding="utf-8")


# --- the regression itself: relative → anchored (FEAT-031's own transition) -------------------


def test_upgrade_rewires_relative_to_anchored_single_impl(tmp_path: Path):
    """The bug: upgrading left the relative (broken) entry AND appended the anchored one."""
    p = tmp_path / "settings.json"
    _write(p, _claude(_RELATIVE))

    merge_settings(p, _claude(_ANCHORED), replace_stale=True)

    assert _commands(p) == [_ANCHORED], "the stale rendering must be replaced, not accompanied"


def test_install_does_not_duplicate_and_names_the_stale_hook(tmp_path: Path):
    """Install must not remove (its contract) — but must not DUPLICATE either, and must say so."""
    p = tmp_path / "settings.json"
    _write(p, _claude(_RELATIVE))

    outcome, detail = merge_settings(p, _claude(_ANCHORED))  # replace_stale=False

    assert outcome is Outcome.MERGED
    assert _commands(p) == [_RELATIVE], "install never rewrites the host's wiring"
    assert _HOOK in detail and "upgrade" in detail, (
        f"install must NAME the stale hook and point at `upgrade`, got: {detail!r}"
    )


# --- the axis Noetix's host was on: PowerShell → Python --------------------------------------


def test_upgrade_rewires_ps1_to_py(tmp_path: Path):
    """Reported by the Noetix node (2026-07-16): `.ps1` + `.py` wired side by side, both firing."""
    p = tmp_path / "settings.json"
    _write(p, _claude(_PS1))

    merge_settings(p, _claude(_ANCHORED), replace_stale=True)

    assert _commands(p) == [_ANCHORED]


# --- the Copilot axis: same command, a sibling key changed (the SILENT failure) ---------------


def test_upgrade_rewires_when_only_cwd_was_added(tmp_path: Path):
    """Copilot's FEAT-031 fix added `cwd` and left the command untouched → the old dedup saw a
    duplicate and DISCARDED the fix. Worse than a duplicate: silently no-op."""
    p = tmp_path / "sertor-hooks.json"
    cmd = f"uv run --no-project python .github/hooks/{_HOOK}.py --assistant copilot-cli"
    _write(p, {"version": 1, "hooks": {"SessionEnd": [{"type": "command", "command": cmd}]}})

    fragment = {
        "version": 1,
        "hooks": {"SessionEnd": [{"type": "command", "command": cmd, "cwd": "."}]},
    }
    merge_settings(p, fragment, replace_stale=True)

    entries = json.loads(p.read_text(encoding="utf-8"))["hooks"]["SessionEnd"]
    assert len(entries) == 1, "the same hook must not be wired twice"
    assert entries[0].get("cwd") == ".", "the fix must actually land"


# --- the real host state: SEVERAL renderings of one hook, already duplicated -----------------


def test_upgrade_collapses_an_already_duplicated_hook(tmp_path: Path):
    """The dogfood's actual state (2026-07-16): a pre-fix `install` had ALREADY appended the
    anchored entry next to the relative one. Upgrading must collapse BOTH into one — replacing only
    the first match would leave two identical entries behind (caught on the real host, not here)."""
    p = tmp_path / "settings.json"
    _write(
        p,
        {
            "hooks": {
                "SessionEnd": [
                    {"hooks": [{"type": "command", "command": _RELATIVE}]},
                    {"hooks": [{"type": "command", "command": _ANCHORED}]},
                ]
            }
        },
    )

    merge_settings(p, _claude(_ANCHORED), replace_stale=True)

    assert _commands(p) == [_ANCHORED], "one hook → exactly one wiring per event"


def test_upgrade_collapses_three_generations(tmp_path: Path):
    """`.ps1` + relative `.py` + anchored `.py` at once — every generation Sertor has shipped."""
    p = tmp_path / "settings.json"
    _write(
        p,
        {
            "hooks": {
                "SessionEnd": [
                    {"hooks": [{"type": "command", "command": _PS1}]},
                    {"hooks": [{"type": "command", "command": _RELATIVE}]},
                    {"hooks": [{"type": "command", "command": _ANCHORED}]},
                ]
            }
        },
    )

    merge_settings(p, _claude(_ANCHORED), replace_stale=True)

    assert _commands(p) == [_ANCHORED]


def test_install_reports_a_duplicated_hook_without_touching_it(tmp_path: Path):
    p = tmp_path / "settings.json"
    _write(
        p,
        {
            "hooks": {
                "SessionEnd": [
                    {"hooks": [{"type": "command", "command": _RELATIVE}]},
                    {"hooks": [{"type": "command", "command": _ANCHORED}]},
                ]
            }
        },
    )

    _, detail = merge_settings(p, _claude(_ANCHORED))

    assert _commands(p) == [_RELATIVE, _ANCHORED], "install does not rewrite"
    assert _HOOK in detail and "upgrade" in detail


# --- invariants that must NOT regress --------------------------------------------------------


def test_user_hook_with_unrelated_script_is_preserved(tmp_path: Path):
    p = tmp_path / "settings.json"
    mine = "python .claude/hooks/my-own-thing.py"
    _write(p, _claude(mine))

    merge_settings(p, _claude(_ANCHORED), replace_stale=True)

    assert set(_commands(p)) == {mine, _ANCHORED}, "a user's own hook is never touched"


def test_rerun_is_idempotent(tmp_path: Path):
    p = tmp_path / "settings.json"
    merge_settings(p, _claude(_ANCHORED))
    outcome, detail = merge_settings(p, _claude(_ANCHORED))

    assert outcome is Outcome.MERGED
    assert detail == "no new entries"
    assert _commands(p) == [_ANCHORED]


def test_same_hook_in_a_different_event_is_a_different_wiring(tmp_path: Path):
    """Identity is per-event: `wiki-pending-check` legitimately runs on both Stop and SessionEnd."""
    p = tmp_path / "settings.json"
    stop = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": _ANCHORED}]}]}}
    _write(p, stop)

    merge_settings(p, _claude(_ANCHORED), replace_stale=True)  # SessionEnd

    data = json.loads(p.read_text(encoding="utf-8"))
    assert set(data["hooks"]) == {"Stop", "SessionEnd"}, "both events keep their wiring"
