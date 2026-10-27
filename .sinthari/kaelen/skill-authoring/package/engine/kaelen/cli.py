"""`kaelen` command line (specs/014-declaration-contract/contracts/cli.md)."""

from __future__ import annotations

import argparse
import sys
from importlib import metadata
from pathlib import Path

from kaelen.contract import supported_versions
from kaelen.contract.schema_eval import UnsupportedKeyword
from kaelen.outcome import (
    EXIT_CODES,
    VALID,
    Outcome,
    PackageOutcome,
    error_envelope,
    render_json,
)
from kaelen.package import package
from kaelen.placement import UNKNOWN, RuleError, load_rule, place, rule_digest
from kaelen.validate import validate


class UsageError(Exception):
    pass


HOST_VERBS = ("install", "update", "uninstall", "verify")


class _Parser(argparse.ArgumentParser):
    # argparse exits with 2 on bad arguments; the contract says 64 (EX_USAGE).
    def error(self, message):
        raise UsageError(message)


def engine_version() -> str:
    """Derived from the installed distribution, never from a constant beside it."""
    try:
        return metadata.version("kaelen")
    except metadata.PackageNotFoundError:
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="kaelen", description="Kaelen install engine.")
    parser.add_argument("--version", action="store_true", help="print the engine version")
    sub = parser.add_subparsers(dest="command", parser_class=_Parser)

    v = sub.add_parser("validate", help="check a declaration against its contract")
    v.add_argument("declaration", type=Path)
    v.add_argument("--producer", type=Path, help="producer repository to check sources against")
    v.add_argument("--json", action="store_true", help="machine-readable output")

    c = sub.add_parser("contracts", help="list the contract versions this engine supports")
    c.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("package", help="build the self-contained package of a capability")
    p.add_argument("declaration", type=Path)
    p.add_argument("--producer", type=Path, required=True, help="the producer repository")
    p.add_argument("--dry-run", action="store_true", help="report what would be packaged")
    p.add_argument(
        "--sign-key",
        type=Path,
        help="sign the package record with this SSH key (the declaration names the signer)",
    )
    p.add_argument("--json", action="store_true", help="machine-readable output")

    r = sub.add_parser("placement", help="list the placement rule, or ask where an item goes")
    r.add_argument("--target", help="assistant target of the query")
    r.add_argument("--kind", help="item kind of the query")
    r.add_argument(
        "--qualifier",
        help="extension point (instruction-block), event (hook) or git file (git-lines)",
    )
    r.add_argument("--name", help="item name, to resolve the locations")
    r.add_argument("--capability", help="capability name, to resolve the locations")
    r.add_argument("--directory", help="host directory of a git-lines item (default: the root)")
    r.add_argument("--node", help="node name, to resolve the capability's home .<node>/kaelen/")
    r.add_argument("--json", action="store_true", help="machine-readable output")

    helps = {
        "install": "install the package's capability into a host",
        "update": "bring an installed capability to this package's release",
        "uninstall": "remove what the capability installed",
        "verify": "compare what is installed with what was recorded",
    }
    for verb, text in helps.items():
        h = sub.add_parser(verb, help=text)
        h.add_argument(
            "--host",
            type=Path,
            help="the host repository (default: the one holding this package's copy)",
        )
        h.add_argument(
            "--package", type=Path, help="the package (default: the one carrying this engine)"
        )
        h.add_argument("--json", action="store_true", help="machine-readable output")
        if verb in ("install", "update", "uninstall"):
            h.add_argument("--target", action="append", default=[], help="assistant target")
            h.add_argument("--dry-run", action="store_true", help="report the plan, write nothing")
            h.add_argument(
                "--authorise",
                action="append",
                default=[],
                metavar="PATH",
                help="consent to replacing or removing exactly this host file",
            )
        if verb == "verify":
            h.add_argument(
                "--capability",
                help="without a package: verify only this installed capability",
            )
            h.add_argument(
                "--live",
                action="store_true",
                help="also start each MCP server, handshake and list its tools (runs its code)",
            )
            h.add_argument(
                "--live-timeout",
                type=float,
                default=10.0,
                metavar="SECONDS",
                help="time limit per MCP server for --live (default 10)",
            )
        if verb in ("install", "update", "uninstall"):
            h.add_argument(
                "--break-dependents",
                action="store_true",
                help="proceed although installed capabilities require this one (left as they are)",
            )
        if verb in ("install", "update"):
            h.add_argument(
                "--with",
                dest="with_groups",
                action="append",
                default=[],
                metavar="GROUP",
                help="install this group of the capability (repeatable)",
            )
            h.add_argument(
                "--without",
                dest="without_groups",
                action="append",
                default=[],
                metavar="GROUP",
                help="leave this group out (repeatable; never the mandatory one)",
            )
            h.add_argument(
                "--origin",
                help="where this package came from: git+URL@COMMIT#subdirectory=PATH",
            )
            h.add_argument(
                "--trust",
                metavar="SIGNER",
                help="accept, for this operation only, a valid signature by this untrusted signer",
            )
            h.add_argument(
                "--allow-unsigned",
                action="store_true",
                help="accept, for this operation only, an unsigned package where one is expected",
            )
        if verb == "verify":
            h.add_argument(
                "--provenance",
                action="store_true",
                help="fetch the recorded commit (online) and compare it with the deposited copy",
            )
            h.add_argument(
                "--provenance-timeout",
                type=float,
                default=60.0,
                metavar="SECONDS",
                help="time limit per fetch for --provenance (default 60)",
            )
        if verb == "update":
            h.add_argument(
                "--allow-downgrade",
                action="store_true",
                help="accept an older package or engine than the installed one",
            )
    b = sub.add_parser("rollback", help="undo an interrupted operation from its copies")
    b.add_argument(
        "--host", type=Path, help="the host repository (default: the one holding this package)"
    )
    b.add_argument("--capability", help="the capability whose interrupted operation to undo")
    b.add_argument("--package", type=Path, help="a package of the capability (for its name)")
    b.add_argument("--dry-run", action="store_true", help="report what would be restored")
    b.add_argument(
        "--authorise",
        action="append",
        default=[],
        metavar="PATH",
        help="consent to restoring exactly this location, changed since the interruption",
    )
    b.add_argument("--json", action="store_true", help="machine-readable output")
    i = sub.add_parser("installed", help="list the capabilities recorded on a host")
    i.add_argument("--host", type=Path, required=True, help="the host repository")
    i.add_argument("--json", action="store_true", help="machine-readable output")
    u = sub.add_parser("self-update", help="replace the host's main Kaelen with a newer engine")
    u.add_argument("--host", type=Path, required=True, help="the host repository")
    u.add_argument(
        "--package", type=Path, help="the package whose engine to use (default: this one)"
    )
    u.add_argument("--dry-run", action="store_true", help="report the replacement, write nothing")
    u.add_argument("--json", action="store_true", help="machine-readable output")
    x = sub.add_parser("self-remove", help="remove the host's main Kaelen when nothing needs it")
    x.add_argument("--host", type=Path, required=True, help="the host repository")
    x.add_argument("--dry-run", action="store_true", help="report the removal, write nothing")
    x.add_argument("--json", action="store_true", help="machine-readable output")
    d = sub.add_parser("draft", help="write a declaration draft from the producer's layout")
    d.add_argument("--producer", type=Path, help="the producer repository")
    d.add_argument("--base", help="the folder, inside the producer, where the conventions start")
    d.add_argument("--declaration", type=Path, help="the declaration (default: in the producer)")
    d.add_argument("--dry-run", action="store_true", help="report the draft, write nothing")
    d.add_argument("--replace", action="store_true", help="overwrite a different existing draft")
    d.add_argument("--conventions", action="store_true", help="list the layout conventions")
    d.add_argument("--json", action="store_true", help="machine-readable output")
    t = sub.add_parser("trust", help="the host's trusted package signers (main Kaelen)")
    t.add_argument("action", choices=["add", "remove", "list"])
    t.add_argument("--host", type=Path, required=True, help="the host repository")
    t.add_argument("--principal", help="the signer's name, as packages declare it")
    t.add_argument("--key", type=Path, help="add: the signer's public key file")
    t.add_argument("--package", type=Path, help="add: a package signed by the signer")
    t.add_argument("--dry-run", action="store_true", help="show the change, write nothing")
    t.add_argument("--json", action="store_true", help="machine-readable output")
    c = sub.add_parser(
        "contribute",
        help="(between engines) the main Kaelen applies contributions to shared files",
    )
    c.add_argument("--host", type=Path, required=True, help="the host repository")
    mode = c.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="check the set on stdin, write nothing")
    mode.add_argument("--rollback", action="store_true", help="roll back a capability's part")
    mode.add_argument("--release", action="store_true", help="drop a part whose operation ended")
    c.add_argument("--capability", help="the capability whose part to roll back or release")
    c.add_argument("--serves", help="the operation the part to release served")
    c.add_argument("--dry-run", action="store_true", help="say what it would write, write nothing")
    c.add_argument("--json", action="store_true", help="machine-readable output")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    want_json = "--json" in argv
    try:
        args = build_parser().parse_args(argv)
        if args.version:
            print(f"kaelen {engine_version()}")
            return EXIT_CODES["VALID"]
        if args.command is None:
            raise UsageError(
                "a command is required: validate, contracts, package, placement, "
                "install, update, uninstall, verify, rollback, installed, self-update, "
                "self-remove, contribute, trust, draft"
            )
        if args.command == "contracts":
            return _contracts(args.json)
        if args.command == "package":
            return _package(args)
        if args.command == "placement":
            return _placement(args)
        if args.command in HOST_VERBS:
            return _host(args)
        if args.command == "rollback":
            return _rollback(args)
        if args.command == "installed":
            return _installed(args)
        if args.command in ("self-update", "self-remove"):
            return _main_kaelen(args)
        if args.command == "contribute":
            return _contribute(args)
        if args.command == "trust":
            return _trust(args)
        if args.command == "draft":
            return _draft(args)
        return _validate(args)
    except UsageError as exc:
        return _fail("USAGE", f"usage error: {exc}", "run 'kaelen --help'", want_json)
    except UnsupportedKeyword as exc:
        return _fail("INTERNAL", f"engine defect: {exc}", None, want_json)
    except RuleError as exc:
        return _fail("INTERNAL", f"engine defect: {exc}", None, want_json)


