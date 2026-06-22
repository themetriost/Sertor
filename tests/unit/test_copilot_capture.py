"""FEAT-008 — `CopilotCliCaptureAdapter` defensive parser & project association.

Synthetic `<uuid>/events.jsonl` files under `tmp_path`; no real Copilot CLI, no network, no Copilot
installed (RNF-4). Mirrors `test_claude_code_capture.py`.
"""
from __future__ import annotations

import json
import logging

from sertor_core.adapters.capture.copilot_cli import (
    CopilotCliCaptureAdapter,
    _paths_match,
)
from sertor_core.domain.memory import SessionRef


def _make_session(tmp_path, uuid, events):
    """Create `<tmp_path>/<uuid>/events.jsonl` with the given list of event objects (or raw lines).

    A dict is JSON-encoded; a str is written verbatim (to inject malformed lines).
    """
    uuid_dir = tmp_path / uuid
    uuid_dir.mkdir(parents=True, exist_ok=True)
    lines = [e if isinstance(e, str) else json.dumps(e) for e in events]
    (uuid_dir / "events.jsonl").write_text("\n".join(lines), encoding="utf-8")
    return uuid_dir / "events.jsonl"


def _session_start(cwd=None, git_root=None):
    context: dict = {}
    if cwd is not None:
        context["cwd"] = cwd
    if git_root is not None:
        context["gitRoot"] = git_root
    return {"type": "session.start", "data": {"context": context},
            "timestamp": "2026-06-22T09:00:00Z"}


def _user(content, **extra):
    data = {"content": content}
    data.update(extra)
    return {"type": "user.message", "data": data, "timestamp": "2026-06-22T10:00:00Z"}


def _assistant(content, **extra):
    data = {"content": content}
    data.update(extra)
    return {"type": "assistant.message", "data": data, "timestamp": "2026-06-22T10:00:01Z"}


def _adapter(session_dir, project_id):
    return CopilotCliCaptureAdapter(session_dir, project_id=project_id)


# --- list_sessions: project association (US4, DA-CM-4) -----------------------------------------

def test_list_sessions_returns_matching_project(tmp_path):
    proj = str(tmp_path)
    _make_session(tmp_path, "uuid-a", [_session_start(cwd=proj), _user("hi")])
    _make_session(tmp_path, "uuid-b", [_session_start(cwd=proj), _user("yo")])
    refs = _adapter(tmp_path, proj).list_sessions()
    assert sorted(r.session_key for r in refs) == ["uuid-a", "uuid-b"]
    assert all(r.project_id == proj for r in refs)


def test_list_sessions_excludes_other_project(tmp_path):
    _make_session(tmp_path, "uuid-x", [_session_start(cwd="/some/other/project"), _user("hi")])
    refs = _adapter(tmp_path, str(tmp_path)).list_sessions()
    assert refs == []


def test_list_sessions_skips_unassociated_with_warning(tmp_path, caplog):
    # session.start present but no cwd/gitRoot → indeterminable project → skip + warning.
    _make_session(tmp_path, "uuid-u", [_session_start(), _user("hi")])
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        refs = _adapter(tmp_path, str(tmp_path)).list_sessions()
    assert refs == []
    assert any("memory_capture_session_unassociated" in r.getMessage() for r in caplog.records)


def test_list_sessions_no_session_start_skipped_with_warning(tmp_path, caplog):
    # No session.start at all → (None, None) → unassociated skip (no misattribution, DA-CM-2).
    _make_session(tmp_path, "uuid-n", [_user("hi"), _assistant("yo")])
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        refs = _adapter(tmp_path, str(tmp_path)).list_sessions()
    assert refs == []
    assert any("memory_capture_session_unassociated" in r.getMessage() for r in caplog.records)


def test_list_sessions_uses_gitroot_when_cwd_differs(tmp_path):
    # cwd is a subfolder of the repo, gitRoot is the project root → matches via gitRoot (DA-CM-4).
    proj = str(tmp_path)
    sub = str(tmp_path / "packages" / "sub")
    _make_session(tmp_path, "uuid-g", [_session_start(cwd=sub, git_root=proj), _user("hi")])
    refs = _adapter(tmp_path, proj).list_sessions()
    assert [r.session_key for r in refs] == ["uuid-g"]


