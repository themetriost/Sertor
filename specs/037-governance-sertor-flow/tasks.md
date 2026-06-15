# Tasks: Installer di governance/SDLC `sertor-flow`

**Feature**: 037-governance-sertor-flow · **Branch**: `037-governance-sertor-flow`
**Input**: [plan.md](plan.md) · [research.md](research.md) · [data-model.md](data-model.md) ·
[contracts/](contracts/) · [spec.md](spec.md)

**Convenzione**: `- [ ] [TaskID] [P?] [Story?] Descrizione con percorso file`. `[P]` = parallelizzabile
(file diversi, nessuna dipendenza su task incompleti).

**Nota tecnica chiave**: il pezzo più rischioso è la **Fase 2 (estrazione del toolkit + repoint di
`sertor`)**: è refactor di codice funzionante, il gate è la **non-regressione della suite
`packages/sertor`**. Le user story si poggiano su quel toolkit.

---

## Phase 1: Setup

- [ ] T001 Crea lo scheletro del membro workspace `packages/sertor-install-kit/` (dir
  `src/sertor_install_kit/` con `__init__.py`, `tests/unit/`, `tests/integration/`) e
  `packages/sertor-install-kit/pyproject.toml` (`name=sertor-install-kit`, `requires-python>=3.11`,
  `license=MIT`, **nessuna dipendenza runtime**, build hatchling con `packages=["src/sertor_install_kit"]`,
  `[tool.pytest.ini_options]` con `pythonpath=["src"]`).
- [ ] T002 Crea lo scheletro del membro workspace `packages/sertor-flow/` (dir `src/sertor_flow/` con
  `__init__.py`, `src/sertor_flow/assets/`, `tests/unit/`, `tests/integration/`) e
  `packages/sertor-flow/pyproject.toml` (`name=sertor-flow`, `dependencies=["sertor-install-kit"]`,
  `[project.scripts] sertor-flow="sertor_flow.__main__:main"`, build hatchling
  `packages=["src/sertor_flow"]`, `[tool.uv.sources] sertor-install-kit={workspace=true}`).
- [ ] T003 Aggiorna la root `pyproject.toml`: `[tool.uv.workspace] members` →
  `["packages/sertor", "packages/sertor-install-kit", "packages/sertor-flow"]`; `[tool.ruff] src`
  esteso ai nuovi `packages/*/src` e `packages/*/tests`; `[tool.ruff.lint.isort] known-first-party` +=
  `sertor_install_kit`, `sertor_flow`.
- [ ] T004 `uv sync --extra dev` e verifica che i tre membri si risolvano (editable dal workspace);
  `uv run python -c "import sertor_install_kit, sertor_flow"` ok.

---

## Phase 2: Foundational — Estrazione toolkit + repoint `sertor` (BLOCCANTE per tutte le storie)

> Goal: il motore di installazione vive in `sertor-install-kit` (stdlib-only, **niente `sertor-core`**),
> e `sertor` (wiki/rag) lo riusa restando **verde**. **Gate**: `uv run pytest packages/sertor/tests`
> tutto verde dopo il repoint.

### Nuovi moduli del kit

- [ ] T005 Crea `packages/sertor-install-kit/src/sertor_install_kit/errors.py`: `InstallerError(Exception)`
  e `ConfigError(InstallerError)` (sostituiscono la dipendenza da `sertor_core.domain.errors`).
- [ ] T006 Crea `packages/sertor-install-kit/src/sertor_install_kit/observability.py`:
  `log_event(level, operation, **fields)` su `logging` stdlib (extra strutturato, **nessun segreto**),
  senza dipendere dal core.

### Migrazione dei primitivi (da `packages/sertor/src/sertor_installer/` al kit)

- [ ] T007 [P] Sposta `artifacts.py` → `packages/sertor-install-kit/src/sertor_install_kit/artifacts.py`
  (`Artifact`/`ArtifactKind`/`WriteStrategy`/`Outcome`/`ArtifactOutcome`); repoint
  `from sertor_core.domain.errors import ConfigError` → `from sertor_install_kit.errors import ConfigError`.
