"""What a package contains: content files and per-target lists (specs/015 data-model).

Runs only on a declaration `validate` found valid against the producer: every source is a
relative path inside the producer, and it exists.
"""

from __future__ import annotations

import os
import posixpath
from pathlib import Path

from kaelen.outcome import Problem
from kaelen.package.location import AREA
from kaelen.placement import PLACED, place_item, qualifier_of, with_source_suffix


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _overlaps_area(source: str) -> bool:
    area = "/".join(AREA)
    return source in (".", area) or source.startswith(area + "/") or area.startswith(source + "/")


def _sources(document: dict) -> list[tuple[str, str, str]]:
    """(where, label, declared source) of every source the package carries."""
    runtime = document.get("runtime") or {}
    sources = [
        (f"items[{i}].source", f"{item['kind']} {item['name']!r}", item["source"])
        for i, item in enumerate(document["items"])
        if "source" in item  # an engine item has none: the package injects the engine itself
    ]
    # the runtime's recipe travels as content too, never a built environment (specs/022 FR-005)
    sources += [
        (f"runtime.{k}", f"runtime {k}", runtime[k]) for k in ("lock", "code") if k in runtime
    ]
    return sources


def _python_cache(rel: str) -> bool:
    return "__pycache__" in rel.split("/") or rel.endswith((".pyc", ".pyo"))


def leave_out(
    planned: list[tuple[str, Path]], document: dict, producer: Path, git
) -> tuple[list[tuple[str, Path]], list[dict], list[Problem], bool]:
    """What the package carries once the producer's leftovers are left out (specs/033 R-3).

    Git decides what the repository ignores (tracked files never are); Python caches are left
    out whatever git says. Returns (kept, left_out, refusals, rules_unread).
    """
    rels = [rel.removeprefix("content/") for rel, _ in planned]
    caches = {r for r in rels if _python_cache(r)}
    rest = [r for r in rels if r not in caches]
    code, out = git.run(["check-ignore", "--stdin", "-z"], producer, input="\0".join(rest))
    ignored = {p for p in out.split("\0") if p} & set(rest) if code == 0 else set()
    unread = code not in (0, 1, 128)  # 128: not a repository, so no rules to apply
    left = caches | ignored
    left_out = [
        {"path": r, "reason": "python-cache" if r in caches else "ignored"} for r in sorted(left)
    ]
    problems = []
    for where, label, declared in _sources(document):
        source = posixpath.normpath(declared)
        own = [r for r in rels if r == source or r.startswith(source + "/")]
        if own and all(r in left for r in own):
            problems.append(
                Problem(
                    "source-ignored",
                    where,
                    f"{label}: every file of source {declared!r} is ignored by the producer's "
                    f"repository or is a Python cache ({', '.join(own[:3])}"
                    f"{', …' if len(own) > 3 else ''}); declare a tracked source",
                )
            )
    kept = [(rel, path) for rel, path in planned if rel.removeprefix("content/") not in left]
    return kept, left_out, problems, unread


def plan_content(document: dict, producer: Path) -> tuple[list[tuple[str, Path]], list[Problem]]:
    """(package path, producer file) for every declared source file, sorted; or the refusals."""
    files: dict[str, Path] = {}
    problems: list[Problem] = []
    for where, label, declared in _sources(document):
        item = {"source": declared}
        source = posixpath.normpath(item["source"])
        if _overlaps_area(source):
            problems.append(
                Problem(
                    "source-in-package",
                    where,
                    f"{label}: source {item['source']!r} overlaps the package area "
                    f"{'/'.join(AREA)!r}; a package cannot contain itself",
                )
            )
            continue
        root = producer / source
        for path in _walk(root) if root.is_dir() else [root]:
            rel = path.relative_to(producer).as_posix()
            if not _inside(path, producer):
                problems.append(
                    Problem(
                        "source-link-outside",
                        where,
                        f"{label}: {rel} is a link that resolves outside the producer",
                    )
                )
                continue
            files[f"content/{rel}"] = path
    return sorted(files.items()), problems


def _walk(root: Path) -> list[Path]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        dirnames.sort()
        out.extend(Path(dirpath) / name for name in sorted(filenames))
    return out


def targets_report(
    document: dict, producer: Path | None = None
) -> tuple[list[dict], list[Problem]]:
    """Per declared target, each applicable item with its placement read from the rule.

    An item aimed at a target that cannot receive it is reported, never hidden: one
    `unsupported-on-target` finding per (item, target), and the package is still produced
    (specs/016 FR-015, FR-016).
    """
    capability = document["capability"]
    targets, findings = [], []
    for target in document["targets"]:
        items = []
        for i, item in enumerate(document["items"]):
            if target not in item.get("targets", document["targets"]):
                continue
            qualifier = qualifier_of(item)
            answer = place_item(target, item, capability, document["node"])
            entry = {
                "name": item["name"],
                "kind": item["kind"],
                "qualifier": qualifier,
                "outcome": answer["outcome"],
            }
            if answer["outcome"] == PLACED:
                source_is_file = (
                    producer is not None and (producer / item.get("source", "")).is_file()
                )
                entry["locations"] = [
                    {
                        "path": with_source_suffix(loc, item, source_is_file)["path"],
                        "wrapper": loc["wrapper"],
                        "section": loc["section"],
                        "shared": loc["shared"],
                    }
                    for loc in answer["locations"]
                ]
            else:
                entry["reason"] = answer["reason"]
                findings.append(
                    Problem(
                        "unsupported-on-target",
                        f"items[{i}]",
                        f"{item['kind']} {item['name']!r}: not supported on {target} "
                        f"({answer['reason']}): {answer['detail']}",
                    )
                )
            entry["verified"] = answer["evidence"]["verified"]
            items.append(entry)
        targets.append({"target": target, "items": items})
    return targets, findings
