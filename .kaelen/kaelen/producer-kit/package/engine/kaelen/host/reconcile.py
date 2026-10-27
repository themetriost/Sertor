"""The one reconciliation behind install, update and uninstall (specs/017 research R-3, FR-019).

Desired state (from the package) against the capability's registry and the host's bytes gives a
plan: actions to apply, decisions that need the operator's per-file consent, refusals, findings,
and the registry to write afterwards. Install is the case with no registry yet; uninstall is the
case with nothing desired for the targets in scope. Nothing here writes.
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field
from pathlib import Path

from kaelen.host import home as homes
from kaelen.host import runtime, sections, settingsfile
from kaelen.host.apply import encode
from kaelen.host.desired import Placement, desired
from kaelen.host.jsonspan import Unmergeable
from kaelen.host.registry import SCHEMA as REGISTRY_SCHEMA
from kaelen.host.state import observe, read_text
from kaelen.outcome import Problem


@dataclass
class Decision:
    """A conflict (not ours) or divergence (ours, modified by the host) awaiting consent."""

    kind: str  # conflict | divergence
    path: str
    address: str | None
    found: str  # identical | different
    digest_found: str
    on_yes: list[dict]  # actions applied with consent
    entry_yes: dict | None  # registry entry with consent
    entry_no: dict | None  # registry entry without consent (divergence kept)
    previous: str | None = None  # adopt | retire: a declared previous location (specs/024)

    @property
    def label(self) -> str:
        return self.path + (
            f" @ {self.address}" if self.address and "[" not in self.address else ""
        )


@dataclass
class Plan:
    actions: list[dict] = field(default_factory=list)
    entries: list[dict] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    refusals: list[Problem] = field(default_factory=list)
    findings: list[Problem] = field(default_factory=list)
    unsupported: list[dict] = field(default_factory=list)
    settings: list[dict] = field(default_factory=list)  # [{name, description, state}]
    registry_after: dict | None = None
    prune_dirs: list[str] = field(default_factory=list)
    final_targets: list[str] = field(default_factory=list)
    settings_record: dict | None = None
    replaced: list[dict] = field(default_factory=list)
    previous: list[dict] = field(default_factory=list)  # [{path, member, result}] (specs/024)


def _loc_key(loc: dict) -> tuple[str, str]:
    return (loc["path"], loc.get("address") or "")


def _entry(p: Placement) -> dict:
    entry = {
        "path": p.path,
        "form": p.form,
        "ownership": p.ownership,
        "item": dict(p.item),
        "targets": list(p.targets),
        "wrapper": p.wrapper,
        "digest": p.digest,
    }
    if p.style:
        entry["style"] = p.style
    if p.address:
        entry["address"] = p.address
    if p.json_path is not None:
        entry["json_path"] = list(p.json_path)
    if p.json_key is not None:
        entry["json_key"] = p.json_key
    return entry


def _encoded(p: Placement):
    if p.form == "directory":
        return [[name, encode(data)] for name, data in p.content]
    if p.style:
        return p.content
    return encode(p.content)


def _add_action(p: Placement, replace: bool) -> dict:
    if p.ownership == "owned" or p.style is None:
        op = "write"
    elif p.style in ("markdown", "hash"):
        op = "section-replace" if replace else "section-add"
    elif p.style == "json-member":
        op = "member-replace" if replace else "member-add"
    else:
        op = "element-add"
    action = {
        "op": op,
        "path": p.path,
        "form": p.form,
        "content": _encoded(p),
        "entry": list(p.key),
    }
    for name in ("style", "address", "json_path", "json_key"):
        value = getattr(p, name)
        if value is not None:
            action[name] = value
    return action


def _remove_action(loc: dict, created_file: bool, claimed: bool) -> dict:
    style = loc.get("style")
    if loc["ownership"] == "owned" or style is None:
        return {"op": "delete", "path": loc["path"], "form": loc.get("form", "file")}
    op = {
        "markdown": "section-remove",
        "hash": "section-remove",
        "json-member": "member-remove",
    }.get(style, "element-remove")
    action = {
        "op": op,
        "path": loc["path"],
        "style": style,
        "address": loc.get("address"),
        "inserted": loc.get("inserted") or {},
        "created_file": created_file,
        "claimed_by_others": claimed,
    }
    for name in ("json_path", "json_key", "inherited_created"):
        if name in loc:
            action[name] = loc[name]
    return action


def _retire(host, previous, matched, keys, owned, claimed_file, out: Plan, removes) -> None:
    """Declared previous locations the capability no longer installs (specs/024 D-3)."""
    for (path, member), prev in sorted(previous.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        if (path, member) in matched:
            continue
        if member is None:
            loc = {
                "path": path,
                "ownership": "owned",
                "form": "directory" if (host / path).is_dir() else "file",
            }
            key = (path, "")
        else:
            parts = member.split(".")
            loc = {
                "path": path,
                "ownership": "section",
                "style": "json-member",
                "address": member,
                "json_path": parts[:-1],
                "json_key": parts[-1],
                "inserted": {},
            }
            key = (path, member)
        other = _claimed_by(path, key, keys, owned)
        report = {"path": path, "member": member}
        if other is not None:
            out.findings.append(
                Problem("previous-claimed", path, f"{path}: installed by {other!r}; not retired")
            )
            out.previous.append({**report, "result": "claimed-by-other"})
            continue
        found = observe(host, loc)
        if found is None:
            out.previous.append({**report, "result": "absent"})
            continue
        action = _remove_action(loc, False, claimed_file(path))
        if found in prev.get("digests", ()):
            removes.append(action)
            out.previous.append({**report, "result": "retired"})
        else:
            out.decisions.append(
                Decision(
                    "divergence",
                    path,
                    member,
                    "different",
                    found,
                    [action],
                    None,
                    None,
                    "retire",
                )
            )


def _runtime_action(p: Placement, capability: str) -> dict:
    """Build the environment from its recipe (specs/022 research R-6)."""
    recipe = p.content
    return {
        "op": "runtime",
        "path": p.path,
        "form": "runtime",
        "capability": capability,
        "digest": p.digest,
        "lock": encode(recipe["lock"]),
        "code": [[rel, encode(data)] for rel, data in recipe["code"]],
        "dependencies": len(runtime.parse_lock(recipe["lock"].decode("utf-8"))[0]),
        "entry": list(p.key),
    }


def _other_runtimes(others: list[dict]) -> bool:
    """Another capability's environment still in the old shared folder (specs/026 R-6)."""
    return any(
        isinstance(loc, dict)
        and loc.get("form") == "runtime"
        and str(loc.get("path", "")).startswith(homes.OLD_RUNTIMES + "/")
        for reg in others
        for loc in reg.get("locations", [])
    )


