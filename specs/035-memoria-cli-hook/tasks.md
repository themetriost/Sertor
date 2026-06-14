---
description: "Task list — Superficie CLI memoria + cattura automatica a fine sessione (035)"
feature: "035-memoria-cli-hook"
branch: "035-memoria-cli-hook"
spec: "specs/035-memoria-cli-hook/spec.md"
plan: "specs/035-memoria-cli-hook/plan.md"
---

# Tasks: Superficie CLI memoria + cattura automatica a fine sessione (035)

**Input**: Artefatti di design in `specs/035-memoria-cli-hook/`

**Prerequisiti letti**: plan.md, spec.md, research.md, data-model.md, contracts/cli-memory.md,
contracts/hook-session-end.md, quickstart.md.

**Principio guida**: thin consumer — i comandi delegano interamente al core via le factory
`build_memory_archiver`/`build_episodic_search`; nessuna logica di archiviazione/ricerca
reimplementata. Core (`services/`, `composition.py`, `domain/`, `config/`) invariato (FR-019).

## Formato: `[ID] [P?] [Story?] Descrizione con path file`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza da task incompleti)
- **[Story]**: user story di appartenenza (US1 / US2 / US3)
- Path espliciti in ogni task

---

## Phase 1: Setup

**Nota**: nessuna nuova infrastruttura di progetto da creare. Il CLI (`src/sertor_core/cli/`),
le dipendenze (solo stdlib + argparse), i target di test (`tests/unit/`) e gli hook
(`.claude/hooks/`) esistono già. La fase è ridotta al solo controllo di disponibilità.

- [x] T001 Verificare che `src/sertor_core/cli/__main__.py` e `src/sertor_core/cli/output.py` siano presenti e allineati al design (import `build_memory_archiver`, `build_episodic_search` in `src/sertor_core/composition.py`)
- [x] T002 [P] Verificare che `tests/unit/test_cli_search.py` sia presente come modello di stile da seguire (pattern monkeypatch, fixture `_no_dotenv`, helper `_run`)

**Checkpoint**: infrastruttura verificata — si può procedere con la Foundational phase.

---

## Phase 2: Foundational (prerequisiti bloccanti trasversali)

**Scopo**: aggiungere i prerequisiti che tutte e tre le user story richiedono prima di poter
essere implementate e testate indipendentemente.

**Struttura argparse (D1)**: gruppo `memory` con sub-subparser `archive`/`search`; dispatch
`main()` invariato (ogni sub-subparser registra il proprio handler via `set_defaults`).

**Gate di privacy (D2)**: helper `_require_archiver`/`_require_episodic_search` che intercettano
il `None` delle factory e sollevano `ConfigError` azionabile (exit 1).

**Funzioni pure di output (D5)**: `format_archive_report` e `format_memory_results` in
`src/sertor_core/cli/output.py`, pure e testabili senza terminale.

**Import delle factory**: aggiungere `build_memory_archiver`, `build_episodic_search` all'import
di `src/sertor_core/cli/__main__.py` da `sertor_core.composition`.

- [x] T003 Aggiungere `build_memory_archiver`, `build_episodic_search` agli import da `sertor_core.composition` in `src/sertor_core/cli/__main__.py`
- [x] T004 Aggiungere il parser di primo livello `memory` (`sub.add_parser("memory", ...)`) con sub-subparser `msub = p_memory.add_subparsers(dest="memory_command", required=True, metavar="subcommand")` in `src/sertor_core/cli/__main__.py` — dispatch `main()` invariato
- [x] T005 Aggiungere gli helper di gate `_require_archiver(settings)` e `_require_episodic_search(settings)` in `src/sertor_core/cli/__main__.py` (intercettano `None` → `ConfigError("memory is disabled; set SERTOR_MEMORY=true to enable archiving", key="SERTOR_MEMORY")`)
- [x] T006 [P] Aggiungere `format_archive_report(report: ArchiveRunReport, *, json: bool) -> str` in `src/sertor_core/cli/output.py` — umano: `archived=N skipped=N errors=N`; JSON: `{"archived": N, "skipped": N, "errors": N}`
- [x] T007 [P] Aggiungere `format_memory_results(results: EpisodicResults, settings: Settings, *, json: bool) -> str` in `src/sertor_core/cli/output.py` — umano: blocchi numerati `[i] score=…  role=…  session=…  turn=…  @=<iso-utc>` + snippet indentato; JSON: array di oggetti; `(no results)` se vuoto; `captured_at` umano = ISO-8601 UTC (`time.gmtime` + `strftime`), JSON = epoch float

