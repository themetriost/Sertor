"""RAG execution CLI `sertor-rag` (FEAT-011, contracts/cli-commands.md).

`sertor-rag index <path>` indexes a repository; `sertor-rag search <query>` queries the index.
Equivalent: `python -m sertor_core.cli`. **Thin** layer (Principio I): parsing → core composition
root → formatting. No retrieval logic here. Exit codes: `0` success · `1` domain error
(`SertorError`, message on stderr) · `2` usage error (argparse). Reference pattern:
`sertor_core/wiki_tools/__main__.py`.
"""
from __future__ import annotations

import argparse
import calendar
import dataclasses
import logging
import sys
import time
from pathlib import Path

from sertor_core.cli import output
from sertor_core.cli.logging_setup import setup_logging
from sertor_core.composition import (
    build_baseline_engine,
    build_episodic_search,
    build_eval_runner,
    build_facade,
    build_graph_eval_runner,
    build_indexed_docs,
    build_indexer,
    build_memory_archiver,
    build_memory_reader,
    enable_observability,
)
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import (
    ConfigError,
    GraphRegressionDetected,
    IngestionError,
    RegressionDetected,
    SertorError,
    SessionNotFoundError,
)
from sertor_core.observability.logging import log_event
from sertor_core.services.episodic_search import SearchQuery
from sertor_core.services.eval.baseline_io import (
    load_baseline,
    now_iso_utc,
    write_baseline,
)
from sertor_core.services.eval.graph_baseline_io import (
    now_iso_utc as graph_now_iso_utc,
)
from sertor_core.services.eval.graph_baseline_io import (
    write_graph_baseline,
)
from sertor_core.services.eval.graph_runner import validate_refs
from sertor_core.services.eval.models import Baseline, EvalCase, GraphBaseline, GraphCase
from sertor_core.services.eval.regression import compare_to_baseline
from sertor_core.services.eval.runner import emit_eval_event, validate_paths
from sertor_core.services.eval.suite_io import (
    add_case,
    add_graph_case,
    amend_graph_case,
    load_suite,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sertor-rag",
        description="RAG execution CLI: index a repository and query it from the terminal.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    p_index = sub.add_parser(
        "index", help="index a repository into a vector collection (incremental by default)",
        description=(
            "Builds/refreshes the repository's vector index and reports the counts. "
            "Incremental by default (only changed files are re-processed); --full forces a rebuild."
        ),
    )
    p_index.add_argument("path", help="root of the repository to index")
    p_index.add_argument("--full", action="store_true",
                         help="force a full rebuild from scratch (otherwise incremental)")
    p_index.add_argument("--corpus", default=None,
                         help="corpus namespace; overrides SERTOR_CORPUS")
    p_index.add_argument("--json", action="store_true", help="report as a JSON object")
    _add_logging_flags(p_index)
    p_index.set_defaults(handler=_cmd_index)

    p_search = sub.add_parser(
        "search", help="query the index and return the top-k results",
        description="Semantic search over the index; results with path, type, chunk_id, score.",
    )
    p_search.add_argument("query", help="query text (non-empty)")
    p_search.add_argument("-k", type=int, default=None,
                          help="number of results (default: Settings.default_k)")
    p_search.add_argument("--type", choices=["code", "doc", "both"], default="both",
                          help="document-type filter (default: both)")
    p_search.add_argument("--full", action="store_true",
                          help="full chunk text instead of the truncated preview")
    p_search.add_argument("--json", action="store_true", help="results as a JSON array")
    p_search.add_argument("--corpus", default=None,
                          help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_search)
    p_search.set_defaults(handler=_cmd_search)

    p_observe = sub.add_parser(
        "observe", help="open the live observability panel (TUI)",
        description="Live panel (last index, cache, cost, recent events), auto-refreshing. "
                    "Needs the `tui` extra and SERTOR_OBSERVABILITY=true.",
    )
    p_observe.add_argument("--corpus", default=None,
                           help="corpus namespace; overrides SERTOR_CORPUS")
    p_observe.set_defaults(handler=_cmd_observe)

    _add_memory_parser(sub)
    _add_eval_parser(sub)
    _add_graph_eval_parser(sub)

    return parser


