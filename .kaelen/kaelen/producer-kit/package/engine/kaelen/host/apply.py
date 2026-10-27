"""Applying a plan on the host, under an operation record (specs/017 research R-9).

Order: write the operation record, apply the actions one by one (each a whole-file write), then
write the registry and drop the record. Every action is idempotent given the plan, so an
interrupted operation completes by applying the actions not yet marked done.

Before the first write of each location, a copy of its prior state is kept beside the record, so an
interrupted operation can also be rolled back (specs/021 research R-1..R-5).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
from pathlib import Path

from kaelen.host import home as homes
from kaelen.host import jsonspan, registry, runtime, sections, settingsfile
from kaelen.host.state import STYLES, element_identity, read_text, read_tree

SCHEMA = "kaelen.operation/2"
SCHEMA_1 = "kaelen.operation/1"
ABSENT = "absent"


class Writer:
    """Every mutation of the host goes through here, so a test can make the k-th one fail."""

    def write(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".kaelen-tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    def delete(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    def rmdir(self, path: Path) -> None:
        path.rmdir()

    def mkdir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def move(self, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)


def encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


# --- operation record --------------------------------------------------------------------------


def where(op: dict) -> homes.Home:
    return homes.from_record(op)


def copies_dir(host: Path, op: dict) -> Path:
    if op.get("copies_dir"):  # the main Kaelen's part names its own (specs/027 R-4)
        return host / op["copies_dir"]
    return host / where(op).copies


def load_record(host: Path, capability: str) -> dict | None:
    """The capability's operation record: in its home, else in the old layout (specs/026 R-5)."""
    found = homes.find(host, capability)
    candidates = ([found] if found is not None else []) + [homes.old(capability)]
    for place in candidates:
        path = host / place.record
        if not path.is_file():
            continue
        try:
            op = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(op, dict):
                raise ValueError("not an object")
        except (OSError, ValueError):
            op = {
                "schema": SCHEMA,
                "operation": "unknown",
                "capability": capability,
                "broken": True,
            }
            if not place.legacy:
                op["home"] = place.root
        else:
            if place.legacy:
                op.pop("home", None)
        return op
    return None


def save_record(host: Path, op: dict, writer: Writer) -> None:
    place = where(op)
    if place.legacy:
        ignore = host / homes.OLD_OPERATIONS / ".gitignore"
        if not ignore.is_file():
            writer.write(ignore, b"*\n")
        writer.write(host / place.record, (json.dumps(op, indent=2) + "\n").encode("utf-8"))
        return
    # the record is the first write of an operation: whatever stops after it, it describes
    writer.write(host / place.record, (json.dumps(op, indent=2) + "\n").encode("utf-8"))
    if ignore_state(host, place.ignore) in ("absent", "old"):
        writer.write(host / place.ignore, homes.IGNORE_BYTES)


def ignore_state(host: Path, rel: str | None) -> str:
    """The home's ignore file: absent, current, old (an earlier engine's bytes) or edited."""
    if rel is None or not (host / rel).is_file():
        return "absent"
    data = (host / rel).read_bytes()
    if data == homes.IGNORE_BYTES:
        return "current"
    return "old" if data == homes.OLD_IGNORE_BYTES else "edited"


def drop_record(host: Path, op: dict, writer: Writer) -> None:
    """Remove the record and its copies; an emptied home goes with them (R-9; specs/026 R-1)."""
    place = where(op)
    if place.legacy:
        directory = host / homes.OLD_OPERATIONS
        capability = op["capability"]
        others = (
            [p for p in directory.glob("*.json") if p.stem != capability]
            if directory.is_dir()
            else []
        )
        if others:
            writer.delete(host / place.record)
            if (host / place.copies).exists():
                writer.delete(host / place.copies)
        else:
            writer.delete(directory)
        return
    writer.delete(host / place.record)
    if (host / place.copies).exists():
        writer.delete(host / place.copies)
    if not (host / place.registry).is_file() and (host / place.ignore).is_file():
        writer.delete(host / place.ignore)
    _prune_home(host, place, op.get("home_created") or [], writer)


