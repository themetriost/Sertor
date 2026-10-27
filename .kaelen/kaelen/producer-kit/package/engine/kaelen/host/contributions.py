"""The main Kaelen as the only writer of shared files (specs/027).

A capability's engine plans its text actions on shared files as before, then hands them to the
host's main Kaelen as a contribution set (`kaelen.contributions/1`). The main Kaelen knows no item
kind: it checks the set, keeps its own part of the operation with copies of prior states under
`.kaelen/contributions/`, applies the set with the same transforms, and answers with each
contribution's result. The protocol grows only by addition (FR-007).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from kaelen.host import apply as applier
from kaelen.host import home as homes

SCHEMA = "kaelen.contributions/1"
PART_SCHEMA = "kaelen.main-operation/1"
MINIMUM = "0.13.0"  # the first engine that knows the protocol
IGNORE = b"*\n"

# The fields each kind needs; any other field a kind carries is optional (R-10)
_SECTION = ("path", "style", "address")
_MEMBER = ("path", "json_path", "json_key")
_ELEMENT = ("path", "json_path", "address")
_SETTINGS = ("path", "capability", "content")
KINDS = {
    "section-add": (*_SECTION, "content"),
    "section-replace": (*_SECTION, "content"),
    "section-remove": _SECTION,
    "member-add": (*_MEMBER, "content"),
    "member-replace": (*_MEMBER, "content"),
    "member-remove": _MEMBER,
    "element-add": (*_ELEMENT, "content"),
    "element-remove": _ELEMENT,
    "settings-add": _SETTINGS,
    "settings-remove": _SETTINGS,
}
FIELDS = {
    "index", "op", "path", "style", "address", "json_path", "json_key", "content", "result",
    "inserted", "separator", "capability", "created_file", "claimed_by_others",
    "inherited_created", "entry", "form",
}  # fmt: skip
SET_FIELDS = ("schema", "capability", "operation", "serves", "files", "contributions")
OPTIONAL_SET_FIELDS = ("engine", "requires", "must_understand")


class Refused(Exception):
    """The main Kaelen will not apply this set; nothing was written."""

    def __init__(self, rule: str, message: str, path: str = "", minimum: str | None = None):
        super().__init__(message)
        self.rule, self.message, self.path, self.minimum = rule, message, path, minimum


# --- the set ------------------------------------------------------------------------------------


def files_of(host: Path, actions: list[dict]) -> dict:
    """Each shared file the actions touch, with its digest now (the fingerprint, R-6)."""
    paths = sorted({a["path"] for a in actions})
    return {p: applier.location_digest(host, p) for p in paths}


def build_set(op: dict, action: dict, engine_version: str) -> dict:
    """The set a `contribute` action hands the main Kaelen, from the record it belongs to."""
    return {
        "schema": SCHEMA,
        "capability": op["capability"],
        "operation": op["operation"],
        "serves": op["id"],
        "engine": {"version": engine_version},
        "requires": MINIMUM,  # the oldest main Kaelen that knows every kind used here
        "files": action["files"],
        "contributions": [{"index": i, **op["actions"][i]} for i in action["indices"]],
    }


def validate(doc) -> None:
    """Refuse a set this main Kaelen does not fully know (FR-009)."""
    if not isinstance(doc, dict):
        raise Refused("unreadable-contributions", "the contribution set is not a JSON object")
    if doc.get("schema") != SCHEMA:
        raise Refused(
            "contribution-unsupported",
            f"contribution set schema {doc.get('schema')!r} is not known to this main Kaelen "
            f"(it knows {SCHEMA})",
            minimum=doc.get("requires"),
        )
    missing = [f for f in SET_FIELDS if f not in doc]
    if missing:
        raise Refused("unreadable-contributions", f"the set lacks {', '.join(missing)}")
    for name in doc.get("must_understand") or []:
        if name not in FIELDS and name not in (*SET_FIELDS, *OPTIONAL_SET_FIELDS):
            raise Refused(
                "contribution-unsupported",
                f"the set needs field {name!r}, which this main Kaelen does not know",
                minimum=doc.get("requires"),
            )
    for c in doc["contributions"]:
        kind = c.get("op")
        if kind not in KINDS:
            raise Refused(
                "contribution-unsupported",
                f"contribution kind {kind!r} is not known to this main Kaelen",
                c.get("path", ""),
                doc.get("requires"),
            )
        lacking = [f for f in ("index", *KINDS[kind]) if f not in c]
        if lacking:
            raise Refused(
                "unreadable-contributions",
                f"a {kind} contribution lacks {', '.join(lacking)}",
                c.get("path", ""),
            )
        if c["path"] not in doc["files"]:
            raise Refused("unreadable-contributions", f"{c['path']} has no fingerprint", c["path"])


def _fingerprints(host: Path, doc: dict) -> None:
    changed = [p for p, d in sorted(doc["files"].items()) if applier.location_digest(host, p) != d]
    if changed:
        raise Refused(
            "shared-file-changed",
            f"{len(changed)} shared file(s) changed since the operation was planned: "
            f"{', '.join(changed)}; nothing was written",
            changed[0],
        )


# --- the main Kaelen's part ----------------------------------------------------------------------


def part_path(capability: str) -> str:
    return f"{homes.CONTRIBUTIONS}/{capability}.json"


def load_part(host: Path, capability: str) -> dict | None:
    path = host / part_path(capability)
    if not path.is_file():
        return None
    try:
        part = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        where = part_path(capability)
        raise Refused("unreadable-part", f"{where}: {exc}", where) from exc
    if not isinstance(part, dict) or part.get("schema") != PART_SCHEMA:
        found = part.get("schema") if isinstance(part, dict) else None
        raise Refused(
            "operation-unsupported",
            f"{part_path(capability)} has schema {found!r}; this main Kaelen knows {PART_SCHEMA}",
            part_path(capability),
        )
    return part


def save_part(host: Path, part: dict, writer: applier.Writer) -> None:
    # the part first: whatever stops after it, it describes (the ignore file included)
    data = (json.dumps(part, indent=2) + "\n").encode("utf-8")
    writer.write(host / part_path(part["capability"]), data)
    ignore = host / homes.CONTRIBUTIONS / ".gitignore"
    if not ignore.is_file():
        writer.write(ignore, IGNORE)


def drop_part(host: Path, capability: str, writer: applier.Writer) -> None:
    folder = host / homes.CONTRIBUTIONS
    writer.delete(host / part_path(capability))
    pre = folder / f"{capability}.pre"
    if pre.exists():
        writer.delete(pre)
    if folder.is_dir() and [p.name for p in folder.iterdir()] in ([], [".gitignore"]):
        writer.delete(folder)
        kaelen = host / ".kaelen"
        if kaelen.is_dir() and not any(kaelen.iterdir()):
            writer.rmdir(kaelen)


def _orphan(host: Path, part: dict) -> bool:
    """A part whose capability operation is gone: stopped between its end and the release."""
    record = applier.load_record(host, part["capability"])
    return record is None or record.get("id") != part.get("serves")


def check(host: Path, doc) -> None:
    validate(doc)
    part = load_part(host, doc["capability"])
    if part is not None and part.get("serves") == doc["serves"]:
        return  # resuming: the part's own record carries it
    if part is not None and not _orphan(host, part):
        raise Refused(
            "other-operation",
            f"another operation of {doc['capability']!r} has a pending part on shared files",
            part_path(doc["capability"]),
        )
    _fingerprints(host, doc)


def apply_set(host: Path, doc, writer: applier.Writer) -> dict:
    """Apply a set all or none, under the main Kaelen's part; returns the results by index."""
    validate(doc)
    capability = doc["capability"]
    part = load_part(host, capability)
    if part is not None and part.get("serves") != doc["serves"]:
        if not _orphan(host, part):
            raise Refused(
                "other-operation",
                f"another operation of {capability!r} has a pending part on shared files",
                part_path(capability),
            )
        drop_part(host, capability, writer)
        part = None
    if part is not None and part.get("rolling_back"):
        raise Refused(
            "rollback-in-progress",
            f"a rollback of {capability!r}'s part on shared files is in progress",
            part_path(capability),
        )
    if part is None:
        _fingerprints(host, doc)
        part = {
            "schema": PART_SCHEMA,
            "serves": doc["serves"],
            "capability": capability,
            "copies_dir": f"{homes.CONTRIBUTIONS}/{capability}.pre",
            "set": doc,
            "done": [],
            "results": {},
            "copies": [],
            "rolling_back": False,
        }
        save_part(host, part, writer)  # the first write: whatever stops after it, it describes
    done = set(part["done"])
    for c in part["set"]["contributions"]:
        key = str(c["index"])
        if c["index"] in done:
            continue
        action = {k: v for k, v in c.items() if k != "index"}
        intended = applier.intended_digest(host, action)
        applier.ensure_copy(host, part, action["path"], intended, writer, save=save_part)
        part["results"][key] = applier.execute(host, action, writer)
        part["done"] = sorted({*done, c["index"]})
        done = set(part["done"])
        save_part(host, part, writer)
    return dict(part["results"])


