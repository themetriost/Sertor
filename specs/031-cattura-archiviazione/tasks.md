---
description: "Task list per la feature 031 — Cattura & archiviazione locale dei transcript"
---

# Tasks: Cattura & archiviazione locale dei transcript (031)

**Input**: Design documents da `specs/031-cattura-archiviazione/`

**Prerequisites**: plan.md (letto), spec.md (letto), research.md (letto), data-model.md (letto),
contracts/transcript-capture-port.md, contracts/memory-archive-store.md,
contracts/memory-archive-service.md, quickstart.md (tutti letti).

**Test**: richiesti esplicitamente (plan.md §Project Structure, spec.md §Success Criteria, contratti
§Test del contratto, quickstart.md §Test offline). Test offline, mock adapter, `tmp_path`, senza rete.

**Organizzazione**: task raggruppati per user story (US1 P1, US2 P2, US3 P3), con prerequisiti
fondamentali isolati in fase Foundational. Ogni storia testabile indipendentemente.

## Formato: `[ID] [P?] [Story] Descrizione con path file`

- **[P]**: eseguibile in parallelo (file diversi, nessuna dipendenza da task incompleti)
- **[Story]**: user story di riferimento (US1/US2/US3)
- Path file espliciti per ogni task

---

## Phase 1: Setup (Struttura moduli e manopole)

**Purpose**: Creare la struttura di directory e aggiungere le manopole di configurazione.
Nessun prerequisito — può iniziare subito.

- [X] T001 Creare package `src/sertor_core/adapters/capture/` con `__init__.py` vuoto
- [X] T002 Creare package `src/sertor_core/adapters/memory/` con `__init__.py` vuoto
- [X] T003 [P] Estendere `src/sertor_core/config/settings.py`: aggiungere helper `_int_or_none_env` (gemello di `_float_or_none_env`) e 5 manopole (`memory_enabled`, `memory_adapter`, `memory_retention_days`, `memory_scrub_patterns`, +`claude_projects_dir` per finding F2) con default solo in `Settings.load()` (D7); env: `SERTOR_MEMORY`, `SERTOR_MEMORY_ADAPTER`, `SERTOR_MEMORY_RETENTION_DAYS`, `SERTOR_MEMORY_SCRUB_PATTERNS`, `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`
- [X] T004 [P] Aggiungere test delle 5 nuove manopole in `tests/unit/test_settings.py`: verifica default, override env, `_int_or_none_env` con valori `None`/intero/blank, `memory_scrub_patterns` via CSV, `claude_projects_dir` (F2)

**Checkpoint Setup**: struttura directory e manopole pronte; le fasi Foundational e US possono iniziare.

---

## Phase 2: Foundational (Prerequisiti trasversali bloccanti)

**Purpose**: Entità di dominio pure, porta `TranscriptCaptureAdapter`, store `MemoryArchive`, funzione
pura `scrub_text`, servizio orchestrante `MemoryArchiveService`, wiring composition. Devono essere
completi prima di qualsiasi implementazione per user story.

**Dipende da**: Phase 1 (T001-T003).

**Attenzione**: nessuna user story può iniziare finché questa fase non e' completata.

### Dominio (entita' pure)

- [X] T005 Creare `src/sertor_core/domain/memory.py` con le quattro entita' di dominio `@dataclass(frozen=True)`: `SessionRef` (session_key, project_id, source_path), `TranscriptTurn` (index, role, text, ts: float|None=None), `TranscriptContent` (session_key, project_id, adapter_kind, captured_at, turns: tuple[TranscriptTurn,...]), `ArchivedSession` (session_key, project_id, captured_at, adapter_kind, turns: tuple[TranscriptTurn,...], retention_days: int|None=None); nessun import di SDK (Principio I)
- [X] T006 [P] Estendere `src/sertor_core/domain/ports.py`: aggiungere `TranscriptCaptureAdapter` come 8a porta `@runtime_checkable Protocol` con attributo `kind: str` e metodi `list_sessions() -> list[SessionRef]` e `read_session(ref: SessionRef) -> TranscriptContent`; importare `SessionRef`/`TranscriptContent` da `domain/memory.py` (data-model.md §2)

### Scrub del contenuto (funzione pura)

