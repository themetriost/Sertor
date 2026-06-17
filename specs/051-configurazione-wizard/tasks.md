# Tasks — `sertor configure` (FEAT-003 epica sertor-cli)

**Branch**: `051-configurazione-wizard` | **Data**: 2026-06-17
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Pacchetto target**: `packages/sertor` (`sertor_installer`)

---

## Legenda

- `[P]` task eseguibile in parallelo con altri `[P]` dello stesso gruppo
- `[BLOCKED: motivo]` task bloccato da dipendenza esterna non ancora soddisfatta
- **(Should/Deferred)** task di US5 — `--check` probe live; dipende da `sertor-rag check` in
  `sertor-core`, non ancora implementato. Implementa il punto di estensione e il degrado onesto
  ora; completa il probe reale quando la FEAT di core arriverà.
- Ogni task ha path espliciti relativi alla radice del repo (`packages/sertor/...`).

---

## Fase 0 — Setup & ricognizione (1 task)

Questa fase non produce codice di produzione ma garantisce che l'ambiente di test sia coerente
prima di iniziare l'implementazione.

- [ ] **T-000** Verificare che la suite esistente di `packages/sertor` sia verde sul branch corrente.
  Comando: `uv run pytest packages/sertor/tests/ -q`.
  Blocco se fallisce: investigare prima di procedere (non-regressione baseline).

---

## Fase 1 — Fondamenta: entità pure e mascheramento (senza CLI, senza I/O) [P]

I task di questa fase sono **indipendenti tra loro** e parallelizzabili. Non toccano `__main__.py`.
Ogni task produce moduli nuovi con i propri test. Dipendenza verso la Fase 2: tutti i task di
questa fase devono essere completati prima di procedere.

### T-100 `mask_secret` — funzione pura di mascheramento [P]

File da creare:
- `packages/sertor/src/sertor_installer/configure_fields.py` (includerà anche il catalogo)

Compito:
- [ ] Implementare `mask_secret(value: str) -> str` in
  `packages/sertor/src/sertor_installer/configure_fields.py`.
  Regola: stringa vuota o solo spazi → `"(unset)"`; valore < 8 caratteri → `"****"`;
  altrimenti `"****" + value[-4:]`. Funzione pura, zero import di terze parti.

File di test da creare:
- `packages/sertor/tests/test_config_fields.py`

Task di test inclusi:
- [ ] `test_mask_secret_empty` — stringa vuota → `"(unset)"`.
- [ ] `test_mask_secret_short` — valore di 4 caratteri → `"****"` (no suffisso).
- [ ] `test_mask_secret_long` — valore di 12 caratteri → `"****" + ultimi 4`.
- [ ] `test_mask_secret_pure` — dato un segreto noto (`"sk-my-secret-key"`), il risultato
  non contiene il valore originale (anti-leak elementare).

---

### T-110 `ConfigField` e catalogo statico [P]

File: `packages/sertor/src/sertor_installer/configure_fields.py` (estende T-100)

Compito:
- [ ] Definire `FieldStatus` (enum: `SET`, `KEPT`, `MISSING`, `OVERWRITTEN`).
- [ ] Definire dataclass `ConfigField(name: str, description: str, secret: bool,
  default: str | None)`.
- [ ] Definire il catalogo statico `FIELD_CATALOG: dict[str, ConfigField]` con le cinque voci
  verificate in `settings.py:203-214` + `env.azure.tmpl`:
  - `AZURE_OPENAI_ENDPOINT` (non segreto, no default)
  - `AZURE_OPENAI_API_KEY` (segreto, no default)
  - `AZURE_OPENAI_EMBED_DEPLOYMENT` (non segreto, default `"text-embedding-3-large"`)
  - `AZURE_SEARCH_ENDPOINT` (non segreto, no default)
  - `AZURE_SEARCH_API_KEY` (segreto, no default)
- [ ] Esporre `get_field(name: str) -> ConfigField` che solleva `KeyError` se il nome non è
  nel catalogo (errore esplicito, Principio IV).

File di test: `packages/sertor/tests/test_config_fields.py` (estende T-100)

Task di test inclusi:
- [ ] **T-110-COV** `test_catalog_covers_all_validate_backend_fields` — test di copertura
  catalogo ↔ `validate_backend` (invariante di non-drift, Principio V / data-model §2).
  Per ogni `backend ∈ {azure, local}` × `store ∈ {local, azure}`, costruisce un `Settings`
  fittizio con quei valori e chiama `Settings.validate_backend()` su un environment privo
  delle variabili; verifica che ogni nome restituito sia presente in `FIELD_CATALOG`.
  Questo test fallisce se il core aggiunge un campo richiesto non coperto dal catalogo.