def rollback_part(host: Path, capability: str, writer: applier.Writer) -> bool:
    """Put back every shared file the part touched, from its copies; False when there is none."""
    part = load_part(host, capability)
    if part is None:
        return False
    if not part.get("rolling_back"):
        part["rolling_back"] = True
        save_part(host, part, writer)
    for entry in reversed(part.get("copies", [])):
        applier.restore(host, part, entry, writer)
    applier.remove_created(host, part, writer)
    drop_part(host, capability, writer)
    return True


def release_part(host: Path, capability: str, serves: str, writer: applier.Writer) -> bool:
    """Drop the part once the operation it served has ended; False when there is none."""
    part = load_part(host, capability)
    if part is None or part.get("serves") != serves:
        return False
    drop_part(host, capability, writer)
    return True


def command(host: Path, request: dict, writer: applier.Writer, engine_version: str) -> dict:
    """The `contribute` verb: what it answers, as its `--json` document (contract)."""
    mode = request["mode"]
    doc = {"verdict": "internal", "engine": {"version": engine_version}, "results": {},
           "errors": [], "minimum": None}  # fmt: skip
    payload = request.get("set")
    if isinstance(payload, dict):
        doc["serves"] = payload.get("serves")
    try:
        if request.get("dry_run"):
            _dry_run(host, request, payload, doc)
        elif mode == "check":
            check(host, payload)
            doc["verdict"] = "checked"
        elif mode == "apply":
            doc["results"] = apply_set(host, payload, writer)
            doc["verdict"] = "contributed"
        elif mode == "rollback":
            done = rollback_part(host, request["capability"], writer)
            doc["verdict"] = "rolled-back" if done else "nothing-to-roll-back"
        elif mode == "release":
            done = release_part(host, request["capability"], request["serves"], writer)
            doc["verdict"] = "released" if done else "nothing-to-release"
    except Refused as exc:
        doc["verdict"] = "unable-to-check" if exc.rule.startswith("unreadable") else "refused"
        if exc.rule == "contribution-unsupported":
            doc["minimum"] = exc.minimum or "a newer main Kaelen"
        doc["errors"].append({"rule": exc.rule, "path": exc.path, "message": exc.message})
    except OSError as exc:  # stopped half way: the part stays for completion or rollback
        doc["verdict"] = "incomplete"
        doc["errors"].append(
            {
                "rule": "write-failed",
                "path": str(getattr(exc, "filename", "") or ""),
                "message": f"the main Kaelen's part stopped: {exc}",
            }  # fmt: skip
        )
    except Exception as exc:  # a defect, said as one, never a traceback (constitution I.)
        doc["verdict"] = "internal"
        doc["errors"].append(
            {"rule": "internal", "path": "", "message": f"{type(exc).__name__}: {exc}"}
        )
    if doc["verdict"] in ERROR_CODES:  # the constitution's envelope on every failure (I.)
        first = (doc["errors"] or [{}])[0]
        message = first.get("message") or f"the main Kaelen's contribute ended {doc['verdict']}"
        minimum = doc["minimum"]
        hint = None
        if minimum:
            hint = (
                f"needs a main Kaelen {minimum} or later"
                if minimum[0].isdigit()
                else f"needs {minimum}"
            )
        doc["error"] = {"code": ERROR_CODES[doc["verdict"]], "message": message, "hint": hint}
    return doc