def _add_eval_parser(sub) -> None:
    """`eval` command group with `run`/`add-case`/`validate-path` sub-subcommands (065, US1/US5).

    Mirrors the `memory` pattern: a nested `add_subparsers`, each action registering its handler
    via `set_defaults`. `required=True` gives the usage error (exit 2) when `sertor-rag eval` is
    invoked without an action. The run is a deterministic VEHICLE (Principio XI): never an LLM.
    """
    p_eval = sub.add_parser(
        "eval", help="ground-truth evaluation of retrieval quality + non-regression gate",
        description="Measure hit-rate@k/MRR against a versioned eval suite (eval/suite.toml) and "
                    "gate non-regression against a recorded baseline.",
    )
    esub = p_eval.add_subparsers(dest="eval_command", required=True, metavar="subcommand")

    p_run = esub.add_parser(
        "run", help="evaluate the suite and report metrics + non-regression verdict",
        description="Loads eval/suite.toml, builds the engine, computes hit-rate@k/MRR, and gates "
                    "against eval/baseline.toml (exit 1 on regression beyond tolerance).",
    )
    p_run.add_argument("--compare", default=None,
                       help="comma-separated config labels to compare on the same suite "
                            "(e.g. baseline,hybrid)")
    p_run.add_argument("--record-baseline", action="store_true",
                       help="record/update eval/baseline.toml with the current metrics")
    p_run.add_argument("--by-kind", action="store_true",
                       help="route each case by kind: symbol→code-graph, else→relevance engine "
                            "(measures the right tool per query; requires the code graph)")
    p_run.add_argument("-k", default=None,
                       help="comma-separated k values for hit-rate@k (default: 1,3,5,10)")
    p_run.add_argument("--json", action="store_true", help="report as a JSON object")
    p_run.add_argument("--corpus", default=None,
                       help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_run)
    p_run.set_defaults(handler=_cmd_eval_run)

    p_add = esub.add_parser(
        "add-case", help="add a case to the eval suite (validated against the index)",
        description="Persists a (query → expected paths) case in eval/suite.toml. A path absent "
                    "from the index warns and requires --confirm before writing.",
    )
    p_add.add_argument("--query", required=True, help="the query text (non-empty)")
    p_add.add_argument("--expected", required=True,
                       help="comma-separated expected path(s), POSIX, relative to the indexed root")
    p_add.add_argument("--kind", default=None, help='optional kind (e.g. "symbol"/"nl")')
    p_add.add_argument("--confirm", action="store_true",
                       help="write even if an expected path is not in the index")
    p_add.add_argument("--json", action="store_true", help="report as a JSON object")
    p_add.add_argument("--corpus", default=None,
                       help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_add)
    p_add.set_defaults(handler=_cmd_eval_add)

    p_val = esub.add_parser(
        "validate-path", help="check path(s) against the indexed documents (primitive for skills)",
        description="Reports which of the given paths are present/missing in the index. Exit 0 "
                    "always (it is a check, not a gate). Vehicle for the eval-authoring skills.",
    )
    p_val.add_argument("paths", nargs="+", help="one or more paths to check")
    p_val.add_argument("--json", action="store_true", help="report as a JSON object")
    p_val.add_argument("--corpus", default=None,
                       help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_val)
    p_val.set_defaults(handler=_cmd_eval_validate)


