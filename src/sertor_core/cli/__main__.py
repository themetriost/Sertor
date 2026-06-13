"""RAG execution CLI `sertor-rag` (FEAT-011, contracts/cli-commands.md).

`sertor-rag index <path>` indexes a repository; `sertor-rag search <query>` queries the index.
Equivalent: `python -m sertor_core.cli`. **Thin** layer (Principio I): parsing → core composition
root → formatting. No retrieval logic here. Exit codes: `0` success · `1` domain error
(`SertorError`, message on stderr) · `2` usage error (argparse). Reference pattern:
`sertor_core/wiki_tools/__main__.py`.
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

from sertor_core.cli import output
from sertor_core.cli.logging_setup import setup_logging
from sertor_core.composition import (
    build_baseline_engine,
    build_facade,
    build_indexer,
)
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError, IngestionError, SertorError


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

    return parser


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
    report = build_indexer(settings).index(path, rebuild=True)
    print(output.format_index_report(report, json=args.json))


def _cmd_search(args) -> None:
    """Handler for `search`: strict path for every `--type`, then routes and formats (US2)."""
    setup_logging(args)
    if not args.query.strip():
        raise ConfigError("empty or whitespace-only query")
    settings = _resolve_settings(args)
    _check_backend(settings)
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