- [ ] T008 [P] Sposta `resources.py` → kit, generalizzando l'anchor: `asset_path(anchor, relative)` /
  `read_asset_text(anchor, relative)` / `iter_asset_dir(anchor, relative)` (l'anchor è il package del
  consumatore, non più fisso `sertor_installer`).
- [ ] T009 [P] Sposta `report.py` → kit (`InstallReport`/`ArtifactOutcome`). **Mantieni il metodo
  esistente `render_json()`** (NON rinominare in `to_json()` — eviti di toccare i call-site di `sertor`,
  F1) e **generalizza il default `capability`**: oggi è `capability: str = "wiki"` → rendilo argomento
  **obbligatorio** (no default) così `sertor-flow` passa `"governance"` esplicito e i title di reso non
  ereditano `"wiki"` (F4). Aggiorna i call-site di `sertor` (wiki/rag) per passare la capability
  esplicita.
- [ ] T010 [P] Sposta i merge additivi → kit: `settings_merge.py`, `env_merge.py`, `mcp_merge.py`,
  `gitignore_append.py` (repoint eventuali import di errori al kit).
- [ ] T011 [P] Sposta `command_runner.py` → kit (`CommandRunner`, `is_available`/`run`).
- [ ] T012 Generalizza `claude_md.py` → kit:
  `write_marker_block(path, content, marker_start, marker_end) -> Outcome` (3 casi assente/append/skip,
  preservazione byte-per-byte fuori dai marker). NON inchiodare più i marker wiki.
- [ ] T013 Crea `packages/sertor-install-kit/src/sertor_install_kit/executor.py`:
  `execute_plan(plan, apply) -> InstallReport` generico (callback `apply: Artifact -> ArtifactOutcome`,
  fail-fast no-rollback, `failed_step`).
- [ ] T014 Sposta `sync.py` → kit, parametrizzando le radici asset (anchor + lista di sottoalberi, es.
  `claude`/`specify`) e la directory destinazione, così è riusabile da `sertor` e `sertor-flow`.
- [ ] T015 [P] Esporta la superficie pubblica del kit da
  `packages/sertor-install-kit/src/sertor_install_kit/__init__.py` (tipi, errori, report, merge,
  `write_marker_block`, `execute_plan`, resources, `CommandRunner`, `log_event`).
- [ ] T016 [P] Porta i test dei primitivi nel kit
  (`packages/sertor-install-kit/tests/unit/`: artifacts, merge, claude_md marker parametrico, executor
  fail-fast, resources, report json) e rendili verdi: `uv run pytest packages/sertor-install-kit/tests`.

### Repoint di `sertor` (packages/sertor) sul kit — non-regressione

- [ ] T017 `packages/sertor/pyproject.toml`: aggiungi `sertor-install-kit` alle `dependencies` (+
  `[tool.uv.sources] sertor-install-kit={workspace=true}`).
- [ ] T018 **(atomico con T019 — F2)** Repoint degli import in
  `packages/sertor/src/sertor_installer/install_wiki.py` e `install_rag.py` ai simboli del kit
  (`artifacts`, `report`, `resources`, `claude_md`, merge, `command_runner`, `executor.execute_plan`);
  rimuovi i moduli ormai migrati da `sertor_installer` (o lasciali come re-export sottili se altri li
  importano). **Va fatto NELLO STESSO cambiamento di T019** (il repoint dell'esecutore — che ora cattura
  `InstallerError` invece di `SertorError` — senza il wrapping di T019 lascerebbe una finestra in cui la
  suite `sertor` si rompe).
