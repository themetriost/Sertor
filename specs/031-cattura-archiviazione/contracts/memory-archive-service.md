# Contract — `MemoryArchiveService` (servizio di archiviazione)

**Feature**: 031 · **Tipo**: servizio (`src/sertor_core/services/memory_archive.py`) · **ID contratto**: `memory.archive-service/1`

Orchestra il flusso deterministico: scoperta → lettura → **scrub** → upsert idempotente. Dipende **solo**
da astrazioni (la porta `TranscriptCaptureAdapter`, il componente `MemoryArchive`, `scrub_text`,
`Settings`); cablato in composition (FR-026). Testabile offline con adapter mock + `tmp_path` (Principio V).

## Interfaccia

```python
class MemoryArchiveService:
    def __init__(self, adapter: TranscriptCaptureAdapter, archive: MemoryArchive,
                 settings: Settings): ...
    def archive_all(self) -> ArchiveRunReport: ...
```

## `archive_all() -> ArchiveRunReport`
Flusso (guard clause, basso nesting — Principio VII):
1. `refs = adapter.list_sessions()`. Vuoto → ritorna report a zero (sorgente assente già loggata
   dall'adapter, FR-006).
2. Per ogni `ref`:
   - `if archive.exists(ref.session_key)`: emette `memory_session_skipped` (FR-024), `skipped += 1`,
     continua (skip osservabile, **non** no-op silenzioso — Edge Case «riprocesso massivo»).
   - `content = adapter.read_session(ref)`. `turns` vuoto → skip con warning (D3 regola 5).
   - **scrub**: per ogni turno, `scrub_text(turn.text, settings.memory_scrub_patterns)` → turni scrubbed.
   - `ArchivedSession` con `retention_days = settings.memory_retention_days` (gancio, FR-021).
   - `is_new = archive.upsert(session)`. `is_new` → emette `memory_session_archived` (FR-023:
     `session_key`, `project_id`, `adapter_kind`, `content_size` post-scrub, `turn_count`, `is_new=True`),
     `archived += 1`.
3. Ritorna `ArchiveRunReport(archived, skipped, errors)`.

```python
@dataclass
class ArchiveRunReport:
    archived: int = 0
    skipped: int = 0
    errors: int = 0
```

## Garanzie
| Requisito | Garanzia |
|---|---|
| FR-017/027 | Lo scrub è applicato a **ogni** turno **prima** dell'upsert; nessun percorso persiste testo non-scrubbed; gli eventi non includono `content` grezzo (solo `content_size`). |
| FR-015/016 | Idempotenza delegata a `archive.upsert` (`INSERT OR IGNORE`) + check `exists` per lo skip osservabile. |
| FR-025 | Guasto store → `upsert` non-fatale; il servizio prosegue con gli altri ref. |
| FR-005 | Il servizio non conosce l'identità dell'host: nessun ramo `if adapter is ClaudeCode` (SC-005). |
| FR-006 | Sorgente assente → archivio invariato, report a zero. |

## Privacy-by-default (FR-001/002)
- Il servizio è **costruito e invocato solo se `settings.memory_enabled`** (gate in composition, D8). A
  flag off non viene istanziato → adapter e store mai creati, nessun file aperto (SC-003).

## Test del contratto (offline)
- Mock adapter con 3 sessioni → report `archived=3, skipped=0`; archivio = 3 record (SC-001).
- Ri-esecuzione → `archived=0, skipped=3`, archivio invariato (SC-002, SC-006).
- Turni con segreti sintetici → 0 occorrenze in chiaro nel `get` (SC-004).
- 2 mock adapter diversi → stesso comportamento, nessun ramo host-specifico (SC-005).
- Store guasto iniettato → l'esecuzione prosegue, warning, nessuna eccezione (SC-007).
