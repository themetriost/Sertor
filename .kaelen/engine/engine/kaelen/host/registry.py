"""The per-capability registry (contracts/host-formats.md §2; location specs/026 R-1, R-5).

A stable contract between engines of different ages: additive only. A reader accepts unknown
fields and keeps them when it rewrites its own capability's file; it never writes another's.
It lives in the capability's home, `.<node>/kaelen/<capability>/registry.json`; engines up to
0.11.0 kept it at `.kaelen/registry/<capability>.json`, which is read and no longer written.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from kaelen.host import home as homes

SCHEMA = "kaelen.registry/1"

ORDER = (
    "schema",
    "node",
    "capability",
    "version",
    "contract",
    "package",
    "engine",
    "placement_rule",
    "targets",
    "locations",
    "shared_files",
    "unsupported",
    "settings",
)
# Fields this engine writes beyond ORDER (specs/026..029): absent from a new registry means gone,
# never "unknown to this engine, keep it" (specs/029 analyze I1)
OWNED = (*ORDER, "created_dirs", "shared_writer", "origin", "provenance", "requires", "groups")
_REQUIRED = {
    "schema": str,
    "node": str,
    "capability": str,
    "version": str,
    "contract": int,
    "engine": dict,
    "targets": list,
    "locations": list,
}


class UnreadableRegistry(Exception):
    """The registry file exists but cannot be read as a registry (FR-043)."""


class UnsupportedRegistry(Exception):
    """The registry file carries a schema this engine does not support (FR-043)."""

    def __init__(self, found):
        super().__init__(f"registry schema {found!r} is not supported; supported: {SCHEMA}")
        self.found = found


def locate(host: Path, capability: str, node: str | None = None) -> homes.Home | None:
    """Where the capability's registry is now: its home (any node), else the old layout; when it
    has none, the home it would have for `node` (None without a node)."""
    registered = [h for h in homes.homes(host) if h.capability == capability]
    registered = [h for h in registered if (host / h.registry).is_file()]
    # another node's home for the same capability comes first: it is the conflict to report
    registered.sort(key=lambda h: h.node == node)
    if registered:
        return registered[0]
    found = homes.find(host, capability)
    legacy = homes.old(capability)
    if (host / legacy.registry).is_file():
        return legacy
    if found is not None:
        return found
    return homes.new(node, capability) if node else None


def path(host: Path, capability: str) -> Path:
    where = locate(host, capability) or homes.old(capability)
    return host / where.registry


def relative(capability: str, host: Path | None = None) -> str:
    where = locate(host, capability) if host is not None else None
    return (where or homes.old(capability)).registry


def _key(loc: dict) -> tuple[str, str]:
    return (str(loc.get("path", "")), str(loc.get("address") or ""))


def parse(data: bytes) -> dict:
    try:
        reg = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise UnreadableRegistry(f"not readable as JSON: {exc}") from exc
    if not isinstance(reg, dict):
        raise UnreadableRegistry("the registry is not a JSON object")
    schema = reg.get("schema")
    if isinstance(schema, str) and schema.startswith("kaelen.registry/") and schema != SCHEMA:
        raise UnsupportedRegistry(schema)
    for field, kind in _REQUIRED.items():
        value = reg.get(field)
        if not isinstance(value, kind) or isinstance(value, bool):
            raise UnreadableRegistry(f"field {field!r} is missing or not a {kind.__name__}")
    if reg["schema"] != SCHEMA:
        raise UnreadableRegistry(f"schema {reg['schema']!r} is not a Kaelen registry")
    if not all(
        isinstance(loc, dict) and isinstance(loc.get("path"), str) for loc in reg["locations"]
    ):
        raise UnreadableRegistry("a location has no path")
    return reg


def load(host: Path, capability: str) -> dict | None:
    where = locate(host, capability)
    return None if where is None else load_at(host, where)


def load_at(host: Path, where: homes.Home) -> dict | None:
    file = host / where.registry
    if not file.exists():
        return None
    try:
        data = file.read_bytes()
    except OSError as exc:
        raise UnreadableRegistry(str(exc)) from exc
    return parse(data)


def serialise(reg: dict) -> bytes:
    out = {k: reg[k] for k in ORDER if k in reg}
    out.update({k: v for k, v in reg.items() if k not in out})
    out["locations"] = sorted(reg.get("locations", []), key=_key)
    return (json.dumps(out, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def keep_unknown(new: dict, old: dict | None) -> dict:
    """`new` with every field of `old` this engine does not write carried over (FR-044)."""
    if not old:
        return new
    merged = dict(new)
    for k, v in old.items():
        if k not in OWNED and k not in merged:
            merged[k] = v
    old_locs = {_key(loc): loc for loc in old.get("locations", []) if isinstance(loc, dict)}
    locs = []
    for loc in new.get("locations", []):
        before = old_locs.get(_key(loc), {})
        locs.append({**{k: v for k, v in before.items() if k not in loc}, **loc})
    merged["locations"] = locs
    return merged


def write(host: Path, reg: dict) -> None:
    """Replace the capability's registry file whole, in its home (FR-042)."""
    file = host / homes.new(reg["node"], reg["capability"]).registry
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_name(file.name + ".tmp")
    tmp.write_bytes(serialise(reg))
    os.replace(tmp, file)


def everything(host: Path) -> list[tuple[homes.Home, dict | Exception]]:
    """Every registry on the host, in both layouts, each with its home (or why it cannot be read).

    A capability with a registry in its home is not read again from the old layout.
    """
    out: list[tuple[homes.Home, dict | Exception]] = []
    seen = set()
    for where in homes.homes(host):
        if not (host / where.registry).is_file():
            continue
        seen.add(where.capability)
        out.append((where, _read(host, where)))
    folder = host / homes.OLD_REGISTRY
    if folder.is_dir():
        for file in sorted(folder.glob("*.json")):
            if file.stem not in seen:
                where = homes.old(file.stem)
                out.append((where, _read(host, where)))
    return out


def _read(host: Path, where: homes.Home) -> dict | Exception:
    try:
        return parse((host / where.registry).read_bytes())
    except (UnreadableRegistry, UnsupportedRegistry, OSError) as exc:
        return exc


def read_others(host: Path, capability: str) -> tuple[list[dict], list[str], list[tuple[str, str]]]:
    """Other capabilities' registries, read only to detect claims, in both layouts (FR-022).

    Returns (registries, unreadable capabilities, [(capability, schema)] of unknown schemas).
    """
    others, unreadable, unsupported = [], [], []
    for where, reg in everything(host):
        if where.capability == capability:
            continue
        if isinstance(reg, UnsupportedRegistry):
            unsupported.append((where.capability, str(reg.found)))
        elif isinstance(reg, Exception):
            unreadable.append(where.capability)
        else:
            others.append(reg)
    return others, unreadable, unsupported
