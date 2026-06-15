"""Sync of `sertor`'s assets to `.claude/` in the dev repo (D2) — over the kit's `sync` (037).

Canonical source = assets in the package; `.claude/` in the repo is the **derived copy**. This
script, *in development*, propagates `assets/claude/**` → `.claude/**` so that dogfooding runs on
the installable version. Canonical direction: **assets → .claude** (never the reverse).

The generic sync helper migrated to `sertor-install-kit` (anchor + subtree→dest parametric); this
wrapper binds the anchor to `"sertor_installer"` and the single `claude` → `.claude` mapping,
preserving the historical `sync_assets_to_claude(repo_root, dry_run)` API.

Usage: `python -m sertor_installer.sync [--repo-root <path>] [--dry-run]`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sertor_install_kit.sync import sync_subtree

_ANCHOR = "sertor_installer"


def sync_assets_to_claude(repo_root: Path, dry_run: bool = False) -> dict[str, str]:
    """Copies `assets/claude/**` to `<repo_root>/.claude/`. Returns `{rel: status}`.

    Status ∈ `created` · `updated` · `identical`. The returned keys keep the historical form
    (relative to `.claude/`, without the `claude/` prefix) for backward compatibility.
    """
    prefixed = sync_subtree(_ANCHOR, "claude", repo_root / ".claude", dry_run=dry_run)
    # Strip the `claude/` subtree prefix the kit adds, to keep the historical key form.
    return {rel.removeprefix("claude/"): status for rel, status in prefixed.items()}


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