def _dry_run(host: Path, request: dict, payload, doc: dict) -> None:
    """What the mode would write, written nowhere (constitution I.)."""
    mode = request["mode"]
    doc["dry_run"] = True
    doc["would_write"] = []
    if mode in ("check", "apply"):
        check(host, payload)
        doc["verdict"] = "checked" if mode == "check" else "would-contribute"
        doc["would_write"] = sorted(payload["files"])
        return
    part = load_part(host, request["capability"])
    if mode == "rollback":
        if part is None:
            doc["verdict"] = "nothing-to-roll-back"
            return
        doc["verdict"] = "would-roll-back"
        doc["would_write"] = sorted({e["path"] for e in part.get("copies", [])})
        return
    if part is None or part.get("serves") != request["serves"]:
        doc["verdict"] = "nothing-to-release"
        return
    doc["verdict"] = "would-release"


ERROR_CODES = {"refused": "REFUSED", "incomplete": "INCOMPLETE",
               "unable-to-check": "UNABLE_TO_CHECK", "internal": "INTERNAL"}  # fmt: skip
EXIT = {"checked": 0, "contributed": 0, "rolled-back": 0, "nothing-to-roll-back": 0,
        "released": 0, "nothing-to-release": 0, "would-contribute": 0, "would-roll-back": 0,
        "would-release": 0, "refused": 1, "incomplete": 3,
        "unable-to-check": 66, "internal": 70}  # fmt: skip


