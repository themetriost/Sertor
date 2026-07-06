---
description: "Task list for feature 036 — Aggancio della distillazione all'archivio episodico (FEAT-003)"
---

# Tasks: Aggancio della distillazione all'archivio episodico (FEAT-003)

**Input**: Artefatti di design da `specs/036-aggancio-distillazione/`

**Documenti letti**: plan.md (richiesto), spec.md (richiesto), research.md (D-1..D-8),
data-model.md, contracts/cli-memory-show-list.md, contracts/memory-reader.md, quickstart.md

**Branch**: `036-aggancio-distillazione`

**Organizzazione**: task raggruppati per user story; ogni storia è un incremento testabile in modo
indipendente. Tre user story: US1 (recupero transcript, P1 — cuore MVP), US2 (elenco sessioni, P2),
US3 (garanzia no-automazione + gate, P1 — verifica di vincolo). US3 è molto leggera (perlopiù test
e verifica documentale, nessun codice nuovo di logica).

## Formato: `[ID] [P?] [Story] Descrizione con path`

- **[P]**: eseguibile in parallelo ad altri [P] della stessa fase (file diversi, nessuna dipendenza)
- **[Story]**: user story di appartenenza (US1/US2/US3)
- Path file sempre espliciti e assoluti rispetto alla root del repo

---

## Phase 1: Setup

**Scopo**: nessuna struttura da inizializzare (feature additiva, cartelle e moduli esistono tutti).
La fase registra le sole verifiche preliminari bloccanti: confermare lo stato del codebase e
leggere i contratti di riferimento prima di toccare qualsiasi file.

- [X] T001 Verificare che il branch `036-aggancio-distillazione` sia attivo e pulito (git status)
- [X] T002 [P] Leggere `src/sertor_core/domain/errors.py` per individuare la posizione esatta dove inserire `SessionNotFoundError` (accanto a `IndexNotFoundError`/`InvalidTimeWindowError`)
- [X] T002b [P] Leggere `src/sertor_core/domain/memory.py` per individuare la posizione esatta dove inserire `SessionSummary` (accanto alle dataclass esistenti `ArchivedSession`/`TranscriptTurn`)
- [X] T003 [P] Leggere `src/sertor_core/config/settings.py` per individuare la posizione esatta di `episodic_limit` dove affiancare `memory_list_limit`
- [X] T004 [P] Leggere `src/sertor_core/composition.py` per individuare il blocco `build_memory_archiver`/`build_episodic_search` dove inserire `build_memory_reader`

**Checkpoint**: struttura confermata, posizioni di inserimento note — si procede con Foundational.

---

## Phase 2: Foundational (Prerequisiti bloccanti)

**Scopo**: entità di dominio, eccezione, manopola e factory di composition. Tutti i task di questa
fase DEVONO essere completati prima di iniziare qualsiasi user story. T005 e T006 sono parallelizzabili
(file diversi, nessuna dipendenza reciproca); T007 dipende da T006 (usa `SessionSummary`); T008 dipende
da T004+T007 (usa `MemoryArchive` + `SessionSummary`).

**ATTENZIONE**: nessuna storia può iniziare prima che questa fase sia completa.

- [X] T005 [P] Aggiungere `SessionNotFoundError(session_key: str)` come sottoclasse di `SertorError` in `src/sertor_core/domain/errors.py` — messaggio azionabile «session not found: {session_key}; use `memory list` to see available sessions»; coerente con `IndexNotFoundError`/`InvalidTimeWindowError`
- [X] T006 [P] Aggiungere `Settings.memory_list_limit: int = 20` (letto da `SERTOR_MEMORY_LIST_LIMIT`) in `src/sertor_core/config/settings.py`, accanto a `episodic_limit`; aggiornare `Settings.load()` per leggere la variabile d'ambiente
- [X] T007 Aggiungere dataclass `SessionSummary(session_key: str, captured_at: float, turn_count: int)` — `@dataclass(frozen=True)`, nessun import SDK — in `src/sertor_core/domain/memory.py`, accanto ad `ArchivedSession`/`TranscriptTurn`; aggiornare gli export da `src/sertor_core/domain/__init__.py` se necessario
- [X] T008 Aggiungere `build_memory_reader(settings) -> MemoryArchive | None` in `src/sertor_core/composition.py` (accanto a `build_memory_archiver`/`build_episodic_search`): gate `if not settings.memory_enabled: return None`; abilitata → `MemoryArchive(settings.index_dir)`; import lazy del componente; esportare da `src/sertor_core/__init__.py`