# Which item kinds may sit at which reserved name of a capability's home (specs/026 FR-007).
_RESERVED_FOR = {
    homes.PACKAGE: ("package",),
    homes.RUNTIME: ("runtime",),
    homes.LAUNCHER: ("runtime",),
    homes.ENGINE: ("engine",),
    homes.HOOKS: ("hook",),
}


def _reserved(p: Placement, root: str) -> str | None:
    """The reserved name of the home that `p` would take, if it is not its own."""
    if not p.path.startswith(root + "/"):
        return None
    first = p.path[len(root) + 1 :].split("/")[0]
    if first not in (*homes.RESERVED, homes.HOOKS):
        return None
    return None if p.item["kind"] in _RESERVED_FOR.get(first, ()) else first


def _inherited_parents(p: Placement, others: list[dict]) -> list[list[str]]:
    """JSON containers on our path that another capability created: ours to prune if emptied.

    Without this, the capability that created `hooks.<Event>` could be removed first, and the one
    removed last would leave the empty container behind (FR-037, FR-045).
    """
    if p.json_path is None:
        return []
    found = set()
    for reg in others:
        for loc in reg.get("locations", []):
            if not isinstance(loc, dict) or loc.get("path") != p.path:
                continue
            created = list((loc.get("inserted") or {}).get("created") or [])
            created += list(loc.get("inherited_created") or [])
            for path in created:
                if isinstance(path, list) and p.json_path[: len(path)] == path:
                    found.add(tuple(path))
    return [list(path) for path in sorted(found)]


