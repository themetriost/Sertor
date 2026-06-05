"""Parsing del frontmatter e dei wikilink via regex su stdlib (research D2).

Il frontmatter del wiki è semplice (coppie `chiave: valore`, liste di tag): basta `re`, senza
librerie YAML (Principio III, nessuna nuova dipendenza). Si estraggono i campi scalari, le liste
in stile `[a, b]` o `- voce`, e i bersagli dei wikilink `[[name]]` uscenti dal corpo.
"""
from __future__ import annotations

import re

# Blocco frontmatter all'inizio del file: `---\n ... \n---`.
_FM_BLOCK = re.compile(r"\A﻿?---[ \t]*\r?\n(?P<body>.*?)\r?\n---[ \t]*\r?\n?", re.DOTALL)
# Coppia `chiave: valore` (chiave alfanumerica/underscore, indentazione zero).
_FM_PAIR = re.compile(r"^(?P<key>[A-Za-z0-9_-]+)[ \t]*:[ \t]*(?P<value>.*)$")
# Voce di lista in blocco (`  - foo`).
_FM_ITEM = re.compile(r"^[ \t]*-[ \t]+(?P<value>.*)$")
# Wikilink `[[target]]` (eventuale alias `[[target|alias]]` → si tiene il target).
_WIKILINK = re.compile(r"\[\[([^\[\]|#]+)(?:[#|][^\[\]]*)?\]\]")


def _strip_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_list(raw: str) -> list[str]:
    """Interpreta una lista inline `[a, b, c]` (o `[]`)."""
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [_strip_scalar(part) for part in inner.split(",") if part.strip()]


def parse_frontmatter(text: str) -> dict:
    """Estrae il frontmatter come dizionario; `{}` se il blocco è assente.

    Gestisce scalari, liste inline `[a, b]` e liste in blocco (`- voce`). Non interpreta YAML
    annidato (non serve per il wiki): valori complessi restano stringhe.
    """
    match = _FM_BLOCK.match(text)
    if not match:
        return {}

    fields: dict[str, object] = {}
    pending_key: str | None = None
    pending_items: list[str] = []

    def _flush() -> None:
        nonlocal pending_key, pending_items
        if pending_key is not None:
            fields[pending_key] = list(pending_items)
            pending_key = None
            pending_items = []

    for line in match.group("body").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = _FM_ITEM.match(line)
        if item is not None and pending_key is not None:
            pending_items.append(_strip_scalar(item.group("value")))
            continue
        pair = _FM_PAIR.match(line)
        if pair is None:
            continue
        _flush()
        key = pair.group("key")
        value = pair.group("value").strip()
        if value == "":
            # Possibile lista in blocco nelle righe seguenti.
            pending_key = key
            pending_items = []
        elif value.startswith("[") and value.endswith("]"):
            fields[key] = _parse_list(value)
        else:
            fields[key] = _strip_scalar(value)
    _flush()
    return fields


def has_frontmatter(text: str) -> bool:
    """`True` se il documento apre con un blocco frontmatter parsabile."""
    return _FM_BLOCK.match(text) is not None


def missing_required(fields: dict, required: list[str]) -> list[str]:
    """Campi richiesti assenti o vuoti, nell'ordine di `required` (Principio IV)."""
    missing: list[str] = []
    for name in required:
        value = fields.get(name)
        if value is None or value == "" or value == []:
            missing.append(name)
    return missing


def body_after_frontmatter(text: str) -> str:
    """Corpo del documento dopo il blocco frontmatter (o l'intero testo se assente)."""
    match = _FM_BLOCK.match(text)
    return text[match.end():] if match else text


def extract_wikilinks(text: str) -> list[str]:
    """Bersagli `[[..]]` uscenti, deduplicati preservando l'ordine di prima occorrenza."""
    seen: dict[str, None] = {}
    for raw in _WIKILINK.findall(body_after_frontmatter(text)):
        target = raw.strip()
        if target:
            seen.setdefault(target, None)
    return list(seen)