def _contribute(args) -> int:
    """The main Kaelen's side of the contribution protocol (specs/027 contracts)."""
    import json

    from kaelen.host import apply as applier
    from kaelen.host import contributions

    if args.rollback or args.release:
        if not args.capability or (args.release and not args.serves):
            raise UsageError(
                "--rollback needs --capability; --release needs --capability and --serves"
            )
        request = {
            "mode": "rollback" if args.rollback else "release",
            "capability": args.capability,
            "serves": args.serves,
            "dry_run": args.dry_run,
        }
    else:
        try:
            payload = json.loads(sys.stdin.read() or "null")
        except ValueError as exc:
            payload = None
            print(f"the contribution set is not JSON: {exc}", file=sys.stderr)
        request = {"mode": "check" if args.check else "apply", "set": payload,
                   "dry_run": args.dry_run}  # fmt: skip
    doc = contributions.command(args.host, request, applier.Writer(), engine_version())
    human = (
        doc["verdict"].upper()
        + "\n"
        + "".join(f"  {error['rule']}: {error['message']}\n" for error in doc["errors"])
    )
    code = contributions.EXIT.get(doc["verdict"], 70)
    if args.json:
        sys.stdout.write(render_json(doc))
        if code != 0:  # stderr carries the human form, as for every verb (I.)
            sys.stderr.write(human)
    else:
        sys.stdout.write(human)
    return code


