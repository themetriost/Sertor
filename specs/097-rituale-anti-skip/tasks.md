# Tasks: Rituale wiki anti-skip (scoperta deterministica + dichiarazione forzata)

**Feature**: 097-rituale-anti-skip (E10-FEAT-026, MVP parte 1+3) | **Branch**: `097-rituale-anti-skip`
**Input**: [spec.md](spec.md) · [plan.md](plan.md) · [research.md](research.md) · [data-model.md](data-model.md) · [contracts/ritual-check.md](contracts/ritual-check.md) · [quickstart.md](quickstart.md)

> **Confine D↔N:** il tool `ritual-check` **trova** (deterministico, zero-LLM, sola lettura); l'agente
> **giudica**. `sertor-core` engine di retrieval **INVARIATO**. Tutti i comandi/asset host-facing con parità
> Claude/Copilot + guardia sync.

## Phase 1: Setup (contratto + scaffold modulo)

- [ ] T001 Aggiungere a `src/sertor_core/wiki_tools/contracts.py` le dataclass `RitualCheckResult`,
  `DistillCandidate`, `DriftCandidate` (`wiki.ritual_check/1`, campi da `data-model.md`) + serializzazione
  `--json` coerente con gli altri contratti.
- [ ] T002 Creare `src/sertor_core/wiki_tools/ritual_check.py` con lo scheletro della funzione pura
  `ritual_check(profile, *, base, pages)` che ritorna `RitualCheckResult` e logga `log_event("ritual_check", …)`.

## Phase 2: Foundational — scope + link-graph (bloccante per US1/US3)

- [ ] T003 Determinazione dello scope dello step in `ritual_check.py`: `git diff --name-only <base>...HEAD`
  (default base = merge-base con `master`) filtrato ai `source_dirs` del profilo; override `--pages`; **fail-loud**
  (`ConfigError` azionabile) se non-git e senza `--pages` (REQ-006). `subprocess` stdlib, offline.
- [ ] T004 Estrarre/riusare da `lint.py` un helper del **backlink-graph** (link fra pagine) utilizzabile su una
  versione arbitraria; calcolare i **backlink nuovi** (HEAD ∖ base) per le pagine in scope (git show del blob base).

## Phase 3: User Story 1 — scoperta distill deterministica (P1) 🎯 MVP

**Goal:** `ritual-check` elenca i candidati a distillazione senza dipendere dalla memoria dell'agente.

**Independent Test:** fixture positiva (≥2 pagine changed, ≥2 nuovi backlink incrociati, 0 nuove
`concepts/`/`tech/`) → candidato; fixture negativa → 0 candidati.

- [ ] T005 [US1] Implementare l'**euristica distill** in `ritual_check.py`: gruppi di ≥2 pagine changed che
  condividono ≥2 backlink incrociati **nuovi** e nessuna delle changed è una **nuova pagina** sotto
  `concepts/`/`tech/` (tassonomia dal profilo) → `DistillCandidate` con `reason`.
- [ ] T006 [P] [US1] Test `tests/unit/test_ritual_check.py`: euristica distill **positivo** e **negativo**
  (0 candidati spuri); verifica **sola lettura** (nessuna pagina modificata) e **zero-LLM/import provider**.

## Phase 4: User Story 3 — candidati a drift (P2)

**Goal:** il tool elenca pagine con segnale strutturale di drift, da far giudicare col lint.

**Independent Test:** dato ogni segnale strutturale, la pagina compare come `drift_candidate`; nessun verdetto semantico.

- [ ] T007 [US3] Segnali drift **host-agnostici** in `ritual_check.py`: `stale-updated` (frontmatter `updated:` <
  data modifica git della pagina, via `frontmatter` + git) e `neighbor-of-change` (pagine linkate dalle changed
  ma non changed, via link-graph).
