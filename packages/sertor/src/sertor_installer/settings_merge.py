"""Additive merge of `.claude/settings.json` (D5, FR-015).

**Additive merge with deduplication by `command`**: absent → create with the 3 hook entries;
valid → add only entries whose `command` is not already present in the same event; malformed →
`ConfigError` (fail-fast, file not touched). Preservation is **semantic** (no user entry lost),
not byte-for-byte: `settings.json` is structured config, not user prose (D5).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_core.domain.errors import ConfigError
from sertor_installer.artifacts import Outcome

_HOOK_EVENTS = ("SessionStart", "Stop", "SessionEnd")


def _inner_commands(entry: dict) -> set[str]:
    """Extracts the `command` values from the innermost entries of a hook entry
    (`{hooks:[{command:...}]}`)."""
    commands: set[str] = set()
    for inner in entry.get("hooks", []):
        if isinstance(inner, dict) and "command" in inner:
            commands.add(inner["command"])
    return commands


def _dedup_hooks(existing: dict, fragment: dict) -> tuple[dict, int]:
    """Merges the fragment into the existing entries (dedup by `command`); returns
    (merged, n_added).

    Does not mutate `existing` in place: operates on a deep copy of the `hooks` section.
    """
    merged = json.loads(json.dumps(existing))  # copia profonda
    hooks = merged.setdefault("hooks", {})
    added = 0

    for event in _HOOK_EVENTS:
        frag_entries = fragment.get("hooks", {}).get(event, [])
        if not frag_entries:
            continue
        event_entries = hooks.setdefault(event, [])
        existing_commands: set[str] = set()
        for entry in event_entries:
            if isinstance(entry, dict):
                existing_commands |= _inner_commands(entry)
        for entry in frag_entries:
            entry_commands = _inner_commands(entry)
            # add only if NONE of the entry's commands are already present in the event
            if entry_commands & existing_commands:
                continue
            event_entries.append(entry)
            existing_commands |= entry_commands
            added += 1

    return merged, added


def merge_settings(settings_path: Path, hooks_fragment: dict) -> tuple[Outcome, str]:
    """Applies the dedup merge (D5). Returns `(outcome, detail)`.

    - absent → create the file with the fragment entries → `(CREATED, "+N hook entries")`;
    - present and valid → additive merge → `(MERGED, "+N hook entries" | "no new entries")`;
    - present and malformed → `ConfigError` (file not touched).
    """
    if not settings_path.exists():
        _, added = _dedup_hooks({}, hooks_fragment)
        merged, _ = _dedup_hooks({}, hooks_fragment)
        settings_path.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return Outcome.CREATED, f"+{added} hook entries"

    raw = settings_path.read_text(encoding="utf-8")
    try:
        existing = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"malformed JSON at line {exc.lineno}: {exc.msg}", key=str(settings_path)
        ) from exc
    if not isinstance(existing, dict):
        raise ConfigError("settings.json is not a JSON object", key=str(settings_path))

    merged, added = _dedup_hooks(existing, hooks_fragment)
    settings_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    detail = f"+{added} hook entries" if added else "no new entries"
    return Outcome.MERGED, detail
