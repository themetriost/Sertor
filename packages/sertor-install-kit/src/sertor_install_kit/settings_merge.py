"""Additive merge of `.claude/settings.json` (D5, FR-015).

**Additive merge with deduplication by `command`**: absent → create with the fragment's hook
entries; valid → add only entries whose `command` is not already present in the same event;
malformed → `ConfigError` (fail-fast, file not touched). The events are derived from the fragment
itself (any Claude Code event, e.g. `PreToolUse`), not a fixed list. Preservation is **semantic**
(no user entry lost), not byte-for-byte: `settings.json` is structured config, not user prose (D5).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.errors import ConfigError


def _inner_commands(entry: dict) -> set[str]:
    """Extracts the `command` values of a hook entry, schema-aware (FEAT-011/data-model §4).

    Two shapes coexist after FEAT-011:
      - Claude (nested): `{matcher?, hooks: [{command, ...}]}` — commands live in the inner list.
      - Copilot (flat): `{type, command, timeoutSec, matcher?}` — the command is on the entry.
    Recognizing BOTH keeps the dedup (and the inverse removal) correct on either wiring, and on a
    file that mixes both shapes. Backward-compatible: the Claude nested form is unchanged.
    """
    commands: set[str] = set()
    for inner in entry.get("hooks", []):
        if isinstance(inner, dict) and "command" in inner:
            commands.add(inner["command"])
    # Copilot flat form: the payload is directly on the entry — `command` for a command-hook,
    # `prompt` for a prompt-hook (SessionStart on copilot-cli). BOTH serve as the dedup/removal
    # identity, so a re-run recognizes a prompt entry (idempotency, FR-040) and uninstall
    # recognizes it as Sertor-owned. Without `prompt`, a prompt entry has an empty identity.
    for key in ("command", "prompt"):
        if isinstance(entry.get(key), str):
            commands.add(entry[key])
    return commands


def _dedup_hooks(existing: dict, fragment: dict) -> tuple[dict, int]:
    """Merges the fragment into the existing entries (dedup by `command`); returns
    (merged, n_added).

    Does not mutate `existing` in place: operates on a deep copy of the `hooks` section.
    """
    merged = json.loads(json.dumps(existing))  # copia profonda
    # FEAT-011: the Copilot wiring file carries a top-level `"version": 1` (schema requirement R1).
    # Carry it over from the fragment when the existing file does not already declare one, so the
    # merged file stays schema-valid. Claude's `settings.json` has no such key → no-op for Claude.
    if "version" in fragment and "version" not in merged:
        merged["version"] = fragment["version"]
    hooks = merged.setdefault("hooks", {})
    added = 0

    # Events are derived from the union of existing + fragment hook keys (not a fixed list): a
    # consumer may bring any Claude Code event (e.g. `PreToolUse`), and the merge stays additive +
    # dedup-by-command on whatever events appear. Sorted for deterministic output.
    events = sorted(set(fragment.get("hooks", {}).keys()) | set(hooks.keys()))
    for event in events:
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


def _fragment_commands(fragment: dict) -> set[str]:
    """All `command` values declared by the Sertor fragment (across all its hook events)."""
    commands: set[str] = set()
    for entries in fragment.get("hooks", {}).values():
        for entry in entries:
            if isinstance(entry, dict):
                commands |= _inner_commands(entry)
    return commands


def remove_settings_entries(
    settings_path: Path, hooks_fragment: dict
) -> tuple[Outcome, str]:
    """Removes ONLY the Sertor-owned hook entries — inverse of `merge_settings`.

    A hook entry is Sertor-owned iff at least one of its inner `command` values appears in the
    Sertor `fragment`. The user's other hook entries (and any non-hook keys) are preserved. Reuses
    `_inner_commands` (the same recognition logic the merge uses), so the two cannot drift.

    - file absent / no Sertor-owned entry present → `(SKIPPED, "no Sertor entries")` (idempotency);
    - one or more removed → `(REMOVED, "-N hook entries")`. An event left with an empty list is
      pruned; if `hooks` becomes empty it is pruned too.
    - malformed JSON → `ConfigError` (file not touched), like the merge.
    """
    if not settings_path.exists():
        return Outcome.SKIPPED, "no Sertor entries"

    raw = settings_path.read_text(encoding="utf-8")
    try:
        existing = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"malformed JSON at line {exc.lineno}: {exc.msg}", key=str(settings_path)
        ) from exc
    if not isinstance(existing, dict):
        raise ConfigError("settings.json is not a JSON object", key=str(settings_path))

    sertor_commands = _fragment_commands(hooks_fragment)
    pruned = json.loads(json.dumps(existing))  # deep copy, never mutate in place
    hooks = pruned.get("hooks", {})
    removed = 0
    for event in list(hooks.keys()):
        kept = []
        for entry in hooks[event]:
            entry_commands = _inner_commands(entry) if isinstance(entry, dict) else set()
            if entry_commands & sertor_commands:
                removed += 1
                continue
            kept.append(entry)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if not hooks and "hooks" in pruned:
        del pruned["hooks"]

    if removed == 0:
        return Outcome.SKIPPED, "no Sertor entries"
    settings_path.write_text(
        json.dumps(pruned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return Outcome.REMOVED, f"-{removed} hook entries"
