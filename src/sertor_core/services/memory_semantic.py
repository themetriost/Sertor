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
from sertor_core.domain.memory import ArchivedSession, TranscriptTurn
from sertor_core.domain.ports import EmbeddingProvider, VectorStore
from sertor_core.observability.logging import log_event
from sertor_core.services.chunking._tokens import cap_to_tokens

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
class RejectedTurn:
    """A turn the embeddings provider refused (145, REQ-035): where, and the provider's reason.

    Never carries transcript text: it feeds the user-facing report, not observability events.
    """

    session_key: str
    turn_index: int
    reason: str


@dataclass(frozen=True)
class SemanticIndexReport:
    """Outcome of one indexing/backfill run (counts, never text).

    `embedded`/`skipped`/`errors` count TURNS (a split turn counts once). `rejected` details the
    turns the provider refused (⊆ errors); `errors − len(rejected)` were lost to an unavailable
    provider/store.
    """

    embedded: int = 0
    skipped: int = 0
    errors: int = 0
    rejected: tuple[RejectedTurn, ...] = ()


@dataclass(frozen=True)
class _Unit:
    """One embeddable unit of a turn: the whole turn, or one piece of an oversized turn (145)."""

    chunk_id: str
    text: str
    part: int | None = None
    parts: int | None = None


