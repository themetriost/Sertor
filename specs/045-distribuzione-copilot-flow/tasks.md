---

description: "Task list — FEAT-009 Distribuzione governance/SDLC su GitHub Copilot (sertor-flow)"
---

# Tasks: Distribuzione governance/SDLC su GitHub Copilot (`sertor-flow`)

**Input**: Design documents from `specs/045-distribuzione-copilot-flow/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUSI (richiesti). Pattern host in `tmp_path`; il lancio di `specify` è **mockato** via
`CommandRunner` (nessuna rete).

**Organization**: per user story (P1→P2). Ambito SOLO `sertor-flow` + spostamento renderer nel kit;
NON toccare `sertor-core`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza incompleta)
- **[Story]**: US1/US2 (solo nelle fasi delle storie)

## Path Conventions

- Kit: `packages/sertor-install-kit/src/sertor_install_kit/`, test `…/tests/`
- Flow: `packages/sertor-flow/src/sertor_flow/`, asset `…/assets/`, test `packages/sertor-flow/tests/`
- Sertor (solo aggiornamento import): `packages/sertor/src/sertor_installer/`

---

## Phase 1: Setup

- [ ] T001 [P] Verifica baseline verde: `uv run pytest packages/sertor-install-kit packages/sertor packages/sertor-flow -q` (per-package) e `uv run ruff check packages/`
- [ ] T002 [P] Inventaria gli asset SpecKit vendorati da rimuovere: elenca `packages/sertor-flow/src/sertor_flow/assets/claude/skills/speckit-*`, `…/claude/agents/speckit-*`, `…/specify/**`, `NOTICE`, `LICENSES/spec-kit-MIT.txt` (input per US1) e distingui i Sertor-authored da MANTENERE (`requirements-analyst`, `configuration-manager`, skill `requirements`, `constitution-starter.md`, `claude-md-block-sdlc.md`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: prerequisiti condivisi; nessuna storia inizia prima.

- [ ] T003 Sposta il renderer `surfaces.py` da `packages/sertor/src/sertor_installer/surfaces.py` a `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py` (reso prompt-file/custom-agent da fonte unica); esportalo da `sertor_install_kit/__init__.py`
- [ ] T004 Aggiorna `packages/sertor/src/sertor_installer/` per reimportare il renderer dal kit (shim o import diretto), **senza cambiare comportamento** (non-regressione FEAT-007)
- [ ] T005 [P] Verifica non-regressione FEAT-007: `uv run pytest packages/sertor -q` resta verde dopo lo spostamento del renderer
- [ ] T006 Estendi `GovernanceProfile` in `packages/sertor-flow/src/sertor_flow/profile.py`: `assistant` guida targeting+launch; aggiungi la **versione spec-kit pinnata** (config, non hardcoded sparso — Principio VIII)
- [ ] T007 [P] Test del profilo in `packages/sertor-flow/tests/unit/test_profile.py`: default assistant documentato, versione spec-kit presente, valore assistant ignoto → errore

**Checkpoint**: renderer condiviso nel kit; profilo pronto; FEAT-007 non regredita.

---

## Phase 3: User Story 1 - SpecKit via launch-installer (Priority: P1) 🎯 MVP

**Goal**: `sertor-flow install --assistant <claude|copilot>` ottiene SpecKit **lanciando** `specify init
--ai <assistant>` (non più vendorato), per entrambi gli assistenti; Claude resta equivalente a oggi.

**Independent Test**: install con `specify` mockato → comandi/agenti SpecKit + `.specify/` presenti per
l'assistente; spec-kit assente → fail-fast; bundle non contiene più asset SpecKit vendorati.

### Tests for User Story 1 ⚠️

- [ ] T008 [P] [US1] Test in `packages/sertor-flow/tests/test_speckit_launch.py` (CommandRunner mockato): `--ai claude`/`--ai copilot` invocati col `--script` giusto; layout verificato → `created`; assente/comando fallito/layout mancante → `InstallerError` fail-fast; già presente → `skipped` (contracts/speckit-launch.md). Deve FALLIRE prima dell'implementazione.
- [ ] T009 [P] [US1] Test non-regressione Claude in `packages/sertor-flow/tests/integration/test_install_governance.py` (estende): con `specify` mockato che emette il layout Claude, l'install `--assistant claude` produce governance funzionalmente equivalente a oggi (FR-012/SC-003). Deve FALLIRE prima del refactor.
- [ ] T010 [P] [US1] Test guardia in `packages/sertor-flow/tests/unit/test_no_vendored_speckit.py`: il bundle `assets/` NON contiene più `claude/skills/speckit-*`, `claude/agents/speckit-*`, `specify/**` (SC: no-vendored). Deve FALLIRE prima della rimozione.

### Implementation for User Story 1

- [ ] T011 [US1] Crea `packages/sertor-flow/src/sertor_flow/speckit_launch.py`: funzione che lancia `specify init --ai <assistant> --script <ps|sh>` (versione pinnata) via il `CommandRunner` del kit, verifica il layout prodotto, fail-fast su assente/fallito/layout inatteso (contracts/speckit-launch.md, FR-003/004)
- [ ] T012 [US1] Refactor `build_governance_plan`/`execute_governance_plan` in `packages/sertor-flow/src/sertor_flow/install_governance.py`: sostituisci l'enumerazione vendorata di `assets/claude/skills/speckit-*`+`assets/specify/**` con lo **step di launch** (per entrambi gli assistenti); mantieni l'ordine canonico e gli altri step
- [ ] T013 [US1] Rimuovi fisicamente dal bundle gli asset SpecKit vendorati: `packages/sertor-flow/src/sertor_flow/assets/claude/skills/speckit-*`, `…/claude/agents/speckit-*`, `…/specify/**`, e `NOTICE`/`LICENSES/spec-kit-MIT.txt` se non più pertinenti (attribuzione ora dall'output di `specify`)
- [ ] T014 [US1] Emetti `log_event` per il launch (assistant, versione, esito) in `speckit_launch.py` (Principio IX)

**Checkpoint**: MVP — SpecKit ottenuto via launch per Claude (non-regressione) e Copilot.

---

## Phase 4: User Story 2 - Superfici Sertor-authored su Copilot (Priority: P2)

**Goal**: agenti `requirements-analyst`/`configuration-manager`, skill `requirements` e blocco rituale
SDLC resi per Copilot via `AssistantProfile`; costituzione assistant-agnostic.

**Independent Test**: install `--assistant copilot` → custom-agent in `.github/agents/`, skill in
`.github/prompts/`, blocco SDLC in `.github/copilot-instructions.md`; costituzione identica.

### Tests for User Story 2 ⚠️

- [ ] T015 [P] [US2] Test in `packages/sertor-flow/tests/test_install_governance_copilot.py`: agenti Sertor-authored → `.github/agents/*.agent.md`, skill `requirements` → `.github/prompts/`, blocco SDLC → `.github/copilot-instructions.md` (marker, idempotente), costituzione identica (FR-007/008/009). Deve FALLIRE prima dell'implementazione.

### Implementation for User Story 2

- [ ] T016 [US2] In `build_governance_plan(copilot)` instrada le superfici Sertor-authored (AGENT/COMMAND) via `AssistantProfile` + renderer del kit, e il blocco SDLC (INSTRUCTION_BLOCK) su `.github/copilot-instructions.md` in `packages/sertor-flow/src/sertor_flow/install_governance.py` (FR-007/008)
- [ ] T017 [US2] Mantieni la costituzione-starter assistant-agnostic (target invariato per ogni assistente) in `install_governance.py` (FR-009)
- [ ] T018 [US2] Verifica che gli asset Sertor-authored resi per Copilot derivino dalla fonte unica (riuso renderer, no seconda copia) — guardia anti-drift

**Checkpoint**: parità governance piena su Copilot.

---

## Phase 5: Polish & Cross-Cutting

- [ ] T019 [P] Test parità governance in `packages/sertor-flow/tests/test_governance_parity.py`: copertura copilot ⊇ claude o gap dichiarato (SC-002; contracts/governance-parity.md) + coesistenza claude+copilot
- [ ] T020 [P] Guardia `test_no_core_dependency` resta verde: nessun import di `sertor_core` in `sertor-flow` (FR-016/SC-006)
- [ ] T021 [US? polish] Aggiungi/propaga l'opzione `--assistant claude|copilot` (default `claude`) nel CLI `packages/sertor-flow/src/sertor_flow/__main__.py` (contracts/cli-assistant.md, FR-001/002)
- [ ] T022 [P] Aggiorna la doc di `sertor-flow` (README/docs) con `--assistant`, il pivot launch-installer e la dipendenza install-time da spec-kit (deroga II dichiarata)
- [ ] T023 Verifica gap dichiarati nel report (FR-011): nessuna superficie omessa in silenzio
- [ ] T024 `uv run ruff check packages/` pulito + suite per-package verde (`pytest packages/sertor-install-kit`, `packages/sertor`, `packages/sertor-flow`)
- [ ] T025 Esegui la validazione di `specs/045-distribuzione-copilot-flow/quickstart.md` (host `tmp`, `specify` mockato)

---

## Dependencies & Execution Order

- **Setup (Ph1)**: nessuna dipendenza.
- **Foundational (Ph2)**: dopo Setup — BLOCCA le storie (T003 sposta il renderer; T004/T005 non-regressione; T006/T007 profilo).
- **US1 (Ph3)**: dopo Foundational. MVP. T011→T012→T013; test T008/T009/T010 prima.
- **US2 (Ph4)**: dopo Foundational; indipendente da US1 (può integrare ma testabile da sola).
- **Polish (Ph5)**: dopo le storie.

### Parallel Opportunities
- T001/T002; T008/T009/T010 (test US1) tra loro; T019/T020/T022 in polish.
- US1 e US2 lavorabili in parallelo dopo la Foundational.

---

## Implementation Strategy

### MVP First (US1)
Setup → Foundational (renderer nel kit + profilo) → US1 (launch-installer + refactor + non-regressione Claude) → **STOP & VALIDATE** (Claude equivalente, Copilot SpecKit presente, no vendored).

### Incremental
US1 (SpecKit via launch) → US2 (Sertor-authored su Copilot) → Polish (parità, guardie, CLI, docs). Non-regressione Claude verde a ogni passo.

---

## Notes
- [P] = file diversi. [Story] = tracciabilità.
- Commit dopo ogni task/gruppo (delega al `configuration-manager`).
- Invarianti sempre verdi: install≠run, non distruttivo, idempotente, **no sertor-flow→sertor-core**, fail-fast spec-kit assente, gap dichiarati, non-regressione Claude.
- Il lancio di `specify` è SEMPRE mockato nei test (niente rete).