**Checkpoint**: entità + factory disponibili — le user story possono iniziare (US1 e US2 in parallelo se
si dispone di due sviluppatori; US3 può iniziare subito a verificare i vincoli documentali).

---

## Phase 3: User Story 1 — Recuperare una conversazione passata per distillarla (Priority: P1) — MVP

**Goal**: dato il `session_key` di una sessione archiviata, `sertor-rag memory show <session_key>
[--json]` restituisce il transcript completo (tutti i turni con ruolo, timestamp, testo non troncato).
not-found → exit 1 + messaggio azionabile. Gate privacy attivo (FR-008/FR-009).

**Independent Test**: con `SERTOR_MEMORY=true` e almeno una sessione archiviata, eseguire
`sertor-rag memory show <session_key>` restituisce tutti i turni in ordine senza troncatura.
Verificabile da solo, senza US2 o US3.

### Test per User Story 1

- [X] T009 [P] [US1] Aggiungere test unitari per `format_session_transcript` (umano e `--json`) in `tests/unit/test_cli_output_session.py`: sessione con N turni → output ordinato, testo intero, equivalenza umano↔JSON; sessione vuota → intestazione + `(empty session)`
- [X] T010 [P] [US1] Aggiungere test unitari per l'handler `_cmd_memory_show` con core mockato in `tests/unit/test_cli_memory_show_list.py`: gate `None → ConfigError` exit 1; not-found → `SessionNotFoundError` exit 1; sessione vuota → exit 0; successo con N turni → exit 0; flag `--json`

### Implementazione User Story 1

- [X] T011 [US1] Aggiungere `format_session_transcript(session: ArchivedSession, *, json: bool = False) -> str` in `src/sertor_core/cli/output.py`: umano = intestazione (session_key, captured_at ISO-8601, turns, adapter_kind) + turni `[index] role @ts\n    text` (riuso `_iso_utc`); JSON = dict con `session_key`/`project_id`/`captured_at`/`adapter_kind`/`turns` (lista di `{index, role, ts, text}`); nessuna troncatura; sessione vuota → intestazione + `(empty session)` / `turns: []`
- [X] T012 [US1] Aggiungere sotto-comando `memory show` al gruppo `memory` in `src/sertor_core/cli/__main__.py`: sub-subparser argparse con `session_key` (posizionale, richiesto) + `--json`; `set_defaults(handler=_cmd_memory_show)`; helper `_require_memory_reader(settings) -> MemoryArchive` che chiama `build_memory_reader` e solleva `ConfigError` se ritorna `None` (identico a `_require_archiver`/`_require_episodic_search`)
- [X] T013 [US1] Implementare `_cmd_memory_show(args)` in `src/sertor_core/cli/__main__.py`: `setup_logging(args)` → `settings = _resolve_settings(args)` → `enable_observability(settings)` → `reader = _require_memory_reader(settings)` → `session = reader.get(args.session_key)` → se `None`: `raise SessionNotFoundError(args.session_key)` → altrimenti `print(output.format_session_transcript(session, json=args.json))`; emettere evento `log_event("memory_show", session_key=..., turn_count=..., found=True/False)` con conteggi (mai contenuto)
- [X] T014 [US1] Aggiungere il metodo `MemoryArchive.list_recent(limit: int) -> tuple[SessionSummary, ...]` in `src/sertor_core/adapters/memory/archive.py`: query `SELECT session_key, captured_at, metadata FROM sessions ORDER BY captured_at DESC LIMIT ?`; `turn_count` da `json.loads(metadata)["turn_count"]` con fallback `0` difensivo se chiave assente; degradazione non-fatale su `sqlite3.Error` → `()` + warning `memory_archive_unavailable`; `limit <= 0` → `()` (guard)

