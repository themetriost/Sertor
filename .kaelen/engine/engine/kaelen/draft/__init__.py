"""`kaelen draft`: a declaration draft deduced from the producer's layout (specs/030).

An aid outside the contract: the declaration is the author's, and no verb reads the draft. The
engine reads the layout by the fixed conventions of `conventions.json`, writes
`kaelen.declaration.draft.toml` beside the declaration, and never touches anything else.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DRAFT = "kaelen.declaration.draft.toml"
DECLARATION = "kaelen.declaration.toml"
SCHEMA = "kaelen.draft/1"
_EXIT = {
    "drafted": 0,
    "would-draft": 0,
    "unchanged": 0,
    "nothing-to-add": 0,
    "listed": 0,
    "refused": 1,
    "usage": 64,
    "internal": 70,
}


def conventions() -> dict:
    return json.loads((Path(__file__).parent / "conventions.json").read_text(encoding="utf-8"))


def _contract() -> tuple[re.Pattern, list[str]]:
    """The name rule and the hook events, from the declaration schema: never a copy."""
    from kaelen.contract import raw_schema

    defs = raw_schema(1)["$defs"]
    return re.compile(defs["name"]["pattern"]), list(defs["hookEvent"]["enum"])


@dataclass
class DraftOutcome:
    verdict: str
    path: str | None = None
    entries: list[dict] = field(default_factory=list)
    flags: list[dict] = field(default_factory=list)
    unclassified: list[dict] = field(default_factory=list)
    hints: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    conventions: list[dict] | None = None
    ignored: dict = field(default_factory=lambda: {"git": False, "count": 0})  # specs/031 FR-008

    @property
    def exit_code(self) -> int:
        return _EXIT[self.verdict]

    def to_document(self, engine_version: str) -> dict:
        doc = {
            "schema": SCHEMA,
            "engine": {"version": engine_version},
            "verdict": self.verdict,
            "path": self.path,
            "entries": self.entries,
            "flags": self.flags,
            "unclassified": self.unclassified,
            "hints": self.hints,
            "findings": self.findings,
            "errors": self.errors,
            "ignored": self.ignored,
        }
        if self.conventions is not None:
            doc["conventions"] = self.conventions
        if self.exit_code != 0:  # the constitution's envelope on every failure (I.)
            first = (self.errors or [{}])[0]
            message = first.get("message") or f"draft ended {self.verdict}"
            doc["error"] = {"code": self.verdict.upper(), "message": message, "hint": None}
        return doc


def _covered(rel: str, sources: list[str]) -> bool:
    return any(rel == s or rel.startswith(s.rstrip("/") + "/") for s in sources)


def _toml(text: str) -> str:
    """A TOML basic string: backslashes and quotes escaped, so any file name stays valid TOML."""
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _candidates(base: Path, prefix: str, conv: dict) -> list[str]:
    """The paths `_scan` may classify, relative to the producer. A folder is named without a
    trailing `/`: git then looks at the folder itself, so `dir/*` with `!dir/keep` does not hide
    `dir`."""
    folders = {c["folder"] for c in conv["conventions"]}
    out = []
    for child in sorted(base.iterdir(), key=lambda p: p.name):
        if child.name in conv["exclusions"]:
            continue
        rel = prefix + child.name
        out.append(rel)
        if child.is_dir() and child.name in folders:
            out += [f"{rel}/{item.name}" for item in sorted(child.iterdir(), key=lambda p: p.name)]
    return out


def _ignored(producer: Path, candidates: list[str], git) -> set[str] | None:
    """The candidates git ignores in the producer, asked of git itself (its negations, nested
    files and excludes included); None when git cannot answer (specs/031 R-8)."""
    if not candidates:
        return set()
    stdin = "".join(c + "\0" for c in candidates)
    code, out = git.run(["check-ignore", "--stdin", "-z"], producer, input=stdin)
    if code not in (0, 1):  # 0: some ignored, 1: none; anything else is no answer
        return None
    return {p for p in out.split("\0") if p}


def _scan(
    base: Path,
    prefix: str,
    conv: dict,
    also_excluded: set[str] = frozenset(),
    ignored: set[str] = frozenset(),
) -> tuple[list[dict], list[dict], list[dict], int]:
    """(entries, unclassified, hints, paths left out as git-ignored) under `base`; sources carry
    `prefix`."""
    entries, unclassified, hints = [], [], []
    left_out = 0
    by_folder = {c["folder"]: c for c in conv["conventions"]}
    hint_folders = {h["folder"]: h for h in conv["hints"]}
    excluded = set(conv["exclusions"]) | set(also_excluded)
    for child in sorted(base.iterdir(), key=lambda p: p.name):
        rel = prefix + child.name
        if child.name in excluded:
            continue
        if rel in ignored:
            left_out += 1
            continue
        if child.name in hint_folders and child.is_dir():
            hints.append(
                {
                    "id": hint_folders[child.name]["id"],
                    "path": rel,
                    "text": hint_folders[child.name]["text"],
                }
            )
            continue
        c = by_folder.get(child.name)
        if c is None or not child.is_dir():
            unclassified.append({"path": rel, "why": "outside every convention"})
            continue
        for item in sorted(child.iterdir(), key=lambda p: p.name):
            irel = f"{rel}/{item.name}"
            if item.name in excluded:
                continue
            if irel in ignored:
                left_out += 1
                continue
            match = c["match"]
            if match == "dir-with-SKILL.md":
                ok, why = (
                    item.is_dir() and (item / "SKILL.md").is_file(),
                    ("a skill folder needs a SKILL.md"),
                )
            elif match.startswith("*."):
                ok, why = (
                    item.is_file() and item.suffix == match[1:],
                    (f"{c['folder']}/ holds {match} files"),
                )
            elif match == "file":
                ok, why = item.is_file(), f"{c['folder']}/ holds files"
            else:  # entry: a file or a folder
                ok, why = True, ""
            # the name, as the conventions file says (R-1): a folder's name, or a file's stem
            name = item.name if c["name_from"] == "dir" or item.is_dir() else item.stem
            if not ok:
                unclassified.append({"path": irel, "why": why})
                continue
            entry = {
                "kind": c["kind"],
                "name": name,
                "source": irel,
                "convention": c["id"],
                "fill": list(c["fill"]),
                "commented": False,
                "why": None,
            }
            if c.get("extension_point"):
                entry["extension_point"] = c["extension_point"]
            if not _contract()[0].fullmatch(name):
                entry["commented"] = True
                entry["why"] = (
                    f"{name!r} is not a valid name (lowercase letters, digits and hyphens, "
                    "starting with a letter): choose one"
                )
            entries.append(entry)
    return entries, unclassified, hints, left_out


def _render(entries, flags, unclassified, hints, conv, folders, has_declaration, targets) -> str:
    out = [
        "# Kaelen declaration DRAFT, generated by `kaelen draft` (specs/030).",
        "# It is NOT the declaration: no verb reads it. Review it, then copy what you want into",
        f"# {DECLARATION} by hand. Each entry names the convention that produced it.",
        "",
    ]
    if not has_declaration:
        out += [
            "# Fill these, then remove the comment marks:",
            '# node = ""',
            '# capability = ""',
            '# version = ""',
            "# targets = ["
            + ", ".join(f'"{t}"' for t in targets)
            + "]   # keep the ones you support",
            "contract = 1",
            "",
        ]
    if folders:
        out += [
            "# Proposed: every file under these folders must then be declared (validate checks):",
            "# governs = [" + ", ".join(f'"{f}"' for f in folders) + "]",
            "",
        ]
    if not has_declaration:
        out.append(
            "# Not deduced (see the kaelen-authoring skill): " + ", ".join(conv["not_deduced"])
        )
        out.append("")
    for e in entries:
        mark = "# " if e["commented"] else ""
        out.append(f"# convention {e['convention']}: {e['source']}")
        if e["why"]:
            out.append(f"# NOTE: {e['why']}")
        out.append(f"{mark}[[items]]")
        out.append(f"{mark}kind = {_toml(e['kind'])}")
        out.append(f"{mark}name = {_toml(e['name'])}")
        out.append(f"{mark}source = {_toml(e['source'])}")
        if e.get("extension_point"):
            out.append(f'{mark}extension_point = "{e["extension_point"]}"')
        if "event" in e["fill"]:
            out.append('# event = ""   # fill: ' + ", ".join(_contract()[1]))
        out.append("")
    for f in flags:
        out.append(
            f"# DECLARED BUT NOT FOUND: items[{f['index']}] {f['kind']} {f['name']!r}: "
            f"{f['source']} does not exist"
        )
    if flags:
        out.append("")
    if unclassified:
        out.append("# Not classified by any convention (declare them by hand if they belong):")
        out += [f"#   {u['path']}: {u['why']}" for u in unclassified]
        out.append("")
    for h in hints:
        out.append(f"# Hint ({h['path']}): {h['text']}")
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def draft(
    producer: Path,
    *,
    base: str | None = None,
    declaration: Path | None = None,
    dry_run: bool = False,
    replace: bool = False,
    git=None,
) -> DraftOutcome:
    """Write (or report) the draft for `producer` (specs/030 FR-001…FR-011)."""
    from kaelen.placement import load_rule
    from kaelen.validate import validate_document

    if not producer.is_dir():
        return DraftOutcome(
            "usage",
            errors=[
                {
                    "rule": "producer-not-directory",
                    "path": "",
                    "message": f"{producer.as_posix()!r} is not a folder",
                }
            ],
        )
    prefix = ""
    scan_root = producer
    if base:
        scan_root = (producer / base).resolve()
        try:
            rel = scan_root.relative_to(producer.resolve()).as_posix()
        except ValueError:
            rel = None
        if rel is None or not scan_root.is_dir():
            return DraftOutcome(
                "usage",
                errors=[
                    {
                        "rule": "base-invalid",
                        "path": base,
                        "message": f"--base {base!r} is not a folder inside the producer",
                    }
                ],
            )
        prefix = "" if rel == "." else rel + "/"
    decl = declaration or producer / DECLARATION
    target = decl.parent / DRAFT
    conv = conventions()
    out = DraftOutcome("drafted", path=target.as_posix())
    if git is None:
        from kaelen.provenance import DEFAULT_GIT as git
    ignored = _ignored(producer, _candidates(scan_root, prefix, conv), git)
    entries, unclassified, hints, left_out = _scan(
        scan_root, prefix, conv, {decl.name}, ignored or set()
    )
    out.unclassified, out.hints = unclassified, hints
    out.ignored = {"git": ignored is not None, "count": left_out}
    has_declaration = decl.is_file()
    if has_declaration:
        try:
            doc = tomllib.loads(decl.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            out.verdict = "refused"
            out.errors.append(
                {
                    "rule": "declaration-unreadable",
                    "path": decl.as_posix(),
                    "message": f"the declaration cannot be read as TOML: {exc}",
                }
            )
            return out
        checked, _, _ = validate_document(decl, producer)
        if checked.errors:
            out.findings.append(
                {
                    "rule": "declaration-invalid",
                    "path": decl.as_posix(),
                    "message": "the declaration does not validate: " + checked.errors[0].message,
                }
            )
        items = [i for i in doc.get("items", []) if isinstance(i, dict)]
        sources = [str(i["source"]) for i in items if i.get("source")]
        runtime = doc.get("runtime") or {}
        sources += [str(runtime[k]) for k in ("lock", "code") if runtime.get(k)]
        declared = {(i.get("kind"), i.get("name")) for i in items}
        entries = [e for e in entries if not _covered(e["source"], sources)]
        for e in entries:
            if (e["kind"], e["name"]) in declared:
                e["commented"] = True
                clash = f"a {e['kind']} named {e['name']!r} is already declared"
                e["why"] = f"{e['why']}; {clash}" if e["why"] else clash
        for index, item in enumerate(doc.get("items", [])):
            if isinstance(item, dict) and item.get("source"):
                if not (producer / str(item["source"])).exists():
                    out.flags.append(
                        {
                            "index": index,
                            "kind": item.get("kind"),
                            "name": item.get("name"),
                            "source": item["source"],
                        }
                    )
        unclassified = [u for u in unclassified if not _covered(u["path"], sources)]
        out.unclassified = unclassified
        if not entries and not out.flags and not unclassified:
            out.verdict = "nothing-to-add"
            out.path = None
            return out
    entries.sort(key=lambda e: (e["kind"], e["source"]))
    out.entries = [dict(e) for e in entries]
    if not entries and not has_declaration:
        out.findings.append(
            {
                "rule": "no-convention-matched",
                "path": prefix or ".",
                "message": "no file matched a convention: write the declaration by hand",
            }
        )
    # the convention folders that gave entries, as a `governs` proposal (Q-1e)
    folders = (
        []
        if has_declaration
        else sorted({prefix + e["source"][len(prefix) :].split("/")[0] for e in entries})
    )
    targets = list(load_rule()["targets"])
    text = _render(entries, out.flags, unclassified, hints, conv, folders, has_declaration, targets)
    data = text.encode("utf-8")
    if target.is_file():
        if target.read_bytes() == data:
            out.verdict = "unchanged"
            return out
        if dry_run and not replace:  # a preview shows the new draft; only writing refuses (032)
            out.verdict = "would-draft"
            out.findings.append(
                {
                    "rule": "draft-exists",
                    "path": target.as_posix(),
                    "message": f"{target.name} exists and differs from this draft: the real run "
                    "needs --replace to overwrite it",
                }
            )
            return out
        if not replace:
            out.verdict = "refused"
            out.errors.append(
                {
                    "rule": "draft-exists",
                    "path": target.as_posix(),
                    "message": f"{target.name} exists and differs from a new draft: review "
                    "it, or pass --replace to overwrite it",
                }
            )
            return out
    if dry_run:
        out.verdict = "would-draft"
        return out
    tmp = target.with_name(target.name + ".kaelen-tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, target)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink()
        out.verdict = "refused"
        out.errors.append(
            {
                "rule": "write-failed",
                "path": target.as_posix(),
                "message": f"cannot write the draft: {exc}",
            }
        )
    return out


def render_human(out: DraftOutcome) -> str:
    head = {
        "drafted": f"DRAFTED {out.path}",
        "would-draft": f"WOULD-DRAFT {out.path}",
        "unchanged": f"UNCHANGED {out.path}",
        "nothing-to-add": "NOTHING-TO-ADD: the declaration covers every conventional file",
        "refused": "REFUSED",
        "usage": "USAGE",
        "internal": "INTERNAL",
        "listed": "CONVENTIONS",
    }[out.verdict]
    lines = [head]
    if out.verdict in ("drafted", "would-draft", "unchanged"):
        proposed = sum(1 for e in out.entries if not e["commented"])
        lines.append(
            f"  {proposed} entry(ies) proposed, {len(out.entries) - proposed} commented, "
            f"{len(out.flags)} declared item(s) flagged, "
            f"{len(out.unclassified)} file(s) not classified"
        )
        if not out.ignored["git"]:
            lines.append("  git not consulted: nothing left out as ignored")
        elif out.ignored["count"]:
            lines.append(f"  {out.ignored['count']} path(s) left out: git ignores them")
    for c in out.conventions or []:
        lines.append(f"  {c['id']}: {c['folder']}/ {c['match']} -> {c['kind']}")
    for e in out.errors:
        lines.append(f"  ERROR {e['rule']}: {e['message']}")
    for f in out.findings:
        lines.append(f"  FINDING {f['rule']}: {f['message']}")
    return "\n".join(lines) + "\n"
