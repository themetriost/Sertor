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

- [X] T001 Verificare di essere su branch `089-asset-install` con working tree pulito (`git status`); i soli untracked ammessi sono `.sertor/.last-hook-error` e `wiki/sources/Human/` (non correlati, non toccarli)
- [X] T002 Catturare la baseline: `git rev-parse HEAD` (4364472) e `git ls-files --eol` (1454 file) su scratch come riferimento per il confronto no-churn

---

## Phase 2: Foundational — policy line-ending (BLOCCANTE, precede gli installer)

**Purpose**: azzerare il churn CRLF **prima** di eseguire gli installer, altrimenti il diff dell'install è
illeggibile (D1). Serve US3 ma è prerequisito di US1. ⚠️ Nessun installer va eseguito prima che questa fase
sia verde.

- [X] T003 Creato `.gitattributes` alla radice del dogfood con `* text=auto eol=lf` + commento d'intenzione
- [X] T004 Index allineato a LF: `git add .gitattributes && git add --renormalize .` → 94 file rinormalizzati, `i/crlf`=0 (index tutto LF), worktree pulito in `git status` (attributo `eol=lf` neutralizza il CRLF su disco)
- [X] T005 [P] Bundle `assets/` già LF (verificato); coperti dal renormalize globale — nessuna modifica necessaria (guardie byte confrontano via `read_text` = EOL-insensibili)
- [X] T006 **[FEAT-010, host-facing]** Aggiunto `assets/rag/gitattributes` (host-agnostico) + artifact `FILE/CREATE_IF_ABSENT` in `build_rag_plan` (target `.gitattributes`, non clobbera un file host preesistente); pin positivo `test_rag_plan_deposits_gitattributes` + whitelist host-root aggiornata
- [X] T007 [P] `tests/unit/test_asset_install_eol.py`: policy LF presente + `.gitattributes` dogfood byte-identico all'asset installer (process-fidelity, SC-2); 2 test verdi

**Checkpoint fase 2:** repo EOL-consistente, guardie byte ancora verdi, `sertor-core` non toccato.

---

## Phase 3: US1 — la FONTE degli asset è il vero installer (P1) 🎯 MVP

**Goal**: gli asset host-facing prodotti eseguendo i 3 veri installer sul dogfood (ordine flow → rag → wiki).
**Independent test**: eseguendo i 3 installer, gli asset già fedeli risultano `skipped`/aggiornati (mai
duplicati) e gli artefatti curati restano preservati (SC-1).

- [X] T008 [US1] `sertor-flow install --no-deps` eseguito: `specify init` **skipped** (già presente, no clobber `.specify/`), costituzione **preservata**, blocco SDLC-RITUAL inserito
- [X] T009 [US1] `sertor install rag --no-deps` eseguito: `.env`/`.mcp.json` **preservati**, `.gitattributes` **skipped** (FEAT-010 process-fidelity), `.gitignore` +8 runtime ignores, `settings.json` +PreToolUse RAG-usage, blocco RAG-USAGE inserito, `.sertor/sertor-cli-reference.md` **creato**
- [X] T010 [US1] `sertor install wiki` eseguito: asset skipped, `wiki.config.toml` **preservato**, `settings.json` +wiki SessionStart, blocco WIKI-RITUAL inserito, `wiki/log.md` spurio creato
- [X] T011 [US1] Ispezionato: `git diff --stat src/sertor_core/` **vuoto** (XI ✅); residuo = CLAUDE.md +174 righe (3 blocchi) + settings.json (2 wiring) + .gitignore (+8) + cli-reference (created) + wiki/log.md (spurio). Coerente col dry-run
- [X] T012 [US1] **Nessun clobber non mappato** (R-1 azzerato): `.env`/costituzione/`.mcp.json`/`wiki.config.toml` tutti preservati/skipped. `.gitignore`+`settings.json` = divergenze dogfood-indietro-vs-client → adotta forma-client (SC-6)
- [X] T013 [US1] `.sertor/sertor-cli-reference.md` **presente** (untracked, NON gitignorato) → da tracciare (forma-client, SC-5)

**Checkpoint US1:** asset depositati dal processo reale; nessun clobber curato; core invariato.

---

## Phase 4: US2 — CLAUDE.md riconciliato (ibrido per-blocco) (P1)

**Goal**: nessuna duplicazione blocco-vs-prosa; ogni tema coperto una sola volta (SC-3).
**Independent test**: conteggio marker = 1 per tema; nessuna prosa duplica pura il blocco convivente.

