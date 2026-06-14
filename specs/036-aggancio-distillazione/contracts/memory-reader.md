# Contract — Lettura dell'archivio (`sertor.memory-reader/1`)

Superficie di lettura del core esposta ai thin consumer (FR-005). **Nessuna nuova porta**: il «reader» è
il componente concreto `MemoryArchive` (single consumer — stesso profilo di `EpisodicSearch`), esposto da
una factory di composition gated. Sola lettura, local-first, non-fatale (FR-004/FR-014).

## Factory `build_memory_reader(settings) -> MemoryArchive | None`

`src/sertor_core/composition.py` (additiva, accanto a `build_memory_archive`/`build_memory_archiver`/
`build_episodic_search`).

- **Gate privacy**: `if not settings.memory_enabled: return None` (privacy-by-default, identico alle
  altre factory memoria — `composition.py:363,381`). Nessun file aperto, nessun import host-specifico a
  memoria spenta.
- **Abilitata**: ritorna `MemoryArchive(settings.index_dir)` (riusa `build_memory_archive`).
- **Import lazy** del componente (coerente con le altre `build_*`).

Il `None` è **consumato** dal comando CLI (`_require_memory_reader` → `ConfigError`, exit 1) — la policy
di disponibilità vive in composition (Principio I), il veicolo la traduce in errore azionabile
(Principio IV).

## Metodo `MemoryArchive.get(session_key) -> ArchivedSession | None` (RIUSATO)

Invariato (`adapters/memory/archive.py:104-139`). Vedi `data-model.md` per gli esiti.

## Metodo `MemoryArchive.list_recent(limit: int) -> tuple[SessionSummary, ...]` (NUOVO)

### Firma

```python
def list_recent(self, limit: int) -> tuple[SessionSummary, ...]: ...
```

### Semantica

- Ritorna le sessioni archiviate più recenti, **ordine recency-first** (`captured_at DESC`), al più
  `limit` voci.
- Ogni voce è una `SessionSummary(session_key, captured_at, turn_count)` — nessun contenuto di turno
  caricato.
- `turn_count` letto da `metadata.turn_count` (già persistito, `archive.py:142-150`).
- **Degradazione non-fatale** (Principio IV, policy FEAT-001/002): archivio assente / vuoto / illeggibile
  / `sqlite3.Error` → `()` + warning `memory_archive_unavailable` (riuso evento esistente). Mai crash.
- **Sola lettura**: nessun `INSERT`/`UPDATE`/`DELETE`, nessuna creazione di tabelle o indici.
- `limit <= 0` → `()` (nessun risultato; SQLite `LIMIT 0` o guard) — coerente con la natura «al più N».

### Osservabilità (Principio IX, RNF-2)

- Evento informativo `memory_list` con `count` e `limit` (conteggi, **mai** testo).
- Guasti store: `memory_archive_unavailable` (riuso).

## Eccezione di dominio `SessionNotFoundError(session_key)` (NUOVA)

`src/sertor_core/domain/errors.py`, sottoclasse di `SertorError` (coerente con `IndexNotFoundError`/
`InvalidTimeWindowError`).

- **Non** sollevata dal core di lettura (`get` ritorna `None` per assenza, policy non-fatale del core).
- Sollevata dal **consumer CLI** quando `get` ritorna `None` su `memory show`, per dare un esito
  esplicito «not found» (FR-003/FR-009) con exit non-zero. Messaggio azionabile, es.:
  `session not found: <session_key>` + suggerimento `memory list` per scoprire le chiavi.

## Invarianti di test (contratto core)

- **R-GATE**: `memory_enabled=False` → `build_memory_reader` ritorna `None` (nessun file aperto).
- **R-LIST-ORDER**: `list_recent` ordina recency-first; rispetta il limite.
- **R-LIST-COUNT**: `turn_count` corretto per ogni voce.
- **R-LIST-EMPTY**: archivio assente/vuoto → `()` (no eccezione).
- **R-LIST-STOREKO**: store illeggibile → `()` + warning (no crash).
- **R-GET-REUSE**: `get` resta invariato (nessuna regressione su FEAT-001).
- **R-READONLY**: dopo `get`/`list_recent`, `sessions`/`turns`/schema sono invariati (sola lettura).
