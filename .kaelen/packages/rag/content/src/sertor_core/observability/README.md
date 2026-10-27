# Core observability (`sertor_core.observability`)

Structured logging for the core (Principio IX, REQ-031). Every runtime operation emits a record
on the logger named `sertor_core` via `log_event(level, operation, **fields)` (`logging.py`), with
secrets **redacted** before emission (`redact()`, REQ-032/FR-022).

The core **does not impose** handlers or levels on the caller: configuration (level, JSON format,
file/syslog appenders via dictConfig) is the consumer's responsibility — for the CLI see
`sertor_core/cli/logging_setup.py` (FEAT-011, flags `-v`/`--log-json`/`--log-config`).

## Log field schema

The **authoritative schema** of the fields emitted for each `operation` (`index`, `retrieve`,
`baseline_query`, and the boundary events `embeddings_error`/`store_error`/`index_error`) is
documented in:

- [`specs/011-cli-esecuzione-rag/contracts/log-events.md`](../../../specs/011-cli-esecuzione-rag/contracts/log-events.md)

That contract is the stable source that external appenders (file/syslog/Splunk/ELK) can
index (FR-021/REQ-054, SC-006). Extending the schema → update that file.