- [ ] `test_field_catalog_secret_flags` — `AZURE_OPENAI_API_KEY` e `AZURE_SEARCH_API_KEY`
  hanno `secret=True`; gli altri tre hanno `secret=False`.
- [ ] `test_field_catalog_default_deployment` — `AZURE_OPENAI_EMBED_DEPLOYMENT` ha
  `default="text-embedding-3-large"`.
- [ ] `test_local_profile_no_required_fields` — con `backend=local, store=local`,
  `validate_backend` restituisce lista vuota (SC-007: local-only senza cloud).

---

### T-120 Entità di report: `ConfigProfile`, `FieldResolution`, `ValidationOutcome`,
`LiveCheckOutcome`, `ConfigureReport` [P]

File da creare:
- `packages/sertor/src/sertor_installer/configure_report.py`

Compito:
- [ ] Definire `ConfigProfile(backend: str, store: str)` con validazione `__post_init__`
  (valori fuori da `{azure,local}` / `{local,azure}` → `ValueError`, uscirà come exit 2 nel
  parser).
- [ ] Definire `FieldResolution(field: ConfigField, value: str | None, status: FieldStatus,
  source: str)`. I campi con `field.secret=True` devono esporre il valore già mascherato
  (`mask_secret`) tramite una proprietà `display_value`.
- [ ] Definire `ValidationOutcome(complete: bool, missing: tuple[str, ...])`.
- [ ] Definire `LiveCheckOutcome(requested: bool, ok: bool | None, detail: str)`.
- [ ] Definire `ConfigureReport(target: str, profile: ConfigProfile,
  fields: tuple[FieldResolution, ...], validation: ValidationOutcome,
  live_check: LiveCheckOutcome, env_path: str, notes: tuple[str, ...])` con:
  - `exit_code() -> int`: 0 se `validation.complete ∧ (¬live_check.requested ∨ live_check.ok)`,
    altrimenti 1.
  - `render_human() -> str`: formato testo leggibile (backend/store, per-campo name+status,
    validazione, probe se richiesto, env_path, note).
  - `render_json() -> str`: JSON con la struttura del contratto (`contracts/cli-commands.md §6`);
    valori segreti solo mascherati.

File di test da creare:
- `packages/sertor/tests/test_configure_report.py`

Task di test inclusi:
- [ ] **T-120-LEAK** `test_no_secret_in_render_human` — costruisce un `ConfigureReport` con un
  segreto noto (`"sk-secret-1234"`) in un `FieldResolution`; asserisce che la stringa non
  compare in `render_human()`. (SC-008 / FR-013 — anti-leak strutturale)
- [ ] **T-120-LEAK-JSON** `test_no_secret_in_render_json` — stessa asserzione su `render_json()`.
- [ ] `test_exit_code_complete_no_check` — `validation.complete=True`, `live_check.requested=False`
  → `exit_code() == 0`.
- [ ] `test_exit_code_missing_fields` — `validation.complete=False` → `exit_code() == 1`.
- [ ] `test_exit_code_probe_failed` — `validation.complete=True`, `live_check.requested=True`,
  `live_check.ok=False` → `exit_code() == 1`.
- [ ] `test_exit_code_probe_unavailable` — `live_check.ok=None` (degrado onesto) → exit code
  determinato solo dalla validazione statica.
- [ ] `test_render_json_structure` — `render_json()` produce JSON valido con i campi attesi
  (target, profile, fields, validation, live_check, env_path, notes, exit_code).
- [ ] `test_render_human_contains_profile` — `render_human()` contiene backend e store.

---

## Fase 2 — Logica di scrittura e scaffold [P]

I task di questa fase sono parallelizzabili tra loro. Dipendenza: Fase 1 completata.

### T-200 Scaffold `.sertor/.env` da template di backend [P]

File coinvolti (solo lettura/riuso):
- `packages/sertor/src/sertor_installer/install_rag.py` (riuso `read_asset_text`)
- `packages/sertor/src/sertor_installer/resources.py` (riuso `read_asset_text`)
- `packages/sertor-install-kit/src/sertor_install_kit/env_merge.py` (riuso `merge_env`)

File da creare:
- `packages/sertor/src/sertor_installer/configure.py` (modulo orchestratore principale)