- [X] T007 [P] Creare `src/sertor_core/observability/scrub.py` con funzione pura `scrub_text(text: str, extra_patterns: tuple[str,...] = ()) -> str`: regex pre-compilate per API key (`sk-[A-Za-z0-9]+`, `AKIA[0-9A-Z]{16}`), bearer/Authorization, `CHIAVE=VALORE` con hint (`key|token|secret|password|authorization`, riusando `_SECRET_HINTS` da `observability/logging.py`), header inline; `extra_patterns` compilate per chiamata; ripiego conservativo su errore regex (redige il segmento, emette warning `memory_scrub_fallback`); segnaposto `[REDACTED]`; stdlib-only (`re`) (D6, FR-017/018/019/020)

### Store di archivio (concreto, stdlib)

- [X] T008 Creare `src/sertor_core/adapters/memory/archive.py` con classe `MemoryArchive`: `__init__(index_dir: Path|str)` salva solo il path (`<index_dir>/memory.sqlite`), nessun file aperto; `_connect()` lazy (CREATE TABLE IF NOT EXISTS, `self._conn` assegnato solo dopo schema OK — file corrotto resta `None`); schema SQL a due tabelle (`sessions`: session_key PK, project_id, captured_at REAL, adapter_kind, metadata TEXT JSON; `turns`: PK(session_key, turn_index), role, ts REAL nullable, content TEXT); indici `idx_sessions_project` e `idx_turns_session`; `upsert(session: ArchivedSession) -> bool` (INSERT OR IGNORE sessione+turni stessa transazione, True=nuova, False=presente/errore); `exists(session_key: str) -> bool`; `get(session_key: str) -> ArchivedSession | None`; ogni metodo avvolge `sqlite3.Error` in warning non-fatale (pattern `observability/store.py`, FR-009/014/015/016/025)

### Servizio orchestrante

- [X] T009 Creare `src/sertor_core/services/memory_archive.py` con `ArchiveRunReport` (`@dataclass`: archived=0, skipped=0, errors=0) e `MemoryArchiveService(adapter: TranscriptCaptureAdapter, archive: MemoryArchive, settings: Settings)` con metodo `archive_all() -> ArchiveRunReport`: flusso guard-clause (list_sessions → per ogni ref: exists→skip osservabile `memory_session_skipped`, read_session→turni vuoti→skip, scrub ogni turno con `scrub_text(turn.text, settings.memory_scrub_patterns)`, costruisci `ArchivedSession` con `retention_days=settings.memory_retention_days`, `archive.upsert(session)`→emetti `memory_session_archived` con session_key/project_id/adapter_kind/content_size/turn_count/is_new=True); nessun segreto negli eventi (solo content_size, FR-023/024/027); nessun ramo `if adapter is ClaudeCode` (FR-005)

### Wiring composition (lazy, gated)

