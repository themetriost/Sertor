"""CLI backbone for the `sertor` command (contracts/cli-commands.md, D8).

Thin **layer** (Principio I): argparse parsing → installer functions → report formatting.
Reference pattern: `src/sertor_core/cli/__main__.py`. Exit code: `0` success · `1` domain error
(`SertorError`) · `2` usage error (argparse).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from sertor_core.domain.errors import ConfigError, IngestionError, SertorError
from sertor_install_kit.artifacts import ArtifactOutcome, LifecycleOp, Outcome
from sertor_install_kit.assistant import AssistantId
from sertor_install_kit.errors import InstallerError
from sertor_install_kit.lifecycle import remove_path
from sertor_install_kit.observability import log_event
from sertor_install_kit.report import InstallReport
from sertor_installer.command_runner import SubprocessRunner
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_rag import (
    build_rag_plan,
    execute_rag_lifecycle,
    execute_rag_plan,
)
from sertor_installer.install_wiki import (
    build_install_plan,
    execute_plan,
    execute_wiki_lifecycle,
)
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions

# Capabilities `sertor` owns (governance lives in `sertor-flow`, pointer only).
_SERTOR_CAPABILITIES = ("wiki", "rag")


class UsageError(InstallerError):
    """Invalid flag combination → exit code 2 (argparse-style usage error, feature 048, FR-005)."""

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
        help="target assistant: claude (default) | copilot (VS Code) | copilot-cli",
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
        help="target assistant: claude (default) | copilot (VS Code) | copilot-cli",
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

    # --- feature 051: configure (guided wizard) ----------------------------------------------
    configure = sub.add_parser(
        "configure", help="guided configuration of .sertor/.env (provider/store credentials)"
    )
    configure.add_argument(
        "capability", nargs="?", default="rag", choices=["rag"],
        help="capability to configure (default: rag — the only one today)",
    )
    configure.add_argument("--target", default=".", help="host repo root (default: cwd)")
    configure.add_argument(
        "--backend", choices=["azure", "local"], default="azure",
        help="embeddings provider → RAG_BACKEND (default: azure)",
    )
    configure.add_argument(
        "--store", choices=["local", "azure"], default=None,
        help="vector store → SERTOR_STORE_BACKEND (default: = backend)",
    )
    configure.add_argument(
        "--set", action="append", default=None, metavar="KEY=VALUE", dest="set",
        help="explicit value for a field (repeatable); KEY must be a known field",
    )
    configure.add_argument(
        "--overwrite", action="store_true",
        help="allow overwriting values already present in .sertor/.env",
    )
    configure.add_argument(
        "--non-interactive", action="store_true",
        help="never prompt (flag-driven only), even with a TTY (CI-safe)",
    )
    configure.add_argument(
        "--check", action="store_true",
        help="opt-in live probe of the provider (via the sertor-rag vehicle); Should/deferred",
    )
    configure.add_argument("--json", action="store_true", help="emit the report as JSON")

    # --- feature 048: lifecycle verbs --------------------------------------------------------
    upgrade = sub.add_parser(
        "upgrade", help="upgrade installed capabilities (refresh assets, remove obsoletes)"
    )
    upgrade.add_argument(
        "capabilities", nargs="*", metavar="<capability>",
        help="wiki | rag | governance (0..N; empty → all installed)",
    )
    _add_lifecycle_flags(upgrade)

    uninstall = sub.add_parser(
        "uninstall", help="uninstall capabilities (remove runtime, assets, shared edits)"
    )
    uninstall.add_argument(
        "capabilities", nargs="*", metavar="<capability>",
        help="wiki | rag | governance (0..N; empty → all installed)",
    )
    _add_lifecycle_flags(uninstall)
    uninstall.add_argument(
        "--purge-wiki", action="store_true",
        help="also remove the wiki/ directory (opt-in, needs --yes or a TTY confirmation)",
    )
    uninstall.add_argument(
        "--yes", action="store_true",
        help="non-interactive consent for --purge-wiki (CI-safe)",
    )

    return parser


def _add_lifecycle_flags(p: argparse.ArgumentParser) -> None:
    """Common flags for `upgrade`/`uninstall` (FR-001/002/003)."""
    p.add_argument("--target", default=".", help="host repo root (default: cwd)")
    p.add_argument(
        "--assistant", default="claude",
        help="target assistant: claude (default) | copilot | copilot-cli",
    )
    p.add_argument("--backend", choices=["azure", "local"], default="azure",
                   help="embeddings backend for the reconstructed rag plan (default: azure)")
    p.add_argument("--mcp-scope", choices=["project", "local"], default="project",
                   help="MCP scope used when reconstructing the rag plan (default: project)")
    p.add_argument("--no-deps", action="store_true",
                   help="do not touch the isolated Python deps (skip the uv bootstrap step)")
    p.add_argument("--dry-run", action="store_true",
                   help="project the operation without touching the filesystem")
    p.add_argument("--json", action="store_true", help="emit the report as JSON")


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


def _parse_set_pairs(raw: list[str] | None) -> dict[str, str]:
    """Parse `--set KEY=VALUE` pairs. Missing `=` → UsageError (exit 2, contracts §7)."""
    pairs: dict[str, str] = {}
    for item in raw or []:
        if "=" not in item:
            raise UsageError(f"--set expects KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise UsageError(f"--set expects a non-empty KEY, got: {item}")
        pairs[key] = value.strip()
    return pairs


def _cmd_configure(args) -> int:
    """Handler for `configure`: validates the target, runs the wizard, prints the report.

    `interactive` requires BOTH stdin and stdout to be a TTY and `--non-interactive` absent
    (NFR-05): otherwise the flow is strictly flag-driven (never a hidden prompt, CI-safe).
    """
    from sertor_installer.configure import configure_rag

    target_root = _validate_target(args)
    explicit_values = _parse_set_pairs(args.set)
    interactive = (
        sys.stdin.isatty() and sys.stdout.isatty() and not args.non_interactive
    )
    report = configure_rag(
        target_root=target_root,
        backend=args.backend,
        store=args.store,  # None → resolved from .env/template (default = local for azure)
        explicit_values=explicit_values,
        overwrite=args.overwrite,
        interactive=interactive,
        check=args.check,
        runner=SubprocessRunner(),
    )
    print(report.render_json() if args.json else report.render_human())
    return report.exit_code()


def _validate_target(args) -> Path:
    target_root = Path(args.target).resolve()
    if not target_root.exists():
        raise ConfigError("target does not exist", key=str(target_root))
    if not target_root.is_dir():
        raise IngestionError("target is not a directory", path=str(target_root))
    return target_root


def _lifecycle_rag(target_root: Path, args, op: LifecycleOp) -> InstallReport:
    """Builds the rag plan and runs the lifecycle verb (feature 048)."""
    assistant = AssistantId.from_str(args.assistant)
    opts = RagInstallOptions(
        target_root=target_root, backend=args.backend, mcp_scope=args.mcp_scope,
        with_deps=not getattr(args, "no_deps", False),
    )
    profile = RagHostProfile.from_options(opts)
    plan = build_rag_plan(
        profile, with_deps=opts.with_deps, mcp_scope=args.mcp_scope, assistant=assistant
    )
    return execute_rag_lifecycle(
        plan, profile, SubprocessRunner(), op, assistant, dry_run=args.dry_run
    )


def _lifecycle_wiki(target_root: Path, args, op: LifecycleOp) -> InstallReport:
    """Builds the wiki plan and runs the lifecycle verb (feature 048)."""
    assistant = AssistantId.from_str(args.assistant)
    profile = build_host_profile(target_root)
    plan = build_install_plan(assistant)
    report = execute_wiki_lifecycle(plan, profile, op, assistant, dry_run=args.dry_run)
    # `--purge-wiki` gate (uninstall only, FR-027/028, decision D4) lives in the CLI.
    if op is LifecycleOp.UNINSTALL and getattr(args, "purge_wiki", False):
        _maybe_purge_wiki(target_root, args, report)
    return report


def _maybe_purge_wiki(target_root: Path, args, report: InstallReport) -> None:
    """Applies the deterministic `--purge-wiki` rules (decision D4). Mutates `report` in place."""
    wiki_dir = target_root / "wiki"
    n_pages, n_bytes = _wiki_size(wiki_dir)
    info = f"{n_pages} pages, ~{n_bytes} bytes"
    if args.dry_run:
        # `--purge-wiki --dry-run` is a usage error (handled earlier); reaching here is a no-op.
        return  # pragma: no cover
    if args.yes:
        outcome = remove_path(wiki_dir)
        report.add(ArtifactOutcome("wiki", outcome, f"purged ({info})"))
        return
    if sys.stdin.isatty():
        print(f"About to remove wiki/ ({info}). Continue? [y/N] ", end="", flush=True)
        answer = sys.stdin.readline().strip().lower()
        if answer in ("y", "yes"):
            outcome = remove_path(wiki_dir)
            report.add(ArtifactOutcome("wiki", outcome, f"purged ({info})"))
        else:
            report.add(ArtifactOutcome("wiki", Outcome.SKIPPED, "purge declined"))
        return
    # No TTY and no --yes: never destroy (CI-safe default).
    report.add(
        ArtifactOutcome(
            "wiki", Outcome.SKIPPED,
            f"wiki preserved ({info}); pass --yes to confirm removal non-interactively",
        )
    )


def _wiki_size(wiki_dir: Path) -> tuple[int, int]:
    """Counts pages (*.md) and total bytes under `wiki/` via stdlib (no `sertor_core`)."""
    if not wiki_dir.exists():
        return 0, 0
    pages = 0
    total = 0
    for path in wiki_dir.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
            if path.suffix == ".md":
                pages += 1
    return pages, total


def _run_lifecycle(args, op: LifecycleOp) -> int:
    """Shared `upgrade`/`uninstall` handler (per-capability + aggregate, feature 048)."""
    target_root = _validate_target(args)
    capabilities = args.capabilities or list(_SERTOR_CAPABILITIES) + ["governance"]

    purge = getattr(args, "purge_wiki", False)
    if purge:
        if args.dry_run:
            raise UsageError("--purge-wiki cannot be combined with --dry-run")
        if args.capabilities and "wiki" not in args.capabilities:
            raise UsageError("--purge-wiki is valid only for the `wiki` capability (or aggregate)")

    reports: list[InstallReport] = []
    governance_hint = False
    for cap in capabilities:
        if cap == "rag":
            reports.append(_lifecycle_rag(target_root, args, op))
        elif cap == "wiki":
            reports.append(_lifecycle_wiki(target_root, args, op))
        elif cap == "governance":
            governance_hint = True
        else:
            raise UsageError(f"unknown capability: {cap}")

    report = _aggregate(reports, target_root, args, op) if len(reports) != 1 else reports[0]
    _emit_lifecycle_event(op, report, args)
    out = report.render_json() if args.json else report.render_human()
    print(out)
    if governance_hint and not args.json:
        print(
            f"\nnote: governance/SDLC is managed by `sertor-flow {op.value}` "
            "(separate package, not bundled with `sertor`)."
        )
    return report.exit_code()


def _aggregate(
    reports: list[InstallReport], target_root: Path, args, op: LifecycleOp
) -> InstallReport:
    """Merges per-capability reports into one aggregate report (US8/FR-032)."""
    agg = InstallReport(
        target=str(target_root), capability="all",
        assistant=getattr(args, "assistant", None), op=op,
    )
    for r in reports:
        for o in r.outcomes:
            agg.add(o)
    return agg


def _emit_lifecycle_event(op: LifecycleOp, report: InstallReport, args) -> None:
    """Observability (FR-007): one event per operation, no secrets in the fields."""
    log_event(
        logging.INFO, op.value, capability=report.capability,
        assistant=getattr(args, "assistant", None),
        updated=report.updated, removed=report.removed,
        skipped=report.skipped, errors=report.errors,
    )


def _dispatch(args) -> int:
    if args.command == "install":
        if args.capability == "wiki":
            return _cmd_install_wiki(args)
        if args.capability == "rag":
            return _cmd_install_rag(args)
        # governance is not a `sertor` capability: it lives in `sertor-flow` (D9). Point there.
        raise GovernanceElsewhereError()
    if args.command == "configure":
        return _cmd_configure(args)
    if args.command == "upgrade":
        return _run_lifecycle(args, LifecycleOp.UPGRADE)
    if args.command == "uninstall":
        return _run_lifecycle(args, LifecycleOp.UNINSTALL)
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
    except UsageError as exc:
        # Invalid flag combination (e.g. --purge-wiki --dry-run) → usage error, exit 2 (FR-005).
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (SertorError, InstallerError) as exc:
        # `InstallerError` covers the kit's errors (e.g. an invalid `--assistant`), so an actionable
        # message is printed (exit 1) instead of a traceback (feature 044, Principio IV).
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