- [ ] T019 **(atomico con T018 — F2)** In `install_wiki.py`: avvolgi gli errori di
  `sertor_core.wiki_tools` (`load_profile`, `init_structure`) in `InstallerError` al boundary (D3), così
  `execute_plan` (che cattura `InstallerError`) mantiene il fail-fast; `write_ritual_block` ora chiama
  `write_marker_block(..., MARKER_START_WIKI, MARKER_END_WIKI)` con i marker wiki esistenti. **Eseguire
  T018+T019 come unico passo atomico**, poi T021 valida.
- [ ] T020 Allinea `sync.py`/`test_assets_sync.py` di `packages/sertor` alla nuova firma del kit (anchor
  `sertor_installer`).
- [ ] T021 **GATE non-regressione**: `uv run pytest packages/sertor/tests` tutto verde; `uv run ruff
  check packages/sertor packages/sertor-install-kit`.

**Checkpoint**: il toolkit è estratto, `sertor` resta verde. Si può costruire `sertor-flow`.

---

## Phase 3: User Story 1 — Portare il metodo SDLC con un comando (Priority: P1) 🎯 MVP

> Goal: `sertor-flow install` deposita l'intero bundle governance su un ospite, non distruttivo,
> install≠run. **Independent test**: su repo pulito → bundle presente e invocabile, nessuna fase avviata.

### Profilo, generazione, plan, apply

- [x] T022 [US1] `packages/sertor-flow/src/sertor_flow/profile.py`: `GovernanceProfile`
  (`target_root`, `assistant="claude"`, `script` inferito da OS `ps|bash`, `speckit_version="0.8.18"`) +
  `build_governance_profile(target_root, ...)` (inferenza, stile `config_gen.build_host_profile`).
- [x] T023 [US1] `packages/sertor-flow/src/sertor_flow/generate.py`: generazione dei file init/integration
  per-host da template (`init-options.json`, `integration.json`, `integrations/*.manifest.json`)
  iniettando i valori del `GovernanceProfile` (D7).
- [x] T024 [US1] `packages/sertor-flow/src/sertor_flow/install_governance.py`:
  `build_governance_plan(profile) -> list[Artifact]` nell'ordine canonico (data-model §piano): FILE×N da
  `assets/claude/**`, FILE×N da `assets/specify/**`, CONFIG starter costituzione, **CONFIG init×M**, FILE
  NOTICE/licenza, MARKER_BLOCK SDLC. Piano **derivato** dalla composizione (FR-005), `feature.json`
  escluso. **(F10/F12)** I file init/integration per-host usano il `kind` esistente **`CONFIG` con
  strategia `GENERATE_CONFIG`** (genera-da-template, skip-se-presente) — **NESSUN nuovo `ArtifactKind`
  `GENERATE_INIT`**: l'executor non va esteso con un kind nuovo.
- [x] T025 [US1] In `install_governance.py`: le `apply`-functions per ogni `kind`
  (`_apply_file` CREATE_IF_ABSENT, `_apply_config` starter skip-se-esiste, `_apply_generate_init`,
  `_apply_marker` con marker SDLC, `_apply_notice`) + `execute_governance_plan(profile)` che chiama
  `kit.execute_plan(plan, apply)`; ritorna `InstallReport(capability="governance")`.
- [x] T026 [US1] `packages/sertor-flow/src/sertor_flow/__main__.py`: CLI `sertor-flow install
  [--target PATH] [--json]` (argparse), wiring a `build_governance_profile` + `execute_governance_plan`,
  resa umana + `--json` (FR-018/020), exit code (0 ok, ≠0 su passo fallito). **install≠run** (nessuna
  fase avviata).

### Bundle assets (US1) — vendoring + Sertor-authored

- [x] T027 [P] [US1] Copia gli asset **Sertor-authored** in `packages/sertor-flow/src/sertor_flow/assets/`:
  `claude/skills/requirements/**` (da `.claude/skills/requirements/`),
  `claude/agents/requirements-analyst.md`, `claude/agents/configuration-manager.md` (da `.claude/agents/`).