def _add_graph_eval_parser(sub) -> None:
    """`graph-eval` command group: set-based navigation eval + non-regression gate (066, US1/US2).

    Separate from `eval` (IR): set-based semantics + a distinct baseline (`graph_baseline.toml`).
    Sub-subcommands `run`/`add-case`/`amend-case`/`validate-ref`, each registering its handler via
    `set_defaults`. `--relation` uses `choices` (usage error exit 2 outside the MVP set, REQ-005).
    The run is a deterministic VEHICLE (Principio XI): never an LLM.
    """
    p_ge = sub.add_parser(
        "graph-eval",
        help="set-based evaluation of code-graph navigation + non-regression gate",
        description="Measure precision/recall/F1 of graph navigation (who_calls/defines) against "
                    "the [[graph_case]] of eval/suite.toml and gate non-regression on mean_f1.",
    )
    gsub = p_ge.add_subparsers(dest="graph_eval_command", required=True, metavar="subcommand")

    p_run = gsub.add_parser(
        "run", help="evaluate the [[graph_case]] and report set metrics + non-regression verdict",
        description="Loads eval/suite.toml, navigates the code graph, computes precision/recall/F1 "
                    "and gates mean_f1 against eval/graph_baseline.toml (exit 1 on regression).",
    )
    p_run.add_argument("--record-baseline", action="store_true",
                       help="record/update eval/graph_baseline.toml with the current metrics")
    p_run.add_argument("--exact", action="store_true",
                       help="enable the exact-set gate: a case with got != expected fails the run")
    p_run.add_argument("--json", action="store_true", help="report as a JSON object")
    p_run.add_argument("--corpus", default=None,
                       help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_run)
    p_run.set_defaults(handler=_cmd_graph_eval_run)

    p_add = gsub.add_parser(
        "add-case", help="add a graph-navigation case (validated against the graph)",
        description="Persists a (relation, target → expected refs) [[graph_case]] in eval/suite. "
                    "A ref the graph does not confirm warns and requires --confirm.",
    )
    _add_graph_case_args(p_add)
    p_add.set_defaults(handler=_cmd_graph_eval_add)

    p_amend = gsub.add_parser(
        "amend-case", help="re-author the expected refs of an existing graph-navigation case",
        description="Updates the expected set of the [[graph_case]] identified by (relation, "
                    "target). Same write-time validation as add-case; absent case → exit 1.",
    )
    _add_graph_case_args(p_amend)
    p_amend.set_defaults(handler=_cmd_graph_eval_amend)

    p_vr = gsub.add_parser(
        "validate-ref", help="navigate (relation, target) and check ref(s) (primitive for skills)",
        description="Reports which of the given refs are confirmed by the graph. Exit 0 always "
                    "(it is a check, not a gate). Vehicle for the eval-authoring skills.",
    )
    p_vr.add_argument("--relation", required=True, choices=["who_calls", "defines"],
                      help="navigation relation (MVP: who_calls | defines)")
    p_vr.add_argument("--target", required=True, help="the target symbol name")
    p_vr.add_argument("refs", nargs="*", help="zero or more refs (path#qualname) to check")
    p_vr.add_argument("--json", action="store_true", help="report as a JSON object")
    p_vr.add_argument("--corpus", default=None,
                      help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_vr)
    p_vr.set_defaults(handler=_cmd_graph_eval_validate_ref)


def _add_graph_case_args(p: argparse.ArgumentParser) -> None:
    """Shared args for `graph-eval add-case` / `amend-case`."""
    p.add_argument("--relation", required=True, choices=["who_calls", "defines"],
                   help="navigation relation (MVP: who_calls | defines)")
    p.add_argument("--target", required=True, help="the target symbol name")
    p.add_argument("--expected", required=True,
                   help="comma-separated expected ref(s) (path#qualname); empty for «none»")
    p.add_argument("--confirm", action="store_true",
                   help="write even if a ref is not confirmed by the graph")
    p.add_argument("--json", action="store_true", help="report as a JSON object")
    p.add_argument("--corpus", default=None,
                   help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p)


def _graph_baseline_path(settings: Settings) -> Path:
    return settings.eval_dir / "graph_baseline.toml"


def _parse_ks(raw: str | None) -> tuple[int, ...]:
    """Parse the `-k` flag (`1,3,5,10`) → tuple of ints; default when absent (REQ-033)."""
    if not raw:
        return (1, 3, 5, 10)
    try:
        return tuple(int(p.strip()) for p in raw.split(",") if p.strip())
    except ValueError as exc:
        raise ConfigError(f"invalid -k value {raw!r}: expected comma-separated integers") from exc


def _suite_path(settings: Settings) -> Path:
    return settings.eval_dir / "suite.toml"


def _baseline_path(settings: Settings) -> Path:
    return settings.eval_dir / "baseline.toml"


