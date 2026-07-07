"""Sync of the governance bundle to the dev repo (`.claude/`) — over the kit's sync.

Canonical source = the Sertor-authored assets vendored in this package; the dev repo trees are the
**derived copy**, so dogfooding runs on the installable governance bundle. Canonical direction:
**assets → repo** (never the reverse). A guard test (`test_assets_sync.py`) prevents the two copies
from diverging (drift = CI error).

**Role after E15 asset-install — dev-tool / anti-drift guard, NOT the fidelity source.** The dogfood
now *obtains* its governance assets by running the **real** `sertor-flow install` on itself
(process-fidelity, E15-FEAT-001 scope B). This `sync` remains only as a development convenience and
the propagation side of the byte guard; it is not how the assets are meant to get there.

Scope after the launch-installer pivot (feature 045): the bundle NO LONGER vendors SpecKit
(`assets/claude/skills/speckit-*`, `assets/claude/agents/speckit-*`, `assets/specify/**`) — those
come from `specify init`. So the only Sertor-authored `claude/**` surfaces left to sync are:
- `assets/claude/skills/requirements/**` → `.claude/skills/requirements/**`
- `assets/claude/agents/{requirements-analyst,configuration-manager}.md` → `.claude/agents/**`

Excluded from sync (no dogfood mirror / generated / agnostic): the `*.tmpl` init/integration
templates, `constitution-starter.md`, `claude-md-block-sdlc.md`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sertor_install_kit.sync import sync_subtree

_ANCHOR = "sertor_flow"


def sync_governance_assets(repo_root: Path, dry_run: bool = False) -> dict[str, str]:
    """Propagates the Sertor-authored governance subset of the bundle to `repo_root`.

    Returns `{rel: status}` with status ∈ `created` · `updated` · `identical`. Keys are prefixed
    with their subtree (`claude/…`). SpecKit is not vendored anymore (feature 045) so only the
    Sertor-authored `claude/**` surfaces are synced.
    """
    return sync_subtree(_ANCHOR, "claude", repo_root / ".claude", dry_run=dry_run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sertor_flow.sync",
        description="Propagates the Sertor-authored governance assets to .claude/ in the dev repo.",
    )
    parser.add_argument("--repo-root", default=".", help="root of the dev repo (default: cwd)")
    parser.add_argument("--dry-run", action="store_true", help="do not write, only report")
    args = parser.parse_args(argv)

    result = sync_governance_assets(Path(args.repo_root).resolve(), dry_run=args.dry_run)
    for rel, status in sorted(result.items()):
        print(f"  {status:<10}{rel}")
    n_changed = sum(1 for s in result.values() if s != "identical")
    print(f"Sync: {n_changed} file{'s to update' if args.dry_run else 's updated'}, "
          f"{len(result)} total")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
