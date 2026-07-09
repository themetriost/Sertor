"""Tests for feature 042 (Principio XI, groups B+C): host-facing RAG-usage enforcement.

`install rag` now deposits a `CLAUDE.md` block (`SERTOR:RAG-USAGE`, group B) and a host-specific
PreToolUse hook (`.claude/hooks/sertor-rag-usage-check.py` + settings entry, group C). Additive,
non-destructive, idempotent; the hook's absence must not break the capability (Principio X).
"""
from __future__ import annotations

import json
from pathlib import Path

from sertor_install_kit.artifacts import ArtifactKind, WriteStrategy
from sertor_installer.install_rag import (
    MARKER_END_RAG,
    MARKER_START_RAG,
    build_rag_plan,
    execute_rag_plan,
)
from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
from sertor_installer.resources import asset_path


def _run(target: Path, runner, **opts):
    options = RagInstallOptions(target_root=target, **opts)
    profile = RagHostProfile.from_options(options)
    plan = build_rag_plan(profile, with_deps=options.with_deps, mcp_scope=options.mcp_scope)
    return execute_rag_plan(plan, profile, runner), profile


_HOOK_REL = ".claude/hooks/sertor-rag-usage-check.py"
_SETTINGS_REL = ".claude/settings.json"


# --- plan composition ------------------------------------------------------------------------

def test_plan_contains_rag_usage_artifacts(tmp_path: Path):
    profile = RagHostProfile.from_options(RagInstallOptions(target_root=tmp_path, backend="azure"))
    plan = build_rag_plan(profile, with_deps=True)

    marker = [a for a in plan if a.kind is ArtifactKind.MARKER_BLOCK]
    assert len(marker) == 1
    assert marker[0].target_rel == "CLAUDE.md"
    assert marker[0].strategy is WriteStrategy.APPEND_BLOCK

    files = [a for a in plan if a.kind is ArtifactKind.FILE]
    assert any(a.target_rel.replace("\\", "/") == _HOOK_REL for a in files)
    assert all(a.strategy is WriteStrategy.CREATE_IF_ABSENT for a in files)

    settings = [a for a in plan if a.kind is ArtifactKind.SETTINGS_MERGE]
    # rag-usage (PreToolUse) + memory-capture (SessionEnd, FEAT-009) both merge into settings.json.
    assert len(settings) >= 1
    assert all(a.target_rel.replace("\\", "/") == _SETTINGS_REL for a in settings)
    assert all(a.strategy is WriteStrategy.MERGE_DEDUP for a in settings)


def test_plan_order_block_after_gitignore(tmp_path: Path):
    profile = RagHostProfile.from_options(RagInstallOptions(target_root=tmp_path, backend="azure"))
    kinds = [a.kind for a in build_rag_plan(profile, with_deps=False)]
    # canonical: ...GITIGNORE_APPEND → MARKER_BLOCK → FILE(hook) → SETTINGS_MERGE
    assert kinds.index(ArtifactKind.GITIGNORE_APPEND) < kinds.index(ArtifactKind.MARKER_BLOCK)
    assert kinds.index(ArtifactKind.MARKER_BLOCK) < kinds.index(ArtifactKind.FILE)
    assert kinds.index(ArtifactKind.FILE) < kinds.index(ArtifactKind.SETTINGS_MERGE)


# --- group B: CLAUDE.md block ----------------------------------------------------------------

def test_rag_usage_block_includes_search_first_discipline(tmp_path: Path, make_runner):
    # The host block must carry the "search first / errors are a signal" discipline (MCP-first),
    # not only the do-not-import rule, so installed hosts inherit it (feature-complete corollary).
    report, _ = _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    assert report.exit_code() == 0
    md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Search first, read second" in md
    assert "query the Sertor RAG before reading files" in md


def test_claude_md_block_deposited_with_distinct_markers(tmp_path: Path, make_runner):
    report, _ = _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    assert report.exit_code() == 0
    md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert MARKER_START_RAG in md and MARKER_END_RAG in md
    # distinct from wiki/SDLC markers
    assert "SERTOR:WIKI-RITUAL" not in md
    assert "SERTOR:SDLC-RITUAL" not in md
    # usage instruction content present
    assert "sertor-rag" in md
    assert "sertor_core" in md


def test_claude_md_block_created_when_absent(tmp_path: Path, make_runner):
    assert not (tmp_path / "CLAUDE.md").exists()
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    assert (tmp_path / "CLAUDE.md").is_file()


