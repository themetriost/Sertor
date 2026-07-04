# Tasks: Rituale post-merge — re-lock del runtime `.sertor/` a HEAD

**Feature**: E15-FEAT-008 (epica `fedelta-dogfood`) | **Branch**: `092-f8-relock-runtime`
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

Feature di **tooling dogfood** (zero `sertor-core`). Tre user story: US1 (script re-lock, P1), US2 (nessun
churn dal lock committato, P1), US3 (meccanico + fail-loud + rituale, P2). US2 è **prerequisito** di US1 (senza
il gitignore, il re-lock genererebbe churn/loop) → precede in Foundational.

## Phase 1: Setup

- [ ] T001 Verifica il contesto: sei sul branch `092-f8-relock-runtime`, `.sertor/pyproject.toml` e
  `.sertor/uv.lock` sono tracciati, `origin/master` è fetchato. Nessun file da creare in questa fase.

## Phase 2: Foundational (prerequisito bloccante — US2 core)

**Goal:** rendere `.sertor/uv.lock` locale prima di attivare il re-lock, così il re-lock non produce churn.

- [ ] T002 [US2] Aggiungi `**/.sertor/uv.lock` al blocco `.sertor/` di `.gitignore` (accanto a
  `**/.sertor/.rag-health.json` / `**/.sertor/.sertor-version`), con commento «lock volatile del runtime
  dogfood — tracks HEAD, rigenerato dal re-lock (E15-FEAT-008)».
- [ ] T003 [US2] Rimuovi `.sertor/uv.lock` dal tracking git mantenendolo su disco:
  `git rm --cached .sertor/uv.lock` (delega al `configuration-manager` al momento del commit; qui basta che
  il file esca da `git ls-files`). Verifica che `.sertor/pyproject.toml` resti tracciato.

**Checkpoint:** `git ls-files .sertor/` mostra `pyproject.toml` ma NON `uv.lock`; `git status` non segnala il
lock (gitignorato).

## Phase 3: User Story 1 — Il runtime si riallinea a HEAD dopo un merge (P1) 🎯 MVP

**Goal:** un passo deterministico check-then-act che porta `.sertor/` all'HEAD di `origin/master`.
**Independent test:** con lock a un commit precedente e `origin/master` avanzato, eseguire lo script →
`sertor-core` risolto in `.sertor/.venv` == nuovo `origin/master`; già a HEAD → no-op.

- [ ] T004 [US1] Crea `scripts/dev/relock-runtime.ps1` con lo scheletro + preflight fail-loud (FR-005):
  verifica `uv` sul PATH e `.sertor/pyproject.toml` esistente → altrimenti messaggio azionabile + `exit 2`.
  Param `-WhatIf` (dry-run). Header di commento: dogfood-only, non bundlato.
- [ ] T005 [US1] Implementa il **check** in `scripts/dev/relock-runtime.ps1` (FR-002, Q2): `git fetch origin
  master --quiet` (fail-loud → `exit 3`); estrai lo SHA lockato da `.sertor/uv.lock` (regex
  `Sertor\.git#([0-9a-f]+)`); confronta con `git rev-parse origin/master`. Uguali → stampa
  `runtime già a HEAD (<sha7>): no-op` + `exit 0`. Lock assente → tratta come `behind`.
- [ ] T006 [US1] Implementa il **re-lock** in `scripts/dev/relock-runtime.ps1` (FR-001, FR-006): solo se
  `behind` e non `-WhatIf`, esegui `uv lock --upgrade-package sertor-core --project .sertor` poi
  `uv sync --project .sertor` (solo vehicle `uv`, mai import `sertor_core`); fail-loud su errore
  (rete/risoluzione/sync) → messaggio azionabile + `exit 3`, nessun runtime parziale spacciato per ok.
  Stampa `re-lock: <old_sha7> -> <new_sha7>` + `exit 0`. Con `-WhatIf`, riporta solo l'azione che farebbe.