Compito:
- [ ] Implementare `scaffold_env_if_absent(target_root: Path, backend: str,
  corpus: str | None = None) -> bool` in `packages/sertor/src/sertor_installer/configure.py`.
  Logica: se `.sertor/.env` non esiste, legge `rag/env.{backend}.tmpl` via `read_asset_text`,
  applica `sanitize_corpus` (da `rag_profile.py`) per il corpus, chiama `merge_env` per scriverlo.
  Restituisce `True` se creato, `False` se già esistente. Non avvia `uv`, non crea indici
  (install ≠ run, FR-015 / FR-030).

File di test da creare:
- `packages/sertor/tests/test_configure_write.py`

Task di test inclusi:
- [ ] `test_scaffold_creates_env_from_template_azure` — `tmp_path` senza `.sertor/.env`;
  chiama `scaffold_env_if_absent(tmp_path, "azure")`; verifica che `.sertor/.env` esista
  e contenga `RAG_BACKEND=azure`.
- [ ] `test_scaffold_creates_env_from_template_local` — stesso per `backend=local`.
- [ ] `test_scaffold_skips_if_existing` — `.sertor/.env` già presente; `scaffold_env_if_absent`
  ritorna `False` e non sovrascrive il contenuto.
- [ ] `test_scaffold_no_uv_no_index` — verifica che `scaffold_env_if_absent` non richiami
  alcun subprocess (mock `SubprocessRunner` non viene invocato).

---

### T-210 Risoluzione valori per-campo (resolve chain) [P]

File: `packages/sertor/src/sertor_installer/configure.py`

Compito:
- [ ] Implementare `resolve_field(field: ConfigField, explicit_values: dict[str, str],
  env_path: Path, interactive: bool) -> FieldResolution` in
  `packages/sertor/src/sertor_installer/configure.py`.
  Catena di risoluzione (research Punto 1):
  1. `explicit_values` (da `--set` / `--backend` / `--store`) → `status=SET, source="flag"`.
  2. Valore non-vuoto già in `env_path` (letto riga per riga, no import pesanti) →
     `status=KEPT, source="existing"`.
  3. Default non-segreto da `field.default` (se `not field.secret`) →
     `status=SET, source="template-default"`.
  4. Se `interactive=True` → prompt via `input()` o `getpass.getpass()` (solo se `field.secret`).
     Invio a vuoto con valore corrente → `KEPT`. → `status=SET, source="prompt"`.
  5. Nessun valore: `status=MISSING, value=None`.
  **Invariante**: nessun prompt mai se `interactive=False` (CI-safe, FR-004 / FR-005).

File di test: `packages/sertor/tests/test_configure_write.py`

Task di test inclusi:
- [ ] `test_resolve_from_flag` — `explicit_values` contiene la chiave → `status=SET,
  source="flag"`.
- [ ] `test_resolve_from_existing_env` — chiave già nel `.env` → `status=KEPT,
  source="existing"`.
- [ ] `test_resolve_from_template_default` — chiave non in env, campo non segreto con default
  → `status=SET, source="template-default"`.
- [ ] **T-210-CI** `test_resolve_missing_non_interactive` — nessuna fonte disponibile e
  `interactive=False` → `status=MISSING, value=None` (mai un prompt, CI-safe, FR-005).
- [ ] `test_resolve_secret_not_echoed` — campo `secret=True`; valore risolto da flag; verifica
  che la `FieldResolution` abbia `display_value` mascherato (non il valore in chiaro).

---

### T-220 Scrittura non-distruttiva con overwrite controllato [P]

File: `packages/sertor/src/sertor_installer/configure.py`
Riuso: `sertor_install_kit.env_merge.merge_env`, `_replace_key_line` (da kit)

Compito:
- [ ] Implementare `write_resolved_fields(env_path: Path,
  resolutions: list[FieldResolution], overwrite: bool) -> list[FieldResolution]`
  in `packages/sertor/src/sertor_installer/configure.py`.
  Logica (research Punto 5, contratto §3):
  - Per ogni `resolution` con `status != MISSING`:
    - Se la chiave ha già un valore non-vuoto in `env_path` E `overwrite=True` →
      chiama `_replace_key_line` (da `sertor_install_kit.env_merge`) → aggiorna `status=OVERWRITTEN`.
    - Altrimenti → lascia `merge_env` aggiungere le chiavi mancanti (comportamento nativo).
  - Le chiavi `MISSING` non vengono scritte (nessuna configurazione parziale, FR-005).
  - Restituisce la lista aggiornata con gli `status` finali.

