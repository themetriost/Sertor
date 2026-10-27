"""The capability's runtime environment (specs/022-capability-runtime).

Everything about environments lives here: the recipe a declaration describes and its digest, the
interpreter versions, the lock file, the builder that drives uv or venv + pip (substitutable, so
tests never build a real environment: Constitution VI), the launcher written into the host, and
the inspection verify relies on. Nothing here edits the host's shared files.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from kaelen.host import home as homes

OLD_IGNORE = f"{homes.OLD_RUNTIMES}/.gitignore"
STAMP = "kaelen-runtime.json"
STAMP_SCHEMA = "kaelen.runtime/1"
LANGUAGES = ("python",)
SEEDS = frozenset({"pip", "setuptools", "wheel"})  # what a tool puts in a fresh environment


def runtime_rel(node: str, capability: str) -> str:
    """The environment's place, in the capability's home (specs/026 R-11)."""
    return homes.new(node, capability).runtime


def launcher_rel(node: str, capability: str) -> str:
    return homes.new(node, capability).launcher


def is_runtime_location(rel: str) -> bool:
    return homes.is_runtime(rel)


# --- interpreter versions (research R-7) --------------------------------------------------------

_SPEC = re.compile(r"^\s*(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+)*)\s*$")


def parse_specifier(text: str) -> list[tuple[str, tuple[int, ...]]]:
    parts = []
    for piece in text.split(","):
        match = _SPEC.match(piece)
        if not match:
            raise ValueError(f"{piece.strip()!r} is not a version specifier")
        parts.append((match.group(1), tuple(int(n) for n in match.group(2).split("."))))
    return parts


def satisfies(text: str, version: tuple[int, ...]) -> bool:
    for op, wanted in parse_specifier(text):
        have = tuple(version[: len(wanted)])
        ok = {
            ">=": have >= wanted,
            ">": have > wanted,
            "<=": have <= wanted,
            "<": have < wanted,
            "==": have == wanted,
            "!=": have != wanted,
        }[op]
        if not ok:
            return False
    return True


def interpreter_version() -> tuple[int, ...]:
    return tuple(sys.version_info[:3])


# --- the lock file (research R-2) ---------------------------------------------------------------

_REQ = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?==([^\s;\\]+)\s*"
    r"(;[^\\]*?)?\s*((?:--hash[= ]\S+\s*)*)$"
)
_HASH = re.compile(r"^--hash[= ]sha256:[0-9a-f]{64}$")


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass
class Locked:
    name: str  # normalised
    version: str
    marker: bool  # carries an environment marker: may not apply on this machine


def parse_lock(text: str) -> tuple[list[Locked], list[tuple[str, str]]]:
    """(requirements, problems as (rule, message)); every requirement pinned and hashed."""
    logical, current = [], ""
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if line.endswith("\\"):
            current += line[:-1] + " "
            continue
        current += line
        if current.strip():
            logical.append(current.strip())
        current = ""
    if current.strip():
        logical.append(current.strip())
    found, problems = [], []
    for line in logical:
        if line.startswith("-"):
            problems.append(
                (
                    "runtime-lock-option",
                    f"{line.split()[0]}: only pinned, hashed requirements are allowed",
                )
            )
            continue
        match = _REQ.match(line)
        if not match:
            name = re.split(r"[\s=<>!~;\[]", line, maxsplit=1)[0]
            rule = (
                "runtime-lock-unpinned"
                if "://" not in line and "@" not in line
                else "runtime-lock-option"
            )
            problems.append(
                (rule, f"{name}: not pinned to one version with ==, or not a plain requirement")
            )
            continue
        tokens = re.findall(r"--hash[= ]\S+", match.group(5) or "")
        if not tokens or not all(_HASH.match(t) for t in tokens):
            problems.append(
                (
                    "runtime-lock-unhashed",
                    f"{match.group(1)}=={match.group(3)}: needs --hash=sha256:<64 hex>",
                )
            )
            continue
        found.append(Locked(normalise(match.group(1)), match.group(3), bool(match.group(4))))
    if not found and not problems:
        problems.append(("runtime-lock-empty", "the lock file holds no requirement"))
    return found, problems


# --- the recipe ---------------------------------------------------------------------------------


def _sha(data: bytes) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(data).hexdigest()


def recipe(document: dict, read_file, read_tree) -> dict:
    """The recipe of the capability's environment, from the package (lock, code, entry points)."""
    spec = document["runtime"]
    code = read_tree(spec["code"]) if spec.get("code") else []
    return {
        "capability": document["capability"],
        "language": spec["language"],
        "python": spec["python"],
        "lock": read_file(spec["lock"]),
        "code": code,
        "entry_points": {
            name: {"module": e["module"], "args": list(e.get("args", []))}
            for name, e in sorted(spec["entry_points"].items())
        },
    }


