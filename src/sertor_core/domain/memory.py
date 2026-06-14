"""Domain entities for conversation memory — capture & archive (feature 031, FEAT-001).

Pure data structures, no external SDK imports (Principio I): shared by the capture port, the
service and the archive store. They model the raw episodic tier (a conversation, its turns) and
the archived unit (a session). The host-specific knowledge (where transcripts live, how a JSONL
line is shaped) is NOT here — it lives only in the capture adapter (Principio X).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionRef:
    """Lightweight reference to a session at the source (produced by `list_sessions`).

    Carries the canonical key and just enough to read the content, WITHOUT loading it (lazy).
    """

    session_key: str   # canonical key = filename stem (FR-008): drives idempotency
    project_id: str    # host project namespace (FR-010), provided by the adapter
    source_path: str   # opaque path to the source (host-specific; the service never interprets it)


@dataclass(frozen=True)
class TranscriptTurn:
    """A single conversational turn (boundary preserved, FR-013), BEFORE scrub.

    `role` is `user` or `assistant`; `ts` is nullable (absent/unreadable timestamp → `None`).
    """

    index: int                 # stable ordinal in emission order (turn idempotency)
    role: str                  # 'user' | 'assistant'
    text: str                  # turn text (NOT yet scrubbed)
    ts: float | None = None    # epoch UTC of the turn, None if absent in the source


@dataclass(frozen=True)
class TranscriptContent:
    """Structured content of a session (pre-scrub), produced by `read_session`."""

    session_key: str
    project_id: str
    adapter_kind: str                   # source adapter kind (→ sessions.adapter_kind, FR-012)
    captured_at: float                  # epoch UTC of the capture instant (FR-012)
    turns: tuple[TranscriptTurn, ...]   # turn boundaries preserved (FR-013)


@dataclass(frozen=True)
class ArchivedSession:
    """The conserved unit in the archive (post-scrub): the domain view of a persisted record.

    The `turns` content is ALREADY scrubbed. Used as a read value (tests, FEAT-002 in future);
    writes go through `MemoryArchive.upsert`.
    """

    session_key: str
    project_id: str
    captured_at: float
    adapter_kind: str
    turns: tuple[TranscriptTurn, ...]   # scrubbed
    retention_days: int | None = None   # retention hook (FR-021): recorded in metadata, not applied
