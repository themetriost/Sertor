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
from sertor_core.domain.memory import ArchivedSession, SessionSummary
from sertor_core.engines.evaluation import EvalReport
from sertor_core.services.episodic_search import EpisodicResults
from sertor_core.services.eval.models import (
    FusedEvalReport,
    FusedRegressionVerdict,
    GraphEvalReport,
    GraphRegressionVerdict,
    PathValidation,
    RefValidation,
    RegressionVerdict,
)
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
                "mode": report.mode,
                "documents": report.documents,
                "chunks": report.chunks,
                "added": report.added,
                "updated": report.updated,
                "removed": report.removed,
                "unchanged": report.unchanged,
                "cache_hits": report.cache_hits,
                "embedding_dim": report.embedding_dim,  # None → null nel JSON
                "elapsed_ms": report.elapsed_ms,
            }
        )
    return (
        f"mode={report.mode} "
        f"collection={report.collection} "
        f"documents={report.documents} "
        f"chunks={report.chunks} "
        f"added={report.added} updated={report.updated} "
        f"removed={report.removed} unchanged={report.unchanged} "
        f"cache_hits={report.cache_hits} "
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
    if json:
        return _json.dumps(_results_json(results, settings, full=full))
    return _results_human(results, settings, full=full)


def _results_json(
    results: Sequence[RetrievalResult], settings: Settings, *, full: bool
) -> list[dict]:
    """One result → its JSON dict (shared by the mono-type and fused renderers)."""
    field = "text" if full else "preview"
    return [
        {
            "path": r.path,
            "doc_type": str(r.doc_type),
            "chunk_id": r.chunk_id,
            "score": round(r.score, 6),
            field: _preview(r.text, settings, full=full),
        }
        for r in results
    ]


def _results_human(
    results: Sequence[RetrievalResult], settings: Settings, *, full: bool
) -> str:
    """Human block for a result list (shared); empty → `(no results)` (honest empty state)."""
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


def format_fused_search_results(
    docs: list[RetrievalResult],
    code: list[RetrievalResult],
    settings: Settings,
    *,
    json: bool,
    full: bool,
) -> str:
    """Formats `search_combined` (070, DA-d): TWO labelled flows (`docs` / `code`).

    Takes the two flows of the `(docs, code)` tuple returned by `search_combined`. Human: a `docs:`
    section then a `code:` section, each rendered with the existing per-result logic (no
    duplication, Principio III/VII); an empty flow → its label + `(no results)` (honest empty,
    never
    silence). JSON: `{"docs": [...], "code": [...]}` — the twin of the MCP. The citable `path#chunk`
    form is preserved in both. `--type code`/`--type doc` are unchanged (they keep using
    `format_search_results`).
    """
    if json:
        return _json.dumps(
            {
                "docs": _results_json(docs, settings, full=full),
                "code": _results_json(code, settings, full=full),
            }
        )
    return (
        "docs:\n"
        + _indent(_results_human(docs, settings, full=full))
        + "\n\ncode:\n"
        + _indent(_results_human(code, settings, full=full))
    )


def _indent(block: str) -> str:
    """Indent each line of a rendered result block by two spaces (section nesting)."""
    return "\n".join(f"  {line}" if line else line for line in block.split("\n"))


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


def format_session_transcript(session: ArchivedSession, *, json: bool) -> str:
    """Formats the full transcript of a session for `memory show` (036, FR-001/SC-001).

    The text is rendered in FULL — no truncation, no preview: the session is already targeted, the
    point is the entire content for distillation (research D5). `captured_at`/`ts` are ISO-8601 UTC
    in the human view and raw epoch floats in JSON; a turn with no timestamp renders `@=?` (human)
    / `null` (JSON). An existing session with no turns prints an explicit empty state and an empty
    `turns` (distinct from "not found", handled in the CLI handler, not here). Human/JSON
    informational equivalence is the invariant (SC-002).
    """
    if json:
        return _json.dumps(
            {
                "session_key": session.session_key,
                "project_id": session.project_id,
                "captured_at": session.captured_at,
                "adapter_kind": session.adapter_kind,
                "turns": [
                    {"index": t.index, "role": t.role, "ts": t.ts, "text": t.text}
                    for t in session.turns
                ],
            }
        )
    header = (
        f"session={session.session_key}  @={_iso_utc(session.captured_at)}  "
        f"turns={len(session.turns)}  adapter={session.adapter_kind}"
    )
    if not session.turns:
        return f"{header}\n(empty session)"
    blocks: list[str] = [header]
    for t in session.turns:
        ts = _iso_utc(t.ts) if t.ts is not None else "?"
        blocks.append(f"[{t.index}] {t.role}  @={ts}\n    {t.text}")
    return "\n".join(blocks)


def _hit_rate_line(hit_rate: dict[int, float]) -> str:
    """`hit@1=0.55  hit@3=0.82  …` for a hit-rate dict, k ascending."""
    return "  ".join(f"hit@{k}={hit_rate[k]:.2f}" for k in sorted(hit_rate))


def _verdict_line(verdict: RegressionVerdict) -> str:
    """One-line non-regression summary: `non-regression: PASS (tolerance=…)  mrr Δ=… …`."""
    label = {"pass": "PASS", "regressed": "REGRESSED", "no-baseline": "NO-BASELINE"}[
        verdict.verdict
    ]
    deltas = "  ".join(f"{d.name} Δ={d.delta:+.2f}" for d in verdict.deltas)
    head = f"non-regression: {label} (tolerance={verdict.tolerance:.2f})"
    return f"{head}  {deltas}".rstrip()


def format_eval_report(
    report: EvalReport,
    kinds: tuple[str | None, ...],
    verdict: RegressionVerdict | None,
    *,
    json: bool,
) -> str:
    """Format an eval run: aggregate metrics + per-query hit/miss detail (065, REQ-033/SC-002).

    Human: a metrics line, then one row per query `[hit]`/`[miss]` + kind + rank + path; an
    optional non-regression line. JSON: the informational equivalent (same fields). The `kind` is
    re-associated from the suite by index (the core report does not carry it).
    """
    if json:
        return _json.dumps(
            {
                "provider": report.provider,
                "queries": report.queries,
                "hit_rate": {str(k): report.hit_rate[k] for k in sorted(report.hit_rate)},
                "mrr": round(report.mrr, 6),
                "per_query": [
                    {
                        "query": o.query,
                        "kind": kinds[i] if i < len(kinds) else None,
                        "hit": o.hit,
                        "rank": o.rank,
                        "expected": list(o.expected),
                        "top_path": o.top_path,
                    }
                    for i, o in enumerate(report.per_query)
                ],
                "non_regression": None
                if verdict is None
                else {
                    "verdict": verdict.verdict,
                    "tolerance": verdict.tolerance,
                    "deltas": [
                        {
                            "name": d.name,
                            "current": d.current,
                            "baseline": d.baseline,
                            "delta": d.delta,
                            "regressed": d.regressed,
                        }
                        for d in verdict.deltas
                    ],
                },
            }
        )
    lines = [
        f"provider={report.provider}  queries={report.queries}",
        f"{_hit_rate_line(report.hit_rate)}  mrr={report.mrr:.2f}",
    ]
    for i, o in enumerate(report.per_query):
        kind = kinds[i] if i < len(kinds) else None
        tag = "hit " if o.hit else "miss"
        rank = str(o.rank) if o.rank is not None else "-"
        detail = (
            f"{', '.join(o.expected)} → {o.top_path}"
            if o.hit
            else f"{o.query}  (top: {o.top_path})"
        )
        lines.append(f"[{tag}] {kind or '-':<7} rank={rank:<3} {detail}")
    if verdict is not None:
        lines.append(_verdict_line(verdict))
    return "\n".join(lines)


def format_comparison(
    reports: tuple[tuple[str, EvalReport], ...], *, json: bool
) -> str:
    """Format a side-by-side comparison of ≥2 configs on the same suite (065, REQ-034)."""
    if json:
        return _json.dumps(
            {
                label: {
                    "provider": rep.provider,
                    "hit_rate": {str(k): rep.hit_rate[k] for k in sorted(rep.hit_rate)},
                    "mrr": round(rep.mrr, 6),
                }
                for label, rep in reports
            }
        )
    if not reports:
        return "(no configs to compare)"
    labels = [label for label, _ in reports]
    # Union of all k across reports, ascending.
    ks = sorted({k for _, rep in reports for k in rep.hit_rate})
    header = "metric".ljust(10) + "".join(label.ljust(11) for label in labels)
    lines = [header]
    for k in ks:
        row = f"hit@{k}".ljust(10) + "".join(
            f"{rep.hit_rate.get(k, 0.0):.2f}".ljust(11) for _, rep in reports
        )
        lines.append(row)
    mrr_row = "mrr".ljust(10) + "".join(f"{rep.mrr:.2f}".ljust(11) for _, rep in reports)
    lines.append(mrr_row)
    return "\n".join(lines)


def format_regression_report(verdict: RegressionVerdict, *, json: bool) -> str:
    """Format a standalone non-regression verdict (065, REQ-043)."""
    if json:
        return _json.dumps(
            {
                "verdict": verdict.verdict,
                "tolerance": verdict.tolerance,
                "deltas": [
                    {
                        "name": d.name,
                        "current": d.current,
                        "baseline": d.baseline,
                        "delta": d.delta,
                        "regressed": d.regressed,
                    }
                    for d in verdict.deltas
                ],
            }
        )
    return _verdict_line(verdict)


def _fused_verdict_line(verdict: FusedRegressionVerdict) -> str:
    """One-line fused non-regression summary (070): label + per-metric Δ (incl. union_hit_rate)."""
    label = {"pass": "PASS", "regressed": "REGRESSED", "no-baseline": "no baseline"}[
        verdict.verdict
    ]
    deltas = "  ".join(f"{d.name} Δ={d.delta:+.2f}" for d in verdict.deltas)
    head = f"non-regression: {label} (tolerance={verdict.tolerance:.2f})"
    return f"{head}  {deltas}".rstrip()


def _fused_verdict_json(verdict: FusedRegressionVerdict) -> dict:
    return {
        "verdict": verdict.verdict,
        "tolerance": verdict.tolerance,
        "deltas": [
            {
                "name": d.name,
                "current": d.current,
                "baseline": d.baseline,
                "delta": d.delta,
                "regressed": d.regressed,
            }
            for d in verdict.deltas
        ],
    }


def format_fused_eval_report(
    report: FusedEvalReport, verdict: FusedRegressionVerdict, *, json: bool
) -> str:
    """Format a fused run: per-surface metrics + union hit-rate + non-regression (070, REQ-021).

    Human: header (cases per intent + provider) + per-surface hit-rate@k/MRR + the union hit-rate
    block (one `[hit]`/`[miss]` row per `both`-intent case with which stream found it) + a
    non-regression line. The headline is the UNION (OR), not the AND (`has_doc`/`has_code` survive
    only as informative per-case detail). JSON: the informational equivalent. The union hit-rate is
    reported ACCANTO a hit@k/MRR, never instead (REQ-042/SC-008).
    """
    fusion = report.fusion
    by_surface = {s.surface: s.report for s in report.surfaces}
    code_n = by_surface["search_code"].queries if "search_code" in by_surface else 0
    docs_n = by_surface["search_docs"].queries if "search_docs" in by_surface else 0
    if json:
        return _json.dumps(
            {
                "provider": report.provider,
                "cases": {"code": code_n, "doc": docs_n, "both": fusion.cases_count},
                "surfaces": [
                    {
                        "surface": s.surface,
                        "provider": s.report.provider,
                        "queries": s.report.queries,
                        "hit_rate": {
                            str(k): s.report.hit_rate[k] for k in sorted(s.report.hit_rate)
                        },
                        "mrr": round(s.report.mrr, 6),
                    }
                    for s in report.surfaces
                ],
                "fusion": {
                    "union_hit_rate": round(fusion.union_hit_rate, 6),
                    "cases_count": fusion.cases_count,
                    "cases": [
                        {
                            "query": c.query,
                            "expected": list(c.expected),
                            "has_doc": c.has_doc,
                            "has_code": c.has_code,
                            "hit": c.hit,
                        }
                        for c in fusion.cases
                    ],
                },
                "non_regression": _fused_verdict_json(verdict),
            }
        )
    hit_count = sum(1 for c in fusion.cases if c.hit)
    lines = [
        f"fused eval  cases: code={code_n} docs={docs_n} fusion={fusion.cases_count}  "
        f"provider={report.provider}",
        "",
        "per-surface (hit-rate@k / MRR):",
    ]
    for s in report.surfaces:
        at_k = " ".join(
            f"@{k}={s.report.hit_rate[k]:.2f}" for k in sorted(s.report.hit_rate)
        )
        lines.append(f"  {s.surface:<16} {at_k}  MRR={s.report.mrr:.2f}")
    lines.append("")
    head = (
        f"union hit-rate: {fusion.union_hit_rate:.2f}  "
        f"({hit_count}/{fusion.cases_count} hit in doc OR code)"
    )
    lines.append(head)
    for c in fusion.cases:
        if c.hit:
            lines.append(f"  [hit ] {c.query}   {_fusion_hit_detail(c)}")
        else:
            lines.append(f"  [miss] {c.query}   neither doc nor code retrieved")
    lines.append("")
    lines.append(_fused_verdict_line(verdict))
    return "\n".join(lines)


def _fusion_hit_detail(case) -> str:
    """Human detail of which stream(s) found a `both` case (070, informative only)."""
    if case.has_doc and case.has_code:
        return "doc+code"
    if case.has_doc:
        return "doc only"
    return "code only"


def format_fused_regression(verdict: FusedRegressionVerdict, *, json: bool) -> str:
    """Format a standalone fused non-regression verdict (069). Reusable."""
    if json:
        return _json.dumps(_fused_verdict_json(verdict))
    return _fused_verdict_line(verdict)


def format_path_validation(pv: PathValidation, *, json: bool) -> str:
    """Format a write-time path validation (065, REQ-012). Exit 0 always (it is a check)."""
    if json:
        return _json.dumps(
            {
                "checked": list(pv.checked),
                "missing": list(pv.missing),
                "index_available": pv.index_available,
            }
        )
    if not pv.index_available:
        return (
            f"index not available: cannot verify {len(pv.checked)} path(s) "
            "— index the project first with `sertor-rag index .`"
        )
    if not pv.missing:
        return f"all {len(pv.checked)} path(s) present in the index"
    return (
        f"warning: {len(pv.missing)} of {len(pv.checked)} path(s) NOT in the index: "
        + ", ".join(pv.missing)
    )


def _case_tag(metric) -> str:
    """`[exact]`/`[miss ]`/`[part ]` for one case (066, TASK-A02 rules)."""
    if metric.exact:
        return "exact"
    if metric.recall < 1.0 and metric.precision == 1.0:
        return "miss "
    return "part "


def _graph_verdict_line(verdict: GraphRegressionVerdict) -> str:
    """One-line graph non-regression summary (066)."""
    label = {"pass": "PASS", "regressed": "REGRESSED", "no-baseline": "NO-BASELINE"}[
        verdict.verdict
    ]
    deltas = "  ".join(f"{d.name} Δ={d.delta:+.2f}" for d in verdict.deltas)
    head = f"non-regression: {label} (tolerance={verdict.tolerance:.2f})"
    return f"{head}  {deltas}".rstrip()


def format_graph_eval_report(
    report: GraphEvalReport, verdict: GraphRegressionVerdict, *, json: bool
) -> str:
    """Format a graph-navigation run: set metrics + per-case detail (066, REQ-021/030/SC-002).

    Human: header + means + by-relation + one row per case (`[exact]`/`[part ]`/`[miss ]` + relation
    + target + P/R/F1 + `+extra`/`-missing` when non-empty) + a non-regression line. JSON: the
    informational equivalent. Rendered in a DISTINCT section from the IR `eval` report (REQ-030).
    """
    if json:
        return _json.dumps(
            {
                "cases": report.cases_count,
                "mean_f1": round(report.mean_f1, 6),
                "mean_recall": round(report.mean_recall, 6),
                "mean_precision": round(report.mean_precision, 6),
                "by_relation": {k: round(v, 6) for k, v in report.by_relation.items()},
                "per_case": [
                    {
                        "relation": c.relation,
                        "target": c.target,
                        "precision": round(c.metric.precision, 6),
                        "recall": round(c.metric.recall, 6),
                        "f1": round(c.metric.f1, 6),
                        "exact": c.metric.exact,
                        "got": list(c.metric.got),
                        "expected": list(c.metric.expected),
                        "missing": list(c.metric.missing),
                        "extra": list(c.metric.extra),
                    }
                    for c in report.cases
                ],
                "non_regression": {
                    "verdict": verdict.verdict,
                    "tolerance": verdict.tolerance,
                    "deltas": [
                        {
                            "name": d.name,
                            "current": d.current,
                            "baseline": d.baseline,
                            "delta": d.delta,
                            "regressed": d.regressed,
                        }
                        for d in verdict.deltas
                    ],
                },
            }
        )
    lines = [
        f"graph navigation eval  cases={report.cases_count}",
        f"mean_f1={report.mean_f1:.2f}  mean_recall={report.mean_recall:.2f}  "
        f"mean_precision={report.mean_precision:.2f}",
    ]
    if report.by_relation:
        by_rel = "  ".join(f"{rel}={f1:.2f}" for rel, f1 in sorted(report.by_relation.items()))
        lines.append(f"by-relation: {by_rel}")
    for c in report.cases:
        m = c.metric
        row = (
            f"[{_case_tag(m)}] {c.relation:<10} {c.target:<22} "
            f"P={m.precision:.2f} R={m.recall:.2f} F1={m.f1:.2f}"
        )
        if m.extra:
            row += f"  +extra: {', '.join(m.extra)}"
        if m.missing:
            row += f"  -missing: {', '.join(m.missing)}"
        lines.append(row)
    lines.append(_graph_verdict_line(verdict))
    return "\n".join(lines)


def format_graph_regression(verdict: GraphRegressionVerdict, *, json: bool) -> str:
    """Format a standalone graph non-regression verdict (066). Reusable."""
    if json:
        return _json.dumps(
            {
                "verdict": verdict.verdict,
                "tolerance": verdict.tolerance,
                "deltas": [
                    {
                        "name": d.name,
                        "current": d.current,
                        "baseline": d.baseline,
                        "delta": d.delta,
                        "regressed": d.regressed,
                    }
                    for d in verdict.deltas
                ],
            }
        )
    return _graph_verdict_line(verdict)


def format_ref_validation(rv: RefValidation, *, json: bool) -> str:
    """Format a write-time ref validation (066, REQ-042). Exit 0 always (it is a check)."""
    if json:
        return _json.dumps(
            {
                "checked": list(rv.checked),
                "unverifiable": list(rv.unverifiable),
                "graph_available": rv.graph_available,
            }
        )
    if not rv.graph_available:
        return (
            f"graph not available: cannot verify {len(rv.checked)} ref(s) "
            "— index the project first with `sertor-rag index .`"
        )
    if not rv.unverifiable:
        return f"all {len(rv.checked)} ref(s) confirmed by the graph"
    return (
        f"warning: {len(rv.unverifiable)} of {len(rv.checked)} ref(s) NOT confirmed by the graph: "
        + ", ".join(rv.unverifiable)
    )


def format_session_list(summaries: Sequence[SessionSummary], *, json: bool) -> str:
    """Formats the recent-sessions list for `memory list` (036, FR-002/SC-002).

    Recency-first order is the core's responsibility (`list_recent`); this view only renders. Each
    entry exposes `session_key`/`captured_at`/`turn_count` (counts only, never content). Empty list
    → honest empty state (`(no sessions)` / `[]`), never an error. Human/JSON informational
    equivalence is the invariant (SC-002).
    """
    if json:
        return _json.dumps(
            [
                {
                    "session_key": s.session_key,
                    "captured_at": s.captured_at,
                    "turn_count": s.turn_count,
                }
                for s in summaries
            ]
        )
    if not summaries:
        return "(no sessions)"
    blocks: list[str] = []
    for i, s in enumerate(summaries, start=1):
        blocks.append(
            f"[{i}] session={s.session_key}  @={_iso_utc(s.captured_at)}  turns={s.turn_count}"
        )
    return "\n".join(blocks)