def test_list_sessions_absent_source_returns_empty_with_warning(tmp_path, caplog):
    missing = tmp_path / "no-session-state"
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        refs = _adapter(missing, str(tmp_path)).list_sessions()
    assert refs == []
    assert any("memory_capture_source_absent" in r.getMessage() for r in caplog.records)


def test_source_dir_empty_list_sessions_empty(tmp_path, caplog):
    # Dir exists but no UUID subfolders → [] with no warning (honest: no sessions, not an error).
    (tmp_path / "session-state").mkdir()
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        refs = _adapter(tmp_path / "session-state", str(tmp_path)).list_sessions()
    assert refs == []
    assert not any("memory_capture_source_absent" in r.getMessage() for r in caplog.records)


def test_session_key_is_uuid_folder_name(tmp_path):
    proj = str(tmp_path)
    events_path = _make_session(tmp_path, "the-uuid-folder",
                                [_session_start(cwd=proj), _user("hi")])
    refs = _adapter(tmp_path, proj).list_sessions()
    assert refs[0].session_key == "the-uuid-folder"
    assert refs[0].source_path == str(events_path)


def test_session_key_stable_idempotent(tmp_path):
    proj = str(tmp_path)
    _make_session(tmp_path, "uuid-a", [_session_start(cwd=proj), _user("hi")])
    a = _adapter(tmp_path, proj).list_sessions()
    b = _adapter(tmp_path, proj).list_sessions()
    assert [r.session_key for r in a] == [r.session_key for r in b]


def test_list_sessions_idempotent(tmp_path):
    proj = str(tmp_path)
    _make_session(tmp_path, "uuid-a", [_session_start(cwd=proj), _user("hi")])
    _make_session(tmp_path, "uuid-b", [_session_start(cwd=proj), _user("yo")])
    first = sorted(r.session_key for r in _adapter(tmp_path, proj).list_sessions())
    second = sorted(r.session_key for r in _adapter(tmp_path, proj).list_sessions())
    assert first == second


def test_list_sessions_multi_project_isolation(tmp_path):
    # 3 sessions: A cwd=/projA, B cwd=/projB, C gitRoot=/projA → only A & C for /projA (SC-009).
    _make_session(tmp_path, "uuid-A", [_session_start(cwd="/projA"), _user("a")])
    _make_session(tmp_path, "uuid-B", [_session_start(cwd="/projB"), _user("b")])
    _make_session(tmp_path, "uuid-C", [_session_start(cwd="/projA/sub", git_root="/projA"),
                                       _user("c")])
    refs = _adapter(tmp_path, "/projA").list_sessions()
    assert sorted(r.session_key for r in refs) == ["uuid-A", "uuid-C"]


def test_list_sessions_skips_subfolder_without_events(tmp_path):
    # A UUID folder with no events.jsonl → skipped silently (not an error).
    (tmp_path / "uuid-empty").mkdir()
    proj = str(tmp_path)
    _make_session(tmp_path, "uuid-ok", [_session_start(cwd=proj), _user("hi")])
    refs = _adapter(tmp_path, proj).list_sessions()
    assert [r.session_key for r in refs] == ["uuid-ok"]


# --- _paths_match unit (US4, synthetic paths, offline) -----------------------------------------

def test_paths_match_exact_cwd():
    assert _paths_match("/repo", "/repo", None) is True


def test_paths_match_gitroot_contains_project():
    assert _paths_match("/repo/sub", "/elsewhere", "/repo") is True


def test_paths_match_cwd_is_ancestor():
    # cwd is an ANCESTOR of the project → False (rule is «cwd/gitRoot CONTAINS the project»).
    assert _paths_match("/repo/sub", "/repo", None) is False


def test_paths_match_both_none():
    assert _paths_match("/repo", None, None) is False


def test_paths_match_sibling_not_matched():
    assert _paths_match("/repo", "/repository", None) is False  # prefix but not a path component


# --- read_session: dialog extraction (US3, DA-CM-1) --------------------------------------------

def test_read_session_extracts_user_and_assistant_turns(tmp_path):
    f = _make_session(tmp_path, "u", [_user("hello there"), _assistant("the answer")])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert len(content.turns) == 2
    assert content.turns[0].role == "user"
    assert content.turns[0].text == "hello there"
    assert content.turns[1].role == "assistant"
    assert content.turns[1].text == "the answer"
    assert content.adapter_kind == "copilot-cli"
    assert content.turns[0].ts is not None  # ISO timestamp parsed to epoch