def _fail(code: str, message: str, hint: str | None, want_json: bool) -> int:
    if want_json:
        sys.stdout.write(render_json({"error": error_envelope(code, message, hint)}))
    print(message, file=sys.stderr)
    return EXIT_CODES[code]


def _contracts(want_json: bool) -> int:
    versions = supported_versions()
    if want_json:
        sys.stdout.write(
            render_json(
                {
                    "schema": "kaelen.contracts/1",
                    "engine": {"version": engine_version()},
                    "supported": versions,
                }
            )
        )
    else:
        print("supported contract versions: " + ", ".join(str(v) for v in versions))
    return EXIT_CODES["VALID"]


def _placement(args) -> int:
    """`kaelen placement` (specs/016-placement-rule/contracts/cli.md)."""
    if (args.target is None) != (args.kind is None):
        raise UsageError("--target and --kind go together")
    if args.target is None and any((args.qualifier, args.name, args.capability)):
        raise UsageError("--qualifier, --name and --capability need --target and --kind")
    rule = load_rule()
    head = {"schema": "kaelen.placement/1", "engine": {"version": engine_version()}}
    if args.target is None:
        doc = {
            **head,
            "rule": {
                "schema": rule["schema"],
                "contract": rule["contract"],
                "digest": rule_digest(rule),
                "targets": list(rule["targets"]),
            },
            "entries": rule["entries"],
        }
        if args.json:
            sys.stdout.write(render_json(doc))
        else:
            sys.stdout.write(render_rule_human(doc))
        return EXIT_CODES["VALID"]
    answer = place(
        args.target,
        args.kind,
        args.qualifier,
        args.name,
        args.capability,
        args.directory,
        args.node,
    )
    doc = {**head, "rule": {"digest": rule_digest(rule)}, **answer}
    code = "INVALID" if answer["outcome"] == UNKNOWN else "VALID"
    headline = _placement_line(answer)
    if args.json:
        if code != "VALID":
            doc["error"] = error_envelope(code, headline, "run 'kaelen placement' to list the rule")
        sys.stdout.write(render_json(doc))
        if code != "VALID":
            print(headline, file=sys.stderr)
    else:
        print(headline)
    return EXIT_CODES[code]


