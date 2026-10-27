"""The outcome of a validation: verdict, problems, perimeter, and its JSON form."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

CHECK_IDS = (
    "read",
    "contract-version",
    "schema",
    "coherence",
    "producer-sources",
    "producer-undeclared",
)

VALID = "valid"
INVALID = "invalid"
UNABLE_TO_CHECK = "unable-to-check"

# specs/014-declaration-contract/contracts/cli.md — stable, documented.
EXIT_CODES = {
    "VALID": 0,
    "INVALID": 1,
    "USAGE": 64,
    "UNABLE_TO_CHECK": 66,
    "INTERNAL": 70,
}

_SYMBOL_BY_VERDICT = {VALID: "VALID", INVALID: "INVALID", UNABLE_TO_CHECK: "UNABLE_TO_CHECK"}


@dataclass(frozen=True)
class Problem:
    """One error or finding: which rule, at which element, and why."""

    rule: str
    path: str
    message: str
    known: tuple[str, ...] | None = None

    def to_dict(self) -> dict:
        data = {"rule": self.rule, "path": self.path, "message": self.message}
        if self.known is not None:
            data["known"] = list(self.known)
        return data


@dataclass
class Outcome:
    declaration: str
    producer: str | None
    verdict: str
    ran: list[str] = field(default_factory=list)
    not_run: list[str] = field(default_factory=list)
    errors: list[Problem] = field(default_factory=list)
    findings: list[Problem] = field(default_factory=list)
    summary: dict | None = None
    # Why the run could not complete, when the verdict is unable-to-check.
    reason: str | None = None

    @property
    def symbol(self) -> str:
        return _SYMBOL_BY_VERDICT[self.verdict]

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.symbol]

    def to_document(self, engine_version: str) -> dict:
        doc = {
            "schema": "kaelen.validate/1",
            "engine": {"version": engine_version},
            "declaration": self.declaration,
            "producer": self.producer,
            "verdict": self.verdict,
            "checks": {"ran": list(self.ran), "not_run": list(self.not_run)},
            "errors": [p.to_dict() for p in self.errors],
            "findings": [p.to_dict() for p in self.findings],
            "summary": self.summary if self.verdict == VALID else None,
        }
        if self.exit_code != 0:
            doc["error"] = error_envelope(self.symbol, self.headline(), None)
        return doc

    def headline(self) -> str:
        if self.verdict == VALID:
            return "declaration is valid"
        if self.verdict == INVALID:
            return f"declaration is invalid: {len(self.errors)} error(s)"
        return f"unable to check: {self.reason or 'input could not be opened'}"


def error_envelope(code: str, message: str, hint: str | None) -> dict:
    """The constitution's error member for every non-zero exit under --json."""
    return {"code": code, "message": message, "hint": hint}


