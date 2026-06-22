"""GitHub Copilot CLI transcript capture adapter (FEAT-008, host-specific — Principio X).

The SECOND implementation of the `TranscriptCaptureAdapter` port, mirroring `claude_code.py`. ALL
the host-specific Copilot knowledge lives here and ONLY here: where Copilot CLI stores sessions
(`<copilot_session_dir>/<uuid>/events.jsonl`), the `events.jsonl` event shape (`type`/`data`/
`timestamp`), which events are dialog turns (`user.message`/`assistant.message`) and how a session
is associated to a project (`session.start` → `data.context.cwd`/`gitRoot`). The service and the
domain never see any of this (FR-017, SC-003).

Verified against Copilot CLI **1.0.63** (reconnaissance 2026-06-22). The `events.jsonl` format is an
internal Copilot detail, NOT a contract (NFR-006): the parser is defensive/best-effort (D3, parità
Claude) — a non-JSON/empty line is skipped (the latter silently), an unreadable source yields empty,
an unknown `type` is dropped, never fatal. The source is read-only. stdlib-only.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from sertor_core.domain.memory import SessionRef, TranscriptContent, TranscriptTurn
from sertor_core.observability.logging import log_event

# The ONLY place that knows Copilot event `type` → turn role (host-specific vocabulary, confined to
# this module — DA-CM-1). Every other `type` is absent from the dict → automatically dropped
# (`system.message`/`tool.*`/`hook.*`/`session.*`/`permission.*`/`subagent.*`/`assistant.turn_*`).
_TURN_EVENT_ROLES = {"user.message": "user", "assistant.message": "assistant"}

# The event that carries the project association (cwd/gitRoot) for `list_sessions`.
_SESSION_START_EVENT = "session.start"


class CopilotCliCaptureAdapter:
    """`TranscriptCaptureAdapter` over Copilot CLI's `<uuid>/events.jsonl` session-state folders."""

    kind = "copilot-cli"

    def __init__(self, session_dir: Path | str, project_id: str):
        self._dir = Path(session_dir)
        self._project_id = project_id

    def list_sessions(self) -> list[SessionRef]:
        """`SessionRef` per UUID subfolder whose session belongs to the current project.

        Source absent → `[]` + warning `memory_capture_source_absent`, never an error (FR-019). For
        each `<uuid>/events.jsonl` the first `session.start` gives `(cwd, gitRoot)`; the session is
        included only if `_paths_match` (path-containment, DA-CM-4). A session with no readable
        `session.start` / no cwd-gitRoot → skip + warning `memory_capture_session_unassociated`
        (no misattribution — REQ-010, DA-CM-2). `session_key` = the UUID folder name (stable id →
        idempotence, REQ-005).
        """
        if not self._dir.is_dir():
            log_event(logging.WARNING, "memory_capture_source_absent",
                      adapter_kind=self.kind, source=str(self._dir))
            return []

        refs: list[SessionRef] = []
        for uuid_dir in sorted(self._dir.iterdir()):
            if not uuid_dir.is_dir():
                continue
            events_path = uuid_dir / "events.jsonl"
            if not events_path.is_file():
                continue
            try:
                cwd, git_root = _session_context(events_path)
            except OSError as exc:
                log_event(logging.WARNING, "memory_capture_unreadable",
                          session_key=uuid_dir.name, reason=type(exc).__name__)
                continue
            if cwd is None and git_root is None:
                log_event(logging.WARNING, "memory_capture_session_unassociated",
                          session_key=uuid_dir.name, adapter_kind=self.kind)
                continue
            if not _paths_match(self._project_id, cwd, git_root):
                continue  # session of another project → skip silently
            refs.append(SessionRef(
                session_key=uuid_dir.name,
                project_id=self._project_id,
                source_path=str(events_path),
            ))
        return refs

    def read_session(self, ref: SessionRef) -> TranscriptContent:
        """Read `events.jsonl` line-by-line (best-effort), extracting user/assistant turns (D3).

        Empty/non-JSON lines are skipped (the latter with a warning). Non-dialog events
        (session/tool/hook/...) and turns with no extractable text are ignored. Zero turns → `()`.
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


def _session_context(events_path: Path) -> tuple[str | None, str | None]:
    """Find the first `session.start` event → `(cwd, gitRoot)`, or `(None, None)` if absent.

    Reads line-by-line until the first `session.start`; malformed lines are skipped. Missing context
    fields → `None`. May raise `OSError` (handled by the caller); no other exception escapes.
    """
    raw_lines = events_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != _SESSION_START_EVENT:
            continue
        data = event.get("data")
        context = data.get("context") if isinstance(data, dict) else None
        if not isinstance(context, dict):
            return (None, None)
        cwd = context.get("cwd")
        git_root = context.get("gitRoot")
        return (
            cwd if isinstance(cwd, str) and cwd else None,
            git_root if isinstance(git_root, str) and git_root else None,
        )
    return (None, None)


def _paths_match(project_id: str, cwd: str | None, git_root: str | None) -> bool:
    """True if the Copilot session belongs to the current project (DA-CM-4).

    Two asymmetric slots, both path-containment (normalized, case-insensitive on Windows — purely
    lexical, testable offline with synthetic paths, RNF-4):
    - `cwd` matches if it is **within-or-equal** to the project (the session was started inside the
      project); a `cwd` that is an *ancestor* of the project (the whole repo while we run from a
      subfolder) does NOT match — it would over-attribute the repo's sessions to the subproject.
    - `git_root` matches if it is an **ancestor-or-equal** of the project (the session's repo
      contains the current project); this lets a session opened in a subfolder match via gitRoot.

    `cwd=None` and `git_root=None` → `False`.
    """
    if cwd is not None and _within(cwd, project_id):
        return True
    if git_root is not None and _within(project_id, git_root):
        return True
    return False


def _within(child: str, parent: str) -> bool:
    """True if `child` is `parent` or a descendant (normalized, case-insensitive on Windows)."""
    c, p = _normalize(child), _normalize(parent)
    return c == p or c.startswith(p + os.sep)


def _normalize(path: str) -> str:
    """Normalize a path for containment compare (case-insensitive on Windows, no trailing sep)."""
    return os.path.normcase(os.path.normpath(path))


def _turn_from_event(event: dict, index: int) -> TranscriptTurn | None:
    """Build a turn from a `user.message`/`assistant.message` event, or `None` (DA-CM-1).

    Text = `data.content` (NEVER `transformedContent` — that is system-reminder injection, not the
    dialog). `data.toolRequests` are ignored (not turns, FR-009). Empty/whitespace/non-string
    `content` → `None` (turn skipped). Missing `data` → `None`.
    """
    role = _TURN_EVENT_ROLES.get(event.get("type"))
    if role is None:
        return None
    data = event.get("data")
    if not isinstance(data, dict):
        return None
    content = data.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return TranscriptTurn(
        index=index,
        role=role,
        text=content.strip(),
        ts=_parse_timestamp(event.get("timestamp")),
    )


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


def _parse_timestamp(raw: object) -> float | None:
    """ISO-8601 timestamp → epoch float, or `None` if absent/unreadable (not an error, D3)."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None
