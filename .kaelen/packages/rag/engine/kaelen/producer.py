"""Correspondence between a declaration and its producer repository.

Runs only on a coherent declaration: every source and governed area is a relative path
that stays inside the producer.
"""

from __future__ import annotations

import posixpath
from pathlib import Path

from kaelen.outcome import Problem


def _norm(path: str) -> str:
    return posixpath.normpath(path)


def missing_sources(declaration: dict, producer: Path) -> list[Problem]:
    problems = []
    for i, item in enumerate(declaration["items"]):
        if "source" not in item:  # an engine item: nothing to find in the producer
            continue
        source = _norm(item["source"])
        if not (producer / source).exists():
            problems.append(
                Problem(
                    "source-missing",
                    f"items[{i}].source",
                    f"{item['kind']} {item['name']!r}: expected source {item['source']!r} "
                    "not found in the producer",
                )
            )
    problems.extend(_runtime_files(declaration, producer))
    return problems


def _runtime_files(declaration: dict, producer: Path) -> list[Problem]:
    """The runtime's lock exists and is fully pinned and hashed; its code is a directory."""
    from kaelen.host.runtime import parse_lock

    runtime = declaration.get("runtime")
    if runtime is None:
        return []
    problems = []
    lock = producer / _norm(runtime["lock"])
    if not lock.is_file():
        problems.append(
            Problem(
                "runtime-lock-missing",
                "runtime.lock",
                f"lock file {runtime['lock']!r} not found in the producer",
            )
        )
    else:
        try:
            text = lock.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            text = None
            problems.append(Problem("runtime-lock-unreadable", "runtime.lock", "not UTF-8 text"))
        if text is not None:
            _, found = parse_lock(text)
            problems.extend(Problem(rule, "runtime.lock", message) for rule, message in found)
    if "code" in runtime and not (producer / _norm(runtime["code"])).is_dir():
        problems.append(
            Problem(
                "runtime-code-missing",
                "runtime.code",
                f"code directory {runtime['code']!r} not found in the producer",
            )
        )
    return problems


def runtime_sources(declaration: dict) -> list[str]:
    runtime = declaration.get("runtime") or {}
    return [_norm(runtime[k]) for k in ("lock", "code") if k in runtime]


def undeclared_files(declaration: dict, producer: Path) -> list[Problem]:
    sources = [_norm(item["source"]) for item in declaration["items"] if "source" in item]
    sources += runtime_sources(declaration)

    def covered(rel: str) -> bool:
        return any(rel == s or rel.startswith(s + "/") for s in sources)

    findings = []
    for i, area in enumerate(declaration.get("governs", ())):
        root = producer / _norm(area)
        if not root.is_dir():
            findings.append(
                Problem(
                    "governed-area-missing",
                    f"governs[{i}]",
                    f"governed area {area!r} does not exist in the producer",
                )
            )
            continue
        files = sorted(p.relative_to(producer).as_posix() for p in root.rglob("*") if p.is_file())
        for rel in files:
            if not covered(rel):
                findings.append(
                    Problem(
                        "undeclared-file",
                        f"governs[{i}]",
                        f"{rel} is inside governed area {area!r} but no item declares it",
                    )
                )
    return findings
