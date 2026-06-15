"""Integration test for `sertor-flow install` end-to-end on a temp dir (T034)."""
from __future__ import annotations

import socket
from pathlib import Path

import pytest

from sertor_flow.__main__ import main


@pytest.fixture()
def installed(tmp_path: Path) -> Path:
    """Runs `sertor-flow install --target <tmp>` on a clean repo and returns the target."""
    rc = main(["install", "--target", str(tmp_path)])
    assert rc == 0
    return tmp_path


def test_install_deposits_speckit_skill(installed: Path):
    assert (installed / ".claude/skills/speckit-specify/SKILL.md").exists()


def test_install_deposits_requirements_analyst_agent(installed: Path):
    assert (installed / ".claude/agents/requirements-analyst.md").exists()


def test_install_deposits_configuration_manager_agent(installed: Path):
    assert (installed / ".claude/agents/configuration-manager.md").exists()


def test_install_deposits_specify_templates(installed: Path):
    assert (installed / ".specify/templates/plan-template.md").exists()


def test_install_ships_both_shells(installed: Path):
    """F3/DA-e: both bash and powershell scaffolding scripts are deposited."""
    assert (installed / ".specify/scripts/bash/check-prerequisites.sh").exists()
    assert (installed / ".specify/scripts/powershell/check-prerequisites.ps1").exists()


def test_install_deposits_constitution_starter(installed: Path):
    constitution = installed / ".specify/memory/constitution.md"
    assert constitution.exists()
    assert "Constitution" in constitution.read_text(encoding="utf-8")


def test_install_deposits_notice_and_license(installed: Path):
    assert (installed / ".specify/NOTICE").exists()
    assert (installed / ".specify/LICENSES/spec-kit-MIT.txt").exists()


def test_install_inserts_sdlc_block_in_claude_md(installed: Path):
    claude_md = installed / "CLAUDE.md"
    assert claude_md.exists()
    text = claude_md.read_text(encoding="utf-8")
    assert "<!-- SERTOR:SDLC-RITUAL START -->" in text
    assert "<!-- SERTOR:SDLC-RITUAL END -->" in text


def test_install_generates_init_options(installed: Path):
    init = installed / ".specify/init-options.json"
    assert init.exists()
    import json

    data = json.loads(init.read_text(encoding="utf-8"))
    assert data["integration"] == "claude"


def test_install_does_not_deposit_feature_json(installed: Path):
    """`.specify/feature.json` is runtime state, never installed (DA-e)."""
    assert not (installed / ".specify/feature.json").exists()


def test_install_does_not_run_any_phase(installed: Path):
    """install != run: no SDLC/git/index side effect (FR-003, SC-002)."""
    assert not (installed / ".git").exists()
    assert not (installed / "specs").exists()  # no feature created
    assert not (installed / ".sertor").exists()  # no index/runtime


def test_install_completes_offline(tmp_path: Path, monkeypatch):
    """F11/NFR-3: the install path makes no network connection."""

    def _blocked(*args, **kwargs):  # pragma: no cover - only triggered on regression
        raise AssertionError("network access attempted during install (must be offline)")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    rc = main(["install", "--target", str(tmp_path)])
    assert rc == 0


def test_install_report_json(tmp_path: Path, capsys):
    """`--json` emits a governance report consumable as JSON."""
    import json

    rc = main(["install", "--target", str(tmp_path), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["target"] == str(tmp_path)
    assert any(o["outcome"] == "created" for o in payload["outcomes"])