- [X] T014 [US2] **GATE reversibilità**: diff completo ispezionato — solo contenuto reale (0 righe EOL), nessun clobber inatteso, core invariato. Confermato con l'utente (AskUserQuestion)
- [X] T015 [US2] Riconciliazione via **ownership-note** (non cancellazione): i 3 blocchi restano proprietari del contratto client-form; la prosa IT dogfood è l'applicazione autoritativa. Nota d'orientamento aggiunta prima della regione blocchi
- [X] T016 [US2] `SERTOR:WIKI-RITUAL`: prosa dogfood autoritativa ma il blocco **resta** per idempotenza/process-fidelity (rimuoverlo lo farebbe ri-aggiungere all'install); ownership esplicitata nella nota
- [X] T017 [US2] `SERTOR:SDLC-RITUAL`: blocco tenuto (7 fasi SpecKit) + ownership vs prosa git chiarita dalla nota; nessuna prosa dogfood-critica cancellata
- [X] T018 [US2] Single-coverage: 3 marker START (uno/blocco), bilingue (EN+IT), ri-install **non re-inserisce** (T027: `block:0`)

**Checkpoint US2:** `CLAUDE.md` senza duplicazioni, contratto di governance intatto.

---

## Phase 5: US3 — diff pulito, nessun churn CRLF (P2)

**Goal**: il diff dell'install mostra solo contenuto reale (SC-2). La policy è già in fase 2; qui si verifica.

- [X] T019 [US3] INV-2 verificato: `git diff` dei file toccati = solo inserzioni (0 righe EOL); `git ls-files --eol` `i/crlf`=0 (repo consistente)

**Checkpoint US3:** churn CRLF azzerato, diff review-abile.

---

## Phase 6: US4 — sync/script come guardia, non fonte (P2)

**Goal**: la documentazione non indica più sync/script come modo di *ottenere* gli asset; guardie byte attive.

- [X] T020 [P] [US4] Header dei 3 moduli sync marcati **dev-tool/guardia anti-drift, NON fonte di fedeltà** (fonte = vero install)
- [X] T021 [P] [US4] Header di `scripts/dev/materialize-speckit.ps1` marcato dev-tool/bootstrap fallback, non fonte
- [X] T022 [US4] Prosa `CLAUDE.md` §«Machinery SpecKit» riscritta: la fonte è il vero install; sync/script = dev-tool/guardia (nota E15)
- [X] T023 [US4] Guardie byte verdi: `test_assets_sync` (root+flow) + `test_assets_rag_dogfood_sync` — 37 verdi

**Checkpoint US4:** rete anti-drift preservata; ambiguità sulla fonte chiusa.

---

## Phase 7: US5 — `wiki/log.md` legacy risolto (P3)

**Goal**: il dogfood non traccia un `wiki/log.md` spurio; la conoscenza resta in `wiki/log/<data>.md`.

- [X] T024 [US5] `wiki/log.md` spurio rimosso; `wiki/log/` intatto. Per «0 special-case» NON gitignorato (sarebbe workaround dogfood-locale)
- [X] T025 [US5] Dichiarato: il `wiki/log/` del dogfood è la forma-rotazione; `init_structure` che semina `wiki/log.md` monolitico = **staleness template → E15-FEAT-006** (promosso, non seppellito). Residuo `?? wiki/log.md` a ogni `install wiki` = dichiarato

**Checkpoint US5:** log del dogfood coerente con la rotazione.

---

## Phase 8: Polish & cross-cutting

**Purpose**: doc utente (host-facing), verifica idempotenza, gate pre-merge, rituale.

- [X] T026 [P] **Doc utente (FEAT-010)**: riga `.gitattributes` aggiunta alla capability-table di `docs/install.md` (host-root, create-if-absent, perché+cosa su Windows)
- [X] T027 **Idempotenza (NFR-1/C2)**: ri-eseguiti i 3 installer → `block:0` ovunque (0 blocchi duplicati), curati preservati; unico residuo = `?? wiki/log.md` dichiarato (FEAT-006)
- [X] T028 **Gate pre-merge (SC-5)**: root **1156** · sertor **492** · flow **142** · kit **151** · speclift **122** · specaudit **59** verdi; `ruff check .` clean; `sertor-core` invariato
- [X] T029 Roadmap aggiornata (riga E15 + FEAT-010 ✅ + FEAT-006 promossa); record delegato al `wiki-curator` (log 2026-07-06 + experiment page + index); distill/lint dichiarati dal flusso principale
- [~] T030 Commit delegato al `configuration-manager` (in corso). **PR + merge = conferma utente** (mai master diretto); post-merge: re-lock runtime → re-index → smoke MCP → EXEC roadmap

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
