"""The host verbs: install, update, uninstall, verify (specs/017-host-verbs).

Orchestration only: the package is opened and checked (source), the plan comes from the one
reconciliation (reconcile), consent is per file (consent), and the plan is applied under an
operation record (apply). Every outcome is a `HostOutcome`.
"""

from __future__ import annotations

import dataclasses
import json
import re
import secrets
import subprocess
import sys
from pathlib import Path

from kaelen import provenance
from kaelen.host import apply as applier
from kaelen.host import checks as form_checks
from kaelen.host import contributions, reconcile, registry, runtime, settingsfile
from kaelen.host import home as homes
from kaelen.host import live as live_checks
from kaelen.host.consent import NON_INTERACTIVE, Interaction, decide
from kaelen.host.desired import desired
from kaelen.host.jsonspan import Unmergeable
from kaelen.host.registry import UnreadableRegistry, UnsupportedRegistry
from kaelen.host.source import PackageError, open_package
from kaelen.host.state import folder_files, observe, read_text
from kaelen.outcome import VERIFY_SEVERITY, HostOutcome, HostVerification, Problem
from kaelen.package import inject
from kaelen.package.record import digest_tree
from kaelen.placement import PLACED, RuleError, place_item, rule_digest

PACKAGE_AREA = ".kaelen/packages/"
OLDER_ENGINES = "0.11.0"  # the last engine of the old layout (specs/026 R-5)
NOT_CHECKED = ["whether each assistant actually loads and runs the installed items (FEAT-007)"]
VERIFY_NOT_CHECKED = [
    "whether each assistant loads the installed items: only their form is checked",
    "hooks are not executed: only their command is resolved",
    "the tools of MCP servers are listed, never invoked",
]
NOT_LIVE = "MCP servers were not started: pass --live to start them"


def running_engine(version: str) -> dict:
    try:
        files = inject.engine_files(version)
    except inject.InjectionError:
        return {"version": version, "digest": "unknown"}
    return {
        "version": version,
        "digest": digest_tree([(p, d) for p, d in files if p.startswith("engine/")]),
    }


def running_directory() -> Path:
    """The directory the running engine is imported from (`.../engine` holding `kaelen/`)."""
    return Path(__file__).resolve().parent.parent.parent


def _version_key(text: str):
    return tuple(int(p) if p.isdigit() else -1 for p in re.split(r"[.+-]", text or "0"))