def _entry_label(e: dict) -> str:
    q = f"/{e['qualifier']}" if e.get("qualifier") else ""
    return f"{e['target']} {e['kind']}{q}"


def _placement_line(answer: dict) -> str:
    q = answer["query"]
    label = _entry_label(q)
    if answer["outcome"] == UNKNOWN:
        return f"{label}: unknown to the rule ({answer['unknown']})"
    ev = answer["evidence"]
    if answer["outcome"] == "unsupported":
        return f"{label}: unsupported ({answer['reason']}) - {answer['detail']}"
    where = ", ".join(
        f"{loc['path'] or loc['pattern']}"
        + (f" @ {loc['section']}" if loc["section"] else "")
        + f" [{loc['wrapper']}]"
        for loc in answer["locations"]
    )
    return f"{label}: placed -> {where} ({ev['basis']} {ev['verified']})"


def render_rule_human(doc: dict) -> str:
    rule = doc["rule"]
    lines = [
        f"placement rule {rule['digest']} (contract {rule['contract']}): "
        f"{', '.join(rule['targets'])} - {len(doc['entries'])} entries"
    ]
    for e in doc["entries"]:
        ev = e["evidence"]
        if e["outcome"] == "unsupported":
            lines.append(f"{_entry_label(e)}: unsupported ({e['reason']}) - {e['detail']}")
            continue
        where = ", ".join(
            loc["pattern"]
            + (f" @ {loc['section']}" if loc["section"] else "")
            + f" [{loc['wrapper']}]"
            for loc in e["locations"]
        )
        lines.append(f"{_entry_label(e)}: placed -> {where} ({ev['basis']} {ev['verified']})")
    return "\n".join(lines) + "\n"


def _validate(args) -> int:
    outcome = validate(args.declaration, args.producer)
    if args.json:
        sys.stdout.write(render_json(outcome.to_document(engine_version())))
        if outcome.exit_code != 0:
            print(outcome.headline(), file=sys.stderr)
    else:
        sys.stdout.write(render_human(outcome))
    return outcome.exit_code


def _package(args) -> int:
    outcome = package(
        args.declaration, args.producer, engine_version(), args.dry_run, sign_key=args.sign_key
    )
    if args.json:
        sys.stdout.write(render_json(outcome.to_document(engine_version())))
        if outcome.exit_code != 0:
            print(outcome.headline(), file=sys.stderr)
    else:
        sys.stdout.write(render_package_human(outcome))
    return outcome.exit_code


def render_package_human(outcome: PackageOutcome) -> str:
    label = outcome.verdict.upper()
    if outcome.produced:
        items = len(outcome.record["files"]) if outcome.record else 0
        head = (
            f"{label} {outcome.package}: {items} file(s), {outcome.size['total']} bytes "
            f"(engine {outcome.size['engine']})"
        )
    else:
        head = f"{label} {outcome.declaration}: {outcome.headline()}"
    lines = [head]
    for p in outcome.errors:
        lines.append(_problem_line("ERROR", p))
    for p in outcome.findings:
        lines.append(_problem_line("FINDING", p))
    for e in outcome.left_out:
        lines.append(f"left out ({e['reason']}): {e['path']}")
    if outcome.not_run and not outcome.produced:
        lines.append("not checked: " + ", ".join(outcome.not_run))
    for t in outcome.targets or ():
        placed = sum(1 for i in t["items"] if i["outcome"] == "placed")
        missing = len(t["items"]) - placed
        lines.append(
            f"{t['target']}: {len(t['items'])} item(s), {placed} placed"
            + (f", {missing} not supported" if missing else "")
        )
    if outcome.produced and outcome.launch:
        sub = outcome.launch["subdirectory"]
        if outcome.launch["uvx"]:
            lines.append(
                f'launch: uvx --from "git+<repository>@<reference>#subdirectory={sub}" '
                f"{outcome.launch['command']} <verb> ..."
            )
        lines.append(f"launch: python {sub}/run.py <verb> ...")
    return "\n".join(lines) + "\n"


