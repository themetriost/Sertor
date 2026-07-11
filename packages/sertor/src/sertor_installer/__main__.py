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
from sertor_install_kit.assistant import AssistantId, AssistantProfile, Surface
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
        help="target assistant: claude (default) | copilot-cli",
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
        help="target assistant: claude (default) | copilot-cli",
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
        help="embeddings profile → SERTOR_EMBED_PROVIDER (azure→azure, local→glove; def: azure)",
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

    return parser


def _add_lifecycle_flags(p: argparse.ArgumentParser) -> None:
    """Common flags for `upgrade`/`uninstall` (FR-001/002/003)."""
    p.add_argument("--target", default=".", help="host repo root (default: cwd)")
    p.add_argument(
        "--assistant", default=None,
        help="target assistant: claude | copilot-cli. Omit to auto-detect what is installed "
             "and operate on all of it (never strips a coexisting assistant).",
    )
    p.add_argument("--backend", choices=["azure", "local"], default="azure",
                   help="embeddings backend for the reconstructed rag plan (default: azure)")
    p.add_argument("--mcp-scope", choices=["project", "local"], default="project",
                   help="MCP scope used when reconstructing the rag plan (default: project)")
    p.add_argument("--no-deps", action="store_true",
                   help="do not touch the isolated Python deps (skip the uv bootstrap step)")
    p.add_argument("--dry-run", action="store_true",
                   help="project the operation without touching the filesystem")
    p.add_argument(
        "--yes", action="store_true",
        help="non-interactive consent for a destructive action (an assistant switch on upgrade, "
             "or --purge-wiki on uninstall); CI-safe",
    )
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


def _lifecycle_rag(
    target_root: Path, args, op: LifecycleOp, assistant: AssistantId,
    obsolete_assistants: tuple[AssistantId, ...] | None,
) -> InstallReport:
    """Builds the rag plan and runs the lifecycle verb for `assistant` (feature 048)."""
    opts = RagInstallOptions(
        target_root=target_root, backend=args.backend, mcp_scope=args.mcp_scope,
        with_deps=not getattr(args, "no_deps", False),
    )
    profile = RagHostProfile.from_options(opts)
    plan = build_rag_plan(
        profile, with_deps=opts.with_deps, mcp_scope=args.mcp_scope, assistant=assistant
    )
    return execute_rag_lifecycle(
        plan, profile, SubprocessRunner(), op, assistant, dry_run=args.dry_run,
        obsolete_assistants=obsolete_assistants,
    )


def _lifecycle_wiki(
    target_root: Path, args, op: LifecycleOp, assistant: AssistantId,
    obsolete_assistants: tuple[AssistantId, ...] | None,
) -> InstallReport:
    """Builds the wiki plan and runs the lifecycle verb for `assistant` (feature 048)."""
    profile = build_host_profile(target_root)
    plan = build_install_plan(assistant)
    report = execute_wiki_lifecycle(
        plan, profile, op, assistant, dry_run=args.dry_run,
        obsolete_assistants=obsolete_assistants,
    )
    # `--purge-wiki` gate (uninstall only, FR-027/028, decision D4) lives in the CLI.
    if op is LifecycleOp.UNINSTALL and getattr(args, "purge_wiki", False):
        _maybe_purge_wiki(target_root, args, report)
    return report


# --- A-01: install-state detection + assistant-switch consent (no silent cross-assistant strip) --

_RAG_MARKER = "SERTOR:RAG-USAGE"
_WIKI_MARKER = "SERTOR:WIKI-RITUAL"


def _instruction_marker_present(target_root: Path, assistant: AssistantId, marker: str) -> bool:
    """An assistant has a capability installed iff its instruction file carries the marker block.

    The authoritative signal is the marker written by a *real* install — NOT a stray owned file
    (a leftover standalone hook of an uninstalled assistant is cruft, not a coexisting install).
    """
    rel = AssistantProfile.for_assistant(assistant).target_for(Surface.INSTRUCTION_BLOCK).target_rel
    path = target_root / rel
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:  # pragma: no cover - unreadable file → treat as absent
        return False
    return f"<!-- {marker} START -->" in text


def _installed_assistants(capability: str, target_root: Path) -> list[AssistantId]:
    """Assistants with `capability` (`rag`/`wiki`) actually installed on the host."""
    marker = _RAG_MARKER if capability == "rag" else _WIKI_MARKER
    return [
        a for a in AssistantId
        if _instruction_marker_present(target_root, a, marker)
    ]


