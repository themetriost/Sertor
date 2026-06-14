# Data Model — feature 020

Nessuna entità di **dominio** del retrieval cambia (`RetrievalResult`/`EmbeddedChunk`/le 6 porte
restano invariati). Le entità qui sono la nuova **porta** di osservabilità, l'artefatto di persistenza e
le manopole, confinati in `observability/` + `domain/ports.py` + `config/settings.py`.

## 1. Evento di osservabilità (riga dello store)

Tabella `events` in `<index_dir>/observability.sqlite`:

| Campo | Tipo SQLite | Significato |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | autoincrement (ordine di arrivo) |
| `ts` | REAL | istante dell'evento (epoch secondi, da `LogRecord.created`) |
| `operation` | TEXT | tipo di operazione (`index`, `embeddings`, `embeddings_cache`, `retrieve`, …) |
| `fields` | TEXT | JSON dei campi dell'evento (già **redatti** a monte da `log_event`) |

- **Indici:** `(operation, ts)` per la query per-operation-e-intervallo (FR-003); `(ts)` per le query
  per sola finestra temporale.
- **Bootstrap:** `CREATE TABLE IF NOT EXISTS` + indici, lazy alla prima apertura (idempotente).
- **Ciclo di vita:** scritto dal handler per ogni evento strutturato; **append-only**; mai modificato.
  Cancellabile in blocco (artefatto rigenerabile). Retention = gancio, politica rinviata.
- **Robustezza:** errori SQLite catturati nel handler → l'eccezione non risale (logging `handleError`),
  warning emesso; l'operazione osservata non è influenzata.

## 2. Porta `ObservabilityStore` (domain/ports.py) — la 7ª porta

```
@runtime_checkable
class ObservabilityStore(Protocol):
    def record_event(self, ts: float, operation: str, fields: dict) -> None: ...
    def query_events(self, operation: str | None, since: float | None,
                     until: float | None) -> list[ObservedEvent]: ...
```

- `record_event` — scrive un evento (idempotenza non richiesta: ogni emissione è un evento distinto;
  l'`id` autoincrement dà l'ordine).
- `query_events` — recupera per operation (o tutti) e finestra temporale; è il **seam** che **FEAT-002**
  consumerà per le aggregazioni. (Le aggregazioni/bucket NON sono qui.)
- `ObservedEvent` — piccola dataclass di dominio `(ts, operation, fields)` per il valore di ritorno
  (niente tipi SQLite che risalgono nel dominio, coerente con le altre porte).

## 3. Adapter `SqliteObservabilityStore` (observability/store.py)

Implementa `ObservabilityStore` su `sqlite3` (stdlib). `record_event` → `INSERT`; `query_events` →
`SELECT ... WHERE` con i filtri; deserializza `fields` da JSON. Errori `sqlite3.Error` → catturati e
loggati (warning `observability_store_unavailable`), mai propagati.

## 4. Handler `EventPersistenceHandler` (observability/capture.py)

Un `logging.Handler`. `emit(record)`: se `record` ha l'attributo `operation` (è un evento strutturato di
`log_event`), estrae `operation`, i campi (gli attributi `extra` che `log_event` ha aggiunto, già
redatti) e `ts = record.created`, e chiama `store.record_event(...)`. I record senza `operation` (log
generici) sono ignorati. Le eccezioni in `emit` sono gestite dal framework (`handleError`) → non-fatali.

## 5. Manopole (`Settings`)

| Campo | Env | Default | Significato |
|---|---|---|---|
| `observability_enabled` | `SERTOR_OBSERVABILITY` | `False` | Attiva la persistenza (attach del handler). Off = comportamento odierno (FR-004). |
| *(sede)* | — (derivata) | `<index_dir>/observability.sqlite` | Non è una manopola separata: deriva da `index_dir` (gitignored). |
| *(retention)* | `SERTOR_OBSERVABILITY_RETENTION` | *nessuna* | **Gancio** previsto; politica rinviata (DA-O-b). |

## 6. Relazioni

```
composition.py  (solo se settings.observability_enabled)
  ├─ store = SqliteObservabilityStore(settings.index_dir)          [observability/store.py]
  └─ logging.getLogger("sertor_core").addHandler(
         EventPersistenceHandler(store))                            [observability/capture.py]

log_event(...) → LogRecord(operation, **safe) → [handler] → store.record_event(...)   (additivo)

FEAT-002 (futuro) → store.query_events(operation, since, until) → aggregazioni/report
```
