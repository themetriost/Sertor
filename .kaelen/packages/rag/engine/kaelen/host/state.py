"""What a location holds on the host now: absent, or present with a digest (specs/017 R-8).

The one place that reads host locations, for reconcile and verify alike.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from kaelen.host import jsonspan, sections
from kaelen.host.desired import content_digest, sha
from kaelen.host.jsonspan import Unmergeable
from kaelen.host.runtime import read_stamp
from kaelen.host.sections import HASH, MARKDOWN
from kaelen.package.record import digest_tree

STYLES = {"markdown": MARKDOWN, "hash": HASH}


def read_text(host: Path, rel: str) -> str | None:
    path = host / rel
    if not path.is_file():
        return None
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Unmergeable(f"{rel} is not UTF-8 text") from exc


def read_tree(path: Path) -> list[tuple[str, bytes]]:
    files = []
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            files.append((full.relative_to(path).as_posix(), full.read_bytes()))
    return sorted(files)


def element_identity(address: str) -> str:
    return address[address.index("[") + 1 : -1]


def observe(host: Path, loc: dict) -> str | None:
    """The digest of what `loc` holds on the host, or None when it is absent."""
    rel = loc["path"]
    path = host / rel
    style = loc.get("style")
    if loc.get("form") == "runtime":  # the recipe the built environment was made from (specs/022)
        stamp = read_stamp(path)
        return stamp.get("recipe") if isinstance(stamp, dict) else None
    if loc["ownership"] == "owned" or style is None:
        if loc.get("form") == "directory":
            if path.is_dir():
                return digest_tree(read_tree(path))
            return sha(path.read_bytes()) if path.is_file() else None
        if path.is_file():
            return sha(path.read_bytes())
        return digest_tree(read_tree(path)) if path.is_dir() else None
    text = read_text(host, rel)
    if text is None:
        return None
    if style in STYLES:
        body = sections.body(text, loc["address"], STYLES[style])
        return None if body is None else content_digest("file", style, body)
    if style == "json-member":
        value = jsonspan.value_text(text, [*loc["json_path"], loc["json_key"]])
        return None if value is None else jsonspan.canonical_digest(json.loads(value))
    identity = element_identity(loc["address"])
    return identity if jsonspan.find_element(text, loc["json_path"], identity) else None


def folder_files(host: Path, reg: dict, loc: dict) -> list[dict] | None:
    """Each file of a folder location that differs from what was installed (specs/032 R-4).

    What was installed is the item rendered from the package copy deposited in the capability's
    home: the installed version by construction. None when that cannot be known (no copy, another
    version, a rendering whose digest is not the recorded one, the old layout).
    """
    from kaelen.host import home as homes
    from kaelen.host.desired import desired
    from kaelen.host.source import PackageError, open_package

    place = homes.find(host, reg.get("capability", ""))
    if place is None or place.package is None:
        return None
    try:
        pkg = open_package(host / place.package)
    except (PackageError, OSError, ValueError):
        return None
    if pkg.document.get("version") != reg.get("version"):
        return None
    try:
        placements, _, _ = desired(pkg, list(reg.get("targets", [])))
    except Exception:  # a copy this engine cannot render is a copy it cannot compare with
        return None
    placement = next(
        (p for p in placements if p.path == loc["path"] and p.form == "directory"), None
    )
    if placement is None or placement.digest != loc.get("digest"):
        return None
    installed = dict(placement.content)
    path = host / loc["path"]
    found = dict(read_tree(path)) if path.is_dir() else {}
    files = [
        {"path": rel, "state": "removed" if rel not in found else "modified"}
        for rel, data in installed.items()
        if found.get(rel) != data
    ]
    files += [{"path": rel, "state": "added"} for rel in found if rel not in installed]
    if path.is_file():
        files.append({"path": ".", "state": "added"})
    return sorted(files, key=lambda f: f["path"])
