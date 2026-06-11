# Osservabilità del nucleo (`sertor_core.observability`)

Logging strutturato del core (Principio IX, REQ-031). Ogni operazione a runtime emette un record
sul logger nominato `sertor_core` via `log_event(level, operation, **fields)` (`logging.py`), con i
segreti **redatti** prima dell'emissione (`redact()`, REQ-032/FR-022).

Il core **non impone** handler o livelli al chiamante: la configurazione (livello, formato JSON,
appender file/syslog via dictConfig) è responsabilità del consumatore — per la CLI vedi
`sertor_core/cli/logging_setup.py` (FEAT-011, leve `-v`/`--log-json`/`--log-config`).

## Schema dei campi di log

Lo **schema autoritativo** dei campi emessi per ciascuna `operation` (`index`, `retrieve`,
`baseline_query`, e gli eventi di boundary `embeddings_error`/`store_error`/`index_error`) è
documentato in:

- [`specs/011-cli-esecuzione-rag/contracts/log-events.md`](../../../specs/011-cli-esecuzione-rag/contracts/log-events.md)

Quel contratto è la fonte stabile che gli appender esterni (file/syslog/Splunk/ELK) possono
indicizzare (FR-021/REQ-054, SC-006). Estendere lo schema → aggiornare quel file.
