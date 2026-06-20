"""Domain exceptions for the core (Principio IV: explicit errors, no silent None).

Third-party errors (provider/store SDKs) must be **wrapped** in these exceptions at the
adapter boundary, so the core never exposes external types. A legitimate absence (unreadable
file, empty index) is NOT an error: handle it with a warning + continuation / empty result,
not by raising these exceptions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # forward ref only — avoid importing the services layer into `domain`
    from sertor_core.services.eval.models import RegressionVerdict


class SertorError(Exception):
    """Root of all Sertor domain exceptions."""


class ConfigError(SertorError):
    """Missing or inconsistent configuration."""

    def __init__(self, message: str, *, key: str | None = None):
        self.key = key
        super().__init__(message if key is None else f"{message} (key: {key})")


class IngestionError(SertorError):
    """The repository root is not accessible or is not a valid directory."""

    def __init__(self, message: str, *, path: str | None = None):
        self.path = path
        super().__init__(message if path is None else f"{message} (path: {path})")


class EmbeddingError(SertorError):
    """The embedding provider is unavailable or returned an error (REQ-015).

    Exposes provider, reason, and retriability so the caller can make an informed decision.
    """

    def __init__(self, message: str, *, provider: str, reason: str, retriable: bool):
        self.provider = provider
        self.reason = reason
        self.retriable = retriable
        super().__init__(
            f"{message} [provider={provider}, reason={reason}, retriable={retriable}]"
        )


class VectorStoreError(SertorError):
    """The vector store backend is unavailable (REQ-021).

    Raised instead of silently returning empty results.
    """

    def __init__(self, message: str, *, backend: str, reason: str):
        self.backend = backend
        self.reason = reason
        super().__init__(f"{message} [backend={backend}, reason={reason}]")


class ProviderMismatchError(SertorError):
    """A corpus targeted by a combined search is indexed with a different provider (FR-009).

    Scores from different vector spaces are not comparable: no answer is better than a
    misleading merge (deliberate waiver of the facade's tolerant policy, clarify 2026-06-10).
    """

    def __init__(self, message: str, *, corpus: str, expected: str, found: list[str]):
        self.corpus = corpus
        self.expected = expected
        self.found = found
        super().__init__(
            f"{message} [corpus={corpus}, expected={expected}, found={found}] — "
            "re-index the corpus with the current provider or switch provider"
        )


class GraphNotFoundError(SertorError):
    """A code graph is queried before it has been built (FEAT-005, FR-007).

    Absence of the GRAPH = explicit usage error (build it with an index); absence of a
    SYMBOL in the graph is instead a legitimate empty result (FR-017) — two distinct semantics.
    """

    def __init__(self, message: str, *, corpus: str):
        self.corpus = corpus
        super().__init__(f"{message} [corpus={corpus}]")


class IndexNotFoundError(SertorError):
    """An index is queried before it exists (REQ-009 from FEAT-002).

    At engine level, a missing index is an explicit usage error (build the index before
    querying), not a silent empty result.
    """

    def __init__(self, message: str, *, collection: str):
        self.collection = collection
        super().__init__(f"{message} [collection={collection}]")


class IndexLockedError(SertorError):
    """A second indexing run tried to acquire the single-writer lock already held (046, FR-020).

    Concurrent indexing of the same `(corpus, provider)` index would corrupt the manifest and the
    derived artifacts: rather than racing, the second run fails explicitly (Principio IV). Carries
    the index directory so the message can name the index the other process is building.
    """

    def __init__(self, index_dir: str):
        self.index_dir = index_dir
        super().__init__(
            f"index is locked: another process is indexing {index_dir} — "
            "wait for it to finish, or remove the stale lock file (.index.lock) if no process is "
            "running"
        )


class InvalidTimeWindowError(SertorError):
    """An episodic search was given a window with `since > until` (033, FR-007).

    An impossible window is an explicit, actionable usage error (Principio IV), distinct from a
    window that simply matches no session (a legitimate empty result). Carries the offending
    bounds so the caller can correct them.
    """

    def __init__(self, since: float, until: float):
        self.since = since
        self.until = until
        super().__init__(
            f"invalid time window: since ({since}) is after until ({until}) — "
            "swap the bounds so that since <= until"
        )


class SessionNotFoundError(SertorError):
    """A `memory show` was given a session key that is not in the archive (036, FR-009).

    An absent session is an explicit, actionable usage error for the CLI consumer (Principio IV),
    distinct from a session that exists but has no turns (a legitimate empty result, exit 0).
    Raised by the consumer (not by the read core: `MemoryArchive.get` returns `None` for absence,
    keeping its non-fatal policy). Carries the offending key so the message can suggest `memory
    list`. Coherent with `IndexNotFoundError`/`InvalidTimeWindowError`.
    """

    def __init__(self, session_key: str):
        self.session_key = session_key
        super().__init__(
            f"session not found: {session_key}; "
            "use `memory list` to see the available sessions"
        )


class SuiteNotFoundError(SertorError):
    """An evaluation run/amend was asked for a suite that does not exist (065, REQ-032).

    Absence of the suite is an explicit, actionable usage error for the consumer (Principio IV) —
    NOT a deceptive zero score: a run on a missing suite must fail and name how to create it, never
    report `hit@k=0` as if the retrieval were bad. Carries the offending path so the message can
    point at `sertor-rag eval add-case`.
    """

    def __init__(self, path: str):
        self.path = path
        super().__init__(
            f"eval suite not found: {path} — "
            "create it with `sertor-rag eval add-case` (or author it by hand)"
        )


class SuiteValidationError(SertorError):
    """A case in the eval suite (or the baseline file) is malformed (065, REQ-004).

    A bad entry is an authoring bug in a curated, versioned file — not a legitimate empty result:
    rather than scoring a fasullo, fail and IDENTIFY the offending case by index + a partial detail
    so the author can fix it (Principio IV).
    """

    def __init__(self, case_index: int, detail: str):
        self.case_index = case_index
        self.detail = detail
        super().__init__(f"invalid eval suite case [{case_index}]: {detail}")


class SuiteWriteError(SertorError):
    """The eval suite/baseline writer could not serialise the data safely (065, DA-a).

    The hand-rolled TOML writer validates by round-trip (re-reads with `tomllib`); if the produced
    text does not parse back, the writer refuses to persist an ambiguous file (fail-safe, Principio
    IV/VI) and raises this instead. Carries the target path for the message.
    """

    def __init__(self, path: str):
        self.path = path
        super().__init__(
            f"could not serialise the eval artifact safely: {path} — "
            "the round-trip validation failed (the written TOML did not parse back)"
        )


class RegressionDetected(SertorError):
    """The evaluation run scored below the recorded baseline beyond tolerance (065, REQ-043).

    This is the non-regression GATE: at least one metric (mrr / hit@k) dropped by more than the
    configured tolerance versus `eval/baseline.toml`. An explicit failure (exit 1) so CI can block
    the change; the message names every degraded metric and the tolerance. Carries the full
    `RegressionVerdict` so a consumer can render the per-metric deltas.
    """

    def __init__(self, verdict: RegressionVerdict):
        self.verdict = verdict
        degraded = ", ".join(
            f"{d.name} {d.current:.3f}<{d.baseline:.3f} (Δ={d.delta:+.3f})"
            for d in verdict.deltas
            if d.regressed
        )
        super().__init__(
            f"non-regression gate FAILED (tolerance={verdict.tolerance:.3f}): {degraded} — "
            "fix the retrieval quality or, if this is an accepted new level, "
            "re-record with `sertor-rag eval run --record-baseline`"
        )
