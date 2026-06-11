"""Merge di `.claude/settings.json` (D5, FR-015).

Merge **additivo con deduplicazione per `command`**: assente → crea con le 3 voci hook; valido →
aggiunge solo le voci il cui `command` non è già presente nello stesso evento; malformato →
`ConfigError` (fail-fast, file non toccato). La preservazione è **semantica** (nessuna voce
utente persa), non byte-per-byte: `settings.json` è config strutturata, non prosa utente (D5).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_core.domain.errors import ConfigError
from sertor_installer.artifacts import Outcome

_HOOK_EVENTS = ("SessionStart", "Stop", "SessionEnd")


def _inner_commands(entry: dict) -> set[str]:
    """Estrae i `command` delle voci innermost di una entry hook (`{hooks:[{command:...}]}`)."""
    commands: set[str] = set()
    for inner in entry.get("hooks", []):
        if isinstance(inner, dict) and "command" in inner:
            commands.add(inner["command"])
    return commands


def _dedup_hooks(existing: dict, fragment: dict) -> tuple[dict, int]:
    """Fonde il frammento nelle voci esistenti (dedup per `command`); ritorna (merged, n_aggiunte).

    Non muta `existing` in place: lavora su una copia profonda della sezione `hooks`.
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
            # aggiungi solo se NESSUN command della voce è già presente nell'evento
            if entry_commands & existing_commands:
                continue
            event_entries.append(entry)
            existing_commands |= entry_commands
            added += 1

    return merged, added


def merge_settings(settings_path: Path, hooks_fragment: dict) -> tuple[Outcome, str]:
    """Applica il merge dedup (D5). Ritorna `(outcome, detail)`.

    - assente → crea il file con le voci del frammento → `(CREATED, "+N voci hook")`;
    - presente valido → merge additivo → `(MERGED, "+N voci hook" | "nessuna nuova voce")`;
    - presente malformato → `ConfigError` (file non toccato).
    """
    if not settings_path.exists():
        _, added = _dedup_hooks({}, hooks_fragment)
        merged, _ = _dedup_hooks({}, hooks_fragment)
        settings_path.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return Outcome.CREATED, f"+{added} voci hook"

    raw = settings_path.read_text(encoding="utf-8")
    try:
        existing = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"JSON malformato alla riga {exc.lineno}: {exc.msg}", key=str(settings_path)
        ) from exc
    if not isinstance(existing, dict):
        raise ConfigError("settings.json non è un oggetto JSON", key=str(settings_path))

    merged, added = _dedup_hooks(existing, hooks_fragment)
    settings_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    detail = f"+{added} voci hook" if added else "nessuna nuova voce"
    return Outcome.MERGED, detail
