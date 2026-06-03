"""Formattazione dell'output: testo leggibile o JSON, anteprime troncate (REQ-020/023)."""
from __future__ import annotations

import json

from sertor_core.domain.entities import IndexReport, RetrievalResult

PREVIEW_CHARS = 200  # lunghezza massima dell'anteprima (economia di token); --full la disattiva


def _preview(text: str, full: bool) -> str:
    flat = " ".join(text.split())
    if full:
        return text
    return flat if len(flat) <= PREVIEW_CHARS else flat[:PREVIEW_CHARS] + "…"


def format_results(
    results: list[RetrievalResult], *, as_json: bool = False, full: bool = False
) -> str:
    """Formatta i risultati di `search` come JSON (per agenti) o testo (per umani)."""
    if as_json:
        payload = [
            {
                "path": r.path,
                "doc_type": r.doc_type.value,
                "chunk_id": r.chunk_id,
                "score": round(r.score, 4),
                "preview": _preview(r.text, full),
            }
            for r in results
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    if not results:
        return "(nessun risultato)"
    lines: list[str] = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.path}  [{r.doc_type.value}]  score {r.score:.3f}  ({r.chunk_id})")
        lines.append(f"   {_preview(r.text, full)}")
    return "\n".join(lines)


def format_report(report: IndexReport, *, as_json: bool = False) -> str:
    """Formatta il report di indicizzazione."""
    if as_json:
        return json.dumps(
            {
                "collection": report.collection,
                "documents": report.documents,
                "chunks": report.chunks,
                "embedding_dim": report.embedding_dim,
                "elapsed_ms": report.elapsed_ms,
            },
            ensure_ascii=False,
            indent=2,
        )
    if report.chunks == 0:
        return "Nessun documento indicizzato."
    return (
        f"Indicizzati {report.documents} documenti, {report.chunks} chunk "
        f"(dim embedding {report.embedding_dim}) nella collezione '{report.collection}'."
    )