- [X] T010 Estendere `src/sertor_core/composition.py` con tre `build_*` con import lazy: `build_capture_adapter(settings: Settings) -> TranscriptCaptureAdapter` (seleziona da `settings.memory_adapter`: "claude-code" → `ClaudeCodeCaptureAdapter`; valore ignoto → `ConfigError` con valori ammessi, come `_validated_engine`); `build_memory_archive(settings: Settings) -> MemoryArchive` (`MemoryArchive(settings.index_dir)`); `build_memory_archiver(settings: Settings) -> MemoryArchiveService | None` (costruisce `MemoryArchiveService` solo se `settings.memory_enabled`, altrimenti ritorna `None` — nessun import dell'adapter a flag off, FR-002, D8); esportare da `src/sertor_core/__init__.py`

**Checkpoint Foundational**: entita' dominio, porta, store, scrub, servizio e composition wiring pronti.
Le tre user story possono iniziare (US1/US2/US3 in parallelo dopo questo punto).

---

## Phase 3: User Story 1 — Archiviazione idempotente e conservata (Priority: P1, MVP)

**Goal**: con la cattura attiva, archivio N sessioni distinte → esattamente N record; ri-archiviare le
stesse N → conteggio invariato, record inalterati, nessun duplicato.

**Independent Test**: `uv run pytest tests/unit/test_memory_archive_store.py -q`
— con mock adapter che fornisce N sessioni distinte: `archive_all()` → `report.archived=N,
report.skipped=0`; secondo `archive_all()` → `report.archived=0, report.skipped=N`; archivio
contiene esattamente N record, contenuti invariati (SC-001, SC-002, SC-006).

**Dipende da**: Foundational (T005-T010).

### Test per US1

- [X] T011 [P] [US1] Creare `tests/unit/test_memory_archive_store.py`: test `MemoryArchive` con `tmp_path` — N sessioni distinte → N record 0 duplicati (SC-001); K upsert stessa sessione → 1 record invariato, ritorno True poi False (SC-002); sessioni di 2 project_id → record separati (US1 scenario 4); store corrotto (`write_bytes(b"not a database")`) → upsert/get non sollevano, warning emesso (SC-007); nessuna sessione cancellata da archiviazioni successive (SC-006); contratto `memory.archive/1`
- [X] T012 [P] [US1] Creare `tests/unit/test_memory_archive_service.py`: orchestrazione con mock adapter — 3 sessioni → `archived=3, skipped=0`; ri-esecuzione → `archived=0, skipped=3`, archivio invariato; skip osservabile (evento `memory_session_skipped`) vs no-op silenzioso; sessione con turns vuoti → saltata; store guasto iniettato → esecuzione prosegue, nessuna eccezione (SC-007); contratto `memory.archive-service/1`

### Implementazione US1

- [X] T013 [US1] Verificare che `MemoryArchive.upsert` usi `INSERT OR IGNORE` su `sessions` + `turns` in un'unica transazione SQLite in `src/sertor_core/adapters/memory/archive.py` (già definito in T008); aggiungere il test di namespacing per `project_id` tramite campo in tabella `sessions` (FR-010, D5) — se gia' coperto da T011 non servono modifiche
- [X] T014 [US1] Verificare in `src/sertor_core/services/memory_archive.py` (T009) che lo skip osservabile emetta `log_event("memory_session_skipped", ...)` con `session_key`/`project_id` e che il report accumuli `skipped += 1`; che `memory_session_archived` porti `is_new=True` e `content_size` (post-scrub, non il testo grezzo) (FR-023/024, D9)
- [X] T015 [US1] Aggiungere `ArchiveRunReport` e `MemoryArchiveService` alle esportazioni pubbliche di `src/sertor_core/__init__.py` e verificare che `build_memory_archiver` sia raggiungibile da `from sertor_core.composition import build_memory_archiver` (quickstart.md)

**Checkpoint US1**: archivio idempotente e conservato verificato. MVP della feature consegnabile.

---

## Phase 4: User Story 2 — Privacy by default e contenuto scrubbed (Priority: P2)

**Goal**: con `SERTOR_MEMORY=false` (default) zero scritture; con cattura attiva, segreti sintetici
(sk-…, bearer, PASSWORD=…) non compaiono mai in chiaro nell'archivio.

**Independent Test**: `uv run pytest tests/unit/test_scrub.py -q`
— (a) `SERTOR_MEMORY=false`: `build_memory_archiver(settings)` ritorna `None`, nessun file
`memory.sqlite` creato (SC-003); (b) turno con segreti sintetici → 0 occorrenze in chiaro nel campo
`content` della tabella `turns` dopo `archive_all()` (SC-004).

**Dipende da**: Foundational (T005-T010). Non dipende da US1.

### Test per US2

- [X] T016 [P] [US2] Creare `tests/unit/test_scrub.py`: test `scrub_text` pura con segreti sintetici — `sk-abc123` → `[REDACTED]`, `AKIA1234567890ABCDEF` → `[REDACTED]`, `Authorization: Bearer tok` → `[REDACTED]`, `API_KEY=secret` → `[REDACTED]`, `PASSWORD=mysecret` → `[REDACTED]`; testo senza segreti → invariato; pattern extra via `extra_patterns`; ripiego conservativo su regex invalida → warning + segmento redatto; testo vuoto (SC-004)
- [X] T017 [P] [US2] Aggiungere a `tests/unit/test_memory_archive_service.py` (o nuovo `tests/unit/test_memory_privacy.py`): con `settings.memory_enabled=False` → `build_memory_archiver` ritorna `None`, nessun file `memory.sqlite` in `tmp_path` (SC-003); con cattura attiva → turno con `sk-secret` → `archive.get(key).turns[0].content` non contiene `sk-secret` (SC-004); eventi `memory_session_archived` non portano `content` grezzo (FR-027)

### Implementazione US2

- [X] T018 [US2] Verificare in `src/sertor_core/composition.py` (T010) che `build_memory_archiver` ritorni `None` esattamente quando `settings.memory_enabled is False` e che l'import lazy di `ClaudeCodeCaptureAdapter` avvenga solo dentro la `build_*` (non a livello di modulo `composition`) — confermando zero overhead a flag off (FR-002, D8)
- [X] T019 [US2] Verificare in `src/sertor_core/services/memory_archive.py` (T009) che lo scrub sia applicato a ogni turno via `scrub_text(turn.text, settings.memory_scrub_patterns)` prima di costruire `ArchivedSession` e che il campo `content` passato a `archive.upsert` sia sempre il testo scrubbed (mai il grezzo) — nessun percorso che persiste testo non-scrubbed (FR-017, FR-027)
- [X] T020 [US2] Verificare che `src/sertor_core/observability/scrub.py` (T007) usi `_SECRET_HINTS` importato da `observability/logging.py` per il pattern `KEY=VALUE`, evitando duplicazione del vocabolario segreto (D6, DRY); aggiungere `scrub_text` alle esportazioni di `src/sertor_core/observability/__init__.py`

**Checkpoint US2**: privacy-by-default e scrub verificati offline con segreti sintetici.

---

## Phase 5: User Story 3 — Host-agnosticita' e adapter Claude Code (Priority: P3)

**Goal**: stessa logica di archivio con >=2 adapter simulati; adapter Claude Code legge i file `.jsonl`
senza modificarli; sorgente assente → warning + archivio invariato.

**Independent Test**: `uv run pytest tests/unit/test_claude_code_capture.py -q`
— (a) servizio con 2 mock adapter diversi → stessa logica, nessun ramo `if adapter is ClaudeCode`
(SC-005); (b) adapter Claude Code su directory JSONL sintetica → turni corretti estratti, righe
illeggibili skippate con warning; (c) sorgente assente → `list_sessions()` ritorna `[]` + warning
`memory_capture_source_absent`.

**Dipende da**: Foundational (T005-T010). Non dipende da US1 ne' da US2.

### Test per US3

- [X] T021 [P] [US3] Creare `tests/unit/test_claude_code_capture.py`: test parser difensivo su file JSONL sintetici (costruiti con `tmp_path`) — evento `user` con `message.content` stringa → 1 turno user; evento `assistant` con blocchi `text`/`thinking` → testo concatenato; evento `system`/`tool_use` → ignorato; riga non-JSON → skip + warning `memory_capture_unparsable_line`; riga vuota → skip silenzioso; `timestamp` illeggibile → `ts=None`; sessione con zero turni → `turns=()`; directory sorgente assente → `list_sessions()=[]` + warning (D3, contratto `memory.capture/1`)
- [X] T022 [P] [US3] Aggiungere a `tests/unit/test_memory_archive_service.py` test con >=2 mock adapter distinti (MAdapterA e MAdapterB con `kind` diverso): `archive_all()` si comporta in modo identico, nessun `isinstance`/ramo host-specifico nel servizio (SC-005, FR-005)

### Implementazione US3

- [X] T023 [US3] Creare `src/sertor_core/adapters/capture/claude_code.py` con classe `ClaudeCodeCaptureAdapter`: `kind = "claude-code"`; costruttore accetta `project_source_dir: Path` (encoding del cwd del progetto ospite, fornito dalla config/composition — non hardcodato: Principio X); `list_sessions()` scansiona `project_source_dir/*.jsonl` (solo file, non cartelle omonime), ritorna lista di `SessionRef(session_key=stem, project_id=..., source_path=str(path))`; sorgente assente → `[]` + warning `memory_capture_source_absent` (FR-006/007); `read_session(ref)` apre il file, itera riga per riga best-effort: skip riga vuota/non-JSON (warning `memory_capture_unparsable_line` con numero riga), estrae turni da eventi con `message.role in {"user","assistant"}` (block `text`/`thinking`, ignora `tool_use`/`tool_result`/altri), `timestamp` ISO → `ts` epoch float o `None`, ritorna `TranscriptContent`; tutta la conoscenza host-specifica (encoding path, nomi campi JSONL, tipi block) vive solo qui (Principio X, D3)
- [X] T024 [US3] Aggiornare `src/sertor_core/composition.py` (T010): nella `build_capture_adapter`, l'import lazy di `ClaudeCodeCaptureAdapter` avviene dentro la funzione; derivare `project_source_dir` da `settings` (es. `settings.claude_projects_dir` se aggiunta, oppure derivare dall'`index_dir` del progetto con logica coerente con D3 e D5 — path encoding: sostituire separatori del `cwd` con `-`); se `project_source_dir` non e' configurabile, aggiungere campo opzionale `Settings.claude_projects_dir: Path | None` (default `None` → `~/.claude/projects/<encoded-cwd>`) con env `SERTOR_CLAUDE_PROJECTS_DIR`
- [X] T025 [US3] Verificare in `src/sertor_core/services/memory_archive.py` (T009) che non esistano rami condizionali sull'identita' dell'host (`if adapter.kind == "claude-code"` o simili); il servizio usa solo `adapter.list_sessions()` e `adapter.read_session(ref)` senza ispezionare `kind` (FR-005, SC-005)

