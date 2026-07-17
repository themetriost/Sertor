"""Additive merge of `.claude/settings.json` (D5, FR-015).

**Additive merge, deduplicated by hook IDENTITY**: absent → create with the fragment's hook entries;
valid → add only entries whose hook is not already wired for the same event; malformed →
`ConfigError` (fail-fast, file not touched). The events are derived from the fragment itself (any
Claude Code event, e.g. `PreToolUse`), not a fixed list. Preservation is **semantic** (no user entry
lost), not byte-for-byte: `settings.json` is structured config, not user prose (D5).

**Identity is the hook SCRIPT, not the command string (E10-FEAT-032).** Sertor re-wires the same
hook over time — PowerShell → portable Python (A-09), relative path → anchored on
`${CLAUDE_PROJECT_DIR}` (FEAT-031), added `cwd` for Copilot — so the raw command string is a MUTABLE
rendering detail. Keying identity on it made every re-wiring look like a NEW hook: the stale entry
was never recognised, so it **survived** and the new one was **appended** (Claude → the same hook
wired twice, the broken copy still firing) or, when only a sibling key changed, the incoming entry
was discarded as a duplicate (Copilot → the fix never landed, silently). Keying on the script stem
(`rag-freshness`) makes all three transitions the same hook, so a re-wiring is seen as such:

- `merge_settings(..., replace_stale=False)` — the INSTALL contract (idempotent, non-destructive):
  never removes, and now never DUPLICATES either. A stale form is left untouched and REPORTED, so
  the host is told to run `upgrade` instead of being silently left with two wirings.
- `merge_settings(..., replace_stale=True)` — the UPGRADE contract: the stale form is replaced in
  place (Sertor-owned wiring only; the user's own entries are never matched).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.errors import ConfigError

# A hook command references its script: `… python .claude/hooks/x.py --assistant claude`,
# `… python "${CLAUDE_PROJECT_DIR}/.claude/hooks/x.py" …`, `pwsh -File .github/hooks/x.ps1`,
# `& (Join-Path $d 'hooks/x.ps1')`. The STEM (`x`) is what survives every re-wiring → the identity.
_SCRIPT_RE = re.compile(r"([\w][\w.-]*)\.(?:py|ps1)\b")


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


def _entry_identities(entry: dict) -> set[str]:
    """Logical identity of a hook entry: the STEM of each script it runs (E10-FEAT-032).

    `python .claude/hooks/rag-freshness.py`, `python "${CLAUDE_PROJECT_DIR}/.claude/hooks/
    rag-freshness.py"` and `pwsh -File .github/hooks/rag-freshness.ps1` all yield `rag-freshness`:
    ONE hook, three renderings. An entry that runs no script (a Copilot SessionStart `prompt`) has
    no script identity — `_inner_commands` stays its identity, so its behaviour is unchanged.
    """
    return {m.group(1) for cmd in _inner_commands(entry) for m in _SCRIPT_RE.finditer(cmd)}


def _dedup_hooks(
    existing: dict, fragment: dict, *, replace_stale: bool = False
) -> tuple[dict, int, int, list[str]]:
    """Merges the fragment into the existing entries; returns (merged, n_added, n_replaced, stale).

    Per event, an incoming entry is matched against the existing ones by identity (script stem, with
    the command string as the fallback for script-less `prompt` entries):

    - an existing entry EQUAL to the incoming one → already wired, nothing to do;
    - an existing entry with the SAME identity but a different rendering → a STALE form of the same
      hook (re-wired since it was installed). `replace_stale` decides: `True` (upgrade) replaces it
      in place; `False` (install) leaves it and reports it — never appending a second wiring of the
      same hook, which is what produced the duplicates (E10-FEAT-032);
    - no match → appended (the genuinely new hook).

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
    replaced = 0
    stale: list[str] = []

    # Events are derived from the union of existing + fragment hook keys (not a fixed list): a
    # consumer may bring any Claude Code event (e.g. `PreToolUse`), and the merge stays additive +
    # dedup-by-identity on whatever events appear. Sorted for deterministic output.
    events = sorted(set(fragment.get("hooks", {}).keys()) | set(hooks.keys()))
    for event in events:
        frag_entries = fragment.get("hooks", {}).get(event, [])
        if not frag_entries:
            continue
        event_entries = hooks.setdefault(event, [])
        for entry in frag_entries:
            ids = _entry_identities(entry)
            cmds = _inner_commands(entry)
            # ALL the entries wiring this hook — not just the first. A host can carry SEVERAL stale
            # renderings at once (a `.ps1` AND a relative `.py`, or the duplicates a pre-fix install
            # already created); collapsing only the first would leave the rest behind — or, when the
            # first is stale and a good one follows, produce two identical entries. One hook = ONE
            # wiring per event, whatever the host arrived with (E10-FEAT-032).
            matches = [
                i
                for i, cur in enumerate(event_entries)
                if isinstance(cur, dict)
                and (
                    (ids & _entry_identities(cur))
                    if (ids and _entry_identities(cur))
                    else (cmds & _inner_commands(cur))
                )
            ]
            if not matches:
                event_entries.append(entry)
                added += 1
                continue
            if all(event_entries[i] == entry for i in matches) and len(matches) == 1:
                continue  # already wired, byte-for-byte → nothing to do
            # At least one rendering differs (or the hook is wired more than once): replace
            # (upgrade) or report (install) — install NEVER appends a second wiring (that is what
            # produced the duplicates), and NEVER rewrites the host's entries (its contract).
            label = sorted(ids)[0] if ids else event
            if replace_stale:
                event_entries[matches[0]] = entry
                for i in reversed(matches[1:]):
                    del event_entries[i]
                replaced += 1
            else:
                stale.append(label)

    return merged, added, replaced, stale