def render_human(outcome: Outcome) -> str:
    lines = [f"{outcome.symbol} {outcome.declaration}: {outcome.headline()}"]
    for p in outcome.errors:
        lines.append(_problem_line("ERROR", p))
    for p in outcome.findings:
        lines.append(_problem_line("FINDING", p))
    if outcome.not_run:
        lines.append("not checked: " + ", ".join(outcome.not_run))
    if outcome.verdict == VALID and outcome.summary:
        s = outcome.summary
        items = ", ".join(f"{k} {n}" for k, n in s["items"].items())
        lines.append(
            f"{s['node']}/{s['capability']} {s['version']} (contract {s['contract']}) "
            f"for {', '.join(s['targets'])}: {items}"
        )
    return "\n".join(lines) + "\n"


def _problem_line(label: str, p) -> str:
    known = f" (known: {', '.join(p.known)})" if p.known else ""
    return f"{label} {p.path or '<document>'}: {p.message}{known} [{p.rule}]"


def _host(args) -> int:
    """The host verbs (specs/017-host-verbs/contracts/cli.md)."""
    from kaelen import host as host_verbs
    from kaelen.host.consent import NON_INTERACTIVE, ConsentUsage, Interaction, authorised
    from kaelen.host.source import carrying_package

    try:
        allowed = authorised(getattr(args, "authorise", []))
    except ConsentUsage as exc:
        raise UsageError(str(exc)) from exc
    package = args.package or carrying_package(Path(__file__).resolve().parent)
    if getattr(args, "capability", None) and package is not None:
        raise UsageError("--capability is for verify without a package: drop one of them")
    if package is None and args.command == "verify":
        return _verify_all(args)
    if package is None:
        raise UsageError("no package: run from a package's run.py or pass --package")
    origin = getattr(args, "origin", None)
    if origin:
        from kaelen import provenance

        if provenance.parse_reference(origin) is None:
            raise UsageError(
                f"--origin {origin!r} is not a git reference: git+URL@COMMIT#subdirectory=PATH"
            )
    outcome = host_verbs.run(
        args.command,
        _host_of(args, package),
        package,
        engine_version=engine_version(),
        targets=getattr(args, "target", []),
        dry_run=getattr(args, "dry_run", False),
        allowed=allowed,
        interaction=NON_INTERACTIVE if args.json else Interaction(),
        allow_downgrade=getattr(args, "allow_downgrade", False),
        live=getattr(args, "live", False),
        live_timeout=getattr(args, "live_timeout", 10.0),
        origin=getattr(args, "origin", None),
        trust=getattr(args, "trust", None),
        allow_unsigned=getattr(args, "allow_unsigned", False),
        check_provenance=getattr(args, "provenance", False),
        provenance_timeout=getattr(args, "provenance_timeout", 60.0),
        with_groups=getattr(args, "with_groups", []),
        without_groups=getattr(args, "without_groups", []),
        break_dependents=getattr(args, "break_dependents", False),
    )
    if args.json:
        sys.stdout.write(render_json(outcome.to_document(engine_version())))
        if outcome.exit_code != 0:
            print(outcome.headline(), file=sys.stderr)
    else:
        sys.stdout.write(render_host_human(outcome))
    return outcome.exit_code


def _verify_all(args) -> int:
    """`verify` without a package: every capability, each by its own engine (specs/031 R-9)."""
    from kaelen import host as host_verbs

    if args.host is None:
        raise UsageError("--host is required to verify without a package")
    report = host_verbs.verify_all(
        args.host, args.capability, live=args.live, provenance=args.provenance
    )
    if report.verdict == "usage":
        raise UsageError(report.reason)
    if args.json:
        sys.stdout.write(render_json(report.to_document(engine_version())))
        if report.exit_code != 0:
            print(report.headline(), file=sys.stderr)
    else:
        sys.stdout.write(render_host_verification(report))
    return report.exit_code