def _add_memory_parser(sub) -> None:
    """`memory` command group with `archive`/`search` sub-subcommands (035, D1).

    A second `add_subparsers` level nested in `memory`; each sub-subcommand registers its own
    handler via `set_defaults`, so `main()`'s dispatch stays unchanged. `required=True` gives the
    usage error (exit 2) when `sertor-rag memory` is invoked without an action.
    """
    p_memory = sub.add_parser(
        "memory", help="local episodic memory: archive and search project conversations",
        description="Memory area (gated by SERTOR_MEMORY): archive transcripts and search them.",
    )
    msub = p_memory.add_subparsers(dest="memory_command", required=True, metavar="subcommand")

    p_archive = msub.add_parser(
        "archive", help="archive every discoverable session (idempotent)",
        description="Delegates to MemoryArchiveService.archive_all(); reports archived/skipped/"
                    "errors. Idempotent: a re-run skips already-archived sessions.",
    )
    p_archive.add_argument("--json", action="store_true", help="report as a JSON object")
    p_archive.add_argument("--corpus", default=None,
                           help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_archive)
    p_archive.set_defaults(handler=_cmd_memory_archive)

    p_msearch = msub.add_parser(
        "search", help="full-text search over the archived conversations",
        description="Delegates to EpisodicSearch.search(); cites session/role/turn/snippet/score. "
                    "Read-only.",
    )
    p_msearch.add_argument("query", help="FTS5 query text (empty → honest empty state)")
    p_msearch.add_argument("--since", type=_parse_time, default=None,
                           help="lower time bound on captured_at (ISO-8601 or epoch)")
    p_msearch.add_argument("--until", type=_parse_time, default=None,
                           help="upper time bound on captured_at (ISO-8601 or epoch)")
    p_msearch.add_argument("--order", choices=["relevance", "recency"], default="relevance",
                           help="result ordering (default: relevance)")
    p_msearch.add_argument("-k", "--limit", type=int, default=None, dest="k",
                           help="max number of results (default: Settings.episodic_limit)")
    p_msearch.add_argument("--json", action="store_true", help="results as a JSON array")
    p_msearch.add_argument("--corpus", default=None,
                           help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_msearch)
    p_msearch.set_defaults(handler=_cmd_memory_search)

    p_show = msub.add_parser(
        "show", help="show the full transcript of an archived session",
        description="Delegates to MemoryArchive.get(); prints every turn (role/ts/text), no "
                    "truncation. not-found → exit 1; existing-but-empty → exit 0. Read-only.",
    )
    p_show.add_argument("session_key", help="opaque session key (filename stem)")
    p_show.add_argument("--json", action="store_true", help="transcript as a JSON object")
    p_show.add_argument("--corpus", default=None,
                        help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_show)
    p_show.set_defaults(handler=_cmd_memory_show)

    p_list = msub.add_parser(
        "list", help="list the most recent archived sessions (recency-first)",
        description="Delegates to MemoryArchive.list_recent(); lists session/captured_at/turns. "
                    "Empty archive → honest empty state, exit 0. Read-only.",
    )
    p_list.add_argument("-k", "--limit", type=int, default=None, dest="k",
                        help="max number of sessions (default: Settings.memory_list_limit)")
    p_list.add_argument("--json", action="store_true", help="results as a JSON array")
    p_list.add_argument("--corpus", default=None,
                        help="corpus namespace; overrides SERTOR_CORPUS")
    _add_logging_flags(p_list)
    p_list.set_defaults(handler=_cmd_memory_list)


def _add_logging_flags(p: argparse.ArgumentParser) -> None:
    """Observability levers shared by both subcommands (US3, FR-017..019)."""
    p.add_argument("-v", "--verbose", action="store_true",
                   help="enable structured INFO logs on stderr")
    p.add_argument("--log-json", action="store_true",
                   help="emit log records as JSON (one object per event)")
    p.add_argument("--log-config", default=None,
                   help="dictConfig file (JSON/YAML) to configure the logging appenders")


def _resolve_settings(args) -> Settings:
    """Loads the centralised config and applies the `--corpus` override if present (D7)."""
    settings = Settings.load()
    if args.corpus:
        settings = dataclasses.replace(settings, corpus=args.corpus)
    return settings


def _check_backend(settings: Settings) -> None:
    """Static backend validation before contacting any service (FR-015, D3)."""
    missing = settings.validate_backend()
    if missing:
        raise ConfigError(
            f"incomplete backend configuration: missing {', '.join(missing)}"
        )


def _require_archiver(settings: Settings):
    """Consume the privacy gate: turn the factory's `None` into an actionable error (035, D2).

    The gate lives in composition (`build_memory_archiver` → `None` if memory is off, Principio I);
    the command does not duplicate it — it *consumes* the `None` and raises an explicit
    `ConfigError` (exit 1, Principio IV) that names `SERTOR_MEMORY=true`.
    """
    archiver = build_memory_archiver(settings)
    if archiver is None:
        raise ConfigError(
            "memory is disabled; set SERTOR_MEMORY=true to enable archiving",
            key="SERTOR_MEMORY",
        )
    return archiver