def render_json(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


# --- Packaging (specs/015-packaging-injection/contracts/cli.md) -----------------------------

PACKAGE_CHECK_IDS = (*CHECK_IDS, "location", "inject", "write")

PACKAGED = "packaged"
WOULD_PACKAGE = "would-package"
REFUSED = "refused"
INTERNAL = "internal"

_SYMBOL_BY_PACKAGE_VERDICT = {
    PACKAGED: "VALID",
    WOULD_PACKAGE: "VALID",
    REFUSED: "INVALID",
    UNABLE_TO_CHECK: "UNABLE_TO_CHECK",
    INTERNAL: "INTERNAL",
}


@dataclass
class PackageOutcome:
    declaration: str
    producer: str
    dry_run: bool
    verdict: str
    ran: list[str] = field(default_factory=list)
    not_run: list[str] = field(default_factory=list)
    errors: list[Problem] = field(default_factory=list)
    findings: list[Problem] = field(default_factory=list)
    package: str | None = None
    files: list[dict] | None = None
    targets: list[dict] | None = None
    size: dict | None = None
    record: dict | None = None
    reason: str | None = None
    launch: dict | None = None
    left_out: list[dict] = field(default_factory=list)  # specs/033 R-3

    @property
    def symbol(self) -> str:
        return _SYMBOL_BY_PACKAGE_VERDICT[self.verdict]

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.symbol]

    @property
    def produced(self) -> bool:
        return self.verdict in (PACKAGED, WOULD_PACKAGE)

    def to_document(self, engine_version: str) -> dict:
        ok = self.produced
        doc = {
            "schema": "kaelen.package/2",
            "engine": {"version": engine_version},
            "declaration": self.declaration,
            "producer": self.producer,
            "dry_run": self.dry_run,
            "verdict": self.verdict,
            "checks": {"ran": list(self.ran), "not_run": list(self.not_run)},
            "errors": [p.to_dict() for p in self.errors],
            "findings": [p.to_dict() for p in self.findings],
            "package": self.package if ok else None,
            "files": self.files if ok else None,
            "targets": self.targets if ok else None,
            "size": self.size if ok else None,
            "external_resources": [],
            "record": self.record if ok else None,
            "launch": self.launch if ok else None,
            "left_out": list(self.left_out),
        }
        if self.exit_code != 0:
            doc["error"] = error_envelope(self.symbol, self.headline(), None)
        return doc

    def headline(self) -> str:
        if self.verdict == PACKAGED:
            return f"packaged at {self.package}"
        if self.verdict == WOULD_PACKAGE:
            return f"would package at {self.package}"
        if self.verdict == REFUSED:
            return f"packaging refused: {len(self.errors)} error(s)"
        if self.verdict == INTERNAL:
            return f"engine defect: {self.reason}"
        return f"unable to check: {self.reason or 'input could not be opened'}"


# --- Host verbs (specs/017-host-verbs/contracts/cli.md) --------------------------------------

HOST_EXIT_CODES = {
    "SUCCESS": 0,
    "REFUSED": 1,
    "DIVERGENT": 2,
    "INCOMPLETE": 3,
    "NOT_INSTALLED": 4,
    "NOT_CHECKED": 5,  # verify --provenance could not check: not a pass (specs/028)
    "USAGE": 64,
    "UNABLE_TO_CHECK": 66,
    "INTERNAL": 70,
}

_SYMBOL_BY_HOST_VERDICT = {
    "installed": "SUCCESS",
    "would-install": "SUCCESS",
    "already-installed": "SUCCESS",
    "updated": "SUCCESS",
    "would-update": "SUCCESS",
    "uninstalled": "SUCCESS",
    "would-uninstall": "SUCCESS",
    "not-installed": "SUCCESS",
    "verified": "SUCCESS",
    "rolled-back": "SUCCESS",
    "would-roll-back": "SUCCESS",
    "nothing-to-roll-back": "SUCCESS",
    "cannot-roll-back": "INCOMPLETE",
    "listed": "SUCCESS",
    "divergent": "DIVERGENT",
    "not-checked": "NOT_CHECKED",
    "trusted": "SUCCESS",
    "would-trust": "SUCCESS",
    "removed": "SUCCESS",
    "would-remove": "SUCCESS",
    "not-trusted": "SUCCESS",
    "refused": "REFUSED",
    "incomplete": "INCOMPLETE",
    "no-installation": "NOT_INSTALLED",
    "unable-to-check": "UNABLE_TO_CHECK",
    "internal": "INTERNAL",
}


