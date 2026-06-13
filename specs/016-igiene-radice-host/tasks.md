---
description: "Task list — feature 016 igiene radice host"
---

# Tasks: Igiene e collocazione degli artefatti sull'ospite

**Input**: Design documents from `specs/016-igiene-radice-host/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-commands.md, quickstart.md

**Tests**: inclusi — la costituzione (Principio V) impone test F.I.R.S.T. e il quickstart definisce
verifiche per SC-001..006. Tutti i test girano **senza rete** (`FakeCommandRunner`, fixtures host).

**Organization**: per user story (P1 → P2 → P3), ciascuna indipendentemente testabile.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza non risolta)
- **[Story]**: US1 / US2 / US3 (mappa alle user story della spec)

## Path Conventions

- Installer: `packages/sertor/src/sertor_installer/` (+ `tests/`)
- CLI core wiki: `src/sertor_core/wiki_tools/`
- Asset canonici: `packages/sertor/src/sertor_installer/assets/`
- Repo Sertor (dogfood, fix one-shot): `.claude/`, `wiki/wiki.config.toml`, `CLAUDE.md`

---

## Phase 1: Setup

**Purpose**: baseline verde prima di toccare il codice.

- [ ] T001 Stabilire la baseline: `uv run pytest packages/sertor -q` + `uv run pytest tests/unit -q -k wiki_tools` verdi e `uv run ruff check packages src` pulito (nessun nuovo pacchetto introdotto da questa feature).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: doppi di test condivisi da più story.

**⚠️ CRITICAL**: completare prima delle story che li usano.

- [ ] T002 [P] Estendere il doppio `FakeCommandRunner` (in `packages/sertor/tests/conftest.py`) per scriptare la disponibilità di `claude` e gli esiti di `claude mcp get`/`claude mcp add-json` (record delle chiamate, returncode configurabile). Blocca i test US3.
- [ ] T003 [P] Aggiungere un helper di asserzione sul contenuto della radice host (set delle entry top-level di un `tmp_path`) in `packages/sertor/tests/conftest.py`. Blocca i test di collocazione US1/US3.

**Checkpoint**: doppi pronti — le story possono procedere.

---

## Phase 3: User Story 1 - Radice host minima e prevedibile (Priority: P1) 🎯 MVP

**Goal**: un install su un ospite pulito colloca `wiki.config.toml` in `wiki/`, il runtime RAG solo in `.sertor/`, e nessun file di tooling sparso in radice.

**Independent Test**: dopo `install wiki` + `install rag --no-deps` su un `tmp_path`, la radice contiene solo `.claude/`, `CLAUDE.md`, `wiki/`, `.gitignore`, `.mcp.json`, `.sertor/`; `wiki.config.toml` è in `wiki/`, non in radice.

### Implementation for User Story 1

- [ ] T004 [US1] In `packages/sertor/src/sertor_installer/install_wiki.py`: cambiare `_CONFIG_TARGET` da `"wiki.config.toml"` a `"wiki/wiki.config.toml"`; in `_apply_config` aggiungere `dest.parent.mkdir(parents=True, exist_ok=True)` prima della scrittura (copre FR-002 lato collocazione).
- [ ] T005 [US1] In `install_wiki._apply_structure`: chiamare `load_profile(config_path, root_override=target_root)` così la tassonomia si crea sotto `<host>/wiki` con la config in `wiki/` (verifica: `root="wiki"` del template invariato).
- [ ] T006 [P] [US1] Test in `packages/sertor/tests/test_install_wiki.py`: `install wiki` scrive `wiki/wiki.config.toml` (non in radice), `load_profile` del file generato è valido, la struttura è creata sotto `<host>/wiki`; re-run → `wiki/wiki.config.toml` `skipped` (idempotenza).
- [ ] T007 [P] [US1] Test-guardia REQ-301 in `packages/sertor/tests/test_install_rag.py`: nessun `Artifact` del piano RAG ha `target_rel` in radice oltre `.mcp.json` e `.gitignore` (tutto il resto sotto `.sertor/`).
- [ ] T008 [P] [US1] Test REQ-306 (collocazione end-to-end) in `packages/sertor/tests/test_install_wiki.py` (o nuovo `test_root_hygiene.py`): dopo `install wiki` + piano RAG `--no-deps` con scope project, il set delle entry di radice è esattamente `{.claude, CLAUDE.md, wiki, .gitignore, .mcp.json, .sertor}` (usa l'helper T003).

**Checkpoint**: nuovo install → radice pulita e prevedibile (MVP consegnabile).

---

## Phase 4: User Story 2 - Wiki autocontenuto e invocazioni sempre funzionanti (Priority: P2)

**Goal**: con la config in `wiki/`, gli strumenti la trovano (auto-discovery + convenzione esplicita), tutti gli asset puntano alla nuova sede, e Sertor stesso è riallineato one-shot.

**Independent Test**: da una radice host con `wiki/wiki.config.toml`, `sertor-wiki-tools scan --json` (senza flag) risolve i path dalla radice; nessun asset installato referenzia il vecchio path; i test di sync di Sertor sono verdi.

### Implementation for User Story 2

- [ ] T009 [US2] Auto-discovery del `--config` in `src/sertor_core/wiki_tools/__main__.py`: se `--config` assente cerca `./wiki.config.toml` poi `./wiki/wiki.config.toml`; se trovata sotto `wiki/` e `--root` assente imposta `root_override=CWD`; nessuna trovata → `ConfigError` (Principio IV). `--config`/`--root` espliciti hanno precedenza (copre FR-002/FR-003, SC-002).
- [ ] T010 [P] [US2] Test auto-discovery (suite wiki_tools, es. `tests/unit/test_wiki_tools_cli.py`): config in radice → usata; solo in `wiki/` → usata con root=CWD; entrambe assenti → `ConfigError`; `--config` esplicito bypassa la ricerca; `--root` esplicito vince sull'auto-impostazione.
- [ ] T011 [P] [US2] Aggiornare l'hook eseguibile `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.ps1`: `$config = Join-Path $root 'wiki/wiki.config.toml'` e invocazione `scan --config $config` coerente.
- [ ] T012 [P] [US2] Aggiornare prosa ed esempi di invocazione negli asset `packages/sertor/src/sertor_installer/assets/claude/**` (SKILL.md, wiki-playbook.md, ops/*.md, commands/wiki.md, agents/wiki-curator.md, page-craft.md, wiki-craft.md, log-craft.md) e `assets/claude-md-block.md` alla nuova sede/convenzione (`--config wiki/wiki.config.toml --root .`, "config in `wiki/`").
- [ ] T013 [P] [US2] Aggiornare i commenti di `packages/sertor/src/sertor_installer/assets/wiki.config.toml.tmpl` (valore `root="wiki"` INVARIATO; annotare che il file vive in `wiki/`).
- [ ] T014 [US2] Fix one-shot del repo Sertor: `git mv wiki.config.toml wiki/wiki.config.toml`; ri-sincronizzare `.claude/` dagli asset aggiornati; aggiornare `CLAUDE.md` di radice (esempi `append-log`, blocco rituale) e gli esempi del playbook in `.claude/skills/wiki-author/`. (Dipende da T004, T009, T011, T012, T013.)
- [ ] T015 [US2] Aggiornare/verificare la guardia di sync `packages/sertor/tests/test_host_agnostic.py`: `.claude/` di Sertor combacia con gli asset dopo il riallineamento (FR-007/FR-008).
- [ ] T016 [P] [US2] Test-guardia REQ-303 in `packages/sertor/tests/` (nuovo `test_no_legacy_config_path.py`): nessun asset sotto `assets/claude/**` né `.claude/**` referenzia il vecchio path radice (`wiki.config.toml` senza prefisso `wiki/`) in un'invocazione `--config` o nel hook.

**Checkpoint**: tooling pienamente funzionante con config in `wiki/`; Sertor verde.

---

## Phase 5: User Story 3 - Scelta dello scope di registrazione MCP (Priority: P3)

**Goal**: `install rag --mcp-scope project|local`; local registra via `claude` CLI senza file nel repo, con fail-fast.

**Independent Test**: `install rag --mcp-scope local --no-deps` (con `FakeCommandRunner` che simula `claude`) non crea `.mcp.json` e registra il server; con `claude` assente fallisce con messaggio leggibile e nessun file.

### Implementation for User Story 3

- [ ] T017 [P] [US3] In `packages/sertor/src/sertor_installer/artifacts.py`: aggiungere `ArtifactKind.MCP_REGISTER` e `WriteStrategy.REGISTER_CLI` (data-model §1).
- [ ] T018 [P] [US3] In `packages/sertor/src/sertor_installer/rag_profile.py`: aggiungere `RagInstallOptions.mcp_scope: str = "project"` con validazione `{"project","local"}` → `ConfigError` (data-model §2).
- [ ] T019 [US3] In `packages/sertor/src/sertor_installer/install_rag.py`: aggiungere `McpRegistrationError(SertorError)`; `_apply_mcp_register(profile, runner)` (idempotente: `claude mcp get` → presente=SKIPPED, assente=`claude mcp add-json … --scope local`=CREATED; `is_available("claude")` falso o add fallito → `McpRegistrationError` + comando manuale; emette `log_event`); `build_rag_plan(profile, with_deps, mcp_scope)` seleziona `MCP_REGISTER` vs `MCP_MERGE`; `execute_rag_plan` gestisce il nuovo kind. (Dipende da T017, T018.)
- [ ] T020 [US3] In `packages/sertor/src/sertor_installer/__main__.py`: aggiungere `--mcp-scope {project,local}` (default `project`) a `install rag`; propagare a `RagInstallOptions`/`build_rag_plan`. (Dipende da T019.)
- [ ] T021 [P] [US3] Test in `packages/sertor/tests/test_install_rag.py` (+ eventuale `test_mcp_register.py`): scope project invariato; scope local registra via `FakeCommandRunner` e NON crea `.mcp.json`; `claude` assente → `McpRegistrationError`, nessun file (SC-005); re-run con server presente → `skipped` (idempotenza); `--mcp-scope` invalido → `ConfigError`/exit 2.

**Checkpoint**: le tre story indipendentemente funzionanti.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T022 [P] `docs/install.md`: sezione "Cosa resta in radice host e perché" (residenti inevitabili + `.sertor/` + `.mcp.json` solo scope project) e documentazione di `--mcp-scope` (REQ-306, mossa #4).
- [ ] T023 Suite completa verde: `uv run pytest -m "not cloud"` (root + packages) + `uv run ruff check packages src`.
- [ ] T024 Validazione quickstart.md; annotare l'esito **live** della mappatura flag `local` → `--scope local` di Claude Code (come la validazione uvx della 015; differibile a post-merge).
- [ ] T025 Re-index del corpus `sertor` dopo le modifiche ad asset/`.claude/`/`docs`/`CLAUDE.md` (regola standing; obbligata dopo il merge su master).

---

## Dependencies & Execution Order

- **Setup (T001)** → **Foundational (T002, T003)** → User Stories.
- **US1 (T004–T008)**: indipendente; MVP. T004 prima di T005/T006/T008.
- **US2 (T009–T016)**: T009 prima di T010/T014; T011/T012/T013 prima di T014; T014 prima di T015; T016 dopo T011/T012. US2 dipende concettualmente da T004 (collocazione) per il fix one-shot coerente.
- **US3 (T017–T021)**: T017+T018 → T019 → T020; T021 dopo T019/T020.
- **Polish (T022–T025)**: dopo le story desiderate; T025 obbligata dopo merge.

### Parallel Opportunities

- Foundational: T002 ∥ T003.
- US1: T006 ∥ T007 ∥ T008 (file/asserzioni diverse) dopo T004/T005.
- US2: T011 ∥ T012 ∥ T013 (asset diversi); T010 ∥ con gli asset; poi T014 sequenziale.
- US3: T017 ∥ T018; T021 in coda.
- US1, US2, US3 sono lavorabili in parallelo dopo il Foundational (con cautela su T014 che tocca asset toccati anche da US2).

---

## Implementation Strategy

- **MVP** = US1 (Setup + Foundational + Phase 3): nuovo install → radice pulita. Stop & validate.
- **Incrementale**: +US2 (tooling usabile con config in `wiki/` + Sertor allineato) → +US3 (scope MCP).
- **Coverage FR**: FR-001→T007 · FR-002→T004/T005/T009 · FR-003→T011/T012/T016 · FR-004→T017–T020 · FR-005→T019/T021 · FR-006→T008/T022 · FR-007→T015 · FR-008→T014/T015.

## Notes

- Test senza rete (Principio V): `FakeCommandRunner` per `claude`, fixtures `tmp_path` per la radice.
- Idempotenza verificata per config, struttura, merge `.mcp.json` e registrazione local.
- Il fix di Sertor è **one-shot**: nessun comando di migrazione per ospiti esterni (D4).
- Commit dopo ogni story o gruppo logico; il re-index (T025) è obbligato dopo il merge su master.
