"""Transcript archiving service (feature 031, contract `memory.archive-service/1`).

Orchestrates the deterministic flow: discovery → read → **scrub** → idempotent upsert. Depends ONLY
on abstractions (the `TranscriptCaptureAdapter` port, the concrete `MemoryArchive`, the pure
`scrub_text`, `Settings`); wired in composition (FR-026). Host-agnostic: it never inspects the
adapter identity — no `if adapter is ClaudeCode` branch (FR-005, SC-005).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.config.settings import Settings
from sertor_core.domain.memory import ArchivedSession, TranscriptTurn
from sertor_core.domain.ports import TranscriptCaptureAdapter
from sertor_core.observability.logging import log_event
from sertor_core.observability.scrub import scrub_text


@dataclass
class ArchiveRunReport:
    """Outcome of one `archive_all()` run (counts, never secrets)."""

    archived: int = 0
    skipped: int = 0
    errors: int = 0


class MemoryArchiveService:
    """Archive every discoverable session, idempotently and privacy-safe."""

    def __init__(
        self,
        adapter: TranscriptCaptureAdapter,
        archive: MemoryArchive,
        settings: Settings,
    ):
        self._adapter = adapter
        self._archive = archive
        self._settings = settings

    def archive_all(self) -> ArchiveRunReport:
        """Discover, scrub, archive sessions. Idempotent; degrades non-fatally (guard clauses)."""
        report = ArchiveRunReport()
        for ref in self._adapter.list_sessions():
            if self._archive.exists(ref.session_key):
                log_event(logging.INFO, "memory_session_skipped",
                          session_key=ref.session_key, project_id=ref.project_id)
                report.skipped += 1
                continue

            content = self._adapter.read_session(ref)
            if not content.turns:
                log_event(logging.INFO, "memory_session_skipped",
                          session_key=ref.session_key, project_id=ref.project_id, reason="empty")
                report.skipped += 1
                continue

            scrubbed = tuple(self._scrub_turn(turn) for turn in content.turns)
            session = ArchivedSession(
                session_key=content.session_key,
                project_id=content.project_id,
                captured_at=content.captured_at,
                adapter_kind=content.adapter_kind,
                turns=scrubbed,
                retention_days=self._settings.memory_retention_days,
            )
            if not self._archive.upsert(session):
                # Store failure (or a race that made it already-present): no new record, no
                # `archived` event — only the store's own warning. The run continues (FR-025).
                report.skipped += 1
                continue

            log_event(logging.INFO, "memory_session_archived",
                      session_key=session.session_key, project_id=session.project_id,
                      adapter_kind=session.adapter_kind,
                      content_size=sum(len(t.text) for t in scrubbed),
                      turn_count=len(scrubbed), is_new=True)
            report.archived += 1
        return report

    def _scrub_turn(self, turn: TranscriptTurn) -> TranscriptTurn:
        """Scrub a turn's text before persisting; nothing else is ever written (FR-017/027)."""
        return TranscriptTurn(
            index=turn.index,
            role=turn.role,
            text=scrub_text(turn.text, self._settings.memory_scrub_patterns),
            ts=turn.ts,
        )
