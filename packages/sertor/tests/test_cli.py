"""Tests for the `sertor` CLI backbone (T020, T029, US1/US3): help, stub, exit code, options.

SC-007.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sertor_installer.__main__ import main


def test_help_root(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "install" in out


def test_help_install(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["install", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "wiki" in out
    assert "rag" in out
    assert "governance" in out


def test_no_subcommand_exit_2(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_unknown_subcommand_exit_2(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["frobnicate"])
    assert exc.value.code == 2


def test_install_rag_no_deps_exit_0(tmp_path: Path, capsys):
    # --no-deps: scaffold without invoking `uv` (no network)
    rc = main(["install", "rag", "--target", str(tmp_path), "--no-deps"])
    assert rc == 0
    assert (tmp_path / ".sertor" / ".env").is_file()
    assert (tmp_path / ".mcp.json").is_file()
    assert (tmp_path / ".gitignore").is_file()


def test_install_rag_bad_backend_exit_2():
    with pytest.raises(SystemExit) as exc:
        main(["install", "rag", "--backend", "foo", "--no-deps"])
    assert exc.value.code == 2


def test_install_rag_json_report(tmp_path: Path, capsys):
    rc = main(["install", "rag", "--target", str(tmp_path), "--no-deps", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["schema"] == "install.report/1"
    assert payload["summary"]["errors"] == 0


def test_install_rag_assistant_copilot_exit_0(tmp_path: Path):  # feature 044, FR-001/002
    rc = main(["install", "rag", "--target", str(tmp_path), "--no-deps", "--assistant", "copilot"])
    assert rc == 0
    assert (tmp_path / ".vscode" / "mcp.json").is_file()
    assert not (tmp_path / ".mcp.json").exists()  # not the Claude file


def test_install_wiki_assistant_default_is_claude(tmp_path: Path):  # feature 044, FR-002
    rc = main(["install", "wiki", "--target", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "CLAUDE.md").is_file()  # default = claude (non-regression)
    assert not (tmp_path / ".github" / "copilot-instructions.md").exists()


def test_install_assistant_unknown_exit_1_actionable(tmp_path: Path, capsys):  # feature 044, FR-002
    rc = main(["install", "wiki", "--target", str(tmp_path), "--assistant", "codex"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "codex" in err and "claude" in err and "copilot" in err  # lists valid values


def test_install_governance_points_to_sertor_flow(capsys):
    """`install governance` is a pointer to the separate `sertor-flow` package (T043/T044)."""
    rc = main(["install", "governance"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "sertor-flow" in err  # names the package
    assert "install" in err  # tells the user how to install/run it


def test_sertor_pyproject_does_not_depend_on_sertor_flow():
    """`sertor` must NOT declare `sertor-flow` among its dependencies (FR-023/SC-008, T044)."""
    import tomllib

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", [])
    normalized = [d.split(">=")[0].split("==")[0].split("[")[0].strip().lower() for d in deps]
    assert "sertor-flow" not in normalized
    assert "sertor_flow" not in normalized
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    assert "sertor-flow" not in sources


def test_target_nonexistent_exit_1_no_artifacts(tmp_path: Path, capsys):
    missing = tmp_path / "does-not-exist"
    rc = main(["install", "wiki", "--target", str(missing)])
    assert rc == 1
    assert "error:" in capsys.readouterr().err
    assert not missing.exists()


def test_target_writes_under_target_not_cwd(tmp_path: Path, capsys):
    rc = main(["install", "wiki", "--target", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "wiki/wiki.config.toml").is_file()  # feature 016: config in wiki/
    assert not (tmp_path / "wiki.config.toml").exists()
    assert (tmp_path / ".claude/skills/wiki-author/SKILL.md").is_file()


def test_language_it_in_config(tmp_path: Path):
    main(["install", "wiki", "--target", str(tmp_path), "--language", "it"])
    config = (tmp_path / "wiki/wiki.config.toml").read_text(encoding="utf-8")
    assert 'language = "it"' in config


def test_source_dirs_override_in_config(tmp_path: Path):
    (tmp_path / "src").mkdir()
    main(["install", "wiki", "--target", str(tmp_path), "--source-dirs", "src,docs"])
    config = (tmp_path / "wiki/wiki.config.toml").read_text(encoding="utf-8")
    assert 'source_dirs = ["src", "docs"]' in config


def test_json_flag_emits_valid_report(tmp_path: Path, capsys):
    rc = main(["install", "wiki", "--target", str(tmp_path), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out.strip())
    assert payload["schema"] == "install.report/1"
    assert payload["summary"]["errors"] == 0
    assert payload["failed_step"] is None
    assert any(o["target_rel"] == "CLAUDE.md" and o["outcome"] == "block"
               for o in payload["outcomes"])
