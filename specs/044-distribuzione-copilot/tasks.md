---

description: "Task list — FEAT-007 Distribuzione su GitHub Copilot (pacchetto sertor)"
---

# Tasks: Distribuzione su GitHub Copilot (parità di assistente) — pacchetto `sertor`

**Input**: Design documents from `specs/044-distribuzione-copilot/`

**Prerequisites**: plan.md, spec.md, research.md (DA-2=ibrido), data-model.md, contracts/

**Tests**: INCLUSI (richiesti). Pattern host in `tmp_path` come `test_install_wiki.py`/`test_install_rag.py`.

**Organization**: per user story (P1→P3). Ambito SOLO pacchetto `sertor` (wiki+rag); governance
`sertor-flow` = FEAT-009, fuori taglio.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza incompleta)
- **[Story]**: US1/US2/US3 (solo nelle fasi delle storie)

## Path Conventions

- Kit: `packages/sertor-install-kit/src/sertor_install_kit/`, test `packages/sertor-install-kit/tests/`
- Installer: `packages/sertor/src/sertor_installer/`, asset `…/assets/`, test `packages/sertor/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: predisporre lo scaffolding degli asset Copilot.

- [X] T001 [P] Crea le cartelle asset Copilot vuote (con `.gitkeep`) `packages/sertor/src/sertor_installer/assets/copilot/{prompts,agents,hooks,instructions}/`
- [X] T002 [P] Verifica baseline verde prima di iniziare: `uv run pytest packages/sertor-install-kit packages/sertor -q` e `uv run ruff check packages/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: il meccanismo di targeting per-assistente — prerequisito condiviso da TUTTE le storie (e da FEAT-009).

**⚠️ CRITICAL**: nessuna storia può iniziare prima del completamento di questa fase.

- [X] T003 [P] Test del profilo assistente in `packages/sertor-install-kit/tests/unit/test_assistant.py`: `AssistantId` (claude/copilot, valore ignoto → `ConfigError`), default documentato = `claude`, e la risoluzione `AssistantProfile.target_for(Surface)` per i due assistenti (mappa di data-model §3). Deve FALLIRE prima di T004/T005.
- [X] T004 Implementa `AssistantId` (enum) e `Surface` (enum) in `packages/sertor-install-kit/src/sertor_install_kit/assistant.py` (data-model §1, §2)
- [X] T005 Implementa `AssistantProfile` in `packages/sertor-install-kit/src/sertor_install_kit/assistant.py`: mappa `Surface → (target_rel, WriteStrategy/contenitore)` per `claude` e `copilot` (data-model §3); `target_rel` validati relativi
- [X] T006 [P] Test estensione `merge_mcp` in `packages/sertor-install-kit/tests/unit/test_mcp_merge.py`: root-key parametrico (`mcpServers` default ↔ `servers`) + target parametrico, additivo/idempotente, retrocompatibile col comportamento attuale. Deve FALLIRE prima di T007.
- [X] T007 Estendi `merge_mcp` in `packages/sertor-install-kit/src/sertor_install_kit/mcp_merge.py` con parametro `root_key` (default `mcpServers` → retrocompat) (data-model §4)
- [X] T008 Rendi `build_install_plan(assistant: AssistantId)` e `build_rag_plan(assistant: AssistantId, …)` parametrici in `packages/sertor/src/sertor_installer/install_wiki.py` e `install_rag.py`: i target dei plan vengono chiesti all'`AssistantProfile`, non più cablati (`.claude/...`); `claude` resta il comportamento attuale (non-regressione)
- [X] T009 Aggiungi l'opzione `--assistant claude|copilot` (default `claude`, validazione → `ConfigError` azionabile) in `packages/sertor/src/sertor_installer/__main__.py`, propagata a `install wiki`/`install rag` (FR-001/002; contracts/cli-assistant.md)
- [X] T010 Aggiungi l'`assistant` target all'`InstallReport` (campo informativo, Principio IX) in `packages/sertor/src/sertor_installer/report.py`

**Checkpoint**: targeting pronto; `--assistant claude` non regredisce (tutta la suite esistente verde).

---

## Phase 3: User Story 1 - RAG (MCP) raggiungibile da Copilot (Priority: P1) 🎯 MVP

**Goal**: `sertor install rag --assistant copilot` registra `sertor-rag` in `.vscode/mcp.json` (chiave `servers`), usabile dal client Copilot senza editing manuale.

