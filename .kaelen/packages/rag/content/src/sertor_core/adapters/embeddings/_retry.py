"""Retry helper for embedding calls (018, REQ-H3).

Shared by the embedding adapters (DRY, Principio III): a single tested place that retries
transient provider failures with exponential backoff + jitter. Lives at the boundary
(`adapters/`) and catches ONLY the domain exception `EmbeddingError` — no provider SDK leaks here.
"""
from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from sertor_core.domain.errors import EmbeddingError
from sertor_core.observability.logging import log_event

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """How many times to retry a retriable embedding failure, and the backoff base.

    `max_attempts` is the TOTAL number of attempts (1 = no retry). `base_backoff_s` is the base
    of the exponential backoff in seconds. The total wait is bounded by `max_attempts` itself
    (no hidden cap — Principio VIII): with conservative defaults the worst case is a few seconds.
    """

    max_attempts: int = 3
    base_backoff_s: float = 0.5

    @property
    def attempts(self) -> int:
        """Effective attempts (a value below 1 is normalised to a single attempt)."""
        return self.max_attempts if self.max_attempts >= 1 else 1


def with_retry(
    fn: Callable[[], T],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] = random.random,
    provider: str | None = None,
) -> T:
    """Run `fn`, retrying retriable `EmbeddingError`s with exponential backoff + jitter.

    Retries only when `EmbeddingError.retriable` is true and attempts remain; a non-retriable
    failure propagates immediately (FR-004). On exhaustion the last `EmbeddingError` is re-raised
    with its type preserved (FR-003). `sleep`/`rng` are injectable so tests are deterministic and
    incur no real wait (SC-005).
    """
    attempts = policy.attempts
    for i in range(attempts):
        try:
            return fn()
        except EmbeddingError as exc:
            is_last = i == attempts - 1
            if not exc.retriable or is_last:
                raise
            wait = policy.base_backoff_s * (2**i) * (0.5 + rng())
            log_event(
                logging.WARNING,
                "embeddings_retry",
                provider=provider,
                attempt=i + 1,
                reason=exc.reason,
                wait_ms=round(wait * 1000, 2),
            )
            sleep(wait)
    raise AssertionError("with_retry: unreachable")  # the loop always returns or raises
