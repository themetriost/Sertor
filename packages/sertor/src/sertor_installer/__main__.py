"""CLI backbone for the `sertor` command (contracts/cli-commands.md, D8).

Thin **layer** (Principio I): argparse parsing → installer functions → report formatting.
Reference pattern: `src/sertor_core/cli/__main__.py`. Exit code: `0` success · `1` domain error
(`SertorError`) · `2` usage error (argparse).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sertor_core.domain.errors import ConfigError, IngestionError, SertorError
from sertor_install_kit.assistant import AssistantId
from sertor_install_kit.errors import InstallerError
from sertor_installer.command_runner import SubprocessRunner
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_rag import build_rag_plan, execute_rag_plan
from sertor_installer.install_wiki import build_install_plan, execute_plan
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions

# The governance/SDLC method ships as the SEPARATE package `sertor-flow` (FEAT-005,
# feature 037): `sertor` has NO dependency on it (FR-023/SC-008). `sertor install
# governance` is a POINTER — it tells the user that governance lives in `sertor-flow`
# and how to install it, then exits with a dedicated code.
_GOVERNANCE_INSTALL_HINT = (
    'uvx --from "git+https://github.com/themetriost/Sertor'
    '#subdirectory=packages/sertor-flow" sertor-flow install'
)


class GovernanceElsewhereError(SertorError):
    """`install governance` points to the standalone `sertor-flow` package (F9, D9).

    Kept a subclass of `SertorError` so the `except SertorError` in `main()` still
    catches it and exits with code 1 — `sertor` does NOT import `sertor-flow`.
    """

    def __init__(self):
        super().__init__(
            "governance/SDLC is provided by the separate package `sertor-flow` "
            "(it does not ship with `sertor`). Install and run it with:\n"
            f"  {_GOVERNANCE_INSTALL_HINT}"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sertor",
        description="Installer for Sertor capabilities on a host repository.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    install = sub.add_parser(
        "install", help="install a capability on the host (wiki | rag | governance)"
    )
    install_sub = install.add_subparsers(
        dest="capability", required=True, metavar="<capability>"
    )

    wiki = install_sub.add_parser("wiki", help="install the wiki system (available)")
    wiki.add_argument("--target", default=".", help="host repo root (default: cwd)")
    wiki.add_argument(
        "--assistant", default="claude",
        help="target assistant: claude (default) | copilot",
    )
    wiki.add_argument(
        "--language", default="en", help="language of the generated wiki.config.toml (default: en)"
    )
    wiki.add_argument(
        "--source-dirs", default=None,
        help="CSV override of source folders (e.g. 'src,docs'); bypasses the heuristic",
    )
    wiki.add_argument("--json", action="store_true", help="emit the report as JSON")

    rag = install_sub.add_parser("rag", help="install the RAG capability (.sertor/ + .mcp.json)")
    rag.add_argument("--target", default=".", help="host repo root (default: cwd)")
    rag.add_argument(
        "--assistant", default="claude",
        help="target assistant: claude (default) | copilot",
    )
    rag.add_argument(
        "--backend", choices=["azure", "local"], default="azure",
        help="embeddings provider (default: azure)",
    )
    rag.add_argument(
        "--corpus", default=None,
        help="corpus name (SERTOR_CORPUS); default: sanitized name of the target dir",
    )
    rag.add_argument("--no-graph", action="store_true", help="exclude the `graph` extra (networkx)")
    rag.add_argument("--no-rerank", action="store_true", help="exclude the `rerank` extra")
    rag.add_argument(
        "--no-deps", action="store_true",
        help="config scaffold only; do not add dependencies (no uv)",
    )
    rag.add_argument(
        "--mcp-scope", choices=["project", "local"], default="project",
        help="where to register the MCP server: project (.mcp.json in host root, default) | "
             "local (in the client via `claude`, no file in the repo)",
    )
    rag.add_argument("--json", action="store_true", help="emit the report as JSON")

    install_sub.add_parser(
        "governance", help="governance/SDLC — provided by the separate `sertor-flow` package"
    )

    return parser


def _cmd_install_wiki(args) -> int:
    """Handler for `install wiki`: validates the target, builds the plan, executes, prints the
    report."""
    target_root = Path(args.target).resolve()
    if not target_root.exists():
        raise ConfigError("target does not exist", key=str(target_root))
    if not target_root.is_dir():
        raise IngestionError("target is not a directory", path=str(target_root))

    assistant = AssistantId.from_str(args.assistant)
    source_dirs = (
        [d for d in args.source_dirs.split(",")] if args.source_dirs else None
    )
    profile = build_host_profile(
        target_root, source_dirs_override=source_dirs, language=args.language
    )
    plan = build_install_plan(assistant)
    report = execute_plan(plan, profile, assistant)

    print(report.render_json() if args.json else report.render_human())
    return report.exit_code()


def _cmd_install_rag(args) -> int:
    """Handler for `install rag`: validates the target, executes the RAG plan, prints the report."""
    target_root = Path(args.target).resolve()
    if not target_root.exists():
        raise ConfigError("target does not exist", key=str(target_root))
    if not target_root.is_dir():
        raise IngestionError("target is not a directory", path=str(target_root))

    assistant = AssistantId.from_str(args.assistant)
    opts = RagInstallOptions(
        target_root=target_root,
        backend=args.backend,
        corpus=args.corpus,
        include_graph=not args.no_graph,
        include_rerank=not args.no_rerank,
        with_deps=not args.no_deps,
        json_report=args.json,
        mcp_scope=args.mcp_scope,
    )
    profile = RagHostProfile.from_options(opts)
    plan = build_rag_plan(
        profile, with_deps=opts.with_deps, mcp_scope=opts.mcp_scope, assistant=assistant
    )
    report = execute_rag_plan(plan, profile, SubprocessRunner(), assistant)

    print(report.render_json() if args.json else report.render_human())
    return report.exit_code()


def _dispatch(args) -> int:
    if args.command == "install":
        if args.capability == "wiki":
            return _cmd_install_wiki(args)
        if args.capability == "rag":
            return _cmd_install_rag(args)
        # governance is not a `sertor` capability: it lives in `sertor-flow` (D9). Point there.
        raise GovernanceElsewhereError()
    raise ConfigError(f"unsupported command: {args.command}")  # pragma: no cover


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `sertor` console-script. Returns the exit code (0/1/2)."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    args = _build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except (SertorError, InstallerError) as exc:
        # `InstallerError` covers the kit's errors (e.g. an invalid `--assistant`), so an actionable
        # message is printed (exit 1) instead of a traceback (feature 044, Principio IV).
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