**Nota**: T006 e T007 sono [P] perché modificano lo stesso file `output.py` MA su funzioni distinte
e non dipendenti l'una dall'altra; se assegnati allo stesso sviluppatore, eseguirli in sequenza.

**Checkpoint**: parser `memory`, gate e funzioni di output pronti — US1, US2, US3 possono
iniziare in parallelo.

---

## Phase 3: User Story 1 — Archiviare le conversazioni del progetto (P1) — MVP

**Goal**: il comando `sertor-rag memory archive` delega a `archive_all()` e stampa il report
`archived/skipped/errors`; idempotente; gate off → errore azionabile exit 1.

**Dipende da**: T003, T004, T005, T006.

**Independent Test (SC-001, FR-002/003/004)**:
Con `SERTOR_MEMORY=true` e sessioni non ancora archiviate, eseguire `sertor-rag memory archive`
e verificare che il report indichi sessioni archiviate; rilancio immediato → `archived=0` (tutte
saltate). Con `--json`, i conteggi sono identici in forma strutturata. Con `SERTOR_MEMORY` assente
o falso, exit 1 con messaggio che nomina `SERTOR_MEMORY=true`.

### Implementazione US1

- [x] T008 [US1] Aggiungere il parser `archive` (`msub.add_parser("archive", ...)`) con opzione `--json`, `--corpus`, flag di logging (`_add_logging_flags`), e `set_defaults(handler=_cmd_memory_archive)` in `src/sertor_core/cli/__main__.py`
- [x] T009 [US1] Implementare `_cmd_memory_archive(args)` in `src/sertor_core/cli/__main__.py`: chiama `_require_archiver(_resolve_settings(args))`, poi `archiver.archive_all()`, poi `print(output.format_archive_report(report, json=args.json))`

### Test US1

- [x] T010 [US1] Aggiungere test `test_memory_archive_human_output` in `tests/unit/test_cli_memory.py`: monkeypatch `build_memory_archiver` con fake che restituisce `ArchiveRunReport(archived=2, skipped=1, errors=0)`; verifica exit 0 e `archived=2` in stdout
- [x] T011 [US1] Aggiungere test `test_memory_archive_json_output` in `tests/unit/test_cli_memory.py`: stessa fake, `--json`, verifica `json.loads(out) == {"archived": 2, "skipped": 1, "errors": 0}`
- [x] T012 [US1] Aggiungere test `test_memory_archive_idempotent` in `tests/unit/test_cli_memory.py`: seconda fake con `archived=0, skipped=2`; verifica exit 0 e `archived=0` (nessun duplicato)
- [x] T013 [US1] Aggiungere test `test_memory_archive_gate_off_exit1` in `tests/unit/test_cli_memory.py`: `build_memory_archiver` restituisce `None`; verifica exit 1 e `SERTOR_MEMORY` in stderr

**Checkpoint US1**: `sertor-rag memory archive` funzionale e testato indipendentemente.

---

## Phase 4: User Story 2 — Ritrovare una conversazione da riga di comando (P1)

**Goal**: il comando `sertor-rag memory search <query>` delega a `EpisodicSearch.search()`,
formatta i risultati con sessione/ruolo/turno/snippet/score; `--since`/`--until`/`-k` applicati;
gate off → errore azionabile; sola lettura; stato vuoto onesto.

**Dipende da**: T003, T004, T005, T007. Può partire in parallelo con US1 dopo il Foundational.

**Independent Test (SC-002/003, FR-005/006/007/008/009)**:
Con archivio popolato (mock), query con parola presente → hit con tutti i campi attesi; finestra
temporale → zero fuori range; `-k 2` → al più 2 risultati; `--json` → array strutturato;
`--since` dopo `--until` → exit 1; query vuota o archivio assente → `(no results)` exit 0.

### Implementazione US2