- [ ] T008 [US3] Segnale **`capability-exec` config-driven**: se `wiki.config.toml` ha `[ritual].capability_globs`
  + `exec_page`, e il diff tocca i glob ma non l'`exec_page` → segnala l'`exec_page`. Assente la config → segnale
  disattivato (nessun path hardcodato, Principio X). Estendere `profile.WikiProfile` per leggere `[ritual]`.
- [ ] T009 [P] [US3] Test drift: `stale-updated` · `neighbor-of-change` · `capability-exec` con/senza config;
  confine D↔N (candidati, non verdetti).

## Phase 5: User Story 2 — dichiarazione forzata + CLI (P1)

**Goal:** lo skip diventa visibile; il tool emette lo scaffold e il contratto host-facing forza la dichiarazione.

**Independent Test:** l'output include lo scaffold pre-popolato; il blocco rituale distribuito richiede la
riga di dichiarazione; `test_assets_sync` verde.

- [ ] T010 [US2] `declaration_scaffold` nell'output (summary + JSON): `Rituale: record: <?> · distill: <N…> ·
  lint: <M…>` coi conteggi dei candidati pre-popolati (DA-4).
- [ ] T011 [US2] Registrare il sottocomando **`ritual-check`** in `src/sertor_core/wiki_tools/__main__.py`
  (opzioni `--base`/`--pages`/`--json`/`--config`/`--root`), come da `contracts/ritual-check.md`; exit-code
  0/1/2.
- [ ] T012 [US2] **Contratto host-facing:** aggiungere la regola di **dichiarazione forzata** (`Rituale: record ✅ ·
  distill: <verdetto> · lint: <verdetto>`, «non serve» incluso) + il rimando a `ritual-check` come strumento di
  scoperta, nel blocco `SERTOR:WIKI-RITUAL` (claude-md-block) **e** nel `wiki-playbook.md`. Parità Claude/Copilot.
- [ ] T013 [US2] **Bundle + sync:** propagare gli asset host-facing (`packages/sertor/.../assets/**`) via
  `uv run python -m sertor_installer.sync`; verde la guardia root `tests/unit/test_assets_sync.py`. Aggiornare la
  **prosa IT** del `CLAUDE.md`/playbook del dogfood (ownership-note).

## Phase 6: Polish & verifica (cross-cutting)

- [ ] T014 Test **fail-loud** (SC-005): scope indeterminabile (no git, no `--pages`) → exit 1 + messaggio, mai
  liste vuote. Test **contratto JSON** `wiki.ritual_check/1` + summary umano.
- [ ] T015 **Dogfood + gate:** `uv run --project .sertor sertor-wiki-tools ritual-check --json` sul branch
  corrente (esito reale sui candidati di questo step); gate pre-merge `uv run pytest -m "not cloud"` + `uv run
  ruff check .` verdi; `sertor-core` engine invariato.

## Dependencies & order

- **Setup (T001-T002)** → **Foundational (T003-T004)** prima delle user story.
- **US1 (T005-T006)** è l'MVP; **US3 (T007-T009)** indipendente (drift); **US2 (T010-T013)** dipende dallo scope
  (T003) e dai candidati (T005/T007) per lo scaffold.
- **[P]** = parallelizzabili (file di test distinti): T006, T009.
- **Polish (T014-T015)** alla fine.

## Analyze (inline) — copertura

- **FR→task:** FR-001/002→T005 · FR-003→T007/T008 · FR-004→T001/T011/T014 · FR-005→T003/T008 (config) ·
  FR-006→T003/T014 · FR-007/008→T012 · FR-009→T010 · FR-010→T013 · FR-011→T005/T006 (sola lettura, no LLM).
- **SC→verifica:** SC-001→T006/T009 · SC-002→T012 · SC-003→T006 · SC-004→T008/T013 · SC-005→T014.
- Nessun task orfano; Constitution gate PASS. **Task totali: 15** (US1: 2 · US3: 3 · US2: 4 · Setup 2 · Found. 2 · Polish 2).
