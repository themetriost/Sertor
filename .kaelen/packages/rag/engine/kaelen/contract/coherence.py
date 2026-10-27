"""Coherence rules the schema cannot express — their one and only definition.

They run only on a declaration that already satisfies its schema, so the shape of every
field is guaranteed here.
"""

from __future__ import annotations

import posixpath
import re

from kaelen.outcome import Problem

_DRIVE = re.compile(r"^[A-Za-z]:")


def check(declaration: dict) -> list[Problem]:
    problems: list[Problem] = []
    declared_targets = set(declaration["targets"])
    seen: dict[tuple[str, str], int] = {}
    engine: int | None = None

    for i, path in enumerate(declaration.get("governs", ())):
        problem = _path_problem(path, f"governs[{i}]", "governed area")
        if problem:
            problems.append(problem)

    for i, item in enumerate(declaration["items"]):
        key = (item["kind"], item["name"])
        if key in seen:
            problems.append(
                Problem(
                    "duplicate-name",
                    f"items[{i}].name",
                    f"items[{seen[key]}] and items[{i}] are both {item['kind']} {item['name']!r}",
                )
            )
        else:
            seen[key] = i

        for j, target in enumerate(item.get("targets", ())):
            if target not in declared_targets:
                problems.append(
                    Problem(
                        "target-not-declared",
                        f"items[{i}].targets[{j}]",
                        f"{target!r} is not among the declaration's targets",
                        tuple(declaration["targets"]),
                    )
                )

        if item["kind"] == "git-lines":
            problems.extend(_git_lines(item, f"items[{i}]"))
            continue  # no source: its lines are in the declaration (specs/025)

        if item["kind"] == "engine":
            if engine is not None:
                problems.append(
                    Problem(
                        "engine-duplicate",
                        f"items[{i}]",
                        f"items[{engine}] and items[{i}] are both engine items; a capability "
                        "carries at most one engine",
                    )
                )
            else:
                engine = i
            continue  # no source: its content is the engine the package carries (specs/018)

        problem = _path_problem(item["source"], f"items[{i}].source", "source")
        if problem:
            problems.append(problem)

    problems.extend(_settings(declaration))
    problems.extend(_runtime(declaration))
    problems.extend(_previous(declaration))
    problems.extend(_requires_and_groups(declaration))
    return problems


def _requires_and_groups(declaration: dict) -> list[Problem]:
    """Requirements and groups that cannot mean anything (specs/029 R-2)."""
    from kaelen import versions

    problems: list[Problem] = []
    seen: set[tuple[str, str]] = set()
    own = (declaration["node"], declaration["capability"])
    for i, req in enumerate(declaration.get("requires", ())):
        where, key = f"requires[{i}]", (req["node"], req["capability"])
        if key == own:
            problems.append(Problem("requires-self", where, "a capability cannot require itself"))
        if key in seen:
            problems.append(
                Problem("requires-duplicate", where, f"{key[0]}/{key[1]} is required twice")
            )
        seen.add(key)
        if versions.parse_range(req["version"]) is None:
            problems.append(
                Problem(
                    "requires-range",
                    f"{where}.version",
                    f'{req["version"]!r} is not a version range: comparators such as ">=1.2,<2"',
                )
            )
    names = {item["name"] for item in declaration["items"]}
    groups: set[str] = set()
    mandatory = []
    for i, group in enumerate(declaration.get("groups", ())):
        where = f"groups[{i}]"
        if group["name"] in groups:
            problems.append(
                Problem("group-duplicate", where, f"group {group['name']!r} is declared twice")
            )
        groups.add(group["name"])
        if group.get("mandatory"):
            mandatory.append(group["name"])
        for j, name in enumerate(group["items"]):
            if name not in names:
                problems.append(
                    Problem(
                        "group-unknown-item",
                        f"{where}.items[{j}]",
                        f"group {group['name']!r} names {name!r}, which is not an item",
                    )
                )
    if len(mandatory) > 1:
        problems.append(
            Problem(
                "group-mandatory-many",
                "groups",
                f"only one group may be mandatory; marked: {', '.join(mandatory)}",
            )
        )
    return problems


def _previous(declaration: dict) -> list[Problem]:
    """Previous locations (specs/024): inside the host, outside the engine's own area, a member
    only inside a JSON file, and each listed once."""
    problems, seen = [], set()
    for i, prev in enumerate(declaration.get("previous", ())):
        path, member = prev["path"], prev.get("member")
        where = f"previous[{i}]"
        # as the host would resolve it: `./x`, `a/../x` and a different case all name the same place
        normalised = posixpath.normpath(path).strip("/").casefold()
        if (
            path.startswith("/")
            or _DRIVE.match(path)
            or not resolves_inside(path)
            or normalised == ".kaelen"
            or normalised.startswith(".kaelen/")
        ):
            problems.append(
                Problem(
                    "previous-unsafe",
                    f"{where}.path",
                    f"previous location {path!r} must be relative, inside the host, and outside "
                    "the engine's area .kaelen",
                )
            )
        if member is not None and not path.endswith(".json"):
            problems.append(
                Problem(
                    "previous-member-not-json",
                    f"{where}.member",
                    f"a member is addressed only inside a JSON file, not in {path!r}",
                )
            )
        key = (path, member)
        if key in seen:
            problems.append(
                Problem("previous-duplicate", where, f"{path} {member or ''} is listed twice")
            )
        seen.add(key)
    return problems


