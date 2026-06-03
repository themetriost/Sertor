# Osservabilità — schema dei campi di log

Il core emette **log strutturati** sul logger nominato `sertor_core` (Principio IX). Di default è
muto: il consumatore (es. la CLI con `-v`/`--log-json`/`--log-config`) decide handler, livello e
appender. Ogni evento porta un campo `operation` + campi specifici (passati via `extra`), così un
appender esterno (file, syslog, Splunk/ELK) può indicizzarli. I **segreti sono redatti** prima
dell'emissione (`redact`, REQ-032/055).

## Campi per operazione

| `operation` | Livello | Campi |
|-------------|---------|-------|
| `ingest` | INFO | `root`, `documents`, `skipped` |
| `ingest_skip` | WARNING | `path`, `reason` (file illeggibile saltato) |
| `index` | INFO | `collection`, `provider`, `documents`, `chunks`, `embedding_dim`, `elapsed_ms` |
| `index` | ERROR | `collection`, `provider`, `error`, `reason` (fallimento sul boundary, REQ-053) |
| `retrieve` | INFO | `collection`, `provider`, `doc_type`, `k`, `results`, `elapsed_ms` |
| `retrieve` | WARNING | `collection`, `status=no_index`, `doc_type` (indice assente) |
| `retrieve` | ERROR | `collection`, `provider`, `error`, `reason` (fallimento sul boundary) |
| `baseline_query` | INFO | `collection`, `provider`, `k`, `results`, `elapsed_ms` |
| `wiki_create` | INFO | `root`, `changed` |
| `wiki_record` / `wiki_ingest` | INFO | `page`, `changed` |
| `wiki_distill` | INFO | `page`, `provider`, `changed` |
| `wiki_index` | INFO/WARNING | `root`, `collection`, `documents`, `chunks` / `status=empty` |

## Abilitare i log (via CLI)

```bash
sertor index . -v                       # INFO a console
sertor index . --log-json               # record JSON (un evento per riga)
sertor index . --log-config logging.yaml  # appender esterni (file/syslog/Splunk) via dictConfig
```

## Abilitare i log (come libreria)

```python
import logging
logging.getLogger("sertor_core").setLevel(logging.INFO)
logging.getLogger("sertor_core").addHandler(logging.StreamHandler())
```

Gli errori di dominio restano **eccezioni esplicite** (Principio IV); l'evento di log ERROR sui
boundary li rende anche diagnosticabili dal monitoring (Principio IX) senza nascondere l'eccezione.