def run(
    verb: str,
    host: Path,
    package: Path | None,
    *,
    engine_version: str,
    targets: list[str] | None = None,
    dry_run: bool = False,
    allowed: set[str] | None = None,
    interaction: Interaction = NON_INTERACTIVE,
    writer: applier.Writer | None = None,
    allow_downgrade: bool = False,
    running_from: Path | None = None,
    builder: runtime.RuntimeBuilder | None = None,
    live: bool = False,
    live_timeout: float = live_checks.DEFAULT_TIMEOUT,
    runner=None,
    origin: str | None = None,
    trust: str | None = None,
    allow_unsigned: bool = False,
    check_provenance: bool = False,
    provenance_timeout: float = 60.0,
    with_groups: list[str] | None = None,
    without_groups: list[str] | None = None,
    break_dependents: bool = False,
    git=None,
) -> HostOutcome:
    writer = writer or applier.Writer()
    builder = builder or runtime.ToolBuilder()
    git = git or provenance.DEFAULT_GIT
    out = HostOutcome(
        verb, host.as_posix(), package.as_posix() if package else None, dry_run, "internal"
    )
    out.not_checked = list(NOT_CHECKED)

    def stop(verdict: str, rule: str | None = None, message: str | None = None) -> HostOutcome:
        out.verdict = verdict
        if message:
            out.errors.append(Problem(rule or verdict, "", message))
        return out

    if not host.is_dir():
        return stop(
            "unable-to-check", "host-not-directory", f"host {host.as_posix()!r} is not a directory"
        )
    if package is None:
        return stop("unable-to-check", "no-package", "no package: pass --package")
    try:
        pkg = open_package(package)
    except PackageError as exc:
        return stop("unable-to-check", exc.rule, str(exc))
    document = pkg.document
    capability = document["capability"]
    out.capability, out.version = capability, document["version"]
    if verb in ("install", "update") and homes.deposit_of(package) is not None:
        return stop(
            "refused",
            "deposited-package",
            f"this package is the copy kept in {capability!r}'s folder on the host; {verb} needs "
            "the producer's package (uninstall, verify and rollback run from here)",
        )
    engine = running_engine(engine_version)
    try:
        digest = rule_digest()
    except RuleError as exc:
        return stop("internal", "rule", str(exc))

    if verb != "verify" and not dry_run:
        try:
            applier.tidy(host, writer)
        except OSError as exc:
            return stop("incomplete", "write-failed", f"cannot tidy the Kaelen area: {exc}")
    pending = applier.load_record(host, capability)
    if pending is not None:
        unknown = _unknown_record(pending)
        if unknown:
            return stop("refused", "operation-unsupported", unknown)
        out.incomplete = _incomplete(host, pending)
        if pending.get("rolling_back"):
            return stop(
                "incomplete",
                "rollback-in-progress",
                f"a rollback of {capability!r} is in progress on this host",
            )
        same = pending.get("operation") == verb and (pending.get("package") or {}).get(
            "producer_state"
        ) == pkg.record.get("producer_state")
        if verb == "verify" or not same or dry_run:
            return stop(
                "incomplete",
                "incomplete-operation",
                f"an interrupted {pending.get('operation')} of {capability!r} is on this host: "
                f"{out.incomplete['done']} of {out.incomplete['actions']} action(s) done",
            )
        _ignore_note(out, host, pending.get("home"))
        return _complete(out, host, pending, writer, verb, builder, runner)

    place = registry.locate(host, capability, document["node"])
    try:
        reg = registry.load_at(host, place)
    except UnreadableRegistry as exc:
        return stop("unable-to-check", "registry-unreadable", f"{place.registry}: {exc}")
    except UnsupportedRegistry as exc:
        verdict = "unable-to-check" if verb == "verify" else "refused"
        return stop(verdict, "registry-unsupported", f"{place.registry}: {exc}")
    target_home = homes.new(document["node"], capability)
    if reg is None:
        problem = _home_problem(host, target_home)
        if problem is not None and verb == "install":
            return stop("refused", *problem)
    if reg is not None and reg.get("node") != document["node"]:
        return stop(
            "refused",
            "capability-other-producer",
            f"capability {capability!r} on this host was installed by node {reg.get('node')!r}, "
            f"not by {document['node']!r}",
        )

    # the items this operation installs: the chosen groups and the items in none (specs/029)
    try:
        selected, chosen, changes = _selection(
            document, reg, verb, with_groups or [], without_groups or []
        )
    except _GroupChoice as exc:
        return stop("refused", exc.rule, exc.message)
    if document.get("groups"):
        names = {i["name"] for i in selected}
        out.groups = {
            "declared": [g["name"] for g in document["groups"]],
            "chosen": chosen,
            "included": sorted(names),
            "left_out": sorted(i["name"] for i in document["items"] if i["name"] not in names),
            **changes,
        }
    elif (reg or {}).get("groups") and verb == "update":  # the new version declares none (FR-020)
        out.groups = {
            "declared": [],
            "chosen": [],
            "included": sorted(i["name"] for i in document["items"]),
            "left_out": [],
            "added": [],
            "dropped": list(reg["groups"].get("chosen") or []),
        }
    pkg = dataclasses.replace(pkg, document={**document, "items": selected})
    if verb in ("install", "update"):
        problem = _requirements(out, host, document, capability)
        if problem is not None:
            out.errors.append(problem)
            return stop("refused")
    if verb in ("uninstall", "update") and reg is not None:
        refusals = _dependents(out, host, document, verb, chosen, break_dependents)
        if refusals:
            out.errors.extend(refusals)
            return stop("refused")

    if verb == "verify":
        if reg is not None:  # the installation is what is checked (specs/031 FR-001)
            out.version = reg.get("version")
        if reg is not None and place.legacy:
            _old_layout(out, host, place)
        if reg is not None:
            _requirements(out, host, document, capability, report_only=True)
        _verify(
            out, host, pkg, reg, engine, digest, live, live_timeout,
            check_provenance, provenance_timeout,
        )  # fmt: skip
        if reg is not None and not place.legacy:
            _hidden(out, host, place, pkg, git)
        return out

    recorded_provenance = None
    if verb in ("install", "update"):
        try:
            refusal, recorded_provenance = _provenance_gate(
                out, host, pkg, reg, verb, origin, trust, allow_unsigned
            )
        except ValueError as exc:
            return stop("refused", "origin-unreadable", str(exc))
        if refusal is not None:
            out.errors.append(refusal)
            return stop("refused")
    elif verb == "uninstall" and reg is not None:
        deposit = host / homes.new(reg["node"], reg["capability"]).package
        _signer_note(out, host, deposit if deposit.is_dir() else pkg.root, reg)

    spec = document.get("runtime")
    if spec and verb in ("install", "update"):
        if not runtime.satisfies(spec["python"], runtime.interpreter_version()):
            return stop(
                "refused",
                "runtime-python",
                f"{capability} needs Python {spec['python']}; this interpreter is "
                f"{runtime.python_label()}: run the package with a Python that satisfies it",
            )

    targets = list(targets or [])
    recorded = list((reg or {}).get("targets", []))
    if verb == "install":
        unknown = [t for t in targets if t not in document["targets"]]
        if not targets or unknown:
            what = ", ".join(unknown) if unknown else "none named"
            return stop(
                "refused",
                "target-not-declared",
                f"install needs targets declared by the package ({what}); declared: "
                + ", ".join(document["targets"]),
            )
        if reg is not None and reg.get("version") != document["version"]:
            return stop(
                "refused",
                "other-version-installed",
                f"{capability} {reg.get('version')} is installed; this package is "
                f"{document['version']}: use update",
            )
    else:
        if reg is None:
            if verb == "uninstall":
                out.verdict = "not-installed"
                return out
            return stop("refused", "not-installed", f"{capability!r} is not installed on this host")
        stray = [t for t in targets if t not in recorded]
        if stray:
            return stop(
                "refused",
                "target-not-recorded",
                f"{', '.join(stray)} not installed for {capability!r}; "
                f"recorded: {', '.join(recorded)}",
            )
        if verb == "update":
            older = _version_key(document["version"]) < _version_key(reg.get("version", ""))
            older_engine = _version_key(engine_version) < _version_key(
                (reg.get("engine") or {}).get("version", "")
            )
            if (older or older_engine) and not allow_downgrade:
                return stop(
                    "refused",
                    "downgrade",
                    f"installed {reg.get('version')} by engine "
                    f"{(reg.get('engine') or {}).get('version')}; "
                    f"this package is {document['version']} with engine {engine_version}: "
                    "pass --allow-downgrade to replace it",
                )

    others, unreadable, unsupported = registry.read_others(host, capability)
    for name in unreadable:
        out.findings.append(
            Problem(
                "registry-unreadable",
                registry.relative(name, host),
                "another capability's registry cannot be read; left as is",
            )
        )
    for name, schema in unsupported:
        out.findings.append(
            Problem(
                "registry-unsupported",
                registry.relative(name, host),
                f"another capability's registry has schema {schema!r}, which this engine does not "
                f"know ({registry.SCHEMA}); left as is",
            )
        )
    plan = reconcile.plan(verb, host, pkg, targets, reg, others, engine, digest)
    out.findings.extend(plan.findings)
    out.settings = plan.settings
    out.previous = plan.previous
    if plan.refusals:
        out.errors.extend(plan.refusals)
        return stop("refused")

    answers = decide(plan.decisions, allowed or set(), interaction)
    for index, decision in enumerate(plan.decisions):
        record = {
            "path": decision.path,
            "address": decision.address,
            "found": decision.found,
            "digest_found": decision.digest_found,
            "kind": decision.kind,
        }
        if decision.previous:
            consented = {"adopt": "adopted-with-consent", "retire": "retired-with-consent"}
            refused = {"adopt": "refused", "retire": "kept"}
            plan.previous.append(
                {
                    "path": decision.path,
                    "member": decision.address if decision.previous == "retire" else None,
                    "result": (consented if answers[index] else refused)[decision.previous],
                }
            )
        if answers[index]:
            plan.actions.extend(decision.on_yes)
            if decision.entry_yes:
                plan.entries.append(decision.entry_yes)
            out.replaced.append({"path": decision.path, "digest_found": decision.digest_found})
        elif decision.kind == "conflict":
            out.conflicts.append(record)
        else:
            _name_files(record, host, reg)
            out.divergences.append(record)
            if decision.entry_no:
                plan.entries.append(decision.entry_no)
            out.findings.append(
                Problem(
                    "kept-modified", decision.path, f"{decision.label}: modified on the host; kept"
                )
            )
    if out.conflicts:
        out.errors.append(
            Problem(
                "conflict",
                out.conflicts[0]["path"],
                f"{len(out.conflicts)} location(s) hold content not installed by {capability!r}; "
                "nothing was written",
            )
        )
        return stop("refused")
    for entry in plan.entries:
        if entry.get("form") == "runtime" and "runtime" not in entry:
            entry["runtime"] = {"tool": builder.tool(), "python": runtime.python_label()}
    reconcile.seal(plan, engine, digest)
    if recorded_provenance is not None and plan.registry_after is not None:
        plan.registry_after.update(recorded_provenance)  # additive fields (specs/028 FR-003)
    if plan.registry_after is not None:  # additive fields (specs/029 R-7)
        if document.get("requires"):
            plan.registry_after["requires"] = [_requirement(r) for r in document["requires"]]
        if document.get("groups"):
            plan.registry_after["groups"] = {
                "declared": [g["name"] for g in document["groups"]],
                "chosen": chosen,
            }
    out.main = _plan_main(host, verb, pkg, plan, target_home)
    migrating = reg is not None and place.legacy and verb == "update"
    if migrating:
        out.findings.append(
            Problem(
                "older-engines-blind",
                target_home.registry,
                f"{capability!r} moves to {target_home.root}/; engines {OLDER_ENGINES} and "
                "earlier look for registries only in .kaelen/registry/ and will not see its claims "
                "on shared files",
            )
        )
    out.runtime = _runtime_report(plan, builder, dry_run)
    forbidden = [a["path"] for a in plan.actions if a["path"].startswith(PACKAGE_AREA)]
    if forbidden:
        return stop(
            "refused", "package-area", f"{forbidden[0]}: the verbs never write the package area"
        )
    running = running_from if running_from is not None else running_directory()
    for action in plan.actions:
        own_deposit = (
            verb == "uninstall"
            and action["op"] == "delete"
            and action["path"] == target_home.package
        )
        if not own_deposit and _inside(running, host / action["path"]):
            out.errors.append(
                Problem(
                    "running-engine-in-plan",
                    action["path"],
                    f"this {verb} would {action['op']} {action['path']}, which holds the engine "
                    "running it; run it from the run.py of "
                    f"{capability!r}'s package as its producer publishes it",
                )
            )
            return stop("refused")
    out.changes = [
        {
            "op": a["op"],
            "path": a["path"],
            **({"address": a["address"]} if a.get("address") else {}),
        }
        for a in plan.actions
        if not _transient(host, a)
    ]
    out.targets = _target_report(plan)
    if verb in ("install", "update"):
        _hidden(out, host, target_home, pkg, git)
    unchanged_registry = (
        reg is not None
        and plan.registry_after is not None
        and (
            registry.serialise(registry.keep_unknown(plan.registry_after, reg))
            == registry.serialise(reg)
        )
    )
    if verb == "install" and reg is not None and not plan.actions and set(targets) <= set(recorded):
        out.verdict = "already-installed"
        if unchanged_registry or dry_run:
            return out
    contribution = _contribution_action(host, plan.actions, engine_version)
    if contribution is not None:
        probe = {"capability": capability, "operation": verb, "id": "check"}
        probe["actions"] = plan.actions
        refusal = _check_contributions(host, probe, contribution, out, runner)
        if refusal is not None:
            out.errors.append(refusal)
            return stop("refused")
        out.contributions = {
            "count": len(contribution["indices"]),
            "files": sorted(contribution["files"]),
            "writer": "main Kaelen",
            # the main Kaelen that applies the set: the arriving one, or the one about to go
            "main_kaelen": (out.main or {}).get("version")
            or (out.main or {}).get("from")
            or contribution["engine"],
        }
    if plan.registry_after is not None and (plan.actions or not unchanged_registry):
        _ignore_note(out, host, target_home.root)  # this operation writes the record (R-1)
    if dry_run:
        out.verdict = {"install": "would-install", "update": "would-update"}.get(
            verb, "would-uninstall"
        )
        return out
    if not plan.actions and unchanged_registry:
        out.verdict = {"install": "already-installed", "update": "updated"}.get(verb, "uninstalled")
        return out
    after = (
        registry.keep_unknown(plan.registry_after, reg) if plan.registry_after is not None else None
    )
    try:
        applier.precompute(host, plan.actions)
    except Unmergeable as exc:
        return stop("refused", "unmergeable", f"a shared file cannot be merged: {exc}")
    op = {
        "schema": applier.SCHEMA,
        "operation": verb,
        "capability": capability,
        "home": target_home.root,
        "registry": target_home.registry if after is not None else place.registry,
        "legacy": [place.registry] if place.legacy and after is not None else [],
        "home_created": _absent(host, target_home.root),
        "package": {"producer_state": pkg.record.get("producer_state")},
        "targets": plan.final_targets,
        "actions": plan.actions,
        "done": [],
        "registry_after": after,
        "prune_dirs": plan.prune_dirs,
        "rolling_back": False,
        "copies": [],
        "id": secrets.token_hex(8),
    }
    broken = [d for d in (out.dependents or []) if d.get("broken")]
    if broken:  # the consent to break them, kept with the operation (specs/029 FR-013)
        op["broken_dependents"] = broken
    if contribution is not None:  # one action hands every text action to the main Kaelen (R-2)
        for index in contribution["indices"]:
            op["actions"][index]["via"] = "contribute"
        op["actions"].insert(applier.engines_from(op), contribution)
    if out.verdict != "already-installed":
        out.verdict = {"install": "installed", "update": "updated"}.get(verb, "uninstalled")
    return _execute(out, host, op, writer, builder, runner)


def _ignore_note(out: HostOutcome, host: Path, root: str | None) -> None:
    """The home's ignore file of an earlier engine, rewritten by this operation (specs/033 R-1)."""
    rel = f"{root}/{homes.IGNORE}" if root else None
    if applier.ignore_state(host, rel) == "old":
        out.findings.append(
            Problem(
                "ignore-file-corrected",
                rel,
                "the ignore file an earlier engine wrote also hid the package's own runtime/ "
                "folder; it is rewritten with lines anchored to the capability's folder",
            )
        )


HIDDEN_NOT_CHECKED = "whether the host's ignore rules hide the deposited package"