def _require_episodic_search(settings: Settings):
    """Same gate as `_require_archiver`, for `build_episodic_search` (035, D2)."""
    search = build_episodic_search(settings)
    if search is None:
        raise ConfigError(
            "memory is disabled; set SERTOR_MEMORY=true to enable archiving",
            key="SERTOR_MEMORY",
        )
    return search


def _require_memory_reader(settings: Settings):
    """Same gate as `_require_archiver`, for `build_memory_reader` (036, D2)."""
    reader = build_memory_reader(settings)
    if reader is None:
        raise ConfigError(
            "memory is disabled; set SERTOR_MEMORY=true to enable archiving",
            key="SERTOR_MEMORY",
        )
    return reader


def _parse_time(value: str) -> float:
    """Parse `--since`/`--until`: ISO-8601 (`YYYY-MM-DD[THH:MM:SS]`) or epoch float → epoch UTC.

    Naive ISO timestamps are interpreted as UTC (the archive stores epoch-UTC `captured_at`). An
    unparseable value raises `ValueError`, which argparse turns into a usage error (exit 2).
    """
    try:
        return float(value)
    except ValueError:
        pass
    text = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = time.strptime(text, fmt)
        except ValueError:
            continue
        return calendar.timegm(parsed)
    raise ValueError(
        f"invalid time '{value}': expected ISO-8601 (YYYY-MM-DD[THH:MM:SS]) or an epoch number"
    )


def _cmd_index(args) -> None:
    """Handler for `index`: validates path/backend, builds the indexer and prints the report."""
    setup_logging(args)
    path = Path(args.path)
    # CLI pre-flight check (does not duplicate core logic, FR-006/edge case).
    if not path.exists() or not path.is_dir():
        raise IngestionError(
            f"invalid path or not a directory: {args.path}", path=str(args.path)
        )
    settings = _resolve_settings(args)
    _check_backend(settings)
    enable_observability(settings)  # persist events if SERTOR_OBSERVABILITY=true (no-op otherwise)
    # Incremental by default (046, FR-002); --full forces a full rebuild (rebuild=True, FR-010).
    report = build_indexer(settings).index(path, rebuild=args.full)
    print(output.format_index_report(report, json=args.json))


def _cmd_search(args) -> None:
    """Handler for `search`: strict path for every `--type`, then routes and formats (US2)."""
    setup_logging(args)
    if not args.query.strip():
        raise ConfigError("empty or whitespace-only query")
    settings = _resolve_settings(args)
    _check_backend(settings)
    enable_observability(settings)  # persist events if SERTOR_OBSERVABILITY=true (no-op otherwise)
    # Strict path for ANY --type: missing index → IndexNotFoundError (FR-012, D6).
    engine = build_baseline_engine(settings)
    engine.ensure_index()
    if args.type == "both":
        # search_combined inherits the fan-out over extra corpora (fix F13).
        results = build_facade(settings).search_combined(args.query, k=args.k)
    else:
        facade = build_facade(settings)
        results = (
            facade.search_code(args.query, k=args.k)
            if args.type == "code"
            else facade.search_docs(args.query, k=args.k)
        )
    print(output.format_search_results(results, settings, json=args.json, full=args.full))


def _cmd_observe(args) -> None:
    """Handler for `observe`: launches the live TUI panel (thin — delegates to composition)."""
    from sertor_core.composition import run_observability_panel

    run_observability_panel(_resolve_settings(args))


def _cmd_memory_archive(args) -> None:
    """Handler for `memory archive`: gate → archive_all() → report (035, US1)."""
    setup_logging(args)
    settings = _resolve_settings(args)
    enable_observability(settings)  # persist events if SERTOR_OBSERVABILITY=true (no-op otherwise)
    archiver = _require_archiver(settings)
    report = archiver.archive_all()
    print(output.format_archive_report(report, json=args.json))


