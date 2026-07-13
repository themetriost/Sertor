"""Tests for the installer ergonomics of E2-FEAT-010:

- multi-target install (one command → several assistants, disjoint containers, aggregated report,
  deps bootstrapped once, fail-fast);
- the advisory non-Python host note (present on a non-Python host, absent on a Python host, sources
  untouched);
- the honest `uv`-absent guidance message.

CLI-level tests drive `main([...])`. `--no-deps` avoids any real `uv` (SubprocessRunner makes no
calls when the plan has no DEPENDENCIES/MCP_REGISTER step); the deps-once test injects the fake
runner by monkeypatching `SubprocessRunner`.
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_installer.__main__ import main
from sertor_installer.install_rag import NON_PYTHON_HOST_NOTE

_RAG_MARKER = "<!-- SERTOR:RAG-USAGE START -->"
_WIKI_MARKER = "<!-- SERTOR:WIKI-RITUAL START -->"


# --- multi-target install (REQ-001/002/003/005) -------------------------------------------------

def test_rag_multi_target_one_command_installs_both(tmp_path: Path, capsys):
    rc = main(
        ["install", "rag", "--target", str(tmp_path),
         "--assistant", "claude,copilot-cli", "--no-deps", "--json"]
    )
    assert rc == 0
    # disjoint containers: Claude → CLAUDE.md, Copilot → .github/copilot-instructions.md
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    copilot_md = (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert _RAG_MARKER in claude_md
    assert _RAG_MARKER in copilot_md
    # no double block in either container
    assert claude_md.count(_RAG_MARKER) == 1
    assert copilot_md.count(_RAG_MARKER) == 1
    # aggregated report: several assistants → assistant is None (honest), errors == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["assistant"] is None
    assert payload["summary"]["errors"] == 0


def test_wiki_multi_target_one_command_installs_both(tmp_path: Path, capsys):
    rc = main(
        ["install", "wiki", "--target", str(tmp_path), "--assistant", "claude,copilot-cli"]
    )
    assert rc == 0
    assert _WIKI_MARKER in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert (tmp_path / ".github" / "copilot-instructions.md").is_file()


def test_all_alias_installs_every_assistant(tmp_path: Path, capsys):
    rc = main(
        ["install", "rag", "--target", str(tmp_path), "--assistant", "all", "--no-deps"]
    )
    assert rc == 0
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / ".github" / "copilot-instructions.md").is_file()


def test_single_target_report_unchanged(tmp_path: Path, capsys):
    # SC-7: a single value (the default `claude`) → the report is the single one, assistant set.
    rc = main(["install", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["assistant"] == "claude"


def test_multi_target_deps_bootstrapped_once(tmp_path: Path, capsys, make_runner, monkeypatch):
    # The runtime (`.sertor/`, deps) is assistant-agnostic → `uv add` runs ONCE across both targets.
    shared = make_runner()
    monkeypatch.setattr("sertor_installer.__main__.SubprocessRunner", lambda: shared)
    rc = main(["install", "rag", "--target", str(tmp_path), "--assistant", "claude,copilot-cli"])
    assert rc == 0
    uv_add = [cmd for cmd, _ in shared.calls if cmd[:2] == ["uv", "add"]]
    assert len(uv_add) == 1


def test_multi_target_fail_fast_stops_before_next_assistant(
    tmp_path: Path, capsys, make_runner, monkeypatch
):
    # First target (claude, deps-bearing) fails on `uv add` → fail-fast: the second target
    # (copilot) is never touched (no .github container), overall exit reflects the failure.
    shared = make_runner(fail_on="add")
    monkeypatch.setattr("sertor_installer.__main__.SubprocessRunner", lambda: shared)
    rc = main(["install", "rag", "--target", str(tmp_path), "--assistant", "claude,copilot-cli"])
    assert rc == 1
    assert not (tmp_path / ".github" / "copilot-instructions.md").exists()


# --- non-Python host advisory note (REQ-006/007/008) --------------------------------------------

def test_non_python_host_gets_advisory_note(tmp_path: Path, capsys):
    (tmp_path / "App.sln").write_text("Microsoft Visual Studio Solution File\n", encoding="utf-8")
    csproj = tmp_path / "Foo.csproj"
    csproj.write_text("<Project></Project>\n", encoding="utf-8")
    csproj_before = csproj.read_text(encoding="utf-8")
    rc = main(["install", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert NON_PYTHON_HOST_NOTE in payload.get("notes", [])
    # REQ-007: advisory only — the host's own sources are untouched.
    assert csproj.read_text(encoding="utf-8") == csproj_before


def test_python_host_gets_no_non_python_note(tmp_path: Path, capsys):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    rc = main(["install", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert NON_PYTHON_HOST_NOTE not in payload.get("notes", [])


# --- honest uv-absent guidance (REQ-009) --------------------------------------------------------

def test_uv_absent_message_is_actionable_and_honest(tmp_path: Path, make_runner, monkeypatch):
    shared = make_runner(available=False)  # simulate `uv` absent
    monkeypatch.setattr("sertor_installer.__main__.SubprocessRunner", lambda: shared)
    rc = main(["install", "rag", "--target", str(tmp_path)])
    assert rc == 1  # fail-loud (no silent fallback)
    # no partial state (REQ-214 preserved)
    assert not (tmp_path / ".sertor").exists()


def test_uv_absent_dependency_error_names_real_options(tmp_path: Path, make_runner):
    # REQ-009: the message names install-uv + `--no-deps`, and flags pip as NOT yet available
    # (never implies pip works today).
    import pytest

    from sertor_installer.install_rag import DependencyError, _apply_deps
    from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions

    profile = RagHostProfile.from_options(RagInstallOptions(target_root=tmp_path))
    with pytest.raises(DependencyError) as exc:
        _apply_deps(profile, make_runner(available=False))
    msg = str(exc.value)
    assert "uv" in msg
    assert "--no-deps" in msg
    assert "pip" in msg.lower()
    assert "not available yet" in msg or "not yet available" in msg