def _hidden(out: HostOutcome, host: Path, home: homes.Home, pkg, git) -> None:
    """Every file of the deposited package that an ignore rule of the host hides (FR-017).

    Asked of git itself, read-only: a hidden file is not committed, so a clone lacks it.
    """
    from kaelen.package import record as package_record

    names = [e["path"] for e in pkg.record.get("files", [])] + [package_record.FILENAME]
    if (pkg.root / package_record.SIGNATURE).is_file():
        names.append(package_record.SIGNATURE)
    paths = [f"{home.package}/{n}" for n in sorted(names)]
    code, text = git.run(["check-ignore", "-v", "--stdin", "-z"], host, input="\0".join(paths))
    if code == 128:  # not a repository: nothing is under version control, nothing is hidden
        return
    if code not in (0, 1):
        out.not_checked.append(HIDDEN_NOT_CHECKED)
        return
    fields = text.split("\0")
    for i in range(0, len(fields) - 3, 4):
        source, line, pattern, path = fields[i : i + 4]
        if not path:
            continue
        rule = f"{source}:{line}:{pattern}"
        if source.replace("\\", "/") == home.ignore:
            out.findings.append(
                Problem(
                    "ignore-file-edited",
                    path,
                    f"the capability's ignore file was edited and hides this file of the "
                    f"deposited package ({rule}); a clone will lack it",
                )
            )
        else:
            out.findings.append(
                Problem(
                    "package-hidden",
                    path,
                    f"hidden from version control by {rule}; a clone will lack this file of the "
                    "deposited package, which then cannot verify or uninstall",
                )
            )


def _execute(
    out: HostOutcome, host: Path, op: dict, writer, builder=None, runner=None
) -> HostOutcome:
    try:
        applier.save_record(host, op, writer)
        applier.apply(host, op, writer, builder, runner=runner)
        applier.finish(host, op, writer, runner)
    except applier.ReleaseFailed as exc:  # done; only the main Kaelen's part is left (027 U2)
        out.verdict = "incomplete"
        out.incomplete = {**_incomplete(host, op), "done": len(op.get("actions", [])),
                          "rollback": "not-needed"}  # fmt: skip
        out.errors.append(Problem("release-failed", exc.filename or "", str(exc)))
    except Exception as exc:  # an interrupted operation is declared, never hidden (FR-029)
        where = getattr(exc, "filename", None)
        out.verdict = "incomplete"
        out.incomplete = _incomplete(host, op)
        rule = getattr(exc, "rule", None) or "write-failed"  # the main Kaelen's, if it gave one
        out.errors.append(Problem(rule, str(where or ""), f"the {op['operation']} stopped: {exc}"))
    return out


def _complete(
    out: HostOutcome, host: Path, pending: dict, writer, verb: str, builder=None, runner=None
) -> HostOutcome:
    out.completed = True
    out.verdict = {"install": "installed", "update": "updated"}.get(verb, "uninstalled")
    out.changes = [
        {"op": a["op"], "path": a["path"]}
        for i, a in enumerate(pending["actions"])
        if i not in set(pending.get("done", [])) and a["op"] != "contribute"
    ]
    return _execute(out, host, pending, writer, builder, runner)


def _incomplete(host: Path, op: dict) -> dict:
    """What an incomplete operation is, and whether it can be rolled back (specs/021 R-7)."""
    return {
        "operation": op.get("operation"),
        "done": len(op.get("done", [])),
        "actions": len(op.get("actions", [])),
        "rollback": "not-possible" if applier.rollback_problem(host, op) else "possible",
        "rolling_back": bool(op.get("rolling_back")),
    }


class _Divergence:
    """A location changed since the interruption, in the shape `decide()` asks about."""

    kind = "changed since the interruption"
    found = "modified"
    on_yes = ({"op": "write"},)

    def __init__(self, path: str, digest: str):
        self.path = self.label = path
        self.digest_found = digest


def rollback(
    host: Path,
    capability: str,
    *,
    engine_version: str,
    package: Path | None = None,
    dry_run: bool = False,
    allowed: set[str] | None = None,
    interaction: Interaction = NON_INTERACTIVE,
    writer: applier.Writer | None = None,
    running_from: Path | None = None,
    runner=None,
) -> HostOutcome:
    """Undo one capability's incomplete operation from its copies (specs/021 research R-4).

    The shared files its contributions touched are put back by the main Kaelen, from its own part,
    at the point of the operation where the `contribute` action stood (specs/027 R-8).
    """
    writer = writer or applier.Writer()
    out = HostOutcome(
        "rollback", host.as_posix(), package.as_posix() if package else None, dry_run, "internal"
    )
    out.capability = capability

    def stop(verdict: str, rule: str | None = None, message: str | None = None) -> HostOutcome:
        out.verdict = verdict
        if message:
            out.errors.append(Problem(rule or verdict, "", message))
        return out

    if not host.is_dir():
        return stop(
            "unable-to-check", "host-not-directory", f"host {host.as_posix()!r} is not a directory"
        )
    pending = applier.load_record(host, capability)
    if pending is None:
        if not dry_run:
            try:
                applier.tidy(host, writer)  # copies a resumed rollback left after its record
            except OSError as exc:
                return stop("incomplete", "write-failed", f"cannot tidy the Kaelen area: {exc}")
        out.verdict = "nothing-to-roll-back"
        return out
    unknown = _unknown_record(pending)
    if unknown:
        return stop("refused", "operation-unsupported", unknown)
    out.incomplete = _incomplete(host, pending)
    problem = applier.rollback_problem(host, pending)
    if problem:
        return stop(
            "cannot-roll-back",
            "cannot-roll-back",
            f"the interrupted {pending.get('operation')} of {capability!r} cannot be rolled back: "
            + problem,
        )
    entries = list(reversed(pending["copies"]))
    resuming = bool(pending.get("rolling_back"))
    flight = None if resuming else applier.in_flight(pending)
    contribute = next((a for a in pending["actions"] if a["op"] == "contribute"), None)
    try:
        part = contributions.load_part(host, capability) if contribute is not None else None
    except contributions.Refused as exc:
        return stop("cannot-roll-back", exc.rule, exc.message)
    shared = list(reversed(part["copies"])) if part is not None else []
    diverged = []
    for entry in entries + shared:
        now = applier.location_digest(host, entry["path"])
        if not resuming and now not in entry["accepted"] and entry["path"] != flight:
            diverged.append(_Divergence(entry["path"], now))
    answers = decide(diverged, allowed or set(), interaction)
    consented = {d.path for i, d in enumerate(diverged) if answers[i]}
    refused = [d for i, d in enumerate(diverged) if not answers[i]]
    if refused:
        out.divergences = [
            {"path": d.path, "state": d.kind, "digest_found": d.digest_found} for d in refused
        ]
        return stop(
            "refused",
            "divergent",
            f"{len(refused)} location(s) changed since the interruption; nothing was written",
        )
    running = running_from if running_from is not None else running_directory()
    for entry in entries:
        # a location already as it was is not written, so it may hold the running engine
        unchanged = applier.location_digest(host, entry["path"]) == entry["digest_before"]
        if not unchanged and _inside(running, host / entry["path"]):
            return stop(
                "refused",
                "running-engine-in-plan",
                f"this rollback would restore {entry['path']}, which holds the engine running it; "
                + _elsewhere(host, running, capability),
            )
    for entry in entries + shared:
        if applier.location_digest(host, entry["path"]) == entry["digest_before"]:
            continue
        if entry["path"] in consented:
            result = "restored-with-consent"
        else:
            result = "removed" if entry["state"] == applier.ABSENT else "restored"
        out.restored.append({"path": entry["path"], "result": result})
    if not pending.get("home_created"):  # a home the rollback keeps
        _ignore_note(out, host, pending.get("home"))
    if dry_run:
        out.verdict = "would-roll-back"
        return out
    try:
        if not resuming:
            pending["rolling_back"] = True
            applier.save_record(host, pending, writer)
        split = (contribute or {}).get("copies_from")
        late = [e for e in entries if split is not None and e["n"] >= split]
        for entry in late:  # what followed the contributions, first (the main Kaelen, its part)
            applier.restore(host, pending, entry, writer)
        if contribute is not None and (host / contributions.part_path(capability)).is_file():
            request = {"mode": "rollback", "capability": capability}
            asked = applier.runner_for(host, runner, contribute.get("engine"))
            doc = asked(contributions.main_run(host), host, request, writer)
            if doc.get("verdict") not in ("rolled-back", "nothing-to-roll-back"):
                error = (doc.get("errors") or [{}])[0]
                raise applier.ContributionFailed(
                    f"the main Kaelen did not roll back its part ({doc.get('verdict')}): "
                    + str(error.get("message", "")),
                    contributions.part_path(capability),
                    error.get("rule"),
                )
        for entry in entries:
            if entry not in late:
                applier.restore(host, pending, entry, writer)
        applier.drop_record(host, pending, writer)
        applier.remove_created(host, pending, writer)
        applier.tidy(host, writer)
    except Exception as exc:  # an interrupted rollback is declared, never hidden (FR-018)
        out.incomplete = _incomplete(host, applier.load_record(host, capability) or pending)
        return stop(
            "incomplete",
            getattr(exc, "rule", None) or "write-failed",  # the main Kaelen's, if it gave one
            f"the rollback stopped: {exc} ({getattr(exc, 'filename', '') or ''})",
        )
    out.verdict = "rolled-back"
    return out


