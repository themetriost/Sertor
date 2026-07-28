"""Frontmatter and wikilink parsing via stdlib regex (research D2).

The wiki frontmatter is simple (`key: value` pairs, tag lists): plain `re` is enough, no
YAML libraries needed (Principio III, no new dependency). Extracts scalar fields, inline lists
`[a, b]` or block lists `- item`, and outgoing wikilink `[[name]]` targets from the body.
"""
from __future__ import annotations

import re

# Frontmatter block at the start of the file: `---\n ... \n---`.
_FM_BLOCK = re.compile(r"\A﻿?---[ \t]*\r?\n(?P<body>.*?)\r?\n---[ \t]*\r?\n?", re.DOTALL)
# `key: value` pair (alphanumeric/underscore key, zero indentation).
_FM_PAIR = re.compile(r"^(?P<key>[A-Za-z0-9_-]+)[ \t]*:[ \t]*(?P<value>.*)$")
# Block list item (`  - foo`).
_FM_ITEM = re.compile(r"^[ \t]*-[ \t]+(?P<value>.*)$")
# Wikilink `[[target]]` (optional alias `[[target|alias]]` → target is kept).
_WIKILINK = re.compile(r"\[\[([^\[\]|#]+)(?:[#|][^\[\]]*)?\]\]")
# Fenced code block (``` or ~~~, >=3 markers, optional info string), closed by the SAME marker run.
# An UNTERMINATED fence is deliberately not matched: conservative, we prefer a false link to eating
# the rest of the page.
_FENCE = re.compile(
    r"^[ \t]*(?P<f>`{3,}|~{3,})[^\n]*\n.*?^[ \t]*(?P=f)[ \t]*$",
    re.DOTALL | re.MULTILINE,
)
# Inline code span: a backtick run closed by an identical run (CommonMark rule).
_INLINE_CODE = re.compile(r"(?P<t>`+)(?:(?!(?P=t)).)*?(?P=t)", re.DOTALL)


def _strip_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_list(raw: str) -> list[str]:
    """Parses an inline list `[a, b, c]` (or `[]`)."""
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [_strip_scalar(part) for part in inner.split(",") if part.strip()]


def parse_frontmatter(text: str) -> dict:
    """Extracts the frontmatter as a dictionary; `{}` if the block is absent.

    Handles scalars, inline lists `[a, b]` and block lists (`- item`). Does not parse nested YAML
    (not needed for the wiki): complex values remain strings.
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
            # Possible block list in the following lines.
            pending_key = key
            pending_items = []
        elif value.startswith("[") and value.endswith("]"):
            fields[key] = _parse_list(value)
        else:
            fields[key] = _strip_scalar(value)
    _flush()
    return fields


def has_frontmatter(text: str) -> bool:
    """`True` if the document opens with a parsable frontmatter block."""
    return _FM_BLOCK.match(text) is not None


def missing_required(fields: dict, required: list[str]) -> list[str]:
    """Required fields that are absent or empty, in the order of `required` (Principio IV)."""
    missing: list[str] = []
    for name in required:
        value = fields.get(name)
        if value is None or value == "" or value == []:
            missing.append(name)
    return missing


def body_after_frontmatter(text: str) -> str:
    """Document body after the frontmatter block (or the entire text if absent)."""
    match = _FM_BLOCK.match(text)
    return text[match.end():] if match else text


def strip_code(text: str) -> str:
    """Body without fenced blocks and inline code spans (fences first, then spans).

    `[[..]]` inside code is NOT a link: it is sample syntax the page is quoting — TOML
    array-of-tables (`[[requirement]]`), or the wikilink form named literally while explaining it
    (`` `[[x]]` ``). Extracting from code produced *false* broken links, which is worse than noise:
    a lint that cries wolf trains its reader to ignore it.
    """
    return _INLINE_CODE.sub(" ", _FENCE.sub("\n", text))


def extract_wikilinks(text: str) -> list[str]:
    """Outgoing `[[..]]` targets, deduplicated while preserving first-occurrence order.

    Code (fences and inline spans) is stripped first — see `strip_code`.
    """
    seen: dict[str, None] = {}
    for raw in _WIKILINK.findall(strip_code(body_after_frontmatter(text))):
        target = raw.strip()
        if target:
            seen.setdefault(target, None)
    return list(seen)