# --- reaching the main Kaelen ---------------------------------------------------------------------


class MainUnreachable(OSError):
    """The main Kaelen could not be run or did not answer: nothing is written instead of it."""

    def __init__(self, message: str, path: str = "", rule: str = "main-unreachable"):
        super().__init__(message, path)
        self.message, self.filename, self.rule = message, path, rule

    def __str__(self) -> str:
        return self.message


def main_run(host: Path) -> Path:
    return host / homes.MAIN / "run.py"


class Runner:
    """Runs the main Kaelen's own code in its own process, the request on stdin (R-5, FR-016)."""

    def __call__(self, target: Path, host: Path, request: dict, writer=None) -> dict:
        if not target.is_file():
            raise MainUnreachable(f"the main Kaelen is missing: {target}", str(target))
        args = [sys.executable, "-I", "-B", str(target), "contribute", "--host", str(host)]
        mode = request["mode"]
        if mode == "check":
            args.append("--check")
        elif mode in ("rollback", "release"):
            args += ["--capability", request["capability"], f"--{mode}"]
            if mode == "release":
                args += ["--serves", request["serves"]]
        if request.get("dry_run"):
            args.append("--dry-run")
        args.append("--json")
        try:
            done = subprocess.run(
                args,
                input=json.dumps(request.get("set") or {}),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=600,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise MainUnreachable(f"the main Kaelen could not be run: {exc}", str(target)) from exc
        try:
            return json.loads(done.stdout)
        except ValueError as exc:
            if "invalid choice" in done.stderr and "contribute" in done.stderr:
                return {
                    "verdict": "refused",
                    "results": {},
                    "minimum": MINIMUM,
                    "errors": [
                        {
                            "rule": "contribution-unsupported",
                            "path": homes.MAIN,
                            "message": "the main Kaelen does not know the contribution protocol",
                        }
                    ],
                }
            tail = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no answer"]
            raise MainUnreachable(
                f"the main Kaelen did not answer: {tail[0]}", str(target)
            ) from exc


class InProcess:
    """The same engine's `contribute`, called directly: for tests and for the arriving engine
    (byte-identical to the main Kaelen it is about to become)."""

    def __init__(self, engine_version: str = MINIMUM):
        self.engine_version = engine_version

    def __call__(self, target: Path, host: Path, request: dict, writer=None) -> dict:
        doc = command(host, request, writer or applier.Writer(), self.engine_version)
        if doc["verdict"] == "incomplete":  # the interruption itself, as the subprocess would end
            error = doc["errors"][0]
            raise MainUnreachable(error["message"], error["path"], error["rule"])
        return doc


DEFAULT_RUNNER: Runner | InProcess = Runner()
