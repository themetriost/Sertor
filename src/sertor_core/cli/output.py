"""Output projections for the `sertor-rag` CLI (human vs `--json`).

Pure formatting functions: take core entities (`IndexReport`, `RetrievalResult`) and produce a
textual representation. No retrieval logic (Principio I) — view only.
Human/JSON informational equivalence is a required invariant (SC-002).

Optional report fields (`elapsed_ms`, `embedding_dim`): may be `None` (e.g. empty corpus
→ provider never queried → `dim` unknown). Rendered explicitly and consistently across both
formats: in JSON the field is present with value `null`; in human format rendered as `?`
(fix F7/F12 analyze).
"""
from __future__ import annotations

import json as _json
from collections.abc import Sequence

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import IndexReport, RetrievalResult


def _human_optional(value) -> str:
    """Renders an optional field in human format: `?` if absent (fix F7/F12)."""
    return "?" if value is None else str(value)


def format_index_report(report: IndexReport, *, json: bool) -> str:
    """Formats the outcome of `index` (FR-005/007/008, SC-001)."""
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
    """Full text with `--full`, otherwise truncated preview up to `preview_chars` (D5)."""
    if full or len(text) <= settings.preview_chars:
        return text
    return text[: settings.preview_chars] + "…"


def format_search_results(
    results: Sequence[RetrievalResult], settings: Settings, *, json: bool, full: bool
) -> str:
    """Formats the results of `search` (FR-010/011/013, SC-002).

    Each hit exposes at least `path`, `doc_type`, `chunk_id`, `score` and the preview/text. With
    `--full` the text field is the full chunk text (`text`), otherwise the truncated preview
    (`preview`).
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
        return "(no results)"
    blocks: list[str] = []
    for i, r in enumerate(results, start=1):
        body = _preview(r.text, settings, full=full)
        blocks.append(
            f"[{i}] score={r.score:.3f}  doc={r.doc_type}  path={r.path}  chunk={r.chunk_id}\n"
            f"    {body}"
        )
    return "\n".join(blocks)
