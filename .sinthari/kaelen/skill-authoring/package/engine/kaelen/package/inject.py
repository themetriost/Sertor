"""Engine injection: a source copy of the running engine, stamped with its version (R-1, R-2)."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

LAUNCHER = "launcher.py.txt"


class InjectionError(Exception):
    """The engine cannot be copied into a package: packaging must fail (FR-010)."""


def engine_files(version: str) -> list[tuple[str, bytes]]:
    """Every file the injected engine consists of, as (package-relative path, bytes), sorted."""
    if not version or version == "unknown":
        raise InjectionError("the running engine does not know its own version")
    root = Path(str(resources.files("kaelen")))
    if not root.is_dir():
        raise InjectionError(f"the running engine is not a directory on disk: {root}")
    files = []
    try:
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root).as_posix()
            if not path.is_file() or "__pycache__" in rel.split("/") or rel.endswith(".pyc"):
                continue
            files.append((f"engine/kaelen/{rel}", path.read_bytes()))
        launcher = root.joinpath("package", LAUNCHER).read_bytes()
    except OSError as exc:
        raise InjectionError(f"cannot read the running engine: {exc}") from exc
    metadata = f"Metadata-Version: 2.1\nName: kaelen\nVersion: {version}\n".encode()
    files.append((f"engine/kaelen-{version}.dist-info/METADATA", metadata))
    files.append(("run.py", launcher))
    return sorted(files)


def inject_engine(dest: Path, version: str) -> list[tuple[str, bytes]]:
    """Write the engine, its dist-info and the launcher under `dest`; return what was written."""
    files = engine_files(version)
    try:
        for rel, data in files:
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    except OSError as exc:
        raise InjectionError(f"cannot write the injected engine: {exc}") from exc
    return files
