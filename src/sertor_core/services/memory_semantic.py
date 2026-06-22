"""Optional semantic search over the memory archive (072, FEAT-004).

Makes the transcript archive produced by FEAT-001 (`<index_dir>/memory.sqlite`) *queryable by
meaning* — the lexical-only floor of the FTS5 episodic search (FEAT-002) misses paraphrases and
conceptual matches. Technical approach (plan.md): a DEDICATED vector store that REUSES ONLY the
core primitives (`build_embedder`/`build_store`/`collection_name`, wired in composition); it does
NOT reuse `IndexingService.index()` nor the FEAT-009 manifest.

Concrete component, NO new port (single consumer/backend today — same profile as `MemoryArchive`
and `EpisodicSearch`, Principio III/YAGNI). It depends only on the `EmbeddingProvider`/`VectorStore`
ports + existing entities/errors (Principio I): the concrete choices live in `composition.py`.

Granularity = TURN (`chunk_id = f"{session_key}#{turn_index}"`, stable/deterministic — Princ. VI):
re-processing the same turn produces the same id → `upsert` idempotent, no dupes. Incrementality
has NO own registry (DA-SS-4, Opzione 3): «already indexed» ⇔ the turn's `chunk_id` exists in the
collection; only the new turns are embedded. A provider change → a different `embedder.name` → a
different collection name → an implicit rebuild (REQ-032).

Degradation is non-fatal everywhere except an impossible time window (`since > until` →
`InvalidTimeWindowError`, Principio IV/parity with FEAT-002): a missing/empty collection, a provider
outage, a malformed unit — all degrade to an explicit empty state / a counted error + warning, never
a crash (REQ-021/022/023). Host-agnostic (Principio X): operates on `memory.sqlite`, never branching
on the assistant. Observability is metrics-only (REQ-026/027): the query is hashed, never in clear,
and transcript text/snippets/single keys never reach the event.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass

from sertor_core.adapters.memory.archive import MemoryArchive
from sertor_core.config.settings import Settings
from sertor_core.domain.entities import EmbeddedChunk
from sertor_core.domain.errors import EmbeddingError, InvalidTimeWindowError, VectorStoreError
from sertor_core.domain.memory import ArchivedSession
from sertor_core.domain.ports import EmbeddingProvider, VectorStore
from sertor_core.observability.logging import log_event

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SemanticMemoryQuery:
    """Input of a semantic memory search (data-model.md). The semantic path ALWAYS orders by
    similarity (REQ-009): no `order` field. `since`/`until` are epoch-UTC bounds on the session's
    `captured_at` (`None` = open), applied post-query. `since > until` → `InvalidTimeWindowError`.
    """

    text: str
    since: float | None = None
    until: float | None = None
    limit: int = 20


@dataclass(frozen=True)
class SemanticMemoryHit:
    """A matching turn enriched with its citation (REQ-010). Carries the six required fields.

    `score` = `RetrievalResult.score` (cosine similarity, higher = more relevant). `snippet` is the
    turn's text (already scrubbed by FEAT-001, A-007).
    """

    session_key: str
    turn_index: int
    captured_at: float
    role: str
    snippet: str
    score: float


@dataclass(frozen=True)
class SemanticMemoryResults:
    """Explicit outcome of a semantic search (avoids an ambiguous `None`, Principio IV).

    `hits=()` = explicit empty state (no match / index absent / provider outage — all legitimate,
    NOT errors at the core level). `latency_ms` feeds observability.
    """

    hits: tuple[SemanticMemoryHit, ...]
    latency_ms: float


@dataclass(frozen=True)
class SemanticIndexReport:
    """Outcome of one indexing/backfill run (counts, never text)."""

    embedded: int = 0
    skipped: int = 0
    errors: int = 0


class MemorySemanticIndex:
    """Dedicated semantic index over the memory archive (concrete, NO port — Principio III).

    Wraps an `EmbeddingProvider` + a `VectorStore` + an isolated collection name. `search` embeds
    the query and ranks turns by similarity; `index_session`/`index_all` embed only the new turns
    (incrementality via store state). Everything degrades non-fatally.
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection: str,
        settings: Settings,
    ):
        self._embedder = embedder
        self._store = store
        self._collection = collection
        self._settings = settings

    # --- search ----------------------------------------------------------------------------------

    def search(self, query: SemanticMemoryQuery) -> SemanticMemoryResults:
        """Semantic search over the memory collection (contract `memory.semantic/1` §search).

        Empty/whitespace query → empty state. `since > until` → `InvalidTimeWindowError`. Index
        absent / collection empty → `hits=()` + warning (`index_absent`), NOT an error (REQ-021).
        Provider outage / store outage → empty state + warning, the caller never crashes (REQ-022).
        Malformed records are skipped with a warning (REQ-023). Emits `memory_semantic_search`
        (metrics-only, query HASHED) — non-fatal (REQ-028).
        """
        start = time.monotonic()
        if not query.text.strip():
            return SemanticMemoryResults(hits=(), latency_ms=0.0)
        if query.since is not None and query.until is not None and query.since > query.until:
            raise InvalidTimeWindowError(query.since, query.until)

        hits = self._run_search(query)
        latency_ms = (time.monotonic() - start) * 1000.0
        results = SemanticMemoryResults(hits=hits, latency_ms=latency_ms)
        self._emit_search_event(query, results)
        return results

    def _run_search(self, query: SemanticMemoryQuery) -> tuple[SemanticMemoryHit, ...]:
        """Embed the query, query the store, map + time-filter the hits. Non-fatal degradation."""
        if not self._store.exists(self._collection):
            log_event(
                logging.WARNING, "memory_semantic_unavailable", reason="index_absent",
            )
            return ()
        try:
            vectors = self._embedder.embed([query.text])
        except EmbeddingError as exc:
            log_event(
                logging.WARNING, "memory_semantic_unavailable",
                reason="provider_unavailable", detail=exc.reason,
            )
            return ()
        if not vectors:
            return ()
        try:
            # Over-fetch a little so the post-query time filter still has candidates to keep.
            results = self._store.query(self._collection, vectors[0], k=max(query.limit, 1))
        except VectorStoreError as exc:
            log_event(
                logging.WARNING, "memory_semantic_unavailable",
                reason="store_unavailable", detail=exc.reason,
            )
            return ()
        return self._results_to_hits(results, query)

    def _results_to_hits(
        self, results, query: SemanticMemoryQuery
    ) -> tuple[SemanticMemoryHit, ...]:
        """Map `RetrievalResult`s → `SemanticMemoryHit`, apply the time window, cut to `limit`.

        A record with a missing/malformed payload is skipped with a warning (REQ-023); the valid
        ones are still served. The time window filters on the payload's `captured_at` (post-query).
        """
        hits: list[SemanticMemoryHit] = []
        for result in results:
            payload = result.metadata or {}
            try:
                captured_at = float(payload["captured_at"])
                if query.since is not None and captured_at < query.since:
                    continue
                if query.until is not None and captured_at > query.until:
                    continue
                hits.append(
                    SemanticMemoryHit(
                        session_key=str(payload["session_key"]),
                        turn_index=int(payload["turn_index"]),
                        captured_at=captured_at,
                        role=str(payload["role"]),
                        snippet=str(payload.get("text", result.text)),
                        score=float(result.score),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                log_event(
                    logging.WARNING, "memory_semantic_bad_row", reason=type(exc).__name__,
                )
        return tuple(hits[: query.limit])

    # --- indexing --------------------------------------------------------------------------------

    def index_session(self, session: ArchivedSession) -> SemanticIndexReport:
        """Embed the session's NEW turns and upsert them (contract §index_session).

        `chunk_id = f"{session_key}#{turn_index}"`. Turns whose id is already in the collection are
        skipped (incrementality via store state — DA-SS-4). A fully-indexed session → `embedded=0,
        skipped=N` with ZERO embedding calls (NFR-009). A store/provider outage → a counted error +
        warning, non-fatal (REQ-008/REQ-006).
        """
        turns = session.turns
        if not turns:
            return SemanticIndexReport()
        try:
            already = self._existing_ids(session)
        except VectorStoreError as exc:
            log_event(
                logging.WARNING, "memory_semantic_index_failed",
                reason="store_unavailable", detail=exc.reason,
            )
            return SemanticIndexReport(errors=len(turns))

        new_turns = [
            turn
            for turn in turns
            if f"{session.session_key}#{turn.index}" not in already
        ]
        skipped = len(turns) - len(new_turns)
        if not new_turns:
            return SemanticIndexReport(embedded=0, skipped=skipped, errors=0)

        try:
            vectors = self._embedder.embed([turn.text for turn in new_turns])
        except EmbeddingError as exc:
            log_event(
                logging.WARNING, "memory_semantic_index_failed",
                reason="provider_unavailable", detail=exc.reason,
            )
            return SemanticIndexReport(embedded=0, skipped=skipped, errors=len(new_turns))

        records = [
            EmbeddedChunk(
                chunk_id=f"{session.session_key}#{turn.index}",
                vector=vector,
                payload={
                    "text": turn.text,
                    "session_key": session.session_key,
                    "turn_index": turn.index,
                    "captured_at": session.captured_at,
                    "role": turn.role,
                },
            )
            for turn, vector in zip(new_turns, vectors, strict=False)
        ]
        try:
            self._store.upsert(self._collection, records)
        except VectorStoreError as exc:
            log_event(
                logging.WARNING, "memory_semantic_index_failed",
                reason="store_unavailable", detail=exc.reason,
            )
            return SemanticIndexReport(embedded=0, skipped=skipped, errors=len(new_turns))
        return SemanticIndexReport(embedded=len(records), skipped=skipped, errors=0)

    def index_all(self, archive: MemoryArchive) -> SemanticIndexReport:
        """Incremental backfill over every archived session (contract §index_all).

        Iterates the archived sessions and runs `index_session` on each; aggregates the reports.
        Embeds only the not-yet-indexed turns (incrementality between runs). Does NOT re-archive
        anything (REQ-029: the index is derived, the raw archive is intact). Emits
        `memory_semantic_index` (metrics-only) — non-fatal.
        """
        start = time.monotonic()
        total = SemanticIndexReport()
        for summary in archive.list_recent(self._backfill_limit()):
            session = archive.get(summary.session_key)
            if session is None:
                continue
            report = self.index_session(session)
            total = SemanticIndexReport(
                embedded=total.embedded + report.embedded,
                skipped=total.skipped + report.skipped,
                errors=total.errors + report.errors,
            )
        latency_ms = (time.monotonic() - start) * 1000.0
        self._emit_index_event(total, latency_ms)
        return total

    def _existing_ids(self, session: ArchivedSession) -> set[str]:
        """The turn ids of `session` already present in the collection (incrementality probe).

        Watermark = state of the store (DA-SS-4, Opzione 3): «already indexed» ⇔ the turn's
        `chunk_id` exists in the collection. The `VectorStore` port has no id enumeration; rather
        than widen it (Principio III), this probes a NARROW, optional duck-typed capability
        `contains_ids(collection, ids) -> Iterable[str]`. If the concrete store provides it, only
        the genuinely-new turns are embedded → ZERO embedding calls on a fully-indexed session
        (NFR-009).
        If absent, the set degrades to empty (every turn looks new) and `upsert` idempotency on the
        stable ids still prevents duplicates (REQ-006) — correctness is preserved, the optimisation
        is best-effort. A store outage propagates as `VectorStoreError` (handled by the caller).
        """
        probe = getattr(self._store, "contains_ids", None)
        if probe is None:
            return set()
        ids = [f"{session.session_key}#{turn.index}" for turn in session.turns]
        return set(probe(self._collection, ids))

    def _backfill_limit(self) -> int:
        """Upper bound on sessions scanned during a backfill — large enough to cover the archive.

        FEAT-001's `list_recent` takes a limit; the backfill wants every session. We pass a large
        sentinel; the archive returns fewer if there are fewer (non-fatal, recency-ordered).
        """
        return 1_000_000

    # --- observability (metrics-only, REQ-026/027) -----------------------------------------------

    def _emit_search_event(
        self, query: SemanticMemoryQuery, results: SemanticMemoryResults
    ) -> None:
        """Emit `memory_semantic_search` — query HASHED, never in clear (REQ-027). Non-fatal."""
        try:
            query_hash = hashlib.sha256(query.text.encode()).hexdigest()[:16]
            log_event(
                logging.INFO, "memory_semantic_search",
                query_hash=query_hash,
                query_len=len(query.text),
                since=query.since,
                until=query.until,
                limit=query.limit,
                results=len(results.hits),
                latency_ms=round(results.latency_ms, 3),
            )
        except Exception as exc:  # noqa: BLE001 — observability must never break the search.
            _LOGGER.debug("memory_semantic_search event emission failed: %s", exc)

    def _emit_index_event(self, report: SemanticIndexReport, latency_ms: float) -> None:
        """Emit `memory_semantic_index` — counts + provider only, never text (REQ-026). Nonfatal."""
        try:
            log_event(
                logging.INFO, "memory_semantic_index",
                embedded=report.embedded,
                skipped=report.skipped,
                errors=report.errors,
                provider=self._embedder.name,
                latency_ms=round(latency_ms, 3),
            )
        except Exception as exc:  # noqa: BLE001 — observability must never break the run.
            _LOGGER.debug("memory_semantic_index event emission failed: %s", exc)