def _runtime_report(plan, builder, dry_run: bool) -> dict | None:
    """What happens to the capability's environment in this operation (specs/022 FR-015, FR-017)."""
    build = next((a for a in plan.actions if a["op"] == "runtime"), None)
    drop = next(
        (a for a in plan.actions if a["op"] == "delete" and a.get("form") == "runtime"), None
    )
    kept = next((e for e in plan.entries if e.get("form") == "runtime"), None)
    if build is not None:
        return {
            "state": "would-build" if dry_run else "built",
            "tool": builder.tool(),
            "python": runtime.python_label(),
            "dependencies": build["dependencies"],
        }
    if drop is not None:
        return {"state": "would-remove" if dry_run else "removed"}
    if kept is not None:
        return {"state": "kept", **(kept.get("runtime") or {})}
    return None


def _target_report(plan) -> list[dict]:
    report = []
    touched = {a["path"] for a in plan.actions}
    for target in plan.final_targets:
        items = {}
        for entry in plan.entries:
            if target in entry.get("targets", []):
                key = (entry["item"]["kind"], entry["item"]["name"])
                result = (
                    "changed"
                    if entry["path"] in touched
                    else items.get(key, {}).get("result", "unchanged")
                )
                items[key] = {"kind": key[0], "name": key[1], "result": result}
        for u in plan.unsupported:
            if u["target"] == target:
                key = (u["item"]["kind"], u["item"]["name"])
                items[key] = {
                    "kind": key[0],
                    "name": key[1],
                    "result": "not-installed",
                    "reason": u["reason"],
                }
        report.append({"target": target, "items": [items[k] for k in sorted(items)]})
    return report


def _name_files(record: dict, host: Path, reg: dict | None, loc: dict | None = None) -> None:
    """Add the files of a folder location that differ from what was installed (specs/032 R-4)."""
    if loc is None:
        loc = next(
            (
                entry
                for entry in (reg or {}).get("locations", [])
                if entry["path"] == record["path"]
                and entry.get("form") == "directory"
                and not entry.get("address")
            ),
            None,
        )
    if loc is None or loc.get("form") != "directory" or reg is None:
        return
    files = folder_files(host, reg, loc)
    if files is None:
        record["files_unknown"] = True
    else:
        record["files"] = files


def _verify(
    out: HostOutcome,
    host: Path,
    pkg,
    reg: dict | None,
    engine: dict,
    digest: str,
    live: bool = False,
    live_timeout: float = live_checks.DEFAULT_TIMEOUT,
    check_provenance: bool = False,
    provenance_timeout: float = 60.0,
) -> HostOutcome:
    if reg is None:
        out.verdict = "no-installation"
        return out
    states = []
    for loc in sorted(reg["locations"], key=lambda loc: (loc["path"], loc.get("address") or "")):
        try:
            found = observe(host, loc)
        except Exception as exc:
            out.verdict = "unable-to-check"
            out.errors.append(Problem("unreadable", loc["path"], str(exc)))
            return out
        state = (
            "absent"
            if found is None
            else ("unchanged" if found == loc.get("digest") else "modified")
        )
        entry = {
            "path": loc["path"],
            "item": loc.get("item"),
            "targets": loc.get("targets", []),
            "state": state,
        }
        if loc.get("address") and "[" not in loc["address"]:
            entry["address"] = loc["address"]
        divergence = {"path": loc["path"], "address": loc.get("address"), "state": state}
        if state != "unchanged" and loc.get("form") == "directory":
            _name_files(entry, host, reg, loc)
            for key in ("files", "files_unknown"):
                if key in entry:
                    divergence[key] = entry[key]
        states.append(entry)
        if state != "unchanged":
            out.divergences.append(divergence)
    for u in reg.get("unsupported", []):
        states.append(
            {
                "path": None,
                "item": u["item"],
                "targets": [u["target"]],
                "state": "not-supported",
                "reason": u["reason"],
            }
        )
    out.items = states
    out.runtime = _inspect_runtime(out, host, pkg, reg)
    _what_runs(out, host, pkg, reg, live, live_timeout)
    recorded = {
        "capability_version": reg.get("version"),
        "engine": reg.get("engine"),
        "placement_rule": (reg.get("placement_rule") or {}).get("digest"),
    }
    running = {
        "engine": engine,
        "placement_rule": digest,
        "capability_version": pkg.document["version"],
    }
    differs = []
    if (recorded["engine"] or {}).get("version") != engine["version"]:
        differs.append("engine")
    if recorded["placement_rule"] != digest:
        differs.append("placement_rule")
    out.versions = {"running": running, "recorded": recorded, "differs": differs}
    settings_file = (reg.get("settings") or {}).get("file") or pkg.document.get("settings_file")
    if pkg.document.get("settings"):
        present = (
            settingsfile.present(read_text(host, settings_file) or "") if settings_file else None
        )
        out.settings = [
            {
                "name": s["name"],
                "description": s["description"],
                "state": "not-checked"
                if present is None
                else ("present" if s["name"] in present else "missing"),
            }
            for s in pkg.document["settings"]
        ]
    _shared_writers(out, host, reg)
    check = _provenance_verify(out, host, reg, check_provenance, provenance_timeout)
    broken = [r for r in (out.requirements or []) if not r["satisfied"]]
    for r in broken:
        out.findings.append(
            Problem(
                "requirement-unsatisfied",
                f"{r['node']}/{r['capability']}",
                f"requires {r['node']}/{r['capability']} {r['version']}"
                + (f" with groups {', '.join(r['groups'])}" if r["groups"] else "")
                + f": {r['why']}",
            )
        )
    if out.divergences or broken or check in ("differs", "mismatch"):
        out.verdict = "divergent"
    elif check == "not-checked":
        out.verdict = "not-checked"
    else:
        out.verdict = "verified"
    return out


def _shared_writer(reg: dict) -> str:
    """Who writes this capability's parts of shared files: the main Kaelen when its registry says
    so (engines from 0.13.0 on), else the capability's own engine (specs/027 R-11)."""
    return "main" if reg.get("shared_writer") == "main" else "direct"


def _shared_writers(out: HostOutcome, host: Path, reg: dict) -> None:
    """Findings about who writes shared files on this host (specs/027 R-7, R-11). Read-only."""
    capability = reg["capability"]
    part = host / contributions.part_path(capability)
    if part.is_file():
        record = applier.load_record(host, capability)
        try:
            serves = (contributions.load_part(host, capability) or {}).get("serves")
        except contributions.Refused:
            serves = None
        if record is None or record.get("id") != serves:
            out.findings.append(
                Problem(
                    "orphan-contribution",
                    contributions.part_path(capability),
                    "the main Kaelen kept a part of an operation that has ended; the next "
                    "operation on this host drops it",
                )
            )
    for place, other in registry.everything(host):
        if isinstance(other, Exception) or other.get("capability") == capability:
            continue
        if _shared_writer(other) == "direct":
            engine = (other.get("engine") or {}).get("version")
            out.findings.append(
                Problem(
                    "direct-writer",
                    place.registry,
                    f"{other['capability']!r} was installed by engine {engine}, which writes its "
                    "parts of shared files itself; its first update by a package of engine "
                    f"{contributions.MINIMUM} or later hands them to the main Kaelen",
                )
            )


def _rule_location(loc: dict, target: str, pkg, capability: str) -> dict | None:
    item = loc.get("item") or {}
    declared = next(
        (
            i
            for i in pkg.document["items"]
            if (i["kind"], i["name"]) == (item.get("kind"), item.get("name"))
        ),
        None,
    )
    if declared is None:
        return None
    answer = place_item(target, declared, capability, pkg.document["node"])
    if answer["outcome"] != PLACED:
        return None
    return next((x for x in answer["locations"] if x["path"].rstrip("/") == loc["path"]), None)


def _what_runs(out: HostOutcome, host: Path, pkg, reg: dict, live: bool, timeout: float) -> None:
    """Form checks, hook commands and, when asked, live MCP servers (specs/023)."""
    capability = reg["capability"]
    try:
        placements = {
            p.key: p
            for p in desired(
                pkg, [t for t in reg.get("targets", []) if t in pkg.document["targets"]]
            )[0]
        }
    except Exception:  # the rendering is the package's; verify still reports the rest
        placements = {}
    by_path = {(i.get("path"), i.get("address")): i for i in out.items if i.get("path")}
    servers: dict[tuple[str, str], dict] = {}
    for loc in reg["locations"]:
        item = by_path.get(
            (
                loc["path"],
                loc.get("address") if loc.get("address") and "[" not in loc["address"] else None,
            )
        )
        if item is None or (loc.get("item") or {}).get("kind") == "runtime":
            continue
        rule_locs = [
            r for t in loc.get("targets", []) if (r := _rule_location(loc, t, pkg, capability))
        ]
        checks = [c for r in rule_locs[:1] for c in r.get("checks", [])]
        if not checks:
            item["form"] = {"state": "no-checks"}
        elif item["state"] == "absent":
            item["form"] = {"state": "not-checked", "reason": "absent"}
        else:
            failed = form_checks.run(host, loc["path"], checks)
            item["form"] = {"state": "fails", "failed": failed} if failed else {"state": "passes"}
            if failed:
                out.divergences.append(
                    {"path": loc["path"], "address": loc.get("address"), "state": "form"}
                )
        kind = (loc.get("item") or {}).get("kind")
        placed = placements.get((loc["path"], loc.get("address") or ""))
        if kind == "hook" and placed is not None and loc.get("wrapper") != "verbatim":
            try:
                commands = form_checks.hook_commands(placed.content)
            except (TypeError, ValueError):
                commands = []
            missing = sorted({m for c in commands for m in form_checks.resolve(host, c)})
            item["command"] = (
                {"state": "unresolved", "missing": missing} if missing else {"state": "resolves"}
            )
            if missing:
                out.divergences.append(
                    {"path": loc["path"], "address": loc.get("address"), "state": "command"}
                )
        if kind == "mcp-server" and live:
            key = (loc["path"], (loc.get("item") or {}).get("name"))
            if key not in servers:
                spec = live_checks.definition(host, key[0], key[1])
                result = (
                    {
                        "state": "failed",
                        "cause": "definition not found where the assistant reads it",
                    }
                    if spec is None
                    else live_checks.check(host, spec, timeout)
                )
                servers[key] = {"server": key[1], "path": key[0], "targets": [], **result}
            servers[key]["targets"] = sorted(set(servers[key]["targets"]) | set(loc["targets"]))
    out.live = list(servers.values()) if live else None
    for server in out.live or []:
        if server["state"] == "failed":
            out.divergences.append(
                {"path": server["path"], "address": None, "state": "not-running"}
            )
    out.not_checked = list(VERIFY_NOT_CHECKED) + ([] if live else [NOT_LIVE])
    if live:
        out.not_checked.append("live checks ran the producer's MCP servers on this machine")


