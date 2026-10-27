"""Marked sections in shared text files: marking convention v1 (contracts/host-formats.md §1).

A contribution to a Markdown, TOML or settings file sits between two marker lines that carry its
identity `<capability>/<item>`. The convention is a stable contract between engines of different
ages: later versions may only add attributes after the identity, which readers ignore.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from kaelen.host.jsonspan import Unmergeable, newline


@dataclass(frozen=True)
class Style:
    name: str
    begin: str
    end: str
    pattern: re.Pattern


MARKDOWN = Style(
    "markdown",
    "<!-- kaelen:begin {} -->",
    "<!-- kaelen:end {} -->",
    re.compile(
        r"^[ \t]*<!--[ \t]*kaelen:(begin|end)[ \t]+(\S+)(?:[ \t]+[^\r\n]*?)?[ \t]*-->[ \t]*$"
    ),
)
HASH = Style(
    "hash",
    "# kaelen:begin {}",
    "# kaelen:end {}",
    re.compile(r"^[ \t]*#[ \t]*kaelen:(begin|end)[ \t]+(\S+)(?:[ \t]+[^\r\n]*)?$"),
)


@dataclass(frozen=True)
class Span:
    start: int  # first byte of the begin line
    body_start: int  # first byte after the begin line's terminator
    body_end: int  # first byte of the end line
    end: int  # first byte after the end line's terminator (or end of text)


def _lines(text: str):
    pos = 0
    for line in text.splitlines(keepends=True):
        yield pos, line
        pos += len(line)


def find_all(text: str, style: Style) -> dict[str, Span]:
    """Every marked section of `text`; refuses unpaired, nested or duplicated markers."""
    found: dict[str, Span] = {}
    open_id = open_start = open_body = None
    for pos, line in _lines(text):
        m = style.pattern.match(line.rstrip("\r\n"))
        if not m:
            continue
        what, ident = m.group(1), m.group(2)
        if what == "begin":
            if open_id is not None:
                raise Unmergeable(f"section {open_id!r} is not closed before {ident!r} begins")
            if ident in found:
                raise Unmergeable(f"section {ident!r} appears more than once")
            open_id, open_start, open_body = ident, pos, pos + len(line)
        else:
            if open_id != ident:
                raise Unmergeable(f"end marker of {ident!r} without its begin marker")
            found[ident] = Span(open_start, open_body, pos, pos + len(line))
            open_id = None
    if open_id is not None:
        raise Unmergeable(f"section {open_id!r} has no end marker")
    return found


def body(text: str, identity: str, style: Style) -> str | None:
    span = find_all(text, style).get(identity)
    return None if span is None else text[span.body_start : span.body_end]


def digest(body_text: str) -> str:
    data = body_text.replace("\r\n", "\n").encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _block(identity: str, body_text: str, style: Style, nl: str) -> str:
    content = body_text.replace("\r\n", "\n").replace("\n", nl)
    if content and not content.endswith(nl):
        content += nl
    return style.begin.format(identity) + nl + content + style.end.format(identity) + nl


def append(text: str, identity: str, body_text: str, style: Style) -> tuple[str, dict]:
    """Append a section; returns the new text and {"separator", "text"} for exact removal."""
    if identity in find_all(text, style):
        raise Unmergeable(f"section {identity!r} is already present")
    nl = newline(text) if text else "\n"
    if not text:
        separator = ""
    elif text.endswith("\n"):
        separator = nl
    else:
        separator = nl + nl
    block = _block(identity, body_text, style, nl)
    return text + separator + block, {"separator": separator, "text": separator + block}


def remove(text: str, identity: str, style: Style, separator: str) -> str:
    span = find_all(text, style).get(identity)
    if span is None:
        return text
    start = span.start
    if separator and text[max(0, start - len(separator)) : start] == separator:
        start -= len(separator)
    return text[:start] + text[span.end :]


def replace_body(text: str, identity: str, style: Style, body_text: str) -> str:
    span = find_all(text, style)[identity]
    nl = newline(text)
    content = body_text.replace("\r\n", "\n").replace("\n", nl)
    if content and not content.endswith(nl):
        content += nl
    return text[: span.body_start] + content + text[span.body_end :]
