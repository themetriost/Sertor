"""Acceptance tests US1/US2 for `install wiki` (T019, T025): empty repo, dogfood, idempotence."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sertor_core.wiki_tools.profile import load_profile
from sertor_installer.artifacts import Outcome
from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_wiki import build_install_plan, execute_plan


def _install(target: Path, **kwargs):
    profile = build_host_profile(target, **kwargs)
    plan = build_install_plan()
    return execute_plan(plan, profile)


# ---------------------------------------------------------------- US1: empty repo

def test_empty_repo_all_created_exit_zero(tmp_path: Path):
    report = _install(tmp_path)
    assert report.exit_code() == 0
    assert report.errors == 0
    # all outcomes are created/block (none skipped/error on empty repo)
    assert all(o.outcome in (Outcome.CREATED, Outcome.BLOCK) for o in report.outcomes)
    # counts derive from the plan, not fixed numbers: all FILE entries in the bundle + specials
    n_files = sum(1 for _ in build_install_plan() if _.target_rel.startswith(".claude/skills")
                  or _.target_rel.startswith(".claude/commands")
                  or _.target_rel.startswith(".claude/agents")
                  or _.target_rel.startswith(".claude/hooks"))
    assert n_files >= 17  # 14 skills + command + agent + hook
    # CLAUDE.md has outcome block (F11)
    claude_outcomes = [o for o in report.outcomes if o.target_rel == "CLAUDE.md"]
    assert len(claude_outcomes) == 1 and claude_outcomes[0].outcome is Outcome.BLOCK


def test_empty_repo_expected_files_present(tmp_path: Path):
    _install(tmp_path)
    assert (tmp_path / ".claude/skills/wiki-author/SKILL.md").is_file()
    assert (tmp_path / ".claude/commands/wiki.md").is_file()
    assert (tmp_path / ".claude/agents/wiki-curator.md").is_file()
    assert (tmp_path / ".claude/hooks/wiki-pending-check.ps1").is_file()
    assert (tmp_path / ".claude/settings.json").is_file()
    assert (tmp_path / "CLAUDE.md").is_file()
    # feature 016: config lives in wiki/, NOT in root (clean host root)
    assert (tmp_path / "wiki/wiki.config.toml").is_file()
    assert not (tmp_path / "wiki.config.toml").exists()
    assert (tmp_path / "wiki/index.md").is_file()
    assert (tmp_path / "wiki/concepts").is_dir()


def test_root_hygiene_only_unavoidable_residents(tmp_path: Path):
    """SC-001/FR-006 (feature 016): the host root contains only unavoidable residents."""
    _install(tmp_path)
    roots = {p.name for p in tmp_path.iterdir()}
    assert roots == {".claude", "CLAUDE.md", "wiki"}, (
        f"non-minimal root after install wiki: {sorted(roots)}"
    )
    # in particular: no wiki.config.toml scattered in root
    assert "wiki.config.toml" not in roots


def test_generated_config_passes_core_load_profile(tmp_path: Path):
    _install(tmp_path, language="it")
    # config in wiki/; root relative to host root (feature 016)
    profile = load_profile(tmp_path / "wiki/wiki.config.toml", root_override=tmp_path)
    assert profile.language == "it"
    assert len(profile.taxonomy) == 5
    assert profile.root_path == tmp_path / "wiki"  # root="wiki" resolved from host root


def test_dogfood_wiki_tools_scan_runs_on_generated_config(tmp_path: Path):
    """SC-008: sertor-wiki-tools runs on the generated config (direct import, no network)."""
    _install(tmp_path)
    # invocation via subprocess of the core console-script, on the config generated in wiki/
    # (canonical form feature 016: --config wiki/wiki.config.toml --root <host>)
    result = subprocess.run(
        [sys.executable, "-m", "sertor_core.wiki_tools", "scan",
         "--config", str(tmp_path / "wiki/wiki.config.toml"), "--root", str(tmp_path), "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["schema"] == "wiki.scan/1"


def test_no_network_no_rag_in_config(tmp_path: Path):
    """SC-005: install ≠ run — [rag] enabled=false in the generated config."""
    _install(tmp_path)
    profile = load_profile(tmp_path / "wiki/wiki.config.toml", root_override=tmp_path)
    assert profile.rag.get("enabled") is False


# ---------------------------------------------------------------- US2: pre-populated repo

def test_prepopulated_user_content_preserved(tmp_path: Path):
    # user CLAUDE.md
    user_md = "# Il mio progetto\n\nIstruzioni dell'utente.\n"
    (tmp_path / "CLAUDE.md").write_text(user_md, encoding="utf-8")
    # settings.json with user hook
    user_settings = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "shell": "bash", "command": "echo mine"}]}
            ]
        },
    }
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude/settings.json").write_text(
        json.dumps(user_settings, indent=2), encoding="utf-8"
    )
    # existing wiki.config.toml (user): valid for load_profile but with custom values,
    # so STRUCTURE does not fail and we can verify the file is not touched.
    existing_config = (tmp_path / "wiki.config.toml")
    existing_config.write_text(
        "# config utente\n"
        'language = "xx"\n'
        'root = "mywiki"\n'
        "[[taxonomy]]\n"
        'name = "notes"\n'
        'dir = "notes"\n'
        'type = "note"\n',
        encoding="utf-8",
    )
    config_hash_before = existing_config.read_bytes()
    # partial skill: one skill file already present
    (tmp_path / ".claude/skills/wiki-author").mkdir(parents=True)
    partial = tmp_path / ".claude/skills/wiki-author/SKILL.md"
    partial.write_text("contenuto skill personalizzato\n", encoding="utf-8")

    report = _install(tmp_path)

    # CLAUDE.md: user content byte-identical outside the markers
    after = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert after.startswith(user_md)
    assert "SERTOR:WIKI-RITUAL START" in after
    # settings.json: user hook preserved + 3 entries added
    merged = json.loads((tmp_path / ".claude/settings.json").read_text(encoding="utf-8"))
    cmds = [h["command"] for e in merged["hooks"]["SessionStart"] for h in e["hooks"]]
    assert "echo mine" in cmds
    # wiki.config.toml not touched
    assert existing_config.read_bytes() == config_hash_before
    # existing skill not overwritten
    assert partial.read_text(encoding="utf-8") == "contenuto skill personalizzato\n"
    # missing skill files created
    assert (tmp_path / ".claude/skills/wiki-author/wiki-playbook.md").is_file()
    assert report.exit_code() == 0


def test_double_run_idempotent(tmp_path: Path):
    """SC-003: two runs → second report all skipped/merged-0, filesystem state stable."""
    _install(tmp_path)
    snapshot = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    report2 = _install(tmp_path)
    assert report2.exit_code() == 0
    assert report2.created == 0
    assert report2.block == 0
    assert report2.merged == 1  # settings always "merged" but 0 new entries
    # filesystem identical
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert snapshot.keys() == after.keys()
    for p, content in snapshot.items():
        assert after[p] == content, f"{p} changed on re-run"


def test_malformed_settings_fail_fast(tmp_path: Path):
    """Malformed settings.json → exit 1, file not touched, failed_step set."""
    (tmp_path / ".claude").mkdir()
    bad = tmp_path / ".claude/settings.json"
    bad.write_text('{"hooks": {bad json', encoding="utf-8")
    bad_before = bad.read_bytes()

    report = _install(tmp_path)
    assert report.exit_code() == 1
    assert report.errors == 1
    assert report.failed_step == ".claude/settings.json"
    # malformed file not touched
    assert bad.read_bytes() == bad_before
    # FILE artifacts before settings remain written (no rollback)
    assert (tmp_path / ".claude/skills/wiki-author/SKILL.md").is_file()
