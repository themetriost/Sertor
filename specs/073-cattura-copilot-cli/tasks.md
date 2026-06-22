# Tasks — Cattura memoria su GitHub Copilot CLI (FEAT-008)

**Branch**: `073-cattura-copilot-cli` · **Generato**: 2026-06-22
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/copilot-capture.md`](contracts/copilot-capture.md) ·
**Requisiti**: `requirements/memoria-conversazioni/cattura-multi-assistente/requirements.md`

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO a leva spenta.** Con `SERTOR_MEMORY=false` (default), o con
> `SERTOR_MEMORY_ADAPTER=claude-code` (default invariato), comportamento e costo sono identici a
> oggi: nessun file Copilot aperto, nessun adapter Copilot costruito, import lazy non eseguito
> (RNF-3/NFR-003). Il tier a valle (archivio, FTS, semantica, distillazione) è invariato (RNF-5).
>
> **Strategia MVP/incrementale.**
> - **Setup** (TASK-S01–S02): manopola `copilot_session_dir` + test. Prerequisiti zero; bloccante
>   per le fasi successive.
> - **Fondazionale** (TASK-F01): nuovo adapter `CopilotCliCaptureAdapter` completo. Unico blocco
>   costruttivo; testabile in isolamento con fixture senza Copilot installato.
> - **Storia 1 — Cattura alla pari di Claude** (P1 Must, TASK-US1-01..02): wiring composition +
>   test di integrazione composition.
> - **Storia 2 — Selezione adapter** (P1 Must, TASK-US2-01..02): test dispatch + errore azionabile
>   + default invariato.
> - **Storia 3 — Estrazione turni: solo dialogo, best-effort** (P1 Must, TASK-US3-01): test parser
>   Copilot (mix eventi, riga malformata, solo user/assistant).
> - **Storia 4 — Associazione sessione↔progetto** (P1 Must, TASK-US4-01): test filtro cwd/gitRoot
>   UUID multi-progetto.
> - **Storia 5 — Privacy, local-first, sorgente assente** (P1 Must, TASK-US5-01): test gate
>   privacy + assenza sorgente.
> - **Storia 6 — Idempotenza e robustezza al cambio formato** (P2 Should, TASK-US6-01): test
>   idempotenza + formato inatteso.
> - **Storia 7 — Hook reso vivo su Copilot** (P2 Should, TASK-US7-01): verifica manuale/doc hook.
> - **Polish/cross-cutting** (TASK-P01–P03): suite verde, lint, additività residua.
>
> L'ordine tra le User Story P1 (1–5) segue il piano: fondamenta (adapter) → wiring (composition)
> → verifica selezione → verifica parser → verifica associazione → verifica privacy. Le US P2
> costruiscono sopra le P1.

---

## Fase 0 — Setup: manopola `copilot_session_dir` (2 task)

> Prerequisiti: nessuno. Bloccante per le fasi successive.

### TASK-S01 — Aggiungi `copilot_session_dir` in `src/sertor_core/config/settings.py`
**File**: `src/sertor_core/config/settings.py`
→ dipende da: nessuno
- [ ] Aggiungi il campo `copilot_session_dir: Path` con default `Path.home() / ".copilot" /
      "session-state"` (letto da env `SERTOR_MEMORY_COPILOT_SESSION_DIR`). Mirror **esatto** della
      forma di `claude_projects_dir` / `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR` (DA-CM-3).
- [ ] Aggiungi la lettura del nuovo campo in `load()` (o nella logica di lettura env esistente),
      seguendo esattamente il pattern di `claude_projects_dir`: `default_factory` su `Path.home()`,
      override via `os.environ.get("SERTOR_MEMORY_COPILOT_SESSION_DIR")` → `Path(...)`.
- [ ] Posiziona il campo nella sezione `memory_*` di `Settings`, immediatamente dopo
      `claude_projects_dir`; nessun default hardcodato altrove (Principio VIII).
- [ ] Verifica: `Settings()` costruito senza env → `copilot_session_dir == Path.home() /
      ".copilot" / "session-state"`; con `SERTOR_MEMORY_COPILOT_SESSION_DIR=/tmp/test` nel env →
      `copilot_session_dir == Path("/tmp/test")`.

### TASK-S02 [P] — Test `copilot_session_dir` in `tests/unit/test_settings.py`
**File**: `tests/unit/test_settings.py`
→ dipende da: TASK-S01
- [ ] Aggiungi test: `Settings()` senza env → `copilot_session_dir` è `~/.copilot/session-state`
      (verifica path atteso come `Path.home() / ".copilot" / "session-state"`).
- [ ] Aggiungi test: con `SERTOR_MEMORY_COPILOT_SESSION_DIR=/tmp/fake` nel env →
      `copilot_session_dir == Path("/tmp/fake")`.
- [ ] Verifica che il campo sia **distinto** e indipendente da `claude_projects_dir`
      (nessun aliasing, override di uno non influenza l'altro).
- [ ] Test `not cloud`, offline (solo lettura env).

---

## Fase 1 — Fondazionale: `CopilotCliCaptureAdapter` (1 task)

> Prerequisiti: TASK-S01 (manopola). Bloccante per tutte le storie.
> Testabile in isolamento con directory di fixture (`tmp_path`), senza Copilot installato (RNF-4).

### TASK-F01 — Crea `src/sertor_core/adapters/capture/copilot_cli.py` con `CopilotCliCaptureAdapter`
**File**: `src/sertor_core/adapters/capture/copilot_cli.py` (NUOVO)
→ dipende da: TASK-S01
- [ ] **Docstring di modulo**: dichiara la versione di Copilot CLI verificata (**1.0.63**,
      ricognizione 2026-06-22) e che il formato `events.jsonl` è un dettaglio interno non
      contrattuale (NFR-006); cita il rispecchiamento con `claude_code.py`.
- [ ] **Costante di mapping** (host-specific vocabulary, confinata nel modulo):
      ```python
      _TURN_EVENT_ROLES = {"user.message": "user", "assistant.message": "assistant"}
      ```
      Il mapping è il solo punto che conosce i `type` di evento Copilot → ruolo turno (DA-CM-1).
      Tutti gli altri `type` non sono nel dict → automaticamente scartati (REQ-008/FR-009).
- [ ] **Classe `CopilotCliCaptureAdapter`** — implementa la porta `TranscriptCaptureAdapter`
      (structural typing, **nessuna ereditarietà**), `kind = "copilot-cli"`, stdlib-only
      (`json`/`logging`/`os`/`datetime`/`pathlib`), best-effort non-fatale:
      ```python
      class CopilotCliCaptureAdapter:
          kind = "copilot-cli"
          def __init__(self, session_dir: Path | str, project_id: str): ...
          def list_sessions(self) -> list[SessionRef]: ...
          def read_session(self, ref: SessionRef) -> TranscriptContent: ...
      ```
- [ ] **`list_sessions()`** (FR-004/006/010/011/019, contratto §list_sessions):
      - Se `self._dir` non è una directory → `[]` + `log_event(WARNING,
        "memory_capture_source_absent", adapter_kind="copilot-cli", source=str(self._dir))`
        (parità Claude, REQ-018/FR-019).
      - Enumera le **sottocartelle UUID** (solo dir, non file) sotto `self._dir`.
      - Per ciascuna sottocartella, chiama `_session_context(uuid_dir / "events.jsonl")` per
        ottenere `(cwd, git_root)`; gestisce `OSError` con warning `memory_capture_unreadable` +
        skip.
      - Chiama `_paths_match(self._project_id, cwd, git_root)`:
        - `True` → include: `SessionRef(session_key=uuid_dir.name, project_id=...,
          source_path=str(uuid_dir / "events.jsonl"))`.
        - `False` perché mancano cwd/gitRoot → skip + `log_event(WARNING,
          "memory_capture_session_unassociated", session_key=uuid_dir.name,
          adapter_kind="copilot-cli")` (DA-CM-2, FR-011/REQ-010).
        - `False` per mancanza di match progetto → skip silenzioso (sessione di altro progetto).
      - Ritorna la lista dei `SessionRef` corrispondenti al progetto corrente.
- [ ] **`read_session(ref)`** (FR-007/008/009, contratto §read_session):
      - Legge `events.jsonl` riga per riga (`path.read_text(errors="replace").splitlines()`);
        `OSError` → warning `memory_capture_unreadable` + `turns=()`.
      - Per ogni riga chiama `_parse_line(line, ref.session_key, lineno)` → skip se `None`.
      - Per ogni evento valido chiama `_turn_from_event(event, index=len(turns))` → append se non
        `None`.
      - `captured_at` = mtime di `events.jsonl` (fallback `0.0` se il file è scomparso, parità
        con l'adapter Claude).
      - Ritorna `TranscriptContent(session_key=ref.session_key, project_id=ref.project_id,
        adapter_kind=self.kind, captured_at=captured_at, turns=tuple(turns))`.
- [ ] **Helper puri** (confinati nel modulo, host-specific vocabulary — data-model §Helper):
      - `_session_context(events_path: Path) -> tuple[str | None, str | None]`:
        Apre `events_path`, legge riga per riga fino al primo evento `session.start`, estrae
        `data.context.cwd` e `data.context.gitRoot`; riga malformata → skip; evento `session.start`
        non trovato o campi assenti → `(None, None)`. **Nessuna eccezione non gestita.**
      - `_paths_match(project_id: str, cwd: str | None, git_root: str | None) -> bool`:
        Ritorna `True` se **almeno uno** tra `cwd` e `git_root` è antenato-o-uguale al
        `project_id` (path-containment, DA-CM-4). Confronto su path **normalizzati**:
        `Path.resolve()` se il path esiste (best-effort), altrimenti `os.path.normcase()` +
        `PurePath` lessicale (testabilità offline, RNF-4). Case-insensitive su Windows.
        `cwd=None` e `git_root=None` → `False`.
      - `_turn_from_event(event: dict, index: int) -> TranscriptTurn | None`:
        Ottiene `role = _TURN_EVENT_ROLES.get(event.get("type"))` → `None` se tipo non nel dict
        (→ nessun turno); testo = `event.get("data", {}).get("content")`; `content` vuoto,
        whitespace o non-stringa → `None` (turno saltato); altrimenti `TranscriptTurn(index=index,
        role=role, text=content.strip(), ts=_parse_timestamp(event.get("timestamp")))`.
        `toolRequests` dentro `data` **ignorati** (non acceduti, FR-009).
      - `_parse_line(line: str, session_key: str, lineno: int) -> dict | None`:
        Identico a `claude_code.py`: riga vuota → `None` silenzioso; non-JSON → warning
        `memory_capture_unparsable_line` + `None`; non-dict → `None` (parità Claude, FR-008).
      - `_parse_timestamp(raw: object) -> float | None`:
        Identico a `claude_code.py`: ISO-8601 → epoch float via `datetime.fromisoformat`, `None`
        se assente/illeggibile (non-fatale, parità Claude).
- [ ] **Crea `tests/unit/test_copilot_capture.py`** (NUOVO) con fixture di directory session-state:
      - Helper di costruzione fixture:
        ```python
        def _make_session(tmp_path, uuid, events):
            """Crea <tmp_path>/<uuid>/events.jsonl con la lista di eventi dati."""
        ```
      - `test_list_sessions_returns_matching_project(tmp_path)`:
        2 sessioni, stessa dir; `session.start` con `cwd = str(tmp_path)` per entrambe;
        `project_id = str(tmp_path)` → `list_sessions()` ritorna 2 `SessionRef` (SC-009/FR-010).
      - `test_list_sessions_excludes_other_project(tmp_path)`:
        1 sessione con `cwd` di un altro progetto → `list_sessions()` ritorna `[]`
        (SC-009, US4-AC1).
      - `test_list_sessions_skips_unassociated_with_warning(tmp_path, caplog)`:
        1 sessione senza evento `session.start` (o senza cwd/gitRoot leggibili) →
        `list_sessions()` ritorna `[]` + warning `memory_capture_session_unassociated`
        (DA-CM-2, FR-011/US4-AC2).
      - `test_list_sessions_uses_gitroot_when_cwd_differs(tmp_path)`:
        Sessione con `cwd` di una sottocartella ma `gitRoot` = `str(tmp_path)` →
        inclusa quando `project_id = str(tmp_path)` (DA-CM-4).
      - `test_list_sessions_absent_source_returns_empty_with_warning(tmp_path, caplog)`:
        Dir session-state assente → `[]` + warning `memory_capture_source_absent` (FR-019/SC-006).
      - `test_session_key_is_uuid_folder_name(tmp_path)`:
        `session_key` della `SessionRef` = nome della cartella UUID (non un path) (FR-006).
      - `test_read_session_extracts_user_and_assistant_turns(tmp_path)`:
        `events.jsonl` con 1 evento `user.message` + 1 `assistant.message` →
        `TranscriptContent` con 2 turni in ordine, ruoli corretti, testo da `data.content`
        (FR-007/DA-CM-1/US3-AC1).
      - `test_read_session_discards_non_dialog_events(tmp_path)`:
        Mix di eventi: `session.start`, `tool.execution_start`, `hook.start`, `system.message`,
        `permission.request`, `subagent.selected`, `assistant.turn_start`, `user.message`,
        `assistant.message` → soli 2 turni user/assistant estratti (FR-009/SC-008/US3-AC1).
      - `test_read_session_ignores_tool_requests_in_assistant(tmp_path)`:
        Evento `assistant.message` con `data.toolRequests` popolato → turno estratto dal
        `data.content`, `toolRequests` non diventano turni separati (FR-009/US3-AC2).
      - `test_read_session_skips_empty_content(tmp_path)`:
        Evento `user.message` con `data.content=""` → nessun turno (DA-CM-1).
      - `test_read_session_unparsable_line_skipped_with_warning(tmp_path, caplog)`:
        Riga non-JSON in mezzo → saltata + warning `memory_capture_unparsable_line`; turni
        validi prima e dopo estratti (FR-008/SC-006/US3-AC3).
      - `test_read_session_ts_parsed_from_timestamp_field(tmp_path)`:
        Evento con `timestamp="2026-06-22T10:00:00Z"` → `ts` è un `float` non-None
        (parità Claude).
      - `test_read_session_missing_timestamp_gives_none(tmp_path)`:
        Evento senza campo `timestamp` → `ts=None` (non-fatale, DA-CM-1).
      - `test_read_session_oserror_returns_empty_turns(tmp_path, caplog)`:
        `source_path` inesistente → `turns=()` + warning `memory_capture_unreadable`
        (FR-008/SC-006).
      - `test_session_key_stable_idempotent(tmp_path)`:
        Due chiamate a `list_sessions()` sulla stessa dir → stesso `session_key` (FR-006).
      - `test_source_read_only(tmp_path)`:
        `read_session()` non modifica `events.jsonl` (sorgente read-only, parità Claude).
      - Tutti i test: `not cloud`, offline, nessun Copilot installato (RNF-4).

---

## Fase 2 — Storia 1: Cattura Copilot alla pari di Claude (P1, Must) (2 task)

> Prerequisiti: TASK-F01 (adapter). Questa fase cabla l'adapter nel composition root e verifica
> il dispatch. TASK-US1-01 (composition) è bloccante per TASK-US1-02 (test integration).

### TASK-US1-01 — `src/sertor_core/composition.py`: estendi `build_capture_adapter` con `"copilot-cli"`
**File**: `src/sertor_core/composition.py`
→ dipende da: TASK-F01, TASK-S01
- [ ] Aggiorna `_VALID_MEMORY_ADAPTERS = ("claude-code", "copilot-cli")` (riga 29): aggiungi
      `"copilot-cli"` (data-model §Selettore, REQ-001/FR-001).
- [ ] Nella funzione `build_capture_adapter`, dopo il ramo `claude-code` (invariato), aggiungi:
      ```python
      # settings.memory_adapter == "copilot-cli"
      from sertor_core.adapters.capture.copilot_cli import CopilotCliCaptureAdapter  # LAZY
      return CopilotCliCaptureAdapter(settings.copilot_session_dir, project_id=project_id)
      ```
      L'import è **lazy** (dentro la funzione, non a livello di modulo) per preservare
      l'additività a leva spenta (RNF-3/NFR-003).
- [ ] Il ramo `claude-code` resta **invariato** nel comportamento (non-regressione FR-003/SC-010):
      encoding path + `claude_projects_dir` identici a prima; default `"claude-code"` preservato.
- [ ] Il `ConfigError` per valore ignoto ora include **entrambi** i valori ammessi nel messaggio:
      `"(allowed: claude-code, copilot-cli)"` (REQ-002/FR-002).
- [ ] Verifica: `build_capture_adapter` con `memory_adapter="copilot-cli"` → istanza
      `CopilotCliCaptureAdapter`; con `"claude-code"` → `ClaudeCodeCaptureAdapter` (comportamento
      invariato); con valore ignoto → `ConfigError` (comportamento invariato); con
      `SERTOR_MEMORY=false` → `build_memory_archiver` ritorna `None`, `build_capture_adapter`
      mai chiamato (gate privacy invariato, SC-010/011).

### TASK-US1-02 [P] — Test wiring composition in `tests/unit/test_composition.py`
**File**: `tests/unit/test_composition.py`
→ dipende da: TASK-US1-01
- [ ] Aggiungi test: `SERTOR_MEMORY_ADAPTER=copilot-cli` + `SERTOR_MEMORY=true` →
      `build_capture_adapter(settings)` ritorna un'istanza `CopilotCliCaptureAdapter`
      (SC-001/US2-AC1).
- [ ] Aggiungi test: `SERTOR_MEMORY_ADAPTER=claude-code` (default) → `ClaudeCodeCaptureAdapter`
      (non-regressione SC-010/FR-003/US2-AC3).
- [ ] Aggiungi test: valore ignoto (es. `"gemini"`) → `ConfigError` con messaggio che contiene
      `"claude-code"` **e** `"copilot-cli"` (REQ-002/FR-002/US2-AC2).
- [ ] Verifica che con `SERTOR_MEMORY=false` → `build_memory_archiver` ritorna `None` e il nuovo
      ramo `copilot-cli` **non** viene eseguito (additività, RNF-3/SC-011).
- [ ] Tutti `not cloud`, Settings mock, nessun adapter reale che legga file.

---

## Fase 3 — Storia 2: Selezione adapter (P1, Must) (2 task)

> Prerequisiti: TASK-US1-01 (composition aggiornato). Verifica il selettore, il default invariato
> e l'errore azionabile. TASK-US2-01 e TASK-US2-02 [P].

### TASK-US2-01 [P] — Test selezione e default in `tests/unit/test_composition.py` (estensione)
**File**: `tests/unit/test_composition.py`
→ dipende da: TASK-US1-01
- [ ] Test: `SERTOR_MEMORY_ADAPTER` non impostato (env assente) → `settings.memory_adapter ==
      "claude-code"` → `ClaudeCodeCaptureAdapter` selezionato (FR-003/SC-010, US2-AC3).
- [ ] Test: `_VALID_MEMORY_ADAPTERS` contiene esattamente `("claude-code", "copilot-cli")` — nessun
      valore in più o in meno (contratto §Selettore).
- [ ] Test: il comportamento di `build_memory_archiver` con `memory_enabled=True` e adapter
      `claude-code` è **bit-identico** a prima di questa feature (non-regressione: il ramo
      `claude-code` non è stato toccato, SC-010/RNF-005).
- [ ] Tutti `not cloud`.

### TASK-US2-02 [P] — Test `_VALID_MEMORY_ADAPTERS` in `tests/unit/test_settings.py` (estensione)
**File**: `tests/unit/test_settings.py`
→ dipende da: TASK-S01
- [ ] Test: `Settings()` default → `memory_adapter == "claude-code"` (default invariato, FR-003).
- [ ] Test: `SERTOR_MEMORY_ADAPTER=copilot-cli` → `settings.memory_adapter == "copilot-cli"`
      (FR-001/REQ-001).
- [ ] Test: `SERTOR_MEMORY_ADAPTER=sconosciuto` → `settings.memory_adapter == "sconosciuto"` (la
      Settings non valida — la validazione è in `build_capture_adapter`; la configurazione non
      blocca la costruzione di Settings; FR-002 si attiva al momento del build).
- [ ] Tutti `not cloud`, offline.

---

## Fase 4 — Storia 3: Estrazione turni, solo dialogo, best-effort (P1, Must) (1 task)

> Prerequisiti: TASK-F01 (adapter con fixture). I test di questa storia sono già inclusi
> in TASK-F01 (test del parser). Questo task verifica specificamente i casi di confine
> elencati in US3 e SC-008, separato per leggibilità e tracciabilità.
> [P] rispetto a TASK-US2-01/02.

### TASK-US3-01 [P] — Verifica test parser US3 in `tests/unit/test_copilot_capture.py`
**File**: `tests/unit/test_copilot_capture.py`
→ dipende da: TASK-F01
- [ ] Verifica che il test `test_read_session_discards_non_dialog_events` copra esplicitamente
      **tutti** i tipi di evento scartati dichiarati nel contratto: `session.start`,
      `tool.execution_start`, `tool.execution_complete`, `hook.start`, `hook.end`,
      `system.message`, `permission.request`, `subagent.selected`, `assistant.turn_start`,
      `assistant.turn_end` → nessuno di questi produce un turno (FR-009/SC-008/US3-AC1).
- [ ] Aggiungi se mancante: `test_read_session_transformed_content_ignored`:
      Evento `user.message` con `data.transformedContent="injected"` e `data.content="real"` →
      testo del turno è `"real"`, non `"injected"` (DA-CM-1, REQ-008).
- [ ] Aggiungi se mancante: `test_read_session_non_string_content_skipped`:
      Evento `user.message` con `data.content=[]` (lista, non stringa) → turno saltato; nessun
      crash (DA-CM-1 fallback, FR-008/US3-AC3).
- [ ] Aggiungi se mancante: `test_session_with_zero_dialog_events`:
      `events.jsonl` con solo eventi `session.start` e `tool.*` → `turns=()` (FR-009/US3-AC1).
- [ ] Tutti `not cloud`, fixture `tmp_path`.

---

## Fase 5 — Storia 4: Associazione sessione↔progetto (P1, Must) (1 task)

> Prerequisiti: TASK-F01. Test helper `_paths_match` e discovery multi-progetto.
> [P] rispetto a TASK-US2-01/02, TASK-US3-01.

### TASK-US4-01 [P] — Verifica test associazione in `tests/unit/test_copilot_capture.py`
**File**: `tests/unit/test_copilot_capture.py`
→ dipende da: TASK-F01
- [ ] Aggiungi `test_paths_match_exact_cwd`:
      `_paths_match("/repo", "/repo", None)` → `True` (match esatto su cwd).
- [ ] Aggiungi `test_paths_match_gitroot_contains_project`:
      `_paths_match("/repo", "/repo/sub", "/repo")` → `True` (gitRoot è antenato, DA-CM-4).
- [ ] Aggiungi `test_paths_match_cwd_is_ancestor`:
      `_paths_match("/repo/sub", "/repo", None)` → `False` (cwd è **antenato** del project_id
      ma la regola è «cwd/gitRoot **contiene** il progetto», non il viceversa — DA-CM-4).
- [ ] Aggiungi `test_paths_match_both_none`:
      `_paths_match("/repo", None, None)` → `False` (DA-CM-2).
- [ ] Aggiungi `test_list_sessions_multi_project_isolation`:
      3 sessioni nella dir: sessione A con `cwd=/progettoA`, sessione B con `cwd=/progettoB`,
      sessione C con `gitRoot=/progettoA` → con `project_id=/progettoA`: solo A e C incluse
      (SC-009/US4-AC1).
- [ ] Tutti test su path **sintetici** (stringhe, non path reali su disco) per garantire
      l'esecuzione offline e la portabilità cross-platform (RNF-4).

---

## Fase 6 — Storia 5: Privacy, local-first, sorgente assente (P1, Must) (1 task)

> Prerequisiti: TASK-F01, TASK-US1-01. Verifica il gate privacy e la degradazione non-fatale
> su sorgente assente. [P] rispetto a TASK-US3-01, TASK-US4-01.

### TASK-US5-01 [P] — Verifica test privacy e sorgente assente in `tests/unit/test_copilot_capture.py`
**File**: `tests/unit/test_copilot_capture.py` + `tests/unit/test_composition.py`
→ dipende da: TASK-F01, TASK-US1-01
- [ ] In `test_copilot_capture.py`: `test_absent_source_dir_list_sessions_empty`:
      `session_dir` inesistente → `list_sessions()` ritorna `[]` + warning
      `memory_capture_source_absent`; nessuna eccezione sollevata (FR-019/SC-006/US5-AC3).
- [ ] In `test_copilot_capture.py`: `test_source_dir_empty_list_sessions_empty`:
      `session_dir` esiste ma è vuota (nessuna sottocartella) → `list_sessions()` ritorna `[]`,
      nessun warning (comportamento onesto: nessuna sessione, non è un errore).
- [ ] In `test_composition.py`: `test_memory_off_copilot_adapter_selected_no_files_read`:
      Con `SERTOR_MEMORY=false` e `SERTOR_MEMORY_ADAPTER=copilot-cli` → `build_memory_archiver`
      ritorna `None`; nessun import dell'adapter Copilot eseguito a livello di modulo
      (additività a leva spenta, RNF-3/NFR-003/FR-014/SC-011/US5-AC1).
- [ ] Documentale: verifica che `quickstart.md` contenga la nota cloud-sync (§6 Privacy &
      cloud-sync) — FR-016/REQ-015. Non richiede modifica: già presente nell'artefatto.
- [ ] Tutti `not cloud`, offline.

---

## Fase 7 — Storia 6: Idempotenza e robustezza al cambio formato (P2, Should) (1 task)

> Prerequisiti: TASK-F01. Costruisce sopra le P1. [P] rispetto a TASK-US5-01.

### TASK-US6-01 [P] — Test idempotenza e formato inatteso in `tests/unit/test_copilot_capture.py`
**File**: `tests/unit/test_copilot_capture.py`
→ dipende da: TASK-F01
- [ ] `test_list_sessions_idempotent`:
      Due chiamate a `list_sessions()` sulla stessa dir con stesse sessioni → stessa lista di
      `session_key` (identità stabile, FR-006/SC-005/US6-AC1).
- [ ] `test_read_session_unknown_event_fields_no_crash`:
      Evento `user.message` con campi extra inattesi (es. `"data": {"content": "ok",
      "futureField": {}}`) → turno estratto correttamente; i campi extra ignorati silenziosamente
      (FR-020/RNF-1/US6-AC2).
- [ ] `test_read_session_missing_data_field_no_crash`:
      Evento `user.message` senza campo `data` → saltato (nessun crash, RNF-1/FR-020/US6-AC2).
- [ ] `test_read_session_content_not_string_no_crash`:
      Evento `assistant.message` con `data.content={"nested": "obj"}` → saltato (DA-CM-1
      fallback, RNF-1).
- [ ] `test_read_session_entirely_unknown_format_returns_empty_turns`:
      `events.jsonl` con solo eventi di tipo `"future.event.type"` sconosciuto →
      `turns=()`, nessuna eccezione (FR-020/US6-AC2, degradazione best-effort).
- [ ] Tutti `not cloud`, fixture `tmp_path`.

---

## Fase 8 — Storia 7: Hook reso vivo su Copilot (P2, Should) (1 task)

> Prerequisiti: TASK-US1-01/02 (wiring). Questa storia è principalmente documentale e di
> integrazione: l'hook `SessionEnd` già esiste (FEAT-009); questa feature lo rende funzionante
> perché ora ha una sorgente Copilot. Nessun nuovo artefatto host.

### TASK-US7-01 — Verifica hook reso vivo (documentale + test di integrazione CLI)
**File**: `specs/073-cattura-copilot-cli/quickstart.md` (lettura) +
`tests/unit/test_composition.py` (estensione)
→ dipende da: TASK-US1-01, TASK-US1-02
- [ ] Verifica che `quickstart.md` §3 menzioni esplicitamente che l'hook `SessionEnd` già
      depositato da FEAT-009 smette di essere inerte quando la memoria è attiva e l'adapter
      è `copilot-cli` (FR-021/REQ-020/US7-AC1). Non richiede modifica: già presente.
- [ ] In `test_composition.py`: aggiungi un test di integrazione sottile che simula il flusso
      dell'hook: con `SERTOR_MEMORY=true` e `SERTOR_MEMORY_ADAPTER=copilot-cli` →
      `build_memory_archiver(settings)` ritorna un'istanza non-None di `MemoryArchiveService`
      con un adapter di tipo `CopilotCliCaptureAdapter` iniettato (SC-007/US7-AC1).
      (Verifica che il tubo sia connesso, non che catturi sessioni reali.)
- [ ] In `test_composition.py`: con `SERTOR_MEMORY=false` → `build_memory_archiver` ritorna
      `None` → hook diventa no-op (US7-AC2/SC-011/RNF-3).
- [ ] Tutti `not cloud`, Settings mock, nessun Copilot reale.

---

## Fase 9 — Polish e cross-cutting (3 task)

> Prerequisiti: tutte le Fasi 0–8. TASK-P01 e TASK-P02 [P]; TASK-P03 dipende da entrambi.

### TASK-P01 [P] — Suite non-cloud verde + lint ruff pulito
→ dipende da: tutti i task delle Fasi 0–8
- [ ] Esegui `uv run pytest tests/unit/test_copilot_capture.py -v` → verde (tutti i nuovi test).
- [ ] Esegui `uv run pytest tests/unit/test_settings.py -v` → verde (incluse le estensioni S01/S02).
- [ ] Esegui `uv run pytest tests/unit/test_composition.py -v` → verde (incluse le estensioni
      US1-02/US2-01/US7-01).
- [ ] Esegui `uv run pytest -m "not cloud" tests/unit/` → verde (inclusi i test pre-esistenti
      di `test_claude_code_capture.py`, `test_memory_archive.py`, `test_episodic_search.py`,
      `test_cli_memory*.py` — devono restare invariati, RNF-5/SC-011).
- [ ] Esegui `uv run pytest -m "not cloud" tests/` → verde (suite completa non-cloud).
- [ ] Esegui `uv run ruff check .` → zero errori sui file nuovi/modificati
      (`adapters/capture/copilot_cli.py`, `config/settings.py`, `composition.py`,
      `test_copilot_capture.py`, `test_settings.py`, `test_composition.py`).
      Regole E,F,I,UP,B; line-length 100.

### TASK-P02 [P] — Verifica additività residua: tier e adapter invariati
→ dipende da: tutti i task delle Fasi 0–8
- [ ] Verifica che **nessuno** dei seguenti file sia stato modificato (RNF-5/SC-003):
      - `src/sertor_core/domain/memory.py` (entità invariate)
      - `src/sertor_core/domain/ports.py` (porta `TranscriptCaptureAdapter` invariata)
      - `src/sertor_core/adapters/capture/claude_code.py` (adapter Claude invariato)
      - `src/sertor_core/services/memory_archive.py` (tier archiviazione invariato)
      - `src/sertor_core/services/episodic_search.py` (FTS full-text invariata)
      - `src/sertor_core/services/memory_semantic.py` (semantica FEAT-004 invariata)
      - `src/sertor_core/engines/` (tutti i motori invariati)
- [ ] Spot check comportamenti CLI invariati:
      - `SERTOR_MEMORY=false` → `build_memory_archiver` ritorna `None` (gate privacy invariato).
      - `SERTOR_MEMORY_ADAPTER` non impostato → default `claude-code` (SC-010/FR-003).
      - La suite `test_claude_code_capture.py` è verde senza modifiche (non-regressione).
- [ ] Verifica che con `SERTOR_MEMORY_ADAPTER=claude-code` (default): il nuovo modulo
      `adapters/capture/copilot_cli.py` non viene mai importato (import lazy, RNF-3).

### TASK-P03 — Verifica osservabilità: eventi metrics-only, parità Claude
→ dipende da: TASK-P01, TASK-P02
- [ ] Verifica nei test (o aggiungendo un test dedicato) che gli eventi emessi dall'adapter
      Copilot siano **metrics-only** — mai testo di transcript (Principio IX, data-model §Osservabilità):
      - `memory_capture_source_absent`: contiene `adapter_kind` e `source` (path); **non** il testo
        delle sessioni.
      - `memory_capture_unreadable`: contiene `session_key` e `reason` (tipo eccezione); **non** il
        contenuto del file.
      - `memory_capture_unparsable_line`: contiene `session_key` e `line` (numero); **non** la riga
        grezza.
      - `memory_capture_session_unassociated` (NUOVO): contiene `session_key` e `adapter_kind`;
        **non** cwd/gitRoot grezzi (che potrebbero contenere path sensibili).
- [ ] Verifica che i 4 eventi abbiano il campo `adapter_kind="copilot-cli"` (distinzione dalla
      sorgente Claude nei log condivisi).
- [ ] Verifica che un guasto nell'emissione dell'evento (es. `log_event` lancia eccezione) non
      abortisca la discovery o il parsing: nessun `log_event` è in un percorso critico
      non-wrapped (parità con l'adapter Claude, RNF-1).

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01 (Settings: copilot_session_dir) ──────────────────────────────────────┐
TASK-S02 [P] (test settings) ← S01 ────────────────────────────────────────────┤
                                                                                │
                               TASK-F01 (CopilotCliCaptureAdapter + test fixture) ← S01
                                         │
         TASK-US1-01 (composition: _VALID_MEMORY_ADAPTERS + dispatch) ← F01, S01
                  │
                  ├── TASK-US1-02 [P] (test composition dispatch) ← US1-01
                  │
                  ├── TASK-US2-01 [P] (test selezione default) ← US1-01
                  ├── TASK-US2-02 [P] (test Settings adapter) ← S01
                  │
                  ├── TASK-US3-01 [P] (verifica parser US3) ← F01
                  │
                  ├── TASK-US4-01 [P] (test associazione multi-progetto) ← F01
                  │
                  ├── TASK-US5-01 [P] (test privacy + sorgente assente) ← F01, US1-01
                  │
                  └── TASK-US6-01 [P] (test idempotenza + formato inatteso) ← F01

         TASK-US7-01 (hook reso vivo: doc + integrazione) ← US1-01, US1-02

         TASK-P01 [P] (suite verde + lint) ← tutti i task
         TASK-P02 [P] (additività residua) ← tutti i task
         TASK-P03 (osservabilità metrics-only) ← P01, P02
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (cattura alla pari di Claude) | Con `SERTOR_MEMORY=true` e `SERTOR_MEMORY_ADAPTER=copilot-cli`, `build_capture_adapter` ritorna `CopilotCliCaptureAdapter`; `build_memory_archiver` ritorna `MemoryArchiveService` non-None con adapter Copilot iniettato. | TASK-F01, TASK-US1-01/02 | MECCANICO |
| **US2** (selezione adapter) | `copilot-cli` → `CopilotCliCaptureAdapter`; `claude-code` (default) → `ClaudeCodeCaptureAdapter` invariato; valore ignoto → `ConfigError` con entrambi i valori ammessi nel messaggio. | TASK-US1-01, TASK-US2-01/02 | MECCANICO |
| **US3** (solo dialogo, best-effort) | Fixture con mix eventi → soli turni `user`/`assistant` estratti in ordine; `tool.*`/`system.*`/`hook.*`/`session.*`/`permission.*`/`subagent.*` ignorati; `toolRequests` non sono turni; riga malformata → skip + warning + parsing prosegue. | TASK-F01, TASK-US3-01 | MECCANICO |
| **US4** (associazione sessioni UUID) | Multi-sessione multi-progetto nella dir: solo sessioni la cui cwd/gitRoot corrisponde al progetto corrente (path-containment, DA-CM-4); sessione senza `session.start` → skip + warning (DA-CM-2, no misattribuzione); `session_key` = UUID cartella, non path di progetto. | TASK-F01, TASK-US4-01 | MECCANICO |
| **US5** (privacy, local-first, sorgente assente) | Con `SERTOR_MEMORY=false`: `build_memory_archiver` → `None`, nessun import Copilot; session-store assente → `[]` + warning, nessuna eccezione; nessun traffico rete (embedder/store non coinvolti nella cattura). | TASK-F01, TASK-US1-01, TASK-US5-01 | MECCANICO |
| **US6** (idempotenza + robustezza, P2) | Due `list_sessions()` sulla stessa dir → stesso risultato (stabile); evento con formato inatteso/campi extra → skip/turno-vuoto, mai crash; `turns=()` su sessione con solo eventi sconosciuti. | TASK-F01, TASK-US6-01 | MECCANICO |
| **US7** (hook reso vivo, P2) | Con memoria on e adapter Copilot: `build_memory_archiver` non-None (tubo connesso); con memoria off → `None` (hook no-op). Verifica documentale §3 quickstart. | TASK-US1-01, TASK-US7-01 | MECCANICO + DOCUMENTALE |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 (senza prerequisiti — parallelizzabile al 100%):**
- TASK-S01 (manopola `copilot_session_dir` in `settings.py`)

**Sprint 2 (dopo S01 — in parallelo):**
- TASK-S02 (test settings)
- TASK-F01 (adapter + fixture — bloccante per tutto; avviarlo il prima possibile)

**Sprint 3 (dopo F01 — P1 Must, massima parallelizzazione):**
- TASK-US1-01 (composition dispatch) — bloccante per US1-02/US2-01/US5-01/US7-01
- TASK-US3-01 [P] (verifica parser US3 — dipende solo da F01)
- TASK-US4-01 [P] (test associazione — dipende solo da F01)
- TASK-US6-01 [P] (test idempotenza P2 — dipende solo da F01)

**Sprint 4 (dopo US1-01 — consumi della factory):**
- TASK-US1-02 [P] (test dispatch composition)
- TASK-US2-01 [P] (test selezione default)
- TASK-US2-02 [P] (test Settings adapter — dipende solo da S01, può partire in Sprint 2)
- TASK-US5-01 [P] (test privacy + sorgente assente)
- TASK-US7-01 (hook reso vivo)

**Sprint finale (Polish):**
- TASK-P01 [P] (suite verde + lint)
- TASK-P02 [P] (additività residua)
- TASK-P03 (osservabilità metrics-only)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per FEAT-008 — cattura memoria su GitHub Copilot CLI

Fase SpecKit "tasks" completata per specs/073-cattura-copilot-cli.
18 task in 10 fasi:
  Fase 0 Setup                 : 2 task  (TASK-S01/S02 — manopola copilot_session_dir)
  Fase 1 Fondazionale          : 1 task  (TASK-F01 — CopilotCliCaptureAdapter + 16 test fixture)
  Fase 2 Storia 1 (P1 Must)    : 2 task  (TASK-US1-01/02 — composition dispatch + test)
  Fase 3 Storia 2 (P1 Must)    : 2 task  (TASK-US2-01/02 — selezione adapter + default invariato)
  Fase 4 Storia 3 (P1 Must)    : 1 task  (TASK-US3-01 — parser solo-dialogo, best-effort)
  Fase 5 Storia 4 (P1 Must)    : 1 task  (TASK-US4-01 — associazione UUID multi-progetto)
  Fase 6 Storia 5 (P1 Must)    : 1 task  (TASK-US5-01 — privacy + sorgente assente)
  Fase 7 Storia 6 (P2 Should)  : 1 task  (TASK-US6-01 — idempotenza + formato inatteso)
  Fase 8 Storia 7 (P2 Should)  : 1 task  (TASK-US7-01 — hook reso vivo, doc + integrazione)
  Fase 9 Polish                : 3 task  (TASK-P01..P03 — suite verde, lint, osservabilità)

Tutti i task MECCANICI (17) + 1 MECCANICO+DOCUMENTALE (TASK-US7-01).
Copertura: FR-001..021, RNF-1..8, SC-001..012, US1..7.
Nessuna nuova entità di dominio, porta o motore: ADDITIVO puro.
Tier a valle invariato (archivio/FTS/semantica/distillazione): verificato in TASK-P02.
Default "claude-code" invariato: verificato in TASK-US2-01 + TASK-P02 (non-regressione).
Additività a leva spenta: verificata in TASK-US5-01 + TASK-P02 (RNF-3/NFR-003).

Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/073-cattura-copilot-cli/tasks.md` (questo file, nuovo)