File di test: `packages/sertor/tests/test_configure_write.py`

Task di test inclusi:
- [ ] **T-220-IDEM** `test_write_idempotent` — stessi input due volte → `env_path` identico
  byte-per-byte dopo il secondo run (FR-014 / SC-005).
- [ ] `test_write_adds_missing_key` — chiave assente in `.env` → aggiunta da `merge_env`.
- [ ] `test_write_keeps_existing_without_overwrite` — chiave già valorizzata, `overwrite=False`
  → valore originale preservato, `status=KEPT`.
- [ ] `test_write_overwrites_with_flag` — chiave già valorizzata, `overwrite=True` →
  `status=OVERWRITTEN`, nuovo valore scritto.
- [ ] `test_write_preserves_unmanaged_lines` — commenti e righe non gestite nel `.env` restano
  intatti dopo la scrittura (FR-010 / spec §Edge Cases).
- [ ] `test_write_no_partial_on_missing` — `resolution` con `status=MISSING` non viene scritto;
  `.env` invariato per quella chiave.
- [ ] **T-220-NOVCS** `test_secret_not_in_versioned_file` — esegue la scrittura; verifica che
  nessun file al di fuori di `.sertor/.env` venga toccato (SC-003 / FR-012).

---

## Fase 3 — US1: Wizard guidato — configura da "vuoto" a "pronto" (MVP P1)

Dipendenza: Fasi 0, 1 e 2 completate.

**Obiettivo**: implementare l'orchestratore `configure_rag()` e agganciarlo al parser.
Al termine di questa fase, `sertor configure --backend azure` o `sertor configure --backend local`
funzionano end-to-end (modalità interattiva — con TTY — e flag-driven).

### T-300 Orchestratore `configure_rag` — flusso principale

File: `packages/sertor/src/sertor_installer/configure.py`

Compito:
- [ ] Implementare `configure_rag(target_root: Path, backend: str, store: str,
  explicit_values: dict[str, str], overwrite: bool, interactive: bool,
  check: bool, runner: CommandRunner | None = None) -> ConfigureReport`
  in `packages/sertor/src/sertor_installer/configure.py`.
  Flusso (research Punto 1 + contratto §2/3/4):
  1. `scaffold_env_if_absent(target_root, backend)` (T-200).
  2. Deriva `env_path = target_root / ".sertor" / ".env"`.
  3. Carica `Settings` con `env_path` nel contesto (o costruisce un dict equivalente per
     `validate_backend`); chiama `Settings.validate_backend()` per ottenere i nomi richiesti.
  4. Per ogni nome richiesto, recupera `ConfigField` da `FIELD_CATALOG`.
  5. Per ogni `ConfigField`, chiama `resolve_field(...)` (T-210).
  6. Se esistono `FieldResolution` con `status=MISSING` E `interactive=False` →
     solleva `ConfigError` che nomina i campi mancanti, **senza scrivere** (FR-005).
  7. Chiama `write_resolved_fields(env_path, resolutions, overwrite)` (T-220).
  8. Ri-carica `Settings` da `env_path` + esegue `validate_backend()` per
     `ValidationOutcome` (fonte unica post-scrittura, contratto §4).
  9. `live_check`: se `check=False` → `LiveCheckOutcome(requested=False, ok=None, detail="")`.
     Se `check=True` → delega a `_probe_live(target_root, runner)` (T-400, placeholder
     per ora: degrado onesto se `sertor-rag check` non disponibile).
  10. Emette evento osservabilità `configure` (backend, store, conteggi set/kept/missing,
      live_check ok/skip) — **mai** valori segreti, solo nomi/conteggi (contratto §8).
  11. Restituisce `ConfigureReport(...)`.

---

### T-310 Sub-parser `configure` in `__main__.py`

File: `packages/sertor/src/sertor_installer/__main__.py`