def render_host_verification(report) -> str:
    lines = [f"{report.verdict.upper()} {report.headline()}"]
    for c in report.capabilities:
        what = f"{c['node'] or '?'}/{c['capability']} {c['version'] or '?'}"
        why = ""
        if c["verdict"] == "not-verifiable":
            why = f": {c['reason']}"
        elif c["verdict"] != "verified":
            error = (c["document"] or {}).get("error") or {}
            why = f": {error['message']}" if error.get("message") else ""
        lines.append(f"  {c['verdict']} {what}{why}")
        if c.get("remedy"):
            lines.append(f"    remedy: {c['remedy']}")
    hint = report.hint()
    if hint:
        lines.append(f"hint: {hint}")
    return "\n".join(lines) + "\n"


def _draft(args) -> int:
    """`kaelen draft` (specs/030): an aid outside the contract; the declaration is the author's."""
    from kaelen import draft as drafting

    if args.conventions:
        conv = drafting.conventions()
        outcome = drafting.DraftOutcome("listed", conventions=conv["conventions"])
    else:
        if args.producer is None:
            raise UsageError("draft needs --producer (or --conventions)")
        try:
            outcome = drafting.draft(
                args.producer,
                base=args.base,
                declaration=args.declaration,
                dry_run=args.dry_run,
                replace=args.replace,
            )
        except Exception as exc:  # an engine defect, never a refusal (exit 70, not 1)
            outcome = drafting.DraftOutcome("internal")
            outcome.errors.append(
                {"rule": "internal", "path": "", "message": f"engine defect: {exc!r}"}
            )
    if outcome.verdict == "usage" and not args.json:
        raise UsageError(outcome.errors[0]["message"])
    if args.json:
        sys.stdout.write(render_json(outcome.to_document(engine_version())))
        if outcome.exit_code != 0:  # stderr carries the human form, as for every verb (I.)
            sys.stderr.write(drafting.render_human(outcome))
    else:
        sys.stdout.write(drafting.render_human(outcome))
    return outcome.exit_code


def _trust(args) -> int:
    """`kaelen trust add|remove|list` (specs/028 R-12, contracts/provenance.md)."""
    from kaelen import host as host_verbs

    if args.action in ("add", "remove") and not args.principal:
        raise UsageError(f"trust {args.action} needs --principal")
    if args.action == "add" and (args.key is None) == (args.package is None):
        raise UsageError("trust add needs exactly one of --key or --package")
    outcome = host_verbs.trust(
        args.host, args.action, args.principal, args.key, args.package, dry_run=args.dry_run
    )
    if args.json:
        sys.stdout.write(render_json(outcome.to_document(engine_version())))
        if outcome.exit_code != 0:
            print(outcome.headline(), file=sys.stderr)
    else:
        sys.stdout.write(render_host_human(outcome))
        for entry in outcome.trust or []:
            print(f"  {entry['principal']} {entry['key']}")
    return outcome.exit_code


def _rollback(args) -> int:
    """Undo an interrupted operation (specs/021-rollback/contracts/cli.md)."""
    from kaelen import host as host_verbs
    from kaelen.host.consent import NON_INTERACTIVE, ConsentUsage, Interaction, authorised
    from kaelen.host.source import PackageError, carrying_package, open_package

    try:
        allowed = authorised(args.authorise)
    except ConsentUsage as exc:
        raise UsageError(str(exc)) from exc
    package = args.package or carrying_package(Path(__file__).resolve().parent)
    capability = args.capability
    if capability is None and package is not None:
        try:
            capability = open_package(package).document["capability"]
        except PackageError as exc:
            raise UsageError(f"cannot read the package for its capability: {exc}") from exc
    if capability is None:
        raise UsageError("rollback needs --capability NAME, or a package (--package DIR)")
    outcome = host_verbs.rollback(
        _host_of(args, package),
        capability,
        engine_version=engine_version(),
        package=package,
        dry_run=args.dry_run,
        allowed=allowed,
        interaction=NON_INTERACTIVE if args.json else Interaction(),
    )
    if args.json:
        sys.stdout.write(render_json(outcome.to_document(engine_version())))
        if outcome.exit_code != 0:
            print(outcome.headline(), file=sys.stderr)
    else:
        sys.stdout.write(render_host_human(outcome))
    return outcome.exit_code