> Nota: T014 appartiene alla Foundational per responsabilità (metodo su `MemoryArchive`), ma è
> inserito qui perché non blocca US1 (`show` riusa solo `get` già esistente) ed è prerequisito di US2.
> È parallelizzabile con T011/T012.

**Checkpoint**: `memory show` funzionante e testabile indipendentemente — US1 completa.

---

## Phase 4: User Story 2 — Scoprire quale conversazione recuperare (Priority: P2)

**Goal**: `sertor-rag memory list [-k N] [--json]` elenca le sessioni archiviate più recenti
(chiave, data, #turni), ordinate recency-first, entro il limite; archivio vuoto → stato vuoto
esplicito + exit 0. Dipende da T014 (`list_recent`) già implementato in Phase 3.

**Independent Test**: con 3+ sessioni archiviate, `memory list` le restituisce dalla più recente,
con chiave/data/#turni corretti, entro il limite richiesto. Verificabile senza US1 (ma T014 deve
essere completo).

### Test per User Story 2

- [X] T015 [P] [US2] Aggiungere test unitari per `MemoryArchive.list_recent` in `tests/unit/test_memory_archive_list_recent.py` (SQLite temporaneo reale, no mock): recency-first con 3 sessioni in tempi diversi; rispetta il limite; `turn_count` corretto da metadata; fallback `0` se `turn_count` assente in metadata; archivio assente → `()`; store ko (file corrotto) → `()` + warning; `limit <= 0` → `()`
- [X] T016 [P] [US2] Aggiungere test unitari per `format_session_list` (umano e `--json`) in `tests/unit/test_cli_output_session.py`: lista con 2 voci → output indicizzato con session_key/captured_at/turn_count; lista vuota → `(no sessions)` / `[]`; equivalenza umano↔JSON
- [X] T017 [P] [US2] Aggiungere test unitari per l'handler `_cmd_memory_list` con core mockato in `tests/unit/test_cli_memory_show_list.py`: gate `None → ConfigError` exit 1; archivio vuoto → exit 0 + `(no sessions)`; flag `-k/--limit` sovrascrive il default; flag `--json`

### Implementazione User Story 2

- [X] T018 [US2] Aggiungere `format_session_list(summaries: tuple[SessionSummary, ...], *, json: bool = False) -> str` in `src/sertor_core/cli/output.py`: umano = lista indicizzata `[N] session=<key>  @=<ISO-8601>  turns=<count>` (riuso `_iso_utc`); lista vuota → `(no sessions)`; JSON = lista di `{session_key, captured_at, turn_count}`; lista vuota → `[]`; equivalenza informativa umano↔JSON
- [X] T019 [US2] Aggiungere sotto-comando `memory list` al gruppo `memory` in `src/sertor_core/cli/__main__.py`: sub-subparser con `-k/--limit N` (int, `dest=k`, default `None`) + `--json`; `set_defaults(handler=_cmd_memory_list)`
- [X] T020 [US2] Implementare `_cmd_memory_list(args)` in `src/sertor_core/cli/__main__.py`: `setup_logging` → `settings` → `enable_observability` → `reader = _require_memory_reader(settings)` → `limit = args.k if args.k is not None else settings.memory_list_limit` → `summaries = reader.list_recent(limit)` → `print(output.format_session_list(summaries, json=args.json))`; emettere evento `log_event("memory_list", count=len(summaries), limit=limit)` (mai contenuto)