def test_claude_md_block_idempotent_no_duplicate(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    before = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    report2, _ = _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    after = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert before == after  # byte-for-byte unchanged
    assert after.count(MARKER_START_RAG) == 1  # no duplicate block


def test_claude_md_block_preserves_existing_content(tmp_path: Path, make_runner):
    md = tmp_path / "CLAUDE.md"
    md.write_text("# My project\n\nSome host guidance.\n", encoding="utf-8")
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    content = md.read_text(encoding="utf-8")
    assert content.startswith("# My project\n\nSome host guidance.\n")  # preserved
    assert MARKER_START_RAG in content


def test_claude_md_block_coexists_with_wiki_block(tmp_path: Path, make_runner):
    # simulate a CLAUDE.md that already has a wiki ritual block
    md = tmp_path / "CLAUDE.md"
    md.write_text(
        "<!-- SERTOR:WIKI-RITUAL START -->\nwiki ritual\n<!-- SERTOR:WIKI-RITUAL END -->\n",
        encoding="utf-8",
    )
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    content = md.read_text(encoding="utf-8")
    assert "SERTOR:WIKI-RITUAL START" in content  # wiki block untouched
    assert MARKER_START_RAG in content  # RAG block added
    assert content.count(MARKER_START_RAG) == 1


# --- group C: hook file + settings -----------------------------------------------------------

def test_hook_file_deposited(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    hook = tmp_path / _HOOK_REL
    assert hook.is_file()
    text = hook.read_text(encoding="utf-8")
    assert "sertor_core" in text     # detection logic present
    assert "_hooklib.run" in text    # fail-open / non-blocking (always exit 0)


def test_hook_file_create_if_absent_preserves_user_version(tmp_path: Path, make_runner):
    hook = tmp_path / _HOOK_REL
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("# user customized hook\n", encoding="utf-8")
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    assert hook.read_text(encoding="utf-8") == "# user customized hook\n"  # not overwritten


def test_settings_merge_adds_pretooluse_entry(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads((tmp_path / _SETTINGS_REL).read_text(encoding="utf-8"))
    assert "PreToolUse" in settings["hooks"]
    cmds = [
        h["command"]
        for e in settings["hooks"]["PreToolUse"]
        for h in e.get("hooks", [])
    ]
    assert any("sertor-rag-usage-check.py" in c for c in cmds)


def test_settings_merge_preserves_existing_hooks(tmp_path: Path, make_runner):
    settings_path = tmp_path / _SETTINGS_REL
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(
            {
                "$schema": "x",
                "hooks": {
                    "Stop": [{"hooks": [{"type": "command", "command": "echo mine"}]}]
                },
            }
        ),
        encoding="utf-8",
    )
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["$schema"] == "x"  # preserved
    stop_cmds = [h["command"] for e in settings["hooks"]["Stop"] for h in e["hooks"]]
    assert "echo mine" in stop_cmds  # user hook preserved
    assert "PreToolUse" in settings["hooks"]  # ours added


def test_settings_merge_idempotent(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    report2, _ = _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    settings = json.loads((tmp_path / _SETTINGS_REL).read_text(encoding="utf-8"))
    assert len(settings["hooks"]["PreToolUse"]) == 1  # no duplicate entry
    assert all(o.outcome.value in ("skipped", "merged") for o in report2.outcomes)


# --- end-to-end idempotence ------------------------------------------------------------------

def test_rerun_no_changes_to_existing_artifacts(tmp_path: Path, make_runner):
    _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    md_before = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    hook_before = (tmp_path / _HOOK_REL).read_text(encoding="utf-8")
    settings_before = (tmp_path / _SETTINGS_REL).read_text(encoding="utf-8")

    report2, _ = _run(tmp_path, make_runner(), backend="azure", with_deps=False)
    assert report2.exit_code() == 0
    assert report2.created == 0
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == md_before
    assert (tmp_path / _HOOK_REL).read_text(encoding="utf-8") == hook_before
    assert (tmp_path / _SETTINGS_REL).read_text(encoding="utf-8") == settings_before


# --- hook script: portable-Python asset form --------------------------------------------------
#
# The warn/exclusion/fail-open EXECUTION matrix (formerly a pwsh smoke here) is now covered by the
# portable-hook parity gate in `test_portable_hooks_parity.py`: `test_usage_check_warns_on_direct_
# import`, `::test_usage_check_skips_test_paths`, `::test_usage_check_fail_open_on_no_import` and
# `::test_usage_check_fail_open_on_empty_and_garbage` run the `.py` hook and assert exit 0 + a
# stderr-only warning (never a stdout payload). This file keeps only the asset-form check.

def _hook_script_path() -> Path:
    return Path(str(asset_path("rag/hooks/sertor-rag-usage-check.py")))


def test_hook_script_asset_form():
    """Asset is present, portable Python, fail-open (always exit 0) and detects `sertor_core`."""
    text = _hook_script_path().read_text(encoding="utf-8")
    assert "import" in text and "sertor_core" in text  # detection
    assert "_hooklib.run" in text                      # non-blocking / fail-open (always exit 0)
    assert "file=sys.stderr" in text                   # warning on stderr only
