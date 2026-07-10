"""Tests for the lifecycle primitives (feature 048): standalone helpers + execute_lifecycle.

Covers T020 (update_file_if_changed / remove_path / deregister_mcp_client / execute_lifecycle),
and the shared-file precision (T031/T032) is exercised through the dedicated inverse-primitive
tests (claude_md / settings_merge / gitignore / mcp_merge); here we add the integration-level
assertions on the orchestrator and the de-registration primitive.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_install_kit.artifacts import (
    Artifact,
    ArtifactKind,
    ArtifactOutcome,
    LifecycleOp,
    Outcome,
    WriteStrategy,
)
from sertor_install_kit.command_runner import CommandResult
from sertor_install_kit.lifecycle import (
    McpRegistrationError,
    SertorOwnedPaths,
    deregister_mcp_client,
    execute_lifecycle,
    remove_file_if_owned,
    remove_path,
    update_file_if_changed,
)

# --- A-16 content-guard: remove_file_if_owned ---------------------------------------------------

def test_remove_file_if_owned_removes_matching(tmp_path: Path):
    # A file whose content matches what Sertor deposited is removed (the normal uninstall path).
    p = tmp_path / "hook.py"
    p.write_text("print('sertor')\n", encoding="utf-8")
    outcome, _ = remove_file_if_owned(p, "print('sertor')\n")
    assert outcome is Outcome.REMOVED
    assert not p.exists()


def test_remove_file_if_owned_preserves_modified(tmp_path: Path):
    # A user-modified (or pre-existing-different) file is PRESERVED, not blindly deleted.
    p = tmp_path / "hook.py"
    p.write_text("print('user edit')\n", encoding="utf-8")
    outcome, detail = remove_file_if_owned(p, "print('sertor')\n")
    assert outcome is Outcome.SKIPPED
    assert p.exists()
    assert detail and "modified" in detail


def test_remove_file_if_owned_absent_skips(tmp_path: Path):
    outcome, _ = remove_file_if_owned(tmp_path / "nope.py", "x")
    assert outcome is Outcome.SKIPPED


def test_remove_file_if_owned_dry_run_projects_without_deleting(tmp_path: Path):
    p = tmp_path / "hook.py"
    p.write_text("print('sertor')\n", encoding="utf-8")
    outcome, _ = remove_file_if_owned(p, "print('sertor')\n", dry_run=True)
    assert outcome is Outcome.REMOVED
    assert p.exists()  # dry-run projects the removal verdict but never mutates


def test_remove_file_if_owned_line_ending_insensitive(tmp_path: Path):
    # CRLF on disk vs LF expected: the deposit path is line-ending insensitive → still a match.
    p = tmp_path / "hook.py"
    p.write_bytes(b"print('sertor')\r\n")
    outcome, _ = remove_file_if_owned(p, "print('sertor')\n")
    assert outcome is Outcome.REMOVED


class _FakeRunner:
    """Minimal CommandRunner double for the MCP de-registration tests."""

    def __init__(self, *, available: bool = True, result: CommandResult | None = None):
        self.available = available
        self.result = result if result is not None else CommandResult(0, "", "")
        self.calls: list[list[str]] = []

    def is_available(self, tool: str) -> bool:
        return self.available

    def run(self, cmd, cwd, env=None):
        self.calls.append(list(cmd))
        return self.result


def _art(target: str) -> Artifact:
    return Artifact(ArtifactKind.FILE, f"src/{target}", target, WriteStrategy.CREATE_IF_ABSENT)


# --- update_file_if_changed ---------------------------------------------------------------------


def test_update_file_if_changed_creates(tmp_path: Path):
    dest = tmp_path / "sub" / "f.txt"
    assert update_file_if_changed(dest, "hello") is Outcome.CREATED
    assert dest.read_text(encoding="utf-8") == "hello"


def test_update_file_if_changed_updates_when_differs(tmp_path: Path):
    dest = tmp_path / "f.txt"
    dest.write_text("old", encoding="utf-8")
    assert update_file_if_changed(dest, "new") is Outcome.UPDATED
    assert dest.read_text(encoding="utf-8") == "new"


def test_update_file_if_changed_skips_when_equal(tmp_path: Path):
    dest = tmp_path / "f.txt"
    dest.write_text("same", encoding="utf-8")
    before = dest.stat().st_mtime_ns
    assert update_file_if_changed(dest, "same") is Outcome.SKIPPED
    assert dest.stat().st_mtime_ns == before  # not rewritten


# --- remove_path --------------------------------------------------------------------------------


def test_remove_path_file(tmp_path: Path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    assert remove_path(f) is Outcome.REMOVED
    assert not f.exists()


def test_remove_path_directory_tree(tmp_path: Path):
    d = tmp_path / ".sertor"
    (d / "inner").mkdir(parents=True)
    (d / "inner" / "a.txt").write_text("x", encoding="utf-8")
    assert remove_path(d) is Outcome.REMOVED
    assert not d.exists()


def test_remove_path_absent_skips(tmp_path: Path):
    assert remove_path(tmp_path / "nope") is Outcome.SKIPPED


def test_remove_path_idempotent(tmp_path: Path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    remove_path(f)
    assert remove_path(f) is Outcome.SKIPPED


# --- deregister_mcp_client ----------------------------------------------------------------------


def test_deregister_mcp_client_removes(tmp_path: Path):
    runner = _FakeRunner(available=True, result=CommandResult(0, "ok", ""))
    assert deregister_mcp_client(runner) is Outcome.REMOVED
    assert ["claude", "mcp", "remove", "sertor-rag"] in runner.calls


def test_deregister_mcp_client_absent_client_raises(tmp_path: Path):
    runner = _FakeRunner(available=False)
    with pytest.raises(McpRegistrationError) as exc:
        deregister_mcp_client(runner)
    assert "claude mcp remove sertor-rag" in str(exc.value)  # actionable manual fallback


def test_deregister_mcp_client_not_registered_is_idempotent(tmp_path: Path):
    runner = _FakeRunner(available=True, result=CommandResult(1, "", "server not found"))
    assert deregister_mcp_client(runner) is Outcome.SKIPPED


def test_deregister_mcp_client_other_failure_raises(tmp_path: Path):
    runner = _FakeRunner(available=True, result=CommandResult(1, "", "boom"))
    with pytest.raises(McpRegistrationError):
        deregister_mcp_client(runner)


# --- execute_lifecycle --------------------------------------------------------------------------


def test_execute_lifecycle_dry_run_writes_nothing(tmp_path: Path):
    plan = [_art("a"), _art("b")]
    owned = SertorOwnedPaths(owned_files=("a", "b"))
    calls: list[str] = []

    def apply_fn(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        calls.append(art.target_rel)
        # the CLI passes a projecting apply_fn under dry-run: here we just project REMOVED
        return ArtifactOutcome(art.target_rel, Outcome.REMOVED, "projected")

    report = execute_lifecycle(
        plan, owned, apply_fn, op=LifecycleOp.UNINSTALL,
        target=str(tmp_path), capability="rag", dry_run=True,
    )
    assert report.removed == 2
    # no files were created/removed by the orchestrator (the dir is empty)
    assert list(tmp_path.iterdir()) == []
    assert calls == ["a", "b"]


def test_execute_lifecycle_upgrade_obsolete_phase_removes(tmp_path: Path):
    # plan produces only `keep.txt`; `obsolete.txt` exists on disk under an owned dir.
    (tmp_path / "keep.txt").write_text("k", encoding="utf-8")
    (tmp_path / "obsolete.txt").write_text("o", encoding="utf-8")
    plan = [_art("keep.txt")]
    owned = SertorOwnedPaths(owned_files=("keep.txt", "obsolete.txt"))

    def apply_fn(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED)

    report = execute_lifecycle(
        plan, owned, apply_fn, op=LifecycleOp.UPGRADE,
        target=str(tmp_path), capability="rag",
    )
    # keep.txt skipped, obsolete.txt removed
    assert report.removed == 1
    assert not (tmp_path / "obsolete.txt").exists()
    assert (tmp_path / "keep.txt").exists()
    rels = {o.target_rel: o.outcome for o in report.outcomes}
    assert rels["obsolete.txt"] is Outcome.REMOVED


def test_execute_lifecycle_upgrade_non_owned_disk_path_never_removed(tmp_path: Path):
    # A file on disk that is NOT in sertor_owned_paths must be left untouched (FR-013).
    (tmp_path / "user.txt").write_text("u", encoding="utf-8")
    plan = [_art("keep.txt")]
    (tmp_path / "keep.txt").write_text("k", encoding="utf-8")
    owned = SertorOwnedPaths(owned_files=("keep.txt",))  # user.txt is NOT owned

    def apply_fn(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED)

    report = execute_lifecycle(
        plan, owned, apply_fn, op=LifecycleOp.UPGRADE,
        target=str(tmp_path), capability="rag",
    )
    assert (tmp_path / "user.txt").exists()  # never removed
    assert report.removed == 0


def test_execute_lifecycle_dry_run_upgrade_does_not_remove(tmp_path: Path):
    (tmp_path / "obsolete.txt").write_text("o", encoding="utf-8")
    plan = [_art("keep.txt")]
    owned = SertorOwnedPaths(owned_files=("keep.txt", "obsolete.txt"))

    def apply_fn(art: Artifact, op: LifecycleOp) -> ArtifactOutcome:
        return ArtifactOutcome(art.target_rel, Outcome.SKIPPED)

    report = execute_lifecycle(
        plan, owned, apply_fn, op=LifecycleOp.UPGRADE,
        target=str(tmp_path), capability="rag", dry_run=True,
    )
    assert (tmp_path / "obsolete.txt").exists()  # dry-run: nothing removed
    assert report.removed == 1  # projected


# --- T031/T032: shared-file precision (byte-for-byte, non-destructive) --------------------------


def test_shared_claude_md_block_stripped_user_preserved(tmp_path: Path):
    from sertor_install_kit.claude_md import remove_marker_block, write_marker_block

    start, end = "<!-- SERTOR:RAG-USAGE START -->", "<!-- SERTOR:RAG-USAGE END -->"
    p = tmp_path / "CLAUDE.md"
    p.write_text("# User intro\n\nuser para before\n", encoding="utf-8")
    write_marker_block(p, "rag usage rules", start, end)
    p.write_text(p.read_text(encoding="utf-8") + "\nuser para after\n", encoding="utf-8")

    assert remove_marker_block(p, start, end) is Outcome.REMOVED
    text = p.read_text(encoding="utf-8")
    assert "user para before" in text and "user para after" in text
    assert start not in text


def test_shared_settings_only_sertor_hooks_removed(tmp_path: Path):
    import json

    from sertor_install_kit.settings_merge import merge_settings, remove_settings_entries

    frag = {"hooks": {"Stop": [{"hooks": [{"command": "sertor-rag check"}]}]}}
    p = tmp_path / "settings.json"
    p.write_text(
        json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "user own"}]}]}}),
        encoding="utf-8",
    )
    merge_settings(p, frag)
    out, _ = remove_settings_entries(p, frag)
    assert out is Outcome.REMOVED
    data = json.loads(p.read_text(encoding="utf-8"))
    cmds = [h["command"] for e in data["hooks"]["Stop"] for h in e["hooks"]]
    assert cmds == ["user own"]


def test_shared_gitignore_only_sertor_lines_removed(tmp_path: Path):
    from sertor_install_kit.gitignore_append import append_gitignore, remove_gitignore_lines

    p = tmp_path / ".gitignore"
    p.write_text("user/\n", encoding="utf-8")
    append_gitignore(p)
    out, _ = remove_gitignore_lines(p)
    assert out is Outcome.REMOVED
    assert "user/" in p.read_text(encoding="utf-8")


def test_shared_mcp_only_sertor_server_removed(tmp_path: Path):
    import json

    from sertor_install_kit.mcp_merge import remove_mcp_server

    p = tmp_path / ".mcp.json"
    p.write_text(
        json.dumps({"mcpServers": {"other": {"command": "x"}, "sertor-rag": {"command": "y"}}}),
        encoding="utf-8",
    )
    out, _ = remove_mcp_server(p)
    assert out is Outcome.REMOVED
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "other" in data["mcpServers"] and "sertor-rag" not in data["mcpServers"]


def test_shared_mcp_only_server_removes_file(tmp_path: Path):
    import json

    from sertor_install_kit.mcp_merge import remove_mcp_server

    p = tmp_path / ".mcp.json"
    p.write_text(json.dumps({"mcpServers": {"sertor-rag": {"command": "y"}}}), encoding="utf-8")
    out, _ = remove_mcp_server(p)
    assert out is Outcome.REMOVED
    assert not p.exists()


def test_shared_marker_absent_skips_no_op(tmp_path: Path):
    from sertor_install_kit.claude_md import remove_marker_block

    p = tmp_path / "CLAUDE.md"
    p.write_text("# only user content\n", encoding="utf-8")
    before = p.read_bytes()
    assert remove_marker_block(p, "<!-- S START -->", "<!-- S END -->") is Outcome.SKIPPED
    assert p.read_bytes() == before


# --- T056: symmetry — single source of the inverse primitives (SC-010) --------------------------


def test_inverse_primitives_importable_from_kit():
    """Every inverse primitive is importable from the kit's public surface (single source)."""
    import sertor_install_kit as kit

    for name in (
        "remove_marker_block", "update_marker_block", "remove_settings_entries",
        "remove_gitignore_lines", "remove_mcp_server", "deregister_mcp_client",
        "update_file_if_changed", "remove_path",
    ):
        assert hasattr(kit, name), f"{name} must be exported by sertor_install_kit"


def test_no_divergent_inverse_copy_in_consumers():
    """`sertor`/`sertor-flow` must NOT re-implement the inverse primitives (0 divergence, SC-010).

    They may import them from the kit, but no consumer module may DEFINE a function with the same
    name (an inverse primitive copy). Scans the two consumer source trees with the AST.
    """
    import ast

    here = Path(__file__).resolve()
    pkgs = here.parents[3]  # .../packages
    consumer_roots = [
        pkgs / "sertor" / "src" / "sertor_installer",
        pkgs / "sertor-flow" / "src" / "sertor_flow",
    ]
    inverse_names = {
        "remove_marker_block", "update_marker_block", "remove_settings_entries",
        "remove_gitignore_lines", "remove_mcp_server", "deregister_mcp_client",
        "update_file_if_changed", "remove_path",
    }
    offenders: list[str] = []
    for root in consumer_roots:
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name in inverse_names:
                    offenders.append(f"{path.name}: defines {node.name}")
    assert offenders == [], "inverse primitives must live only in the kit:\n" + "\n".join(offenders)