def _ancestors(rel: str) -> list[str]:
    parts = rel.split("/")[:-1]
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def _git_notes(host: Path, p: Placement) -> list[Problem]:
    """What a section may do to the operator's own lines (specs/025 R-6, D-4, D-5): notes only.

    The host's lines are those outside every hash-marked section; git reads the file top down and
    a later line prevails, so the section, appended last, may override one of them.
    """
    path = host / p.path
    try:
        text = path.read_bytes().decode("utf-8") if path.is_file() else ""
        spans = sorted(sections.find_all(text, sections.HASH).values(), key=lambda s: s.start)
    except (UnicodeDecodeError, Unmergeable):
        return []  # the write refuses the file and says why
    own, pos = [], 0
    for span in [*spans, None]:
        chunk = text[pos : span.start if span else len(text)]
        own += [line for line in chunk.replace("\r\n", "\n").split("\n") if line.strip()]
        pos = span.end if span else pos
    ours = [line for line in p.content.split("\n") if line.strip()]
    notes = [
        Problem(
            "git-line-present",
            p.path,
            f"{p.path}: {line!r} is already among the host's own lines; written in "
            f"{p.address} too, so it stays when the capability goes",
        )
        for line in ours
        if line in own
    ]
    if p.path.rsplit("/", 1)[-1] == ".gitattributes":
        patterns = {line.split()[0]: line for line in own if not line.startswith("#")}
        notes += [
            Problem(
                "git-later-prevails",
                p.path,
                f"{p.path}: {line!r} in {p.address} comes after the host's "
                f"{patterns[line.split()[0]]!r}; for git the later line's attributes prevail",
            )
            for line in ours
            if not line.startswith("#") and line.split()[0] in patterns and line not in own
        ]
    elif any(line.startswith("!") for line in ours):
        notes.append(
            Problem(
                "git-later-prevails",
                p.path,
                f"{p.path}: {p.address} re-includes paths with '!' after the host's own lines; "
                "for git the later line prevails",
            )
        )
    return notes


def _claims(others: list[dict]) -> tuple[dict, dict, set, set]:
    """Locations, shared-file origins and created directories recorded by other capabilities."""
    keys, owned = {}, {}
    created_files, created_dirs = set(), set()
    for reg in others:
        for loc in reg.get("locations", []):
            if not isinstance(loc, dict) or "path" not in loc:
                continue
            keys[_loc_key(loc)] = reg["capability"]
            if loc.get("ownership") == "owned":
                owned[loc["path"]] = reg["capability"]
        for shared in reg.get("shared_files", []) or []:
            if isinstance(shared, dict) and shared.get("existed_before") is False:
                created_files.add(shared.get("path"))
        created_dirs.update(d for d in reg.get("created_dirs", []) or [] if isinstance(d, str))
    return keys, owned, created_files, created_dirs


def _claimed_by(p_path: str, key, keys: dict, owned: dict) -> str | None:
    if key in keys:
        return keys[key]
    for path, cap in owned.items():
        if p_path == path or p_path.startswith(path + "/") or path.startswith(p_path + "/"):
            return cap
    return None