**Checkpoint US3**: host-agnosticita' verificata con >=2 mock adapter; adapter Claude Code testato su
JSONL sintetici offline.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: test end-to-end offline, allineamento esportazioni, verifica gitignore, lint.

**Dipende da**: US1 (T011-T015), US2 (T016-T020), US3 (T021-T025).

- [X] T026 [P] Creare `tests/unit/test_memory_archive_e2e.py`: test end-to-end offline con `tmp_path` e mock adapter — flusso completo `build_memory_archiver(settings) → archive_all()` con `memory_enabled=True`; verifica tutti i SC mappati al quickstart: SC-001 (N record), SC-002 (idempotenza), SC-003 (off=0 scritture), SC-004 (0 segreti in chiaro), SC-005 (2 adapter), SC-006 (conservazione), SC-007 (store guasto non-fatale); nessuna rete, nessun Claude Code reale
- [X] T027 [P] Verificare che `<index_dir>/memory.sqlite` sia coperto dalle regole gitignore esistenti (`**/.index/` e `**/.index-*/` in `.gitignore` righe 21-25) senza nuove righe — verifica esplicita come annotato in D5/plan.md; aggiungere commento esplicativo nel test o nel plan se non gia' presente
- [X] T028 [P] Aggiungere ai test di composition (`tests/unit/test_composition.py`) la verifica che con `memory_enabled=False` nessun import di `ClaudeCodeCaptureAdapter` avvenga a livello di modulo e che `build_memory_archiver` ritorni `None`; con `memory_enabled=True` e adapter ignoto → `ConfigError` con messaggio che elenca i valori ammessi
- [X] T029 Eseguire `uv run ruff check . --fix` e correggere eventuali errori di lint in tutti i file nuovi (`domain/memory.py`, `observability/scrub.py`, `adapters/capture/claude_code.py`, `adapters/memory/archive.py`, `services/memory_archive.py`, file di test); verificare che `uv run pytest -m "not cloud"` passi integralmente