@dataclass
class HostOutcome:
    verb: str
    host: str
    package: str | None
    dry_run: bool
    verdict: str
    capability: str | None = None
    version: str | None = None
    targets: list[dict] = field(default_factory=list)
    changes: list[dict] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    divergences: list[dict] = field(default_factory=list)
    replaced: list[dict] = field(default_factory=list)
    restored: list[dict] = field(default_factory=list)  # rollback: per location
    runtime: dict | None = None  # the capability's environment (specs/022)
    live: list[dict] | None = None  # verify --live: MCP servers started (specs/023)
    previous: list[dict] = field(default_factory=list)  # earlier installation (specs/024)
    main: dict | None = None  # the host's main Kaelen in this operation (specs/026)
    contributions: dict | None = None  # what the main Kaelen writes in shared files (specs/027)
    provenance: dict | None = None  # origin and signature (specs/028)
    trust: list[dict] | None = None  # the host's trusted signers (specs/028, `kaelen trust`)
    principal: str | None = None  # the signer a trust verb acts on (specs/031 FR-004)
    requirements: list[dict] | None = None  # what this capability requires (specs/029)
    dependents: list[dict] | None = None  # who requires it and would be broken (specs/029)
    groups: dict | None = None  # declared, chosen, included, left out (specs/029)
    settings: list[dict] = field(default_factory=list)
    errors: list[Problem] = field(default_factory=list)
    findings: list[Problem] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)  # verify: per item state
    capabilities: list[dict] | None = None  # installed: the list
    versions: dict | None = None
    incomplete: dict | None = None
    not_checked: list[str] = field(default_factory=list)
    reason: str | None = None
    completed: bool = False

    @property
    def symbol(self) -> str:
        return _SYMBOL_BY_HOST_VERDICT[self.verdict]

    @property
    def exit_code(self) -> int:
        return HOST_EXIT_CODES[self.symbol]

    def to_document(self, engine_version: str) -> dict:
        doc = {
            "schema": "kaelen.host/1",
            "engine": {"version": engine_version},
            "verb": self.verb,
            "host": self.host,
            "package": self.package,
            "capability": self.capability,
            "version": self.version,
            "dry_run": self.dry_run,
            "verdict": self.verdict,
            "completed_interrupted": self.completed,
            "targets": self.targets,
            "changes": self.changes,
            "conflicts": self.conflicts,
            "divergences": self.divergences,
            "replaced": self.replaced,
            "restored": self.restored,
            "runtime": self.runtime,
            "live": self.live,
            "previous": self.previous,
            "main": self.main,
            "settings": self.settings,
            "items": self.items,
            "errors": [p.to_dict() for p in self.errors],
            "findings": [p.to_dict() for p in self.findings],
            "summary": {
                "changes": len(self.changes),
                "findings": len(self.findings),
                "conflicts": len(self.conflicts),
                "divergences": len(self.divergences),
                "missing_settings": sum(1 for s in self.settings if s.get("state") == "missing"),
            },
            "versions": self.versions,
            "incomplete": self.incomplete,
            "not_checked": self.not_checked,
        }
        if self.capabilities is not None:
            doc["capabilities"] = self.capabilities
        if self.contributions is not None:
            doc["contributions"] = self.contributions
        if self.provenance is not None:
            doc["provenance"] = self.provenance
        if self.trust is not None:
            doc["trust"] = self.trust
        if self.principal is not None:
            doc["principal"] = self.principal
        for name in ("requirements", "dependents", "groups"):
            if getattr(self, name) is not None:
                doc[name] = getattr(self, name)
        if self.exit_code != 0:
            doc["error"] = error_envelope(self.symbol, self.headline(), self.hint())
        return doc

    def hint(self) -> str | None:
        if self.verdict == "refused" and (self.conflicts or self.divergences):
            first = (self.conflicts or self.divergences)[0]["path"]
            return f"re-run with --authorise {first} (one flag per file), or answer at a terminal"
        if self.verdict in ("incomplete", "cannot-roll-back") and self.incomplete:
            verb = self.incomplete.get("operation") or ""
            again = f"rollback --capability {self.capability}"
            if self.incomplete.get("rolling_back"):
                return (
                    f"a rollback of {self.capability} is in progress: "
                    f"run {again} again to finish it"
                )
            if self.incomplete.get("rollback") == "not-needed":
                return (
                    f"the {verb} itself is done; the main Kaelen's leftover part is dropped by the "
                    "next operation on this host: nothing to do"
                )
            complete = f"run the same {verb} again with the same package to complete it"
            if self.incomplete.get("rollback") == "possible":
                return f"{complete}, or run {again} to undo it"
            return complete
        return None

    def headline(self) -> str:
        what = f"{self.capability} {self.version}" if self.capability else (self.package or "")
        if self.verb.startswith("trust-"):  # a signer, not a capability (specs/031 FR-004)
            if self.verdict == "listed":
                return f"trust list: {len(self.trust or [])} signer(s)"
            what = self.principal or ""
        if self.verb == "rollback" and self.verdict in ("rolled-back", "would-roll-back"):
            operation = (self.incomplete or {}).get("operation")
            return (
                f"{self.capability}: {operation} undone, {len(self.restored)} location(s) restored"
            )
        if self.verdict == "nothing-to-roll-back":
            return f"{self.capability}: no interrupted operation on this host"
        if self.verdict in (
            "refused",
            "unable-to-check",
            "internal",
            "incomplete",
            "cannot-roll-back",
        ):
            first = self.errors[0].message if self.errors else (self.reason or "")
            return f"{self.verb} {self.verdict}: {first}".rstrip(": ")
        if self.verdict == "divergent":
            return f"{what}: {len(self.divergences)} item(s) differ from what was installed"
        if self.verdict == "no-installation":
            return f"{what}: no installation recorded on this host"
        return f"{what}: {self.verdict}, {len(self.changes)} change(s)"