def _cmd_memory_search(args) -> None:
    """Handler for `memory search`: gate → EpisodicSearch.search() → results (035, US2).

    `since > until` raises `InvalidTimeWindowError` from the core (a `SertorError` → exit 1 via
    `main()`); the command does NOT re-validate the window (Principio I, no duplication).
    """
    setup_logging(args)
    settings = _resolve_settings(args)
    enable_observability(settings)  # persist events if SERTOR_OBSERVABILITY=true (no-op otherwise)
    search = _require_episodic_search(settings)
    query = SearchQuery(
        text=args.query,
        since=args.since,
        until=args.until,
        order=args.order,
        limit=args.k if args.k is not None else settings.episodic_limit,
        snippet_tokens=settings.episodic_snippet_tokens,
    )
    results = search.search(query)
    print(output.format_memory_results(results, settings, json=args.json))


def _cmd_memory_show(args) -> None:
    """Handler for `memory show`: gate → get() → full transcript (036, US1, FR-001/008/009).

    Three distinct outcomes (research D4): `get` → `None` = session absent → `SessionNotFoundError`
    (exit 1); `ArchivedSession` with no turns = existing-but-empty → explicit empty state (exit 0);
    `ArchivedSession` with N turns = full transcript (exit 0). Trade-off F3: a `None` can also mean
    "store unreadable" (same return value as "absent"); in that case the message «session not
    found … use `memory list`» is technically imprecise, but the cause is distinguished for
    diagnostics by the `memory_archive_unavailable` warning that `get` logs on a store failure
    (Principio IX) — and `memory list` is exactly what the user should try next to verify. Keeping
    the two collapsed avoids changing `get`'s contract (additive constraint, FR-012).
    """
    setup_logging(args)
    settings = _resolve_settings(args)
    enable_observability(settings)  # persist events if SERTOR_OBSERVABILITY=true (no-op otherwise)
    reader = _require_memory_reader(settings)
    session = reader.get(args.session_key)
    # Observability: counts + opaque key only, never conversational content (RNF-2, D8).
    log_event(
        logging.INFO, "memory_show",
        session_key=args.session_key,
        turn_count=len(session.turns) if session is not None else 0,
        found=session is not None,
    )
    if session is None:
        raise SessionNotFoundError(args.session_key)
    print(output.format_session_transcript(session, json=args.json))


def _cmd_memory_list(args) -> None:
    """Handler for `memory list`: gate → list_recent() → recent sessions (036, US2, FR-002/008)."""
    setup_logging(args)
    settings = _resolve_settings(args)
    enable_observability(settings)  # persist events if SERTOR_OBSERVABILITY=true (no-op otherwise)
    reader = _require_memory_reader(settings)
    limit = args.k if args.k is not None else settings.memory_list_limit
    summaries = reader.list_recent(limit)
    # Observability: counts only, never content (RNF-2, D8).
    log_event(logging.INFO, "memory_list", count=len(summaries), limit=limit)
    print(output.format_session_list(summaries, json=args.json))


def _cmd_eval_run(args) -> None:
    """Handler for `eval run`: measure + non-regression gate + optional compare (065, US1/US4).

    Flow (contract cli-eval.md §run): load suite (absent → SuiteNotFoundError, exit 1) → build the
    engine via `build_eval_runner` (vehicle, Principio XI) → `run_evaluation`. With `--compare`,
    evaluate each label side-by-side. With a baseline present (and not `--record-baseline`), compare
    and gate: a regression → `RegressionDetected` (exit 1). `--record-baseline` records the current
    metrics (explicit acceptance, REQ-044). One `eval` event per evaluated config (metrics-only).
    """
    setup_logging(args)
    settings = _resolve_settings(args)
    _check_backend(settings)
    enable_observability(settings)
    ks = _parse_ks(args.k)
    suite = load_suite(_suite_path(settings))  # absent → SuiteNotFoundError (exit 1, actionable)
    runner = build_eval_runner(settings)

    if args.compare:
        labels = [s.strip() for s in args.compare.split(",") if s.strip()]
        reports = []
        for label in labels:
            report, _kinds = runner.run_labelled(label, suite, ks)
            emit_eval_event(report, None)
            reports.append((label, report))
        print(output.format_comparison(tuple(reports), json=args.json))
        return

    report, kinds = runner.run_by_kind(suite, ks) if args.by_kind else runner.run(suite, ks)
    baseline_path = _baseline_path(settings)
    if args.record_baseline:
        baseline = Baseline(
            hit_rate=report.hit_rate,
            mrr=report.mrr,
            queries=report.queries,
            provider=report.provider,
            recorded_at=now_iso_utc(),
        )
        write_baseline(baseline_path, baseline)
        emit_eval_event(report, None)
        print(output.format_eval_report(report, kinds, None, json=args.json))
        return

    baseline = load_baseline(baseline_path)
    verdict = compare_to_baseline(report, baseline, settings.eval_tolerance)
    emit_eval_event(report, verdict)
    print(output.format_eval_report(report, kinds, verdict, json=args.json))
    if verdict.verdict == "regressed":
        raise RegressionDetected(verdict)