def _inspect_runtime(out: HostOutcome, host: Path, pkg, reg: dict) -> dict | None:
    """The environment against its lock, read from what is installed (specs/022 R-8)."""
    loc = next((x for x in reg["locations"] if x.get("form") == "runtime"), None)
    spec = pkg.document.get("runtime")
    if loc is None or spec is None:
        return None
    lock = pkg.content({"kind": "runtime", "source": spec["lock"]})
    report = runtime.inspect(host / loc["path"], lock)
    report.update(loc.get("runtime") or {})
    if report["state"] == "absent":
        report["hint"] = "run install on this host to build the environment"
    for item in out.items:
        if item.get("path") == loc["path"] and report["state"] != "matching":
            item["state"] = report["state"]
    if report["state"] != "matching" and not any(d["path"] == loc["path"] for d in out.divergences):
        out.divergences.append({"path": loc["path"], "address": None, "state": report["state"]})
    return report


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _elsewhere(host: Path, running: Path, capability: str) -> str:
    """Which engine can do what the running one may not: the host's main Kaelen, else the
    producer's package (specs/026 FR-011)."""
    main = host / homes.MAIN
    if (main / "run.py").is_file() and not _inside(running, main):
        return (
            f"run it with the host's main Kaelen ({homes.MAIN}/run.py rollback "
            f"--capability {capability})"
        )
    return f"run it from the run.py of {capability!r}'s package as its producer publishes it"


def _transient(host: Path, action: dict) -> bool:
    """The safety-net delete of the main Kaelen's contributions folder, while it is absent: the
    part this operation writes there is dropped once applied, so the host does not change
    (specs/031 FR-005)."""
    return (
        action.get("main") is True
        and action["op"] == "delete"
        and action["path"] == homes.CONTRIBUTIONS
        and not (host / homes.CONTRIBUTIONS).exists()
    )


def _contribution_action(host: Path, actions: list[dict], engine_version: str) -> dict | None:
    """The `contribute` action that gathers the plan's text actions on shared files (R-1, R-2)."""
    indices = [i for i, a in enumerate(actions) if a["op"] in applier.TEXT_OPS]
    if not indices:
        return None
    return {
        "op": "contribute",
        "path": homes.CONTRIBUTIONS,
        "indices": indices,
        "files": contributions.files_of(host, [actions[i] for i in indices]),
        "engine": engine_version,
    }


def _check_contributions(host: Path, op: dict, action: dict, out, runner) -> Problem | None:
    """Before anything is written: will the main Kaelen take this set? (FR-010, R-9)"""
    arriving = (out.main or {}).get("state") in ("deposited", "promoted")
    # the arriving engine is the running one, byte-identical to the main Kaelen it will become
    if arriving:
        ask = contributions.InProcess(action["engine"])
    else:
        ask = applier.runner_for(host, runner, action["engine"])
    request = {"mode": "check", "set": contributions.build_set(op, action, action["engine"])}
    try:
        doc = ask(contributions.main_run(host), host, request, None)
    except OSError as exc:
        return Problem(
            "main-unavailable",
            homes.MAIN,
            f"{exc}; shared files are written only by the main Kaelen: nothing was written",
        )
    if doc.get("verdict") == "checked":
        return None
    error = (doc.get("errors") or [{}])[0]
    message = str(error.get("message", doc.get("verdict")))
    if doc.get("minimum"):
        message += f"; the main Kaelen must be {doc['minimum']} or later (self-update)"
    rule = str(error.get("rule", "contribution-refused"))
    return Problem(rule, str(error.get("path", "")), message)


# --- provenance (specs/028) ----------------------------------------------------------------------


def _provenance_gate(out, host, pkg, reg, verb, declared, trust, allow_unsigned):
    """Origin and signature of the package, checked before anything is written (R-4..R-7, R-13).

    Returns (refusal or None, the registry fields to record).
    """
    from kaelen.package import distribution

    document = pkg.document
    found = provenance.origin(
        pkg.root, distribution.names(document)["distribution"], declared, provenance.DEFAULT_GIT
    )
    signer = document.get("signer")
    previous = (reg or {}).get("provenance") or {}
    report = {
        "origin": found,
        "previous_origin": (reg or {}).get("origin"),
        "signature": "absent",
        "signer": signer,
        "key": None,
        "trusted": False,
        "consents": [],
    }
    out.provenance = report
    consents = list(previous.get("consents") or [])
    record = (pkg.root / "kaelen-package.json").read_bytes()
    try:
        # the host's own trust first: a consent is needed (and recorded) only where it lacks
        signed = provenance.check_signature(
            pkg.root, record, signer, host, provenance.DEFAULT_KEYGEN
        )
        consented_trust = False
        if trust and signed.state == "valid" and trust == signer and not signed.trusted:
            signed = provenance.check_signature(
                pkg.root, record, signer, host, provenance.DEFAULT_KEYGEN, trust_also=trust
            )
            consented_trust = signed.trusted
    except provenance.NotChecked as exc:
        return Problem(
            "keygen-unavailable",
            provenance.SIGNATURE,
            f"{exc}; the package is signed and its signature must be checked before installing",
        ), None
    except provenance.TrustUnreadable as exc:
        return Problem("trust-unreadable", provenance.TRUST, str(exc)), None
    report.update(signature=signed.state, key=signed.key, trusted=signed.trusted)
    if trust and signed.state == "absent":
        out.findings.append(
            Problem(
                "trust-unused",
                provenance.SIGNATURE,
                f"--trust {trust} was given but the package is not signed: nothing was trusted",
            )
        )
    if signed.state == "invalid":
        return Problem(
            "signature-invalid",
            provenance.SIGNATURE,
            "the package's signature does not verify for its record: it was altered or signed for "
            "another package; nothing was written",
        ), None
    if signed.state == "valid" and trust and trust != signer:
        return Problem(
            "signer-untrusted",
            provenance.SIGNATURE,
            f"--trust names {trust!r} but the package is signed by {signer!r}",
        ), None
    if signed.state == "valid" and not signed.trusted:
        return Problem(
            "signer-untrusted",
            provenance.SIGNATURE,
            f"the package is signed by {signer!r} ({signed.key}), which this host does not trust: "
            f"pass --trust {signer} to accept it for this operation, or add it with "
            f"`kaelen trust add` ({signed.line})",
        ), None
    if consented_trust:
        consents.append({"kind": "trust", "signer": signer, "operation": verb})
        report["consents"].append(consents[-1])
    # pinning (Q-1): once installed signed, a signature stays expected, also after a consented
    # unsigned update
    earlier = previous.get("pinned") or previous.get("signer")
    pinned = previous.get("pinned") or previous.get("signature") == "valid"
    expected = bool(signer) or bool(pinned)
    if signed.state == "absent" and expected:
        if not allow_unsigned:
            why = (
                f"the declaration names signer {signer!r}"
                if signer
                else f"it was installed signed by {earlier!r}"
            )
            return Problem(
                "signature-missing",
                provenance.SIGNATURE,
                f"the package is not signed but {why}: pass --allow-unsigned to accept it for "
                "this operation",
            ), None
        consents.append(
            {
                "kind": "unsigned",
                "signer": signer or previous.get("pinned") or previous.get("signer"),
                "operation": verb,
            }
        )
        report["consents"].append(consents[-1])
    fields = {
        "origin": found,
        "provenance": {
            "signature": signed.state if signed.state == "valid" else "absent",
            "signer": signer if signed.state == "valid" else None,
            "key": signed.key,
            "consents": consents,
        },
    }
    pin = (
        (signer if signed.state == "valid" else None)
        or previous.get("pinned")
        or (previous.get("signer") if previous.get("signature") == "valid" else None)
    )
    if pin:
        fields["provenance"]["pinned"] = pin
    return None, fields


def _signer_note(out, host, root, reg) -> None:
    """Uninstall never depends on provenance; it only says when the signer is no longer trusted."""
    recorded = reg.get("provenance") or {}
    if recorded.get("signature") != "valid":
        return
    record = root / "kaelen-package.json"
    try:
        signed = provenance.check_signature(
            root, record.read_bytes(), recorded.get("signer"), host, provenance.DEFAULT_KEYGEN
        )
    except (provenance.NotChecked, provenance.TrustUnreadable, OSError):
        return
    if signed.state == "invalid":  # never a refusal at uninstall (R-6), always said
        out.findings.append(
            Problem(
                "signature-invalid",
                provenance.SIGNATURE,
                "the deposited package's signature no longer verifies; uninstalling anyway",
            )
        )
    elif signed.state == "valid" and not signed.trusted:
        out.findings.append(_untrusted(recorded.get("signer")))


