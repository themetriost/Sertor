"""The package a host verb installs from: found, checked, and read (specs/017 research R-1, R-2).

Nothing is read from a package before its record matches its files and its declaration is
valid against its own content: the bytes validated at packaging are the bytes installed.
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
from dataclasses import dataclass
from pathlib import Path

from kaelen.outcome import VALID
from kaelen.package import record as package_record
from kaelen.validate import validate_document

DECLARATION = "declaration.toml"
CONTENT = "content"
ENGINE = "engine"
LAUNCHER = "run.py"


class PackageError(Exception):
    """The package cannot be trusted or read: unable to check (FR-005)."""

    rule = "package-unreadable"


class UnsupportedPackageRecord(PackageError):
    """A package record of a schema this engine does not know (specs/026 FR-024)."""

    rule = "package-record-unsupported"


@dataclass
class Package:
    root: Path
    record: dict
    document: dict
    raw: bytes

    def source(self, item: dict) -> Path:
        return self.root / CONTENT / posixpath.normpath(item["source"])

    def content(self, item: dict):
        """The item's bytes, or for a directory its sorted [(relative path, bytes)].

        An `engine` item has no source: its content is the engine this package carries, its
        `engine/` tree and its `run.py`, exactly as injected (specs/018 FR-008, research R-1).
        A `git-lines` item has none either: its content is its lines (specs/025 R-4).
        """
        if item["kind"] == "engine":
            return self.engine()
        if item["kind"] == "git-lines":
            return "".join(line + "\n" for line in item["lines"]).encode("utf-8")
        path = self.source(item)
        if path.is_dir():
            files = []
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames.sort()
                for name in sorted(filenames):
                    full = Path(dirpath) / name
                    files.append((full.relative_to(path).as_posix(), full.read_bytes()))
            return sorted(files)
        return path.read_bytes()

    def files(self) -> list[tuple[str, bytes]]:
        """The package as deposited in the capability's home: every file its record lists, and the
        record itself (specs/026 R-3)."""
        files = [(package_record.FILENAME, (self.root / package_record.FILENAME).read_bytes())]
        signature = self.root / package_record.SIGNATURE
        if signature.is_file():  # the deposit keeps it, so verify can check it again (specs/028)
            files.append((package_record.SIGNATURE, signature.read_bytes()))
        for entry in self.record.get("files", []):
            files.append((entry["path"], (self.root / entry["path"]).read_bytes()))
        return sorted(files)

    def engine(self) -> list[tuple[str, bytes]]:
        files = [(LAUNCHER, (self.root / LAUNCHER).read_bytes())]
        for path in sorted((self.root / ENGINE).rglob("*")):
            if path.is_file():
                files.append((path.relative_to(self.root).as_posix(), path.read_bytes()))
        return sorted(files)


def carrying_package(engine_dir: Path) -> Path | None:
    """The package whose `engine/kaelen/` is `engine_dir`, if the running engine is carried."""
    root = engine_dir.parent.parent
    if engine_dir.parent.name == "engine" and (root / package_record.FILENAME).is_file():
        return root
    return None


def open_package(root: Path) -> Package:
    if not root.is_dir():
        raise PackageError(f"package {root.as_posix()!r} is not a directory")
    record_file = root / package_record.FILENAME
    try:
        rec = package_record.parse(record_file.read_bytes())
    except OSError as exc:
        raise PackageError(f"cannot read the package record: {exc}") from exc
    if rec is None:
        schema = _schema(record_file)
        if isinstance(schema, str) and schema.startswith("kaelen.package-record/"):
            raise UnsupportedPackageRecord(
                f"{package_record.FILENAME} has schema {schema!r}, which this engine does not "
                "know; "
                f"supported: {', '.join(package_record.KNOWN_SCHEMAS)}"
            )
        raise PackageError(f"{package_record.FILENAME} is not a Kaelen package record")
    listed = {}
    if any(e.get("path") == package_record.SIGNATURE for e in rec.get("files", [])):
        raise PackageError(f"{package_record.SIGNATURE} must not be listed in the record it signs")
    missing, differing = [], []  # every one, so the cause shows (specs/033 FR-004)
    for entry in rec.get("files", []):
        listed[entry["path"]] = entry
        path = root / entry["path"]
        if not path.is_file():
            missing.append(entry["path"])
            continue
        data = path.read_bytes()
        if len(data) != entry["size"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            differing.append(entry["path"])
    if missing:
        raise PackageError(f"listed in the record but missing: {', '.join(missing)}")
    if differing:
        raise PackageError(f"differ from the package record: {', '.join(differing)}")
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if "__pycache__" in rel.split("/"):
            continue  # what Python leaves beside a deposited engine it ran is not the package's
        unlisted = (package_record.FILENAME, package_record.SIGNATURE)
        if path.is_file() and rel not in unlisted and rel not in listed:
            raise PackageError(f"{rel} is in the package but not in its record")
    outcome, document, raw = validate_document(root / DECLARATION, root / CONTENT)
    if outcome.verdict != VALID:
        first = outcome.errors[0].message if outcome.errors else outcome.reason
        raise PackageError(f"the carried declaration is not valid: {first}")
    if (root / package_record.SIGNATURE).is_file() and not document.get("signer"):
        raise PackageError(
            f"{package_record.SIGNATURE} is present but the declaration names no signer"
        )
    return Package(root, rec, document, raw)


def _schema(record_file: Path):
    try:
        value = json.loads(record_file.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return value.get("schema") if isinstance(value, dict) else None