def _cmd_eval_add(args) -> None:
    """Handler for `eval add-case`: validate path(s) against the index, then persist (065, US1).

    A path absent from the index → warning + requires `--confirm` (or, on a TTY, an interactive
    confirmation) before writing; otherwise exit 1 azionabile, nothing written. The index being
    unavailable (manifest absent) is the same path: persist only with `--confirm` (honest degrado).
    """
    setup_logging(args)
    settings = _resolve_settings(args)
    enable_observability(settings)
    if not args.query.strip():
        raise ConfigError("empty or whitespace-only query")
    expected = tuple(p.strip() for p in args.expected.split(",") if p.strip())
    if not expected:
        raise ConfigError("no expected path provided")
    pv = validate_paths(expected, build_indexed_docs(settings))
    blocking = bool(pv.missing) or not pv.index_available
    if blocking and not args.confirm and not _confirm_via_tty(pv):
        # Print the warning to stderr; nothing is written (no partial state, REQ-012).
        print(output.format_path_validation(pv, json=False), file=sys.stderr)
        raise ConfigError(
            "expected path(s) not verified against the index; "
            "re-run with --confirm to add the case anyway"
        )
    if blocking:
        print(output.format_path_validation(pv, json=False), file=sys.stderr)
    add_case(_suite_path(settings), EvalCase(query=args.query, expected=expected, kind=args.kind))
    print(output.format_path_validation(pv, json=args.json))


