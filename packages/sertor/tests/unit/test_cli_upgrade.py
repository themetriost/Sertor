"""Tests for `sertor upgrade` (feature 048: US4/US5/US7/US8 + observability/exit codes).

Covers T036 (dry-run), T040 (upgrade refresh), T041 (obsolete phase), T042 (assistant switch),
T044 (aggregate), T053 (observability), T055 (exit codes).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_installer.__main__ import main


def _install_rag(target: Path) -> None:
    assert main(["install", "rag", "--target", str(target), "--no-deps"]) == 0


def _install_wiki(target: Path) -> None:
    assert main(["install", "wiki", "--target", str(target)]) == 0


# --- T040: upgrade refresh ----------------------------------------------------------------------


def test_upgrade_rag_aligned_host_zero_updates(tmp_path: Path, capsys):
    _install_rag(tmp_path)
    capsys.readouterr()
    rc = main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    # aligned host: nothing changes (idempotency, SC-005)
    assert payload["summary"]["updated"] == 0
    assert payload["summary"]["removed"] == 0
    assert payload["summary"]["errors"] == 0


def test_upgrade_rag_updates_changed_standalone_file(tmp_path: Path, capsys):
    _install_rag(tmp_path)
    hook = tmp_path / ".claude/hooks/sertor-rag-usage-check.ps1"
    hook.write_text("# stale content\n", encoding="utf-8")  # simulate an old version
    capsys.readouterr()
    rc = main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["updated"] >= 1  # hook refreshed
    assert "stale content" not in hook.read_text(encoding="utf-8")


def test_upgrade_rag_updates_changed_marker_block(tmp_path: Path, capsys):
    _install_rag(tmp_path)
    claude = tmp_path / "CLAUDE.md"
    text = claude.read_text(encoding="utf-8")
    # mutate inside the RAG-usage markers
    start = text.find("<!-- SERTOR:RAG-USAGE START -->")
    end = text.find("<!-- SERTOR:RAG-USAGE END -->")
    mutated = (
        text[:start]
        + "<!-- SERTOR:RAG-USAGE START -->\nOLD STALE BLOCK\n"
        + text[end:]
    )
    claude.write_text(mutated, encoding="utf-8")
    capsys.readouterr()
    rc = main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["updated"] >= 1
    assert "OLD STALE BLOCK" not in claude.read_text(encoding="utf-8")


def test_upgrade_rag_json_schema(tmp_path: Path, capsys):
    _install_rag(tmp_path)
    capsys.readouterr()
    main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["schema"] == "install.report/1"


# --- T041: obsolete phase -----------------------------------------------------------------------


def test_upgrade_removes_obsolete_owned_path(tmp_path: Path, capsys):
    # Install BOTH assistants' rag hooks on disk; upgrading for claude makes the copilot-only hook
    # (an owned path absent from the claude plan) obsolete → removed (FR-012). Claude hook stays.
    _install_rag(tmp_path)  # claude: .claude/hooks/...ps1
    copilot_hook = tmp_path / ".github/hooks/sertor-rag-usage-check.ps1"
    copilot_hook.parent.mkdir(parents=True, exist_ok=True)
    copilot_hook.write_text("# leftover copilot hook\n", encoding="utf-8")
    capsys.readouterr()
    rc = main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["removed"] >= 1  # the leftover copilot hook
    assert not copilot_hook.exists()
    assert (tmp_path / ".claude/hooks/sertor-rag-usage-check.ps1").exists()  # current plan kept


def test_upgrade_keeps_non_owned_disk_path(tmp_path: Path, capsys):
    _install_rag(tmp_path)
    user_file = tmp_path / "my-notes.txt"
    user_file.write_text("user", encoding="utf-8")
    capsys.readouterr()
    main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps"])
    assert user_file.exists()  # not Sertor-owned → never removed (FR-013)


# --- T036: dry-run ------------------------------------------------------------------------------


def test_upgrade_dry_run_writes_nothing(tmp_path: Path, capsys):
    _install_rag(tmp_path)
    hook = tmp_path / ".claude/hooks/sertor-rag-usage-check.ps1"
    hook.write_text("# stale\n", encoding="utf-8")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    capsys.readouterr()
    rc = main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps", "--dry-run", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["updated"] >= 1  # projected
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after  # 0 byte changed


def test_upgrade_dry_run_exit_0(tmp_path: Path):
    _install_rag(tmp_path)
    assert main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps", "--dry-run"]) == 0


# --- T042: assistant switch ---------------------------------------------------------------------


def test_upgrade_switch_assistant_removes_old_specific(tmp_path: Path, capsys):
    # install for claude, then switch to copilot-cli. A-01 (decision b): the switch REMOVES the
    # coexisting claude install → it is destructive → requires explicit consent (`--yes`).
    _install_rag(tmp_path)
    assert (tmp_path / ".claude/hooks/sertor-rag-usage-check.ps1").exists()
    capsys.readouterr()
    rc = main([
        "upgrade", "rag", "--target", str(tmp_path), "--no-deps",
        "--assistant", "copilot-cli", "--yes", "--json",
    ])
    assert rc == 0
    # claude-specific hook (not shared with copilot-cli) becomes obsolete → removed; copilot-cli
    # surfaces are created/updated.
    assert (tmp_path / ".github/hooks/sertor-rag-usage-check.ps1").exists()
    assert not (tmp_path / ".claude/hooks/sertor-rag-usage-check.ps1").exists()


def test_upgrade_switch_without_consent_is_refused(tmp_path: Path, capsys):
    # A-01 (decision b): an explicit switch that would strip a coexisting assistant WITHOUT --yes
    # (and no TTY) is a usage error — never a silent removal. The claude install is preserved.
    _install_rag(tmp_path)
    capsys.readouterr()
    rc = main([
        "upgrade", "rag", "--target", str(tmp_path), "--no-deps",
        "--assistant", "copilot-cli",  # no --yes, pytest has no TTY
    ])
    assert rc == 2  # UsageError
    assert (tmp_path / ".claude/hooks/sertor-rag-usage-check.ps1").exists()  # untouched
    assert not (tmp_path / ".github/hooks/sertor-rag-usage-check.ps1").exists()  # no switch


def test_bare_upgrade_preserves_coexisting_assistant(tmp_path: Path, capsys):
    # A-01: with BOTH assistants installed, a bare `upgrade` (no --assistant) must upgrade both and
    # strip neither — the confirmed footgun (default --assistant=claude used to remove copilot).
    _install_rag(tmp_path)  # claude
    assert main([
        "install", "rag", "--target", str(tmp_path), "--no-deps", "--assistant", "copilot-cli",
    ]) == 0
    claude_hook = tmp_path / ".claude/hooks/sertor-rag-usage-check.ps1"
    copilot_hook = tmp_path / ".github/hooks/sertor-rag-usage-check.ps1"
    assert claude_hook.exists() and copilot_hook.exists()
    capsys.readouterr()
    rc = main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["removed"] == 0  # nothing stripped
    assert claude_hook.exists()   # coexistence preserved
    assert copilot_hook.exists()
    assert (tmp_path / ".sertor").exists()  # shared runtime never swept as cruft


def test_bare_upgrade_no_capability_creep(tmp_path: Path, capsys):
    # A-01: a bare `upgrade` on a wiki-only host must NOT bootstrap the rag capability the host
    # never asked for (the old default installed rag+wiki+governance regardless).
    _install_wiki(tmp_path)
    assert not (tmp_path / ".sertor").exists()  # rag not installed
    capsys.readouterr()
    rc = main(["upgrade", "--target", str(tmp_path), "--no-deps"])
    assert rc == 0
    assert not (tmp_path / ".sertor").exists()  # still no rag → no creep


def test_bare_lifecycle_clean_host_is_noop(tmp_path: Path, capsys):
    # A-01: bare verb on a host with nothing installed → honest no-op, exit 0, no creep.
    rc = main(["upgrade", "--target", str(tmp_path), "--no-deps"])
    assert rc == 0
    assert not (tmp_path / ".sertor").exists()
    assert "nothing to upgrade" in capsys.readouterr().out


# --- T053: observability ------------------------------------------------------------------------


def test_upgrade_emits_log_event(tmp_path: Path, monkeypatch):
    _install_rag(tmp_path)
    events: list[dict] = []
    monkeypatch.setattr(
        "sertor_installer.__main__.log_event",
        lambda level, operation, **f: events.append({"operation": operation, **f}),
    )
    main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps"])
    ev = events[-1]
    assert ev["operation"] == "upgrade"
    assert ev["capability"] == "rag"
    assert "updated" in ev and "removed" in ev


# --- T044: aggregate ----------------------------------------------------------------------------


def test_upgrade_aggregate_no_args(tmp_path: Path, capsys):
    _install_wiki(tmp_path)
    _install_rag(tmp_path)
    capsys.readouterr()
    rc = main(["upgrade", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["schema"] == "install.report/1"


# --- T055: exit codes ---------------------------------------------------------------------------


def test_upgrade_clean_host_exit_0(tmp_path: Path):
    assert main(["upgrade", "rag", "--target", str(tmp_path), "--no-deps"]) == 0
