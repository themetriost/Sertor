---
description: "Task list — E2 A-09 portabilità hook (hook portabili)"
---

# Tasks: Portabilità POSIX degli hook (hook portabili)

**Input**: Design da `/specs/095-portable-hooks-09/` (plan, research, data-model, contracts, quickstart)
**Branch**: `095-portable-hooks-09` · **Tests**: parità per-hook (offline) + fail-safe + smoke CI matrice
**Riferimento invariante**: gli 8 `.ps1` sono il **contratto** (output per-assistente + effetti di stato) che i `.py` devono riprodurre; la parità è **gate pre-merge**.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi) · **[Story]**: US1/US2/US3 · Setup/Foundational/Polish senza label
- «Fatto» = **parità provata** (output+stato) su ogni OS, `.ps1` ritirati, `sertor-core` invariato.

---

## Phase 1: Setup

- [X] T001 Comportamento di riferimento catturato leggendo i `.ps1` (usage-check: fail-open/stderr; rag-freshness-start: stdout directive se degraded)
- [X] T002 **Invocazione portabile PROVATA:** `uv run --no-project python <hook>` esegue dall'interno del repo Sertor (con pyproject) **ignorandolo** → output corretto, exit 0

---

## Phase 2: Foundational (BLOCCANTE)

**Purpose**: il meccanismo d'invocazione portabile + l'harness di parità, prerequisiti di ogni hook.

- [X] T003 Kit/installer: **wiring portato** — 7 settings JSON Claude (no `"shell"`, `.ps1`→`.py`, comando `uv run --no-project python .../<name>.py [--assistant/--mode]`) + Copilot `HookEntrySpec` (`_PY` al posto di `_PWSH`, `--assistant/--mode`). **Deposito `_hooklib.py`** aggiunto (mancava: gli hook lo importano) per rag+wiki, entrambi gli assistenti; owned-paths aggiornati. `resources.py` salta `__pycache__` (i `.py` negli asset generano bytecode). Suite `-m "not cloud"` **1176 verde**, ruff clean, `sertor-core` invariato. *(Coda coupled resa verde qui: guardie sync dogfood auto-coprono i `.py` (≈T020), sync dogfood eseguito (≈T025), nota `pwsh` rag ora inerte + test invertiti (≈T021 lato-rag); restano T019/T022/T023 + T021 lato-wiki.)*
- [X] T004 Helper condiviso `_hooklib.py` (stdin-guard `read_event`, `project_root`/`sertor_dir`, `write_breadcrumb` secret-free `hook.error/1`, `run()` fail-safe exit-0) — creato + provato
- [X] T005 [P] Harness di parità `test_portable_hooks_parity.py` (subprocess con evento simulato → stdout/stderr + file `.sertor/*`); 10 test verdi

**Checkpoint fase 2:** invocazione + helper + harness pronti; nessun hook ancora portato.

---

## Phase 3: US1 — gli 8 hook operativi su ogni OS (P1) 🎯 MVP

**Goal**: ogni hook riscritto in Python iso-funzionale, operativo senza `pwsh`.
**Independent test**: su host senza `pwsh`, ogni hook al suo evento produce l'effetto atteso (SC-001).

- [X] T006 [P] [US1] `rag-freshness-start.py` — portato iso-funzionale (output stdout byte-fedele), parità verde
- [X] T007 [P] [US1] `version-check-start.py` — portato (notice byte-fedele + dimensions), parità verde
- [X] T008 [P] [US1] `sertor-rag-usage-check.py` — portato (fail-open/stderr, exit 0), parità verde
- [X] T009 [P] [US1] `wiki-session-start.py` — portato (directive byte-fedele, claude stdout / copilot additionalContext), parità verde
- [X] T010 [P] [US1] `wiki-pending-check.py` — portato (Mode/Assistant, delega CLI, output per-assistante), parità no-op verde
- [X] T011 [US1] `version-check.py` — portato (GET https-only via `urllib`, cache 24h, compare semantico), parità cache-path verde
- [X] T012 [US1] `memory-capture.py` — portato (privacy gate, delega vehicle, fallback venv, breadcrumb), parità no-op verde
- [X] T013 [US1] `rag-freshness.py` — portato: worker **detached cross-OS** (`Popen`+`start_new_session`/`DETACHED_PROCESS`), foreground ritorna subito (parità), degrado fail-safe
- [X] **_hooklib.py** condiviso in **entrambi** i bundle (rag/ + claude/) per l'install wiki-only + guardia anti-drift

**Checkpoint US1:** 8 hook Python operativi; parità verde (19 test).

---

## Phase 4: US2 — parità funzionale, gate pre-merge (P1)

**Goal**: ogni portabile riproduce output-per-assistente + stato dei `.ps1`; verifica bloccante (SC-002).

- [X] T014 [US2] Parità **output per-assistente** (claude/copilot) coperta per gli hook con output (usage-check, freshness-start, version-check-start, wiki-session-start)
- [X] T015 [US2] Parità **effetti di stato**: `version-check`→`.version-check.json` (cache-path, no rete), schema invariato; `.rag-health.json` via worker (dogfood)
- [X] T016 [US2] **Fail-safe/stdin-guard** coperti (fail-open usage-check, no-op malformed, no-hang senza stdin)
- [X] T017 [US2] **Detach** foreground di `rag-freshness`: ritorna subito (parità); worker disaccoppiato
- [X] T018 [US2] **Smoke CI matrice** (ubuntu + windows) — `test_portable_hooks_smoke.py` guida ogni hook via il **vero vehicle** `uv run --no-project python <hook>.py` (marker `hooks_smoke`, 8 test, exit-0 + effetti hermetici, no rete); step CI dedicato *«Smoke — portable hooks»* nel job `test` (matrice windows+ubuntu, **per-PR**), escluso dal run sertor principale (no doppio-run). Prova la portabilità reale dell'esecuzione (C6, SC-001/005) su entrambi gli OS senza `pwsh`. Verde in locale (Windows, 8/8, 1.6s), ruff clean.

