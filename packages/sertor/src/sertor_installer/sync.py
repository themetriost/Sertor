"""Sync of assets to `.claude/` in the development repo (D2).

Canonical source = assets in the package; `.claude/` in the repo is the **derived copy**.
This script, *in development*, propagates `assets/claude/**` → `.claude/**` so that dogfooding
runs on the installable version. Canonical direction: **assets → .claude** (never the reverse).
The guard test `tests/unit/test_assets_sync.py` prevents the two copies from diverging
(drift = CI error).

Usage: `python -m sertor_installer.sync [--repo-root <path>] [--dry-run]`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sertor_installer.resources import iter_asset_dir


def sync_assets_to_claude(repo_root: Path, dry_run: bool = False) -> dict[str, str]:
    """Copies `assets/claude/**` to `<repo_root>/.claude/`. Returns `{rel: status}`.

    Status ∈ `created` (new file) · `updated` (different content) · `identical` (no change).
    In `dry_run` mode nothing is written; only reports what would be done.
    """
    result: dict[str, str] = {}
    claude_root = repo_root / ".claude"

    for rel_path, content in iter_asset_dir("claude"):
        dest = claude_root / rel_path
        if not dest.exists():
            status = "created"
        elif dest.read_text(encoding="utf-8") == content:
            status = "identical"
        else:
            status = "updated"
        result[rel_path] = status
        if status != "identical" and not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sertor_installer.sync",
        description="Propagates bundled assets to .claude/ in the dev repo (D2).",
    )
    parser.add_argument(
        "--repo-root", default=".", help="root of the development repo (default: cwd)"
    )
    parser.add_argument("--dry-run", action="store_true", help="do not write, only report")
    args = parser.parse_args(argv)

    result = sync_assets_to_claude(Path(args.repo_root).resolve(), dry_run=args.dry_run)
    for rel, status in sorted(result.items()):
        print(f"  {status:<10}{rel}")
    n_changed = sum(1 for s in result.values() if s != "identical")
    print(f"Sync: {n_changed} file{'s to update' if args.dry_run else 's updated'}, "
          f"{len(result)} total")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
