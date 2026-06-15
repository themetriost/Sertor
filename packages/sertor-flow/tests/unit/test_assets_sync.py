"""Guard anti-drift: il bundle governance corrisponde al sottoinsieme governance del dogfood (T045).

Canonical source = gli asset vendorizzati in `sertor_flow/assets/`; `.claude/`+`.specify/` del repo
sono la copia derivata. Questo test fallisce se le due copie divergono (drift = errore CI), così il
dogfooding gira sempre sulla versione installabile.

Confronto (F6) sul **sottoinsieme governance** propagato da `sync_governance_assets`:
- `assets/claude/**` ↔ `.claude/**` (skill/agenti speckit-* + requirements + requirements-analyst +
  configuration-manager — il bundle NON contiene wiki-author/wiki-curator, quindi è già il subset);
- `assets/specify/{templates,extensions,workflows}/**` ↔ `.specify/**`.

ESCLUSI dal confronto (e dalla propagazione):
- `assets/specify/scripts/**` (scaffolding dall'upstream spec-kit, F3: nessun mirror dogfood
  paritetico — il dogfood ha solo powershell, il bundle ps+bash);
- `constitution-starter.md` (≠ la `.specify/memory/constitution.md` RAG di Sertor);
- i `*.tmpl` init/integration, `NOTICE`, `LICENSES/**`, `claude-md-block-sdlc.md` (no mirror).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_flow.sync import sync_governance_assets
from sertor_install_kit.resources import iter_asset_dir

_ANCHOR = "sertor_flow"
# Repo root = three levels up from this test file (packages/sertor-flow/tests/unit/).
_REPO_ROOT = Path(__file__).resolve().parents[4]

# Bundle subtree → dogfood destination, restricted to the governance subset (F6).
_COMPARISONS: tuple[tuple[str, Path], ...] = (
    ("claude", _REPO_ROOT / ".claude"),
    ("specify/templates", _REPO_ROOT / ".specify" / "templates"),
    ("specify/extensions", _REPO_ROOT / ".specify" / "extensions"),
    ("specify/workflows", _REPO_ROOT / ".specify" / "workflows"),
)


# Excluded from the comparison: intentionally divergent (gruppo D). The bundle ships the GENERIC
# upstream plan-template; the dogfood keeps its gated one (same rationale as the scripts, F3).
_EXCLUDE_FROM_COMPARISON: frozenset[tuple[str, str]] = frozenset(
    {("specify/templates", "plan-template.md")}
)


def _bundle_files() -> list[tuple[str, str, Path]]:
    """Yields `(asset_subtree, rel_path, dogfood_path)` for every compared bundle asset."""
    out: list[tuple[str, str, Path]] = []
    for subtree, dest_root in _COMPARISONS:
        for rel_path, _content in iter_asset_dir(_ANCHOR, subtree):
            if (subtree, rel_path) in _EXCLUDE_FROM_COMPARISON:
                continue
            out.append((subtree, rel_path, dest_root / rel_path))
    return out


@pytest.mark.skipif(
    not (_REPO_ROOT / ".specify").is_dir(),
    reason="dogfood .specify/ not present (running outside the Sertor monorepo)",
)
@pytest.mark.parametrize(
    "subtree,rel_path",
    [(s, r) for s, r, _ in _bundle_files()],
    ids=[f"{s}/{r}" for s, r, _ in _bundle_files()],
)
def test_bundle_asset_matches_dogfood(subtree: str, rel_path: str):
    """Every governance bundle asset exists in the dogfood and is byte-for-byte identical."""
    content = dict(iter_asset_dir(_ANCHOR, subtree))[rel_path]
    dest = dict((s, dr) for s, dr in _COMPARISONS)[subtree] / rel_path
    assert dest.exists(), f"governance asset missing from dogfood: {dest}"
    assert dest.read_text(encoding="utf-8") == content, f"drift between bundle and dogfood: {dest}"


@pytest.mark.skipif(
    not (_REPO_ROOT / ".specify").is_dir(),
    reason="dogfood .specify/ not present (running outside the Sertor monorepo)",
)
def test_sync_dry_run_reports_no_drift():
    """A dry-run sync against the dogfood reports every governance asset as `identical`."""
    result = sync_governance_assets(_REPO_ROOT, dry_run=True)
    drifted = {rel: status for rel, status in result.items() if status != "identical"}
    assert not drifted, f"governance bundle out of sync with dogfood: {drifted}"


def test_scaffolding_scripts_excluded_from_sync():
    """F3: `assets/specify/scripts/**` is NOT propagated (no paritetic dogfood mirror)."""
    result = sync_governance_assets(_REPO_ROOT, dry_run=True)
    assert not any(rel.startswith("specify/scripts/") for rel in result)
    assert not any("/scripts/" in rel and rel.startswith("specify/scripts") for rel in result)


def test_constitution_starter_not_in_sync():
    """The constitution starter is never propagated onto the RAG constitution of the dogfood."""
    result = sync_governance_assets(_REPO_ROOT, dry_run=True)
    assert "constitution-starter.md" not in result
    assert not any(rel.endswith("memory/constitution.md") for rel in result)


def test_plan_template_is_neutral_not_sertor_gated():
    """Gruppo D: the bundle ships the GENERIC plan-template (gates from the host constitution), not
    Sertor's gated one — so a host's Constitution Check derives from its own constitution."""
    content = dict(iter_asset_dir(_ANCHOR, "specify/templates"))["plan-template.md"]
    assert "Gates determined based on constitution" in content  # generic placeholder
    # none of Sertor's specific gate vocabulary leaks into the host template
    sertor_markers = ("sertor_core", "SERTOR_ENGINE", "Consumo via vehicles", "host-agnostiche")
    for marker in sertor_markers:
        assert marker not in content, f"Sertor-specific gate leaked: {marker!r}"


def test_plan_template_excluded_from_sync():
    """Gruppo D: plan-template.md is neither propagated nor compared (intentionally divergent)."""
    result = sync_governance_assets(_REPO_ROOT, dry_run=True)
    assert "specify/templates/plan-template.md" not in result
