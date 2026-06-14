# Contract — `MemoryArchive` (store di archivio, concreto stdlib)

**Feature**: 031 · **Tipo**: componente concreto (NO porta — D2) · **ID contratto**: `memory.archive/1`

Store SQLite locale a `<index_dir>/memory.sqlite`. Pattern identico a `SqliteObservabilityStore`
(`observability/store.py`) ed `EmbeddingCache` (`adapters/embeddings/cache.py`): lazy connect, schema
idempotente, degradazione non-fatale. **stdlib-only** (`sqlite3`, `json`).

## Interfaccia

```python
class MemoryArchive:
    def __init__(self, index_dir: Path | str): ...
    def upsert(self, session: ArchivedSession) -> bool: ...
    def exists(self, session_key: str) -> bool: ...
    def get(self, session_key: str) -> ArchivedSession | None: ...
```

## `__init__(index_dir)`
- Salva solo il path (`<index_dir>/memory.sqlite`). **Nessun** file aperto/creato qui (lazy → flag-off
  safe, FR-002). La connessione e lo schema nascono al primo `upsert`/`get`.

## `upsert(session) -> bool`
| Caso | Comportamento | Ritorno |
|---|---|---|
| Sessione NUOVA | Inserisce riga `sessions` + righe `turns` (stessa transazione) | `True` |
| Sessione già presente (stessa `session_key`) | `INSERT OR IGNORE` → no-op; record esistente **invariato** | `False` |
| `sqlite3.Error` (store guasto/corrotto) | Warning `memory_archive_unavailable` + no-op | `False` (non-fatale, FR-025) |

- **Idempotente** (FR-015/016): K upsert della stessa sessione → 1 record, contenuto invariato (SC-002).
- **Conservativo** (FR-014): nessun `DELETE`/`REPLACE`; sessioni precedenti mai toccate (SC-006).
- `session.turns` è **già scrubbed** (lo scrub è responsabilità del servizio, non dello store).
- `retention_days` → `sessions.metadata` JSON (gancio, mai applicato, FR-021/022).

## `exists(session_key) -> bool`
- `True` se la sessione è in archivio. Su store guasto: warning + `False` (non-fatale).

## `get(session_key) -> ArchivedSession | None`
- `ArchivedSession` ricomposta (sessione + turni in ordine `turn_index`), o `None` se assente.
- Su store guasto: warning + `None` (non-fatale). Usato da test e, in futuro, FEAT-002.

## Invarianti
- **Non solleva mai** per guasto store (FR-025, SC-007): il pattern del repo (`store.py:53`) — un'assenza/
  guasto è un esito legittimo loggato, **non** un'eccezione (distinto dal «null silenzioso» vietato dal
  Principio IV, perché esplicitamente loggato).
- **Append-only conservativo**: nessuna rotazione, nessuna cancellazione automatica.
- **Gitignored**: `<index_dir>/memory.sqlite` è coperto da `**/.index/`/`**/.index-*/` (`.gitignore:21-25`).

## Test del contratto (offline, `tmp_path`)
- N sessioni distinte → `get` ne ritorna N, 0 duplicati (SC-001).
- K upsert della stessa → 1 record, turni invariati, ritorno `True` poi `False` (SC-002).
- Store corrotto (`write_bytes(b"not a database")`) → upsert/get non sollevano, warning emesso (SC-007),
  come `test_observability_store.py::test_store_failure_is_non_fatal`.
- Sessioni di 2 `project_id` → record separati, non mescolati (US1 scenario 4).