def _prune_home(host: Path, place: homes.Home, created: list[str], writer: Writer) -> None:
    """The home and `.<node>/kaelen/` when empty; `.<node>/` only if the engine created it."""
    node_dir = place.root.split("/")[0]
    candidates = {place.root, f"{node_dir}/{homes.KAELEN}", *created}
    for rel in sorted(candidates, key=lambda r: r.count("/"), reverse=True):
        path = host / rel
        if rel == node_dir and rel not in created:
            continue
        if path.is_dir() and not any(path.iterdir()):
            writer.rmdir(path)


def tidy(host: Path, writer: Writer) -> None:
    """Empty Kaelen directories left by an operation that stopped after its record was gone."""
    directory = host / homes.OLD_OPERATIONS
    if directory.is_dir() and not list(directory.glob("*.json")):
        writer.delete(directory)
    elif directory.is_dir():
        for orphan in sorted(directory.glob("*.pre")):
            if not (directory / (orphan.name[: -len(".pre")] + ".json")).is_file():
                writer.delete(orphan)
    _tidy_parts(host, writer)
    # the old layout's shared folders, once a migration or an old engine has emptied them
    for rel in (homes.OLD_REGISTRY, homes.OLD_RUNTIMES, homes.OLD_CAPABILITIES, ".kaelen"):
        path = host / rel
        if rel == homes.OLD_CAPABILITIES and path.is_dir():
            for sub in sorted(path.rglob("*"), key=lambda q: len(q.parts), reverse=True):
                if sub.is_dir() and not any(sub.iterdir()):
                    writer.rmdir(sub)
        if rel == homes.OLD_RUNTIMES and path.is_dir():
            if [q.name for q in path.iterdir()] == [".gitignore"]:
                writer.delete(path / ".gitignore")
        if path.is_dir() and not any(path.iterdir()):
            writer.rmdir(path)
    for top in sorted(p for p in host.iterdir() if p.name.startswith(".") and p.is_dir()):
        base = top / homes.KAELEN
        if not base.is_dir() or top.name == ".git":
            continue
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            if (folder / homes.RECORD).is_file():
                continue
            for leftover in (homes.COPIES, homes.STAGING):
                if (folder / leftover).exists():
                    writer.delete(folder / leftover)
            if (folder / homes.REGISTRY).is_file():
                continue
            # a home with neither record nor registry is what a stopped operation left behind
            for sub in sorted(folder.rglob("*"), key=lambda q: len(q.parts), reverse=True):
                if sub.is_dir() and not any(sub.iterdir()):
                    writer.rmdir(sub)
            if [q.name for q in folder.iterdir()] == [homes.IGNORE]:
                writer.delete(folder / homes.IGNORE)
            if not any(folder.iterdir()):
                writer.rmdir(folder)
        if not any(base.iterdir()):
            writer.rmdir(base)


def _tidy_parts(host: Path, writer: Writer) -> None:
    """Parts of the main Kaelen whose capability operation has ended: what a release that stopped
    left behind (specs/027 R-7). A part still serving a pending operation is kept."""
    folder = host / homes.CONTRIBUTIONS
    if not folder.is_dir():
        return
    for part in sorted(folder.glob("*.json")):
        try:
            serves = json.loads(part.read_text(encoding="utf-8")).get("serves")
        except (OSError, ValueError, AttributeError):
            continue  # unreadable: reported by verify, never removed blind
        record = load_record(host, part.stem)
        if record is None or record.get("id") != serves:
            writer.delete(part)
    for pre in sorted(folder.glob("*.pre")):
        if not (folder / (pre.name[: -len(".pre")] + ".json")).is_file():
            writer.delete(pre)
    if [p.name for p in folder.iterdir()] in ([], [".gitignore"]):
        writer.delete(folder)


