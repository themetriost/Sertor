"""Stadio 7 — render: `SpecLiftReport` → JSON canonico (fonte di verità) + vista Markdown derivata.

Il JSON è l'output canonico (conforme a `contracts/output.schema.json`). La vista Markdown è derivata
**dallo stesso payload JSON** (`report_to_dict`): così l'equivalenza biunivoca di requisiti e àncore è
garantita *per costruzione* (US4) — non ci sono due fonti che possono divergere.
"""

from __future__ import annotations

import json

from speclift.domain.models import SpecLiftReport
from speclift.serialize import report_to_dict


def render_json(report: SpecLiftReport) -> str:
    """JSON canonico, deterministico (indentato, UTF-8, chiavi nell'ordine di dominio)."""
    return json.dumps(report_to_dict(report), indent=2, ensure_ascii=False) + "\n"


def render_markdown(report: SpecLiftReport) -> str:
    """Vista Markdown derivata dal payload canonico del report."""
    return markdown_from_payload(report_to_dict(report))


def markdown_from_payload(payload: dict) -> str:
    """Costruisce il Markdown a partire dal dict canonico (la stessa fonte del JSON)."""
    out: list[str] = [f"# SpecLift — requisiti per `{payload['changeset_ref']}`", ""]

    requirements = payload.get("requirements", [])
    if not requirements:
        out.append("_Nessun requisito confermato._")
        out.append("")
    for req in requirements:
        out.append(f"## {req['id']} · {req['quota']}")
        out.append("")
        out.append(req["statement"])
        out.append("")
        out.append(f"- **Àncora**: `{_anchor_label(req['anchor'])}` ({req['anchor']['status']})")
        out.append("")

    drifts = payload.get("drifts", [])
    if drifts:
        out.append("## Drift proposti")
        out.append("")
        for d in drifts:
            out.append(f"- _(proposed)_ {d['description']} — `{_anchor_label(d['anchor'])}`")
        out.append("")

    excluded = payload.get("excluded", [])
    if excluded:
        out.append("## Requisiti esclusi (àncora non verificabile)")
        out.append("")
        for e in excluded:
            out.append(f"- {e['statement']} — {e['reason']}")
        out.append("")

    open_questions = payload.get("open_questions", [])
    if open_questions:
        out.append("## Domande aperte")
        out.append("")
        for q in open_questions:
            out.append(f"- {q}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _anchor_label(anchor: dict) -> str:
    base = f"{anchor['file']}:{anchor['lines'][0]}-{anchor['lines'][1]}"
    if anchor.get("symbol"):
        base += f" [{anchor['symbol']}]"
    if anchor.get("test"):
        base += f" (test: {anchor['test']['path']})"
    return base
