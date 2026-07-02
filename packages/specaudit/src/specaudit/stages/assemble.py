"""Stadio 2 (FEAT-004) — assembla l'`AuditReport` dall'adjudication dell'agente.

È il **moat strutturale** di SpecAudit: NON ri-giudica il merito (quello è dell'agente), ma
garantisce l'onestà dell'output:
  1. integrità dei riferimenti (indice inesistente → fail-loud),
  2. completezza (ogni item coperto esattamente una volta → fail-loud),
  3. citazione delle àncore copiate dal bundle per indice (mai riverificate),
  4. guard sulla confidenza (FR-011), scoring del rischio, matrice, propagazione dei gap.
"""

from __future__ import annotations

from ..config import DEFAULT_CONFIG, Config
from ..domain.errors import (
    ChangesetMismatchError,
    DanglingReferenceError,
    IncompleteAdjudicationError,
    InvalidAdjudicationError,
)
from ..domain.models import (
    Adjudication,
    Anchor,
    AuditBundle,
    AuditRecord,
    Level,
    Matrix,
    OriginalRequirement,
    RiskScore,
    SpecLiftItem,
    VerdictKind,
)

_VERDICTS = [
    VerdictKind.SODDISFATTO,
    VerdictKind.PARZIALE,
    VerdictKind.MANCANTE,
    VerdictKind.DRIFTED,
    VerdictKind.NON_DOCUMENTATO,
]


def _cite(item: SpecLiftItem) -> str:
    a = item.anchor
    loc = f"{a.file}:{a.lines[0]}-{a.lines[1]}"
    return f"{a.symbol} ({loc})" if a.symbol else loc


def _notes_for_anchors(anchors: list[Anchor]) -> list[str]:
    notes: list[str] = []
    for a in anchors:
        if a.status == "unverified":
            notes.append(f"àncora SpecLift non verificata: {a.file}:{a.lines[0]}-{a.lines[1]}")
    return notes


def _clamp_confidence(verdict_conf: Level, alignment_conf: Level | None) -> tuple[Level, str | None]:
    """FR-011/REQ-010: se l'aggancio è BASSA, il verdetto non può essere più confidente."""

    if alignment_conf is Level.BASSA and verdict_conf is not Level.BASSA:
        return Level.BASSA, (
            f"confidenza verdetto ridotta a 'bassa' (aggancio a bassa confidenza; era '{verdict_conf.value}')"
        )
    return verdict_conf, None


def _risk_for(
    verdict: VerdictKind,
    severity: Level | None,
    detectability: Level | None,
    config: Config,
    ctx: str,
) -> RiskScore | None:
    if verdict is VerdictKind.SODDISFATTO:
        return None
    if severity is None or detectability is None:
        raise InvalidAdjudicationError(
            f"verdetto {verdict.value} ({ctx}) richiede severity e detectability per lo scoring di rischio"
        )
    risk = Level(config.risk_level(severity.value, detectability.value))
    return RiskScore(severity=severity, detectability=detectability, risk=risk)


def _check_integrity(bundle: AuditBundle, adj: Adjudication) -> None:
    n_orig = len(bundle.original)
    n_spec = len(bundle.speclift)
    for g in adj.groups:
        if not (0 <= g.original < n_orig):
            raise DanglingReferenceError(f"gruppo referenzia original index {g.original} inesistente")
        for s in g.speclift:
            if not (0 <= s < n_spec):
                raise DanglingReferenceError(f"gruppo referenzia speclift index {s} inesistente")
    for e in adj.extras:
        if not (0 <= e.speclift < n_spec):
            raise DanglingReferenceError(f"extra referenzia speclift index {e.speclift} inesistente")


def _check_completeness(bundle: AuditBundle, adj: Adjudication) -> None:
    # ogni original in esattamente un gruppo
    orig_seen: list[int] = [g.original for g in adj.groups]
    if sorted(orig_seen) != list(range(len(bundle.original))):
        raise IncompleteAdjudicationError(
            f"copertura dei requisiti originali non esatta: attesi {list(range(len(bundle.original)))}, "
            f"visti {sorted(orig_seen)}"
        )
    # ogni speclift in esattamente un gruppo o in extras
    spec_seen: list[int] = []
    for g in adj.groups:
        spec_seen.extend(g.speclift)
    spec_seen.extend(e.speclift for e in adj.extras)
    if sorted(spec_seen) != list(range(len(bundle.speclift))):
        raise IncompleteAdjudicationError(
            f"copertura degli item SpecLift non esatta (ognuno esattamente una volta): "
            f"attesi {list(range(len(bundle.speclift)))}, visti {sorted(spec_seen)}"
        )