# --- actions ------------------------------------------------------------------------------------


TEXT_OPS = (
    "section-add",
    "section-replace",
    "section-remove",
    "member-add",
    "member-replace",
    "member-remove",
    "element-add",
    "element-remove",
    "settings-add",
    "settings-remove",
)


def transform(text: str | None, action: dict) -> tuple[str | None, dict]:
    """The new text of a shared file after `action`, and what the registry must remember.

    Pure: the same function plans (on text in memory) and applies (on the host's file).
    `None` means the file is to be deleted.
    """
    op = action["op"]
    if op == "section-add":
        style = STYLES[action["style"]]
        current = text or ""
        if sections.body(current, action["address"], style) is not None:
            return current, action.get("result", {})
        out, info = sections.append(current, action["address"], action["content"], style)
        return out, {"inserted": {"separator": info["separator"]}}
    if op == "section-replace":
        style = STYLES[action["style"]]
        current = text or ""
        if sections.body(current, action["address"], style) is None:
            out, info = sections.append(current, action["address"], action["content"], style)
            return out, {"inserted": {"separator": info["separator"]}}
        return sections.replace_body(current, action["address"], style, action["content"]), {}
    if op == "member-add":
        current = text or ""
        path = [*action["json_path"], action["json_key"]]
        if current.strip() and jsonspan.value_text(current, path) is not None:
            return current, action.get("result", {})
        out, info = jsonspan.add_member(
            current, action["json_path"], action["json_key"], action["content"]
        )
        return out, {"inserted": {k: info[k] for k in ("created", "inner_before") if k in info}}
    if op == "member-replace":
        path = [*action["json_path"], action["json_key"]]
        return jsonspan.replace_value(text, path, action["content"]), {}
    if op == "element-add":
        current = text or ""
        identity = element_identity(action["address"])
        if current.strip() and jsonspan.find_element(current, action["json_path"], identity):
            return current, action.get("result", {})
        out, info = jsonspan.append_element(current, action["json_path"], action["content"])
        return out, {"inserted": {k: info[k] for k in ("created", "inner_before") if k in info}}
    if op == "settings-add":
        out, info = settingsfile.add(
            text or "", action["capability"], [tuple(p) for p in action["content"]]
        )
        return out, {"separator": info["separator"], "added": info["added"]}
    if text is None:
        return None, {}
    if op == "section-remove":
        separator = (action.get("inserted") or {}).get("separator", "")
        out = sections.remove(text, action["address"], STYLES[action["style"]], separator)
    elif op == "member-remove":
        inserted = action.get("inserted") or {}
        out = jsonspan.remove_member(
            text, action["json_path"], action["json_key"], inserted.get("inner_before")
        )
        out = _prune(out, inserted, action)
    elif op == "element-remove":
        inserted = action.get("inserted") or {}
        identity = element_identity(action["address"])
        out = jsonspan.remove_element(
            text, action["json_path"], identity, inserted.get("inner_before")
        )
        out = _prune(out, inserted, action)
    elif op == "settings-remove":
        out = text
        for key in action["content"]:
            out = settingsfile.remove(
                out, action["capability"], key["name"], key["digest"], action.get("separator", "")
            )
    else:
        raise ValueError(f"unknown action {op!r}")
    created = action.get("created_file", False)
    empty = not out.strip() or (
        action.get("style", "").startswith("json") and jsonspan.is_skeleton(out)
    )
    if created and empty and not action.get("claimed_by_others"):
        return None, {}
    return out, {}


def precompute(host: Path, actions: list[dict]) -> None:
    """Simulate the text actions in order and store each one's result in the action.

    An action applied but not yet marked done when an operation stopped is found already applied
    on the next run; its result (separators, created parents) must not depend on that run (R-9).
    """
    texts: dict[str, str | None] = {}
    for action in actions:
        if action["op"] not in TEXT_OPS:
            continue
        rel = action["path"]
        if rel not in texts:
            texts[rel] = read_text(host, rel)
        out, info = transform(texts[rel], action)
        texts[rel] = out
        action["result"] = info


