"""US2 — `execute_governance_plan` completa anche se `sertor_core` non è importabile (T038, SC-004).

Simula un host privo del pacchetto `sertor-core`: installa nel `sys.meta_path` un
finder che blocca qualunque import di `sertor_core` sollevando `ImportError`. La
governance non deve toccare il core in nessun punto del percorso d'install, quindi
l'install completa con successo lo stesso.
"""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import sys
from pathlib import Path

import pytest


class _BlockSertorCore(importlib.abc.MetaPathFinder):
    """Meta-path finder that makes any `sertor_core` import fail (simulates its absence)."""

    def find_spec(self, fullname, path, target=None):  # noqa: D401, ANN001
        if fullname == "sertor_core" or fullname.startswith("sertor_core."):
            raise ImportError(f"simulated absence of {fullname} (host without sertor-core)")
        return None


@pytest.fixture()
def core_absent(monkeypatch):
    """Removes any cached `sertor_core` modules and blocks fresh imports for the test."""
    for name in list(sys.modules):
        if name == "sertor_core" or name.startswith("sertor_core."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    finder = _BlockSertorCore()
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])
    # Sanity: the simulation actually blocks the import.
    with pytest.raises(ImportError):
        __import__("sertor_core")
    return finder


def test_governance_install_completes_without_core(core_absent, tmp_path: Path):
    """SC-004: the full governance install succeeds when `sertor_core` is unavailable."""
    from sertor_flow.install_governance import execute_governance_plan
    from sertor_flow.profile import build_governance_profile
    from tests.conftest import FakeSpecifyRunner

    profile = build_governance_profile(tmp_path)
    report = execute_governance_plan(profile, runner=FakeSpecifyRunner())

    assert report.exit_code() == 0
    assert report.errors == 0
    assert report.created > 0
    # Spot-check a few host-facing artifacts landed (SpecKit via launch + Sertor-authored).
    assert (tmp_path / ".claude/commands/speckit.specify.md").exists()
    assert (tmp_path / ".specify/templates/plan-template.md").exists()
    assert (tmp_path / ".claude/agents/requirements-analyst.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()


def test_flow_cli_main_completes_without_core(core_absent, tmp_path: Path):
    """The CLI entry point too runs end-to-end without `sertor_core`."""
    from sertor_flow.__main__ import main
    from tests.conftest import FakeSpecifyRunner

    rc = main(["install", "--target", str(tmp_path)], runner=FakeSpecifyRunner())
    assert rc == 0
