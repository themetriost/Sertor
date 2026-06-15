"""Guard anti-drift: the Sertor-authored governance bundle matches the dogfood (feature 045).

Canonical source = the Sertor-authored assets vendored in `sertor_flow/assets/claude/`; the
`.claude/` of the repo is the derived copy. This test fails if the two diverge (drift = CI error),
so dogfooding always runs on the installable version.

After the launch-installer pivot, the bundle no longer vendors SpecKit — only the Sertor-authored
`claude/**` surfaces (the `requirements` skill + `requirements-analyst`/`configuration-manager`
agents) are compared. The `.specify/**` machinery now comes from `specify init` and is NOT a
vendored asset, so it is out of this comparison.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_flow.sync import sync_governance_assets
from sertor_install_kit.resources import iter_asset_dir

_ANCHOR = "sertor_flow"
# Repo root = four levels up from this test file (packages/sertor-flow/tests/unit/).
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DOGFOOD_CLAUDE = _REPO_ROOT / ".claude"


def _bundle_claude_files() -> list[str]:
    return [rel for rel, _ in iter_asset_dir(_ANCHOR, "claude")]


def test_bundle_holds_only_sertor_authored_claude_assets():
    """The vendored `claude/**` is now the Sertor-authored subset (no speckit-*)."""
    files = _bundle_claude_files()
    assert files, "expected Sertor-authored claude assets in the bundle"
    assert all(not f.startswith("skills/speckit-") for f in files)
    assert all(not f.startswith("agents/speckit-") for f in files)
    assert "skills/requirements/SKILL.md" in files
    assert "agents/requirements-analyst.md" in files
    assert "agents/configuration-manager.md" in files


@pytest.mark.skipif(
    not _DOGFOOD_CLAUDE.is_dir(),
    reason="dogfood .claude/ not present (running outside the Sertor monorepo)",
)
@pytest.mark.parametrize("rel_path", _bundle_claude_files(), ids=_bundle_claude_files())
def test_bundle_asset_matches_dogfood(rel_path: str):
    """Every Sertor-authored bundle asset exists in the dogfood and is byte-for-byte identical."""
    content = dict(iter_asset_dir(_ANCHOR, "claude"))[rel_path]
    dest = _DOGFOOD_CLAUDE / rel_path
    assert dest.exists(), f"governance asset missing from dogfood: {dest}"
    assert dest.read_text(encoding="utf-8") == content, f"drift between bundle and dogfood: {dest}"


@pytest.mark.skipif(
    not _DOGFOOD_CLAUDE.is_dir(),
    reason="dogfood .claude/ not present (running outside the Sertor monorepo)",
)
def test_sync_dry_run_reports_no_drift():
    """A dry-run sync against the dogfood reports every Sertor-authored asset as `identical`."""
    result = sync_governance_assets(_REPO_ROOT, dry_run=True)
    drifted = {rel: status for rel, status in result.items() if status != "identical"}
    assert not drifted, f"governance bundle out of sync with dogfood: {drifted}"


def test_sync_does_not_cover_speckit_or_specify():
    """The sync no longer touches SpecKit/`.specify/**` (obtained via launch, not vendored)."""
    result = sync_governance_assets(_REPO_ROOT, dry_run=True)
    assert not any("speckit-" in rel for rel in result)
    assert not any(rel.startswith("specify/") for rel in result)