def execute(host: Path, action: dict, writer: Writer) -> dict:
    """Apply one action; returns what the registry must remember about it (e.g. separators)."""
    op, rel = action["op"], action["path"]
    target = host / rel
    if op == "write":
        if action["form"] == "directory":
            writer.delete(target)
            for name, data in action["content"]:
                writer.write(target / name, decode(data))
        else:
            if target.is_dir():
                writer.delete(target)
            writer.write(target, decode(action["content"]))
        return {}
    if op == "delete":
        writer.delete(target)
        return {}
    text = read_text(host, rel)
    out, info = transform(text, action)
    if out is None:
        writer.delete(target)
    elif out != text:
        writer.write(target, out.encode("utf-8"))
    return action.get("result", info) if "result" in action else info


def _prune(text: str, inserted: dict, action: dict) -> str:
    paths = list(inserted.get("created") or []) + list(action.get("inherited_created") or [])
    for path in sorted({tuple(p) for p in paths}, key=len, reverse=True):
        text = jsonspan.prune_empty(text, list(path))
    return text


def engines_from(op: dict) -> int:
    """Where the trailing removals of engines begin: the main Kaelen and the capability's deposit
    go after the registry, so that no interruption leaves a registry without an engine on the
    host to finish or roll back its operation (specs/026 FR-011)."""
    engines = {homes.MAIN, homes.CONTRIBUTIONS, where(op).package}
    actions = op["actions"]
    start = len(actions)
    while start and actions[start - 1]["op"] == "delete" and actions[start - 1]["path"] in engines:
        start -= 1
    return start


class ContributionFailed(OSError):
    """The main Kaelen did not apply the operation's contributions (specs/027)."""

    def __init__(self, message: str, path: str = "", rule: str | None = None):
        super().__init__(message, path)
        self.message, self.filename, self.rule = message, path, rule

    def __str__(self) -> str:
        return self.message


class ReleaseFailed(ContributionFailed):
    """The operation ended, but the main Kaelen's part was not dropped: the next tidy drops it."""


def apply(
    host: Path, op: dict, writer: Writer, builder=None, *, last: bool = False, runner=None
) -> dict:
    """Apply the operation's actions not yet done, the engines' removals only when `last`;
    returns the results by action index.

    Text actions on shared files are not applied here: the `contribute` action hands them to the
    host's main Kaelen, which applies them all or none (specs/027 R-2).
    """
    results = {int(k): v for k, v in (op.get("results") or {}).items()}
    done = set(op.get("done", []))
    start = engines_from(op)
    for index, action in enumerate(op["actions"]):
        if index in done or (index >= start) != last or action.get("via") == "contribute":
            continue
        if action["op"] == "contribute":
            results.update(contribute(host, op, action, writer, runner))
            done |= {index, *action["indices"]}
            op["done"] = sorted(done)
            op["results"] = {str(k): v for k, v in sorted(results.items())}
            save_record(host, op, writer)
            continue
        if action["op"] == "runtime":
            results[index] = execute_runtime(host, op, action, writer, builder)
        else:
            ensure_copy(host, op, action["path"], intended_digest(host, action), writer)
            results[index] = execute(host, action, writer)
        op["done"] = sorted({*done, index})
        done = set(op["done"])
        op["results"] = {str(k): v for k, v in sorted(results.items())}
        save_record(host, op, writer)
    return results


def runner_for(host: Path, runner=None, engine: str | None = None):
    """Who answers for the main Kaelen: its own process when it is on the host, else this engine
    (a host without one, e.g. an old-layout capability uninstalled), at its own version."""
    from kaelen.host import contributions

    if contributions.main_run(host).is_file():
        return runner or contributions.DEFAULT_RUNNER
    return contributions.InProcess(engine or contributions.MINIMUM)