# Provider reasons that mean «this input was refused», not «the service is unavailable» (145,
# REQ-034): only these trigger the turn-by-turn fallback. Auth/config errors (401/403/404) would
# fail for every turn, so retrying them one by one only multiplies doomed calls.
_INPUT_REJECTION_REASONS = frozenset({"http 400", "http 413", "http 422"})


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
            # Over-fetch so the per-turn dedup and the post-query time filter still have
            # candidates to keep (pieces of a split turn compete for the same slots — 145).
            results = self._store.query(
                self._collection, vectors[0], k=2 * max(query.limit, 1)
            )
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
        At most one hit per turn (145, FR-003): the pieces of a split turn collapse onto the first
        one met, which is the most relevant because the store returns them by score.
        """
        hits: list[SemanticMemoryHit] = []
        seen: set[tuple[str, int]] = set()
        for result in results:
            payload = result.metadata or {}
            try:
                captured_at = float(payload["captured_at"])
                if query.since is not None and captured_at < query.since:
                    continue
                if query.until is not None and captured_at > query.until:
                    continue
                turn_ref = (str(payload["session_key"]), int(payload["turn_index"]))
                if turn_ref in seen:
                    continue
                seen.add(turn_ref)
                hits.append(
                    SemanticMemoryHit(
                        session_key=turn_ref[0],
                        turn_index=turn_ref[1],
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
        """Embed the session's NEW turns and upsert them (contract §index_session, delta 145).

        Each turn becomes its units (`_turn_units`): the whole turn when it fits
        `max_chunk_tokens`, else the pieces of `cap_to_tokens` — the same cap the corpus applies.
        A turn is skipped when ALL its unit ids are already in the collection (incrementality via
        store state — DA-SS-4); a fully-indexed session → `embedded=0, skipped=N` with ZERO
        embedding calls (NFR-009). The new units go to the provider in ONE call; if the provider
        refuses an input (`_INPUT_REJECTION_REASONS`) the session falls back to one call per unit
        so that only the refused turns are lost (REQ-034). Any other outage → every new turn is a
        counted error + warning, non-fatal (REQ-008/REQ-006).
        """
        turns = session.turns
        if not turns:
            return SemanticIndexReport()
        units = {turn.index: self._turn_units(session, turn) for turn in turns}
        try:
            already = self._existing_ids(units)
        except VectorStoreError as exc:
            log_event(
                logging.WARNING, "memory_semantic_index_failed",
                reason="store_unavailable", detail=exc.reason,
            )
            return SemanticIndexReport(errors=len(turns))

        new_turns = [
            turn
            for turn in turns
            if any(unit.chunk_id not in already for unit in units[turn.index])
        ]
        skipped = len(turns) - len(new_turns)
        if not new_turns:
            return SemanticIndexReport(embedded=0, skipped=skipped, errors=0)

        pairs = [(turn, unit) for turn in new_turns for unit in units[turn.index]]
        try:
            vectors = self._embedder.embed([unit.text for _, unit in pairs])
        except EmbeddingError as exc:
            if exc.reason not in _INPUT_REJECTION_REASONS:
                log_event(
                    logging.WARNING, "memory_semantic_index_failed",
                    reason="provider_unavailable", detail=exc.reason,
                )
                return SemanticIndexReport(embedded=0, skipped=skipped, errors=len(new_turns))
            return self._index_turn_by_turn(session, new_turns, units, skipped)

        records = [
            self._record(session, turn, unit, vector)
            for (turn, unit), vector in zip(pairs, vectors, strict=False)
        ]
        return self._upsert(records, embedded=len(new_turns), skipped=skipped)

    def _index_turn_by_turn(
        self,
        session: ArchivedSession,
        new_turns: list[TranscriptTurn],
        units: dict[int, list[_Unit]],
        skipped: int,
    ) -> SemanticIndexReport:
        """Fallback after an input rejection: one call per unit, turn by turn (145, REQ-034).

        A turn is written all-or-nothing (FR-005): if any of its units is refused, none of its
        records reach the store, so the next run retries the whole turn. A non-rejection error met
        here (the service went down meanwhile) stops the fallback: the turns not yet handled are
        counted as errors with `provider_unavailable`, as on the normal path.
        """
        records: list[EmbeddedChunk] = []
        rejected: list[RejectedTurn] = []
        embedded = 0
        unavailable = 0
        for position, turn in enumerate(new_turns):
            turn_records: list[EmbeddedChunk] = []
            try:
                for unit in units[turn.index]:
                    vector = self._embedder.embed([unit.text])[0]
                    turn_records.append(self._record(session, turn, unit, vector))
            except EmbeddingError as exc:
                if exc.reason not in _INPUT_REJECTION_REASONS:
                    unavailable = len(new_turns) - position
                    log_event(
                        logging.WARNING, "memory_semantic_index_failed",
                        reason="provider_unavailable", detail=exc.reason,
                    )
                    break
                rejected.append(RejectedTurn(session.session_key, turn.index, exc.reason))
                continue
            records.extend(turn_records)
            embedded += 1
        if rejected:
            log_event(
                logging.WARNING, "memory_semantic_index_failed",
                reason="input_rejected",
                detail=",".join(sorted({r.reason for r in rejected})),
                rejected=len(rejected),
            )
        written = self._upsert(records, embedded=embedded, skipped=skipped)
        return SemanticIndexReport(
            embedded=written.embedded,
            skipped=skipped,
            errors=written.errors + len(rejected) + unavailable,
            rejected=tuple(rejected),
        )

    def _upsert(
        self, records: list[EmbeddedChunk], *, embedded: int, skipped: int
    ) -> SemanticIndexReport:
        """Write the records; a store outage turns the `embedded` turns into counted errors."""
        if not records:
            return SemanticIndexReport(embedded=0, skipped=skipped, errors=0)
        try:
            self._store.upsert(self._collection, records)
        except VectorStoreError as exc:
            log_event(
                logging.WARNING, "memory_semantic_index_failed",
                reason="store_unavailable", detail=exc.reason,
            )
            return SemanticIndexReport(embedded=0, skipped=skipped, errors=embedded)
        return SemanticIndexReport(embedded=embedded, skipped=skipped, errors=0)

    def _turn_units(self, session: ArchivedSession, turn: TranscriptTurn) -> list[_Unit]:
        """The embeddable units of a turn (145, REQ-033).

        Within `max_chunk_tokens` → one unit with the historical id `session_key#turn_index`
        (indexes built before 145 stay valid). Above it → the pieces of `cap_to_tokens`, with ids
        `session_key#turn_index/part`: deterministic for a given text and budget (Principio VI).
        """
        base_id = f"{session.session_key}#{turn.index}"
        pieces = cap_to_tokens(
            turn.text, self._settings.max_chunk_tokens, self._settings.chunk_overlap
        )
        if len(pieces) <= 1:
            return [_Unit(chunk_id=base_id, text=turn.text)]
        return [
            _Unit(chunk_id=f"{base_id}/{part}", text=piece, part=part, parts=len(pieces))
            for part, piece in enumerate(pieces)
        ]

    @staticmethod
    def _record(
        session: ArchivedSession, turn: TranscriptTurn, unit: _Unit, vector: list[float]
    ) -> EmbeddedChunk:
        """The store record of a unit; a piece carries `part`/`parts` on top of the turn fields."""
        payload = {
            "text": unit.text,
            "session_key": session.session_key,
            "turn_index": turn.index,
            "captured_at": session.captured_at,
            "role": turn.role,
        }
        if unit.parts is not None:
            payload["part"] = unit.part
            payload["parts"] = unit.parts
        return EmbeddedChunk(chunk_id=unit.chunk_id, vector=vector, payload=payload)

    def index_all(self, archive: MemoryArchive) -> SemanticIndexReport:
        """Incremental backfill over every archived session (contract §index_all).

        Iterates the archived sessions and runs `index_session` on each; aggregates the reports
        (rejected turns included, in session order). Embeds only the not-yet-indexed turns
        (incrementality between runs). Does NOT re-archive anything (REQ-029: the index is
        derived, the raw archive is intact). Emits `memory_semantic_index` (metrics-only) —
        non-fatal.
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
                rejected=total.rejected + report.rejected,
            )
        latency_ms = (time.monotonic() - start) * 1000.0
        self._emit_index_event(total, latency_ms)
        return total

    def _existing_ids(self, units: dict[int, list[_Unit]]) -> set[str]:
        """The unit ids of a session already present in the collection (incrementality probe).

        Watermark = state of the store (DA-SS-4, Opzione 3): «already indexed» ⇔ the unit's
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
        ids = [unit.chunk_id for turn_units in units.values() for unit in turn_units]
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
                rejected=len(report.rejected),
                provider=self._embedder.name,
                latency_ms=round(latency_ms, 3),
            )
        except Exception as exc:  # noqa: BLE001 — observability must never break the run.
            _LOGGER.debug("memory_semantic_index event emission failed: %s", exc)
