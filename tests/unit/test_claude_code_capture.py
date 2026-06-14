"""US3 — `ClaudeCodeCaptureAdapter` defensive parser (031, D3, contract `memory.capture/1`).

Synthetic JSONL files under `tmp_path`; no real Claude Code, no network.
"""
from __future__ import annotations

import json
import logging

from sertor_core.adapters.capture.claude_code import (
    ClaudeCodeCaptureAdapter,
    encode_project_path,
)
from sertor_core.domain.memory import SessionRef


def _write_jsonl(path, lines):
    path.write_text("\n".join(lines), encoding="utf-8")


def _adapter(source_dir):
    return ClaudeCodeCaptureAdapter(source_dir, project_id="proj")


def test_encode_project_path():
    assert encode_project_path("C:\\Workspace\\Git\\Sertor") == "C--Workspace-Git-Sertor"
    assert encode_project_path("/home/me/proj") == "-home-me-proj"


def test_user_string_content_yields_one_turn(tmp_path):
    f = tmp_path / "sess.jsonl"
    _write_jsonl(f, [
        json.dumps({"type": "user", "message": {"role": "user", "content": "hello there"},
                    "timestamp": "2026-05-30T18:20:56.288Z"}),
    ])
    content = _adapter(tmp_path).read_session(
        SessionRef("sess", "proj", str(f)))
    assert len(content.turns) == 1
    assert content.turns[0].role == "user"
    assert content.turns[0].text == "hello there"
    assert content.turns[0].ts is not None  # ISO timestamp parsed to epoch


def test_assistant_text_and_thinking_blocks_concatenated(tmp_path):
    f = tmp_path / "sess.jsonl"
    _write_jsonl(f, [
        json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "let me think", "signature": "x"},
            {"type": "text", "text": "the answer"},
            {"type": "tool_use", "name": "Read", "input": {}},
        ]}}),
    ])
    content = _adapter(tmp_path).read_session(SessionRef("sess", "proj", str(f)))
    assert len(content.turns) == 1
    assert content.turns[0].text == "let me think\nthe answer"  # tool_use ignored
    assert content.turns[0].ts is None  # no timestamp → None (not an error)


def test_system_and_non_turn_events_ignored(tmp_path):
    f = tmp_path / "sess.jsonl"
    _write_jsonl(f, [
        json.dumps({"type": "custom-title", "customTitle": "x"}),
        json.dumps({"type": "system", "content": "boot"}),
        json.dumps({"type": "user", "message": {"role": "user", "content": "real turn"}}),
    ])
    content = _adapter(tmp_path).read_session(SessionRef("sess", "proj", str(f)))
    assert [t.text for t in content.turns] == ["real turn"]


def test_unparsable_line_skipped_with_warning(tmp_path, caplog):
    f = tmp_path / "sess.jsonl"
    _write_jsonl(f, [
        "this is not json {{{",
        "",  # empty line skipped silently
        json.dumps({"type": "user", "message": {"role": "user", "content": "ok"}}),
    ])
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        content = _adapter(tmp_path).read_session(SessionRef("sess", "proj", str(f)))
    assert [t.text for t in content.turns] == ["ok"]
    assert any("memory_capture_unparsable_line" in r.getMessage() for r in caplog.records)


def test_session_with_zero_turns(tmp_path):
    f = tmp_path / "sess.jsonl"
    _write_jsonl(f, [json.dumps({"type": "system", "content": "only system"})])
    content = _adapter(tmp_path).read_session(SessionRef("sess", "proj", str(f)))
    assert content.turns == ()


def test_list_sessions_returns_refs_for_jsonl_files(tmp_path):
    (tmp_path / "a.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "b.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")  # ignored (not .jsonl)
    (tmp_path / "c.jsonl").mkdir()  # a directory named like a session → ignored
    refs = _adapter(tmp_path).list_sessions()
    keys = sorted(r.session_key for r in refs)
    assert keys == ["a", "b"]
    assert all(r.project_id == "proj" for r in refs)


def test_absent_source_returns_empty_with_warning(tmp_path, caplog):
    missing = tmp_path / "does-not-exist"
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        refs = _adapter(missing).list_sessions()
    assert refs == []
    assert any("memory_capture_source_absent" in r.getMessage() for r in caplog.records)


def test_source_is_read_only(tmp_path):
    # FR-007: reading must not modify the source file.
    f = tmp_path / "sess.jsonl"
    payload = json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}})
    _write_jsonl(f, [payload])
    before = f.read_bytes()
    _adapter(tmp_path).read_session(SessionRef("sess", "proj", str(f)))
    assert f.read_bytes() == before