**Checkpoint Polish**: suite offline verde, gitignore verificato, lint pulito.

---

## Dependencies & Execution Order

### Dipendenze tra fasi

- **Phase 1 (Setup)**: nessuna dipendenza — inizia subito.
- **Phase 2 (Foundational)**: dipende da Phase 1 (T001-T003). Blocca tutte le user story.
- **Phase 3 (US1 P1)**: dipende da Phase 2. Nessuna dipendenza da US2/US3.
- **Phase 4 (US2 P2)**: dipende da Phase 2. Nessuna dipendenza da US1/US3.
- **Phase 5 (US3 P3)**: dipende da Phase 2. Nessuna dipendenza da US1/US2.
- **Phase 6 (Polish)**: dipende da US1+US2+US3 (o dal sottoinsieme completato).

### Dipendenze interne alla fase Foundational

```
T001 (pkg capture/) ──┐
T002 (pkg memory/) ───┤
T003 (Settings 4 manopole) ─► T005 (domain/memory.py) ─► T006 (ports.py)
                               T005 ─► T008 (archive.py)
                               T005 + T007 (scrub.py) ─► T009 (service)
                               T006 + T008 + T009 ─► T010 (composition)
T007 (scrub.py) [parallelo a T005/T006]
```

### Dipendenze interne alle user story