def contribute(host: Path, op: dict, action: dict, writer: Writer, runner=None) -> dict:
    """Hand the set to the main Kaelen and return its results by action index (specs/027 R-2)."""
    from kaelen.host import contributions

    if "copies_from" not in action:  # what is copied from here on goes back before the main part
        action["copies_from"] = len(op.get("copies", []))
        save_record(host, op, writer)
    request = {"mode": "apply", "set": contributions.build_set(op, action, action["engine"])}
    ask = runner_for(host, runner, action["engine"])
    doc = ask(contributions.main_run(host), host, request, writer)
    if doc.get("verdict") != "contributed":
        error = (doc.get("errors") or [{}])[0]
        raise ContributionFailed(
            f"the main Kaelen did not apply the contributions ({doc.get('verdict')}): "
            + str(error.get("message", "")),
            str(error.get("path", "")),
            error.get("rule"),
        )
    return {int(k): v for k, v in (doc.get("results") or {}).items()}


def release(host: Path, op: dict, writer: Writer, runner=None) -> None:
    """Drop the main Kaelen's part once the operation ended (specs/027 R-7).

    A release that stops raises `ReleaseFailed`: the operation is over, and the part it leaves is
    an orphan the next operation's `tidy` removes.
    """
    from kaelen.host import contributions

    action = next((a for a in op["actions"] if a["op"] == "contribute"), None)
    if action is None:
        return
    part = contributions.part_path(op["capability"])
    if not (host / part).is_file():
        return
    request = {"mode": "release", "capability": op["capability"], "serves": op.get("id")}
    try:
        doc = runner_for(host, runner, action.get("engine"))(
            contributions.main_run(host), host, request, writer
        )
    except OSError as exc:
        raise ReleaseFailed(f"the main Kaelen's part was not released: {exc}", part) from exc
    if doc.get("verdict") not in ("released", "nothing-to-release"):
        raise ReleaseFailed(f"the main Kaelen's part was not released ({doc.get('verdict')})", part)


def finish(host: Path, op: dict, writer: Writer, runner=None) -> None:
    """Write (or remove) the registry, remove the engines it no longer needs, prune the directories
    the engine created, drop the record.

    The old-layout paths a migration leaves (`legacy`) are deleted, with copies first (specs/026
    R-6).
    """
    after = op.get("registry_after")
    place = where(op)
    reg_rel = op.get("registry") or place.registry
    if after is not None:
        _remember(after, op)
        ensure_copy(host, op, reg_rel, bytes_digest(registry.serialise(after)), writer)
        writer.write(host / reg_rel, registry.serialise(after))
    else:
        ensure_copy(host, op, reg_rel, ABSENT, writer)
        writer.delete(host / reg_rel)
    for rel in op.get("legacy") or []:
        if rel != reg_rel and (host / rel).exists():
            ensure_copy(host, op, rel, ABSENT, writer)
            writer.delete(host / rel)
    old_dir = host / homes.OLD_REGISTRY
    if old_dir.is_dir() and not any(old_dir.iterdir()):
        writer.rmdir(old_dir)
    prune = sorted(op.get("prune_dirs") or [], key=lambda r: r.count("/"), reverse=True)
    for rel in prune:
        path = host / rel
        if path.is_dir() and not any(path.iterdir()):
            writer.rmdir(path)
    apply(host, op, writer, last=True, runner=runner)
    drop_record(host, op, writer)
    # the home held the record until now: what it kept from emptying goes after it
    for rel in prune:
        path = host / rel
        if path.is_dir() and not any(path.iterdir()):
            writer.rmdir(path)
    release(host, op, writer, runner)
    tidy(host, writer)


