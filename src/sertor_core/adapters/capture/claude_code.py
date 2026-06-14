"""Claude Code transcript capture adapter (feature 031, host-specific — Principio X).

The FIRST implementation of the `TranscriptCaptureAdapter` port. ALL the host-specific knowledge
lives here and ONLY here: where Claude Code stores sessions (`<projects>/<encoded-cwd>/<id>.jsonl`),
the project-path encoding, the JSONL line shape (`type`, `message.role`, `content` blocks), the
block kinds we keep (`text`/`thinking`) and the timestamp format. The service and the domain never
see any of this (FR-005, SC-005).

Defensive, best-effort parsing (D3): a non-JSON/empty line is skipped with a warning, never fatal;
an absent source returns `[]` with a warning. The source is read-only (FR-007). stdlib-only.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from sertor_core.domain.memory import SessionRef, TranscriptContent, TranscriptTurn
from sertor_core.observability.logging import log_event

# JSONL event/content shapes we understand (host-specific vocabulary, confined to this module).
_TURN_ROLES = ("user", "assistant")
_TEXT_BLOCK_KINDS = ("text", "thinking")


def encode_project_path(project_path: str) -> str:
    """Encode an absolute project path the way Claude Code names its project folder.

    Separators (`\\`, `/`) and the drive colon collapse to `-`, e.g.
    `C:\\Workspace\\Git\\Sertor` → `C--Workspace-Git-Sertor`. Confined here (Principio X): the
    composition root passes the project's cwd, this module knows the encoding.
    """
    return project_path.replace(":", "-").replace("\\", "-").replace("/", "-")


class ClaudeCodeCaptureAdapter:
    """`TranscriptCaptureAdapter` over Claude Code's `<encoded-project>/<session>.jsonl` files."""

    kind = "claude-code"

    def __init__(self, project_source_dir: Path | str, project_id: str):
        self._dir = Path(project_source_dir)
        self._project_id = project_id

    def list_sessions(self) -> list[SessionRef]:
        """`SessionRef` per `*.jsonl` in the project folder (`session_key` = filename stem).

        Source absent → `[]` + warning `memory_capture_source_absent`, never an error (FR-006/007).
        """
        if not self._dir.is_dir():
            log_event(logging.WARNING, "memory_capture_source_absent",
                      adapter_kind=self.kind, source=str(self._dir))
            return []
        return [
            SessionRef(
                session_key=path.stem,
                project_id=self._project_id,
                source_path=str(path),
            )
            for path in sorted(self._dir.glob("*.jsonl"))
            if path.is_file()
        ]

    def read_session(self, ref: SessionRef) -> TranscriptContent:
        """Read a session file line-by-line (best-effort), extracting user/assistant turns (D3).

        Empty/non-JSON lines are skipped (the latter with a warning). Non-turn events
        (system/tool/...) and turns with no extractable text are ignored. Zero turns → `turns=()`.
        """
        turns: list[TranscriptTurn] = []
        captured_at = self._source_mtime(ref.source_path)
        path = Path(ref.source_path)
        try:
            raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            log_event(logging.WARNING, "memory_capture_unreadable",
                      session_key=ref.session_key, reason=type(exc).__name__)
            raw_lines = []

        for lineno, line in enumerate(raw_lines, start=1):
            event = _parse_line(line, ref.session_key, lineno)
            if event is None:
                continue
            turn = _turn_from_event(event, index=len(turns))
            if turn is not None:
                turns.append(turn)

        return TranscriptContent(
            session_key=ref.session_key,
            project_id=ref.project_id,
            adapter_kind=self.kind,
            captured_at=captured_at,
            turns=tuple(turns),
        )

    @staticmethod
    def _source_mtime(source_path: str) -> float:
        """Capture instant = source file mtime; fall back to 0.0 if the file is gone."""
        try:
            return Path(source_path).stat().st_mtime
        except OSError:
            return 0.0


def _parse_line(line: str, session_key: str, lineno: int) -> dict | None:
    """Parse one JSONL line → dict, or `None` to skip (empty silent, non-JSON warned, D3)."""
    stripped = line.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        log_event(logging.WARNING, "memory_capture_unparsable_line",
                  session_key=session_key, line=lineno)
        return None
    return parsed if isinstance(parsed, dict) else None


def _turn_from_event(event: dict, index: int) -> TranscriptTurn | None:
    """Build a `TranscriptTurn` from a `user`/`assistant` event, or `None` if it is not a turn."""
    if event.get("type") not in _TURN_ROLES:
        return None
    message = event.get("message")
    if not isinstance(message, dict):
        return None
    role = message.get("role")
    if role not in _TURN_ROLES:
        return None
    text = _extract_text(message.get("content"))
    if not text:
        return None
    return TranscriptTurn(
        index=index,
        role=role,
        text=text,
        ts=_parse_timestamp(event.get("timestamp")),
    )


def _extract_text(content: object) -> str:
    """Concatenate the textual blocks of a message's content (str or list of blocks)."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") not in _TEXT_BLOCK_KINDS:
            continue
        value = block.get(block["type"])  # 'text' block → block['text']; 'thinking' → ['thinking']
        if isinstance(value, str) and value:
            parts.append(value)
    return "\n".join(parts)


def _parse_timestamp(raw: object) -> float | None:
    """ISO-8601 timestamp → epoch float, or `None` if absent/unreadable (not an error, D3)."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None