**Checkpoint**: `memory list` funzionante e testabile indipendentemente — US2 completa. Con US1 si
copre il workflow scoperta → recupero → distillazione end-to-end.

---

## Phase 5: User Story 3 — Distillazione disciplinata: backup, non automatismo (Priority: P1)

**Goal**: garanzia verificabile che la feature non introduca alcun trigger automatico di
distillazione; il gating privacy è consistente con feature 035; la procedura `distill` documentata
indica il percorso corretto. Questa fase non introduce nuovo codice di logica: è principalmente
verifica di vincolo e aggiornamento documentale.

**Independent Test**: (a) con la feature consegnata, terminare una sessione non avvia alcuna
distillazione (verificabile per ispezione: hook `SessionEnd` + rituale di step invariati); (b) con
`SERTOR_MEMORY` non configurato, `memory show`/`memory list` falliscono con errore azionabile exit 1;
(c) la procedura `distill.md` descrive il percorso «recupera sessione mirata → condensa →
distilla».

### Test per User Story 3

- [X] T021 [P] [US3] Aggiungere test in `tests/unit/test_cli_memory_show_list.py`: verificare che `build_memory_reader(settings_con_memory_enabled_false)` ritorni `None`; verificare che `_cmd_memory_show`/`_cmd_memory_list` con reader `None` sollevano `ConfigError` con messaggio che nomina `SERTOR_MEMORY`

### Implementazione / Verifica User Story 3