def _confirm_via_tty(pv) -> bool:
    """Interactive confirmation when both stdin and stdout are a TTY; else False (CI-safe)."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    print(output.format_path_validation(pv, json=False), file=sys.stderr)
    answer = input("add the case anyway? [y/N] ").strip().lower()
    return answer in ("y", "yes")


def _cmd_eval_validate(args) -> None:
    """Handler for `eval validate-path`: report path↔index validation (065, primitive for skills).

    Exit 0 always (it is a verification, not a gate): `missing` is information, not an error. It is
    the deterministic vehicle the eval-authoring skills invoke (Principio XI).
    """
    setup_logging(args)
    settings = _resolve_settings(args)
    enable_observability(settings)
    pv = validate_paths(tuple(args.paths), build_indexed_docs(settings))
    print(output.format_path_validation(pv, json=args.json))


def _cmd_graph_eval_run(args) -> None:
    """Handler for `graph-eval run`: set-based navigation eval + non-regression gate (066, US1/US2).

    Flow (contract cli-graph-eval.md §run): load suite (absent → SuiteNotFoundError, exit 1); no
    `[[graph_case]]` → actionable message + empty honest report (exit 0). Builds the graph via
    `build_graph_eval_runner` (vehicle, Principio XI); graph not built → GraphNotFoundError.
    With `--exact` a non-exact case → GraphRegressionDetected (exit 1). With a baseline present (and
    not `--record-baseline`), gate mean_f1 → GraphRegressionDetected on regression. `--record-
    baseline` records the current metrics (explicit acceptance, NEVER touches `expected`, DA-c).
    """
    setup_logging(args)
    settings = _resolve_settings(args)
    _check_backend(settings)
    enable_observability(settings)
    suite = load_suite(_suite_path(settings))  # absent → SuiteNotFoundError (exit 1, actionable)
    exact_gate = args.exact or settings.graph_eval_exact
    runner = build_graph_eval_runner(settings, exact_gate=exact_gate)
    report, verdict = runner.run(suite)

    if report.cases_count == 0:
        # No [[graph_case]] yet: honest empty report, exit 0 (not a fasullo gate on zero cases).
        print(output.format_graph_eval_report(report, verdict, json=args.json))
        print(
            "no [[graph_case]] in the suite — create one with `sertor-rag graph-eval add-case`",
            file=sys.stderr,
        )
        return

    print(output.format_graph_eval_report(report, verdict, json=args.json))

    if args.record_baseline:
        baseline = GraphBaseline(
            mean_f1=report.mean_f1,
            mean_recall=report.mean_recall,
            mean_precision=report.mean_precision,
            cases=report.cases_count,
            recorded_at=graph_now_iso_utc(),
        )
        write_graph_baseline(_graph_baseline_path(settings), baseline)
        return

    if exact_gate and any(not c.metric.exact for c in report.cases):
        raise GraphRegressionDetected(verdict)
    if verdict.verdict == "regressed":
        raise GraphRegressionDetected(verdict)


def _cmd_graph_eval_add(args) -> None:
    """Handler for `graph-eval add-case`: validate refs against the graph, then persist (066, US1).

    A ref the graph does not confirm → warning + requires `--confirm` (or, on a TTY, an interactive
    confirmation) before writing; otherwise exit 1 azionabile, nothing written. The graph being
    unavailable is the same path: persist only with `--confirm` (honest degrado).
    """
    setup_logging(args)
    settings = _resolve_settings(args)
    enable_observability(settings)
    expected = tuple(r.strip() for r in args.expected.split(",") if r.strip())
    rv = validate_refs(
        build_graph_eval_runner(settings).graph, args.relation, args.target, expected
    )
    _gate_graph_write(args, rv)  # raises ConfigError (exit 1) if blocked and not confirmed
    add_graph_case(
        _suite_path(settings),
        GraphCase(relation=args.relation, target=args.target, expected=expected),
    )
    print(output.format_ref_validation(rv, json=args.json))


def _cmd_graph_eval_amend(args) -> None:
    """Handler for `graph-eval amend-case`: re-author the expected refs of a case (066, DA-c).

    Same write-time validation as add-case. The case must exist (else GraphSuiteValidationError,
    exit 1, naming relation+target).
    """
    setup_logging(args)
    settings = _resolve_settings(args)
    enable_observability(settings)
    expected = tuple(r.strip() for r in args.expected.split(",") if r.strip())
    rv = validate_refs(
        build_graph_eval_runner(settings).graph, args.relation, args.target, expected
    )
    _gate_graph_write(args, rv)  # raises ConfigError (exit 1) if blocked and not confirmed
    amend_graph_case(_suite_path(settings), args.relation, args.target, expected)
    print(output.format_ref_validation(rv, json=args.json))


def _gate_graph_write(args, rv) -> None:
    """Shared write-gate for add/amend (066, REQ-042): raise ConfigError if blocked and unconfirmed.

    Blocks when a ref is unverifiable or the graph is unavailable. Without `--confirm` (nor a TTY
    confirmation) → warning on stderr + `ConfigError` (exit 1, nothing written, no partial state).
    With `--confirm` → prints the warning and returns (caller proceeds to write).
    """
    blocking = bool(rv.unverifiable) or not rv.graph_available
    if not blocking:
        return
    if not args.confirm and not _confirm_refs_via_tty(rv):
        print(output.format_ref_validation(rv, json=False), file=sys.stderr)
        raise ConfigError(
            "expected ref(s) not confirmed by the graph; "
            "re-run with --confirm to add the case anyway"
        )
    print(output.format_ref_validation(rv, json=False), file=sys.stderr)


def _confirm_refs_via_tty(rv) -> bool:
    """Interactive confirmation when both stdin and stdout are a TTY; else False (CI-safe)."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    print(output.format_ref_validation(rv, json=False), file=sys.stderr)
    answer = input("add the case anyway? [y/N] ").strip().lower()
    return answer in ("y", "yes")


def _cmd_graph_eval_validate_ref(args) -> None:
    """Handler for `graph-eval validate-ref`: report graph↔ref validation (066, skill primitive).

    Exit 0 always (a verification, not a gate): `unverifiable` is information, not an error. It is
    the deterministic vehicle the eval-authoring skill invokes (Principio XI).
    """
    setup_logging(args)
    settings = _resolve_settings(args)
    enable_observability(settings)
    rv = validate_refs(
        build_graph_eval_runner(settings).graph, args.relation, args.target, tuple(args.refs)
    )
    print(output.format_ref_validation(rv, json=args.json))


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point. Returns the exit code (0/1; argparse exits with 2)."""
    # Stable UTF-8 I/O on any console (Windows cp1252 cannot encode repo content).
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):  # stream not reconfigurable (e.g. redirection): ok
            pass

    args = _build_parser().parse_args(argv)
    try:
        args.handler(args)
    except SertorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