- [x] T014 [US2] Aggiungere helper `_parse_time(value: str) -> float` in `src/sertor_core/cli/__main__.py`: accetta ISO-8601 (`YYYY-MM-DD` o `YYYY-MM-DDTHH:MM:SS`) o epoch float, restituisce epoch UTC; uso in argparse `type=_parse_time`
- [x] T015 [US2] Aggiungere il parser `search` (`msub.add_parser("search", ...)`) con argomento posizionale `query`, `--since`/`--until` (tipo `_parse_time`, default `None`), `--order` (choices `relevance`/`recency`, default `relevance`), `-k`/`--limit` (tipo `int`, default `None`), `--json`, `--corpus`, flag di logging e `set_defaults(handler=_cmd_memory_search)` in `src/sertor_core/cli/__main__.py`
- [x] T016 [US2] Implementare `_cmd_memory_search(args)` in `src/sertor_core/cli/__main__.py`: chiama `_require_episodic_search(_resolve_settings(args))`, costruisce `SearchQuery(text=args.query, since=args.since, until=args.until, order=args.order, limit=args.k or settings.episodic_limit, snippet_tokens=settings.episodic_snippet_tokens)`, chiama `episodic_search.search(query)`, stampa `output.format_memory_results(results, settings, json=args.json)`; `InvalidTimeWindowError` propagato come `SertorError` → exit 1 via `main()`

### Test US2

- [x] T017 [US2] Aggiungere test `test_memory_search_human_output` in `tests/unit/test_cli_memory.py`: monkeypatch `build_episodic_search` con fake che restituisce `EpisodicResults` con un `EpisodicHit`; verifica exit 0 e presenza di `score=`, `role=`, `session=`, `turn=`, `@=` in stdout
- [x] T018 [US2] Aggiungere test `test_memory_search_json_fields` in `tests/unit/test_cli_memory.py`: stessa fake, `--json`; `json.loads(out)` è lista con campi `{"session_key", "captured_at", "role", "turn_index", "snippet", "score"}`
- [x] T019 [US2] Aggiungere test `test_memory_search_k_limits` in `tests/unit/test_cli_memory.py`: fake restituisce 5 hit, invocazione con `-k 2`; verifica che `SearchQuery.limit == 2` ricevuto dalla fake
- [x] T020 [US2] Aggiungere test `test_memory_search_empty_results` in `tests/unit/test_cli_memory.py`: fake restituisce `EpisodicResults(hits=(), latency_ms=0.0)`; verifica exit 0 e `(no results)` in stdout
- [x] T021 [US2] Aggiungere test `test_memory_search_gate_off_exit1` in `tests/unit/test_cli_memory.py`: `build_episodic_search` restituisce `None`; verifica exit 1 e `SERTOR_MEMORY` in stderr
- [x] T022 [US2] Aggiungere test `test_memory_search_invalid_window_exit1` in `tests/unit/test_cli_memory.py`: fake che solleva `InvalidTimeWindowError`; verifica exit 1 e `error:` in stderr

**Checkpoint US2**: `sertor-rag memory search` funzionale e testato indipendentemente (giro
«archivia → ritrova» completo).

---

## Phase 5: User Story 3 — Cattura automatica a fine sessione (P1)