- [X] T022 [P] [US3] Verificare per ispezione che `src/sertor_core/cli/__main__.py` (hook `SessionEnd`, `.claude/hooks/memory-capture.ps1`) e il rituale di step in `CLAUDE.md` siano invariati rispetto alla feature 035 — nessun nuovo trigger di distillazione automatica introdotto dai task precedenti; annotare l'esito nel commento del task
- [X] T023 [US3] Aggiornare `.claude/skills/wiki-author/ops/distill.md` (modalità «from conversation», righe ~16-22): sostituire il riferimento al «brief scritto a mano» con la procedura «(1) individua la sessione con `sertor-rag memory list` o `memory search`; (2) recupera il transcript con `sertor-rag memory show <session_key>`; (3) portalo in contesto, condensa (giudizio del flusso principale) e distilla nelle pagine wiki»; aggiungere avviso vincolo FR-013 (mai sull'intero archivio, mai per-turno/per-sessione)
- [X] T024 [P] [US3] Documentare il no-op di FR-011 in `packages/sertor/src/sertor_installer/assets/claude-md-block.md`: opzionale — valutare se estendere la riga `distill` esistente con «(attinge a una sessione archiviata via `sertor-rag memory show`)»; se si sceglie di non farlo, aggiungere un commento inline nell'asset o nella research D-6 già aggiornata che segnali lo stato (vedi research D-6 per il razionale del no-op)

**Checkpoint**: vincolo FR-013 verificato per ispezione; gating consistente con feature 035 testato;
`distill.md` aggiornata — US3 completa.

---

## Phase 6: Polish e Concern Trasversali

**Scopo**: verifica della suite, coerenza di stile, export da `__init__.py`, verifica quickstart.

- [X] T025 [P] Verificare ed eventualmente aggiornare gli export da `src/sertor_core/__init__.py` per `build_memory_reader` e da `src/sertor_core/domain/__init__.py` per `SessionSummary` e `SessionNotFoundError`
- [X] T026 [P] Eseguire l'intera suite `uv run pytest -m "not cloud"` e verificare che sia verde (nessuna regressione su FEAT-001/002/035); correggere eventuali import mancanti o conflitti di nome
- [X] T027 [P] Verificare lint `uv run ruff check .` e correggere eventuali segnalazioni (line-length 100, regole E/F/I/UP/B)
- [X] T028 Eseguire la verifica rapida del quickstart (`specs/036-aggancio-distillazione/quickstart.md` §5): `SERTOR_MEMORY=true sertor-rag memory list -k 3 --json | python -m json.tool` e `sertor-rag memory show qualsiasi-chiave` con memoria spenta → exit 1 azionabile; verificare che il dogfood (`~5000 turni`) risponda in tempi percepibilmente immediati (RNF-3)
- [X] T029 [P] Verificare che `src/sertor_core/domain/ports.py` non abbia subito modifiche — il numero di `Protocol` deve restare invariato (SC-007); annotare l'esito

---

## Dipendenze e Ordine di Esecuzione

### Dipendenze tra fasi

- **Phase 1 (Setup)**: nessuna dipendenza — inizia subito
- **Phase 2 (Foundational)**: dipende da Phase 1 — blocca tutte le user story
- **Phase 3 (US1)**: dipende da Phase 2 (T005/T006/T007/T008 completi)
- **Phase 4 (US2)**: dipende da Phase 2 + T014 (list_recent, inserito in Phase 3)
- **Phase 5 (US3)**: dipende da Phase 2; T023 e T024 meglio dopo Phase 3 (verifica il comportamento reale)
- **Phase 6 (Polish)**: dipende da Phase 3 + 4 + 5

### Dipendenze interne per user story

**US1 — dipendenze interne**:
- T009/T010 [P] (test) e T011/T012 [P] (output + parser) sono parallelizzabili tra loro
- T013 (handler show) dipende da T011 (format_session_transcript) + T012 (parser + helper)
- T014 (list_recent) è parallelizzabile con T011/T012 (file diverso)

**US2 — dipendenze interne**:
- T015/T016/T017 [P] (test) e T018/T019 [P] (output + parser) sono parallelizzabili tra loro
- T020 (handler list) dipende da T018 (format_session_list) + T019 (parser) + T014 (list_recent)

**US3 — dipendenze interne**:
- T021/T022/T024 [P] eseguibili in parallelo
- T023 (distill.md) indipendente ma beneficia della visione completa di US1 (meglio dopo T013)

### Dipendenze tra storie

- **US1 (P1)**: può iniziare dopo Phase 2 — nessuna dipendenza da US2/US3
- **US2 (P2)**: può iniziare dopo Phase 2 + T014 (list_recent, sviluppato in parallelo con US1)
- **US3 (P1)**: può iniziare dopo Phase 2; T022 e T023 beneficiano di Phase 3 completa

---

## Esempio di Esecuzione Parallela

### Esecuzione sequenziale (singolo sviluppatore, ordine raccomandato)

```
Phase 1: T001 → T002 T002b T003 T004 [paralleli]
Phase 2: T005 T006 [paralleli] → T007 → T008 → T014
US1:     T009 T010 T011 T012 [paralleli] → T013
US2:     T015 T016 T017 T018 T019 [paralleli] → T020
US3:     T021 T022 T024 [paralleli] → T023
Polish:  T025 T026 T027 T029 [paralleli] → T028
```

### Esecuzione parallela (due sviluppatori dopo Phase 2)

```
Sviluppatore A: US1 (T009 → T011/T012/T014 → T013)
Sviluppatore B: US2 (T015/T016/T017 → T018/T019 → T020) + US3 (T021/T022/T023/T024)
→ Polish congiunto: T025/T026/T027/T028/T029
```

---

## Criteri di Test Indipendenti per User Story

### US1 — Verifica indipendente

Con `SERTOR_MEMORY=true` e almeno una sessione archiviata in `<index_dir>/memory.sqlite`:

```bash
# Transcript completo
sertor-rag memory show <session_key>
# → tutti i turni in ordine, testo completo, exit 0

# Not-found → exit 1 azionabile
sertor-rag memory show chiave-inesistente ; echo "exit=$?"
# → error: session not found: chiave-inesistente; use `memory list` ... ; exit=1

# JSON
sertor-rag memory show <session_key> --json | python -m json.tool
# → struttura parseable con turns array

# Gate privacy
sertor-rag memory show <session_key> ; echo "exit=$?"  # senza SERTOR_MEMORY
# → error: memory is disabled; set SERTOR_MEMORY=true ; exit=1
```

### US2 — Verifica indipendente

Con `SERTOR_MEMORY=true` e almeno 3 sessioni archiviate:

```bash
# Elenco recente
sertor-rag memory list
# → sessioni ordinate dalla più recente, con key/data/turns

# Limite
sertor-rag memory list -k 2
# → al più 2 voci

# Archivio vuoto (o limit=0) → exit 0, no errore
sertor-rag memory list -k 0
# → (no sessions)

# JSON
sertor-rag memory list --json | python -m json.tool
# → array di oggetti con session_key/captured_at/turn_count
```

### US3 — Verifica indipendente (ispezione)

```bash
# Gate privacy consistente con feature 035
sertor-rag memory list ; echo "exit=$?"           # senza SERTOR_MEMORY → exit 1
sertor-rag memory archive ; echo "exit=$?"        # idem (baseline già funzionante)

# Nessun trigger automatico: verificare per ispezione
# - .claude/hooks/memory-capture.ps1: invoca solo `memory archive`, NON `distill`
# - Il rituale di step in CLAUDE.md: la distillazione è giudizio manuale, non automatica

# distill.md aggiornata
# Leggere .claude/skills/wiki-author/ops/distill.md e verificare che la modalità
# «from conversation» citi `memory list`/`memory show` invece del brief a mano
```

---

## Strategia di Implementazione

### MVP (solo US1)

1. Completare Phase 1: Setup (verifiche preliminari)
2. Completare Phase 2: Foundational — `SessionNotFoundError` + `SessionSummary` + `memory_list_limit` + `build_memory_reader` (T005..T008); aggiungere anche `list_recent` (T014) per non lasciare `MemoryArchive` incompleto
3. Completare Phase 3: US1 — `format_session_transcript` + sotto-comando `memory show` + handler + test
4. **STOP e VALIDA**: `sertor-rag memory show` funziona end-to-end; gate privacy attivo; suite verde
5. Consegna MVP: già copre il caso d'uso principale (distillazione da archivio)

### Consegna Incrementale

1. Phase 1 + 2 → fondamenta pronte (incluso `list_recent`)
2. Phase 3 (US1) → MVP: `memory show` → distillazione possibile senza brief a mano
3. Phase 4 (US2) → discovery: `memory list` → workflow completo scoperta-recupero-distillazione
4. Phase 5 (US3) → vincolo documentato e verificato; `distill.md` aggiornata
5. Phase 6 (Polish) → suite verde, lint, quickstart validato

Ogni incremento non rompe il precedente; con la memoria spenta il comportamento rimane identico a
prima della feature (FR-012).

---

## Note

- `[P]` = file diversi, nessuna dipendenza reciproca — eseguibili in parallelo
- `[US1/US2/US3]` = appartenenza alla user story per tracciabilità
- I test sono richiesti dalla specifica (FR-012: additivo, suite deve restare verde; pattern già
  stabilito da feature 035 `test_cli_memory.py`/`test_cli_search.py`)
- La feature è puramente additiva: nessun file esistente viene riscritto, solo esteso
- Nessuna nuova porta di dominio (`domain/ports.py` invariato — SC-007)
- `list_recent` (T014) è tecnicamente un metodo Foundational ma è inserito in Phase 3 perché non
  blocca US1 (che riusa solo `get`) ed è prerequisito di US2: parallelizzabile con i task US1
- Commit raccomandato dopo ogni task o gruppo logico (Phase 2 completa, US1 completa, ecc.)
- Evitare: descrizioni vaghe, modifica di file nella stessa riga da due task paralleli,
  dipendenze cross-story non dichiarate