def _detect_installed_capabilities(target_root: Path) -> list[str]:
    """Capabilities `sertor` owns that are actually installed (no creep on a bare verb)."""
    return [c for c in _SERTOR_CAPABILITIES if _installed_assistants(c, target_root)]


def _require_switch_consent(
    args, op: LifecycleOp, requested: AssistantId, others: list[AssistantId]
) -> None:
    """Guard (A-01, decision b): an explicit `--assistant` upgrade that would REMOVE a coexisting
    assistant is an assistant switch — never silent. Consent via `--yes` or an interactive y/N;
    otherwise a usage error names the finding (CI-safe: never destroy without consent)."""
    names = ", ".join(a.value for a in others)
    if getattr(args, "yes", False):
        return
    if sys.stdin.isatty():
        print(
            f"`{op.value} --assistant {requested.value}` will REMOVE the coexisting install of: "
            f"{names} (assistant switch). Continue? [y/N] ",
            end="", flush=True,
        )
        if sys.stdin.readline().strip().lower() in ("y", "yes"):
            return
        raise UsageError("assistant switch declined")
    raise UsageError(
        f"{names} is also installed; `--assistant {requested.value}` would remove it "
        f"(assistant switch). Re-run with --yes to confirm the switch, or omit --assistant to "
        f"{op.value} every installed assistant."
    )


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
    """Shared `upgrade`/`uninstall` handler (per-capability + aggregate, feature 048).

    A-01: a *bare* verb (no capability / no `--assistant`) resolves to what is ACTUALLY installed —
    it never installs capabilities the host did not have (no creep) and never strips a coexisting
    assistant. An explicit `--assistant` that would remove another installed assistant is a switch,
    gated by consent (`_require_switch_consent`).
    """
    target_root = _validate_target(args)
    explicit_assistant = getattr(args, "assistant", None) is not None
    requested = AssistantId.from_str(args.assistant) if explicit_assistant else None

    purge = getattr(args, "purge_wiki", False)
    if purge:
        if args.dry_run:
            raise UsageError("--purge-wiki cannot be combined with --dry-run")
        if args.capabilities and "wiki" not in args.capabilities:
            raise UsageError("--purge-wiki is valid only for the `wiki` capability (or aggregate)")

    # Capability resolution: explicit list as-is; empty → only the installed ones (no creep).
    if args.capabilities:
        capabilities = list(args.capabilities)
    else:
        capabilities = _detect_installed_capabilities(target_root)
        if not capabilities:
            if not args.json:
                print(f"no Sertor capabilities detected under {target_root}; "
                      f"nothing to {op.value}.")
            else:
                empty = InstallReport(
                    target=str(target_root), capability="all", assistant=None, op=op
                )
                print(empty.render_json())
            return 0

    reports: list[InstallReport] = []
    governance_hint = False
    for cap in capabilities:
        if cap == "governance":
            governance_hint = True
            continue
        if cap not in _SERTOR_CAPABILITIES:
            raise UsageError(f"unknown capability: {cap}")
        installed = _installed_assistants(cap, target_root)
        if explicit_assistant:
            targets = [requested]
            if op is LifecycleOp.UPGRADE and (others := [a for a in installed if a != requested]):
                _require_switch_consent(args, op, requested, others)
            obsolete_assts = None  # explicit: all-assistant scope (consented switch / inverse)
        else:
            targets = installed or [AssistantId.CLAUDE]
            # Bare: sweep only cruft (owned paths of NOT-installed assistants); a real coexisting
            # install is in `targets` → never in the obsolete scope → preserved.
            obsolete_assts = tuple(a for a in AssistantId if a not in targets)
        for assistant in targets:
            if cap == "rag":
                reports.append(_lifecycle_rag(target_root, args, op, assistant, obsolete_assts))
            else:
                reports.append(_lifecycle_wiki(target_root, args, op, assistant, obsolete_assts))

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
    """Merges per-capability reports into one aggregate report (US8/FR-032).

    The aggregate assistant is derived from the reports actually produced (A-01): one distinct
    assistant → its value; several (a bare verb over a multi-assistant host) → `None`, honestly.
    """
    seen = {r.assistant for r in reports if getattr(r, "assistant", None)}
    agg = InstallReport(
        target=str(target_root), capability="all",
        assistant=(next(iter(seen)) if len(seen) == 1 else None), op=op,
    )
    for r in reports:
        for o in r.outcomes:
            agg.add(o)
    return agg


def _emit_lifecycle_event(op: LifecycleOp, report: InstallReport, args) -> None:
    """Observability (FR-007): one event per operation, no secrets in the fields."""
    log_event(
        logging.INFO, op.value, capability=report.capability,
        assistant=report.assistant,
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