def plan(
    verb: str,
    host: Path,
    pkg,
    scope: list[str],
    reg: dict | None,
    others: list[dict],
    engine: dict,
    rule_digest: str,
) -> Plan:
    out = Plan()
    document = pkg.document
    capability = document["capability"]
    recorded = {_loc_key(loc): loc for loc in (reg or {}).get("locations", [])}
    rec_targets = list((reg or {}).get("targets", []))
    order = list(document["targets"])
    if verb == "install":
        final = [t for t in order if t in set(rec_targets) | set(scope)]
        acting = set(final)
    elif verb == "update":
        final = [t for t in order if t in rec_targets] + [t for t in rec_targets if t not in order]
        acting = set(scope or rec_targets)
    else:
        final = [t for t in rec_targets if scope and t not in scope]
        acting = set(scope or rec_targets)
    out.final_targets = final
    keys, owned, inherited_files, inherited_dirs = _claims(others)

    def claimed_file(path: str) -> bool:
        return any(k[0] == path for k in keys)

    placements: list[Placement] = []
    if verb in ("install", "update"):
        placements, out.unsupported, findings = desired(pkg, [t for t in final if t in order])
        out.findings.extend(findings)
    wanted: dict[tuple[str, str], Placement] = {}
    for p in placements:
        if verb == "install" or acting & set(p.targets):
            wanted[p.key] = p
    # Recorded locations this operation leaves alone (narrowed update/uninstall).
    for key, loc in recorded.items():
        stays = [t for t in loc.get("targets", []) if t in final]
        untouched = not acting & set(loc.get("targets", []))
        if verb == "uninstall" and stays:
            out.entries.append({**loc, "targets": stays})
        elif untouched and key not in wanted:
            out.entries.append(loc)

    shared_before = {s["path"]: s for s in (reg or {}).get("shared_files", []) or []}

    def existed_before(path: str) -> bool:
        if path in shared_before:
            return bool(shared_before[path].get("existed_before"))
        if path in inherited_files:
            return False
        return (host / path).exists()

    removes, adds = [], []
    previous = {(p["path"], p.get("member")): p for p in document.get("previous", ())}
    # a previous location the capability installs now is adopted, never retired
    matched = {(p.path, p.address if p.style == "json-member" else None) for p in wanted.values()}

    def earlier(p: Placement):
        return previous.get((p.path, p.address if p.style == "json-member" else None))

    root = homes.new(document["node"], capability).root
    for key, p in sorted(wanted.items()):
        if p.path == homes.TRUST or p.path.startswith(homes.TRUST + "/"):
            out.refusals.append(
                Problem(
                    "reserved-location",
                    p.path,
                    f"{p.item['kind']} {p.item['name']!r} would be placed in {homes.TRUST}/, which "
                    "only the operator changes, with `kaelen trust` (specs/028 FR-024)",
                )
            )
            del wanted[key]
    for key, p in sorted(wanted.items()):
        name = _reserved(p, root)
        if name is not None:
            out.refusals.append(
                Problem(
                    "reserved-name",
                    p.path,
                    f"{p.item['kind']} {p.item['name']!r} would be placed at {p.path}, a name the "
                    f"engine keeps for itself in the capability's folder ({name})",
                )
            )
            del wanted[key]
    for key, p in sorted(wanted.items()):
        if p.wrapper != "git-section":
            continue
        inside = next(
            (
                q
                for q in wanted.values()
                if q.ownership == "owned" and p.path.startswith(q.path.rstrip("/") + "/")
            ),
            None,
        )
        if inside is not None:
            out.refusals.append(
                Problem(
                    "git-file-in-owned",
                    p.path,
                    f"{p.path}: inside {inside.path}, which {inside.item['kind']} "
                    f"{inside.item['name']!r} of {capability!r} owns; a git file goes outside it",
                )
            )
            del wanted[key]
        else:
            out.findings.extend(_git_notes(host, p))

    try:
        for key, p in sorted(wanted.items()):
            r = recorded.get(key)
            found = observe(host, _entry(p))
            entry = _entry(p)
            if p.form == "runtime":
                # the engine's own area: never a conflict; absent or different is rebuilt (FR-020)
                if found != p.digest:
                    adds.append(_runtime_action(p, capability))
                elif r is not None and r.get("runtime"):
                    entry["runtime"] = r["runtime"]
                out.entries.append(entry)
                continue
            if r is not None and r.get("inserted"):
                entry["inserted"] = r["inserted"]
            if r is None:
                other = _claimed_by(p.path, key, keys, owned)
                if other is not None:
                    out.refusals.append(
                        Problem(
                            "claimed-by-other",
                            p.path,
                            f"{p.path}: already installed by capability {other!r}; "
                            f"{capability!r} cannot take it",
                        )
                    )
                    continue
                prev = earlier(p) if verb != "uninstall" else None
                if found is None:
                    adds.append(_add_action(p, replace=False))
                    inherited = _inherited_parents(p, others)
                    if inherited:
                        entry["inherited_created"] = inherited
                    out.entries.append(entry)
                    continue
                if prev is not None and (found == p.digest or found in prev.get("digests", ())):
                    # a location the earlier installer left as it was: adopted without asking
                    if found != p.digest:
                        adds.append(_add_action(p, replace=p.ownership == "section"))
                    entry["adopted"] = {"found": found}
                    out.entries.append(entry)
                    out.previous.append(
                        {
                            "path": p.path,
                            "member": p.address if p.style == "json-member" else None,
                            "result": "adopted" if found == p.digest else "adopted-past-version",
                        }
                    )
                    continue
                same = "identical" if found == p.digest else "different"
                out.decisions.append(
                    Decision(
                        "conflict",
                        p.path,
                        p.address,
                        same,
                        found,
                        [_add_action(p, replace=p.ownership == "section")],
                        {**entry, "adopted": {"found": found}} if prev is not None else entry,
                        None,
                        "adopt" if prev is not None else None,
                    )
                )
                continue
            if found is None:
                adds.append(_add_action(p, replace=False))
                entry.pop("inserted", None)
                out.entries.append(entry)
            elif found == r["digest"]:
                if p.digest != r["digest"]:
                    adds.append(_add_action(p, replace=True))
                out.entries.append(entry)
            elif found == p.digest:
                out.entries.append(entry)
            else:
                kept = {**r, "targets": entry["targets"]}
                out.decisions.append(
                    Decision(
                        "divergence",
                        p.path,
                        p.address,
                        "different",
                        found,
                        [_add_action(p, replace=True)],
                        entry,
                        kept,
                    )
                )
        for key, loc in sorted(recorded.items()):
            if key in wanted:
                continue
            if verb == "uninstall" and any(t in final for t in loc.get("targets", [])):
                continue
            if verb != "uninstall" and not acting & set(loc.get("targets", [])):
                continue
            found = observe(host, loc)
            if loc.get("form") == "runtime":
                if found is not None or (host / loc["path"]).exists():
                    removes.append({"op": "delete", "path": loc["path"], "form": "runtime"})
                old_ignore = runtime.OLD_IGNORE
                if (
                    loc["path"].startswith(homes.OLD_RUNTIMES + "/")
                    and not _other_runtimes(others)
                    and (host / old_ignore).is_file()
                ):
                    removes.append({"op": "delete", "path": old_ignore, "form": "file"})
                continue
            if found is None:
                continue
            action = _remove_action(loc, not existed_before(loc["path"]), claimed_file(loc["path"]))
            if found == loc["digest"]:
                removes.append(action)
            else:
                out.decisions.append(
                    Decision(
                        "divergence",
                        loc["path"],
                        loc.get("address"),
                        "different",
                        found,
                        [action],
                        None,
                        None,
                    )
                )
    except Unmergeable as exc:
        out.refusals.append(Problem("unmergeable", "", f"a shared file cannot be merged: {exc}"))
        return out
    if verb in ("install", "update"):
        _retire(host, previous, matched, keys, owned, claimed_file, out, removes)
    deposit = homes.new(document["node"], capability).package
    removes.sort(key=lambda a: a["path"] == deposit)
    out.actions = removes + adds

    _plan_settings(verb, host, document, reg, out, existed_before, final)
    out._ctx = (host, document, pkg, reg, existed_before, inherited_dirs)
    return out


