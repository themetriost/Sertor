"""Where a capability's state lives on a host (specs/026 research R-1, R-5).

The new layout: everything of one capability under its home `.<node>/kaelen/<capability>/`, and in
`.kaelen/` only the host's main Kaelen. The old layout (engines up to 0.11.0) kept the state of
every capability in shared folders under `.kaelen/`: it is read, and never written once a
capability has moved.
No other module spells a path of either layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

KAELEN = "kaelen"
MAIN = ".kaelen/engine"
PACKAGE = "package"
REGISTRY = "registry.json"
RECORD = "operation.json"
COPIES = "operation.pre"
RUNTIME = "runtime"
STAGING = "runtime.build"
LAUNCHER = "launch.py"
HOOKS = "hooks"
IGNORE = ".gitignore"
ENGINE = "engine"
# Names the engine uses inside a home: no hook or support file may land on them (FR-007).
RESERVED = (PACKAGE, REGISTRY, RECORD, COPIES, RUNTIME, STAGING, LAUNCHER, IGNORE, ENGINE)
IGNORED = (RECORD, COPIES + "/", RUNTIME + "/", STAGING + "/")
# anchored to the home: unanchored, `runtime/` also hid the package's own `content/runtime/`
# (specs/033 R-1); the old bytes are rewritten at the next writing operation
IGNORE_BYTES = "".join("/" + line + "\n" for line in IGNORED).encode("ascii")
OLD_IGNORE_BYTES = "".join(line + "\n" for line in IGNORED).encode("ascii")

# The main Kaelen's part of an operation on shared files, one per capability (specs/027 R-4)
CONTRIBUTIONS = ".kaelen/contributions"
# The host's trusted signers, changed only by the operator (specs/028 R-12)
TRUST = ".kaelen/trust"

OLD_REGISTRY = ".kaelen/registry"
OLD_OPERATIONS = ".kaelen/operations"
OLD_RUNTIMES = ".kaelen/runtimes"
OLD_CAPABILITIES = ".kaelen/capabilities"


@dataclass(frozen=True)
class Home:
    """The paths of one capability's state, relative to the host, in one layout."""

    capability: str
    node: str | None  # None for the old layout, which does not name the node
    root: str | None  # the home folder; None for the old layout

    @property
    def legacy(self) -> bool:
        return self.root is None

    @property
    def registry(self) -> str:
        return (
            f"{OLD_REGISTRY}/{self.capability}.json" if self.legacy else f"{self.root}/{REGISTRY}"
        )

    @property
    def record(self) -> str:
        return (
            f"{OLD_OPERATIONS}/{self.capability}.json" if self.legacy else f"{self.root}/{RECORD}"
        )

    @property
    def copies(self) -> str:
        return f"{OLD_OPERATIONS}/{self.capability}.pre" if self.legacy else f"{self.root}/{COPIES}"

    @property
    def staging(self) -> str:
        return (
            f"{OLD_OPERATIONS}/{self.capability}.build" if self.legacy else f"{self.root}/{STAGING}"
        )

    @property
    def runtime(self) -> str:
        return f"{OLD_RUNTIMES}/{self.capability}" if self.legacy else f"{self.root}/{RUNTIME}"

    @property
    def launcher(self) -> str:
        if self.legacy:
            return f"{OLD_CAPABILITIES}/{self.capability}/{LAUNCHER}"
        return f"{self.root}/{LAUNCHER}"

    @property
    def package(self) -> str | None:
        return None if self.legacy else f"{self.root}/{PACKAGE}"

    @property
    def ignore(self) -> str | None:
        return None if self.legacy else f"{self.root}/{IGNORE}"

    def old_paths(self) -> list[str]:
        """The old-layout paths that may hold something of this capability (FR-028)."""
        c = self.capability
        return [
            f"{OLD_REGISTRY}/{c}.json",
            f"{OLD_OPERATIONS}/{c}.json",
            f"{OLD_OPERATIONS}/{c}.pre",
            f"{OLD_RUNTIMES}/{c}",
            f"{OLD_CAPABILITIES}/{c}",
        ]


def new(node: str, capability: str) -> Home:
    return Home(capability, node, f".{node}/{KAELEN}/{capability}")


def old(capability: str) -> Home:
    return Home(capability, None, None)


def from_record(op: dict) -> Home:
    """The home an operation record was written for: a record without one is an old engine's."""
    root = op.get("home")
    if not root:
        return old(op["capability"])
    node = root.split("/")[0][1:]
    return Home(op["capability"], node, root)


def homes(host: Path) -> list[Home]:
    """Every new-layout home: `.<node>/kaelen/<capability>/` holding a registry or a record."""
    out = []
    try:
        tops = sorted(p for p in host.iterdir() if p.name.startswith(".") and p.is_dir())
    except OSError:
        return out
    for top in tops:
        base = top / KAELEN
        if not base.is_dir():
            continue
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            if (folder / REGISTRY).is_file() or (folder / RECORD).is_file():
                out.append(Home(folder.name, top.name[1:], f"{top.name}/{KAELEN}/{folder.name}"))
    return out


def find(host: Path, capability: str) -> Home | None:
    """The new-layout home of `capability`, whatever its node; None when it has none."""
    return next((h for h in homes(host) if h.capability == capability), None)


def old_capabilities(host: Path) -> list[str]:
    """Capabilities with a registry or an operation record in the old layout."""
    names = set()
    for rel in (OLD_REGISTRY, OLD_OPERATIONS):
        folder = host / rel
        if folder.is_dir():
            names.update(p.stem for p in folder.glob("*.json"))
    return sorted(names)


def is_runtime(rel: str) -> bool:
    """A runtime environment's location, in either layout (specs/022 R-6)."""
    parts = rel.split("/")
    if rel.startswith(OLD_RUNTIMES + "/"):
        return len(parts) == 3 and parts[2] != IGNORE
    return (
        len(parts) == 4 and parts[0].startswith(".") and parts[1] == KAELEN and parts[3] == RUNTIME
    )


def deposit_of(package_root: Path) -> Path | None:
    """The host above a deposited package, `<host>/.<node>/kaelen/<capability>/package`, if any."""
    root = package_root.resolve()
    if root.name != PACKAGE or len(root.parents) < 4:
        return None
    if root.parents[1].name != KAELEN or not root.parents[2].name.startswith("."):
        return None
    return root.parents[3]


def main_version(host: Path) -> str | None:
    """The version of the host's main Kaelen, from its distribution metadata; None when absent."""
    engine = host / MAIN / "engine"
    if not engine.is_dir():
        return None
    for meta in sorted(engine.glob("kaelen-*.dist-info/METADATA")):
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    return "unknown"