def _remember(after: dict, op: dict) -> None:
    """Carry what the actions learnt (separators, created parents) into the registry."""
    results = op.get("results") or {}
    by_key = {(loc["path"], loc.get("address") or ""): loc for loc in after.get("locations", [])}
    for index, action in enumerate(op["actions"]):
        result = results.get(str(index)) or {}
        if "inserted" in result and action.get("entry"):
            loc = by_key.get(tuple(action["entry"]))
            if loc is not None:
                loc["inserted"] = result["inserted"]
        if action["op"] == "settings-add" and result.get("separator") and after.get("settings"):
            if not after["settings"].get("separator"):
                after["settings"]["separator"] = result["separator"]


# --- copies of prior states (specs/021) --------------------------------------------------------


def bytes_digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def tree_digest(files: list[tuple[str, bytes]]) -> str:
    listing = [[name, bytes_digest(data)] for name, data in sorted(files)]
    return "tree:" + bytes_digest(json.dumps(listing).encode("utf-8"))


def location_digest(host: Path, rel: str) -> str:
    """What a location holds now: a file's bytes, a directory's files, or absent (R-3).

    A built environment is known by its stamp, written last (specs/022 research R-6).
    """
    path = host / rel
    if homes.is_runtime(rel):
        stamp = path / runtime.STAMP
        if stamp.is_file():
            return bytes_digest(stamp.read_bytes())
        return "unstamped" if path.exists() else ABSENT
    if path.is_file():
        return bytes_digest(path.read_bytes())
    if path.is_dir():
        return tree_digest(read_tree(path))
    return ABSENT


def intended_digest(host: Path, action: dict) -> str:
    """The digest the action's location will hold once the action is applied (R-2)."""
    op = action["op"]
    if op == "write":
        if action["form"] == "directory":
            return tree_digest([(name, decode(data)) for name, data in action["content"]])
        return bytes_digest(decode(action["content"]))
    if op == "delete":
        return ABSENT
    out, _ = transform(read_text(host, action["path"]), action)
    return ABSENT if out is None else bytes_digest(out.encode("utf-8"))


def ensure_copy(host: Path, op: dict, rel: str, intended: str, writer: Writer, save=None) -> None:
    """Keep the prior state of `rel` once, accept `intended`; durable before the write (R-2).

    `save` persists the record that lists the copies: the capability's by default, or the main
    Kaelen's part (specs/027 R-4).
    """
    save = save or save_record
    if op.get("schema") != SCHEMA and not op.get("copies_dir"):
        return  # an operation started by an older engine is completed without copies
    copies = op.setdefault("copies", [])
    entry = next((c for c in copies if c["path"] == rel), None)
    if entry is not None and intended in entry["accepted"]:
        return
    if entry is None:
        path = host / rel
        n = len(copies)
        target = copies_dir(host, op) / str(n)
        if homes.is_runtime(rel) and path.exists():
            # an environment is moved aside, not copied: recorded first, then moved
            before = location_digest(host, rel)
            entry = {
                "path": rel,
                "n": n,
                "state": "directory",
                "moved": True,
                "digest_before": before,
                "accepted": [before, ABSENT, intended],
                "created_ancestors": [],
            }
            copies.append(entry)
            save(host, op, writer)
            writer.move(path, target)
            return
        if path.is_file():
            state = "file"
            writer.write(target, path.read_bytes())
        elif path.is_dir():
            state = "directory"
            files = read_tree(path)
            for name, data in files:
                writer.write(target / name, data)
            if not files:
                writer.mkdir(target)
        else:
            state = ABSENT
        before = location_digest(host, rel)
        entry = {
            "path": rel,
            "n": n,
            "state": state,
            "digest_before": before,
            "accepted": [before],
            "created_ancestors": _absent_ancestors(host, rel) if state == ABSENT else [],
        }
        copies.append(entry)
    if intended not in entry["accepted"]:
        entry["accepted"].append(intended)
    save(host, op, writer)


def _absent_ancestors(host: Path, rel: str) -> list[str]:
    parts = rel.split("/")[:-1]
    return [
        "/".join(parts[:i])
        for i in range(1, len(parts) + 1)
        if not (host / "/".join(parts[:i])).exists()
    ]


