"""Sync of bundled assets to the development repo (D2), with **parametric roots/anchor**.

Canonical source = assets in the package; the dev repo trees (`.claude/`, `.specify/`) are the
**derived copy**. This helper, *in development*, propagates `assets/<subtree>/**` →
`<repo_root>/<dest>/**` so that dogfooding runs on the installable version. Canonical direction:
**assets → repo** (never the reverse). A guard test prevents the two copies from diverging
(drift = CI error).

Generalized over the anchor and the subtree→destination mapping so it is reusable by both `sertor`
(anchor `sertor_installer`, `claude` → `.claude`) and `sertor-flow` (anchor `sertor_flow`,
`claude` → `.claude`, `specify` → `.specify`).
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from sertor_install_kit.resources import iter_asset_dir


def sync_subtree(
    anchor: str, subtree: str, dest_root: Path, dry_run: bool = False
) -> dict[str, str]:
    """Copies `assets/<subtree>/**` (read via `anchor`) to `dest_root`. Returns `{rel: status}`.

    Status ∈ `created` (new file) · `updated` (different content) · `identical` (no change).
    In `dry_run` mode nothing is written; only reports what would be done. The returned keys are
    prefixed with `<subtree>/` so callers can merge several subtrees in one report unambiguously.
    """
    result: dict[str, str] = {}
    for rel_path, content in iter_asset_dir(anchor, subtree):
        dest = dest_root / rel_path
        if not dest.exists():
            status = "created"
        elif dest.read_text(encoding="utf-8") == content:
            status = "identical"
        else:
            status = "updated"
        result[f"{subtree}/{rel_path}"] = status
        if status != "identical" and not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
    return result


def sync_assets(
    anchor: str,
    repo_root: Path,
    mapping: Iterable[tuple[str, str]],
    dry_run: bool = False,
) -> dict[str, str]:
    """Propagates several `(subtree, dest_rel)` mappings from the bundle to `repo_root`.

    Example: `sync_assets("sertor_installer", root, [("claude", ".claude")])`. Returns the merged
    `{rel: status}` of all subtrees.
    """
    result: dict[str, str] = {}
    for subtree, dest_rel in mapping:
        result.update(sync_subtree(anchor, subtree, repo_root / dest_rel, dry_run=dry_run))
    return result