def seal(out: Plan, engine: dict, rule_digest: str) -> None:
    """After consent: the registry to write and the directories to prune."""
    host, document, pkg, reg, existed_before, inherited_dirs = out._ctx
    final = out.final_targets
    out.registry_after = (
        _registry(document, pkg, engine, rule_digest, final, out, existed_before) if final else None
    )
    dirs = set()
    for entry in out.entries:
        for anc in _ancestors(entry["path"]):
            if not (host / anc).exists() or anc in inherited_dirs:
                dirs.add(anc)
            elif reg and anc in (reg.get("created_dirs") or []):
                dirs.add(anc)
    if out.settings_record and not out.settings_record.get("existed_before", True):
        for anc in _ancestors(out.settings_record["file"]):
            if not (host / anc).exists() or (reg and anc in (reg.get("created_dirs") or [])):
                dirs.add(anc)
    if out.registry_after is not None:
        out.registry_after["created_dirs"] = sorted(dirs)
    out.prune_dirs = sorted(set((reg or {}).get("created_dirs") or []) | dirs)


def _plan_settings(verb, host, document, reg, out: Plan, existed_before, final) -> None:
    declared = document.get("settings", []) or []
    file = document.get("settings_file")
    recorded = (reg or {}).get("settings") or {}
    rec_file = recorded.get("file")
    rec_keys = {k["name"]: k for k in recorded.get("keys", [])}
    if verb == "uninstall" and final:
        return
    path = file if verb != "uninstall" else rec_file
    if not path:
        # No settings file declared: presence cannot be checked, and the outcome says so.
        out.settings.extend(
            {"name": s["name"], "description": s["description"], "state": "not-checked"}
            for s in declared
            if verb != "uninstall"
        )
        return
    text = read_text(host, path) or ""
    present = settingsfile.present(text)
    if verb == "uninstall":
        removable = [
            k
            for name, k in sorted(rec_keys.items())
            if name in present and settingsfile.value_digest(present[name]) == k["digest"]
        ]
        for name in sorted(set(rec_keys) - {k["name"] for k in removable}):
            if name in present:
                out.findings.append(
                    Problem("setting-kept", path, f"{name}: changed by the operator; kept")
                )
        if removable:
            out.actions.append(
                {
                    "op": "settings-remove",
                    "path": path,
                    "capability": document["capability"],
                    "content": removable,
                    "separator": recorded.get("separator", ""),
                    "style": "hash",
                    "created_file": not recorded.get("existed_before", True),
                    "claimed_by_others": False,
                }
            )
        return
    defaults = [
        (s["name"], s["default"]) for s in declared if s.get("secret") is False and "default" in s
    ]
    to_add = [(n, d) for n, d in defaults if n not in present]
    keys = []
    declared_defaults = {n for n, _ in defaults}
    for name, k in sorted(rec_keys.items()):
        if name in declared_defaults:
            keys.append(k)
        elif name in present and settingsfile.value_digest(present[name]) == k["digest"]:
            out.actions.append(
                {
                    "op": "settings-remove",
                    "path": path,
                    "capability": document["capability"],
                    "content": [k],
                    "separator": recorded.get("separator", ""),
                    "style": "hash",
                    "created_file": False,
                    "claimed_by_others": True,
                }
            )
    keys.extend({"name": n, "digest": settingsfile.value_digest(d)} for n, d in to_add)
    if to_add:
        out.actions.append(
            {
                "op": "settings-add",
                "path": path,
                "capability": document["capability"],
                "content": [list(p) for p in to_add],
                "settings": True,
            }
        )
    for s in declared:
        secret_or_bare = s.get("secret") is not False or "default" not in s
        state = "present" if s["name"] in present or s["name"] in dict(to_add) else "missing"
        if secret_or_bare and s["name"] not in present:
            state = "missing"
        out.settings.append({"name": s["name"], "description": s["description"], "state": state})
    out.settings_record = {
        "file": path,
        "existed_before": recorded.get("existed_before", existed_before(path))
        if recorded
        else existed_before(path),
        "separator": recorded.get("separator", ""),
        "keys": sorted(keys, key=lambda k: k["name"]),
    }


def _registry(document, pkg, engine, rule_digest, final, out: Plan, existed_before) -> dict:
    shared = sorted({e["path"] for e in out.entries if e["ownership"] == "section"})
    reg = {
        "schema": REGISTRY_SCHEMA,
        "node": document["node"],
        "capability": document["capability"],
        "version": document["version"],
        "contract": document["contract"],
        "package": {
            "producer_state": pkg.record.get("producer_state"),
            "record_schema": pkg.record.get("schema"),
        },
        "engine": engine,
        "placement_rule": {"digest": rule_digest},
        "targets": list(final),
        "locations": list(out.entries),
        "shared_files": [{"path": p, "existed_before": existed_before(p)} for p in shared],
        # its parts of shared files are the main Kaelen's to write (specs/027 R-11)
        "shared_writer": "main",
        "unsupported": sorted(
            out.unsupported, key=lambda u: (u["target"], u["item"]["kind"], u["item"]["name"])
        ),
    }
    if out.settings_record:
        reg["settings"] = out.settings_record
    return reg


def normalise(path: str) -> str:
    return posixpath.normpath(path)
