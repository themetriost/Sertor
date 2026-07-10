"""Sync of `sertor`'s byte-copied assets to the dev repo (D2) — over the kit's `sync` (037).

Canonical source = assets in the package; the dogfood trees are the **derived copy**. This script,
*in development*, propagates every **byte-copied file asset** the installer deposits (FILE/
CREATE_IF_ABSENT) → its dogfood destination, so dogfooding runs on the installable version.
Canonical direction: **assets → repo** (never the reverse).

**Role after E15 asset-install (FEAT-001 scope B) — dev-tool / anti-drift guard, NOT the fidelity
source.** The way the dogfood *obtains* its host-facing assets is now the **real installer** run on
the dogfood (`sertor install rag`/`wiki`, `sertor-flow install`) — process-fidelity. This `sync` is
kept only as a development convenience and as the propagation side of the byte-guard tests
(`test_assets_sync`, `test_assets_rag_dogfood_sync`), which keep dogfood↔bundle in parity. Do
**not** treat it as the source of truth for how the assets get there.

Covered subtrees (E15-FEAT-002): `assets/claude/**` → `.claude/**`, plus the byte-copied RAG assets
`assets/rag/{hooks,skills,agents}/**` → `.claude/{hooks,skills,agents}/**`. The **non-byte** RAG
assets (`rag/env*`, `rag/mcp*`, `rag/settings*`, `claude-md-block*`, `rag/sertor-cli-reference.md`)
live in `assets/rag/` root — NOT in these subtrees — and are merged/generated/marker-deposited at
install (process-fidelity, E15-FEAT-001), so they are excluded by construction.

Usage: `python -m sertor_installer.sync [--repo-root <path>] [--dry-run]`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sertor_install_kit.sync import sync_assets

_ANCHOR = "sertor_installer"

# Byte-copied file-asset subtrees → their dogfood destination. Enumerating the subtrees (not
# filtering by pattern) is what keeps the byte↔non-byte boundary robust and verifiable.
_BYTE_MAPPING: tuple[tuple[str, str], ...] = (
    ("claude", ".claude"),
    ("rag/hooks", ".claude/hooks"),
    ("rag/skills", ".claude/skills"),
    ("rag/agents", ".claude/agents"),
)


def sync_assets_to_claude(repo_root: Path, dry_run: bool = False) -> dict[str, str]:
    """Copies every byte-copied file asset to its dogfood destination.

    Returns `{"<subtree>/<rel>": status}`, status ∈ `created` · `updated` · `identical`. Keys are
    prefixed with the source subtree so several subtrees merge unambiguously (only `main()` consumes
    them, for display).
    """
    return sync_assets(_ANCHOR, repo_root, _BYTE_MAPPING, dry_run=dry_run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sertor_installer.sync",
        description="Propagates bundled assets to .claude/ in the dev repo (D2).",
    )
    parser.add_argument(
        "--repo-root", default=".", help="root of the development repo (default: cwd)"
    )
    parser.add_argument("--dry-run", action="store_true", help="do not write, only report")
    parser.add_argument(
        "--check", action="store_true",
        help="report drift WITHOUT writing and exit non-zero (1) if any asset differs — a gate "
             "for CI / a pre-commit hook (A-17). Implies no write.",
    )
    args = parser.parse_args(argv)

    # `--check`: read-only drift gate. Never writes (dry-run); exit 1 iff any asset is out of sync,
    # so it can be used as a guard alongside the byte-fidelity tests.
    if args.check:
        result = sync_assets_to_claude(Path(args.repo_root).resolve(), dry_run=True)
        drifted = {rel: s for rel, s in result.items() if s != "identical"}
        for rel, status in sorted(drifted.items()):
            print(f"  {status:<10}{rel}")
        if drifted:
            print(f"Sync check: {len(drifted)} of {len(result)} asset(s) DRIFTED — run "
                  "`python -m sertor_installer.sync` to propagate the bundle to the dogfood.")
            return 1
        print(f"Sync check: all {len(result)} byte-copied assets in sync.")
        return 0

    result = sync_assets_to_claude(Path(args.repo_root).resolve(), dry_run=args.dry_run)
    for rel, status in sorted(result.items()):
        print(f"  {status:<10}{rel}")
    n_changed = sum(1 for s in result.values() if s != "identical")
    print(f"Sync: {n_changed} file{'s to update' if args.dry_run else 's updated'}, "
          f"{len(result)} total")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
