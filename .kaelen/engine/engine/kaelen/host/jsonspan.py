"""Byte-preserving edits of JSON files (specs/017-host-verbs research R-6).

The host's shared JSON files (MCP registrations, assistant settings, hook files) are never
re-serialised: a small reader records the span of every member and element, and an edit is a
text splice. Every byte outside the spliced text stays identical, line endings included.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

_WS = " \t\r\n"
_NUMBER = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")
_LITERALS = ("true", "false", "null")


class Unmergeable(Exception):
    """The file cannot be edited without touching bytes that are not ours (FR-038)."""


class Present(Exception):
    """The address already holds a value: a conflict, never an overwrite (FR-012)."""

    def __init__(self, text: str):
        super().__init__("address already holds a value")
        self.text = text


@dataclass
class Node:
    start: int
    end: int


@dataclass
class Member:
    key: str
    start: int
    end: int
    value: Node


@dataclass
class Obj(Node):
    members: list[Member] = field(default_factory=list)


@dataclass
class Arr(Node):
    elements: list[Node] = field(default_factory=list)


class _Reader:
    def __init__(self, text: str):
        self.text = text
        self.i = 0

    def fail(self, what: str):
        raise Unmergeable(f"not valid JSON at offset {self.i}: {what}")

    def ws(self):
        t = self.text
        while self.i < len(t) and (t[self.i] in _WS or (self.i == 0 and t[0] == "﻿")):
            self.i += 1

    def value(self) -> Node:
        self.ws()
        if self.i >= len(self.text):
            self.fail("unexpected end")
        c = self.text[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c == '"':
            start = self.i
            self.string()
            return Node(start, self.i)
        for lit in _LITERALS:
            if self.text.startswith(lit, self.i):
                start = self.i
                self.i += len(lit)
                return Node(start, self.i)
        m = _NUMBER.match(self.text, self.i)
        if m:
            self.i = m.end()
            return Node(m.start(), m.end())
        self.fail(f"unexpected {c!r}")

    def string(self) -> str:
        start = self.i
        self.i += 1
        t = self.text
        while True:
            if self.i >= len(t):
                self.fail("unterminated string")
            c = t[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == '"':
                self.i += 1
                break
            if c < " ":
                self.fail("control character in string")
            self.i += 1
        try:
            return json.loads(t[start : self.i])
        except ValueError:
            self.fail("bad escape")

    def obj(self) -> Obj:
        node = Obj(self.i, -1)
        self.i += 1
        self.ws()
        if self.text.startswith("}", self.i):
            self.i += 1
            node.end = self.i
            return node
        while True:
            self.ws()
            if not self.text.startswith('"', self.i):
                self.fail("expected a member name")
            kstart = self.i
            key = self.string()
            self.ws()
            if not self.text.startswith(":", self.i):
                self.fail("expected ':'")
            self.i += 1
            value = self.value()
            node.members.append(Member(key, kstart, value.end, value))
            self.ws()
            if self.text.startswith(",", self.i):
                self.i += 1
                continue
            if self.text.startswith("}", self.i):
                self.i += 1
                node.end = self.i
                return node
            self.fail("expected ',' or '}'")

    def arr(self) -> Arr:
        node = Arr(self.i, -1)
        self.i += 1
        self.ws()
        if self.text.startswith("]", self.i):
            self.i += 1
            node.end = self.i
            return node
        while True:
            node.elements.append(self.value())
            self.ws()
            if self.text.startswith(",", self.i):
                self.i += 1
                continue
            if self.text.startswith("]", self.i):
                self.i += 1
                node.end = self.i
                return node
            self.fail("expected ',' or ']'")


def parse(text: str) -> Node:
    reader = _Reader(text)
    root = reader.value()
    reader.ws()
    if reader.i != len(text):
        reader.fail("trailing content")
    return root


def find(root: Node, path: list[str]) -> Node | None:
    node = root
    for key in path:
        if not isinstance(node, Obj):
            raise Unmergeable(f"{'.'.join(path)}: {key!r} is not inside an object")
        member = next((m for m in node.members if m.key == key), None)
        if member is None:
            return None
        node = member.value
    return node


def value_text(text: str, path: list[str]) -> str | None:
    if not text.strip():
        return None
    node = find(parse(text), path)
    return None if node is None else text[node.start : node.end]


def canonical_digest(value) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


# --- layout ---------------------------------------------------------------------------------


def newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _line_indent(text: str, pos: int) -> str:
    line_start = text.rfind("\n", 0, pos) + 1
    indent = []
    for c in text[line_start:pos]:
        if c in " \t":
            indent.append(c)
        else:
            break
    return "".join(indent)


def _unit(text: str, root: Node) -> str:
    children = root.members if isinstance(root, Obj) else getattr(root, "elements", [])
    for child in children:
        start = child.start
        if "\n" in text[root.start : start]:
            inner = _line_indent(text, start)
            outer = _line_indent(text, root.start)
            if inner.startswith(outer) and len(inner) > len(outer):
                return inner[len(outer) :]
    return "  "


def _reindent(value: str, indent: str, nl: str) -> str:
    lines = value.replace("\r\n", "\n").strip().split("\n")
    return nl.join([lines[0], *(indent + line for line in lines[1:])])


def _value(keys: list[str], leaf: str, indent: str, unit: str, nl: str, member: bool) -> str:
    """A value at `indent` holding the chain of `keys` down to the leaf.

    In member mode the leaf is the value of the last key; in element mode the last key holds an
    array whose one element is the leaf.
    """
    inner = indent + unit
    if not keys:
        if member:
            return _reindent(leaf, indent, nl)
        return "[" + nl + inner + _reindent(leaf, inner, nl) + nl + indent + "]"
    head = f"{json.dumps(keys[0], ensure_ascii=False)}: "
    return (
        "{"
        + nl
        + inner
        + head
        + _value(keys[1:], leaf, inner, unit, nl, member)
        + nl
        + indent
        + "}"
    )


def _insert_child(text: str, container: Node, child_text, unit: str, nl: str):
    """Insert a child at the end of `container`; `child_text(indent)` renders it."""
    children = container.members if isinstance(container, Obj) else container.elements
    info: dict = {}
    if children:
        last = children[-1]
        if "\n" in text[container.start : last.start]:
            indent = _line_indent(text, last.start)
            ins = "," + nl + indent + child_text(indent)
        else:
            ins = ", " + child_text(_line_indent(text, container.start) + unit)
        info["text"] = ins
        return text[: last.end] + ins + text[last.end :], info
    outer = _line_indent(text, container.start)
    indent = outer + unit
    inner = nl + indent + child_text(indent) + nl + outer
    info["inner_before"] = text[container.start + 1 : container.end - 1]
    info["text"] = inner
    return text[: container.start + 1] + inner + text[container.end - 1 :], info


def _add(text: str, path: list[str], leaf: str, leaf_name: str | None):
    """Shared body of add_member (leaf_name set) and append_element (leaf_name None)."""
    is_member = leaf_name is not None
    if not text.strip():
        nl, unit = "\n", "  "
        keys = [*path, leaf_name] if is_member else list(path)
        out = _value(keys, leaf, "", unit, nl, is_member) + nl
        created = [path[: k + 1] for k in range(len(path))]
        return out, {"created": created, "created_file": True, "text": out}
    root = parse(text)
    if not isinstance(root, Obj):
        raise Unmergeable("the top level is not an object")
    nl, unit = newline(text), _unit(text, root)
    container: Node = root
    for k, key in enumerate(path):
        member = next((m for m in container.members if m.key == key), None)
        if member is None:
            rest = path[k + 1 :]
            keys = [*rest, leaf_name] if is_member else rest

            def render(indent, key=key, keys=keys):
                head = f"{json.dumps(key, ensure_ascii=False)}: "
                return head + _value(keys, leaf, indent, unit, nl, is_member)

            out, info = _insert_child(text, container, render, unit, nl)
            info["created"] = [path[: j + 1] for j in range(k, len(path))]
            return out, info
        last = k == len(path) - 1
        wants_array = last and not is_member
        if wants_array and not isinstance(member.value, Arr):
            raise Unmergeable(f"{'.'.join(path)} does not hold an array")
        if not wants_array and not isinstance(member.value, Obj):
            raise Unmergeable(f"{'.'.join(path[: k + 1])} does not hold an object")
        container = member.value
    if is_member:
        if not isinstance(container, Obj):
            raise Unmergeable(f"{'.'.join(path)} does not hold an object")
        existing = next((m for m in container.members if m.key == leaf_name), None)
        if existing is not None:
            raise Present(text[existing.value.start : existing.value.end])

        def render(indent):
            return f"{json.dumps(leaf_name, ensure_ascii=False)}: " + _reindent(leaf, indent, nl)
    else:
        if not isinstance(container, Arr):
            raise Unmergeable(f"{'.'.join(path)} does not hold an array")

        def render(indent):
            return _reindent(leaf, indent, nl)

    out, info = _insert_child(text, container, render, unit, nl)
    info["created"] = []
    return out, info


def add_member(text: str, path: list[str], name: str, value: str):
    """Add member `name` = `value` to the object at `path`, creating missing parents.

    Returns the new text and an info dict: `created` (parent paths created), `text` (what was
    inserted), and `inner_before` when the object was empty.
    """
    return _add(text, path, value, name)


def append_element(text: str, path: list[str], value: str):
    """Append `value` to the array at `path`, creating missing parents (the array included)."""
    return _add(text, path, value, None)


def _remove_child(text: str, container: Node, idx: int, inner_before: str | None) -> str:
    children = container.members if isinstance(container, Obj) else container.elements
    if len(children) == 1:
        inner = inner_before if inner_before is not None else ""
        return text[: container.start + 1] + inner + text[container.end - 1 :]
    if idx > 0:
        return text[: children[idx - 1].end] + text[children[idx].end :]
    return text[: children[0].start] + text[children[1].start :]


def remove_member(text: str, path: list[str], name: str, inner_before: str | None = None) -> str:
    container = find(parse(text), path)
    if not isinstance(container, Obj):
        raise Unmergeable(f"{'.'.join(path)} does not hold an object")
    idx = next((i for i, m in enumerate(container.members) if m.key == name), None)
    if idx is None:
        return text
    return _remove_child(text, container, idx, inner_before)


def remove_element(
    text: str, path: list[str], identity: str, inner_before: str | None = None
) -> str:
    container = find(parse(text), path)
    if not isinstance(container, Arr):
        return text
    for idx, node in enumerate(container.elements):
        if canonical_digest(json.loads(text[node.start : node.end])) == identity:
            return _remove_child(text, container, idx, inner_before)
    return text


def find_element(text: str, path: list[str], identity: str) -> str | None:
    if not text.strip():
        return None
    container = find(parse(text), path)
    if not isinstance(container, Arr):
        return None
    for node in container.elements:
        if canonical_digest(json.loads(text[node.start : node.end])) == identity:
            return text[node.start : node.end]
    return None


def prune_empty(text: str, path: list[str]) -> str:
    """Remove the member at `path` when its value is an empty object or array."""
    root = parse(text)
    parent = find(root, path[:-1]) if len(path) > 1 else root
    if not isinstance(parent, Obj):
        return text
    idx = next((i for i, m in enumerate(parent.members) if m.key == path[-1]), None)
    if idx is None:
        return text
    value = parent.members[idx].value
    empty = (isinstance(value, Obj) and not value.members) or (
        isinstance(value, Arr) and not value.elements
    )
    if not empty:
        return text
    return _remove_child(text, parent, idx, None)


def is_skeleton(text: str) -> bool:
    """True when the document holds only empty objects and arrays (nothing anybody wrote)."""

    def empty(value) -> bool:
        if isinstance(value, dict):
            return all(empty(v) for v in value.values())
        if isinstance(value, list):
            return not value
        return False

    try:
        return empty(json.loads(text))
    except ValueError:
        return False


def replace_value(text: str, path: list[str], value: str) -> str:
    """Replace the value at `path` in place, keeping its member line's indentation."""
    node = find(parse(text), path)
    if node is None:
        raise Unmergeable(f"{'.'.join(path)} is absent")
    indent = _line_indent(text, node.start)
    return text[: node.start] + _reindent(value, indent, newline(text)) + text[node.end :]
