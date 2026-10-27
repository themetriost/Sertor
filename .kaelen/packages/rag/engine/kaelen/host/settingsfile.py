"""The node's settings file (`.env`-like): defaults written, operator values never touched.

Only keys the engine adds live in its marked block `<capability>/settings`; a key is present when a
`KEY=` or `export KEY=` line exists anywhere. No value is ever reported or recorded: only digests.
"""

from __future__ import annotations

import hashlib
import re

from kaelen.host import sections
from kaelen.host.jsonspan import newline
from kaelen.host.sections import HASH

_LINE = re.compile(r"^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=(.*)$")


def present(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in text.splitlines():
        m = _LINE.match(line)
        if m and m.group(1) not in keys:
            keys[m.group(1)] = m.group(2)
    return keys


def value_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _identity(capability: str) -> str:
    return f"{capability}/settings"


def add(text: str, capability: str, pairs: list[tuple[str, str]]) -> tuple[str, dict]:
    """Add each absent key with its default; returns the text and {"added", "separator"}."""
    have = present(text)
    added = [(k, v) for k, v in pairs if k not in have]
    info = {"added": [k for k, _ in added], "separator": ""}
    if not added:
        return text, info
    ident = _identity(capability)
    lines = "".join(f"{k}={v}\n" for k, v in added)
    current = sections.body(text, ident, HASH)
    if current is None:
        out, block = sections.append(text, ident, lines, HASH)
        info["separator"] = block["separator"]
        return out, info
    return sections.replace_body(text, ident, HASH, current.replace("\r\n", "\n") + lines), info


def remove(text: str, capability: str, key: str, digest: str, separator: str) -> str:
    """Remove `key` from the block if it still holds the value written; drop an empty block."""
    ident = _identity(capability)
    current = sections.body(text, ident, HASH)
    if current is None:
        return text
    nl = newline(text)
    kept, removed = [], False
    for line in current.splitlines():
        m = _LINE.match(line)
        if m and m.group(1) == key and value_digest(m.group(2)) == digest and not removed:
            removed = True
            continue
        kept.append(line)
    if not removed:
        return text
    if not kept:
        return sections.remove(text, ident, HASH, separator)
    return sections.replace_body(text, ident, HASH, "".join(line + nl for line in kept))
