"""Sync of the governance bundle to the dev repo (`.claude/`+`.specify/`) — over the kit's sync.

Canonical source = the assets vendored in this package; the dev repo trees are the **derived
copy**, so that dogfooding runs on the installable governance bundle. Canonical direction:
**assets → repo** (never the reverse). A guard test (`test_assets_sync.py`) prevents the two
copies from diverging (drift = CI error).

What is propagated (F6, the **governance subset only**):
- `assets/claude/**` → `.claude/**`: speckit-* skills/agents + `requirements` skill +
  `requirements-analyst`/`configuration-manager` agents. The bundle does NOT contain the wiki
  assets (`wiki-author`/`wiki-curator`), so this is structurally the governance subset.
- `assets/specify/{templates,extensions,workflows}` → `.specify/**`.

What is **excluded** from sync (and from the drift comparison):
- `assets/specify/scripts/**`: scaffolding scripts vendored from upstream spec-kit (F3); the
  dogfood `.specify/scripts/` ships powershell only — no paritetic mirror, so not comparable.
- `constitution-starter.md`: it is NOT the RAG-flavored `.specify/memory/constitution.md` of
  Sertor (must never be overwritten in the dogfood).
- the `*.tmpl` init/integration templates, `NOTICE`, `LICENSES/**`, `claude-md-block-sdlc.md`:
  generated/attribution assets with no dogfood mirror.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sertor_install_kit.sync import sync_subtree

_ANCHOR = "sertor_flow"

# Subtrees synced from assets/specify → .specify (scripts/** intentionally excluded, F3).
_SPECIFY_SUBTREES: tuple[str, ...] = ("templates", "extensions", "workflows")

# Files excluded from the sync/drift comparison because intentionally divergent (gruppo D, Principio
# XI): the bundle ships the GENERIC upstream `plan-template.md` (gates derived from the host's own
# constitution); Sertor's dogfood keeps its gated one. Same provenance logic as the scripts (F3).
_SUBTREE_EXCLUDE: dict[str, tuple[str, ...]] = {"templates": ("plan-template.md",)}


def sync_governance_assets(repo_root: Path, dry_run: bool = False) -> dict[str, str]:
    """Propagates the governance subset of the bundle to `repo_root`. Returns `{rel: status}`.

    Status ∈ `created` · `updated` · `identical`. Keys are prefixed with their subtree
    (`claude/…`, `specify/templates/…`) so a caller can disambiguate across subtrees.
    """
    result: dict[str, str] = {}
    # assets/claude/** → .claude/** (the bundle already holds only the governance subset).
    result.update(sync_subtree(_ANCHOR, "claude", repo_root / ".claude", dry_run=dry_run))
    # assets/specify/{templates,extensions,workflows} → .specify/** (NOT scripts/**, F3;
    # plan-template.md excluded — bundle generic vs dogfood gated, gruppo D).
    for subtree in _SPECIFY_SUBTREES:
        result.update(
            sync_subtree(
                _ANCHOR,
                f"specify/{subtree}",
                repo_root / ".specify" / subtree,
                dry_run=dry_run,
                exclude=_SUBTREE_EXCLUDE.get(subtree, ()),
            )
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sertor_flow.sync",
        description="Propagates the governance bundle to .claude/+.specify/ in the dev repo (D2).",
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
