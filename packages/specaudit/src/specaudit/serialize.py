"""Serializzazione dict<->model per i tre contratti (audit-bundle, adjudication, output).

Il JSON canonico è la fonte di verità; questi helper sono l'unico punto in cui la forma di wire
incontra il dominio.
"""

from __future__ import annotations

from typing import Any

from .domain.models import (
    Adjudication,
    AlignedGroup,
    Anchor,
    AuditBundle,
    AuditRecord,
    AuditReport,
    ExtraItem,
    Level,
    Matrix,
    OriginalRequirement,
    RiskScore,
    SpecLiftItem,
    VerdictKind,
)

# --- Anchor --------------------------------------------------------------------------------


def anchor_to_dict(a: Anchor) -> dict[str, Any]:
    return {
        "file": a.file,
        "lines": [a.lines[0], a.lines[1]],
        "symbol": a.symbol,
        "test": a.test,
        "granularity": a.granularity,
        "status": a.status,
    }


def anchor_from_dict(d: dict[str, Any]) -> Anchor:
    lines = d["lines"]
    return Anchor(
        file=d["file"],
        lines=(int(lines[0]), int(lines[1])),
        granularity=d["granularity"],
        status=d["status"],
        symbol=d.get("symbol"),
        test=d.get("test"),
    )


# --- AuditBundle ---------------------------------------------------------------------------


def bundle_to_dict(b: AuditBundle) -> dict[str, Any]:
    return {
        "version": b.version,
        "changeset_ref": b.changeset_ref,
        "original": [
            {"index": o.index, "id": o.id, "text": o.text, "provenance": o.provenance}
            for o in b.original
        ],
        "speclift": [
            {
                "index": s.index,
                "origin": s.origin,
                "quota": s.quota,
                "statement": s.statement,
                "anchor": anchor_to_dict(s.anchor),
            }
            for s in b.speclift
        ],
        "declared_gaps": list(b.declared_gaps),
        "source_provenance": dict(b.source_provenance),
    }


def bundle_from_dict(d: dict[str, Any]) -> AuditBundle:
    return AuditBundle(
        version=d["version"],
        changeset_ref=d["changeset_ref"],
        original=[
            OriginalRequirement(
                index=o["index"], id=o["id"], text=o["text"], provenance=o["provenance"]
            )
            for o in d["original"]
        ],
        speclift=[
            SpecLiftItem(
                index=s["index"],
                origin=s["origin"],
                statement=s["statement"],
                anchor=anchor_from_dict(s["anchor"]),
                quota=s.get("quota"),
            )
            for s in d["speclift"]
        ],
        declared_gaps=list(d.get("declared_gaps", [])),
        source_provenance=dict(d["source_provenance"]),
    )


# --- Adjudication --------------------------------------------------------------------------


def _level(v: Any) -> Level | None:
    return Level(v) if v is not None else None


def adjudication_from_dict(d: dict[str, Any]) -> Adjudication:
    groups = [
        AlignedGroup(
            original=g["original"],
            speclift=list(g.get("speclift", [])),
            alignment_confidence=Level(g["alignment_confidence"]),
            verdict=VerdictKind(g["verdict"]),
            verdict_confidence=Level(g["verdict_confidence"]),
            explanation=g.get("explanation"),
            severity=_level(g.get("severity")),
            detectability=_level(g.get("detectability")),
        )
        for g in d["groups"]
    ]
    extras = [
        ExtraItem(
            speclift=e["speclift"],
            verdict=VerdictKind(e["verdict"]),
            explanation=e["explanation"],
            verdict_confidence=Level(e["verdict_confidence"]),
            severity=_level(e.get("severity")),
            detectability=_level(e.get("detectability")),
        )
        for e in d["extras"]
    ]
    return Adjudication(
        changeset_ref=d["changeset_ref"],
        groups=groups,
        extras=extras,
        open_questions=list(d.get("open_questions", [])),
    )