def _untrusted(signer) -> Problem:
    return Problem(
        "signer-untrusted",
        provenance.TRUST,
        f"signer {signer!r} is no longer trusted by this host: uninstall stays possible; an "
        "update will need a package signed by a trusted signer",
    )


def _provenance_verify(out, host, reg, online: bool, timeout: float) -> str:
    """What verify says of provenance (R-8..R-10); returns the online check's result."""
    origin = reg.get("origin")
    recorded = reg.get("provenance") or {}
    report = {
        "origin": origin,
        "signature": recorded.get("signature", "unknown"),
        "signer": recorded.get("signer"),
        "trusted": None,
        "signature_check": "skipped",
        "check": "skipped",
    }
    out.provenance = report
    if origin is None:
        out.findings.append(
            Problem(
                "provenance-unknown",
                registry.relative(reg["capability"], host),
                "no origin is recorded for this capability (installed by an engine before 0.14.0, "
                "or its origin was not known)",
            )
        )
    deposit = host / homes.new(reg["node"], reg["capability"]).package
    if recorded.get("signature") == "valid":
        try:
            signed = provenance.check_signature(
                deposit,
                (deposit / "kaelen-package.json").read_bytes(),
                recorded.get("signer"),
                host,
                provenance.DEFAULT_KEYGEN,
            )
        except provenance.NotChecked as exc:
            report["signature_check"] = "not-checked"
            out.findings.append(
                Problem("signature-not-checked", provenance.SIGNATURE, f"{exc}: not checked")
            )
        except (provenance.TrustUnreadable, OSError) as exc:
            report["signature_check"] = "not-checked"
            out.findings.append(Problem("signature-not-checked", provenance.SIGNATURE, str(exc)))
        else:
            report["signature_check"] = "rechecked"
            report["trusted"] = signed.trusted
            if signed.state != "valid":
                out.findings.append(
                    Problem(
                        "signature-invalid",
                        provenance.SIGNATURE,
                        "the deposited package's signature no longer verifies",
                    )  # fmt: skip
                )
                out.divergences.append({"path": provenance.SIGNATURE, "state": "invalid"})
            elif not signed.trusted:
                out.findings.append(_untrusted(recorded.get("signer")))
    if not online:
        return "skipped"
    left: list[str] = []
    check, details = _fetch_and_compare(host, reg, deposit, timeout, left)
    for message in left:
        out.findings.append(Problem("provenance-temp-left", "", message))
    report["check"] = check
    if check == "not-checked":
        report["cause"] = details
        out.findings.append(Problem("provenance-not-checked", "", details))
    elif check in ("differs", "mismatch"):
        report["files"] = details if check == "differs" else []
        rule = "provenance-differs" if check == "differs" else "provenance-mismatch"
        message = (
            f"the deposited copy differs from {origin.get('repository')}@{origin.get('commit')}: "
            + ", ".join(details)
            if check == "differs"
            else details
        )
        out.findings.append(Problem(rule, "", message))
    return check


def _fetch_and_compare(host, reg, deposit, timeout, left: list[str]) -> tuple[str, object]:
    """Fetch the recorded commit outside the host and compare it with the deposit (R-8)."""
    import tempfile

    from kaelen.package import record as package_record

    origin = reg.get("origin") or {}
    if not origin.get("repository"):
        return "not-checked", "no origin is recorded"
    if not origin.get("resolved"):
        return "not-checked", f"the recorded commit {origin.get('commit')!r} is not resolved"
    if not deposit.is_dir():
        return "not-checked", "no deposited copy of the package to compare"
    tmp = Path(tempfile.mkdtemp(prefix="kaelen-provenance-"))
    try:
        try:
            fetched = provenance.DEFAULT_FETCHER.fetch(
                origin["repository"], origin["commit"], origin.get("subdirectory"), tmp, timeout
            )
        except provenance.NotChecked as exc:
            return "not-checked", str(exc)
        rec = fetched / package_record.FILENAME
        if not rec.is_file():
            return "mismatch", (
                f"{origin.get('subdirectory')!r} at {origin['commit']} holds no Kaelen package"
            )
        try:
            theirs = json.loads(rec.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return "mismatch", f"the package record at {origin['commit']} cannot be read"
        if (theirs.get("node"), theirs.get("capability")) != (reg["node"], reg["capability"]):
            return "mismatch", (
                f"{origin['commit']} holds {theirs.get('node')}/{theirs.get('capability')}, "
                f"not {reg['node']}/{reg['capability']}"
            )
        mine = _tree(deposit)
        found = _tree(fetched)
        differs = sorted(rel for rel in set(mine) | set(found) if mine.get(rel) != found.get(rel))
        return ("differs", differs) if differs else ("confirmed", None)
    finally:
        try:
            provenance.remove_tree(tmp)
        except OSError as exc:  # never silently: the folder is outside the host (FR-009)
            left.append(f"the temporary folder {tmp} could not be removed: {exc}")


def _tree(root: Path) -> dict:
    import hashlib

    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.relative_to(root).parts
    }


def trust(
    host: Path,
    action: str,
    principal: str | None,
    key_file: Path | None = None,
    package: Path | None = None,
    *,
    dry_run: bool = False,
    writer: applier.Writer | None = None,
) -> HostOutcome:
    """The host's trusted signers, changed only by the operator (specs/028 R-12)."""
    writer = writer or applier.Writer()
    out = HostOutcome(f"trust-{action}", host.as_posix(), None, dry_run, "internal")
    out.principal = principal if action in ("add", "remove") else None

    def stop(verdict: str, rule: str, message: str) -> HostOutcome:
        out.verdict = verdict
        out.errors.append(Problem(rule, provenance.TRUST, message))
        return out

    if not host.is_dir():
        return stop("unable-to-check", "host-not-directory", f"{host.as_posix()!r} is not a folder")
    try:
        current = provenance.read_trust(host)
    except provenance.TrustUnreadable as exc:
        return stop("refused", "trust-unreadable", str(exc))

    def listing(entries) -> list[dict]:
        return [
            {"principal": p, "keytype": t, "key": provenance.fingerprint(k)} for p, t, k in entries
        ]

    if action == "list":
        out.trust = listing(current)
        out.verdict = "listed"
        return out
    if action == "add":
        try:
            if key_file is not None:
                parts = key_file.read_text(encoding="utf-8").split()
                keytype, key = parts[0], parts[1]
            else:
                keytype, key = provenance.public_key((package / provenance.SIGNATURE).read_bytes())
        except (OSError, IndexError, ValueError) as exc:
            return stop("refused", "key-unreadable", f"cannot read the signer's public key: {exc}")
        wanted = [*current, (principal, keytype, key)]
        if (principal, keytype, key) in current:
            out.trust = listing(current)
            out.verdict = "trusted"
            return out
        out.changes = [{"op": "add", "path": provenance.TRUST,
                        "address": provenance.trust_line(principal, keytype, key)}]  # fmt: skip
    else:
        wanted = [e for e in current if e[0] != principal]
        if len(wanted) == len(current):
            out.verdict = "not-trusted"
            return out
        out.changes = [{"op": "remove", "path": provenance.TRUST, "address": principal}]
    out.trust = listing(wanted)
    if dry_run:
        out.verdict = "would-trust" if action == "add" else "would-remove"
        return out
    text = "".join(provenance.trust_line(*e) + "\n" for e in wanted)
    try:
        writer.write(host / provenance.TRUST, text.encode("utf-8"))
    except OSError as exc:
        return stop("incomplete", "write-failed", f"cannot write {provenance.TRUST}: {exc}")
    out.verdict = "trusted" if action == "add" else "removed"
    return out


# --- dependencies and groups (specs/029) ---------------------------------------------------------


class _GroupChoice(Exception):
    """A choice of groups that cannot be applied: nothing is written."""

    def __init__(self, rule: str, message: str):
        super().__init__(message)
        self.rule, self.message = rule, message


def _selection(document, reg, verb, with_groups, without_groups) -> tuple[list[dict], list[str]]:
    """(the items to install, the chosen groups): items in no group, the mandatory group, and the
    groups chosen; raises _GroupChoice on a choice that cannot be applied (R-4)."""
    groups = document.get("groups") or []
    declared = [g["name"] for g in groups]
    asked = [*with_groups, *without_groups]
    if not groups:
        if asked:
            raise _GroupChoice(
                "groups-undeclared",
                f"{document['capability']!r} declares no groups: --with and --without do not apply",
            )
        return list(document["items"]), [], {"added": [], "dropped": []}
    unknown = [g for g in asked if g not in declared]
    if unknown:
        raise _GroupChoice(
            "group-unknown",
            f"unknown group(s) {', '.join(unknown)}; declared: " + ", ".join(declared),
        )
    both = sorted(set(with_groups) & set(without_groups))
    mandatory = next((g["name"] for g in groups if g.get("mandatory")), None)
    if both or (mandatory and mandatory in without_groups):
        what = (
            f"{', '.join(both)} named in both --with and --without"
            if both
            else (f"{mandatory!r} is mandatory and cannot be left out")
        )
        raise _GroupChoice("group-contradiction", what)
    recorded = (reg or {}).get("groups") if verb in ("update", "verify", "uninstall") else None
    changes = {"added": [], "dropped": []}
    if recorded is not None:
        known = set(recorded.get("declared") or [])
        changes = {
            "added": [g for g in declared if g not in known],
            "dropped": [g for g in recorded.get("chosen") or [] if g not in declared],
        }
        chosen = [g for g in recorded.get("chosen") or [] if g in declared]
        chosen += [g["name"] for g in groups if g["name"] not in known and g.get("default", True)]
    else:
        chosen = [g["name"] for g in groups if g.get("default", True)]
    chosen = [g for g in declared if (g in chosen or g in with_groups) and g not in without_groups]
    if mandatory and mandatory not in chosen:
        chosen.insert(0, mandatory)
    grouped = {name for g in groups for name in g["items"]}
    wanted = {name for g in groups if g["name"] in chosen for name in g["items"]}
    items = [i for i in document["items"] if i["name"] not in grouped or i["name"] in wanted]
    return items, chosen, changes