def merge_settings(
    settings_path: Path, hooks_fragment: dict, *, replace_stale: bool = False
) -> tuple[Outcome, str]:
    """Applies the identity merge (D5). Returns `(outcome, detail)`.

    - absent → create the file with the fragment entries → `(CREATED, "+N hook entries")`;
    - present and valid → merge → `(MERGED, detail)`;
    - present and malformed → `ConfigError` (file not touched).

    `replace_stale=False` (INSTALL) never removes and never duplicates: a hook already wired in an
    older rendering is left alone and named in the detail, pointing at `upgrade` — the honest report
    the host needs to know it is NOT up to date (Principio XII). `replace_stale=True` (UPGRADE)
    replaces the stale rendering in place.
    """
    if not settings_path.exists():
        merged, added, _, _ = _dedup_hooks({}, hooks_fragment, replace_stale=replace_stale)
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

    merged, added, replaced, stale = _dedup_hooks(
        existing, hooks_fragment, replace_stale=replace_stale
    )
    settings_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    bits = []
    if added:
        bits.append(f"+{added} hook entries")
    if replaced:
        bits.append(f"~{replaced} re-wired")
    if stale:
        # Named, not counted: the host must know WHICH hook is stale to act on it.
        bits.append(f"{len(stale)} stale ({', '.join(sorted(stale))}) — run `sertor upgrade`")
    return Outcome.MERGED, " · ".join(bits) if bits else "no new entries"


def _fragment_commands(fragment: dict) -> set[str]:
    """All `command` values declared by the Sertor fragment (across all its hook events)."""
    commands: set[str] = set()
    for entries in fragment.get("hooks", {}).values():
        for entry in entries:
            if isinstance(entry, dict):
                commands |= _inner_commands(entry)
    return commands


def remove_hook_entries_by_command_substring(
    settings_path: Path, substrings: tuple[str, ...], *, delete_if_empty: bool = False
) -> tuple[Outcome, str]:
    """Removes hook entries whose `command` CONTAINS any of `substrings` — a migration primitive.

    Sibling of `remove_settings_entries` (exact-command match), but matches by substring so it can
    strip a PREVIOUS wiring form whose exact command string is no longer known — e.g. the legacy
    `.ps1` hook entries (Claude `& (Join-Path … 'hooks/<name>.ps1')` or Copilot `pwsh -File
    .github/hooks/<name>.ps1`) that an `upgrade` replaces with the portable `.py` wiring (A-09). The
    substrings are the Sertor hook `.ps1` basenames, so only Sertor's own legacy entries match; a
    user's unrelated hook is preserved. Same shape/idempotency as `remove_settings_entries`.
    """
    if not settings_path.exists():
        return Outcome.SKIPPED, "no legacy entries"

    raw = settings_path.read_text(encoding="utf-8")
    try:
        existing = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"malformed JSON at line {exc.lineno}: {exc.msg}", key=str(settings_path)
        ) from exc
    if not isinstance(existing, dict):
        raise ConfigError("settings.json is not a JSON object", key=str(settings_path))

    pruned = json.loads(json.dumps(existing))  # deep copy, never mutate in place
    hooks = pruned.get("hooks", {})
    removed = 0
    for event in list(hooks.keys()):
        kept = []
        for entry in hooks[event]:
            cmds = _inner_commands(entry) if isinstance(entry, dict) else set()
            if any(sub in cmd for cmd in cmds for sub in substrings):
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
        return Outcome.SKIPPED, "no legacy entries"
    if delete_if_empty and "hooks" not in pruned and set(pruned.keys()) <= {"version"}:
        settings_path.unlink()
        return Outcome.REMOVED, "file removed (no entries left)"
    settings_path.write_text(
        json.dumps(pruned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return Outcome.REMOVED, f"-{removed} legacy hook entries"


def remove_settings_entries(
    settings_path: Path, hooks_fragment: dict, *, delete_if_empty: bool = False
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
    # A Sertor-DEDICATED hooks file (Copilot's `.github/hooks/sertor-hooks.json`) left with no hooks
    # after removing the Sertor entries is an empty shell (`{"version": 1}`) — delete it instead of
    # writing back the shell. NEVER for a SHARED file (Claude's `.claude/settings.json`), which
    # keeps the user's other content; there `delete_if_empty` stays False.
    if delete_if_empty and "hooks" not in pruned and set(pruned.keys()) <= {"version"}:
        settings_path.unlink()
        return Outcome.REMOVED, "file removed (no Sertor entries left)"
    settings_path.write_text(
        json.dumps(pruned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return Outcome.REMOVED, f"-{removed} hook entries"