# --- verify without a package: every capability (specs/031 FR-009…FR-012) ---------------------

# Most severe first; a capability its own engine cannot verify counts as unable-to-check.
VERIFY_SEVERITY = (
    "internal",
    "unable-to-check",
    "incomplete",
    "not-checked",
    "divergent",
    "no-installation",
    "refused",
    "verified",
)


@dataclass
class HostVerification:
    host: str
    capability: str | None = None
    verdict: str = "verified"
    capabilities: list[dict] = field(default_factory=list)
    reason: str | None = None  # a usage error: why

    @property
    def symbol(self) -> str:
        if self.verdict == "usage":
            return "USAGE"
        if self.verdict == "nothing-installed":
            return "SUCCESS"
        return _SYMBOL_BY_HOST_VERDICT[self.verdict]

    @property
    def exit_code(self) -> int:
        return HOST_EXIT_CODES[self.symbol]

    def not_verified(self) -> list[dict]:
        return [c for c in self.capabilities if c["verdict"] != "verified"]

    def headline(self) -> str:
        if self.verdict == "usage":
            return self.reason or "usage error"
        if self.verdict == "nothing-installed":
            return "host: no capability recorded on this host"
        n = len(self.capabilities)
        if self.verdict == "verified":
            return f"host: {n} capability(ies) verified"
        return f"host: {len(self.not_verified())} of {n} capability(ies) not verified"

    def hint(self) -> str | None:
        first = next(iter(self.not_verified()), None)
        if first is None:
            return None
        if first["verdict"] == "not-verifiable":
            return first["remedy"]
        return f"for details run {first['run']} verify --host ."

    def to_document(self, engine_version: str) -> dict:
        fields = (
            "node",
            "capability",
            "version",
            "verdict",
            "exit",
            "document",
            "reason",
            "remedy",
        )
        doc = {
            "schema": "kaelen.host-verify/1",
            "engine": {"version": engine_version},
            "host": self.host,
            "capability": self.capability,
            "verdict": self.verdict,
            "exit": self.exit_code,
            "capabilities": [{k: c.get(k) for k in fields} for c in self.capabilities],
            "summary": {
                "capabilities": len(self.capabilities),
                "verified": len(self.capabilities) - len(self.not_verified()),
                "not_verified": len(self.not_verified()),
            },
        }
        if self.exit_code != 0:
            doc["error"] = error_envelope(self.symbol, self.headline(), self.hint())
        return doc