**Independent Test**: su host pulito, `install rag --assistant copilot` → `.vscode/mcp.json` contiene il server; parte non segreta completa; nessuna ingestione; ri-run idempotente.

### Tests for User Story 1 ⚠️

- [X] T011 [P] [US1] Test in `packages/sertor/tests/test_install_rag_copilot.py`: MCP in `.vscode/mcp.json` (`servers.sertor-rag`), segreti vuoti (FR-006), install≠run (FR-018), idempotenza (FR-020), non distruttività su `.vscode/mcp.json` preesistente (FR-017). Deve FALLIRE prima di T012/T013.

### Implementation for User Story 1

- [X] T012 [US1] In `build_rag_plan(copilot)` instrada `MCP_SERVER` su `.vscode/mcp.json` via `AssistantProfile`; `_apply_mcp` usa `merge_mcp(..., root_key="servers")` sul target del profilo in `packages/sertor/src/sertor_installer/install_rag.py` (FR-004/005)
- [X] T013 [US1] Gestisci `GITIGNORE_APPEND`/`ENV_MERGE`/`DEPENDENCIES` invariati per copilot (riuso) e verifica che `.vscode/mcp.json` sia coperto da `.gitignore` solo se appropriato (non lo è: va committato) in `install_rag.py`
- [X] T014 [US1] Documenta in `packages/sertor/docs/install.md` la verifica MCP lato Copilot (FR-007; quickstart §3)

**Checkpoint**: MVP — un utente Copilot ha il RAG raggiungibile.

---

## Phase 4: User Story 2 - Rituale e comandi del wiki su Copilot (Priority: P2)

**Goal**: blocco istruzioni/rituale in `.github/copilot-instructions.md` + comandi wiki in `.github/prompts/*.prompt.md`; idem blocco RAG-usage per `install rag`.

**Independent Test**: `install wiki --assistant copilot` → blocco a marker in `.github/copilot-instructions.md`; `wiki.prompt.md` presente e ben formato; ri-run idempotente; contenuto condiviso non divergente.

### Tests for User Story 2 ⚠️

- [X] T015 [P] [US2] Test in `packages/sertor/tests/test_install_wiki_copilot.py`: `INSTRUCTION_BLOCK` a marker in `.github/copilot-instructions.md` (idempotente, FR-008/009), presenza/forma dei prompt-file (FR-010). Deve FALLIRE prima dell'implementazione.
- [X] T016 [P] [US2] Test guardia anti-drift in `packages/sertor/tests/test_assets_copilot_guard.py`: il testo del blocco istruzioni e il corpo del comando resi per copilot derivano dalla STESSA fonte di claude (REQ-021; contracts/surface-mapping.md prop.2). Deve FALLIRE prima dell'implementazione.

### Implementation for User Story 2

- [X] T017 [US2] `INSTRUCTION_BLOCK` per copilot: in `build_install_plan(copilot)` e `build_rag_plan(copilot)` instrada il `MARKER_BLOCK` su `.github/copilot-instructions.md` (riuso `write_marker_block`, stessi marker/contenuto) in `install_wiki.py`/`install_rag.py` (FR-008/009)
- [X] T018 [US2] Renderer prompt-file in `packages/sertor/src/sertor_installer/surfaces.py`: genera `.github/prompts/*.prompt.md` dal contenuto condiviso del comando/skill wiki (frontmatter prompt-file); fonte unica + guardia (REQ-021)
- [X] T019 [US2] In `build_install_plan(copilot)` emetti i `COMMAND` come FILE resi verso `.github/prompts/` (al posto di `.claude/commands`+`.claude/skills`) in `install_wiki.py` (FR-010)
- [X] T020 [US2] Asset/reso Copilot del comando `/wiki` e della skill `wiki-author` sotto `packages/sertor/src/sertor_installer/assets/copilot/prompts/`

**Checkpoint**: US1 + US2 funzionanti indipendentemente.

---

## Phase 5: User Story 3 - Automatismi (agente e hook) del wiki su Copilot (Priority: P3)

**Goal**: custom-agent `wiki-curator` in `.github/agents/`; hook wiki (SessionStart/Stop) e anti-bypass XI (PreToolUse) in `.github/hooks/*.json`, con script riusati identici.

**Independent Test**: `install wiki/rag --assistant copilot` → custom-agent presente; `.github/hooks/*.json` validi con gli eventi attesi; script byte-identici a quelli Claude; anti-bypass non bloccante/fail-open.

### Tests for User Story 3 ⚠️