**Goal**: lo script `.claude/hooks/memory-capture.ps1` scatta a `SessionEnd`; pre-check
`SERTOR_MEMORY` → no-op exit 0; else invoca `sertor-rag memory archive`; `try/catch` → exit 0
sempre; voce in `.claude/settings.json` (additiva, accanto all'hook wiki).

**Dipende da**: T008, T009 (il comando `memory archive` deve essere operativo; l'hook lo invoca).
US3 è host-specifico (Claude Code, PowerShell); non dipende logicamente da US2.

**Independent Test (SC-004/005/006, FR-010/011/012/013/015)**:
Con `SERTOR_MEMORY` assente/falso, `.\.claude\hooks\memory-capture.ps1` → nessun output, exit 0.
Con `SERTOR_MEMORY=true`, lo script tenta l'archiviazione e restituisce comunque exit 0 anche in
caso di errore. Verifica manuale documentata in `quickstart.md` §3 (la logica PowerShell non
si può testare con `pytest`; il gate/no-op è verificabile con due comandi PowerShell).

### Implementazione US3

- [x] T023 [US3] Creare `.claude/hooks/memory-capture.ps1` (versionato): pre-check `$env:SERTOR_MEMORY` (match case-insensitive `true`/`1`/`yes`/`on`) → `exit 0` no-op se non abilitato; risoluzione root da `$env:CLAUDE_PROJECT_DIR` → `$hook.cwd` (stdin JSON) → `.`; `try { Push-Location $root; uv run sertor-rag memory archive 2>$null; Pop-Location } catch { try { Pop-Location } catch {} }`; `exit 0` SEMPRE; stile di `wiki-pending-check.ps1`
- [x] T024 [US3] Aggiungere la voce `SessionEnd` memory in `.claude/settings.json`: aggiungere al blocco `"SessionEnd"[0].hooks` l'oggetto `{ "type": "command", "shell": "powershell", "timeout": 15, "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/memory-capture.ps1')" }` accanto alla voce wiki esistente (additivo, non tocca l'hook wiki)

### Verifica US3 (manuale — documentata in quickstart.md §3)

- [x] T025 [US3] Verificare manualmente (PowerShell) che con `$env:SERTOR_MEMORY=$null` lo script `.\.claude\hooks\memory-capture.ps1` produca exit 0 e nessun output; con `$env:SERTOR_MEMORY='true'` lo script tenti l'archiviazione e restituisca comunque exit 0 anche simulando un errore

**Checkpoint US3**: hook operativo — la memoria si popola da sola a ogni fine sessione Claude Code.

---

## Phase 6: Polish e cross-cutting

**Scopo**: qualità del codice, copertura degli edge case residui, lint, verifica del quickstart.

- [x] T026 [P] Aggiungere test `test_memory_archive_json_gate_off` in `tests/unit/test_cli_memory.py`: `build_memory_archiver` → `None`, `--json`; verifica exit 1 e messaggio d'errore su stderr (edge case «output strutturato richiesto in caso di errore»)
- [x] T027 [P] Aggiungere test `test_memory_search_readonly` in `tests/unit/test_cli_memory.py`: verifica che la fake di `build_episodic_search` non abbia ricevuto chiamate di scrittura (l'archivio non viene modificato, FR-008)
- [x] T028 [P] Aggiungere il fixture `_no_dotenv` (stesso pattern di `test_cli_search.py`) in `tests/unit/test_cli_memory.py` per isolare i test dal `.env` del repo
- [x] T029 Eseguire `uv run ruff check src/sertor_core/cli/__main__.py src/sertor_core/cli/output.py` e correggere eventuali violazioni (regole E,F,I,UP,B; line-length 100)
- [x] T030 [P] Eseguire `uv run ruff check tests/unit/test_cli_memory.py` e correggere eventuali violazioni
- [x] T031 Eseguire il quickstart completo di `specs/035-memoria-cli-hook/quickstart.md` (§0 gate off, §1 archive/idempotenza/--json, §2 search/filtri/--json/finestra impossibile, §3 verifica hook manuale) e documentare l'esito
- [x] T032 [P] Eseguire `uv run pytest tests/unit/test_cli_memory.py -v` e verificare che tutti i test passino
- [x] T033 Eseguire `uv run pytest -m "not cloud"` per verifica di non-regressione (SC-009): nessun test preesistente deve fallire

---

## Grafo delle dipendenze

```
Phase 1: Setup
  T001, T002  (nessuna dipendenza — verifiche iniziali)

Phase 2: Foundational
  T003  ← T001
  T004  ← T003
  T005  ← T004
  T006  ← (nessuna dipendenza da T004; dipende da T001 per conferma struttura output.py)
  T007  ← T006 (stesso file, in sequenza se sviluppatore singolo; [P] se assegnati in parallelo)

Phase 3: US1
  T008  ← T004, T005
  T009  ← T008, T006
  T010  ← T009         (test del comportamento umano)
  T011  ← T009         (test --json)
  T012  ← T009         (test idempotenza)
  T013  ← T009         (test gate off)

Phase 4: US2  [può iniziare in parallelo con US1 dopo il Foundational]
  T014  ← T004
  T015  ← T014, T004, T005
  T016  ← T015, T007
  T017  ← T016
  T018  ← T016
  T019  ← T016
  T020  ← T016
  T021  ← T016
  T022  ← T016

Phase 5: US3  [può iniziare dopo T009; indipendente da US2]
  T023  ← T009 (archive deve essere operativo)
  T024  ← T023
  T025  ← T024

Phase 6: Polish
  T026  ← T013
  T027  ← T018
  T028  ← T010 (il fixture è fondamentale per tutti i test)
  T029  ← T009, T016
  T030  ← T032
  T031  ← T025
  T032  ← T013, T022, T025
  T033  ← T032
```

**Dipendenze critiche**:
1. T003 → T004 → T005 sblocca entrambe US1 e US2.
2. T006 è prerequisito di T009 (US1); T007 è prerequisito di T016 (US2).
3. T009 (US1 completa) è prerequisito di T023 (US3): l'hook invoca il comando.
4. T033 (non-regressione) va eseguito per ultimo, dopo tutti i test di fase.

---

## Esecuzione parallela per user story

### Parallelismo US1 (dopo Foundational)

```
T008  →  T009  →  T010 [P]
                   T011 [P]
                   T012 [P]
                   T013 [P]
```

### Parallelismo US2 (dopo Foundational, in parallelo con US1)

```
T014  →  T015  →  T016  →  T017 [P]
                             T018 [P]
                             T019 [P]
                             T020 [P]
                             T021 [P]
                             T022 [P]
```

### Parallelismo US3 (dopo T009)

```
T023  →  T024  →  T025
```

### Parallelismo Polish

```
T026 [P]  T027 [P]  T028 [P]  T029  T030 [P]  T031  T032  T033
```
(T029 precede T030; T032 precede T033; T031 precede T033)

---

## Strategia di implementazione

### MVP (US1 + US2 — giro «archivia → ritrova»)

1. **Phase 1** (Setup): verifiche immediate — T001, T002.
2. **Phase 2** (Foundational): T003 → T004 → T005 → T006 → T007.
3. **Phase 3** (US1): T008 → T009 → T010/T011/T012/T013.
4. **Phase 4** (US2): T014 → T015 → T016 → T017..T022.
5. **STOP e VALIDA**: eseguire `uv run pytest tests/unit/test_cli_memory.py` + verifica manuale
   quickstart §0/§1/§2.
6. Deliverable MVP: `sertor-rag memory archive` e `sertor-rag memory search` operativi.

### Consegna incrementale completa

1. Setup + Foundational → fondamenta pronte.
2. US1 → archiviazione da comando (MVP parziale utile da solo).
3. US2 → ricerca da comando (giro archivia → ritrova completo).
4. US3 → cattura automatica a fine sessione (memoria «continua»).
5. Polish → lint, non-regressione, quickstart completo.

### Consegna con team (due sviluppatori)

Dopo Phase 2:
- Sviluppatore A: US1 (T008, T009, T010-T013) → poi US3 (T023-T025).
- Sviluppatore B: US2 (T014-T022) in parallelo.
- Tutti e due: Phase 6 in parallelo (T026-T030), poi T031-T033 in sequenza.

---

## Note operative

- **Core invariato**: non toccare `src/sertor_core/services/`, `composition.py`, `domain/`,
  `config/settings.py`. Il gate `SERTOR_MEMORY` è già in `Settings` e nelle factory.
- **Import da aggiungere** in `cli/__main__.py`: `build_memory_archiver`, `build_episodic_search`
  da `sertor_core.composition`; `SearchQuery` da `sertor_core.services.episodic_search` (o
  dal modulo che lo esporta); `ArchiveRunReport`, `EpisodicResults`, `EpisodicHit` per le funzioni
  di output (import lazy o top-level, coerente con il resto del file).
- **`InvalidTimeWindowError`**: già un `SertorError` → propagato da `main()` come exit 1 senza
  ramo aggiuntivo.
- **Hook non-fatale**: T023 DEVE terminare sempre con `exit 0`; ogni altra uscita romperebbe la
  chiusura sessione (FR-013). Pattern di `wiki-pending-check.ps1`.
- **`[P]` su T006/T007**: stessa funzione presuppone stesso file `output.py`; se un solo
  sviluppatore, eseguire in sequenza (T006 prima, T007 dopo). Il marker [P] vale per team multi-persona.
- **Test offline**: tutti i test in `tests/unit/test_cli_memory.py` usano monkeypatch delle
  factory (nessuna rete, nessun file su disco) — marker `not cloud` già applicabile.
- **Quickstart §3** (verifica hook): non automatizzabile con pytest; documentata come verifica
  manuale a T025 e T031.
