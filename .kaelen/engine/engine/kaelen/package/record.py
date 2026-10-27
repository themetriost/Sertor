"""The package record `kaelen-package.json` (specs/015-packaging-injection/contracts/package.md).

One definition of the format: built, serialised and parsed here only.
"""

from __future__ import annotations

import hashlib
import json

SCHEMA = "kaelen.package-record/2"
# Records this engine recognises as its own: /1 is spec 015 (engine 0.2), /2 adds placements.
KNOWN_SCHEMAS = ("kaelen.package-record/1", SCHEMA)
FILENAME = "kaelen-package.json"
SIGNATURE = FILENAME + ".sig"  # beside the record, not listed in it (specs/028)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_tree(files: list[tuple[str, bytes]]) -> str:
    """Identity of a set of files: their sorted (path, sha256) pairs (research R-3)."""
    lines = "".join(f"{path} {sha256(data)}\n" for path, data in sorted(files))
    return "sha256:" + sha256(lines.encode("utf-8"))


def producer_state(declaration: bytes, content: list[tuple[str, bytes]]) -> str:
    """Digest of the inputs, never a commit (research R-4)."""
    return digest_tree([("declaration", declaration), *content])


def build_record(
    *,
    document: dict,
    engine_version: str,
    engine_digest: str,
    rule_digest: str,
    producer_state: str,
    targets: list[dict],
    files: list[dict],
) -> dict:
    return {
        "schema": SCHEMA,
        "node": document["node"],
        "capability": document["capability"],
        "version": document["version"],
        "contract": document["contract"],
        "engine": {"version": engine_version, "digest": engine_digest},
        "placement_rule": {"digest": rule_digest},
        "producer_state": producer_state,
        "targets": targets,
        "files": sorted(files, key=lambda f: f["path"]),
    }


def serialise(record: dict) -> bytes:
    return (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def parse(data: bytes) -> dict | None:
    """The record, or None when `data` is not a record of this format."""
    try:
        record = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(record, dict) or record.get("schema") not in KNOWN_SCHEMAS:
        return None
    return record
