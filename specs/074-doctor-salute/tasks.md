# Tasks — `sertor-rag doctor` — verifica di salute deterministica (E12-FEAT-001)

**Branch**: `074-doctor-salute` · **Generato**: 2026-06-23
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/cli-doctor.md`](contracts/cli-doctor.md) ·
[`contracts/event-doctor.md`](contracts/event-doctor.md) ·
[`contracts/configure-check.md`](contracts/configure-check.md)
**Requisiti**: `requirements/usabilita/sertor-rag-doctor/requirements.md`

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO.** `sertor-rag doctor` è un comando nuovo (NFR-5): non altera
> comandi né percorsi esistenti, non scrive sulla config, non tocca l'indice, non ha effetti
> collaterali. È sola lettura e diagnosi pura. Il cablaggio di `configure --check` (pacchetto
> `sertor`) attiva un punto d'estensione già presente e oggi inerte, senza modificare il
> comportamento di `configure` quando `--check` non è richiesto.
>
> **Strategia MVP/incrementale.**
> - **Setup** (TASK-S01–S02): errore di dominio `DoctorCheckFailed` + campo `--corpus` override.
>   Prerequisiti zero; bloccante per le fasi successive.
> - **Fondazionale** (TASK-F01–F03): entità pure del data-model + funzioni di diagnosi per area +
>   formatter. Il nucleo testabile offline prima di toccare CLI o `sertor`.
> - **Storia 1 — «Ha funzionato?» in un comando** (P1 Must, TASK-US1-01..02): handler thin +
>   parser CLI + test umano/JSON + exit code.
> - **Storia 2 — Config/env: chiavi mancanti** (P1 Must, TASK-US2-01): test funzione pura
>   `check_config` con `validate_backend()`.
> - **Storia 3 — Indice: presente? fresco?** (P1 Must, TASK-US3-01..02): helper
>   `current_source_stats` + test `freshness_from_manifest`.
> - **Storia 4 — Provider: statico + probe opt-in** (P2 Should, TASK-US4-01..02): helper
>   `build_provider_probe` + test probe offline/online.
> - **Storia 5 — Server MCP: registrato?** (P2 Should, TASK-US5-01..02): helper
>   `read_mcp_registration` + test `check_mcp`.
> - **Storia 6 — Output machine-readable per skill e CI** (P1 Must, TASK-US6-01): test schema
>   `doctor.report/1`, exit code gate, redazione segreti.
> - **Storia 7 — Offline-safe by default** (P1 Must, TASK-US7-01): test check statici offline,
>   degrado onesto con `--online` offline.
> - **Storia 8 — `configure --check` reso vivo** (P1 Must, TASK-US8-01..02): `_probe_live` nel
>   pacchetto `sertor` + test con `FakeCommandRunner`.
> - **Polish/cross-cutting** (TASK-P01–P04): suite per-package, lint ruff, SC-001..012,
>   debito di completamento.
>
> L'ordine tra le US P1 (1,2,3,6,7,8) prioritizza prima il nucleo puro (F01..F03), poi il
> cablaggio CLI (US1), poi la verifica per area (US2,3,6,7), infine il pacchetto esterno (US8).
> Le US P2 (4,5) costruiscono sopra le P1 e sono parallelizzabili con US6 e US7.

---

## Fase 0 — Setup: errore di dominio + composizione helpers (2 task)

> Prerequisiti: nessuno. Bloccante per tutte le fasi successive.

### TASK-S01 — Aggiungi `DoctorCheckFailed` in `src/sertor_core/domain/errors.py`
**File**: `src/sertor_core/domain/errors.py`
→ dipende da: nessuno
- [ ] Aggiungi la classe `DoctorCheckFailed(SertorError)` come nuovo errore di dominio.
      Pattern identico a `RegressionDetected`/`GraphRegressionDetected`
      (`cli/__main__.py:721,911`): viene sollevato dal handler **dopo** aver stampato il report
      (umano o JSON), così `main()` mappa a exit 1 senza sopprimere l'output.
- [ ] Il messaggio dell'errore è una sintesi delle aree critiche fallite, passato da `scrub_text`
      prima della costruzione (FR-013/SC-006): mai segreti nel messaggio.
- [ ] Non è un crash: il report è già emesso al momento del raise; `DoctorCheckFailed` serve
      **solo** come segnale al gate di exit code (gate critico, DA-D4).
- [ ] Verifica: `DoctorCheckFailed` è istanza di `SertorError`; il costruttore accetta un
      messaggio stringa; nessun import di SDK nel modulo `errors.py`.

### TASK-S02 — Aggiungi `build_provider_probe`, `read_mcp_registration`, `current_source_stats` in `src/sertor_core/composition.py`
**File**: `src/sertor_core/composition.py`
→ dipende da: nessuno
- [ ] **`build_provider_probe(settings) -> ProviderProbe`**: chiama
      `build_embedder(settings, allow_download=False)` + `embed(["__sertor_doctor_probe__"])`;
      cattura eccezioni → `ProviderProbe(status=ProbeStatus.UNREACHABLE, reason=scrub_text(str(e)))`.
      Se `--online` non è attivo il handler **non chiama** questo helper (il probe è opt-in,
      FR-008/SC-005): la funzione è pura nel contratto ma invocata solo dal handler quando
      `args.online is True`. Import lazy di `build_embedder` già presente in composition; nessun
      nuovo import a livello di modulo.
- [ ] **`read_mcp_registration(root: Path) -> bool`**: legge `(root / ".mcp.json")` in stdlib
      (`json.loads`), cerca la chiave `"mcpServers"` o `"servers"` con una voce contenente
      `"sertor-rag"` (project scope). `FileNotFoundError`/`JSONDecodeError`/qualunque errore →
      `False` non-fatale (FR-009/SC-009). Sola lettura, nessun avvio del server (A-003).
- [ ] **`current_source_stats(manifest_state, root: Path) -> list[tuple[Path, float]]`**:
      a partire dai path dei file registrati nel `manifest_state` (campo `files` del manifest,
      già disponibile su `ManifestState` da FEAT-009), esegue `os.stat(path).st_mtime` per
      ciascuno; file scomparso/`OSError` → mtime `0.0` (indica modifica/cancellazione, non crash);
      **nessun re-scan** del repo (FR-006/SC-007). Se `manifest_state is None` → `[]`.
- [ ] Verifica: nessuna nuova dipendenza richiesta; nessun import eager di SDK; helper leggibili
      con guard-clause (Principio VII); nessun default hardcodato (Principio VIII).

---

## Fase 1 — Fondazionale: entità pure, funzioni di diagnosi, formatter (3 task)

> Prerequisiti: TASK-S01 (errore di dominio). Bloccante per tutte le storie.
> Tutto testabile offline con input sintetici, senza FS né rete (Principio V, F.I.R.S.T.).

### TASK-F01 — Crea `src/sertor_core/services/doctor.py` con entità pure e funzioni di diagnosi
**File**: `src/sertor_core/services/doctor.py` (NUOVO)
→ dipende da: TASK-S01
- [ ] **Enum**: `Severity` (`CRITICAL`/`WARN`/`INFO`), `AreaStatus` (`pass_`/`warn`/`fail`),
      `AreaName` (`config`/`provider`/`index`/`mcp`), `ProbeStatus`
      (`reachable`/`unreachable`/`skipped`/`not_applicable`). Invarianti: nomi stabili e
      machine-readable (schema `doctor.report/1`).
- [ ] **Dataclass frozen** `Problem(severity, code, message, remedy, fields=())` dove:
      - `severity: Severity`
      - `code: str` — identificatore stabile (`env_missing_key`, `index_absent`, `index_stale`,
        `provider_unreachable`, `mcp_not_registered`, `mcp_stale_after_reindex`)
      - `message: str` — causa, già scrubbed (FR-013)
      - `remedy: str` — rimedio concreto (FR-002)
      - `fields: tuple[str, ...]` — chiavi env coinvolte, **mai valori** (FR-013/SC-006)
- [ ] **Dataclass frozen** `AreaReport(name, status, problems, detail)` dove `status` è derivato
      dai `problems` (`fail` se ≥1 `CRITICAL`; `warn` se max severità è `WARN`/`INFO`; `pass`
      altrimenti); `detail: dict[str, str | bool | None]` contiene solo metadati non-segreti
      (timestamp, booleani, nome provider, esito probe).
- [ ] **Dataclass frozen** `HealthReport(areas, online, overall)` con metodi puri:
      - `is_healthy() -> bool` — `overall != AreaStatus.fail`
      - `exit_code() -> int` — `1` se ≥1 `Problem` con `Severity.CRITICAL`, else `0`
        (FR-011/SC-004). Coerente con `is_healthy()`.
      - `overall` calcolato: `fail` se ≥1 area `fail`; `warn` se ≥1 area `warn`; `pass` altrimenti.
- [ ] **Dataclass frozen** `ProviderProbe(status: ProbeStatus, reason: str)`.
- [ ] **Funzioni pure di diagnosi** (mapping segnali → esito, testabili con input sintetici):
      - `check_config(missing: list[str]) -> AreaReport`:
        `missing` proviene da `Settings.validate_backend()` (fonte unica, FR-004/A-001).
        Nessuna chiave mancante → `pass`; ≥1 mancante → `fail` con `Problem(CRITICAL,
        "env_missing_key", ...)` per ciascuna, `fields=(chiave,)` (FR-003).
      - `check_provider(missing_provider: list[str], probe: ProviderProbe | None) -> AreaReport`:
        Config provider incompleta (chiavi mancanti filtrate per area provider) → `fail` critico;
        config completa + probe `unreachable` → `warn`; probe `skipped` → nota informativa (INFO,
        non-bloccante); probe `reachable` → `pass` (DA-D4/FR-007/008).
      - `freshness_from_manifest(state, current_stats: list[tuple[Path, float]]) -> AreaReport`:
        `state is None` → `fail` con `Problem(CRITICAL, "index_absent", ...)` + rimedio
        `sertor-rag index .` (FR-005); stato presente: confronta mtime file noti col last-index
        del manifest; nessuna modifica → `pass` con `detail={"last_index": iso_timestamp}`;
        ≥1 file modificato/cancellato → `warn` con `Problem(WARN, "index_stale", ...)` + rimedio
        (FR-006/SC-007). Nessun re-scan, nessuna euristica nuova.
      - `check_mcp(registered: bool, index_stale: bool) -> AreaReport`:
        Non registrato → `warn` con `Problem(WARN, "mcp_not_registered", ...)` + rimedio
        `sertor install rag` (FR-009); registrato + indice stantio → `warn` best-effort
        `Problem(WARN, "mcp_stale_after_reindex", ...)` (DA-D5); registrato + indice fresco →
        `pass` (DA-D4). **MCP non ha mai esito `fail` critico** (contratto DA-D4).
      - `assemble(areas: tuple[AreaReport, ...], online: bool) -> HealthReport`:
        Ordine fisso `(config, provider, index, mcp)`. Calcola `overall`.
- [ ] Stdlib-only (`enum`, `dataclasses`); **nessun SDK importato**; nessun I/O (Principio I/V).

### TASK-F02 — Crea test `tests/unit/test_doctor.py`
**File**: `tests/unit/test_doctor.py` (NUOVO)
→ dipende da: TASK-F01
- [ ] **Test `check_config`**:
      - `test_check_config_pass_no_missing`: `missing=[]` → `AreaReport(status=pass)`.
      - `test_check_config_fail_one_missing`: `missing=["AZURE_OPENAI_API_KEY"]` → `fail`,
        `problems[0].code == "env_missing_key"`, `problems[0].severity == CRITICAL`,
        `"AZURE_OPENAI_API_KEY" in problems[0].fields` (FR-003/SC-002/SC-004).
      - `test_check_config_fail_multiple_missing`: 3 chiavi mancanti → 3 `Problem` CRITICAL
        (SC-002/US2-AC1).
      - `test_check_config_fonte_unica`: verifica che non ci sia una lista duplicata propria
        delle chiavi — la funzione accetta qualunque lista, l'accoppiamento alla fonte unica è
        nel handler (FR-004/A-001). Test di contratto: se `missing` è vuoto → pass.
- [ ] **Test `check_provider`**:
      - `test_check_provider_pass_complete_no_probe`: `missing_provider=[]`, `probe=None` → `pass`.
      - `test_check_provider_fail_incomplete`: `missing_provider=["AZURE_OPENAI_API_KEY"]` →
        `fail` CRITICAL (DA-D4/SC-004).
      - `test_check_provider_warn_unreachable`: config completa + `probe=ProviderProbe(UNREACHABLE,
        "timeout")` → `warn` WARN (SC-002/US4-AC3).
      - `test_check_provider_info_skipped`: config completa + `probe=ProviderProbe(SKIPPED, "")`
        → area pass o info non-bloccante (US4-AC1 offline-safe).
      - `test_check_provider_pass_reachable`: config completa + `probe=ProviderProbe(REACHABLE,
        "")` → `pass` (US4-AC2).
- [ ] **Test `freshness_from_manifest`**:
      - `test_freshness_absent_manifest`: `state=None` → `fail` CRITICAL `index_absent`,
        rimedio contiene `sertor-rag index .` (FR-005/US3-AC1).
      - `test_freshness_fresh_index`: `current_stats` con mtime tutti ≤ last-index → `pass`,
        `detail["last_index"]` valorizzato (FR-006/US3-AC2).
      - `test_freshness_stale_index`: ≥1 file con mtime > last-index → `warn` WARN `index_stale`,
        rimedio presente (FR-006/SC-007/US3-AC3).
      - `test_freshness_deleted_file_triggers_stale`: file con mtime `0.0` (fallback deleted) →
        `warn` (SC-007, file cancellato = stantio).
      - `test_freshness_no_files_in_manifest`: `current_stats=[]`, manifest presente → `pass`
        (corpus vuoto ma indice valido — nessun falso positivo, SC-007).
- [ ] **Test `check_mcp`**:
      - `test_check_mcp_registered_fresh`: `registered=True`, `index_stale=False` → `pass`
        (US5-AC1).
      - `test_check_mcp_not_registered`: `registered=False` → `warn` `mcp_not_registered`,
        rimedio con `sertor install rag` (US5-AC2).
      - `test_check_mcp_stale_after_reindex`: `registered=True`, `index_stale=True` →
        `warn` `mcp_stale_after_reindex` best-effort (US5-AC3/DA-D5).
      - `test_check_mcp_never_critical`: tutti gli scenari MCP → `status` mai `fail`
        (DA-D4: MCP non ha esito critico).
- [ ] **Test `assemble` e `HealthReport`**:
      - `test_assemble_all_pass`: 4 aree `pass` → `overall=pass`, `is_healthy()=True`,
        `exit_code()=0` (SC-004/US1-AC1).
      - `test_assemble_one_critical`: 1 area `fail` → `overall=fail`, `exit_code()=1`
        (FR-011/SC-004/US1-AC2).
      - `test_assemble_warn_only`: solo aree `warn` → `overall=warn`, `exit_code()=0`
        (US1-AC3: warn non è gate).
      - `test_assemble_order`: `areas` nell'ordine `(config, provider, index, mcp)` —
        ordine fisso deterministico (schema stabile, SC-003).
      - `test_area_status_rollup_critical`: area con 1 `CRITICAL` + 1 `WARN` → `fail` (rollup).
- [ ] Tutti `not cloud`, offline; nessun FS; input sintetici (Principio V/F.I.R.S.T.).

### TASK-F03 — Aggiungi `format_health_report` in `src/sertor_core/cli/output.py`
**File**: `src/sertor_core/cli/output.py`
→ dipende da: TASK-F01
- [ ] **`format_health_report(report: HealthReport, *, json_out: bool = False) -> str`** (pura):
      - **Umano** (`json_out=False`): formato a tabella leggibile con intestazione
        `doctor: PASS|WARN|FAIL` + una riga per area (come esempio in `contracts/cli-doctor.md`);
        per ogni area non-pass aggiunge problema con causa e rimedio; exit code non mostrato
        (appare solo tramite `DoctorCheckFailed`).
      - **JSON** (`json_out=True`): serializza `doctor.report/1` (schema stabile SC-003),
        campi top-level fissi (`schema`, `overall`, `online`, `exit_code`, `areas`); ogni stringa
        **passa da `scrub_text`** prima della serializzazione (FR-013/SC-006); `exit_code`
        ridondante nel JSON per comodità delle skill.
      - **Invariante di equivalenza informativa**: umano e JSON portano gli stessi dati
        (pattern degli altri formatter, SC-003).
      - Funzione **pura**: nessun I/O, nessun side-effect. Testabile con `HealthReport` sintetico.
- [ ] Aggiungi test in `tests/unit/test_output.py` (estensione):
      - `test_format_health_report_human_all_pass`: report sano → output umano contiene
        `"doctor: PASS"` e le 4 aree con esito `pass` (US1-AC1).
      - `test_format_health_report_human_critical`: area `fail` → output contiene `"FAIL"`,
        causa e rimedio della chiave mancante (FR-002/SC-002).
      - `test_format_health_report_json_schema`: `json_out=True` → JSON valido con chiavi
        `schema="doctor.report/1"`, `overall`, `online`, `exit_code`, `areas` (lista di 4)
        (SC-003/FR-010).
      - `test_format_health_report_json_scrubbed`: stringa con pattern segreto (es.
        `"sk-abc"`) in un `problem.message` → nel JSON il valore è redatto (FR-013/SC-006).
      - `test_format_health_report_equivalence`: stessi dati, umano e JSON → stesse aree e
        problemi (invariante di equivalenza).
      - Tutti `not cloud`, nessun I/O.

---

## Fase 2 — Storia 1: «Ha funzionato?» in un comando (P1, Must) (2 task)

> Prerequisiti: TASK-F01, TASK-F02, TASK-F03, TASK-S01, TASK-S02. Questa fase cabla il
> sottocomando `doctor` nella CLI e verifica il flusso end-to-end con core mockato.
> TASK-US1-01 (parser+handler) è bloccante per TASK-US1-02 (test handler).

### TASK-US1-01 — `src/sertor_core/cli/__main__.py`: parser `doctor` + handler `_cmd_doctor`
**File**: `src/sertor_core/cli/__main__.py`
→ dipende da: TASK-F01, TASK-F03, TASK-S01, TASK-S02
- [ ] **`_add_doctor_parser(sub)`**: registra il sottocomando `doctor` con i flag:
      - `--online` (store_true, default off): abilita probe provider; **zero traffico di rete**
        senza questo flag (FR-007/012/SC-005).
      - `--area` (choices: `config`, `provider`, `index`, `mcp`, `all`; default `all`): restringe
        le aree eseguite; `config` è il sottoinsieme usato da `configure --check` (DA-D3).
      - `--json` (store_true): emette `doctor.report/1` su stdout (FR-010).
      - `--corpus NAME` (override namespace, come gli altri comandi).
      - Flag di logging condivisi via `_add_logging_flags` (osservabilità, come gli altri handler).
- [ ] **`_cmd_doctor(args)`** (handler thin):
      1. Risolve `Settings` (+ `args.corpus`); chiama `enable_observability(settings)`
         (no-op se off).
      2. Legge `validate_backend()` → `missing_all`, `missing_provider` (sottoinsieme).
      3. Legge `build_indexed_docs`/`IndexManifest` → `manifest_state` (presenza+metadati).
      4. Chiama `current_source_stats(manifest_state, root)` → `stats`.
      5. Se `args.online`: chiama `build_provider_probe(settings)` → `probe`; altrimenti
         `probe = ProviderProbe(ProbeStatus.SKIPPED, "")`.
      6. Chiama `read_mcp_registration(root)` → `registered`.
      7. Calcola `index_stale` da `freshness_from_manifest(...)`.
      8. Assembla `HealthReport` via `check_config`/`check_provider`/`freshness_from_manifest`/
         `check_mcp`/`assemble` — solo le aree richieste (filtra per `args.area`).
      9. Emette evento osservabilità `doctor` (metrics-only, `contracts/event-doctor.md`):
         `log_event("doctor", overall=..., online=..., n_fail=..., n_warn=..., n_pass=...,
         areas=...)`.
      10. Stampa `format_health_report(report, json_out=args.json)` su stdout.
      11. Se `report.exit_code() == 1`: solleva `DoctorCheckFailed(summary_scrubbed)`
          → `main()` mappa a exit 1 (TASK-S01 pattern).
- [ ] Registra `doctor` nel parser principale (`sub.add_parser`) e dispatch (`handlers` dict o
      `set_defaults(handler=_cmd_doctor)`) — pattern degli altri sottocomandi.
- [ ] **Additività**: nessun percorso esistente alterato (SC-012/NFR-5); import di
      `HealthReport`/`check_*`/`assemble`/`format_health_report`/`DoctorCheckFailed` aggiunti
      in testa al modulo dove risiedono le importazioni degli altri handler.

### TASK-US1-02 — Crea `tests/unit/test_cli_doctor.py`
**File**: `tests/unit/test_cli_doctor.py` (NUOVO)
→ dipende da: TASK-US1-01
- [ ] Setup fixture: mock di `build_indexed_docs`/`IndexManifest`/`read_mcp_registration`/
      `build_provider_probe`/`current_source_stats` + `Settings` sintetici; stile di
      `test_cli_search.py` (core mockato, nessun FS reale).
- [ ] `test_cmd_doctor_all_pass_exit_zero`: installazione sana, tutte le aree pass →
      output umano contiene `"doctor: PASS"`, exit 0 (US1-AC1/SC-004).
- [ ] `test_cmd_doctor_critical_exit_one`: config incompleta (env mancante) → output contiene
      `"FAIL"`, exit 1 (US1-AC2/FR-011/SC-004).
- [ ] `test_cmd_doctor_warn_exit_zero`: solo area MCP warn → exit 0 (US1-AC3).
- [ ] `test_cmd_doctor_json_flag`: `--json` → output è JSON valido con `"schema": "doctor.report/1"`
      (FR-010/SC-003).
- [ ] `test_cmd_doctor_online_triggers_probe`: `--online` → `build_provider_probe` chiamato 1 volta;
      senza `--online` → mai chiamato (FR-008/SC-005/US4-AC1).
- [ ] `test_cmd_doctor_area_config_only`: `--area config` → solo l'area `config` riportata,
      handler non chiama `read_mcp_registration` né `current_source_stats` (DA-D3/SC-001).
- [ ] `test_cmd_doctor_emits_observability_event`: l'handler chiama `log_event` con operation
      `"doctor"` e campi `overall`/`online`/`n_fail`/`n_warn`/`n_pass`/`areas` (metrics-only,
      contratto `event-doctor.md`/Principio IX).
- [ ] `test_cmd_doctor_no_secret_in_output`: output umano e JSON non contengono pattern segreto
      (FR-013/SC-006).
- [ ] `test_cmd_doctor_read_only`: nessun write su FS, nessun upsert, nessun side-effect
      (FR-014/SC-009).
- [ ] Tutti `not cloud`, offline; nessun server MCP avviato.

---

## Fase 3 — Storia 2: Configurazione/env — chiavi mancanti (P1, Must) (1 task)

> Prerequisiti: TASK-F01, TASK-F02 (test `check_config` già coperti; questo task verifica
> il collegamento con `validate_backend()` fonte unica). [P] rispetto a TASK-US3-01/02.

### TASK-US2-01 [P] — Verifica fonte unica `validate_backend()` in `tests/unit/test_cli_doctor.py` e `test_doctor.py`
**File**: `tests/unit/test_cli_doctor.py` + `tests/unit/test_doctor.py`
→ dipende da: TASK-US1-01, TASK-F02
- [ ] In `test_cli_doctor.py`: `test_cmd_doctor_config_area_reflects_validate_backend`:
      mock di `validate_backend()` che ritorna `["AZURE_OPENAI_API_KEY", "AZURE_SEARCH_ENDPOINT"]`
      → report area `config` fail con entrambe le chiavi in `problems[*].fields` (FR-003/FR-004).
- [ ] In `test_cli_doctor.py`: `test_cmd_doctor_local_provider_no_missing_keys`:
      `validate_backend()` ritorna `[]` (provider locale `glove`/`hash`, nessuna credenziale
      richiesta) → area `config` pass (US2-AC2).
- [ ] In `test_doctor.py`: `test_check_config_fonte_unica_nessuna_lista_propria`: verifica che
      `check_config` non contenga costanti con nomi di chiavi env hardcoded — la funzione accetta
      qualunque `list[str]` in input (FR-004/A-001/US2-AC3). Implementazione: controlla che il
      modulo `doctor.py` non importi da `settings.py` costanti di chiavi.
- [ ] In `test_doctor.py`: `test_check_provider_inherits_provider_keys`: `missing_provider` è un
      sottoinsieme derivato da `validate_backend()` per le sole chiavi provider → area `provider`
      fail se queste sono mancanti (DA-D4: area provider eredita criticità env per le chiavi
      provider).
- [ ] Tutti `not cloud`, offline.

---

## Fase 4 — Storia 3: Indice — presente? fresco? (P1 Must, P2 freschezza Should) (2 task)

> Prerequisiti: TASK-F01, TASK-F02 (test `freshness_from_manifest` già coperti), TASK-S02
> (helper `current_source_stats`). TASK-US3-01 e TASK-US3-02 [P] tra loro.

### TASK-US3-01 [P] — Test `current_source_stats` in `tests/unit/test_composition.py`
**File**: `tests/unit/test_composition.py`
→ dipende da: TASK-S02
- [ ] `test_current_source_stats_returns_mtime_for_known_files` (`tmp_path`): crea 2 file;
      `ManifestState` finto con quei path; `current_source_stats(state, root)` ritorna lista
      con mtime corretto per ciascuno (FR-006/SC-007).
- [ ] `test_current_source_stats_deleted_file_returns_zero_mtime` (`tmp_path`): manifest con
      path di un file che non esiste su disco → entry con mtime `0.0` (file cancellato = stantio,
      no crash, SC-007).
- [ ] `test_current_source_stats_none_state`: `state=None` → `[]` (TASK-S02 contratto).
- [ ] `test_current_source_stats_no_rescan`: verifica che l'helper NON utilizzi `glob`/`os.walk`/
      `Path.iterdir()` o equivalenti — opera **solo** sui file registrati nel manifest (FR-006/
      SC-007). Implementazione: mock del manifest con un insieme noto di file, verifica che non
      vengano letti file aggiuntivi.
- [ ] Tutti `not cloud`, `tmp_path` pytest.

### TASK-US3-02 [P] — Verifica test `freshness_from_manifest` per area index in `test_doctor.py`
**File**: `tests/unit/test_doctor.py`
→ dipende da: TASK-F02, TASK-S02
- [ ] Verifica che `test_freshness_absent_manifest` copra **esplicitamente** il rimedio
      `"sertor-rag index ."` nel testo del `Problem.remedy` (US3-AC1/FR-005).
- [ ] Aggiungi `test_freshness_last_index_in_detail`: con indice fresco, `area.detail["last_index"]`
      è una stringa ISO-8601 non-None (US3-AC2/FR-006).
- [ ] Aggiungi `test_freshness_stale_remedy_mentions_reindex`: `warn` stantio →
      `Problem.remedy` contiene `"sertor-rag index ."` (US3-AC3).
- [ ] Aggiungi `test_freshness_no_false_positive_on_unchanged`: stat invariato dopo last-index
      → `pass` (no falsi positivi, SC-007/R-1).
- [ ] Tutti `not cloud`, offline, input sintetici.

---

## Fase 5 — Storia 4: Provider embeddings — statico + probe opt-in (P2, Should) (2 task)

> Prerequisiti: TASK-F01, TASK-F02, TASK-S02 (`build_provider_probe`), TASK-US1-01.
> TASK-US4-01 e TASK-US4-02 [P] tra loro; [P] rispetto a TASK-US5-01/02.

### TASK-US4-01 [P] — Test `build_provider_probe` in `tests/unit/test_composition.py`
**File**: `tests/unit/test_composition.py`
→ dipende da: TASK-S02
- [ ] `test_build_provider_probe_reachable`: mock embedder che non lancia eccezioni →
      `ProviderProbe(status=REACHABLE, reason="")` (US4-AC2).
- [ ] `test_build_provider_probe_unreachable_on_exception`: mock embedder che lancia
      `EmbeddingError("timeout")` → `ProviderProbe(status=UNREACHABLE, reason=<scrubbed>)`;
      motivo non contiene segreti (FR-013/SC-006/US4-AC3).
- [ ] `test_build_provider_probe_allow_download_false`: verifica che `build_embedder` sia chiamato
      con `allow_download=False` → GloVe non viene scaricato (DA-D5/R-2/SC-008).
- [ ] `test_build_provider_probe_no_upsert`: `embed` è chiamato con un'unica stringa sentinella;
      nessun metodo di `VectorStore` viene invocato (SC-008/FR-008: non-indicizzante).
- [ ] Tutti `not cloud`, mock embedder senza rete.

### TASK-US4-02 [P] — Verifica test probe in `tests/unit/test_cli_doctor.py`
**File**: `tests/unit/test_cli_doctor.py`
→ dipende da: TASK-US1-01, TASK-US4-01
- [ ] `test_cmd_doctor_no_online_flag_probe_skipped`: senza `--online`, area `provider`
      riporta `detail["probe"] == "skipped"` e nessuna chiamata di rete (FR-007/SC-005/US4-AC1).
- [ ] `test_cmd_doctor_online_probe_unreachable_warn`: `--online` + mock probe UNREACHABLE →
      area `provider` è `warn` (non `fail`), exit 0 se config è completa (DA-D4/US4-AC3).
- [ ] `test_cmd_doctor_online_probe_reachable_pass`: `--online` + mock probe REACHABLE →
      area `provider` è `pass` (US4-AC2).
- [ ] `test_cmd_doctor_glove_unavailable_no_download_with_online`: `build_provider_probe` riceve
      `allow_download=False`; `GloveUnavailableError` → `UNREACHABLE` azionabile, non crash
      (`contracts/cli-doctor.md` §Offline-safe).
- [ ] Tutti `not cloud`, mock `build_provider_probe`.

---

## Fase 6 — Storia 5: Server MCP — registrato? (P2, Should) (2 task)

> Prerequisiti: TASK-F01, TASK-F02, TASK-S02 (`read_mcp_registration`), TASK-US1-01.
> TASK-US5-01 e TASK-US5-02 [P] tra loro; [P] rispetto a TASK-US4-01/02.

### TASK-US5-01 [P] — Test `read_mcp_registration` in `tests/unit/test_composition.py`
**File**: `tests/unit/test_composition.py`
→ dipende da: TASK-S02
- [ ] `test_read_mcp_registration_true` (`tmp_path`): `.mcp.json` con chiave `"mcpServers"`
      contenente voce `"sertor-rag"` → `True` (US5-AC1).
- [ ] `test_read_mcp_registration_false_absent` (`tmp_path`): `.mcp.json` assente → `False`,
      nessuna eccezione (FR-009/US5-AC2).
- [ ] `test_read_mcp_registration_false_no_sertor_key` (`tmp_path`): `.mcp.json` con
      `"mcpServers"` ma nessuna voce `"sertor-rag"` → `False` (US5-AC2).
- [ ] `test_read_mcp_registration_invalid_json` (`tmp_path`): `.mcp.json` corrotto → `False`,
      nessuna eccezione (degrado non-fatale, FR-009).
- [ ] `test_read_mcp_registration_servers_key` (`tmp_path`): `.mcp.json` con chiave `"servers"`
      (formato alternativo) contenente `"sertor-rag"` → `True` (A-003: project scope).
- [ ] `test_read_mcp_registration_readonly`: nessuna scrittura su FS
      (FR-014/SC-009: sola lettura).
- [ ] Tutti `not cloud`, `tmp_path`.

### TASK-US5-02 [P] — Verifica test `check_mcp` e area MCP in `test_cli_doctor.py`
**File**: `tests/unit/test_cli_doctor.py`
→ dipende da: TASK-US1-01, TASK-US5-01
- [ ] `test_cmd_doctor_mcp_not_registered_warn`: `read_mcp_registration=False` → area MCP è
      `warn`, `problem.remedy` menziona `sertor install rag` (US5-AC2/FR-009).
- [ ] `test_cmd_doctor_mcp_registered_pass`: `read_mcp_registration=True`, index fresco →
      area MCP è `pass` (US5-AC1).
- [ ] `test_cmd_doctor_mcp_stale_after_reindex_warn`: `registered=True` + indice stantio →
      area MCP è `warn` con `code="mcp_stale_after_reindex"` best-effort (US5-AC3/DA-D5).
- [ ] `test_cmd_doctor_mcp_never_fail`: in nessuno scenario l'area MCP è `fail` critico
      (DA-D4: MCP non ha esito critico, exit code non influenzato da MCP).
- [ ] Tutti `not cloud`, mock `read_mcp_registration`.

---

## Fase 7 — Storia 6: Output machine-readable per skill e CI (P1, Must) (1 task)

> Prerequisiti: TASK-F01, TASK-F02, TASK-F03, TASK-US1-01, TASK-US1-02.
> [P] rispetto a TASK-US7-01.

### TASK-US6-01 [P] — Verifica schema stabile, exit code gate, redazione in `test_cli_doctor.py` e `test_output.py`
**File**: `tests/unit/test_cli_doctor.py` + `tests/unit/test_output.py`
→ dipende da: TASK-US1-02, TASK-F03
- [ ] In `test_output.py`: `test_json_schema_stable_keys`: JSON prodotto da
      `format_health_report(..., json_out=True)` ha sempre e solo le chiavi top-level
      `schema`, `overall`, `online`, `exit_code`, `areas` — nessuna chiave extra, nessuna
      mancante (SC-003/FR-010).
- [ ] In `test_output.py`: `test_json_areas_always_four_in_order`: `areas` sempre lista di
      4 elementi in ordine `config, provider, index, mcp` (SC-003/schema `doctor.report/1`).
- [ ] In `test_output.py`: `test_json_exit_code_redundant_consistent`: `exit_code` nel JSON
      è coerente con `HealthReport.exit_code()` (SC-003).
- [ ] In `test_cli_doctor.py`: `test_exit_code_gate_critical`: ≥1 problema CRITICAL → exit 1
      (FR-011/SC-004/US6-AC2).
- [ ] In `test_cli_doctor.py`: `test_exit_code_gate_warn_zero`: solo problemi WARN → exit 0
      (FR-011/SC-004/US6-AC2).
- [ ] In `test_cli_doctor.py`: `test_json_and_human_equivalent`: stesso `HealthReport` →
      JSON e umano portano le stesse aree e stessi problemi (SC-003/US6-AC1).
- [ ] In `test_cli_doctor.py`: `test_secret_redacted_in_json`: `problem.message` con
      `"sk-secretkey"` → nel JSON il valore è redatto (FR-013/SC-006/US6-AC3).
- [ ] In `test_cli_doctor.py`: `test_secret_redacted_in_human`: stesso → output umano non
      contiene il pattern segreto (FR-013/SC-006).
- [ ] Tutti `not cloud`, nessun I/O reale.

---

## Fase 8 — Storia 7: Offline-safe by default (P1, Must) (1 task)

> Prerequisiti: TASK-US1-02, TASK-F02. [P] rispetto a TASK-US6-01.

### TASK-US7-01 [P] — Verifica offline-safe e degrado onesto in `test_cli_doctor.py`
**File**: `tests/unit/test_cli_doctor.py`
→ dipende da: TASK-US1-02
- [ ] `test_offline_no_flag_static_checks_complete`: senza `--online`, mock tutti i segnali
      statici → tutte le 4 aree riportate; `build_provider_probe` non chiamato (SC-005/US7-AC1).
- [ ] `test_offline_with_flag_probe_skipped`: `--online` + mock `build_provider_probe`
      che lancia `OSError("unreachable")` → area `provider` riporta `UNREACHABLE` con motivo,
      **nessun crash**, exit 0 se non critico (FR-012/SC-005/US7-AC2).
- [ ] `test_offline_with_flag_read_mcp_no_server_started`: `read_mcp_registration` usa solo
      `json.load` sul file; nessuna connessione a processo server (FR-014/SC-009).
- [ ] `test_no_side_effects_on_config`: nessuna chiamata a funzioni di scrittura su `Settings`,
      manifest o FS (FR-014/SC-009/US7-AC3).
- [ ] `test_glove_offline_allow_download_false_unreachable`: mock `build_embedder` che solleva
      `GloveUnavailableError` → area provider `UNREACHABLE`, motivo azionabile (nomina
      `SERTOR_GLOVE_PATH` e `SERTOR_EMBED_PROVIDER=hash`), nessun download tentato
      (`contracts/cli-doctor.md` §Offline-safe).
- [ ] Tutti `not cloud`, offline.

---

## Fase 9 — Storia 8: `configure --check` reso vivo (P1, Must) — scope `sertor` (2 task)

> Prerequisiti: TASK-US1-01 (il command `doctor` deve esistere nel core). TASK-US8-01
> (modifica `_probe_live`) è bloccante per TASK-US8-02 (test con FakeCommandRunner).

### TASK-US8-01 — `packages/sertor/src/sertor_installer/configure.py`: cablaggio `_probe_live`
**File**: `packages/sertor/src/sertor_installer/configure.py`
→ dipende da: TASK-US1-01
- [ ] In `_probe_live` (riga 369 ca.), cambia il comando invocato da `sertor-rag check` a:
      ```
      sertor-rag doctor --area config --json
      ```
      (FR-016/DA-D3/`contracts/configure-check.md`).
- [ ] Mapping esito subprocess → `LiveCheckOutcome(requested, ok, detail)` (`configure_report.py:58`):
      - Exit 2 / comando assente / `unknown command` → `ok=None`, `detail=` messaggio degrado
        onesto (US8-AC3/FR-018): invariante che `configure --check` non vada mai in crash se
        `doctor` non è disponibile.
      - Exit 0 → `ok=True`, `detail=` «config ok — esegui `sertor-rag doctor` per il quadro
        completo (provider/indice/MCP)» (US8-AC1/FR-016).
      - Exit ≠ 0 (config incompleta) → `ok=False`, `detail=` messaggio config estratto dal JSON
        di `doctor`, già scrubbed via `mask_secret_free` (US8-AC1/FR-013).
- [ ] `configure` **senza** `--check` resta **byte-identico** a oggi (FR-017/SC-011): solo la
      stringa del comando invocato da `_probe_live` è cambiata; nessun altro percorso toccato.
- [ ] Principio XI: invocazione via subprocess del vehicle (`sertor-rag doctor`), mai
      `import build_embedder` o `build_*` dal wizard.

### TASK-US8-02 — Test `_probe_live` in `packages/sertor/tests/` con `FakeCommandRunner`
**File**: `packages/sertor/tests/...test_configure.py` (o file appropriato nella suite `sertor`)
→ dipende da: TASK-US8-01
- [ ] `test_probe_live_exit0_config_ok`: `FakeCommandRunner` ritorna exit 0 + JSON `doctor.report/1`
      con `overall="pass"` → `LiveCheckOutcome(ok=True, ...)`, `detail` menziona
      `sertor-rag doctor` (US8-AC1/FR-016).
- [ ] `test_probe_live_exit1_config_incomplete`: exit 1 + JSON con area `config` `fail` →
      `LiveCheckOutcome(ok=False, ...)`, `detail` contiene messaggio config scrubbed (US8-AC1).
- [ ] `test_probe_live_exit2_usage_error`: exit 2 → `ok=None`, degrado onesto (FR-018/US8-AC3).
- [ ] `test_probe_live_command_unavailable`: `is_available=False` → `ok=None`, degrado onesto
      (FR-018/US8-AC3).
- [ ] `test_configure_without_check_no_runner_call`: `configure` senza `--check` → `_probe_live`
      **non** chiamato, `FakeCommandRunner` con zero invocazioni (regression guard FR-017/SC-011/
      US8-AC2).
- [ ] Verifica che il comando invocato sia `sertor-rag doctor --area config --json` e **non**
      il vecchio `sertor-rag check` (regression guard: il test fallisce se si reintroduce il
      vecchio comando).
- [ ] Tutti `not cloud`, `FakeCommandRunner` offline.

---

## Fase 10 — Polish e cross-cutting (4 task)

> Prerequisiti: tutte le Fasi 0–9. TASK-P01, TASK-P02, TASK-P03 [P]; TASK-P04 dipende da tutti.

### TASK-P01 [P] — Suite non-cloud verde (`sertor-core`)
→ dipende da: tutti i task delle Fasi 0–9
- [ ] `uv run pytest tests/unit/test_doctor.py -v` → verde (tutti i nuovi test).
- [ ] `uv run pytest tests/unit/test_cli_doctor.py -v` → verde.
- [ ] `uv run pytest tests/unit/test_output.py -v` → verde (incluse le estensioni TASK-F03).
- [ ] `uv run pytest tests/unit/test_composition.py -v` → verde (incluse le estensioni
      TASK-S02/US3-01/US4-01/US5-01).
- [ ] `uv run pytest -m "not cloud" tests/unit/` → verde (inclusi i test pre-esistenti:
      `test_cli_search.py`, `test_cli_eval.py`, `test_cli_graph_eval.py`, `test_settings.py`,
      `test_domain.py`, `test_errors.py` — devono restare invariati, SC-012/RNF-5).
- [ ] `uv run pytest -m "not cloud" tests/` → verde (suite completa non-cloud `sertor-core`).
- [ ] `uv run ruff check .` → zero errori sui file nuovi/modificati
      (`services/doctor.py`, `domain/errors.py`, `cli/__main__.py`, `cli/output.py`,
      `composition.py`, `test_doctor.py`, `test_cli_doctor.py`, `test_output.py`,
      `test_composition.py`). Regole E,F,I,UP,B; line-length 100.

### TASK-P02 [P] — Suite non-cloud verde (`sertor`)
→ dipende da: TASK-US8-01, TASK-US8-02
- [ ] `uv run pytest -m "not cloud" packages/sertor/tests/` → verde (inclusi i test
      pre-esistenti di `configure` senza `--check` — invarianti, FR-017/SC-011).
- [ ] `uv run ruff check packages/sertor/` → zero errori su `configure.py` modificato e test.
- [ ] Verifica che la suite `packages/sertor/` non abbia regressioni sui test pre-esistenti
      di `install`/`upgrade`/`uninstall` (SC-012).

### TASK-P03 [P] — Verifica additività residua e SC-001..012
→ dipende da: tutti i task delle Fasi 0–9
- [ ] **SC-012 (additività)**: verifica che i seguenti file NON siano stati modificati:
      - `src/sertor_core/domain/ports.py` (porte invariate)
      - `src/sertor_core/engines/` (tutti i motori invariati)
      - `src/sertor_core/services/retrieval.py` (facade invariata)
      - `src/sertor_core/services/indexing.py` (indexing invariato)
      - `src/sertor_core/adapters/` (tutti gli adapter invariati, escluso composition)
      - `src/sertor_core/cli/__main__.py` — verificare che **solo** `_add_doctor_parser` e
        `_cmd_doctor` siano stati aggiunti, nessun altro handler modificato.
- [ ] **SC-001 (quattro aree)**: `sertor-rag doctor` senza flag riporta le 4 aree — verificato
      in TASK-US1-02 (`test_cmd_doctor_all_pass_exit_zero`).
- [ ] **SC-002 (azionabilità)**: almeno un test per area con causa+rimedio nominati — verificato
      in TASK-F02 (test `check_*`) e TASK-US1-02.
- [ ] **SC-003 (machine-readable)**: schema stabile JSON — verificato in TASK-US6-01 e TASK-F03.
- [ ] **SC-004 (exit code gate)**: exit 1 ⇔ ≥1 CRITICAL — verificato in TASK-US1-02/US6-01.
- [ ] **SC-005 (offline-safe)**: zero rete senza `--online` — verificato in TASK-US7-01.
- [ ] **SC-006 (zero segreti)**: output scrubbed — verificato in TASK-F03/US6-01/US1-02.
- [ ] **SC-007 (freschezza senza falsi positivi)**: manifest + mtime, no re-scan — verificato
      in TASK-US3-01/02.
- [ ] **SC-008 (no indicizzazione di prova)**: probe non upserta — verificato in TASK-US4-01.
- [ ] **SC-009 (sola lettura)**: nessun write — verificato in TASK-US7-01 e TASK-US5-01.
- [ ] **SC-010 (nessun LLM)**: nessuna importazione di LLM nel codice di `doctor.py`,
      `_cmd_doctor`, `output.py` (grep `openai`/`anthropic`/`ollama`/`build_llm` → 0 risultati
      nei file nuovi).
- [ ] **SC-011 (`configure --check` reso vivo)**: verificato in TASK-US8-01/02.
- [ ] **SC-012 (additività)**: suite verde su percorsi pre-esistenti — TASK-P01/P02.

### TASK-P04 — Debito di completamento e promozione rinvii
→ dipende da: TASK-P01, TASK-P02, TASK-P03
- [ ] **Verifica SC-012 knob env**: conferma che nessun nuovo env `SERTOR_DOCTOR_*` sia stato
      introdotto — il probe di rete è governato dal flag CLI `--online`, non da una variabile
      d'ambiente (SC-012/plan.md §Documentazione-debito). Se in future iterazioni il flag
      diventasse un env, quel campo va aggiunto al template `.env` dell'installer (owner E2,
      `requirements/sertor-cli/epic.md`). Registra la conferma come nota nel file di task.
- [ ] **Promozione rinvii durevoli**: verifica che le seguenti voci abbiano già una «casa
      durevole» (non restino appese solo in `specs/074-doctor-salute/`):
      - «stantio MCP forte» (handshake col server) → roadmap `wiki/syntheses/roadmap.md`
        *Nuove funzionalità da discutere* o backlog osservabilità (E3/FEAT-012). Controlla che
        sia già presente; se mancante, aggiungila.
      - «stantio su file nuovi mai indicizzati» → `requirements/usabilita/epic.md` riga
        `FEAT-NNN` o roadmap E12 Could. Controlla e aggiorna se necessario.
      - «distribuzione manopole su ospiti» → `requirements/sertor-cli/epic.md` FEAT-009
        (debito già tracciato nel piano; verifica che la riga esista).
- [ ] **Evento `doctor` metrics-only**: spot check che `log_event("doctor", ...)` non includa
      nomi di chiavi env, valori, stringa sentinella del probe, motivi d'errore del provider,
      path dell'indice, `--corpus` — solo `overall`, `online`, `n_fail`, `n_warn`, `n_pass`,
      `areas` (cardinalità chiusa, `contracts/event-doctor.md`/Principio IX). Verifica nel
      codice di `_cmd_doctor` e nel test `test_cmd_doctor_emits_observability_event`.

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01 (DoctorCheckFailed in errors.py) ──────────────────────────┐
TASK-S02 (composition helpers: probe/mcp/stats) ────────────────────┤
                                                                     │
TASK-F01 (services/doctor.py: entità + funzioni pure) ← S01 ────────┤
TASK-F02 (test_doctor.py: funzioni pure) ← F01                      │
TASK-F03 (output.py: format_health_report) ← F01                    │
                                                                     │
TASK-US1-01 (cli/__main__.py: parser + handler) ← F01, F03, S01, S02
         │
         ├── TASK-US1-02 (test_cli_doctor.py: handler e2e) ← US1-01
         │
         ├── TASK-US2-01 [P] (fonte unica validate_backend) ← US1-01, F02
         │
         ├── TASK-US3-01 [P] (test current_source_stats) ← S02
         ├── TASK-US3-02 [P] (test freshness_from_manifest) ← F02, S02
         │
         ├── TASK-US4-01 [P] (test build_provider_probe) ← S02
         ├── TASK-US4-02 [P] (test probe in cli) ← US1-01, US4-01
         │
         ├── TASK-US5-01 [P] (test read_mcp_registration) ← S02
         ├── TASK-US5-02 [P] (test area MCP in cli) ← US1-01, US5-01
         │
         ├── TASK-US6-01 [P] (schema stabile, exit gate, redazione) ← US1-02, F03
         │
         ├── TASK-US7-01 [P] (offline-safe, degrado onesto) ← US1-02
         │
         └── TASK-US8-01 (configure.py: _probe_live) ← US1-01
                  └── TASK-US8-02 (test FakeCommandRunner) ← US8-01

TASK-P01 [P] (suite non-cloud sertor-core + lint) ← tutti i task 0–9
TASK-P02 [P] (suite non-cloud sertor + lint) ← US8-01, US8-02
TASK-P03 [P] (additività residua SC-001..012) ← tutti i task 0–9
TASK-P04 (debito completamento + promozione rinvii) ← P01, P02, P03
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (quadro in un comando) | Su installazione sana: 4 aree `pass`, exit 0; su ≥1 problema critico: area `fail`, output nomina causa+rimedio, exit 1; su solo problemi warn: exit 0. | TASK-F01/02, TASK-US1-01/02 | MECCANICO |
| **US2** (config/env: chiavi mancanti) | `validate_backend()` fonte unica: `check_config(missing)` produce `fail` con ogni chiave in `fields`; provider locale senza credenziali → `pass`; lista chiavi non duplicata in `doctor.py`. | TASK-F01/02, TASK-US2-01 | MECCANICO |
| **US3** (indice: presente? fresco?) | Manifest assente → `fail` + rimedio `sertor-rag index .`; indice fresco → `pass` + `last_index`; ≥1 sorgente modificata → `warn` stantio + rimedio; valutazione via manifest, no re-scan. | TASK-F01/02, TASK-S02, TASK-US3-01/02 | MECCANICO |
| **US4** (provider: statico + probe, P2) | Senza `--online`: area provider solo stato statico, zero rete; con `--online` + provider raggiungibile → `reachable`; con `--online` + offline → `unreachable` con motivo, mai crash; probe non indicizza mai. | TASK-F01/02, TASK-S02, TASK-US4-01/02 | MECCANICO |
| **US5** (MCP: registrato?, P2) | Server registrato → `pass`; non registrato → `warn` + rimedio; stantio-dopo-reindex → `warn` best-effort; MCP mai `fail` critico. | TASK-F01/02, TASK-S02, TASK-US5-01/02 | MECCANICO |
| **US6** (output machine-readable) | `--json` → documento a schema stabile `doctor.report/1`, campi fissi; exit 1 ⇔ ≥1 CRITICAL; umano e JSON equivalenti; segreti redatti in entrambi. | TASK-F03, TASK-US1-02, TASK-US6-01 | MECCANICO |
| **US7** (offline-safe by default) | Senza `--online` + offline: 4 aree statiche complete, zero rete; con `--online` + offline: probe `unreachable`/`skipped`, nessun crash; nessun side-effect su config/indice. | TASK-US1-02, TASK-US7-01 | MECCANICO |
| **US8** (`configure --check` reso vivo) | `sertor configure --check` esegue verifica config via `doctor --area config --json`; exit 0 → `ok=True` + rimando a `doctor`; exit 1 → `ok=False` + dettaglio scrubbed; doctor non disponibile → degrado onesto `ok=None`; `configure` senza `--check` byte-identico. | TASK-US8-01/02 | MECCANICO |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 (senza prerequisiti — parallelizzabile al 100%):**
- TASK-S01 (`DoctorCheckFailed` in `errors.py`)
- TASK-S02 (helper composition: `build_provider_probe` / `read_mcp_registration` /
  `current_source_stats`)

**Sprint 2 (dopo S01 — in parallelo):**
- TASK-F01 (entità pure + funzioni di diagnosi in `doctor.py` — bloccante per tutto;
  avviarlo il prima possibile)
- TASK-F03 (`format_health_report` in `output.py` — dipende da F01)

**Sprint 3 (dopo F01, F03, S02 — nucleo puro):**
- TASK-F02 (test `test_doctor.py` — dipende da F01)
- TASK-US3-01 [P] (test `current_source_stats` — dipende da S02)
- TASK-US4-01 [P] (test `build_provider_probe` — dipende da S02)
- TASK-US5-01 [P] (test `read_mcp_registration` — dipende da S02)

**Sprint 4 (dopo F01, F03, S01, S02 — cablaggio CLI):**
- TASK-US1-01 (parser + handler `_cmd_doctor` — bloccante per US1-02 e US8-01)

**Sprint 5 (dopo US1-01 — verifiche handler e storie per area):**
- TASK-US1-02 [P] (test handler e2e)
- TASK-US2-01 [P] (fonte unica validate_backend)
- TASK-US3-02 [P] (test `freshness_from_manifest` per area index)
- TASK-US4-02 [P] (test probe in cli)
- TASK-US5-02 [P] (test area MCP in cli)
- TASK-US6-01 [P] (schema, exit gate, redazione — dipende da US1-02, F03)
- TASK-US7-01 [P] (offline-safe — dipende da US1-02)
- TASK-US8-01 (cablaggio `_probe_live` — dipende da US1-01)

**Sprint 6 (dopo US8-01):**
- TASK-US8-02 (test `FakeCommandRunner` — dipende da US8-01)

**Sprint finale (Polish):**
- TASK-P01 [P] (suite verde sertor-core + lint)
- TASK-P02 [P] (suite verde sertor + lint)
- TASK-P03 [P] (additività residua SC-001..012)
- TASK-P04 (debito completamento + rinvii — dopo P01/P02/P03)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E12-FEAT-001 — sertor-rag doctor

Fase SpecKit "tasks" completata per specs/074-doctor-salute.
26 task in 11 fasi:
  Fase 0  Setup                 : 2 task  (TASK-S01/S02 — DoctorCheckFailed + helper composition)
  Fase 1  Fondazionale          : 3 task  (TASK-F01..F03 — entità pure, funzioni diagnosi, formatter)
  Fase 2  Storia 1 (P1 Must)    : 2 task  (TASK-US1-01/02 — parser doctor + handler + test e2e)
  Fase 3  Storia 2 (P1 Must)    : 1 task  (TASK-US2-01 — fonte unica validate_backend)
  Fase 4  Storia 3 (P1 Must)    : 2 task  (TASK-US3-01/02 — current_source_stats + freshness)
  Fase 5  Storia 4 (P2 Should)  : 2 task  (TASK-US4-01/02 — build_provider_probe + test probe)
  Fase 6  Storia 5 (P2 Should)  : 2 task  (TASK-US5-01/02 — read_mcp_registration + test MCP)
  Fase 7  Storia 6 (P1 Must)    : 1 task  (TASK-US6-01 — schema stabile, exit gate, redazione)
  Fase 8  Storia 7 (P1 Must)    : 1 task  (TASK-US7-01 — offline-safe, degrado onesto)
  Fase 9  Storia 8 (P1 Must)    : 2 task  (TASK-US8-01/02 — configure --check reso vivo)
  Fase 10 Polish                : 4 task  (TASK-P01..P04 — suite verde, lint, SC-001..012,
                                           debito completamento)

Tutti i task MECCANICI (26). Copertura: FR-001..018, RNF-1..7, SC-001..012, US1..8.
Nessuna nuova porta, adapter, motore o dipendenza: ADDITIVO puro.
Percorsi esistenti invariati: verificato in TASK-P03 (SC-012).
Scope esteso a pacchetto sertor (TASK-US8-01/02): chiude debito deferred E2/FEAT-003 US5.
Flag CLI --online (nessun env SERTOR_DOCTOR_*): confermato in TASK-P04 (SC-012).

Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/074-doctor-salute/tasks.md` (questo file, nuovo)