def _git_lines(item: dict, where: str) -> list[Problem]:
    """A git-lines item (specs/025 R-3): its directory inside the host, outside `.git` and the
    engine's area; each line one git line that means what it shows and cannot pass for a marker."""
    from kaelen.host.sections import HASH  # the hash form of marking convention v1

    problems = []
    directory = item.get("directory", ".")
    segments = directory.strip("/").split("/")
    if (
        directory.startswith("/")
        or _DRIVE.match(directory)
        or not resolves_inside(directory)
        or ".git" in segments
        or segments[0] == ".kaelen"
    ):
        problems.append(
            Problem(
                "git-directory-unsafe",
                f"{where}.directory",
                f"directory {directory!r} must be relative, inside the host, and outside .git "
                "and the engine's area .kaelen",
            )
        )
    for j, line in enumerate(item["lines"]):
        if "\n" in line or "\r" in line:
            why = "holds a line break"
        elif not line.strip():
            why = "is empty"
        elif line != line.rstrip(" \t"):
            why = "ends with whitespace, which git drops"
        elif HASH.pattern.match(line):
            why = "has the form of a Kaelen marker"
        else:
            continue
        problems.append(Problem("git-line-invalid", f"{where}.lines[{j}]", f"{line!r} {why}"))
    return problems


_NAME = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def _runtime(declaration: dict) -> list[Problem]:
    """Runtime rules (specs/022): a valid interpreter specifier, paths inside the producer, and
    every item that runs in the environment pointing at a declared entry point."""
    from kaelen.host.runtime import parse_specifier

    problems = []
    runtime = declaration.get("runtime")
    if runtime is not None:
        try:
            parse_specifier(runtime["python"])
        except ValueError as exc:
            problems.append(Problem("runtime-python-specifier", "runtime.python", str(exc)))
        for key in ("lock", "code"):
            if key in runtime:
                problem = _path_problem(runtime[key], f"runtime.{key}", key)
                if problem:
                    problems.append(problem)
        if not runtime["entry_points"]:
            problems.append(
                Problem("runtime-no-entry-point", "runtime.entry_points", "declare one entry point")
            )
        for name in runtime["entry_points"]:
            if not _NAME.match(name):
                problems.append(
                    Problem(
                        "runtime-entry-name",
                        f"runtime.entry_points.{name}",
                        f"entry point {name!r} must be lowercase letters, digits and dashes",
                    )
                )
    entries = set((runtime or {}).get("entry_points", {}))
    for i, item in enumerate(declaration["items"]):
        wants = "entry" in item or item.get("runtime") is True
        if wants and runtime is None:
            problems.append(
                Problem(
                    "runtime-missing",
                    f"items[{i}]",
                    f"{item['kind']} {item['name']!r} runs in the environment, but the "
                    "declaration has no [runtime]",
                )
            )
        elif "entry" in item and item["entry"] not in entries:
            problems.append(
                Problem(
                    "entry-undeclared",
                    f"items[{i}].entry",
                    f"{item['kind']} {item['name']!r}: entry point {item['entry']!r} is not "
                    "declared in [runtime.entry_points]",
                    tuple(sorted(entries)),
                )
            )
    return problems


def _settings(declaration: dict) -> list[Problem]:
    """Settings rules (specs/017 FR-048): a default only on a non-secret setting, written to a
    settings file inside the host and outside the package area. Messages never echo a value."""
    problems = []
    has_default = False
    for i, setting in enumerate(declaration.get("settings", ())):
        if "default" in setting:
            has_default = True
            if setting.get("secret") is not False:
                problems.append(
                    Problem(
                        "setting-secret-default",
                        f"settings[{i}].default",
                        f"setting {setting['name']!r} carries a default but is not declared "
                        "secret = false; a secret setting never carries a value",
                    )
                )
    file = declaration.get("settings_file")
    if file is None:
        if has_default:
            problems.append(
                Problem(
                    "settings-file-missing",
                    "settings_file",
                    "settings with a default need settings_file: the host file they are written to",
                )
            )
        return problems
    normalised = file.strip("/")
    if (
        file.startswith("/")
        or _DRIVE.match(file)
        or not resolves_inside(file)
        or normalised == ".kaelen/packages"
        or normalised.startswith(".kaelen/packages/")
    ):
        problems.append(
            Problem(
                "settings-file-unsafe",
                "settings_file",
                f"settings_file {file!r} must be relative, inside the host, and outside "
                "the package area .kaelen/packages",
            )
        )
    return problems


def resolves_inside(path: str) -> bool:
    depth = 0
    for segment in path.split("/"):
        if segment == "..":
            depth -= 1
            if depth < 0:
                return False
        elif segment not in ("", "."):
            depth += 1
    return True


def _path_problem(path: str, where: str, what: str) -> Problem | None:
    if path.startswith("/") or _DRIVE.match(path):
        return Problem(
            "source-absolute",
            where,
            f"{what} {path!r} is absolute; write it relative to the producer",
        )
    if not resolves_inside(path):
        return Problem(
            "source-outside-producer", where, f"{what} {path!r} resolves outside the producer"
        )
    return None
