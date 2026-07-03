"""Guard: the Sertor dogfood stays a faithful Sertor client on the SpecKit surface (E10-FEAT-027).

Two faces of the special case that item A-05 surfaced must not return:

1. **Hand-authored `.claude/agents/speckit-*.md`** — client-divergent artifacts no host receives.
   spec-kit ships SKILLS to a Claude host (via `specify init`), not agents; the distributed bundle
   forbids these agents (`sertor-flow/tests/unit/test_no_vendored_speckit.py`) — this guard watches
   the dogfood repo itself.
2. **Tracked copies of the regenerable SpecKit machinery** — re-vendoring (pin drift), exactly what
   the launch-installer pivot (feature 045) removed. The machinery is produced by
   `scripts/dev/materialize-speckit.ps1` and git-ignored; it must never be committed.

Offline and presence-agnostic: asserts *absences* / git-tracking, never that the machinery is
present — so it passes in CI and on a fresh clone where the machinery is not materialized yet.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_MACHINERY_PREFIXES = (
    ".claude/skills/speckit-",
    ".specify/scripts/",
    ".specify/workflows/",
    ".specify/integrations/",
)
_MACHINERY_EXACT = frozenset(
    {
        ".specify/init-options.json",
        ".specify/integration.json",
        ".specify/templates/checklist-template.md",
        ".specify/templates/constitution-template.md",
        ".specify/templates/spec-template.md",
        ".specify/templates/tasks-template.md",
    }
)
# Sertor-authored artifacts that MUST stay tracked (guard against over-ignoring).
_SERTOR_AUTHORED = (
    ".specify/memory/constitution.md",
    ".specify/templates/plan-template.md",
    ".specify/feature.json",
)


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=_REPO_ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def test_no_hand_authored_speckit_agents():
    offenders = sorted((_REPO_ROOT / ".claude" / "agents").glob("speckit-*.md"))
    assert not offenders, (
        "hand-authored .claude/agents/speckit-*.md must not exist (client-divergent residue, "
        f"E10-FEAT-027 — a Claude host gets spec-kit SKILLS, not these agents): "
        f"{[p.name for p in offenders]}"
    )


def test_no_tracked_regenerable_speckit_machinery():
    offenders = [
        f
        for f in _tracked_files()
        if f.startswith(_MACHINERY_PREFIXES) or f in _MACHINERY_EXACT
    ]
    assert not offenders, (
        "regenerable SpecKit machinery must not be tracked in git (re-vendoring / pin drift, "
        f"E10-FEAT-027): {offenders}. "
        "Materialize it via scripts/dev/materialize-speckit.ps1 (git-ignored)."
    )


def test_sertor_authored_specify_artifacts_remain_tracked():
    tracked = set(_tracked_files())
    missing = [p for p in _SERTOR_AUTHORED if p not in tracked]
    assert not missing, (
        "Sertor-authored artifacts must stay tracked (not over-ignored by the machinery "
        f"gitignore): {missing}"
    )
