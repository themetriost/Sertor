"""Gate «pronta» (research R5): l'unico modo di dichiarare pronta una skill.

Mette insieme lint (calcolato al momento), registro della revisione e verdetto. L'autore può accettare
un bloccante o un verdetto non validato, ma solo in modo esplicito e motivato, e l'accettazione compare
nell'esito.

Confine dichiarato: il gate si fida di `review.json`, che trascrive l'output di `skill-review`.
Impedisce di chiudere con un bloccante registrato aperto; non può sapere se la trascrizione è fedele.

Dalla feature 006 il soggetto può essere un agente (un file). Allora il lint è `agent-lint` sulla sorgente e
sulle forme date con `forms`, il registro deve portare l'impronta dell'agente rivisto (senza, la revisione è
vecchia per costruzione), e ogni forma deve coincidere con la sorgente secondo `agent-forms`.
"""

from __future__ import annotations

from pathlib import Path

from .adapters.agent_fs import FsAgentSource
from .agent_forms import compare_forms
from .agent_lint import lint_agent
from .digest import agent_digest, skill_digest
from .domain.errors import InputError
from .domain.models import ReadyResult, Reason, ReviewFinding, ReviewRegister
from .jsonfiles import load_validated
from .lint import lint_skill

_UNVALIDATED = ("protocol-only", "no-separation")


def load_register(path: Path) -> ReviewRegister:
    doc = load_validated(path, "review")
    return ReviewRegister(
        skill_name=doc["skill_name"],
        round=doc["round"],
        findings=tuple(
            ReviewFinding(f["id"], f["severity"], f["summary"], f["status"], f.get("acceptance_reason"))
            for f in doc["findings"]
        ),
        subject_digest=doc.get("subject_digest"),
    )


def evaluate_ready(
    subject: Path,
    review_path: Path,
    verdict_path: Path,
    accept_unvalidated: str | None = None,
    previous_review: Path | None = None,
    forms: list[Path] | None = None,
) -> ReadyResult:
    if accept_unvalidated is not None and not accept_unvalidated.strip():
        raise InputError("--accept-unvalidated", "serve un motivo non vuoto")
    is_agent = subject.is_file()
    if forms and not is_agent:
        raise InputError("--form", "le forme valgono solo per un agente, non per una cartella-skill")

    digest = agent_digest(subject) if is_agent else skill_digest(subject)
    reasons: list[Reason] = []
    accepted: list[dict] = []

    reasons.extend(_agent_lint_reasons(subject, forms or []) if is_agent else _lint_reasons(subject))
    if is_agent:
        reasons.extend(_review_digest_reasons(review_path, digest))
    reasons.extend(_review_reasons(review_path, previous_review, accepted))
    unvalidated = _verdict_reasons(digest, verdict_path, accept_unvalidated, reasons, accepted)
    notes: list[str] = []
    if is_agent and forms:
        reasons.extend(_forms_reasons(subject, forms, notes))

    if reasons:
        status = "not-ready"
    elif unvalidated:
        status = "ready-unvalidated"
    else:
        status = "ready"
    return ReadyResult(
        skill_name=_subject_name(subject, is_agent),
        status=status,
        reasons=tuple(reasons),
        accepted=tuple(accepted),
        subject_kind="agent" if is_agent else "skill",
        subject_digest=digest,
        notes=tuple(notes),
    )


def _subject_name(subject: Path, is_agent: bool) -> str:
    if not is_agent:
        return subject.resolve().name
    return FsAgentSource().read(subject).stem


def _lint_reasons(skill_dir: Path) -> list[Reason]:
    blocking = [f.location for f in lint_skill(skill_dir).findings if f.severity == "blocking"]
    return [_lint_reason(blocking)] if blocking else []


def _agent_lint_reasons(source: Path, forms: list[Path]) -> list[Reason]:
    blocking = [
        f"{path}: {f.rule} {f.location}"
        for path in (source, *forms)
        for f in lint_agent(path).findings
        if f.severity == "blocking"
    ]
    return [_lint_reason(blocking)] if blocking else []


def _lint_reason(blocking: list[str]) -> Reason:
    return Reason("lint-blocking", f"{len(blocking)} finding bloccanti del lint: {', '.join(blocking)}")


def _review_digest_reasons(review_path: Path, digest: str) -> list[Reason]:
    """Un registro su un agente vale solo per la versione rivista (FR-002, FR-026)."""

    if not review_path.is_file():
        return []  # il registro mancante lo riporta _review_reasons
    recorded = load_register(review_path).subject_digest
    if recorded == digest:
        return []
    detail = (
        "la revisione è di un'altra versione dell'agente: rifalla sulla versione attuale"
        if recorded
        else "il registro non porta l'impronta dell'agente rivisto (subject_digest): rifallo annotandola"
    )
    return [Reason("review-stale", detail)]


def _forms_reasons(source: Path, forms: list[Path], notes: list[str]) -> list[Reason]:
    report = compare_forms(source, forms, FsAgentSource())
    notes.extend(
        f"{f.file}: da controllare a mano, {d.detail}"
        for f in report.forms
        for d in f.differences
        if d.kind == "unverified"
    )
    diverging = [f.file for f in report.forms if f.status == "diverges"]
    if not diverging:
        return []
    return [Reason("forms-diverge", f"forme che non coincidono con la sorgente: {', '.join(diverging)}")]


def _review_reasons(review_path: Path, previous: Path | None, accepted: list[dict]) -> list[Reason]:
    if not review_path.is_file():
        return [Reason("review-missing", f"registro della revisione assente: {review_path}")]
    register = load_register(review_path)
    accepted.extend({"what": f"finding {f.id}", "reason": f.acceptance_reason} for f in register.accepted())
    open_ids = [f.id for f in register.open_blocking()]
    if not open_ids:
        return []
    reappeared = set(register.reappeared(load_register(previous))) if previous else set()
    labels = [
        f"{i} (ricomparso dopo essere stato dichiarato risolto)" if i in reappeared else i for i in open_ids
    ]
    return [Reason("review-open-blocking", f"finding bloccanti aperti: {', '.join(labels)}")]


def _verdict_reasons(
    digest: str, verdict_path: Path, accept: str | None, reasons: list[Reason], accepted: list[dict]
) -> bool:
    """Aggiunge i motivi legati al verdetto; restituisce True se la skill chiude come non validata."""

    if not verdict_path.is_file():
        reasons.append(Reason("verdict-missing", f"verdetto del collaudo assente: {verdict_path}"))
        return False
    doc = load_validated(verdict_path, "verdict")
    # Un verdetto vale solo per la versione collaudata (emerso sul campo: skill corretta dopo il collaudo).
    recorded = doc.get("skill_digest")
    if recorded != digest:
        detail = (
            "il soggetto è cambiato dopo il collaudo: il verdetto si riferisce a un'altra versione"
            if recorded
            else "il verdetto non porta l'impronta del soggetto: rifallo indicandolo (--skill)"
        )
        reasons.append(Reason("verdict-stale", detail))
        return False
    verdict = doc["verdict"]
    if verdict == "incomplete":
        reasons.append(Reason("verdict-incomplete", "collaudo incompleto: completa le valutazioni mancanti"))
        return False
    if verdict not in _UNVALIDATED:
        return False
    if accept is None:
        reasons.append(
            Reason(
                "verdict-unvalidated",
                f"verdetto {verdict}: nessuna asserzione separa sul merito; serve --accept-unvalidated",
            )
        )
        return False
    accepted.append({"what": f"verdetto {verdict}", "reason": accept})
    return True
