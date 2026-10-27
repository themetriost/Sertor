"""The placement rule: where each kind of item lands for each assistant (specs/016-placement-rule).

One artefact, `rule.json`, is the only place a host location is written (FR-001). It is checked
every time it is loaded (research R-2): a rule with a hole, an entry without evidence or a
non-portable location is refused, never used in part. Its version is a digest of its content
(R-3), so it changes whenever an entry does.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from functools import cache
from importlib import resources
from pathlib import PurePosixPath

from kaelen.outcome import Problem

SCHEMA = "kaelen.placement-rule/1"
CONTRACT = 1

PLACED = "placed"
UNSUPPORTED = "unsupported"
UNKNOWN = "unknown"

# Closed sets (research R-5, R-8; contracts/placement-rule.md).
WRAPPERS = (
    "verbatim",
    "markdown-section",
    "copilot-instructions-file",
    "codex-agent-toml",
    "mcp-json-entry",
    "mcp-toml-entry",
    "claude-hook-entry",
    "codex-hook-entry",
    "copilot-hook-file",
    "git-section",
)
REASONS = ("no-surface", "outside-repository", "not-covered")
BASES = ("documented", "observed", "kaelen-convention")
FORMS = ("file", "directory", "as-source")
PLACEHOLDERS = ("name", "capability", "directory", "node")

_NAME = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
_DRIVE = re.compile(r"^[A-Za-z]:")


class RuleError(Exception):
    """The shipped rule failed its load-time checks: an engine defect, never a partial rule."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        lines = "; ".join(p.message for p in problems[:5])
        more = f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""
        super().__init__(f"placement rule refused: {lines}{more}")


# --- the contract's vocabulary ------------------------------------------------------------


def vocabulary(contract: int = CONTRACT) -> dict:
    """Kinds, and which kinds take which qualifier, read from the raw contract schema.

    Read from the artefact as shipped (before targets are injected from this rule), so the rule
    is checked against the contract without a second copy of its vocabulary.
    """
    from kaelen.contract import raw_schema

    schema = raw_schema(contract)
    defs = schema["$defs"]
    item = defs["item"]
    qualified: dict[str, list[str]] = {}
    for clause in item.get("allOf", ()):
        kind = clause.get("if", {}).get("properties", {}).get("kind", {}).get("const")
        required = clause.get("then", {}).get("required", ())
        if kind and required:
            field = required[0]
            ref = item["properties"][field]["$ref"].rsplit("/", 1)[-1]
            qualified[kind] = list(defs[ref]["enum"])
    return {
        "kinds": list(defs["kind"]["enum"]),
        "qualified": qualified,
        "extension_points": list(defs["extensionPoint"]["enum"]),
        "events": list(defs["hookEvent"]["enum"]),
    }


def _admitted(targets: list[str], vocab: dict) -> list[tuple[str, str, str | None]]:
    keys = []
    for target in targets:
        for kind in vocab["kinds"]:
            for qualifier in vocab["qualified"].get(kind, [None]):
                keys.append((target, kind, qualifier))
    return keys


# --- checking -----------------------------------------------------------------------------


def _label(entry: dict) -> str:
    q = entry.get("qualifier")
    return f"{entry.get('target')} {entry.get('kind')}{'/' + q if q else ''}"


def _pattern_problems(pattern) -> list[str]:
    if not isinstance(pattern, str) or not pattern:
        return ["empty pattern"]
    out = []
    if pattern.startswith("/") or _DRIVE.match(pattern):
        out.append(f"pattern {pattern!r} is absolute")
    if pattern.startswith("~"):
        out.append(f"pattern {pattern!r} points into the user's home")
    if "\\" in pattern:
        out.append(f"pattern {pattern!r} uses a backslash")
    if "$" in pattern or "%" in pattern:
        out.append(f"pattern {pattern!r} uses an environment variable")
    segments = pattern.rstrip("/").split("/")
    if any(s in ("", "..", ".") for s in segments):
        out.append(f"pattern {pattern!r} has an empty, '.' or '..' segment")
    for ph in _PLACEHOLDER.findall(pattern):
        if ph not in PLACEHOLDERS:
            out.append(f"pattern {pattern!r} uses unknown placeholder {{{ph}}}")
    return out


