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
import time
from collections.abc import Sequence

from sertor_core.config.settings import Settings
from sertor_core.domain.entities import IndexReport, RetrievalResult
from sertor_core.services.episodic_search import EpisodicResults
from sertor_core.services.memory_archive import ArchiveRunReport


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


def format_archive_report(report: ArchiveRunReport, *, json: bool) -> str:
    """Formats the outcome of `memory archive` (035, FR-002/003, SC-001).

    Counts only, never secrets. Human/JSON informational equivalence is the invariant (FR-003):
    both report `archived`/`skipped`/`errors`.
    """
    if json:
        return _json.dumps(
            {
                "archived": report.archived,
                "skipped": report.skipped,
                "errors": report.errors,
            }
        )
    return (
        f"archived={report.archived} "
        f"skipped={report.skipped} "
        f"errors={report.errors}"
    )


def _iso_utc(epoch: float) -> str:
    """Render an epoch-UTC timestamp as ISO-8601 UTC (`2026-06-14T10:21:03Z`) for the human view."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def format_memory_results(
    results: EpisodicResults, settings: Settings, *, json: bool
) -> str:
    """Formats the results of `memory search` (035, FR-006/009, SC-002).

    Same citation style as `format_search_results`. Each hit exposes `session_key`, `captured_at`,
    `role`, `turn_index`, `snippet`, `score`. `captured_at` is rendered ISO-8601 UTC in the human
    view and as the raw epoch float in JSON (machine-consumable). Empty `hits` → honest empty state
    (`(no results)`), never an error. No `--full`: the core already returns a `snippet` (the
    synthetic form), so there is nothing to expand (research D5).
    """
    hits = results.hits
    if json:
        return _json.dumps(
            [
                {
                    "session_key": h.session_key,
                    "captured_at": h.captured_at,
                    "role": h.role,
                    "turn_index": h.turn_index,
                    "snippet": h.snippet,
                    "score": round(h.score, 6),
                }
                for h in hits
            ]
        )
    if not hits:
        return "(no results)"
    blocks: list[str] = []
    for i, h in enumerate(hits, start=1):
        blocks.append(
            f"[{i}] score={h.score:.3f}  role={h.role}  session={h.session_key}  "
            f"turn={h.turn_index}  @={_iso_utc(h.captured_at)}\n"
            f"    {h.snippet}"
        )
    return "\n".join(blocks)
