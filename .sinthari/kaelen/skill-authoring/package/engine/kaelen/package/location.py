"""The package location `.kaelen/packages/<capability>/`: ownership and atomic swap (R-7, R-8).

Packaging writes nowhere else. The siblings `.<capability>.staging` and
`.<capability>.previous` are owned by name.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from kaelen.package import record

AREA = (".kaelen", "packages")

ABSENT = "absent"
OURS = "ours"
FOREIGN = "foreign"
INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class State:
    state: str
    detail: str = ""


def area(producer: Path) -> Path:
    return producer.joinpath(*AREA)


def final_dir(producer: Path, capability: str) -> Path:
    return area(producer) / capability


def staging_dir(producer: Path, capability: str) -> Path:
    return area(producer) / f".{capability}.staging"


def previous_dir(producer: Path, capability: str) -> Path:
    return area(producer) / f".{capability}.previous"


def relative(capability: str) -> str:
    """The location as reported: producer-relative, POSIX."""
    return "/".join((*AREA, capability))


def inspect(producer: Path, capability: str) -> State:
    final = final_dir(producer, capability)
    if not final.exists():
        if previous_dir(producer, capability).is_dir():
            return State(INTERRUPTED, "a previous package was left aside by an interrupted run")
        return State(ABSENT)
    if not final.is_dir():
        return State(FOREIGN, f"{relative(capability)} is not a directory")
    present = sorted(p.relative_to(final).as_posix() for p in final.rglob("*") if p.is_file())
    rec_path = final / record.FILENAME
    rec = record.parse(rec_path.read_bytes()) if rec_path.is_file() else None
    if rec is None:
        first = present[0] if present else "(empty directory)"
        return State(FOREIGN, f"no package record; first file: {first}")
    listed = {f.get("path") for f in rec.get("files", []) if isinstance(f, dict)}
    for rel in present:
        if rel not in (record.FILENAME, record.SIGNATURE) and rel not in listed:
            return State(FOREIGN, f"{rel} is not listed in the package record")
    return State(OURS)


def recover(producer: Path, capability: str) -> None:
    """Undo what an earlier run left: drop staging, restore or drop `.previous`."""
    staging = staging_dir(producer, capability)
    if staging.exists():
        shutil.rmtree(staging)
    previous = previous_dir(producer, capability)
    if previous.exists():
        final = final_dir(producer, capability)
        if final.exists():
            shutil.rmtree(previous)
        else:
            previous.rename(final)


def discard_staging(producer: Path, capability: str) -> None:
    staging = staging_dir(producer, capability)
    if staging.exists():
        shutil.rmtree(staging)


def swap(producer: Path, capability: str) -> None:
    """Replace the package with the staged one: renames inside the package area only."""
    final = final_dir(producer, capability)
    previous = previous_dir(producer, capability)
    if final.exists():
        final.rename(previous)
    staging_dir(producer, capability).rename(final)
    if previous.exists():
        shutil.rmtree(previous)
