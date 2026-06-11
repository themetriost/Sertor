"""Proiezioni di output della CLI `sertor-rag` (umano vs `--json`).

Pure funzioni di formattazione: prendono le entità del core (`IndexReport`, `RetrievalResult`) e ne
producono una rappresentazione testuale. Nessuna logica di retrieval (Principio I) — solo vista.
L'equivalenza informativa umano/JSON è un invariante richiesto (SC-002).

Campi opzionali del report (`elapsed_ms`, `embedding_dim`): possono essere `None` (es. corpus vuoto
→ provider mai interrogato → `dim` ignota). Resa esplicita e coerente tra i due formati: nel JSON il
campo è presente con valore `null`; nel formato umano si rende con `?` (fix F7/F12 analyze).
"""
from __future__ import annotations

import json as _json
from collections.abc import Sequence

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import IndexReport, RetrievalResult


def _human_optional(value) -> str:
    """Rende un campo opzionale nel formato umano: `?` se assente (fix F7/F12)."""
    return "?" if value is None else str(value)


def format_index_report(report: IndexReport, *, json: bool) -> str:
    """Formatta l'esito di `index` (FR-005/007/008, SC-001)."""
    if json:
        return _json.dumps(
            {
                "collection": report.collection,
                "documents": report.documents,
                "chunks": report.chunks,
                "embedding_dim": report.embedding_dim,  # None → null nel JSON
                "elapsed_ms": report.elapsed_ms,
            }
        )
    return (
        f"collection={report.collection} "
        f"documents={report.documents} "
        f"chunks={report.chunks} "
        f"embedding_dim={_human_optional(report.embedding_dim)} "
        f"elapsed_ms={_human_optional(report.elapsed_ms)}"
    )


def _preview(text: str, settings: Settings, *, full: bool) -> str:
    """Testo completo con `--full`, altrimenti anteprima troncata a `preview_chars` (D5)."""
    if full or len(text) <= settings.preview_chars:
        return text
    return text[: settings.preview_chars] + "…"


def format_search_results(
    results: Sequence[RetrievalResult], settings: Settings, *, json: bool, full: bool
) -> str:
    """Formatta i risultati di `search` (FR-010/011/013, SC-002).

    Ogni hit espone almeno `path`, `doc_type`, `chunk_id`, `score` e l'anteprima/testo. Con `--full`
    il campo testuale è il testo integrale (`text`), altrimenti l'anteprima troncata (`preview`).
    """
    field = "text" if full else "preview"
    if json:
        return _json.dumps(
            [
                {
                    "path": r.path,
                    "doc_type": str(r.doc_type),
                    "chunk_id": r.chunk_id,
                    "score": round(r.score, 6),
                    field: _preview(r.text, settings, full=full),
                }
                for r in results
            ]
        )
    if not results:
        return "(nessun risultato)"
    blocks: list[str] = []
    for i, r in enumerate(results, start=1):
        body = _preview(r.text, settings, full=full)
        blocks.append(
            f"[{i}] score={r.score:.3f}  doc={r.doc_type}  path={r.path}  chunk={r.chunk_id}\n"
            f"    {body}"
        )
    return "\n".join(blocks)
