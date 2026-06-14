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
import sys
import time
from pathlib import Path

from sertor_core.cli import output
from sertor_core.cli.logging_setup import setup_logging
from sertor_core.composition import (
    build_baseline_engine,
    build_episodic_search,
    build_facade,
    build_indexer,
    build_memory_archiver,
    enable_observability,
)
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError, IngestionError, SertorError
from sertor_core.services.episodic_search import SearchQuery


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sertor-rag",
        description="RAG execution CLI: index a repository and query it from the terminal.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    p_index = sub.add_parser(
        "index", help="index a repository into a vector collection (full rebuild)",
        description="Builds the repository's vector index and reports the counts.",
    )
    p_index.add_argument("path", help="root of the repository to index")
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

    return parser


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
    report = build_indexer(settings).index(path, rebuild=True)
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
