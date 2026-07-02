"""Stadio finale — render dell'`AuditReport`: JSON canonico + vista Markdown derivata.

Il JSON è la fonte di verità; il Markdown è DERIVATO dallo stesso oggetto (SC-006): stesso insieme
di verdetti e citazioni, zero divergenze.
"""

from __future__ import annotations

import json

from ..domain.models import AuditRecord, AuditReport
from ..serialize import report_to_dict


def to_json(report: AuditReport) -> str:
    return json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)


def _anchor_line(record: AuditRecord) -> str:
    if not record.anchors:
        return "_nessuna àncora_ (candidato MANCANTE: nessun item SpecLift allineato)"
    parts = []
    for a in record.anchors:
        loc = f"`{a.file}:{a.lines[0]}-{a.lines[1]}`"
        sym = f" · `{a.symbol}`" if a.symbol else ""
        test = f" · test `{a.test}`" if a.test else ""
        flag = " ⚠️ non verificata" if a.status == "unverified" else ""
        parts.append(f"{loc}{sym}{test}{flag}")
    return "; ".join(parts)


def to_markdown(report: AuditReport) -> str:
    m = report.matrix.counts
    lines: list[str] = []
    lines.append(f"# SpecAudit — report per `{report.changeset_ref}`")
    lines.append("")
    lines.append("## Matrice d'insieme")
    lines.append("")
    lines.append("| Verdetto | Conteggio |")
    lines.append("|----------|-----------|")
    for verdict in ("SODDISFATTO", "PARZIALE", "MANCANTE", "DRIFTED", "NON_DOCUMENTATO"):
        lines.append(f"| {verdict} | {m.get(verdict, 0)} |")
    lines.append("")

    if report.declared_gaps:
        lines.append("## Gap dichiarati")
        lines.append("")
        for gap in report.declared_gaps:
            lines.append(f"- ⚠️ {gap}")
        lines.append("")

    lines.append("## Verdetti (i più a rischio in cima)")
    lines.append("")
    for i, r in enumerate(report.records, start=1):
        title = r.original_ref or "(comportamento non documentato)"
        proposed = " _(proposto)_" if r.proposed else ""
        lines.append(f"### {i}. {title} — **{r.verdict.value}**{proposed}")
        lines.append("")
        lines.append(f"- **Confidenza verdetto**: {r.verdict_confidence.value}")
        if r.alignment_confidence is not None:
            lines.append(f"- **Confidenza allineamento**: {r.alignment_confidence.value}")
        if r.risk is not None:
            lines.append(
                f"- **Rischio**: {r.risk.risk.value} "
                f"(severità {r.risk.severity.value} × rilevabilità {r.risk.detectability.value})"
            )
        if r.explanation:
            lines.append(f"- **Come diverge**: {r.explanation}")
        lines.append(f"- **Àncora SpecLift**: {_anchor_line(r)}")
        if r.speclift_refs:
            lines.append(f"- **Item SpecLift**: {', '.join(f'`{s}`' for s in r.speclift_refs)}")
        for note in r.notes:
            lines.append(f"- _nota_: {note}")
        lines.append("")

    if report.open_questions:
        lines.append("## Domande aperte")
        lines.append("")
        for q in report.open_questions:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