def _requirement(req: dict) -> dict:
    return {k: req[k] for k in ("node", "capability", "version", "groups") if k in req}


def _installed_regs(host) -> dict:
    """(node, capability) -> registry, or the reason it cannot be read."""
    out = {}
    for place, reg in registry.everything(host):
        if isinstance(reg, Exception):
            out[(place.node, place.capability)] = reg
        else:
            out[(reg.get("node"), reg.get("capability"))] = reg
    return out


def _requirements(out, host, document, capability, report_only: bool = False) -> Problem | None:
    """Check each `requires` entry against the host (R-5); the first refusal, or None."""
    from kaelen import versions

    regs = _installed_regs(host)
    report, refusal = [], None
    for req in document.get("requires") or []:
        key = (req["node"], req["capability"])
        found = regs.get(key)
        if found is None:  # an old-layout registry is keyed by capability only
            found = next((r for (n, c), r in regs.items() if n is None and c == key[1]), None)
        entry = {**_requirement(req), "groups": req.get("groups") or [],
                 "source": req.get("source"), "found_version": None, "found_groups": None,
                 "satisfied": False, "why": ""}  # fmt: skip
        rule = None
        if isinstance(found, Exception):
            rule, entry["why"] = "requirement-unreadable", f"its registry cannot be read: {found}"
        elif found is None:
            rule, entry["why"] = "requirement-missing", "it is not installed on this host"
        else:
            entry["found_version"] = found.get("version")
            recorded = found.get("groups")
            entry["found_groups"] = None if recorded is None else recorded.get("chosen")
            try:
                inside = versions.satisfies(found.get("version", ""), req["version"])
            except versions.NotSemver:
                rule = "requirement-version"
                entry["why"] = f"its version {found.get('version')!r} is not semver"
            else:
                missing = [g for g in entry["groups"] if g not in (entry["found_groups"] or [])]
                if not inside:
                    rule = "requirement-version"
                    entry["why"] = f"version {found.get('version')} is installed"
                elif missing and recorded is None:
                    rule = "requirement-groups"
                    engine = (found.get("engine") or {}).get("version") or "0"
                    if _version_key(engine) >= _version_key("0.15.0"):
                        entry["why"] = f"it declares no groups ({', '.join(missing)} required)"
                    else:
                        entry["why"] = (
                            f"it was installed by engine {engine}, which records no groups: "
                            f"update it with a package of engine 0.15.0 or later to choose "
                            f"{', '.join(missing)}"
                        )
                elif missing:
                    rule = "requirement-groups"
                    entry["why"] = f"installed without group(s) {', '.join(missing)}"
                    entry["fix"] = f"update it with --with {','.join(missing)}"
                else:
                    entry["satisfied"] = True
        fix = entry.pop("fix", None)  # the remedy goes in the message, not in the report
        report.append(entry)
        if rule and refusal is None and not report_only:
            source = f"; get it with: {req['source']}" if req.get("source") else ""
            refusal = Problem(
                rule,
                f"requires {key[0]}/{key[1]}",
                f"{capability!r} requires {key[0]}/{key[1]} {req['version']}"
                + (f" with groups {', '.join(entry['groups'])}" if entry["groups"] else "")
                + f": {entry['why']}; "
                + (
                    fix
                    if fix
                    else "install a version in range"
                    if rule == "requirement-version"
                    else "update it to a version with those groups"
                    if rule == "requirement-groups" and entry["found_version"]
                    else "install it first"
                )  # fmt: skip
                + source,
            )
    if report:
        out.requirements = report
    return refusal


def _dependents(out, host, document, verb, chosen, consent) -> list[Problem]:
    """Installed capabilities that require this one and this operation would break (R-6)."""
    from kaelen import versions

    me = (document["node"], document["capability"])
    found = []
    for (node, cap), reg in _installed_regs(host).items():
        if (node, cap) == me:
            continue
        if isinstance(reg, Exception):
            out.findings.append(
                Problem(
                    "dependent-unreadable",
                    f"{node}/{cap}" if node else str(cap),
                    f"the registry of {cap!r} cannot be read ({reg}): whether it requires "
                    f"{me[0]}/{me[1]} is not known",
                )
            )
            continue
        for req in reg.get("requires") or []:
            if (req.get("node"), req.get("capability")) != me:
                continue
            why = None
            if verb == "uninstall":
                why = "it would be removed"
            else:
                try:
                    if not versions.satisfies(document["version"], req.get("version", "")):
                        why = f"version {document['version']} is outside {req.get('version')}"
                except (versions.NotSemver, ValueError):
                    why = f"version {document['version']!r} cannot be checked against its range"
                lost = [g for g in req.get("groups") or [] if g not in chosen]
                if why is None and lost:
                    why = f"group(s) {', '.join(lost)} would no longer be installed"
            if why:
                found.append({"node": node, "capability": cap, "version": req.get("version"),
                              "groups": req.get("groups") or [], "why": why})  # fmt: skip
    if not found:
        return []
    out.dependents = [{**d, "broken": consent} for d in found]
    if consent:
        for d in found:
            out.findings.append(
                Problem(
                    "dependent-broken",
                    f"{d['node']}/{d['capability']}",
                    f"{d['node']}/{d['capability']} requires this capability and will be broken "
                    f"({d['why']}): consented with --break-dependents",
                )
            )
        return []
    return [
        Problem(
            "dependent-needs-it",
            f"{d['node']}/{d['capability']}",
            f"{d['node']}/{d['capability']} requires {me[0]}/{me[1]} {d['version']}: {d['why']}; "
            "pass --break-dependents to proceed anyway (the dependent is left as it is)",
        )
        for d in found
    ]


def _required_by(host, node, capability) -> list[dict]:
    out = []
    for (n, c), reg in _installed_regs(host).items():
        if isinstance(reg, Exception):
            continue
        for req in reg.get("requires") or []:
            if (req.get("node"), req.get("capability")) == (node, capability):
                out.append({"node": n, "capability": c, "version": req.get("version")})
    return out


def installed(host: Path) -> list[dict]:
    """Every capability recorded on `host`, in both layouts (FR-047; specs/026 FR-021).

    Read-only.
    """
    out = []
    for place, reg in registry.everything(host):
        layout = "old" if place.legacy else "new"
        if isinstance(reg, Exception):
            out.append(
                {
                    "capability": place.capability,
                    "state": "unreadable",
                    "reason": str(reg),
                    "layout": layout,
                }
            )
            continue
        out.append(
            {
                "capability": reg["capability"],
                "node": reg["node"],
                "version": reg["version"],
                "targets": reg["targets"],
                "engine": (reg.get("engine") or {}).get("version"),
                "layout": layout,
                "shared": _shared_writer(reg),
                "origin": reg.get("origin"),
                "signature": (reg.get("provenance") or {}).get("signature"),
                "requires": reg.get("requires") or [],
                "required_by": _required_by(host, reg["node"], reg["capability"]),
                "groups": reg.get("groups"),
            }
        )
    return sorted(out, key=lambda e: e["capability"])


def _unknown_record(op: dict) -> str | None:
    """Why an operation record is of a schema this engine must not touch (specs/026 FR-024)."""
    if op.get("broken"):
        return None
    schema = op.get("schema")
    if schema in (applier.SCHEMA, applier.SCHEMA_1):
        return None
    return (
        f"the operation record of {op.get('capability')!r} has schema {schema!r}, which this "
        f"engine does not know (supported: {applier.SCHEMA_1}, {applier.SCHEMA}); nothing was "
        "written: run the engine that wrote it"
    )


def _home_problem(host: Path, place: homes.Home) -> tuple[str, str] | None:
    """Why the capability's folder cannot be used (specs/026 FR-008, Q-5)."""
    parts = place.root.split("/")
    for depth in (1, 2):
        rel = "/".join(parts[:depth])
        if (host / rel).exists() and not (host / rel).is_dir():
            return ("home-not-folder", f"{rel} exists and is not a folder; nothing was written")
    folder = host / place.root
    if folder.is_file():
        return ("home-not-folder", f"{place.root} exists and is not a folder; nothing was written")
    if folder.is_dir() and any(folder.iterdir()) and not (folder / homes.RECORD).is_file():
        return (
            "home-occupied",
            f"{place.root}/ holds files no Kaelen registry lists; nothing was written",
        )
    return None


def _absent(host: Path, rel: str) -> list[str]:
    parts = rel.split("/")
    return [
        "/".join(parts[:i])
        for i in range(1, len(parts) + 1)
        if not (host / "/".join(parts[:i])).exists()
    ]


def _old_layout(out: HostOutcome, host: Path, place: homes.Home) -> None:
    for rel in place.old_paths():
        if (host / rel).exists():
            out.findings.append(
                Problem(
                    "old-layout",
                    rel,
                    f"{rel} holds {place.capability!r} in the old layout; its first update moves "
                    "it into its own folder",
                )
            )