- [x] T028 [P] [US1] Vendora gli asset **spec-kit** (pinned 0.8.18) in `assets/claude/`:
  `skills/speckit-*` + `skills/speckit-git-*` (da `.claude/skills/`), `agents/speckit-*.md` (da
  `.claude/agents/`).
- [x] T029 [P] [US1] Vendora il macchinario **`.specify/`** in `assets/specify/` — **attenzione alle
  due fonti (F3)**:
  - `templates/**`, `extensions/git/**` (che già contiene `scripts/{bash,powershell}/`), `workflows/**`
    → dal **dogfood** `.specify/` del repo.
  - `scripts/{bash,powershell}/**` (script di scaffolding: check-prerequisites/common/create-new-feature/
    setup-plan/setup-tasks) → **dall'upstream spec-kit pinnato** `C:\Workspace\Git\ExternalRepos\spec-kit\
    scripts\{bash,powershell}\` (il dogfood `.specify/scripts/` ha SOLO powershell; l'upstream 0.8.18 ha
    **entrambe** le shell → è la fonte corretta per soddisfare DA-e "ship both ps+bash").
- [x] T030 [P] [US1] Crea i template generati per-host in `assets/`: `init-options.json.tmpl`,
  `integration.json.tmpl`, `integrations/*.manifest.json.tmpl` (placeholder per assistant/script/
  speckit_version).
- [x] T031 [P] [US1] Crea `assets/constitution-starter.md` (Sertor-authored, NEUTRA): principi generali
  III/IV/VI/VII + kernel de-RAGizzati di I/V/VIII/IX + sezioni Sicurezza e Governance; **esclusi II e X**
  (base testuale: `assets/specify/templates/constitution-template.md`).
- [x] T032 [P] [US1] Crea `assets/claude-md-block-sdlc.md` (EN): blocco rituale SDLC (flusso SpecKit,
  Constitution Check, delega git al configuration-manager, branch+PR), **owner** della disciplina
  git/commit; sarà racchiuso nei marker `SERTOR:SDLC-RITUAL`.
- [x] T033 [P] [US1] Crea l'attribuzione: `assets/NOTICE` + `assets/LICENSES/spec-kit-MIT.txt` (testo MIT
  di GitHub spec-kit) — REQ-022/SC-007.

### Test US1

- [x] T034 [US1] Integration test `packages/sertor-flow/tests/integration/test_install_governance.py`:
  `sertor-flow install --target <tmp>` su repo pulito → report con artefatti `created`; verifica presenza
  di `.claude/skills/speckit-specify/`, `.claude/agents/requirements-analyst.md`,
  `.specify/templates/plan-template.md`, `.specify/scripts/{bash,powershell}/`,
  `.specify/memory/constitution.md`, `.specify/NOTICE`, blocco `SERTOR:SDLC-RITUAL` in `CLAUDE.md`;
  **assenza** di `.specify/feature.json`; **nessuna** fase SDLC/git/index avviata (install≠run).
  **(F11 — NFR-3 offline)** aggiungi un'asserzione che l'install completa senza rete (es. nessun import
  di `httpx`/`requests`/`urllib` di rete nel percorso, o blocco `socket` nel test).
- [x] T035 [P] [US1] Unit test `tests/unit/test_governance_plan.py`: il piano è derivato dalla
  composizione (aggiungere un asset cambia il piano, FR-005); ordine canonico; `feature.json` mai nel
  piano.
- [x] T036 [P] [US1] Unit test `tests/unit/test_generate.py`: i file init/integration generati hanno lo
  schema atteso (consumabili dalle skill SpecKit) e riflettono il `GovernanceProfile` (assistant/script/
  versione).

**Checkpoint MVP**: US1 completa = il metodo si installa con un comando. Demo-abile da sola.

---

## Phase 4: User Story 2 — Indipendenza dal dominio RAG (Priority: P2)

> Goal: `sertor-flow` si installa senza `sertor-core`. **Independent test**: in un ambiente senza
> `sertor-core`, l'install completa.