**US1**: T011 [P], T012 [P] (test) → T013, T014, T015 (impl, in ordine)
**US2**: T016 [P], T017 [P] (test) → T018, T019, T020 (impl, in ordine)
**US3**: T021 [P], T022 [P] (test) → T023, T024, T025 (impl, in ordine)

### Dipendenza critica

`T010` (composition wiring) e' l'ultimo prerequisito foundational: nessuna user story puo' essere
testata end-to-end prima che `build_memory_archiver` sia cablato. I test di singolo componente
(T011, T016, T021) possono iniziare appena il componente relativo e' pronto (T008, T007, T006/T023
rispettivamente), ma il test E2E (T026) richiede T010.

---

## Parallel Execution Examples

### Phase 2 — Foundational (dopo T001-T003)

```
T005 (domain/memory.py)        — prerequisito per T006/T008/T009
T007 (scrub.py)                — parallelo a T005 [P]
                       ↓
T006 (ports.py) [P]  T008 (archive.py) [P]     ← dipendono da T005
                       ↓
                    T009 (service)               ← dipende da T005+T007+T006+T008
                       ↓
                    T010 (composition)
```

### Phase 3 — US1 (dopo Foundational)

```
T011 (test store) [P]    T012 (test service) [P]    ← parallelizzabili
         ↓                        ↓
       T013              T014              T015      ← sequenziali (stesso file)
```

### Phase 4 — US2 (dopo Foundational, parallelo a US1)

```
T016 (test scrub) [P]    T017 (test privacy) [P]    ← parallelizzabili
         ↓                        ↓
       T018              T019              T020      ← sequenziali
```

### Phase 5 — US3 (dopo Foundational, parallelo a US1/US2)

```
T021 (test adapter) [P]  T022 (test 2-adapter) [P]  ← parallelizzabili
         ↓                        ↓
       T023              T024              T025      ← sequenziali
```

---

## Implementation Strategy

### MVP First (User Story 1 soltanto)

1. Completare Phase 1: Setup (T001-T004)
2. Completare Phase 2: Foundational (T005-T010) — CRITICO, blocca tutto
3. Completare Phase 3: US1 (T011-T015)
4. **STOP e VALIDA**: `uv run pytest tests/unit/test_memory_archive_store.py tests/unit/test_memory_archive_service.py -q` — deve passare interamente
5. La feature e' consegnabile come MVP: archivio idempotente e conservato funzionante

### Consegna incrementale

1. Setup + Foundational → fondamenta pronte
2. US1 → archivio idempotente (MVP!), testabile indipendentemente
3. US2 → scrub + privacy-by-default, testabile indipendentemente (aggiunge garanzia di sicurezza)
4. US3 → adapter Claude Code + host-agnosticita', testabile indipendentemente (habilita il dogfooding)
5. Polish → suite completa verde

### Strategia parallela (due sviluppatori)

Dopo il completamento di Foundational:
- Sviluppatore A: US1 (T011-T015) + US2 (T016-T020) in sequenza
- Sviluppatore B: US3 (T021-T025) in parallelo

Le tre storie non condividono file di implementazione (solo importano da Foundational): nessun
conflitto di merge.

---

## Notes

- **[P] tasks** = file diversi, nessuna dipendenza da task incompleti nella stessa fase
- **[Story]** = traceability verso la user story in spec.md
- **Stdlib-only** nel corpo (`sqlite3`, `json`, `re`, `hashlib`, `pathlib`, `datetime`); zero dipendenze nuove
- **Import lazy** nelle `build_*` di composition: l'import di `ClaudeCodeCaptureAdapter` avviene solo dentro la funzione, non a livello di modulo
- **Default-off**: `SERTOR_MEMORY=false` per default → nessun adapter, nessun file, zero overhead
- **Non-distruttivo**: la sorgente Claude Code e' di sola lettura; l'archivio e' append-only conservativo
- **Verifica gitignore**: `<index_dir>/memory.sqlite` e' gia' coperto da `**/.index/` — nessuna modifica al `.gitignore` necessaria (D5)
- Pattern riusati: `SqliteObservabilityStore` (`observability/store.py`), `EmbeddingCache` (`adapters/embeddings/cache.py`), `_validated_engine` (`composition.py`) per i `ConfigError`
- Ogni test usa `tmp_path` per lo store, adapter mock (senza ereditarieta' — structural typing), file JSONL sintetici per il parser; nessuna rete, nessun Claude Code reale (Principio V)