**Checkpoint US2:** parità verde (gate) su tutti gli hook/assistenti/OS.

---

## Phase 5: US3 — single-impl, no regressione Windows, ritiro `.ps1` (P2)

**Goal**: una implementazione per hook; `.ps1` ritirati a parità verde; wiring OS-indipendente.

- [X] T019 [US3] **Rimossi** gli 8 `.ps1` dal **bundle** (`assets/rag/hooks/*.ps1` ×6 + `assets/claude/hooks/wiki-*.ps1` ×2). Dogfood `.claude/hooks/*.ps1` → migrati **post-merge via `sertor upgrade`** (non hand-edit: regola dogfood-via-install), vedi T028.
- [X] T020 [US3] **Guardie di sync** auto-adattate: `test_assets_rag_dogfood_sync`/`test_assets_sync` enumerano l'asset-dir (ora solo `.py` + `_hooklib.py`) → coprono i `.py` senza modifica; rimosso il ridondante hardcoded `test_rag_freshness_dogfood_sync`.
- [X] T021 [US3] **Nota `pwsh` rimossa** (E10-FEAT-018 superata): eliminati `host_env.py` + `test_host_env.py` + `test_install_pwsh_guard.py` + i 2 call-site (`maybe_note_pwsh`). Il gap pwsh è **chiuso dalla portabilità**, non silenziato (XII). Nota Copilot memory-capture preservata.
- [X] T022 [US3] **`upgrade` riconcilia il wiring**: legacy `.ps1` dichiarati **owned** → obsolete-phase li rimuove (file); nuovo helper kit `remove_hook_entries_by_command_substring` strippa le voci `.ps1` per **basename** (robusto alle vecchie forme Claude `& (Join-Path…)` / Copilot `pwsh -File`), cablato in upgrade rag+wiki. Test: 5 unit kit + 3 integration sertor (file rimossi · wiring strippato · user-hook preservato). *(uninstall-di-host-legacy fuori scope T022 — solo upgrade.)*
- [X] T023 [US3] Single-impl **verificato** (bundle): 0 `.ps1` hook, 0 `"shell":"powershell"` negli asset; solo i target legacy-migration restano in sorgente (intenzionali). Migrazione **live** del dogfood → T028 post-merge.

**Checkpoint US3:** un corpo per hook, wiring OS-indip., `.ps1` ritirati.

---

## Phase 6: Polish & cross-cutting

- [ ] T024 [P] **Doc utente**: `docs/install.md` — aggiornare la sezione «Operatività per target/OS» (gli hook ora funzionano su mac/Linux **senza `pwsh`**) e rimuovere il caveat pwsh dove non più valido (regola §Feature completa 3)
- [ ] T025 **Sync dogfood**: `uv run python -m sertor_installer.sync` → i `.py` nel `.claude/hooks/`; verificare che il dogfood (Windows) esegua i portabili
- [ ] T026 **Gate pre-merge (SC-006)**: `uv run pytest -m "not cloud"` + `uv run ruff check .` verdi; `git diff --stat src/sertor_core/` = **vuoto**
- [ ] T027 Wiki record + roadmap (A-09 → ✅ a parità provata); distill/lint dichiarati
- [ ] T028 Commit + PR (delega `configuration-manager`); merge su OK utente a **CI + parità verdi**; post-merge: re-lock → re-index → smoke MCP + **verifica dal vivo hook portabili sul dogfood** → EXEC roadmap; eliminare il branch ridondante `094`

---

## Dependencies & ordine

- **Phase 2 (wiring+helper+harness) BLOCCA Phase 3+.**
- **US1 (T006–T013):** i 6 hook «leggeri» (T006–T012) sono in gran parte [P] (file diversi); `rag-freshness` (T013, detach) è il più rischioso → attenzione.
- **US2 (parità) richiede US1** (i `.py` esistono).
- **US3 (ritiro `.ps1`) richiede US2 VERDE** (T019 solo a parità provata — DA-1: sostituzione a parità).
- **Polish** ultimo; T028 (merge) solo a CI+parità verdi.

## Parallel opportunities

- US1: T006–T010 (hook leggeri, file diversi) in parallelo; T011/T012/T013 sequenziali per rischio.
- US2: T014/T015/T016 su file di test diversi ∥ possibile.
- T024 (doc) ∥ gran parte di Polish.

## MVP scope

**MVP = Phase 2 + US1 + US2** (gli 8 hook portabili + parità provata). US3 (ritiro `.ps1`) chiude il
single-impl; senza di essa la feature funziona ma resta il doppio-binario — quindi US3 è necessaria per il
«done» pieno (DA-1). Polish rifinisce.

## Independent test per storia

- **US1**: su host senza `pwsh`, 8/8 hook producono l'effetto atteso (SC-001).
- **US2**: parità output+stato == `.ps1` per ogni hook×assistente×OS (SC-002), gate.
- **US3**: 0 `.ps1` residui, 0 `"shell":"powershell"`, wiring OS-indip. (SC-005).
