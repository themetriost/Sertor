"""CLI backbone for the `sertor-flow` command (contracts/cli-assistant.md, D10, feature 045).

Thin **layer** (Principle I): argparse parsing → profile + governance install → report formatting.
Reference pattern: `sertor_installer.__main__`. **install ≠ run**: the command only deposits the
bundle (and launches `specify init` to obtain SpecKit) — it never starts an SDLC/git/index phase.
Exit code: `0` success (even if everything skipped) · `1` domain error · `2` usage error (argparse).

`--assistant claude|copilot` (default `claude`, FR-001/002): selects the target assistant for both
the SpecKit launch (`specify init --ai <assistant>`) and the Sertor-authored surfaces. An unknown
value is rejected by the profile (`ConfigError`).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from sertor_flow.install_governance import (
    execute_governance_lifecycle,
    execute_governance_plan,
)
from sertor_flow.profile import DEFAULT_ASSISTANT, build_governance_profile
from sertor_install_kit import (
    CommandRunner,
    ConfigError,
    InstallerError,
    LifecycleOp,
    log_event,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sertor-flow",
        description="Installer of the Sertor development method (SDLC) on a host repository.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    install = sub.add_parser(
        "install", help="install the governance/SDLC bundle on the host (install != run)"
    )
    install.add_argument("--target", default=".", help="host repo root (default: cwd)")
    install.add_argument(
        "--assistant",
        default=DEFAULT_ASSISTANT,
        choices=["claude", "copilot"],
        help="target AI assistant (default: claude)",
    )
    install.add_argument("--json", action="store_true", help="emit the report as JSON")

    # --- feature 048: lifecycle verbs (symmetric to `sertor`, US9) ---------------------------
    for verb, helptext in (
        ("upgrade", "upgrade the installed governance bundle (refresh, remove obsoletes)"),
        ("uninstall", "uninstall the governance bundle (remove Sertor-authored surfaces)"),
    ):
        p = sub.add_parser(verb, help=helptext)
        p.add_argument("--target", default=".", help="host repo root (default: cwd)")
        p.add_argument(
            "--assistant", default=DEFAULT_ASSISTANT, choices=["claude", "copilot"],
            help="target AI assistant (default: claude)",
        )
        p.add_argument("--dry-run", action="store_true",
                       help="project the operation without touching the filesystem")
        p.add_argument("--json", action="store_true", help="emit the report as JSON")

    return parser


def _cmd_install(args, runner: CommandRunner | None = None) -> int:
    """Handler for `install`: validates the target, builds the profile, executes, prints."""
    target_root = Path(args.target).resolve()
    if not target_root.exists():
        raise ConfigError("target does not exist", key=str(target_root))
    if not target_root.is_dir():
        raise ConfigError("target is not a directory", key=str(target_root))

    profile = build_governance_profile(target_root, assistant=args.assistant)
    report = execute_governance_plan(profile, runner=runner)

    print(report.render_json() if args.json else report.render_human())
    return report.exit_code()


def _cmd_lifecycle(args, op: LifecycleOp, runner: CommandRunner | None = None) -> int:
    """Handler for `upgrade`/`uninstall`: validates the target, runs the lifecycle, prints."""
    target_root = Path(args.target).resolve()
    if not target_root.exists():
        raise ConfigError("target does not exist", key=str(target_root))
    if not target_root.is_dir():
        raise ConfigError("target is not a directory", key=str(target_root))

    profile = build_governance_profile(target_root, assistant=args.assistant)
    report = execute_governance_lifecycle(profile, op, runner=runner, dry_run=args.dry_run)
    log_event(
        logging.INFO, op.value, capability="governance", assistant=args.assistant,
        updated=report.updated, removed=report.removed,
        skipped=report.skipped, errors=report.errors,
    )
    print(report.render_json() if args.json else report.render_human())
    return report.exit_code()


def _dispatch(args, runner: CommandRunner | None = None) -> int:
    if args.command == "install":
        return _cmd_install(args, runner=runner)
    if args.command == "upgrade":
        return _cmd_lifecycle(args, LifecycleOp.UPGRADE, runner=runner)
    if args.command == "uninstall":
        return _cmd_lifecycle(args, LifecycleOp.UNINSTALL, runner=runner)
    raise ConfigError(f"unsupported command: {args.command}")  # pragma: no cover


def main(argv: list[str] | None = None, *, runner: CommandRunner | None = None) -> int:
    """Entry point for the `sertor-flow` console-script. Returns the exit code (0/1/2).

    `runner` is injectable (feature 045) so tests can mock the `specify init` launch (no network);
    production leaves it `None` → the launch uses `SubprocessRunner`.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    args = _build_parser().parse_args(argv)
    try:
        return _dispatch(args, runner=runner)
    except InstallerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