def recipe_digest(r: dict) -> str:
    canon = {
        "language": r["language"],
        "python": r["python"],
        "lock": _sha(r["lock"]),
        "code": [[rel, _sha(data)] for rel, data in sorted(r["code"])],
        "entry_points": r["entry_points"],
    }
    return _sha(json.dumps(canon, sort_keys=True).encode("utf-8"))


def stamp_bytes(capability: str, recipe_sha: str, tool: str, python: str) -> bytes:
    doc = {
        "schema": STAMP_SCHEMA,
        "capability": capability,
        "recipe": recipe_sha,
        "tool": tool,
        "python": python,
    }
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_stamp(directory: Path) -> dict | None:
    try:
        return json.loads((directory / STAMP).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# --- commands the items carry (research R-4) ----------------------------------------------------


def mcp_definition(data: bytes, node: str, capability: str, entry: str) -> bytes:
    """The MCP definition with its command written by the engine: the same text on every OS."""
    value = json.loads(data.decode("utf-8"))
    extra = list(value.get("args", [])) if isinstance(value.get("args"), list) else []
    value["command"] = "python"
    value["args"] = [launcher_rel(node, capability), entry, *extra]
    return json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")


LAUNCHER = '''"""Written by Kaelen for capability {capability!r}.

Runs an entry point, or a script, in the capability's environment, the folder runtime/
beside this file (specs/022, specs/026). Do not edit: the engine records this file.
"""

import subprocess
import sys
from pathlib import Path

CAPABILITY = {capability!r}
ENTRY_POINTS = {entry_points}
HOME = Path(__file__).resolve().parent / "runtime"


def interpreter():
    for rel in ("env/Scripts/python.exe", "env/bin/python"):
        candidate = HOME / rel
        if candidate.is_file():
            return candidate
    return None


def main(argv):
    python = interpreter()
    if python is None or not (HOME / "kaelen-runtime.json").is_file():
        sys.stderr.write(
            "kaelen: the environment of " + CAPABILITY + " is not built on this machine; "
            "run the package's install on this repository to build it "
            "(kaelen install --host <repository> --target <assistant>)\\n"
        )
        return 1
    if len(argv) >= 2 and argv[0] == "--script":
        command = [str(python), argv[1], *argv[2:]]
    elif argv and argv[0] in ENTRY_POINTS:
        entry = ENTRY_POINTS[argv[0]]
        command = [str(python), "-m", entry["module"], *entry["args"], *argv[1:]]
    else:
        known = ", ".join(sorted(ENTRY_POINTS))
        sys.stderr.write("kaelen: unknown entry point; known: " + known + "\\n")
        return 64
    return subprocess.call(command)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


def launcher_bytes(capability: str, entry_points: dict) -> bytes:
    text = LAUNCHER.format(
        capability=capability, entry_points=json.dumps(entry_points, sort_keys=True)
    )
    return text.encode("utf-8")


# --- inspection (research R-8) ------------------------------------------------------------------


def site_packages(env: Path) -> Path | None:
    win = env / "Lib" / "site-packages"
    if win.is_dir():
        return win
    found = sorted((env / "lib").glob("python*/site-packages")) if (env / "lib").is_dir() else []
    return found[0] if found else None


def installed(env: Path) -> dict[str, str]:
    """{normalised name: version} of the distributions installed in `env`."""
    site = site_packages(env)
    out: dict[str, str] = {}
    if site is None:
        return out
    for meta in sorted(site.glob("*.dist-info/METADATA")):
        name = version = None
        for line in meta.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                break
            if line.startswith("Name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("Version:"):
                version = line.split(":", 1)[1].strip()
        if name and version:
            out[normalise(name)] = version
    return out


def inspect(home: Path, lock: bytes) -> dict:
    """matching | divergent (with differences) | absent: the environment against its lock."""
    if not (home / STAMP).is_file() or site_packages(home / "env") is None:
        return {"state": "absent", "differences": []}
    locked, _ = parse_lock(lock.decode("utf-8"))
    have = installed(home / "env")
    differences = []
    for req in locked:
        found = have.get(req.name)
        if found is None:
            if not req.marker:
                differences.append({"name": req.name, "expected": req.version, "found": None})
        elif found != req.version:
            differences.append({"name": req.name, "expected": req.version, "found": found})
    wanted = {req.name for req in locked}
    for name in sorted(set(have) - wanted - SEEDS):
        differences.append({"name": name, "expected": None, "found": have[name]})
    return {"state": "divergent" if differences else "matching", "differences": differences}


# --- the builder (research R-5) -----------------------------------------------------------------


class BuildFailed(Exception):
    """The tool could not build the environment; the message is the tool's own."""


class RuntimeBuilder:
    """Builds an environment into a fresh directory; production drives uv or venv + pip."""

    def tool(self) -> str:
        raise NotImplementedError

    def build(self, home: Path, lock: bytes, code: list[tuple[str, bytes]], stamp: bytes) -> None:
        raise NotImplementedError


def finish_home(home: Path, code: list[tuple[str, bytes]], stamp: bytes) -> None:
    """Own code, its path file, and the stamp last: the common end of every builder."""
    for rel, data in code:
        target = home / "code" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    site = site_packages(home / "env")
    if code and site is not None:
        relative = os.path.relpath(home / "code", site)
        (site / "kaelen-code.pth").write_text(relative + "\n", encoding="utf-8")
    (home / STAMP).write_bytes(stamp)


class ToolBuilder(RuntimeBuilder):
    """uv when it is on the host, otherwise the standard library's venv and pip (D-1)."""

    def __init__(self, which=shutil.which, run=subprocess.run, python: str | None = None):
        self._which = which
        self._run = run
        self._python = python or sys.executable

    def tool(self) -> str:
        return "uv" if self._which("uv") else "pip"

    def _call(self, args: list[str]) -> None:
        done = self._run(args, capture_output=True, text=True)
        if done.returncode != 0:
            message = (done.stderr or done.stdout or "").strip().splitlines()
            raise BuildFailed(
                f"{Path(args[0]).name} failed: "
                + (message[-1] if message else f"exit {done.returncode}")
            )

    def build(self, home: Path, lock: bytes, code: list[tuple[str, bytes]], stamp: bytes) -> None:
        home.mkdir(parents=True, exist_ok=True)
        lock_file = home / "requirements.lock"
        lock_file.write_bytes(lock)
        env = home / "env"
        uv = self._which("uv")
        if uv:
            self._call(
                [uv, "venv", "--python", self._python, "--no-python-downloads", "--quiet", str(env)]
            )
            python = _env_python(env)
            self._call(
                [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    str(python),
                    "--require-hashes",
                    "--no-deps",
                    "--quiet",
                    "-r",
                    str(lock_file),
                ]
            )
        else:
            self._call([self._python, "-m", "venv", str(env)])
            python = _env_python(env)
            self._call(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--require-hashes",
                    "--no-deps",
                    "--disable-pip-version-check",
                    "--quiet",
                    "-r",
                    str(lock_file),
                ]
            )
        lock_file.unlink()
        finish_home(home, code, stamp)


def _env_python(env: Path) -> Path:
    for rel in ("Scripts/python.exe", "bin/python"):
        if (env / rel).is_file():
            return env / rel
    raise BuildFailed(f"no interpreter found in the new environment {env.as_posix()}")


def python_label() -> str:
    return platform.python_version()
