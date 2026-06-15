"""CLI backbone for the `sertor-flow` command (contracts/cli-sertor-flow.md, D10).

Thin **layer** (Principle I): argparse parsing → profile + governance install →
report formatting. Reference pattern: `sertor_installer.__main__`. **install ≠ run**:
the command only deposits the bundle — it never starts an SDLC/git/index phase.
Exit code: `0` success (even if everything skipped) · `1` domain error · `2` usage
error (argparse).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sertor_flow.install_governance import execute_governance_plan
from sertor_flow.profile import build_governance_profile
from sertor_install_kit import ConfigError, InstallerError


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
    install.add_argument("--json", action="store_true", help="emit the report as JSON")

    return parser


def _cmd_install(args) -> int:
    """Handler for `install`: validates the target, builds the profile, executes, prints."""
    target_root = Path(args.target).resolve()
    if not target_root.exists():
        raise ConfigError("target does not exist", key=str(target_root))
    if not target_root.is_dir():
        raise ConfigError("target is not a directory", key=str(target_root))

    profile = build_governance_profile(target_root)
    report = execute_governance_plan(profile)

    print(report.render_json() if args.json else report.render_human())
    return report.exit_code()


def _dispatch(args) -> int:
    if args.command == "install":
        return _cmd_install(args)
    raise ConfigError(f"unsupported command: {args.command}")  # pragma: no cover


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `sertor-flow` console-script. Returns the exit code (0/1/2)."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    args = _build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except InstallerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