- [X] T021 [P] [US3] Test in `packages/sertor/tests/test_install_wiki_copilot.py` (estende): custom-agent `.github/agents/wiki-curator.agent.md` presente/ben formato (FR-011); hook `.github/hooks/*.json` con eventi `SessionStart`/`Stop` (FR-012). Deve FALLIRE prima dell'implementazione.
- [X] T022 [P] [US3] Test in `packages/sertor/tests/test_install_rag_copilot.py` (estende): hook anti-bypass `PreToolUse` in `.github/hooks/*.json`, non bloccante/fail-open (FR-013); script `.ps1` byte-identico tra claude e copilot (contracts/surface-mapping.md prop.3). Deve FALLIRE prima dell'implementazione.

### Implementation for User Story 3

- [X] T023 [US3] `AGENT` per copilot: renderer custom-agent in `surfaces.py` (`.github/agents/*.agent.md`, frontmatter `tools`/`model`) + asset/reso sotto `assets/copilot/agents/`; instradato in `build_install_plan(copilot)` (FR-011)
- [X] T024 [US3] `HOOK` per copilot: in `build_install_plan`/`build_rag_plan(copilot)` instrada lo `SETTINGS_MERGE` sul file `.github/hooks/sertor-*.json` (wiring eventi) e copia lo script come FILE RIUSATO identico in `install_wiki.py`/`install_rag.py` (FR-012/013/014)
- [X] T025 [US3] Asset wiring hook Copilot sotto `assets/copilot/hooks/` (frammento JSON eventi→script); riusa gli script `wiki-pending-check.ps1`/`sertor-rag-usage-check.ps1` esistenti senza duplicarli

**Checkpoint**: parità piena raggiunta su tutte le superfici del pacchetto `sertor`.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T026 [P] Test di parità superfici in `packages/sertor/tests/test_surface_parity.py`: per `capability ∈ {wiki, rag}`, copertura copilot ⊇ claude o gap dichiarato (SC-002; contracts/surface-mapping.md prop.1) + coesistenza claude+copilot senza doppio blocco (prop.5, edge case)
- [X] T027 [P] Aggiorna `packages/sertor/docs/install.md` con la sezione `--assistant` (claude/copilot, default) e la mappatura superfici
- [X] T028 Verifica gap dichiarati nel report (FR-015/016): nessuna superficie omessa in silenzio — asserzione nel report d'installazione
- [X] T029 `uv run ruff check packages/` pulito + suite intera verde (`uv run pytest packages/sertor-install-kit packages/sertor -q`)
- [X] T030 Esegui la validazione di `specs/044-distribuzione-copilot/quickstart.md` (manuale/scriptata su host `tmp`)

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: nessuna dipendenza.
- **Foundational (Phase 2)**: dopo Setup — **BLOCCA** tutte le storie (T003–T010).
- **US1 (Phase 3)**: dopo Foundational. MVP.
- **US2 (Phase 4)**: dopo Foundational; indipendente da US1.
- **US3 (Phase 5)**: dopo Foundational; indipendente (può integrare US1/US2 ma testabile da sola).
- **Polish (Phase 6)**: dopo le storie desiderate.

### Within each story
- Test PRIMA dell'implementazione (devono fallire), poi implementazione.
- Foundational: T004/T005 dopo T003; T007 dopo T006; T008 dopo T004/T005/T007; T009/T010 dopo T008.

### Parallel Opportunities
- T001/T002 in parallelo.
- T003/T006 (test foundational) in parallelo; T011/T015/T016/T021/T022 (test di storia) in parallelo tra storie diverse.
- Le tre storie, completata la Foundational, sono lavorabili in parallelo.

---

## Implementation Strategy

### MVP First (US1)
1. Phase 1 Setup → 2. Phase 2 Foundational (CRITICA) → 3. Phase 3 US1 (MCP su Copilot) → **STOP & VALIDATE** → demo MVP.

### Incremental
US1 (MCP) → US2 (rituale+comandi) → US3 (agente+hook) → Polish (parità+docs). Ogni storia aggiunge valore senza rompere le precedenti; `--assistant claude` non regredisce mai.

---

## Notes
- [P] = file diversi, nessuna dipendenza. [Story] = tracciabilità.
- Commit dopo ogni task o gruppo logico (delega al `configuration-manager`).
- Invarianti sempre verdi: install≠run, non distruttivo, idempotente, CLI assistant-agnostic, segreti non versionati, gap dichiarati.
- Anti-drift: asset Copilot = fonte canonica + guardia (mai seconda copia libera).
