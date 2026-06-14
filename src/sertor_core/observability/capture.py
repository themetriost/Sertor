"""Event capture: the bridge from stdlib `logging` to the observability store (feature 020).

`EventPersistenceHandler` is a `logging.Handler` attached by the composition root to the
`sertor_core` logger ONLY when persistence is enabled. It observes the `LogRecord`s the core already
emits via `log_event` and persists the structured ones — WITHOUT touching `log_event` or any
call-site (the purest observer: the producer does not know the observer exists).

Three properties come for free from the logging framework:
- additive: `log_event`'s signature and the call-sites are unchanged (FR-005);
- non-fatal: the framework never propagates a handler exception to the caller — it routes it to
  `Handler.handleError` (FR-007), so a store outage cannot fail an indexing/search;
- privacy: `log_event` puts the ALREADY-redacted fields on the record (`extra={..., **safe}`), so
  the handler reads redacted data (FR-008/009).
"""
from __future__ import annotations

import logging

from sertor_core.domain.ports import ObservabilityStore

# Standard LogRecord attribute names: everything else on the record is an applicative field that
# `log_event` added via `extra`. Built from an empty record so it tracks the running Python version.
_RESERVED = set(vars(logging.makeLogRecord({}))) | {
    "operation", "message", "asctime", "taskName",
}


class EventPersistenceHandler(logging.Handler):
    """Persists structured `log_event` records to an `ObservabilityStore`."""

    def __init__(self, store: ObservabilityStore):
        super().__init__()
        self._store = store
        self._in_emit = False  # re-entrancy guard (RNF-006): the store's warnings are events too

    def emit(self, record: logging.LogRecord) -> None:
        # Only structured events carry `operation` (set by log_event via extra); skip plain logs.
        operation = getattr(record, "operation", None)
        if operation is None:
            return
        # If the store fails it emits its own `log_event` warning, which comes back here: skip it to
        # avoid infinite recursion. The warning still reaches the other handlers (stderr), so it is
        # observable. Safe under logging's per-handler RLock (re-entrant, same thread).
        if self._in_emit:
            return
        self._in_emit = True
        try:
            fields = {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
            self._store.record_event(record.created, operation, fields)
        finally:
            self._in_emit = False