Compito:
- [ ] Aggiungere il sub-parser `configure` in `_build_parser()`, con:
  - posizionale opzionale `capability` (default `"rag"`, unico valore accettato ora).
  - `--target DIR` (default `"."`, coerente con `install`/`upgrade`/`uninstall`).
  - `--backend {azure,local}` (argparse `choices`, default `"azure"`).
  - `--store {local,azure}` (argparse `choices`, default `None` → verrà risolto come `backend`
    nell'handler).
  - `--set KEY=VALUE` (argparse `action="append"`, ripetibile; validazione `=` obbligatorio →
    exit 2 se mancante).
  - `--overwrite` (flag booleano).
  - `--non-interactive` (flag booleano).
  - `--check` (flag booleano, Should/deferred — presente nel parser ma il probe degrada onesto
    se `sertor-rag check` non è disponibile).
  - `--json` (flag booleano).
- [ ] Aggiungere `_cmd_configure(args) -> int` in `__main__.py`:
  - Valida `--target` (usa `_validate_target` esistente).
  - Costruisce `explicit_values: dict[str, str]` da `args.set` + `args.backend` +
    `args.store`.
  - Determina `interactive = sys.stdin.isatty() and sys.stdout.isatty() and
    not args.non_interactive`.
  - Chiama `configure_rag(...)`.
  - Stampa `report.render_json() if args.json else report.render_human()`.
  - Ritorna `report.exit_code()`.
- [ ] Aggiungere il dispatch in `_dispatch()`: `if args.command == "configure": return
  _cmd_configure(args)`.

---

### T-320 Test CLI — US1 end-to-end

File di test da creare:
- `packages/sertor/tests/test_cli_configure.py`

Task di test inclusi (tutti F.I.R.S.T., no rete, no cloud):
- [ ] **T-320-HELP** `test_configure_help_exit_0` — `main(["configure", "--help"])` → exit 0;
  output contiene `"backend"` e `"check"`.
- [ ] **T-320-LOCAL** `test_configure_local_exit_0` — `main(["configure", "--backend", "local",
  "--target", str(tmp_path)])` → exit 0; `.sertor/.env` contiene `RAG_BACKEND=local`; nessun
  campo cloud richiesto (SC-007 / FR-006).
- [ ] **T-320-AZURE-NODEPS** `test_configure_azure_flag_driven_exit_0` — tutti i campi azure
  forniti via `--set`; `--non-interactive`; exit 0; `.sertor/.env` contiene i valori.
- [ ] **T-320-MISSING** `test_configure_missing_field_non_interactive_exit_1` — backend `azure`,
  campo `AZURE_OPENAI_API_KEY` assente, `--non-interactive`; exit 1; stderr nomina il campo
  mancante; `.sertor/.env` non contiene la chiave (nessuna scrittura parziale, FR-005).
- [ ] **T-320-MALFORMED-SET** `test_configure_set_without_equals_exit_2` — `--set BADKEY` →
  exit 2 (UsageError, contratto §7).
- [ ] **T-320-BAD-BACKEND** `test_configure_bad_backend_exit_2` — `--backend foo` → exit 2
  (argparse `choices`).
- [ ] **T-320-JSON** `test_configure_json_output` — `--json`; output è JSON valido; contiene
  chiave `"exit_code"`.
- [ ] **T-320-NORUN** `test_configure_does_not_index` — verifica che nessun processo `uv` o
  `sertor-rag index` venga avviato (mock `SubprocessRunner`; zero invocazioni di indexing).
  (install ≠ run, FR-030 / SC-009)
- [ ] **T-320-NOLEAK** `test_configure_no_secret_in_stdout` — fornisce un segreto noto via
  `--set AZURE_OPENAI_API_KEY=mysecret`; verifica che `"mysecret"` non compaia in `capsys.readouterr().out`
  né `.err` (SC-008 / FR-013 — anti-leak CLI).

---

## Fase 4 — US2: Modalità CI-safe e idempotenza (P1)

Dipendenza: Fase 3 completata (T-300/310/320 verdi).

Questa fase consolida le garanzie CI-safe e di idempotenza con test aggiuntivi più mirati.
La maggior parte della logica è già in T-210/220/320; qui si aggiungono i test che chiudono
formalmente i criteri di accettazione di US2.

### T-400 Test CI-safe e idempotenza — US2

File di test: `packages/sertor/tests/test_cli_configure.py` (estende Fase 3)

Task di test inclusi:
- [ ] **T-400-CI-COMPLETE** `test_ci_complete_no_prompt` — simula assenza TTY
  (`monkeypatch` su `sys.stdin.isatty` → `False`); tutti i campi forniti via ambiente
  (`monkeypatch.setenv`); exit 0; nessun prompt chiamato (mock `input`/`getpass` mai
  invocato). (FR-004 / SC-006)
- [ ] **T-400-CI-MISSING** `test_ci_missing_field_explicit_error` — assenza TTY + campo
  richiesto mancante; exit 1; messaggio nomina il campo per nome (FR-005). Verifica che
  `.sertor/.env` non contenga la chiave mancante con un valore parziale.
- [ ] **T-400-IDEM** `test_configure_idempotent_double_run` — due esecuzioni con gli stessi
  flag/environment su `tmp_path`; il contenuto di `.sertor/.env` è identico dopo il secondo run
  (SC-005 / FR-014). Usa comparazione hash o byte-level.
- [ ] **T-400-KEPT** `test_configure_keeps_extra_env_vars` — `.sertor/.env` contiene una
  variabile non gestita dal comando (es. `MY_CUSTOM_VAR=hello`); dopo `configure`, quella riga
  è ancora presente (merge additivo non distruttivo, FR-010).

---

## Fase 5 — US3: Profilo locale senza cloud (P1)

Dipendenza: Fase 3 completata.

I test di US3 verificano in modo mirato che il profilo `local` non richieda e non scriva campi
cloud. La logica è già coperta dall'orchestratore (T-300) tramite `validate_backend` che ritorna
`[]` per il profilo locale; questa fase aggiunge i test di accettazione specifici.

### T-500 Test profilo locale — US3

File di test: `packages/sertor/tests/test_cli_configure.py` (estende Fase 3)

Task di test inclusi:
- [ ] **T-500-LOCAL-NOCLOUD** `test_local_profile_no_cloud_fields` — `--backend local`;
  verifica che nel report (umano o JSON) non compaia alcuna delle cinque variabili cloud
  (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBED_DEPLOYMENT`,
  `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`). (SC-007 / FR-006)
- [ ] **T-500-LOCAL-VALID** `test_local_profile_validation_complete` — `--backend local`;
  `validation.complete=True`; exit 0; nessun campo mancante nel report. (US3 SC-002)
- [ ] **T-500-LOCAL-ENV** `test_local_profile_env_has_backend_local` — dopo il run,
  `.sertor/.env` contiene `RAG_BACKEND=local`.

---

## Fase 6 — US4: Riconfigurazione non distruttiva (P2)

Dipendenza: Fasi 3 e 4 completate.

### T-600 Test riconfigurazione — US4

File di test: `packages/sertor/tests/test_cli_configure.py` (estende Fase 3)

Task di test inclusi:
- [ ] **T-600-KEEP** `test_reconfigure_keeps_existing_without_overwrite` — su `.sertor/.env`
  con `AZURE_OPENAI_ENDPOINT=https://vecchio.endpoint/`; riesegue `configure` con
  `--set AZURE_OPENAI_ENDPOINT=https://nuovo.endpoint/` senza `--overwrite` e senza TTY;
  verifica che il valore in `.env` sia ancora `https://vecchio.endpoint/` e che il report
  segnali `status=kept`. (FR-011 / SC-005)
- [ ] **T-600-OVERWRITE** `test_reconfigure_overwrites_with_flag` — stesso scenario con
  `--overwrite`; verifica che il valore sia aggiornato a `https://nuovo.endpoint/` e che
  il report segnali `status=overwritten`. (FR-011)
- [ ] **T-600-COMMENTS** `test_reconfigure_preserves_comments_and_unmanaged` — `.sertor/.env`
  con commenti (`# mio commento`) e una riga non gestita (`MY_CUSTOM=hello`); dopo il run,
  entrambi sono ancora presenti. (FR-010)

---

## Fase 7 — US5: Validazione statica + stub probe live (P2 / Should)

Dipendenza: Fase 3 completata. I task di probe reale sono **bloccati** da dipendenza esterna.

### T-700 Stub punto di estensione `_probe_live` con degrado onesto

**NOTA US5 / `--check`**: il probe live reale dipende da `sertor-rag check` (o equivalente),
un sottocomando minimale del vehicle `sertor-core` **non ancora implementato**. Questo è stato
promosso a backlog come FEAT separata in `requirements/sertor-core/` (research Punto 3 /
plan §Capacità da promuovere). Il task T-700 implementa lo stub di degrado onesto e il punto
di estensione; il completamento reale del probe arriverà con quella FEAT.

File: `packages/sertor/src/sertor_installer/configure.py`

Compito:
- [ ] Implementare `_probe_live(target_root: Path, runner: CommandRunner | None)
  -> LiveCheckOutcome` in `packages/sertor/src/sertor_installer/configure.py`.
  Comportamento attuale (degrado onesto, contratto §5 riga 4):
  - Tenta di localizzare l'eseguibile `sertor-rag` nell'isolato `.sertor/` dell'ospite.
  - Invoca `sertor-rag check` via `runner` (subprocess, Principio XI; **non** importa
    `build_embedder`).
  - Se il sottocomando non esiste o il processo esce con un errore che indica "unknown command" →
    `LiveCheckOutcome(requested=True, ok=None, detail="probe live non disponibile in questa
    versione del runtime (sertor-rag check non trovato)")`.
  - Se esce 0 → `LiveCheckOutcome(requested=True, ok=True, detail="")`.
  - Se esce non-0 con un messaggio azionabile → `LiveCheckOutcome(requested=True, ok=False,
    detail=<messaggio dal subprocess>)`.
  Il punto di estensione è pronto: quando `sertor-rag check` sarà implementato, questa funzione
  funzionerà senza modifiche al flusso dell'orchestratore.

File di test da creare:
- `packages/sertor/tests/test_configure_check.py`

Task di test inclusi (tutti usano `runner` mock, zero rete):
- [ ] **T-700-NOCHECK** `test_check_not_requested_no_network` — `configure_rag(..., check=False)`;
  `runner` mock mai invocato; `live_check.requested=False, ok=None`. (FR-022 / SC-009)
- [ ] **T-700-UNAVAILABLE** `test_check_degrades_when_sertor_rag_check_missing` —
  `runner` mock che simula `sertor-rag check` con exit 2 (unknown command); ritorna
  `ok=None, detail` contiene "non disponibile". (contratto §5 degrado onesto)
- [ ] **T-700-FAIL** `test_check_fails_env_intact` — `runner` mock che simula probe fallito
  (exit 1 con messaggio azionabile); `ok=False`; `.sertor/.env` non viene rimosso o alterato
  (FR-023). (BLOCKED: richiede `sertor-rag check` reale per il test end-to-end; questo test usa
  solo il mock)
- [ ] **T-700-OK** `test_check_ok` — `runner` mock che simula probe con exit 0; `ok=True`.
  (BLOCKED: richiede `sertor-rag check` reale per il test di integrazione — il mock passa)

**Task bloccati / deferred** — da completare quando FEAT `sertor-rag check` sarà su `master`:
- [ ] [BLOCKED: `sertor-rag check` non implementato] `test_check_integration_azure` — test di
  integrazione end-to-end con un environment Azure reale e `runner` reale. Marcato
  `@pytest.mark.integration` e `@pytest.mark.cloud`.
- [ ] [BLOCKED: `sertor-rag check` non implementato] Aggiornare `_probe_live` per usare il
  sottocomando reale una volta disponibile (nessuna modifica al flusso, solo rimuovere il
  degrado "non trovato").

---

### T-710 Test validazione statica — US5 accettazione (senza probe)

File di test: `packages/sertor/tests/test_cli_configure.py`

Task di test inclusi:
- [ ] **T-710-COMPLETE** `test_static_validation_complete_exit_0` — `--backend local`;
  validazione statica `complete=True`; exit 0; report contiene `"complete": true`. (US5 SC1)
- [ ] **T-710-MISSING** `test_static_validation_missing_exit_1` — `--backend azure`,
  `--non-interactive`, senza campi azure; exit 1; report elenca i campi mancanti;
  `.env` scritto ma marcato incompleto (FR-021). (US5 SC2)

---

## Fase 8 — Polish e verifiche cross-cutting

Dipendenza: Fasi 3–7 completate.

### T-800 Verifica non-regressione comandi esistenti [P]

File di test: suite esistente `packages/sertor/tests/`

Compito:
- [ ] Eseguire `uv run pytest packages/sertor/tests/ -q --tb=short` e verificare che TUTTI i test
  preesistenti rimangano verdi. Il sub-parser `configure` è additivo: nessun comando esistente
  (`install`, `upgrade`, `uninstall`) deve essere alterato nel comportamento (NFR non-regressione,
  plan §Summary).
- [ ] Verificare che `main(["--help"])` contenga ancora `"install"`, `"upgrade"`, `"uninstall"`
  (test già presente in `test_cli.py`, non va rotto).

---

### T-810 Verifica host-agnostico [P]

Compito:
- [ ] Aggiungere in `packages/sertor/tests/test_cli_configure.py` (o `test_host_agnostic.py`):
  `test_configure_host_agnostic` — esegue `configure --backend local` su due `tmp_path` distinti
  con nomi cartella diversi; entrambi producono un `.sertor/.env` valido con `SERTOR_CORPUS` che
  riflette il nome della cartella sanitizzato. Nessun path fisso hardcodato nel codice.
  (Principio X / FR-033)

---

### T-820 Lint e copertura [P]

Compito:
- [ ] Eseguire `uv run ruff check packages/sertor/` — zero errori (nessun F/E/I/UP/B non risolto,
  line-length 100). Correggere eventuali warning prodotti dal nuovo codice.
- [ ] Verificare che `packages/sertor/tests/test_config_fields.py::test_catalog_covers_all_validate_backend_fields`
  (T-110-COV) sia incluso nell'esecuzione CI ordinaria (no marker `cloud` / `integration`):
  è un test puramente statico (no rete, no env cloud) e deve girare in ogni PR.

---

### T-830 Evento osservabilità — nessun segreto nei log [P]

File di test: `packages/sertor/tests/test_cli_configure.py`

Compito:
- [ ] `test_observability_event_no_secrets` — esegue `configure --backend azure` con un segreto
  noto via `--set`; cattura l'evento `configure` emesso da `log_event` (mock del logger o
  caplog pytest); verifica che il messaggio strutturato non contenga il segreto in chiaro.
  (Principio IX / contratto §8)

---

## Grafo delle dipendenze (sintesi)

```
Fase 0 (T-000)
    └─▶ Fase 1 [P]: T-100, T-110, T-120
           └─▶ Fase 2 [P]: T-200, T-210, T-220
                  └─▶ Fase 3 (T-300 → T-310 → T-320)
                         ├─▶ Fase 4 (T-400) [consolida CI-safe]
                         ├─▶ Fase 5 (T-500) [local profile]
                         ├─▶ Fase 6 (T-600) [riconfigurazione]
                         └─▶ Fase 7 (T-700 + T-710) [validazione + probe stub]
                                └─▶ Fase 8 [P]: T-800, T-810, T-820, T-830
```

**Parallelismi sfruttabili:**
- Fase 1: T-100, T-110, T-120 completamente indipendenti tra loro (tre sviluppatori simultanei).
- Fase 2: T-200, T-210, T-220 parzialmente indipendenti (T-220 usa output di T-210).
- Fasi 4, 5, 6, 7: indipendenti tra loro dopo Fase 3 — quattro sviluppatori simultanei.
- Fase 8: tutti i task [P] indipendenti.

---

## Strategia MVP / incrementale

**MVP consegnabile dopo Fase 3** (US1 completa):
- `sertor configure --backend local` → configura profilo locale, exit 0.
- `sertor configure --backend azure --set KEY=VAL ... --non-interactive` → CI-safe.
- `sertor configure --backend azure` (con TTY) → wizard interattivo.
- Validazione statica inclusa (è parte dell'orchestratore, non opzionale).

**Valore P1 completo dopo Fasi 3+4+5** (US1+US2+US3):
- Copertura di tutti e tre i must di priorità P1.
- Suite verde, anti-leak verificato, CI-safe garantito.

**Valore P2 dopo Fasi 6+7** (US4+US5):
- Riconfigurazione non-distruttiva (US4).
- Validazione statica esplicita + stub probe onesto (US5 senza probe reale).

**US5 `--check` probe reale**: bloccata da FEAT `sertor-rag check` in `sertor-core`.
Il flag `--check` è già nel parser e il codice degrada onestamente; quando la FEAT arriverà
su `master`, basterà aggiornare `_probe_live` senza toccare l'orchestratore.

---

## Riepilogo task per fase

| Fase | Descrizione | Task | Priority |
|------|-------------|-----:|:--------:|
| 0 | Setup & verifica baseline | 1 | — |
| 1 | Entità pure (mask_secret, ConfigField, ConfigureReport) | 12 | P1 |
| 2 | Logica scrittura (scaffold, resolve, write) | 11 | P1 |
| 3 | US1 wizard guidato (orchestratore + parser + test CLI) | 12 | P1 |
| 4 | US2 CI-safe & idempotenza | 4 | P1 |
| 5 | US3 profilo locale senza cloud | 3 | P1 |
| 6 | US4 riconfigurazione non-distruttiva | 3 | P2 |
| 7 | US5 validazione statica + stub probe live | 6 (+2 bloccati) | P2/Should |
| 8 | Polish (non-regressione, host-agnostico, lint, obs) | 4 | — |
| **Tot.** | | **56** (+2 bloccati) | |

> I 2 task bloccati in Fase 7 (`test_check_integration_azure` e aggiornamento `_probe_live`
> per il probe reale) attendono la FEAT `sertor-rag check` in `sertor-core`. Sono marcati
> `[BLOCKED]` e non impediscono la consegna del P1 né del resto del P2.