def _plan_main(host: Path, verb: str, pkg, plan, place: homes.Home) -> dict:
    """The host's main Kaelen in this operation: deposited, promoted, kept or removed (R-7)."""
    before = homes.main_version(host)
    arriving = (pkg.record.get("engine") or {}).get("version")
    report = {"version": before, "state": "kept"}
    deposit = next((i for i, a in enumerate(plan.actions) if a["path"] == place.package), None)
    if verb in ("install", "update"):
        if before is None or (
            arriving and before != "unknown" and _version_key(arriving) > _version_key(before)
        ):
            action = {
                "op": "write",
                "path": homes.MAIN,
                "form": "directory",
                "content": [[rel, applier.encode(data)] for rel, data in pkg.engine()],
                "main": True,
            }
            plan.actions.append(action)
            report = {
                "version": arriving,
                "state": "deposited" if before is None else "promoted",
                "from": before,
            }
        return report
    if plan.registry_after is None and before is not None:
        remaining = [h for h in homes.homes(host) if h.capability != place.capability]
        remaining = [h for h in remaining if (host / h.registry).is_file()]
        if not remaining:
            action = {"op": "delete", "path": homes.MAIN, "form": "directory", "main": True}
            # the main Kaelen's part on shared files goes with it (specs/027 R-7)
            part = {"op": "delete", "path": homes.CONTRIBUTIONS, "form": "directory", "main": True}
            at = deposit if deposit is not None else len(plan.actions)
            plan.actions.insert(at, action)
            plan.actions.insert(at, part)
            plan.prune_dirs = sorted({*plan.prune_dirs, ".kaelen"})
            report = {"version": None, "state": "removed", "from": before}
    return report


def self_update(
    host: Path,
    package: Path | None,
    *,
    engine_version: str,
    dry_run: bool = False,
    writer: applier.Writer | None = None,
) -> HostOutcome:
    """Replace the host's main Kaelen with a newer engine, explicitly (specs/026 R-8, FR-020)."""
    writer = writer or applier.Writer()
    out = HostOutcome(
        "self-update", host.as_posix(), package.as_posix() if package else None, dry_run, "internal"
    )

    def stop(verdict: str, rule: str, message: str) -> HostOutcome:
        out.verdict = verdict
        out.errors.append(Problem(rule, homes.MAIN, message))
        return out

    if not host.is_dir():
        return stop("unable-to-check", "host-not-directory", f"{host.as_posix()!r} is not a folder")
    if package is None:
        return stop("unable-to-check", "no-package", "no package: pass --package")
    try:
        pkg = open_package(package)
    except PackageError as exc:
        return stop("unable-to-check", exc.rule, str(exc))
    arriving = (pkg.record.get("engine") or {}).get("version") or engine_version
    if not dry_run:
        _tidy_main(host, writer)
    before = homes.main_version(host)
    if before is not None and _version_key(arriving) <= _version_key(before):
        return stop(
            "refused",
            "not-newer",
            f"the main Kaelen is {before}; the engine offered is {arriving}, not newer: "
            "nothing was written",
        )
    out.main = {"version": arriving, "state": "promoted" if before else "deposited", "from": before}
    out.changes = [{"op": "write", "path": homes.MAIN}]
    if dry_run:
        out.verdict = "would-update"
        return out
    main = host / homes.MAIN
    fresh, old = main.with_name("engine.new"), main.with_name("engine.old")
    try:
        for rel, data in pkg.engine():
            writer.write(fresh / rel, data)
        if main.exists():
            writer.move(main, old)
        writer.move(fresh, main)
        if old.exists():
            writer.delete(old)
    except Exception as exc:  # declared, never hidden: the next run puts the old one back
        out.verdict = "incomplete"
        out.errors.append(Problem("write-failed", homes.MAIN, f"self-update stopped: {exc}"))
        return out
    out.verdict = "updated"
    return out


def self_remove(host: Path, *, dry_run: bool = False, writer=None) -> HostOutcome:
    """Remove the host's main Kaelen when no capability of the new layout needs it (R-7)."""
    writer = writer or applier.Writer()
    out = HostOutcome("self-remove", host.as_posix(), None, dry_run, "internal")
    before = homes.main_version(host)
    if before is None:
        out.verdict = "not-installed"
        return out
    using = sorted(h.capability for h in homes.homes(host) if (host / h.registry).is_file())
    if using:
        out.verdict = "refused"
        out.errors.append(
            Problem(
                "main-in-use",
                homes.MAIN,
                f"capabilities of this host rely on the main Kaelen: {', '.join(using)}; "
                "it goes with the last of them",
            )
        )
        return out
    out.main = {"version": None, "state": "removed", "from": before}
    out.changes = [{"op": "delete", "path": homes.MAIN}]
    if dry_run:
        out.verdict = "would-uninstall"
        return out
    writer.delete(host / homes.MAIN)
    kaelen = host / ".kaelen"
    if kaelen.is_dir() and not any(kaelen.iterdir()):
        writer.rmdir(kaelen)
    out.verdict = "uninstalled"
    return out


def _tidy_main(host: Path, writer) -> None:
    """What a stopped self-update left: the old engine put back, the half-written new one gone."""
    main = host / homes.MAIN
    fresh, old = main.with_name("engine.new"), main.with_name("engine.old")
    if not main.exists() and old.exists():
        writer.move(old, main)
    elif old.exists():
        writer.delete(old)
    if fresh.exists():
        writer.delete(fresh)


# --- verify without a package: every capability by its own engine (specs/031 R-9) -----------------


class SubprocessVerify:
    """Runs a capability's deposited engine in its own process: `run.py verify --host H --json`."""

    def __call__(self, run_py: Path, host: Path, extra: list[str]):
        args = [sys.executable, "-I", "-B", str(run_py), "verify", "--host", str(host), "--json"]
        try:
            done = subprocess.run(
                [*args, *extra],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=900,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return None, None, f"could not be run: {exc}"
        try:
            document = json.loads(done.stdout)
        except ValueError:
            document = None
        return done.returncode, document, done.stderr


class InProcessVerify:
    """The same engine's verify on the deposited package, called directly: for tests."""

    def __init__(self, engine_version: str):
        self.engine_version = engine_version

    def __call__(self, run_py: Path, host: Path, extra: list[str]):
        out = run(
            "verify",
            host,
            run_py.parent,
            engine_version=self.engine_version,
            live="--live" in extra,
            check_provenance="--provenance" in extra,
        )
        return out.exit_code, out.to_document(self.engine_version), ""


def verify_all(
    host: Path,
    capability: str | None = None,
    *,
    runner=None,
    live: bool = False,
    provenance: bool = False,
) -> HostVerification:
    """Verify every capability on `host` with the engine it deposited (specs/031 FR-009…FR-012).

    Each engine judges what it installed; this one only gathers the answers. Read-only.
    """
    runner = runner or SubprocessVerify()
    report = HostVerification(host.as_posix(), capability)
    found = registry.everything(host)
    names = sorted({where.capability for where, _ in found})
    if capability is not None and capability not in names:
        report.verdict = "usage"
        listed = ", ".join(names) or "none"
        report.reason = f"{capability!r} is not installed on this host; installed: {listed}"
        return report
    extra = (["--live"] if live else []) + (["--provenance"] if provenance else [])
    for where, reg in found:
        if capability is not None and where.capability != capability:
            continue
        entry = {
            "node": None,
            "capability": where.capability,
            "version": None,
            "verdict": "not-verifiable",
            "exit": 66,
            "document": None,
            "reason": None,
            "remedy": None,
            "run": None,
        }
        report.capabilities.append(entry)
        if isinstance(reg, Exception):
            entry["reason"] = f"registry unreadable: {reg}"
            entry["remedy"] = f"inspect {where.registry}; verify with the producer's package"
            continue
        entry.update(node=reg.get("node"), version=reg.get("version"))
        if where.legacy:
            entry["reason"] = "old layout: no deposited package"
            entry["remedy"] = (
                f"update {where.capability!r} once with its producer's package; "
                "until then verify with that package"
            )
            continue
        run_py = host / homes.new(reg["node"], reg["capability"]).package / "run.py"
        entry["run"] = run_py.relative_to(host).as_posix()
        if not run_py.is_file():
            entry["reason"] = f"no deposited package: {entry['run']} is missing"
            entry["remedy"] = (
                f"verify {where.capability!r} with its producer's package (--package); "
                "an update with it deposits the copy again"
            )
            continue
        code, document, stderr = runner(run_py, host, extra)
        if not isinstance(document, dict) or document.get("verdict") not in VERIFY_SEVERITY:
            lines = (stderr or "").strip().splitlines()
            cause = lines[-1] if lines else f"exit {code}, no JSON answer"
            entry["reason"] = f"its engine gave no verify result: {cause}"
            entry["remedy"] = f"run {entry['run']} verify --host . to see the failure"
            continue
        entry.update(verdict=document["verdict"], exit=code, document=document)
        unreadable = [
            e for e in document.get("errors") or [] if e.get("rule") == "package-unreadable"
        ]
        if unreadable:  # the deposited copy itself is incomplete (specs/033 FR-004)
            entry["reason"] = unreadable[0].get("message")
            entry["remedy"] = (
                "update or reinstall from the producer's package on a machine that has these "
                "files, then commit the capability folder"
            )
    if not report.capabilities:
        report.verdict = "nothing-installed"
        return report

    def rank(entry):
        verdict = "unable-to-check" if entry["verdict"] == "not-verifiable" else entry["verdict"]
        return VERIFY_SEVERITY.index(verdict), verdict

    report.verdict = min(rank(e) for e in report.capabilities)[1]
    return report