**Checkpoint:** eseguito dal vivo, lo script porta il runtime da `2e8ce30` a `879b688` (HEAD attuale) e una
seconda esecuzione è no-op.

## Phase 4: User Story 2 — Nessun churn/loop dal lock committato (P1)

**Goal:** blindare il tracking corretto con una guardia; verificare il clone fresco.
**Independent test:** `.sertor/uv.lock` assente da `git ls-files`, `.sertor/pyproject.toml` presente; dopo un
re-lock `git status` non mostra il lock.

- [ ] T007 [P] [US2] Crea `tests/unit/test_relock_runtime_dogfood.py` — guardia di regressione (offline,
  presence-agnostica): (a) `.sertor/uv.lock` NON è in `git ls-files` (untracked/gitignorato);
  (b) `.sertor/pyproject.toml` È tracciato; (c) `**/.sertor/uv.lock` è presente in `.gitignore`.
- [ ] T008 [US2] Verifica manuale del clone fresco (SC-4, documentata in quickstart): `uv sync --project
  .sertor` su un checkout senza lock committato risolve `sertor-core` a HEAD. Nessun file da creare — solo
  conferma nell'accettazione.

## Phase 5: User Story 3 — Meccanico, fail-loud e nel rituale (P2)

**Goal:** cablare il passo nel rituale post-merge documentato + gate pre-merge; blindare il confine dogfood.
**Independent test:** rete assente → script esce non-zero azionabile; `CLAUDE.md` descrive il passo prima di
re-index/smoke e il gate suite+ruff.

- [ ] T009 [P] [US3] Estendi `tests/unit/test_relock_runtime_dogfood.py` con la guardia del **confine
  dogfood↔distribuito** (SC-6, D5): lo script `scripts/dev/relock-runtime.ps1` NON compare sotto
  `packages/**/assets/` e NON è referenziato da alcun `rag-freshness*.ps1` (né distribuito né in `.claude/`).
- [ ] T010 [US3] Aggiorna il **rituale post-merge** in `CLAUDE.md` (punto 5/6 del rituale di step e/o sezione
  Git): aggiungi il passo «re-lock del runtime `.sertor/` via `scripts/dev/relock-runtime.ps1` **prima** di
  re-index/smoke» e il **gate pre-merge «suite completa (`uv run pytest`) + `uv run ruff check .` verdi prima
  del merge»** (FR-008, regressione 2026-07-03). Nota il confine dogfood-only.

## Phase 6: Polish & verifica finale

- [ ] T011 `uv run ruff check .` pulito su tutto il modificato (incluso il test) — gate anti-regressione del
  fix CI di oggi.
- [ ] T012 `uv run pytest tests/unit/test_relock_runtime_dogfood.py -q` verde + suite root non-cloud verde
  (`uv run pytest -m "not cloud"`); `sertor-core` invariato (`git diff --stat src/sertor_core/` vuoto).
- [ ] T013 Accettazione dal vivo: esegui `scripts/dev/relock-runtime.ps1`; verifica il runtime a HEAD
  (`.sertor/uv.lock` con `#879b688…`) e la seconda esecuzione no-op; `git status` non mostra il lock.

## Dependencies & ordine

- **T001** (setup) → **T002/T003** (foundational, US2 core) → **T004→T005→T006** (US1, sequenziali stesso
  file) → **T007** (guardia US2) → **T009** (guardia confine US3) → **T010** (doc) → **T011/T012/T013** (verifica).
- **US2 (T002/T003) precede US1**: il gitignore deve esserci prima che il re-lock scriva il lock, sennò churn.
- **[P]**: T007 e T009 toccano lo stesso file di test ma sezioni diverse; se fatti insieme, un solo autore.

## MVP

**US1 (T004–T006)** sopra il foundational US2 (T002–T003) = MVP: il runtime si riallinea a HEAD in modo
meccanico, senza churn. US3 (rituale + gate + confine) è l'hardening che lo rende parte del processo.