def adjudication_to_dict(a: Adjudication) -> dict[str, Any]:
    def _grp(g: AlignedGroup) -> dict[str, Any]:
        out: dict[str, Any] = {
            "original": g.original,
            "speclift": list(g.speclift),
            "alignment_confidence": g.alignment_confidence.value,
            "verdict": g.verdict.value,
            "verdict_confidence": g.verdict_confidence.value,
        }
        if g.explanation is not None:
            out["explanation"] = g.explanation
        if g.severity is not None:
            out["severity"] = g.severity.value
        if g.detectability is not None:
            out["detectability"] = g.detectability.value
        return out

    def _extra(e: ExtraItem) -> dict[str, Any]:
        out: dict[str, Any] = {
            "speclift": e.speclift,
            "verdict": e.verdict.value,
            "explanation": e.explanation,
            "verdict_confidence": e.verdict_confidence.value,
        }
        if e.severity is not None:
            out["severity"] = e.severity.value
        if e.detectability is not None:
            out["detectability"] = e.detectability.value
        return out

    return {
        "changeset_ref": a.changeset_ref,
        "groups": [_grp(g) for g in a.groups],
        "extras": [_extra(e) for e in a.extras],
        "open_questions": list(a.open_questions),
    }


# --- AuditReport ---------------------------------------------------------------------------


def _risk_to_dict(r: RiskScore | None) -> dict[str, Any] | None:
    if r is None:
        return None
    return {"severity": r.severity.value, "detectability": r.detectability.value, "risk": r.risk.value}


def record_to_dict(r: AuditRecord) -> dict[str, Any]:
    return {
        "original_ref": r.original_ref,
        "speclift_refs": list(r.speclift_refs),
        "verdict": r.verdict.value,
        "explanation": r.explanation,
        "verdict_confidence": r.verdict_confidence.value,
        "alignment_confidence": r.alignment_confidence.value if r.alignment_confidence else None,
        "anchors": [anchor_to_dict(a) for a in r.anchors],
        "risk": _risk_to_dict(r.risk),
        "proposed": r.proposed,
        "notes": list(r.notes),
    }


def report_to_dict(rep: AuditReport) -> dict[str, Any]:
    return {
        "version": rep.version,
        "changeset_ref": rep.changeset_ref,
        "records": [record_to_dict(r) for r in rep.records],
        "matrix": {
            "counts": dict(rep.matrix.counts),
            "records_by_verdict": dict(rep.matrix.records_by_verdict),
        },
        "declared_gaps": list(rep.declared_gaps),
        "open_questions": list(rep.open_questions),
    }


def _risk_from_dict(d: dict[str, Any] | None) -> RiskScore | None:
    if d is None:
        return None
    return RiskScore(
        severity=Level(d["severity"]), detectability=Level(d["detectability"]), risk=Level(d["risk"])
    )


def record_from_dict(d: dict[str, Any]) -> AuditRecord:
    return AuditRecord(
        verdict=VerdictKind(d["verdict"]),
        verdict_confidence=Level(d["verdict_confidence"]),
        anchors=[anchor_from_dict(a) for a in d["anchors"]],
        proposed=d["proposed"],
        speclift_refs=list(d["speclift_refs"]),
        original_ref=d.get("original_ref"),
        explanation=d.get("explanation"),
        alignment_confidence=_level(d.get("alignment_confidence")),
        risk=_risk_from_dict(d.get("risk")),
        notes=list(d.get("notes", [])),
    )


def report_from_dict(d: dict[str, Any]) -> AuditReport:
    m = d["matrix"]
    return AuditReport(
        version=d["version"],
        changeset_ref=d["changeset_ref"],
        records=[record_from_dict(r) for r in d["records"]],
        matrix=Matrix(counts=dict(m["counts"]), records_by_verdict=dict(m.get("records_by_verdict", {}))),
        declared_gaps=list(d.get("declared_gaps", [])),
        open_questions=list(d.get("open_questions", [])),
    )
