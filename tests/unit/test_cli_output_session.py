"""US1/US2 — pure output functions `format_session_transcript`/`format_session_list` (036).

Pure functions (no terminal, no I/O): take core entities and produce text (human or `--json`).
Same style as `tests/unit` coverage of `format_memory_results`. Invariants under test: full text
(no truncation, SC-001), recency rendering, human↔JSON informational equivalence (SC-002), explicit
empty states (empty session / empty list).
"""
from __future__ import annotations

import json

from sertor_core.cli import output
from sertor_core.domain.memory import ArchivedSession, SessionSummary, TranscriptTurn


def _session(*, turns: tuple[TranscriptTurn, ...]) -> ArchivedSession:
    return ArchivedSession(
        session_key="sess-abc",
        project_id="C:/Workspace/Git/Sertor",
        captured_at=1718360463.0,
        adapter_kind="claude-code",
        turns=turns,
    )


# ============================================================ format_session_transcript (US1)


def test_transcript_human_lists_all_turns_in_order_full_text():
    long_text = "x" * 5000  # well beyond any preview length: must not be truncated (SC-001)
    session = _session(
        turns=(
            TranscriptTurn(index=0, role="user", text="first", ts=1718360455.0),
            TranscriptTurn(index=1, role="assistant", text=long_text, ts=1718360461.0),
        )
    )
    out = output.format_session_transcript(session, json=False)
    assert "session=sess-abc" in out
    assert "turns=2" in out
    assert "adapter=claude-code" in out
    assert "[0] user" in out
    assert "[1] assistant" in out
    assert long_text in out  # full text, no truncation
    assert "…" not in out  # no preview ellipsis
    # order: turn 0 appears before turn 1
    assert out.index("[0] user") < out.index("[1] assistant")


def test_transcript_json_has_all_fields_and_full_text():
    long_text = "y" * 5000
    session = _session(
        turns=(
            TranscriptTurn(index=0, role="user", text="hi", ts=1718360455.0),
            TranscriptTurn(index=1, role="assistant", text=long_text, ts=None),
        )
    )
    payload = json.loads(output.format_session_transcript(session, json=True))
    assert payload["session_key"] == "sess-abc"
    assert payload["project_id"] == "C:/Workspace/Git/Sertor"
    assert payload["captured_at"] == 1718360463.0
    assert payload["adapter_kind"] == "claude-code"
    assert len(payload["turns"]) == 2
    assert payload["turns"][0] == {
        "index": 0, "role": "user", "ts": 1718360455.0, "text": "hi",
    }
    assert payload["turns"][1]["text"] == long_text  # full text
    assert payload["turns"][1]["ts"] is None  # nullable timestamp preserved


def test_transcript_human_and_json_carry_same_turns():
    # SC-002: informational equivalence between human and JSON.
    session = _session(
        turns=(
            TranscriptTurn(index=0, role="user", text="alpha", ts=1718360455.0),
            TranscriptTurn(index=1, role="assistant", text="beta", ts=1718360461.0),
        )
    )
    human = output.format_session_transcript(session, json=False)
    payload = json.loads(output.format_session_transcript(session, json=True))
    for turn in payload["turns"]:
        assert turn["text"] in human


def test_transcript_empty_session_human_and_json():
    session = _session(turns=())
    human = output.format_session_transcript(session, json=False)
    assert "session=sess-abc" in human
    assert "turns=0" in human
    assert "(empty session)" in human
    payload = json.loads(output.format_session_transcript(session, json=True))
    assert payload["turns"] == []


# ============================================================ format_session_list (US2)


def test_list_human_indexed_with_key_date_count():
    summaries = (
        SessionSummary(session_key="sess-recent", captured_at=1718360463.0, turn_count=3),
        SessionSummary(session_key="sess-older", captured_at=1718270000.0, turn_count=12),
    )
    out = output.format_session_list(summaries, json=False)
    assert "[1] session=sess-recent" in out
    assert "[2] session=sess-older" in out
    assert "turns=3" in out
    assert "turns=12" in out
    # order preserved (the core orders recency-first; the view renders as-is)
    assert out.index("sess-recent") < out.index("sess-older")


def test_list_json_array_of_objects():
    summaries = (
        SessionSummary(session_key="sess-a", captured_at=1718360463.0, turn_count=3),
        SessionSummary(session_key="sess-b", captured_at=1718270000.0, turn_count=12),
    )
    arr = json.loads(output.format_session_list(summaries, json=True))
    assert arr == [
        {"session_key": "sess-a", "captured_at": 1718360463.0, "turn_count": 3},
        {"session_key": "sess-b", "captured_at": 1718270000.0, "turn_count": 12},
    ]


def test_list_empty_human_and_json():
    assert output.format_session_list((), json=False) == "(no sessions)"
    assert json.loads(output.format_session_list((), json=True)) == []


def test_list_human_and_json_carry_same_keys():
    # SC-002: informational equivalence.
    summaries = (
        SessionSummary(session_key="sess-a", captured_at=1718360463.0, turn_count=3),
    )
    human = output.format_session_list(summaries, json=False)
    arr = json.loads(output.format_session_list(summaries, json=True))
    assert arr[0]["session_key"] in human