def _location_problems(where: str, loc: dict) -> list[str]:
    out = [f"{where}: {m}" for m in _pattern_problems(loc.get("pattern"))]
    if loc.get("form") not in FORMS:
        out.append(f"{where}: form {loc.get('form')!r} is not one of {', '.join(FORMS)}")
    if loc.get("wrapper") not in WRAPPERS:
        out.append(f"{where}: wrapper {loc.get('wrapper')!r} is not a known wrapper")
    section = loc.get("section")
    if section is not None:
        for ph in _PLACEHOLDER.findall(str(section)):
            if ph not in PLACEHOLDERS:
                out.append(f"{where}: section uses unknown placeholder {{{ph}}}")
    shared = loc.get("shared")
    if shared is not None:
        if not section:
            out.append(f"{where}: a shared location needs a section")
        if not isinstance(shared, dict) or not shared.get("role"):
            out.append(f"{where}: a shared location needs a role")
    if "checks" in loc:  # form checks verify applies (specs/023 FR-001, FR-004)
        from kaelen.host.checks import check_problems

        checks = loc["checks"]
        if not isinstance(checks, list):
            out.append(f"{where}: checks must be a list")
        else:
            for i, check in enumerate(checks):
                out += [f"{where}.checks[{i}]: {m}" for m in check_problems(check)]
    return out


def _evidence_problems(evidence) -> list[str]:
    if not isinstance(evidence, dict):
        return ["evidence is missing"]
    out = []
    if not evidence.get("ref"):
        out.append("evidence ref is missing")
    if evidence.get("basis") not in BASES:
        out.append(f"evidence basis {evidence.get('basis')!r} is not one of {', '.join(BASES)}")
    try:
        datetime.date.fromisoformat(str(evidence.get("verified")))
    except ValueError:
        out.append(f"evidence verified {evidence.get('verified')!r} is not an ISO date")
    return out


def check_rule(rule: dict, vocab: dict) -> list[Problem]:
    """Every reason `rule` cannot be used; empty when it is total, sourced and portable."""
    problems: list[str] = []
    if rule.get("schema") != SCHEMA:
        problems.append(f"schema {rule.get('schema')!r} is not {SCHEMA}")
    if rule.get("contract") != CONTRACT:
        problems.append(f"contract {rule.get('contract')!r} is not {CONTRACT}")
    targets = rule.get("targets")
    if (
        not isinstance(targets, list)
        or not targets
        or len(set(targets)) != len(targets)
        or not all(isinstance(t, str) and _NAME.match(t) for t in targets)
    ):
        problems.append("targets must be a non-empty list of unique names")
        targets = [t for t in dict.fromkeys(targets or []) if isinstance(t, str)]

    admitted = set(_admitted(targets, vocab))
    seen: dict[tuple, int] = {}
    for entry in rule.get("entries", ()):
        key = (entry.get("target"), entry.get("kind"), entry.get("qualifier"))
        label = _label(entry)
        seen[key] = seen.get(key, 0) + 1
        if key not in admitted:
            problems.append(f"{label}: no such combination in the contract or the rule's targets")
            continue
        outcome = entry.get("outcome")
        if outcome == PLACED:
            locations = entry.get("locations") or []
            if not locations:
                problems.append(f"{label}: placed with no location")
            for i, loc in enumerate(locations):
                problems += [f"{label}: {m}" for m in _location_problems(f"locations[{i}]", loc)]
        elif outcome == UNSUPPORTED:
            if entry.get("reason") not in REASONS:
                problems.append(f"{label}: reason {entry.get('reason')!r} is not one of {REASONS}")
            if not entry.get("detail"):
                problems.append(f"{label}: an unsupported entry needs a detail")
        else:
            problems.append(f"{label}: outcome {outcome!r} is not placed or unsupported")
        for pattern in entry.get("also_reads") or ():
            problems += [f"{label}: also_reads {m}" for m in _pattern_problems(pattern)]
        native = {loc.get("pattern") for loc in entry.get("locations") or ()}
        for pattern in sorted(native & set(entry.get("also_reads") or ())):
            problems.append(
                f"{label}: {pattern!r} is a location this assistant only also reads; "
                "an item goes in the assistant's native location (FR-007b)"
            )
        problems += [f"{label}: {m}" for m in _evidence_problems(entry.get("evidence"))]

    for key in _admitted(targets, vocab):
        q = f"/{key[2]}" if key[2] else ""
        if key not in seen:
            problems.append(f"{key[0]} {key[1]}{q}: entry missing")
        elif seen[key] > 1:
            problems.append(f"{key[0]} {key[1]}{q}: more than one entry")
    return [Problem("placement-rule", "rule.json", m) for m in problems]