def rollback_problem(host: Path, op: dict) -> str | None:
    """Why this record cannot be rolled back, or None when it can (FR-015)."""
    if op.get("broken"):
        return "the operation record cannot be read"
    if op.get("schema") != SCHEMA or "copies" not in op:
        return "the interrupted operation has no copies (started by an older engine)"
    copied = {c["path"] for c in op["copies"]}
    for index in op.get("done", []):
        action = op["actions"][index]
        if action["op"] == "contribute" or action.get("via") == "contribute":
            continue  # the main Kaelen's part keeps these copies (specs/027 R-8)
        rel = action["path"]
        if rel not in copied:
            return f"no copy of {rel}"
    base = copies_dir(host, op)
    for entry in op["copies"]:
        data = base / str(entry["n"])
        if entry["state"] == "file" and not data.is_file():
            return f"the copy of {entry['path']} is missing"
        moved_back = entry.get("moved") and (
            location_digest(host, entry["path"]) == entry["digest_before"]
        )
        if entry["state"] == "directory" and not data.is_dir() and not moved_back:
            return f"the copy of {entry['path']} is missing"
    return None


def in_flight(op: dict) -> str | None:
    """The location of the first action not done, when that action writes in several steps."""
    done = set(op.get("done", []))
    for index, action in enumerate(op["actions"]):
        if index not in done and action.get("via") != "contribute":
            return action["path"] if action["op"] == "write" else None
    return None


def restore(host: Path, op: dict, entry: dict, writer: Writer) -> bool:
    """Put one location back to its prior state; False when it already is (idempotent resume)."""
    rel = entry["path"]
    if location_digest(host, rel) == entry["digest_before"]:
        return False
    target = host / rel
    data = copies_dir(host, op) / str(entry["n"])
    if entry["state"] == ABSENT:
        writer.delete(target)
    elif entry.get("moved"):
        if target.exists():
            writer.delete(target)
        writer.move(data, target)
    elif entry["state"] == "file":
        if target.is_dir():
            writer.delete(target)
        writer.write(target, data.read_bytes())
    else:
        if target.exists():
            writer.delete(target)
        files = read_tree(data)
        for name, content in files:
            writer.write(target / name, content)
        if not files:
            writer.mkdir(target)
    return True


def remove_created(host: Path, op: dict, writer: Writer) -> None:
    """Remove the directories the operation created that are left empty, deepest first (R-5)."""
    created = {a for c in op.get("copies", []) for a in c.get("created_ancestors", [])}
    for rel in sorted(created, key=lambda r: r.count("/"), reverse=True):
        path = host / rel
        if path.is_dir() and not any(path.iterdir()):
            writer.rmdir(path)


def execute_runtime(host: Path, op: dict, action: dict, writer: Writer, builder) -> dict:
    """Build beside, move the old environment into the copies, move the new one in (R-6)."""
    builder = builder or runtime.ToolBuilder()
    capability = op["capability"]
    place = where(op)
    staging = host / place.staging
    if staging.exists():
        writer.delete(staging)
    tool = builder.tool()
    stamp = runtime.stamp_bytes(capability, action["digest"], tool, runtime.python_label())
    code = [(rel, decode(data)) for rel, data in action["code"]]
    builder.build(staging, decode(action["lock"]), code, stamp)
    if place.legacy and not (host / runtime.OLD_IGNORE).is_file():
        ensure_copy(host, op, runtime.OLD_IGNORE, bytes_digest(b"*\n"), writer)
        writer.write(host / runtime.OLD_IGNORE, b"*\n")
    ensure_copy(host, op, action["path"], bytes_digest(stamp), writer)
    target = host / action["path"]
    if target.exists():
        writer.delete(target)
    writer.move(staging, target)
    return {"tool": tool, "python": runtime.python_label()}