- [x] T037 [US2] Unit test `packages/sertor-flow/tests/unit/test_no_core_dependency.py`: nessun import di
  `sertor_core` in `sertor_flow` né in `sertor_install_kit` (scan statico degli import / import isolato);
  asserzione che `sertor-flow`/`sertor-install-kit` non dichiarano `sertor-core` tra le dipendenze.
  **(F5 — NFR-2 guardia positiva)** aggiungi anche l'asserzione che `sertor_flow` **non ridefinisce** i
  moduli del kit (no `sertor_flow/claude_md.py`, `artifacts.py`, `report.py`, `executor.py`, merge, …):
  i primitivi vengono dal kit, non duplicati.
- [x] T038 [US2] Integration test: `execute_governance_plan` completa con successo quando `sertor_core`
  non è importabile (simula assenza del core, es. monkeypatch/blocco import) — SC-004.

**Checkpoint**: la governance è davvero ortogonale al RAG.

---

## Phase 5: User Story 3 — Idempotenza e non-distruttività (Priority: P2)

> Goal: re-install sicuro su repo esistente. **Independent test**: doppia esecuzione + file preesistenti
> → nessuna sovrascrittura, nessun blocco duplicato, seconda run a zero modifiche.

- [x] T039 [US3] Integration test `tests/integration/test_idempotency.py`: seconda esecuzione di
  `sertor-flow install` → tutti gli artefatti `skipped`, zero modifiche (FR-017/SC-005).
- [x] T040 [US3] Integration test non-distruttività: file utente preesistenti (es. un
  `.claude/agents/requirements-analyst.md` modificato) → `skipped`, contenuto invariato; costituzione
  preesistente → `skipped` (FR-014).
- [x] T041 [US3] Integration test coesistenza `CLAUDE.md`: un `CLAUDE.md` che contiene già il blocco
  `SERTOR:WIKI-RITUAL` → l'install aggiunge un blocco `SERTOR:SDLC-RITUAL` **distinto** senza toccare il
  blocco wiki; re-run → blocco SDLC non duplicato (FR-015, DA-b).
- [x] T042 [US3] Integration test fail-fast: un passo che fallisce (es. destinazione non scrivibile) →
  stop, `failed_step` nominato, artefatti precedenti in posto (FR-019).

**Checkpoint**: install ripetibile e sicuro su repo reali.

---

## Phase 6: User Story 4 — Puntatore dall'ombrello (Priority: P3)

> Goal: `sertor install governance` rimanda a `sertor-flow`. **Independent test**: invocare il
> sotto-comando → messaggio-puntatore, nessuna dipendenza tra pacchetti.

- [x] T043 [US4] Modifica `packages/sertor/src/sertor_installer/__main__.py`: il dispatch del
  sotto-comando `governance` emette un **messaggio-puntatore** (la governance è fornita da `sertor-flow`,
  con l'istruzione d'installazione) con exit code dedicato. **(F9)** Realizzalo con un **print esplicito +
  exit code** (NON declassare `CapabilityNotAvailableError` fuori da `SertorError`, che romperebbe il
  catch `except SertorError` in `main()`): o stampi e ritorni il codice direttamente, oppure mantieni una
  sottoclasse di `SertorError` col nuovo messaggio-puntatore. **Nessuna** dipendenza di `sertor` da
  `sertor-flow` (FR-023/SC-008). Aggiorna il test esistente `test_install_governance_*` di conseguenza.
- [x] T044 [US4] Unit test in `packages/sertor/tests/`: `sertor install governance` produce il messaggio
  che nomina `sertor-flow` e come installarlo; verifica statica che `packages/sertor/pyproject.toml` NON
  dichiara `sertor-flow` tra le dipendenze.

---

## Phase 7: Polish & Cross-Cutting