def _validate_explanation(verdict: VerdictKind, explanation: str | None, ctx: str) -> None:
    if verdict is not VerdictKind.SODDISFATTO and not (explanation and explanation.strip()):
        raise InvalidAdjudicationError(
            f"verdetto {verdict.value} ({ctx}) richiede una spiegazione specifica (FEAT-003 REQ-007)"
        )


def _record_ref(original_ref: str | None, speclift_refs: list[str]) -> str:
    if original_ref:
        return original_ref
    if speclift_refs:
        return speclift_refs[0]
    return "(senza riferimento)"


def _risk_rank(record: AuditRecord) -> int:
    if record.risk is None:
        return 0
    return {"bassa": 1, "media": 2, "alta": 3}[record.risk.risk.value]


def assemble(
    bundle: AuditBundle, adj: Adjudication, config: Config = DEFAULT_CONFIG
) -> tuple[list[AuditRecord], Matrix, list[str], list[str]]:
    """Restituisce (records ordinati, matrice, declared_gaps, open_questions)."""

    if adj.changeset_ref != bundle.changeset_ref:
        raise ChangesetMismatchError(
            f"adjudication changeset_ref {adj.changeset_ref!r} ≠ bundle {bundle.changeset_ref!r}"
        )

    _check_integrity(bundle, adj)
    _check_completeness(bundle, adj)

    records: list[AuditRecord] = []

    for g in adj.groups:
        orig: OriginalRequirement = bundle.original[g.original]
        items = [bundle.speclift[s] for s in g.speclift]
        anchors = [it.anchor for it in items]
        speclift_refs = [_cite(it) for it in items]
        ctx = f"gruppo su {orig.id}"

        _validate_explanation(g.verdict, g.explanation, ctx)
        conf, clamp_note = _clamp_confidence(g.verdict_confidence, g.alignment_confidence)
        notes = _notes_for_anchors(anchors)
        if clamp_note:
            notes.append(clamp_note)

        records.append(
            AuditRecord(
                verdict=g.verdict,
                verdict_confidence=conf,
                anchors=anchors,
                proposed=g.verdict is VerdictKind.DRIFTED,
                speclift_refs=speclift_refs,
                original_ref=orig.id,
                explanation=g.explanation,
                alignment_confidence=g.alignment_confidence,
                risk=_risk_for(g.verdict, g.severity, g.detectability, config, ctx),
                notes=notes,
            )
        )

    for e in adj.extras:
        item = bundle.speclift[e.speclift]
        anchors = [item.anchor]
        speclift_refs = [_cite(item)]
        ctx = f"extra {speclift_refs[0]}"

        _validate_explanation(e.verdict, e.explanation, ctx)
        notes = _notes_for_anchors(anchors)

        records.append(
            AuditRecord(
                verdict=e.verdict,
                verdict_confidence=e.verdict_confidence,
                anchors=anchors,
                proposed=e.verdict is VerdictKind.DRIFTED,
                speclift_refs=speclift_refs,
                original_ref=None,
                explanation=e.explanation,
                alignment_confidence=None,
                risk=_risk_for(e.verdict, e.severity, e.detectability, config, ctx),
                notes=notes,
            )
        )

    # ordinamento: non-SODDISFATTO per rischio decrescente, poi per gravità del verdetto; SODDISFATTO in coda
    from ..config import VERDICT_SEVERITY_ORDER

    records.sort(
        key=lambda r: (-_risk_rank(r), -VERDICT_SEVERITY_ORDER[r.verdict.value]),
    )

    matrix = _build_matrix(records)
    declared_gaps = list(bundle.declared_gaps)
    return records, matrix, declared_gaps, list(adj.open_questions)


def _build_matrix(records: list[AuditRecord]) -> Matrix:
    counts: dict[str, int] = {v.value: 0 for v in _VERDICTS}
    by_verdict: dict[str, list[str]] = {v.value: [] for v in _VERDICTS}
    for r in records:
        counts[r.verdict.value] += 1
        by_verdict[r.verdict.value].append(_record_ref(r.original_ref, r.speclift_refs))
    return Matrix(counts=counts, records_by_verdict=by_verdict)
