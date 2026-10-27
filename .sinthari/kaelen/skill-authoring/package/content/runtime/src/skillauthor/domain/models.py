"""Modelli di dominio di SkillAuthor (data-model.md). Dati immutabili, nessun I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .errors import InputError

Severity = Literal["blocking", "warning"]
Kind = Literal["merit", "protocol"]
VerdictValue = Literal["validated", "protocol-only", "no-separation", "incomplete"]
ReadyStatus = Literal["ready", "ready-unvalidated", "not-ready"]


# --- Skill -------------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillDoc:
    """Una cartella-skill letta: frontmatter, corpo con i numeri di riga, file presenti."""

    dir_name: str
    frontmatter: dict
    body: tuple[tuple[int, str], ...]
    files: frozenset[str]  # percorsi relativi alla skill, separatore '/'
    has_vendor: bool = False
    vendor_dirs: tuple[str, ...] = ()


# --- Lint --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    location: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "location": self.location,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Allowance:
    rule: str
    match: str
    why: str

    def to_dict(self) -> dict:
        return {"rule": self.rule, "match": self.match, "why": self.why}


@dataclass(frozen=True)
class LintResult:
    skill_dir: str
    findings: tuple[Finding, ...]
    allowed: tuple[Allowance, ...] = ()

    @property
    def has_blocking(self) -> bool:
        return any(f.severity == "blocking" for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "skill_dir": self.skill_dir,
            "findings": [f.to_dict() for f in self.findings],
            "allowed": [a.to_dict() for a in self.allowed],
        }


# --- Verdetto ----------------------------------------------------------------------------


@dataclass(frozen=True)
class ExpectationOutcome:
    eval_id: int
    text: str
    kind: Kind
    pass_rate_with: float
    pass_rate_without: float

    @property
    def separates(self) -> bool:
        return self.pass_rate_with > self.pass_rate_without

    def to_dict(self) -> dict:
        return {
            "eval_id": self.eval_id,
            "text": self.text,
            "kind": self.kind,
            "pass_rate_with": self.pass_rate_with,
            "pass_rate_without": self.pass_rate_without,
            "separates": self.separates,
        }


@dataclass(frozen=True)
class Verdict:
    skill_name: str
    verdict: VerdictValue
    per_expectation: tuple[ExpectationOutcome, ...]
    missing: tuple[str, ...] = ()
    kind_challenges: tuple[dict, ...] = ()
    skill_digest: str | None = None

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "verdict": self.verdict,
            "per_expectation": [o.to_dict() for o in self.per_expectation],
            "missing": list(self.missing),
            "kind_challenges": list(self.kind_challenges),
            "skill_digest": self.skill_digest,
        }


# --- Revisione ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewFinding:
    id: str
    severity: Literal["blocking", "improvement"]
    summary: str
    status: Literal["open", "resolved", "accepted"]
    acceptance_reason: str | None = None

    def __post_init__(self) -> None:
        if self.status == "accepted" and not (self.acceptance_reason or "").strip():
            raise InputError("review.json", f"finding {self.id}: 'accepted' richiede acceptance_reason")


@dataclass(frozen=True)
class ReviewRegister:
    skill_name: str
    round: int
    findings: tuple[ReviewFinding, ...]
    subject_digest: str | None = None  # impronta di ciò che è stato rivisto (feature 006)

    def open_blocking(self) -> tuple[ReviewFinding, ...]:
        return tuple(f for f in self.findings if f.severity == "blocking" and f.status == "open")

    def accepted(self) -> tuple[ReviewFinding, ...]:
        return tuple(f for f in self.findings if f.status == "accepted")

    def reappeared(self, previous: ReviewRegister) -> tuple[str, ...]:
        """Bloccanti dichiarati `resolved` nel giro precedente che ricompaiono `open` in questo."""

        resolved_before = {
            f.id for f in previous.findings if f.severity == "blocking" and f.status == "resolved"
        }
        return tuple(f.id for f in self.open_blocking() if f.id in resolved_before)


# --- Gate --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Reason:
    code: str
    detail: str

    def to_dict(self) -> dict:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class ReadyResult:
    skill_name: str
    status: ReadyStatus
    reasons: tuple[Reason, ...] = ()
    accepted: tuple[dict, ...] = field(default=())
    subject_kind: Literal["skill", "agent"] = "skill"
    subject_digest: str | None = None
    notes: tuple[str, ...] = ()  # cose da controllare a mano che non bloccano il gate (006, B3)

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "status": self.status,
            "reasons": [r.to_dict() for r in self.reasons],
            "accepted": list(self.accepted),
            "subject_kind": self.subject_kind,
            "subject_digest": self.subject_digest,
            "notes": list(self.notes),
        }


# --- Agente (feature 005) ----------------------------------------------------------------


@dataclass(frozen=True)
class AgentDoc:
    """Un file d'agente letto: intestazione e prompt con i numeri di riga del file."""

    path: str
    file_name: str
    form: Literal["markdown", "toml"]
    stem: str
    header: dict
    body: tuple[tuple[int, str], ...]
    dir: str  # cartella che contiene il file: base dei percorsi di allegati citati


@dataclass(frozen=True)
class AgentLintResult:
    agent: str
    name: str
    form: str
    facts: dict
    parity: dict
    findings: tuple[Finding, ...]
    allowed: tuple[Allowance, ...] = ()

    @property
    def has_blocking(self) -> bool:
        return any(f.severity == "blocking" for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "name": self.name,
            "form": self.form,
            "facts": self.facts,
            "parity": self.parity,
            "findings": [f.to_dict() for f in self.findings],
            "allowed": [a.to_dict() for a in self.allowed],
        }


# --- Correzione di un agente (feature 006) -----------------------------------------------


@dataclass(frozen=True)
class FieldChange:
    field: str
    change: Literal["added", "removed", "changed"]
    before: object
    after: object

    def to_dict(self) -> dict:
        return {"field": self.field, "change": self.change, "before": self.before, "after": self.after}


@dataclass(frozen=True)
class AgentDiff:
    before: str
    after: str
    fields: tuple[FieldChange, ...]
    tools: dict | None  # {"added": [...], "removed": [...]}; None se nessuna versione dichiara `tools`
    prompt: dict  # {"changed", "lines_added", "lines_removed"}

    def to_dict(self) -> dict:
        return {
            "before": self.before,
            "after": self.after,
            "fields": [c.to_dict() for c in self.fields],
            "tools": self.tools,
            "prompt": self.prompt,
        }


@dataclass(frozen=True)
class FormDifference:
    field: str
    kind: Literal["declared-loss", "missing", "different", "prompt-differs", "unverified"]
    detail: str

    def to_dict(self) -> dict:
        return {"field": self.field, "kind": self.kind, "detail": self.detail}


@dataclass(frozen=True)
class FormComparison:
    file: str
    target: str
    differences: tuple[FormDifference, ...]

    @property
    def status(self) -> str:
        kinds = {d.kind for d in self.differences}
        if kinds & {"missing", "different", "prompt-differs"}:
            return "diverges"
        if "unverified" in kinds:
            return "unverified"
        return "declared-losses-only" if kinds else "in-sync"

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "target": self.target,
            "status": self.status,
            "differences": [d.to_dict() for d in self.differences],
        }


@dataclass(frozen=True)
class FormsReport:
    source: str
    reference: str
    forms: tuple[FormComparison, ...]

    @property
    def in_sync(self) -> bool:
        return all(f.status != "diverges" for f in self.forms)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "reference": self.reference,
            "forms": [f.to_dict() for f in self.forms],
            "in_sync": self.in_sync,
        }