- [x] T045 [P] Guard test anti-drift `packages/sertor-flow/tests/unit/test_assets_sync.py`: gli asset del
  bundle governance corrispondono al sottoinsieme governance del `.claude/`+`.specify/` del repo (NON gli
  asset wiki di `sertor`, NON la costituzione RAG). **(F6)** Lo `sync.py` di `sertor-flow` (usa il `sync`
  del kit) propaga SOLO: da `assets/claude/` → `.claude/` il **sottoinsieme governance** (skill/agenti
  speckit-* + requirements + requirements-analyst + configuration-manager, NON wiki-author/wiki-curator);
  da `assets/specify/` → `.specify/` templates/extensions/workflows. **ESCLUSI dal confronto e dalla
  propagazione:** `assets/scripts/**` di scaffolding (provengono dall'upstream spec-kit, F3, non hanno
  mirror dogfood paritetico), `constitution-starter.md` (≠ la `.specify/memory/constitution.md` RAG di
  Sertor, da NON sovrascrivere) e i `.tmpl` init.
- [x] T046 [P] Verifica attribuzione MIT (SC-007): test che `assets/NOTICE` e `LICENSES/spec-kit-MIT.txt`
  esistono nel pacchetto e che `sertor-flow install` li deposita su `.specify/NOTICE` sull'ospite.
- [x] T047 Aggiorna `docs/install.md` (radice) con una sezione `sertor-flow` (uso, install≠run,
  cross-platform, indipendenza dal core) — coerente con la sezione `install wiki`/`rag`.
- [x] T048 Quickstart smoke manuale (vedi `quickstart.md`): `sertor-flow install --target <tmp>` reale,
  verifica i 5 punti dello smoke; documenta l'esito. **(F7 — SC-006 cross-platform)** gli integration
  test usano `pathlib`/`tmp_path` (platform-agnostic) e l'argparse è cross-platform → SC-006 è coperto
  dai test che girano sia su Windows sia su POSIX; se disponibile una CI matrix Linux/macOS, aggiungere
  l'entry; altrimenti documentare esplicitamente che la portabilità è garantita da stdlib path-handling
  e l'assenza di assunzioni OS nel corpo (gli script ps+bash sono entrambi spediti).
- [x] T049 **Gate finale**: `uv run pytest` (intera suite: root + tutti i membri) verde; `uv run ruff
  check .` pulito.
- [ ] T050 Aggiorna lo stato in `requirements/sertor-cli/epic.md` (FEAT-005 → consegnata) — al merge.

---

## Dipendenze & ordine

- **Setup (T001-T004)** → blocca tutto.
- **Foundational (T005-T021)** → blocca tutte le user story. Il **gate T021** (suite `sertor` verde) è
  il rischio #1: non procedere a US1 finché non passa.
- **US1 (T022-T036)** → MVP. Dipende da Foundational. T027-T033 (asset) sono `[P]` tra loro; T034-T036
  dipendono dal codice US1 (T022-T026) e dagli asset.
- **US2 (T037-T038)** → dipende da US1 (il pacchetto deve esistere); per lo più test.
- **US3 (T039-T042)** → dipende da US1; test di idempotenza/non-distruttività.
- **US4 (T043-T044)** → indipendente da US1/2/3 (tocca solo `packages/sertor`); può andare in parallelo
  dopo Foundational.
- **Polish (T045-T050)** → dopo le storie.

## Esecuzione parallela (esempi)

- Dopo T006: `T007 T008 T009 T010 T011` (primitivi su file diversi) in parallelo, poi T012-T014.
- In US1: `T027 T028 T029 T030 T031 T032 T033` (asset, file diversi) in parallelo.
- `T044` (US4, packages/sertor) può procedere mentre si lavora US1 (packages/sertor-flow).

## MVP

**US1 (Phase 1+2+3)** = MVP: `sertor-flow install` deposita il metodo con un comando, non distruttivo,
install≠run. US2/US3 induriscono (indipendenza, idempotenza); US4 è la comodità del puntatore.
