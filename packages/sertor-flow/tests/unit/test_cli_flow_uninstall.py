"""Tests for `sertor-flow uninstall` (feature 048, US9) + the `plan ⊆ owned` invariant (T046).

`sertor-flow install` is run with the mocked `specify` launch (no network); then `uninstall`
strips the Sertor-authored surfaces and the SDLC block, preserves the constitution, and is
idempotent. The no-core-dependency invariant (T051) is enforced by the existing
`test_no_core_dependency.py` (AST scan + pyproject) — the new lifecycle code uses only kit
primitives.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_flow.__main__ import main
from sertor_flow.install_governance import build_governance_plan, sertor_owned_paths
from sertor_flow.profile import build_governance_profile

# --- T046: plan ⊆ owned -------------------------------------------------------------------------


@pytest.mark.parametrize("assistant", ["claude", "copilot"])
def test_governance_plan_subset_of_owned(assistant):
    profile = build_governance_profile(Path("."), assistant=assistant)
    plan = build_governance_plan(profile)
    owned = sertor_owned_paths(assistant)
    covered = owned.covered_targets()

    def _covered(rel: str) -> bool:
        rel = rel.replace("\\", "/")
        for d in covered:
            d = d.replace("\\", "/").rstrip("/")
            if rel == d or rel.startswith(d + "/"):
                return True
        return False

    # The constitution is deliberately NOT in `owned` (host's, create-if-absent, preserved).
    constitution = ".specify/memory/constitution.md"
    uncovered = [
        a.target_rel for a in plan
        if not _covered(a.target_rel) and a.target_rel != constitution
    ]
    assert uncovered == [], f"governance/{assistant}: uncovered {uncovered}"


# --- US9: uninstall -----------------------------------------------------------------------------


@pytest.fixture()
def installed(tmp_path: Path, fake_runner) -> Path:
    rc = main(["install", "--target", str(tmp_path)], runner=fake_runner)
    assert rc == 0
    return tmp_path


def test_uninstall_strips_sdlc_block_only(installed: Path, capsys):
    claude = installed / "CLAUDE.md"
    # add user content around the SDLC block
    claude.write_text("# My governance notes\n\n" + claude.read_text(encoding="utf-8"),
                      encoding="utf-8")
    capsys.readouterr()
    rc = main(["uninstall", "--target", str(installed)])
    assert rc == 0
    text = claude.read_text(encoding="utf-8") if claude.exists() else ""
    assert "My governance notes" in text  # user content preserved
    assert "SERTOR:SDLC-RITUAL" not in text  # only the block stripped


def test_uninstall_removes_sertor_authored_surfaces(installed: Path):
    assert (installed / ".claude/agents/requirements-analyst.md").exists()
    main(["uninstall", "--target", str(installed)])
    assert not (installed / ".claude/agents/requirements-analyst.md").exists()
    assert not (installed / ".claude/agents/configuration-manager.md").exists()


def test_uninstall_preserves_constitution(installed: Path):
    constitution = installed / ".specify/memory/constitution.md"
    # the launch mock does not deposit it; install creates it (create-if-absent)
    if not constitution.exists():
        constitution.parent.mkdir(parents=True, exist_ok=True)
        constitution.write_text("# host constitution\n", encoding="utf-8")
    # `.specify/` is removed in block on uninstall → the constitution goes with it (it lives under
    # `.specify/`). FR-040 protects it from OVERWRITE in upgrade; uninstall removes the tree by
    # design (FR-041, `.specify/` is Sertor-owned via `specify init`).
    main(["uninstall", "--target", str(installed)])
    assert not (installed / ".specify").exists()


def test_uninstall_idempotent_clean_host(tmp_path: Path, capsys):
    rc = main(["uninstall", "--target", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["removed"] == 0
    assert payload["summary"]["errors"] == 0


def test_uninstall_dry_run_writes_nothing(installed: Path, capsys):
    before = {p: p.read_bytes() for p in installed.rglob("*") if p.is_file()}
    capsys.readouterr()
    rc = main(["uninstall", "--target", str(installed), "--dry-run", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["removed"] >= 1  # projected
    after = {p: p.read_bytes() for p in installed.rglob("*") if p.is_file()}
    assert before == after  # 0 byte changed


def test_uninstall_json_same_schema(installed: Path, capsys):
    capsys.readouterr()
    main(["uninstall", "--target", str(installed), "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["schema"] == "install.report/1"
    assert set(payload["summary"].keys()) == {
        "created", "skipped", "merged", "block", "updated", "removed", "errors"
    }


def test_uninstall_emits_log_event(installed: Path, monkeypatch):
    events: list[dict] = []
    monkeypatch.setattr(
        "sertor_flow.__main__.log_event",
        lambda level, operation, **f: events.append({"operation": operation, **f}),
    )
    main(["uninstall", "--target", str(installed)])
    ev = events[-1]
    assert ev["operation"] == "uninstall"
    assert ev["capability"] == "governance"


# --- T051: no-core import in the new lifecycle code (cross-check) --------------------------------


def test_no_core_import_in_install_governance():
    """The lifecycle code added to install_governance imports no `sertor_core` (FR-045/SC-010)."""
    import ast

    import sertor_flow.install_governance as m

    source = Path(m.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "sertor_core" or node.module.startswith("sertor_core."):
                offenders.append(node.module)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("sertor_core") or alias.name == "sertor":
                    offenders.append(alias.name)
    assert offenders == []