# --- loading ------------------------------------------------------------------------------


def _read() -> dict:
    return json.loads(resources.files(__name__).joinpath("rule.json").read_text(encoding="utf-8"))


@cache
def load_rule() -> dict:
    """The shipped rule, checked; raises RuleError rather than return a rule with a hole."""
    rule = _read()
    problems = check_rule(rule, vocabulary(rule.get("contract", CONTRACT)))
    if problems:
        raise RuleError(problems)
    return rule


def rule_digest(rule: dict | None = None) -> str:
    """The rule's version: a digest of its canonical content, never a number kept beside it."""
    rule = load_rule() if rule is None else rule
    canonical = json.dumps(rule, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- querying -----------------------------------------------------------------------------


def _resolve(text: str | None, values: dict) -> str | None:
    if text is None:
        return None
    needed = _PLACEHOLDER.findall(text)
    if any(values.get(ph) is None for ph in needed):
        return None
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


def place(
    target: str,
    kind: str,
    qualifier: str | None = None,
    name: str | None = None,
    capability: str | None = None,
    directory: str | None = None,
    node: str | None = None,
) -> dict:
    """Where an item goes: exactly one of placed, unsupported, unknown (FR-013).

    `directory` is a git-lines item's host directory (specs/025 R-2); the root when absent.
    `node` names the capability's home `.{node}/kaelen/{capability}/` (specs/026 R-2).
    """
    rule = load_rule()
    query = {
        "target": target,
        "kind": kind,
        "qualifier": qualifier,
        "name": name,
        "capability": capability,
    }
    if directory is not None:
        query["directory"] = directory
    if node is not None:
        query["node"] = node
    vocab = vocabulary(rule["contract"])
    if target not in rule["targets"]:
        return {"query": query, "outcome": UNKNOWN, "unknown": "target"}
    if kind not in vocab["kinds"]:
        return {"query": query, "outcome": UNKNOWN, "unknown": "kind"}
    allowed = vocab["qualified"].get(kind)
    if (allowed is None) != (qualifier is None) or (allowed and qualifier not in allowed):
        return {"query": query, "outcome": UNKNOWN, "unknown": "qualifier"}
    entry = next(
        e
        for e in rule["entries"]
        if (e["target"], e["kind"], e["qualifier"]) == (target, kind, qualifier)
    )
    answer = {"query": query, "outcome": entry["outcome"]}
    folder = (directory or ".").strip("/")
    values = {
        "name": name,
        "capability": capability,
        "directory": "" if folder == "." else folder + "/",
        "node": node,
    }
    if entry["outcome"] == PLACED:
        answer["locations"] = [
            {
                "pattern": loc["pattern"],
                "path": _resolve(loc["pattern"], values),
                "form": loc["form"],
                "wrapper": loc["wrapper"],
                "section": _resolve(loc["section"], values) or loc["section"],
                "shared": loc["shared"],
                "checks": list(loc.get("checks", [])),
            }
            for loc in entry["locations"]
        ]
    else:
        answer["reason"] = entry["reason"]
        answer["detail"] = entry["detail"]
    answer["also_reads"] = [_resolve(p, values) or p for p in entry["also_reads"]]
    answer["notes"] = entry["notes"]
    answer["evidence"] = entry["evidence"]
    return answer


def with_source_suffix(loc: dict, item: dict, source_is_file: bool) -> dict:
    """An `as-source` file location keeps its source's suffix (`hooks/x` -> `hooks/x.py`).

    The rule names the location by item name; the file keeps the extension its interpreter and
    its readers rely on (specs/017 research R-16). Install and package both use this, so the
    package reports the path install writes (specs/031 FR-007).
    """
    suffix = PurePosixPath(item.get("source", "")).suffix
    path = loc["path"]
    if loc.get("form") == "as-source" and source_is_file and suffix and not path.endswith(suffix):
        return {**loc, "path": path + suffix}
    return loc


def qualifier_of(item: dict) -> str | None:
    """The field of a declared item that the rule keys on besides its kind (the vocabulary's
    qualifier: an extension point, a hook event, a git file)."""
    return item.get("extension_point") or item.get("event") or item.get("file")


def place_item(target: str, item: dict, capability: str, node: str | None = None) -> dict:
    """`place` for a declared item, with every field the rule reads taken from the item."""
    return place(
        target,
        item["kind"],
        qualifier_of(item),
        item["name"],
        capability,
        item.get("directory"),
        node,
    )
