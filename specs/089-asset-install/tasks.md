---
description: "Task list — E15 asset-install (fedelta-dogfood, FEAT-001 scope B)"
---

# Tasks: asset-install — gli asset del dogfood dall'installer (0 special-case)

**Input**: Design documents from `/specs/089-asset-install/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/verification.md, quickstart.md
**Branch**: `089-asset-install` · **Tests**: solo il minimo richiesto (test negativo EOL + riuso guardie byte)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza su task incompleti)
- **[Story]**: US1..US5 (dallo spec) · Setup/Foundational/Polish senza label
- ⚠️ **Natura distruttiva:** i task US1 eseguono i **veri installer sul repo vivo** → tutto su branch,
  diff ispezionato prima del commit (FR-009/NFR-5). Il gate di reversibilità è T014.

---

## Phase 1: Setup (baseline ispezionabile)

**Purpose**: catturare lo stato pre-install per poter ispezionare/annullare.

- [ ] T001 Verificare di essere su branch `089-asset-install` con working tree pulito (`git status`); i soli untracked ammessi sono `.sertor/.last-hook-error` e `wiki/sources/Human/` (non correlati, non toccarli)
- [ ] T002 Catturare la baseline: `git rev-parse HEAD` e `git ls-files --eol > specs/089-asset-install/.eol-baseline.txt` (scratch, non committato) come riferimento per il confronto no-churn

---

## Phase 2: Foundational — policy line-ending (BLOCCANTE, precede gli installer)

**Purpose**: azzerare il churn CRLF **prima** di eseguire gli installer, altrimenti il diff dell'install è
illeggibile (D1). Serve US3 ma è prerequisito di US1. ⚠️ Nessun installer va eseguito prima che questa fase
sia verde.

- [ ] T003 Creare `.gitattributes` alla radice del dogfood con `* text=auto eol=lf` (+ eventuali eccezioni binarie note); documentare l'intenzione in una riga di commento
- [ ] T004 Allineare l'index: `git add .gitattributes && git add --renormalize .`; verificare `git ls-files --eol | Select-String "crlf"` = nessun match testuale spurio (INV-2)
- [ ] T005 [P] Rinormalizzare a LF i bundle `assets/` dei tre package (`packages/sertor/src/sertor_installer/assets/**`, `packages/sertor-flow/src/sertor_flow/assets/**`, `packages/sertor-install-kit/**/assets/**` se presenti) così le guardie byte confrontano LF↔LF (Edge Case CRLF↔byte-guard)
- [ ] T006 **[FEAT-010, host-facing]** Aggiungere `.gitattributes` come **asset distribuito** e cablarlo nel piano dell'installer (`sertor install wiki` o `rag`) con deposito **create-if-absent** (non clobberare un `.gitattributes` preesistente dell'ospite — Principio VI/X); contenuto generico `* text=auto eol=lf`
- [ ] T007 [P] Nuovo test negativo `tests/unit/test_asset_install_eol.py`: asserisce `eol=lf` sui path chiave (`CLAUDE.md`, `.claude/**`, `assets/**`) e fallisce su EOL-inconsistenza (C3)

**Checkpoint fase 2:** repo EOL-consistente, guardie byte ancora verdi, `sertor-core` non toccato.

---

## Phase 3: US1 — la FONTE degli asset è il vero installer (P1) 🎯 MVP

**Goal**: gli asset host-facing prodotti eseguendo i 3 veri installer sul dogfood (ordine flow → rag → wiki).
**Independent test**: eseguendo i 3 installer, gli asset già fedeli risultano `skipped`/aggiornati (mai
duplicati) e gli artefatti curati restano preservati (SC-1).

- [ ] T008 [US1] Eseguire `sertor-flow install --assistant claude` sul dogfood; catturare l'`InstallReport` (machinery `.specify/` + blocco SDLC; preservante su costituzione/`plan-template` via FEAT-005)
- [ ] T009 [US1] Eseguire `sertor install rag --assistant claude`; catturare il report (hook/skill/agenti RAG in `.claude/**` + wiring PreToolUse in `settings.json` + blocco `SERTOR:RAG-USAGE` + `.sertor/sertor-cli-reference.md`)
- [ ] T010 [US1] Eseguire `sertor install wiki --assistant claude`; catturare il report (struttura `wiki/` + blocco `SERTOR:WIKI-RITUAL`)
- [ ] T011 [US1] Ispezionare l'esito: `git diff --stat src/sertor_core/` DEVE essere vuoto (Principio XI); `git status --porcelain` per l'inventario dei cambiamenti; confrontare col dry-run 2026-07-04 (residuo atteso ~174 righe `CLAUDE.md` + hook `settings.json` + cli-reference)
- [ ] T012 [US1] Mappare eventuali **clobber non mappati** (R-1): se un artefatto curato (`.env`, costituzione, `.mcp.json`, `wiki.config.toml`) risulta cambiato → estendere la preservazione dell'installer (meccanismo FEAT-005, host-agnostico) prima di procedere; altrimenti confermare preservazione
- [ ] T013 [US1] Verificare la presenza di `.sertor/sertor-cli-reference.md` (FR-007/SC-5): se dest tracciata → includerlo; se gitignorata → dichiararlo prodotto-a-runtime nel record

**Checkpoint US1:** asset depositati dal processo reale; nessun clobber curato; core invariato.

---

## Phase 4: US2 — CLAUDE.md riconciliato (ibrido per-blocco) (P1)

**Goal**: nessuna duplicazione blocco-vs-prosa; ogni tema coperto una sola volta (SC-3).
**Independent test**: conteggio marker = 1 per tema; nessuna prosa duplica pura il blocco convivente.

- [ ] T014 [US2] **GATE reversibilità**: ispezionare il diff completo di `CLAUDE.md` (`git diff -- CLAUDE.md`); confermare che il residuo è solo contenuto reale (0 righe EOL grazie a fase 2). Se emerge un clobber inatteso → `git checkout -- .` e ritorno a T012
- [ ] T015 [US2] Riconciliare `SERTOR:RAG-USAGE` (D3): tieni il blocco (proprietario della sezione MCP-first host-facing); sfronda dalla prosa IT i duplicati puri
- [ ] T016 [US2] Riconciliare `SERTOR:WIKI-RITUAL` (D3): la prosa dogfood vince (più ricca); rimuovere/minimizzare il blocco per evitare la ridondanza
- [ ] T017 [US2] Riconciliare `SERTOR:SDLC-RITUAL` (D3): ibrido — tieni il blocco (7 fasi SpecKit forma-client) + togli dalla prosa i duplicati puri, lasciando solo ciò che il blocco non dice
- [ ] T018 [US2] Verificare single-coverage: ogni coppia marker compare una volta; `CLAUDE.md` resta bilingue (blocchi EN + prosa IT); un ri-install non re-inserirà (garantito da `write_marker_block`)

**Checkpoint US2:** `CLAUDE.md` senza duplicazioni, contratto di governance intatto.

---

## Phase 5: US3 — diff pulito, nessun churn CRLF (P2)

**Goal**: il diff dell'install mostra solo contenuto reale (SC-2). La policy è già in fase 2; qui si verifica.

- [ ] T019 [US3] Verificare INV-2: `git diff` dei file toccati mostra 0 righe da line-ending; `git ls-files --eol` = repo consistente; confronto con `.eol-baseline.txt` (T002)

**Checkpoint US3:** churn CRLF azzerato, diff review-abile.

---

## Phase 6: US4 — sync/script come guardia, non fonte (P2)

**Goal**: la documentazione non indica più sync/script come modo di *ottenere* gli asset; guardie byte attive.

- [ ] T020 [P] [US4] Aggiornare gli header dei moduli sync (`packages/sertor/src/sertor_installer/sync.py`, `packages/sertor-flow/src/sertor_flow/sync.py`, `packages/sertor-install-kit/src/sertor_install_kit/sync.py`): marcarli **dev-tool/guardia anti-drift**, non «via di fedeltà» (la fonte è il vero install)
- [ ] T021 [P] [US4] Aggiornare l'header di `scripts/dev/materialize-speckit.ps1`: dev-tool, non fonte degli asset
- [ ] T022 [US4] Aggiornare la prosa del rituale (in `CLAUDE.md` / doc dev) dove cita il sync come via di ottenimento asset → puntare al vero install
- [ ] T023 [US4] Verificare che le guardie byte restino verdi e falliscano su drift indotto: `uv run pytest tests/unit/test_assets_sync.py tests/unit/test_assets_rag_dogfood_sync.py packages/sertor-flow/tests/unit/test_assets_sync.py` (C1/SC-4)

**Checkpoint US4:** rete anti-drift preservata; ambiguità sulla fonte chiusa.

---

## Phase 7: US5 — `wiki/log.md` legacy risolto (P3)

**Goal**: il dogfood non traccia un `wiki/log.md` spurio; la conoscenza resta in `wiki/log/<data>.md`.

- [ ] T024 [US5] Rimuovere il `wiki/log.md` spurio prodotto dall'install dal dogfood (`Remove-Item wiki/log.md`); confermare che `wiki/log/` è intatto
- [ ] T025 [US5] Slice E15-FEAT-006: allineare il template/installer alla rotazione `wiki/log/` **o** dichiarare il `wiki/log/` del dogfood come forma-client super-set preservata (REQ-005); promuovere il resto della rotazione-template a FEAT-006 nel backlog (non seppellire)

**Checkpoint US5:** log del dogfood coerente con la rotazione.

---

## Phase 8: Polish & cross-cutting

**Purpose**: doc utente (host-facing), verifica idempotenza, gate pre-merge, rituale.

- [ ] T026 [P] **Doc utente (FEAT-010, regola CLAUDE.md §Feature completa 3)**: aggiungere in `docs/install.md` (+ quick-start `docs/install-claude.md`, `README.md` dove pertinente) la nota sulla policy `.gitattributes`/EOL depositata dal template — perché c'è, cosa fa su host Windows
- [ ] T027 **Idempotenza (NFR-1/C2)**: ri-eseguire i 3 installer (`sertor-flow install`, `sertor install rag`, `sertor install wiki`) → `git status --porcelain` atteso vuoto (o superset dichiarato); 0 blocchi duplicati
- [ ] T028 **Gate pre-merge (SC-5, E15-FEAT-008)**: `uv run pytest -m "not cloud"` **e** `uv run ruff check .` verdi (non fidarsi di run mirati)
- [ ] T029 Aggiornare `wiki/syntheses/roadmap.md` (EXEC + riga E15) e delegare al `wiki-curator` il record/distill dello step; explainer se pertinente
- [ ] T030 Commit + PR (delega `configuration-manager`, mai master diretto); dopo merge: re-lock runtime → re-index (`sertor-rag index .`) → smoke MCP → mostra EXEC roadmap

---

## Dependencies & ordine

- **Phase 2 (EOL) BLOCCA Phase 3+** — nessun installer prima che la policy EOL sia verde (altrimenti churn).
- **T012 (clobber) BLOCCA T014** — mappare i clobber prima del gate reversibilità.
- **US1 (T008–T013) precede US2 (T015–T018)** — riconcili `CLAUDE.md` dopo che l'install ha inserito i blocchi.
- **US3/US4/US5 indipendenti** fra loro dopo US1; US4 e i doc (T026) sono in gran parte [P].
- **T027 (idempotenza) richiede US1+US2+US5 completi** (secondo giro deve essere no-op).
- **T028 (gate) è l'ultimo prima di T029/T030.**

## Parallel opportunities

- Phase 2: T005 ∥ T007 (bundle renorm ∥ nuovo test).
- Phase 6: T020 ∥ T021 (header sync ∥ header script).
- Phase 8: T026 (doc) ∥ gran parte di US4.

## MVP scope

**MVP = Phase 2 + US1 (T003–T013)**: gli asset del dogfood **prodotti dal vero installer** con diff pulito.
US2 (riconciliazione) è P1 e va completata per lo stato committabile; US3/US4/US5 rifiniscono e chiudono
la clausola «0 special-case».

## Independent test per storia

- **US1**: 3 installer → asset `skipped`/aggiornati, 0 duplicati, curati preservati (SC-1).
- **US2**: conteggio marker = 1/tema, nessuna prosa-duplica-blocco (SC-3).
- **US3**: `git ls-files --eol` consistente, 0 righe-diff EOL (SC-2).
- **US4**: guardie byte verdi + rosse su drift; doc non cita più sync come fonte (SC-4).
- **US5**: nessun `wiki/log.md` nel dogfood; `wiki/log/` intatto.
