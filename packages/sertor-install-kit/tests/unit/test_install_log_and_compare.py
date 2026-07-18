"""E2-FEAT-018 (kit layer): additive `Outcome`, shared content comparison, install-event log."""
from __future__ import annotations

import json

from sertor_install_kit.artifacts import Outcome
from sertor_install_kit.lifecycle import content_matches
from sertor_install_kit.observability import INSTALL_LOG_NAME, log_install_event


def test_outcome_present_divergent_is_additive():
    """New member exists; existing members keep their value (report byte-compat, REQ-006)."""
    assert Outcome.PRESENT_DIVERGENT.value == "present_divergent"
    assert Outcome.SKIPPED.value == "skipped"
    assert Outcome.CREATED.value == "created"
    assert Outcome.UPDATED.value == "updated"


def test_content_matches_identical_and_line_ending_insensitive(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("line1\nline2\n", encoding="utf-8")
    assert content_matches(f, "line1\nline2\n")
    assert content_matches(f, "line1\r\nline2\r\n")   # CRLF vs LF must not read as divergent


def test_content_matches_divergent_and_missing(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("original\n", encoding="utf-8")
    assert not content_matches(f, "different\n")
    assert not content_matches(tmp_path / "absent.txt", "x")   # missing/unreadable → False


def test_log_install_event_appends_one_jsonl_line_per_call(tmp_path):
    log_install_event(tmp_path, op="install", capability="rag", target=".sertor",
                      outcome="created", reason="uv add ran", cmd="uv add core", rev="abc123")
    log_install_event(tmp_path, op="install", capability="rag", target="a.md",
                      outcome="present_divergent", reason="present but modified")
    lines = (tmp_path / INSTALL_LOG_NAME).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["schema"] == "install.event/1"
    assert first["op"] == "install" and first["outcome"] == "created" and first["rev"] == "abc123"
    second = json.loads(lines[1])
    assert second["outcome"] == "present_divergent"
    assert "cmd" not in second and "rev" not in second        # absent fields dropped


def test_log_install_event_dry_run_writes_nothing(tmp_path):
    log_install_event(tmp_path, op="install", capability="rag", target="a.md",
                      outcome="created", dry_run=True)
    assert not (tmp_path / INSTALL_LOG_NAME).exists()          # dry-run touches nothing (REQ-005)


def test_log_install_event_is_fail_safe(tmp_path):
    """A write failure must be swallowed, never abort the install (REQ-007)."""
    blocker = tmp_path / "blocked"
    blocker.write_text("i am a file", encoding="utf-8")
    # runtime_dir under a FILE → mkdir raises OSError; log_install_event must NOT propagate it.
    log_install_event(blocker / "x", op="install", capability="rag", target="a", outcome="created")
