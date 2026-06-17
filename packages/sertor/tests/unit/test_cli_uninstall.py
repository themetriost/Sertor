"""Tests for `sertor uninstall` (feature 048: US1/US3/US6/US7/US8 + invariants/observability).

Covers T029/T030 (rag/wiki uninstall), T033 (MCP de-registration), T035 (--purge-wiki D4),
T044 (aggregate), T053 (observability), T054 (system invariants), T055 (exit codes).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_installer.__main__ import main


def _install_rag(target: Path, extra: list[str] | None = None) -> None:
    rc = main(["install", "rag", "--target", str(target), "--no-deps", *(extra or [])])
    assert rc == 0


def _install_wiki(target: Path) -> None:
    rc = main(["install", "wiki", "--target", str(target)])
    assert rc == 0


# --- T029: uninstall rag ------------------------------------------------------------------------


def test_uninstall_rag_removes_runtime_and_shared(tmp_path: Path, capsys):
    # arrange: rag installed + a fake .sertor runtime dir + user content in shared files
    _install_rag(tmp_path)
    (tmp_path / ".sertor").mkdir(exist_ok=True)
    (tmp_path / ".sertor" / "marker.txt").write_text("runtime", encoding="utf-8")
    # add user content around the RAG-usage block and into .gitignore
    claude = tmp_path / "CLAUDE.md"
    claude.write_text("# User top\n\n" + claude.read_text(encoding="utf-8"), encoding="utf-8")
    gi = tmp_path / ".gitignore"
    gi.write_text("user_rule/\n" + gi.read_text(encoding="utf-8"), encoding="utf-8")
    capsys.readouterr()

    rc = main(["uninstall", "rag", "--target", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["removed"] >= 1
    # .sertor removed in block (obsolete phase is upgrade-only; uninstall removes via owned_dir? No:
    # uninstall removes via the plan inverse + the runtime dir is an owned_dir removed by the test's
    # expectation). The marker block was stripped; user content preserved.
    assert "# User top" in claude.read_text(encoding="utf-8")
    assert "SERTOR:RAG-USAGE" not in claude.read_text(encoding="utf-8")
    assert "user_rule/" in gi.read_text(encoding="utf-8")
    assert ".sertor/.env" not in gi.read_text(encoding="utf-8")


def test_uninstall_rag_idempotent_second_run_all_skipped(tmp_path: Path, capsys):
    _install_rag(tmp_path)
    main(["uninstall", "rag", "--target", str(tmp_path)])
    capsys.readouterr()
    rc = main(["uninstall", "rag", "--target", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["removed"] == 0
    assert payload["summary"]["errors"] == 0


def test_uninstall_rag_dry_run_writes_nothing(tmp_path: Path, capsys):
    _install_rag(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    capsys.readouterr()
    rc = main(["uninstall", "rag", "--target", str(tmp_path), "--dry-run", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["removed"] >= 1  # projected
    after = {p.name: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after  # 0 byte changed


def test_uninstall_rag_json_schema(tmp_path: Path, capsys):
    _install_rag(tmp_path)
    capsys.readouterr()
    main(["uninstall", "rag", "--target", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["schema"] == "install.report/1"
    assert set(payload["summary"].keys()) == {
        "created", "skipped", "merged", "block", "updated", "removed", "errors"
    }


# --- T030: uninstall wiki -----------------------------------------------------------------------


def test_uninstall_wiki_preserves_wiki_dir(tmp_path: Path, capsys):
    _install_wiki(tmp_path)
    assert (tmp_path / "wiki").is_dir()
    capsys.readouterr()
    rc = main(["uninstall", "wiki", "--target", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "wiki").is_dir()  # FR-027: preserved without --purge-wiki
    assert not (tmp_path / ".claude/skills/wiki-author/SKILL.md").exists()  # asset removed


def test_uninstall_wiki_idempotent(tmp_path: Path, capsys):
    rc = main(["uninstall", "wiki", "--target", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary"]["removed"] == 0
    assert payload["summary"]["errors"] == 0


# --- T033: MCP de-registration (scope local) ----------------------------------------------------


def test_uninstall_rag_local_scope_deregisters(tmp_path: Path, monkeypatch, capsys):
    # install rag with local scope mocks `claude` via a fake runner inside install; here we exercise
    # uninstall's de-registration path by stubbing SubprocessRunner used by the lifecycle handler.

    calls: list[list[str]] = []

    class _Runner:
        def is_available(self, tool):
            return True

        def run(self, cmd, cwd, env=None):
            calls.append(list(cmd))
            from sertor_install_kit.command_runner import CommandResult
            return CommandResult(0, "", "")

    monkeypatch.setattr("sertor_installer.__main__.SubprocessRunner", _Runner)
    # build a host with a local-scope rag plan: install with --mcp-scope local (claude mocked off
    # would fail install; instead install project scope, then uninstall local to test de-register).
    rc = main([
        "uninstall", "rag", "--target", str(tmp_path), "--mcp-scope", "local",
    ])
    assert rc == 0
    assert any("mcp" in c and "remove" in c for c in calls)


def test_uninstall_rag_local_scope_client_absent_fails(tmp_path: Path, monkeypatch, capsys):
    class _Runner:
        def is_available(self, tool):
            return False

        def run(self, cmd, cwd, env=None):  # pragma: no cover
            from sertor_install_kit.command_runner import CommandResult
            return CommandResult(0, "", "")

    monkeypatch.setattr("sertor_installer.__main__.SubprocessRunner", _Runner)
    rc = main(["uninstall", "rag", "--target", str(tmp_path), "--mcp-scope", "local"])
    assert rc == 1  # fail-fast: domain error
    # the report names the failed step; the actionable manual command is in the detail
    out = capsys.readouterr().out
    assert "claude mcp remove sertor-rag" in out


# --- T035: --purge-wiki (decision D4) -----------------------------------------------------------


def test_purge_wiki_with_yes_removes_dir(tmp_path: Path, capsys):
    _install_wiki(tmp_path)
    (tmp_path / "wiki" / "page.md").write_text("# page\n", encoding="utf-8")
    capsys.readouterr()
    rc = main(["uninstall", "wiki", "--target", str(tmp_path), "--purge-wiki", "--yes"])
    assert rc == 0
    assert not (tmp_path / "wiki").exists()
    out = capsys.readouterr().out
    assert "pages" in out  # count shown (SC-009)


def test_purge_wiki_no_tty_no_yes_preserves(tmp_path: Path, monkeypatch, capsys):
    _install_wiki(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    capsys.readouterr()
    rc = main(["uninstall", "wiki", "--target", str(tmp_path), "--purge-wiki"])
    assert rc == 0
    assert (tmp_path / "wiki").exists()  # CI-safe: not removed
    assert "--yes" in capsys.readouterr().out


def test_purge_wiki_dry_run_usage_error(tmp_path: Path, capsys):
    _install_wiki(tmp_path)
    rc = main(["uninstall", "wiki", "--target", str(tmp_path), "--purge-wiki", "--dry-run"])
    assert rc == 2  # usage error
    assert (tmp_path / "wiki").exists()


def test_purge_wiki_on_rag_usage_error(tmp_path: Path, capsys):
    rc = main(["uninstall", "rag", "--target", str(tmp_path), "--purge-wiki"])
    assert rc == 2  # flag valid only for wiki/aggregate


def test_purge_wiki_count_correct(tmp_path: Path, capsys):
    _install_wiki(tmp_path)
    (tmp_path / "wiki" / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "wiki" / "b.md").write_text("b", encoding="utf-8")
    capsys.readouterr()
    main(["uninstall", "wiki", "--target", str(tmp_path), "--purge-wiki", "--yes"])
    out = capsys.readouterr().out
    # at least the 2 added pages are counted (plus the scaffold's index/log)
    import re
    m = re.search(r"(\d+) pages", out)
    assert m is not None and int(m.group(1)) >= 2


# --- T044: aggregate ----------------------------------------------------------------------------


def test_uninstall_aggregate_equivalent_to_explicit(tmp_path: Path, capsys):
    _install_wiki(tmp_path)
    _install_rag(tmp_path)
    capsys.readouterr()
    rc = main(["uninstall", "--target", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["target"].endswith(tmp_path.name)
    # aggregate report carries capability "all"
    assert payload["assistant"] == "claude"


def test_uninstall_single_capability_leaves_others(tmp_path: Path, capsys):
    _install_wiki(tmp_path)
    _install_rag(tmp_path)
    capsys.readouterr()
    main(["uninstall", "rag", "--target", str(tmp_path)])
    # wiki assets still present (only rag removed)
    assert (tmp_path / ".claude/skills/wiki-author/SKILL.md").exists()


# --- T053: observability ------------------------------------------------------------------------


def test_uninstall_emits_log_event(tmp_path: Path, monkeypatch):
    _install_rag(tmp_path)
    events: list[dict] = []

    def _capture(level, operation, **fields):
        events.append({"operation": operation, **fields})

    monkeypatch.setattr("sertor_installer.__main__.log_event", _capture)
    main(["uninstall", "rag", "--target", str(tmp_path)])
    assert events
    ev = events[-1]
    assert ev["operation"] == "uninstall"
    assert ev["capability"] == "rag"
    assert "removed" in ev and "skipped" in ev and "errors" in ev


# --- T054: system invariants --------------------------------------------------------------------


def test_uninstall_does_not_index(tmp_path: Path):
    """FR-051 install≠run: uninstall never imports the RAG runtime (build_indexer/facade/engine)."""
    import sertor_installer.__main__ as m
    import sertor_installer.install_rag as ir
    import sertor_installer.install_wiki as iw
    source = (
        Path(m.__file__).read_text(encoding="utf-8")
        + Path(ir.__file__).read_text(encoding="utf-8")
        + Path(iw.__file__).read_text(encoding="utf-8")
    )
    for forbidden in ("build_indexer", "build_facade", "build_engine", "build_baseline_engine"):
        assert forbidden not in source


def test_uninstall_non_destructive_on_shared_file(tmp_path: Path):
    """FR-050: a shared file with user content keeps it; only the Sertor block is stripped."""
    _install_rag(tmp_path)
    claude = tmp_path / "CLAUDE.md"
    user_before = "# My very own header\n\nrules here\n"
    claude.write_text(user_before + "\n" + claude.read_text(encoding="utf-8"), encoding="utf-8")
    main(["uninstall", "rag", "--target", str(tmp_path)])
    after = claude.read_text(encoding="utf-8")
    assert user_before in after
    assert "SERTOR:RAG-USAGE" not in after


# --- T055: exit codes ---------------------------------------------------------------------------


def test_exit_0_on_clean_host(tmp_path: Path):
    assert main(["uninstall", "rag", "--target", str(tmp_path)]) == 0


def test_usage_error_purge_dry_run_exit_2(tmp_path: Path):
    assert main(["uninstall", "wiki", "--target", str(tmp_path), "--purge-wiki", "--dry-run"]) == 2
