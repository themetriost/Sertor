"""Tests for `sertor-flow upgrade` (feature 048, US9): refresh assets, SDLC block, idempotency."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_flow.__main__ import main


@pytest.fixture()
def installed(tmp_path: Path, fake_runner) -> Path:
    rc = main(["install", "--target", str(tmp_path)], runner=fake_runner)
    assert rc == 0
    return tmp_path


def test_upgrade_aligned_host_zero_updates(installed: Path, capsys):
    capsys.readouterr()
    rc = main(["upgrade", "--target", str(installed), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["updated"] == 0
    assert payload["summary"]["errors"] == 0


def test_upgrade_refreshes_changed_sertor_authored_asset(installed: Path, capsys):
    agent = installed / ".claude/agents/requirements-analyst.md"
    agent.write_text("# stale agent\n", encoding="utf-8")
    capsys.readouterr()
    rc = main(["upgrade", "--target", str(installed), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["updated"] >= 1
    assert "stale agent" not in agent.read_text(encoding="utf-8")


def test_upgrade_refreshes_changed_sdlc_block(installed: Path, capsys):
    claude = installed / "CLAUDE.md"
    text = claude.read_text(encoding="utf-8")
    start = text.find("<!-- SERTOR:SDLC-RITUAL START -->")
    end = text.find("<!-- SERTOR:SDLC-RITUAL END -->")
    mutated = text[:start] + "<!-- SERTOR:SDLC-RITUAL START -->\nOLD SDLC\n" + text[end:]
    claude.write_text(mutated, encoding="utf-8")
    capsys.readouterr()
    rc = main(["upgrade", "--target", str(installed), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["updated"] >= 1
    assert "OLD SDLC" not in claude.read_text(encoding="utf-8")


def test_upgrade_preserves_constitution(installed: Path):
    constitution = installed / ".specify/memory/constitution.md"
    if not constitution.exists():
        constitution.parent.mkdir(parents=True, exist_ok=True)
    constitution.write_text("# host constitution edited\n", encoding="utf-8")
    main(["upgrade", "--target", str(installed)])
    assert "host constitution edited" in constitution.read_text(encoding="utf-8")  # not overwritten


def test_upgrade_dry_run_writes_nothing(installed: Path, capsys):
    agent = installed / ".claude/agents/requirements-analyst.md"
    agent.write_text("# stale\n", encoding="utf-8")
    before = {p: p.read_bytes() for p in installed.rglob("*") if p.is_file()}
    capsys.readouterr()
    rc = main(["upgrade", "--target", str(installed), "--dry-run", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["updated"] >= 1
    after = {p: p.read_bytes() for p in installed.rglob("*") if p.is_file()}
    assert before == after


def test_upgrade_json_same_schema(installed: Path, capsys):
    capsys.readouterr()
    main(["upgrade", "--target", str(installed), "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["schema"] == "install.report/1"
    assert "updated" in payload["summary"] and "removed" in payload["summary"]


def test_upgrade_emits_log_event(installed: Path, monkeypatch):
    events: list[dict] = []
    monkeypatch.setattr(
        "sertor_flow.__main__.log_event",
        lambda level, operation, **f: events.append({"operation": operation, **f}),
    )
    main(["upgrade", "--target", str(installed)])
    ev = events[-1]
    assert ev["operation"] == "upgrade"
    assert ev["capability"] == "governance"