def _host_of(args, package: Path | None) -> Path:
    """`--host`, or the host above a package kept in a capability's folder (specs/026 R-3)."""
    if args.host is not None:
        return args.host
    from kaelen.host.home import deposit_of

    found = deposit_of(package) if package is not None else None
    if found is None:
        raise UsageError("--host is required (this package is not kept on a host)")
    return found


def _main_kaelen(args) -> int:
    """`kaelen self-update` and `kaelen self-remove` (specs/026 R-8)."""
    from kaelen import host as host_verbs
    from kaelen.host.source import carrying_package

    if args.command == "self-update":
        package = args.package or carrying_package(Path(__file__).resolve().parent)
        outcome = host_verbs.self_update(
            args.host, package, engine_version=engine_version(), dry_run=args.dry_run
        )
    else:
        outcome = host_verbs.self_remove(args.host, dry_run=args.dry_run)
    if args.json:
        sys.stdout.write(render_json(outcome.to_document(engine_version())))
        if outcome.exit_code != 0:
            print(outcome.headline(), file=sys.stderr)
    else:
        sys.stdout.write(render_host_human(outcome))
    return outcome.exit_code


def _installed(args) -> int:
    from kaelen import host as host_verbs

    caps = host_verbs.installed(args.host)
    if args.json:
        doc = {
            "schema": "kaelen.installed/1",
            "engine": {"version": engine_version()},
            "host": args.host.as_posix(),
            "capabilities": caps,
        }
        sys.stdout.write(render_json(doc))
    else:
        if not caps:
            print("no capability recorded on this host")
        for c in caps:
            if c.get("state") == "unreadable":
                print(f"{c['capability']}: registry unreadable ({c['reason']})")
            else:
                layout = " [old layout: its first update moves it]" if c["layout"] == "old" else ""
                print(
                    f"{c['node']}/{c['capability']} {c['version']} for {', '.join(c['targets'])} "
                    f"(engine {c['engine']}){layout}"
                )
                print(f"  origin: {_origin_text(c.get('origin'))}")
                if c.get("signature"):
                    print(f"  signature: {c['signature']}")
                for r in c.get("requires") or []:
                    print(f"  requires {r['node']}/{r['capability']} {r['version']}")
                for r in c.get("required_by") or []:
                    print(f"  required by {r['node']}/{r['capability']}")
                if c.get("groups"):
                    print(
                        f"  groups chosen: {', '.join(c['groups'].get('chosen') or []) or '(none)'}"
                    )
    return EXIT_CODES["VALID"]


def _origin_text(origin) -> str:
    if not origin or origin.get("how") == "unknown":
        return "unknown"
    if not origin.get("commit"):  # a folder: there is no commit to name (specs/031 FR-002)
        where = origin.get("repository") or "unknown"
        if origin.get("subdirectory"):
            where += f"#{origin['subdirectory']}"
        return f"{origin.get('how')} {where} (no commit)"
    where = f"{origin.get('repository')}@{origin.get('commit')}"
    if origin.get("subdirectory"):
        where += f"#{origin['subdirectory']}"
    resolved = "" if origin.get("resolved") else ", commit unresolved"
    return f"{origin.get('how')} {where}{resolved}"


def _provenance_lines(p) -> list[str]:
    lines = [f"origin: {_origin_text(p.get('origin'))}"]
    if p.get("signature") == "valid":
        who = (
            "trusted"
            if p.get("trusted")
            else "NOT trusted"
            if p.get("trusted") is False
            else ("trust not checked")
        )
        lines.append(f"signature: valid by {p.get('signer')} ({who})")
    else:
        lines.append(f"signature: {p.get('signature')}")
    for c in p.get("consents") or []:
        lines.append(f"consent: {c['kind']} for {c.get('signer')} ({c['operation']})")
    if p.get("check") and p["check"] != "skipped":
        cause = f" ({p['cause']})" if p.get("cause") else ""
        lines.append(f"provenance: {p['check']}{cause}")
    return lines