def test_read_session_discards_non_dialog_events(tmp_path):
    f = _make_session(tmp_path, "u", [
        _session_start(cwd="/x"),
        {"type": "tool.execution_start", "data": {}},
        {"type": "tool.execution_complete", "data": {}},
        {"type": "hook.start", "data": {}},
        {"type": "hook.end", "data": {}},
        {"type": "system.message", "data": {"content": "boot"}},
        {"type": "permission.request", "data": {}},
        {"type": "subagent.selected", "data": {}},
        {"type": "assistant.turn_start", "data": {}},
        {"type": "assistant.turn_end", "data": {}},
        {"type": "session.model_change", "data": {}},
        _user("real user turn"),
        _assistant("real assistant turn"),
    ])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert [t.text for t in content.turns] == ["real user turn", "real assistant turn"]


def test_read_session_ignores_tool_requests_in_assistant(tmp_path):
    f = _make_session(tmp_path, "u", [
        _assistant("answer with tools", toolRequests=[{"name": "Read"}, {"name": "Bash"}]),
    ])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert len(content.turns) == 1
    assert content.turns[0].text == "answer with tools"


def test_read_session_transformed_content_ignored(tmp_path):
    # transformedContent is system-reminder injection, NOT the dialog → use `content` (DA-CM-1).
    f = _make_session(tmp_path, "u", [_user("real", transformedContent="injected")])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert content.turns[0].text == "real"


def test_read_session_skips_empty_content(tmp_path):
    f = _make_session(tmp_path, "u", [_user(""), _user("   "), _user("kept")])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert [t.text for t in content.turns] == ["kept"]


def test_read_session_non_string_content_skipped(tmp_path):
    f = _make_session(tmp_path, "u", [_user([]), _assistant({"nested": "obj"}), _user("ok")])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert [t.text for t in content.turns] == ["ok"]


def test_read_session_missing_data_field_no_crash(tmp_path):
    f = _make_session(tmp_path, "u", [{"type": "user.message", "timestamp": "2026-06-22T10:00:00Z"},
                                      _user("ok")])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert [t.text for t in content.turns] == ["ok"]


def test_session_with_zero_dialog_events(tmp_path):
    f = _make_session(tmp_path, "u", [_session_start(cwd="/x"),
                                      {"type": "tool.execution_start", "data": {}}])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert content.turns == ()


def test_read_session_entirely_unknown_format_returns_empty_turns(tmp_path):
    f = _make_session(tmp_path, "u", [{"type": "future.event.type", "data": {"content": "x"}}])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert content.turns == ()


def test_read_session_unknown_event_fields_no_crash(tmp_path):
    f = _make_session(tmp_path, "u", [_user("ok", futureField={"nested": True})])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert [t.text for t in content.turns] == ["ok"]


def test_read_session_unparsable_line_skipped_with_warning(tmp_path, caplog):
    f = _make_session(tmp_path, "u", [
        _user("before"),
        "this is not json {{{",
        "",  # empty line skipped silently
        _assistant("after"),
    ])
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert [t.text for t in content.turns] == ["before", "after"]
    assert any("memory_capture_unparsable_line" in r.getMessage() for r in caplog.records)


def test_read_session_ts_parsed_from_timestamp_field(tmp_path):
    f = _make_session(tmp_path, "u", [_user("hi")])  # timestamp = 2026-06-22T10:00:00Z
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert isinstance(content.turns[0].ts, float)


def test_read_session_missing_timestamp_gives_none(tmp_path):
    f = _make_session(tmp_path, "u", [{"type": "user.message", "data": {"content": "hi"}}])
    content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert content.turns[0].ts is None


def test_read_session_oserror_returns_empty_turns(tmp_path, caplog):
    missing = str(tmp_path / "no-such" / "events.jsonl")
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        content = _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", missing))
    assert content.turns == ()
    assert any("memory_capture_unreadable" in r.getMessage() for r in caplog.records)


def test_source_read_only(tmp_path):
    # The source events.jsonl must not be modified by reading (parità Claude).
    f = _make_session(tmp_path, "u", [_user("hi")])
    before = f.read_bytes()
    _adapter(tmp_path, "proj").read_session(SessionRef("u", "proj", str(f)))
    assert f.read_bytes() == before