def render_host_human(o) -> str:
    lines = [f"{o.verdict.upper()} {o.headline()}"]
    package_version = ((o.versions or {}).get("running") or {}).get("capability_version")
    if o.verb == "verify" and package_version and package_version != o.version:
        lines.append(f"package: {o.capability} {package_version} (installed {o.version})")
    for p in o.errors:
        lines.append(_problem_line("ERROR", p))
    for c in o.conflicts:
        lines.append(
            f"CONFLICT {c['path']} ({c['found']}, {c['digest_found']}): "
            f"not installed by {o.capability}"
        )
    for d in o.divergences:
        state = d.get("state") or "modified"
        lines.append(f"DIVERGENT {d['path']}: {state}")
        for f in d.get("files") or []:  # a folder names its files (specs/032 FR-025)
            lines.append(f"    {f['state']} {f['path']}")
        if d.get("files_unknown"):
            lines.append("    files could not be listed (no installed copy to compare with)")
    # consented files are replaced only by an operation that wrote (specs/031 FR-003)
    written = o.exit_code == 0 and not o.dry_run
    for r in o.replaced:
        label = "REPLACED" if written else "WOULD-REPLACE"
        lines.append(f"{label} {r['path']} (was {r['digest_found']})")
    for r in o.restored:
        lines.append(f"{r['result']} {r['path']}")
    if o.provenance:
        lines += _provenance_lines(o.provenance)
    if o.groups:
        lines.append(f"groups chosen: {', '.join(o.groups['chosen']) or '(none)'}")
        if o.groups.get("left_out"):
            lines.append(f"left out: {', '.join(o.groups['left_out'])}")
        for key in ("added", "dropped"):
            if o.groups.get(key):
                lines.append(f"groups {key}: {', '.join(o.groups[key])}")
    for r in o.requirements or []:
        state = "satisfied" if r["satisfied"] else f"NOT satisfied ({r['why']})"
        lines.append(f"requires {r['node']}/{r['capability']} {r['version']}: {state}")
    for d in o.dependents or []:
        lines.append(f"required by {d['node']}/{d['capability']}: {d['why']}")
    if o.contributions:
        c = o.contributions
        lines.append(
            f"CONTRIBUTIONS {c['count']} to {', '.join(c['files'])} "
            f"(main Kaelen {c.get('main_kaelen') or '?'})"
        )
    if o.main and o.main.get("state") != "kept":
        was = f" (was {o.main['from']})" if o.main.get("from") else ""
        version = f" {o.main['version']}" if o.main.get("version") else ""
        lines.append(f"MAIN KAELEN {o.main['state']}{version}{was}")
    for prev in o.previous:
        member = f" @ {prev['member']}" if prev.get("member") else ""
        lines.append(f"PREVIOUS {prev['result']} {prev['path']}{member}")
    if o.runtime:
        rt = o.runtime
        how = f" with {rt['tool']}" if rt.get("tool") else ""
        python = f", python {rt['python']}" if rt.get("python") else ""
        deps = f", {rt['dependencies']} dependencies" if "dependencies" in rt else ""
        lines.append(f"RUNTIME {rt['state']}{how}{python}{deps}")
        for d in rt.get("differences", []):
            lines.append(
                f"RUNTIME DIFFERS {d['name']}: expected {d['expected']}, found {d['found']}"
            )
        if rt.get("hint"):
            lines.append(f"hint: {rt['hint']}")
    for c in o.changes:
        lines.append(f"{c['op']} {c['path']}")
    for t in o.targets:
        placed = sum(1 for i in t["items"] if i["result"] != "not-installed")
        missing = len(t["items"]) - placed
        lines.append(
            f"{t['target']}: {len(t['items'])} item(s), {placed} installed"
            + (f", {missing} not supported" if missing else "")
        )
    for p in o.findings:
        lines.append(_problem_line("FINDING", p))
    for s in o.settings:
        if s["state"] == "missing":
            lines.append(f"MISSING SETTING {s['name']}: {s['description']}")
    for i in o.items if o.verb == "verify" else []:
        for f in (i.get("form") or {}).get("failed", []):
            lines.append(f"FORM {i['path']}: {f['check']}: {f['detail']}")
        for m in (i.get("command") or {}).get("missing", []):
            lines.append(f"HOOK COMMAND {i['path']}: not found: {m}")
    for server in o.live or []:
        where = ", ".join(server["targets"])
        if server["state"] == "running":
            lines.append(
                f"LIVE {server['server']} ({where}): running, "
                f"server {server.get('version') or 'unversioned'}, {server.get('tools')} tool(s)"
            )
        else:
            lines.append(
                f"LIVE {server['server']} ({where}): {server['state']}: {server.get('cause')}"
            )
    if o.verb == "verify" and o.verdict in ("verified", "divergent"):
        lines.append("not checked: " + "; ".join(o.not_checked))
    hint = o.hint()
    if hint:
        lines.append(f"hint: {hint}")
    return "\n".join(lines) + "\n"
