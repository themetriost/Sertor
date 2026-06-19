# Implementation Plan: Distribuzione corretta della costituzione neutra + rifinitura principi

**Branch**: `058-distribuzione-costituzione` · **Spec**: `specs/058-distribuzione-costituzione/spec.md` ·
**Requirements**: `requirements/debito-tecnico/distribuzione-costituzione/requirements.md` (FEAT-009,
epica `debito-tecnico`).

## Summary

`sertor-flow install` deposita sull'ospite il **placeholder di spec-kit** invece dello starter neutro:
`specify init` (Step 0) crea `.specify/memory/constitution.md` placeholder, poi il nostro CONFIG
`CREATE_IF_ABSENT` (`_apply_config`) lo trova e fa **skip**. Fix = **replace-if-placeholder**: in
`_apply_config` (install) e nel ramo costituzione di `_apply_gov_upgrade` (upgrade), se il file esistente
è riconosciuto come placeholder spec-kit lo **sovrascriviamo** con lo starter; se è una costituzione
**reale** la **preserviamo**. Rilevamento deterministico via **sentinelle** del template (`[PROJECT_NAME]`,
`[PRINCIPLE_1_NAME]`, …). In più, **rifinitura** dello starter: due principi generici nuovi (interfacce
stabili; replaceable details) + allineamento leggibilità, versione bumpata. Guardia offline a prova di
regressione. `sertor-core` invariato; `sertor-flow` senza dipendenza dal core.

## Technical Context

- **Pacchetto toccato**: `sertor-flow` (solo). Eventuale sentinella condivisa resta locale (no nuova API kit).
  **`sertor-core` INVARIATO**; `sertor-flow` **non** dipende da `sertor-core`/`sertor` (NFR-03/guard AST).
- **Punti di codice**:
  - `packages/sertor-flow/src/sertor_flow/install_governance.py` — `_apply_config` (install) e
    `_apply_gov_upgrade` ramo costituzione (upgrade): introdurre la logica replace-if-placeholder via un
    helper condiviso `_apply_constitution(dest, starter_text)` + predicato `_is_speckit_placeholder(text)`.
  - `packages/sertor-flow/src/sertor_flow/assets/constitution-starter.md` — rifinitura contenuto +
    bump versione.
- **Asset/fixture**: il template placeholder reale è prodotto da `specify init`; per i test offline si usa
  una **fixture inline** del placeholder (sottoinsieme con le sentinelle) e una **fixture di costituzione
  reale** (es. una copia ridotta dello starter o un testo arbitrario senza sentinelle).
- **Test**: nuovo `packages/sertor-flow/tests/.../test_constitution_distribution.py` (o estensione di un
  test governance esistente): placeholder→starter, reale→preservata, sentinel test-of-test; le suite
  esistenti restano verdi.
- **Tooling**: `uv`; offline (NFR-04).

## Constitution Check (pre-design) — **PASS 11/11, nessuna deroga**

- **I (core libreria):** `sertor-core` non toccato; la feature vive in `sertor-flow`. ✅
- **II (provider dietro boundary):** n/a (nessun provider); la feature non introduce dipendenze esterne. ✅
- **III (YAGNI, unità piccole):** un helper puro `_is_speckit_placeholder` + un `_apply_constitution`
  condiviso fra install/upgrade (niente duplicazione). Nessuna nuova astrazione/ArtifactKind. ✅
- **IV (errori espliciti):** gli apply ritornano `ArtifactOutcome` espliciti (CREATED/UPDATED/SKIPPED con
  detail); nessun null silenzioso; nessuno stato parziale. ✅
- **V (testabilità da misure):** guardia offline deterministica con fixture (placeholder/reale) + SC
  misurabili. ✅
- **VI (idempotenza, non-distruttività):** **cuore della feature** — replace-if-placeholder è
  **non-distruttivo** verso una costituzione reale (preservata) e **idempotente** (ri-eseguire su uno
  starter già depositato non cambia nulla). ✅
- **VII (leggibilità):** helper piccoli e nominati; lo starter stesso migliora in chiarezza. ✅
- **VIII (config centralizzata):** n/a (nessuna nuova manopola). ✅
- **IX (osservabilità):** l'esito (placeholder sostituito vs preservato) è esplicito nell'`install.report`
  (outcome+detail), diagnosticabile senza leggere il codice. ✅
- **X (host-agnostico):** la feature **realizza** il Principio X: garantisce che l'artefatto neutro
  host-agnostico (lo starter) **arrivi davvero** sull'ospite invece del placeholder. ✅
- **XI (consumo via vehicles):** install-time, non runtime-library; nessun accesso diretto al core. ✅

## Phase 1 — Design

**Data model:** nessuna entità nuova. Concetti: *starter neutro*, *placeholder spec-kit*, *costituzione
reale*, *sentinella di placeholder*.

**Algoritmo (replace-if-placeholder), in `_apply_constitution(dest, starter)`:**
1. Se `dest` **non esiste** → scrivi `starter` → `CREATED` ("constitution starter").
2. Se `dest` esiste e `_is_speckit_placeholder(dest.read_text())`:
   - se il contenuto è già == `starter` → `SKIPPED` ("starter already present") *(difensivo/idempotente)*;
   - altrimenti scrivi `starter` → `UPDATED` ("replaced spec-kit placeholder with neutral starter").
3. Altrimenti (costituzione reale) → `SKIPPED` ("host constitution preserved").

`_is_speckit_placeholder(text)` = `any(s in text for s in _SPECKIT_PLACEHOLDER_SENTINELS)` con
`_SPECKIT_PLACEHOLDER_SENTINELS = ("[PROJECT_NAME]", "[PRINCIPLE_1_NAME]", "[CONSTITUTION_VERSION]")` —
marcatori del template upstream **assenti** in qualunque costituzione reale o nello starter. Fail-safe:
in dubbio (nessuna sentinella) si **preserva** (Principio VI).

**Aggancio:**
- **install** — `_apply_config` chiama `_apply_constitution` (gira nel piano, **dopo** `specify init`).
- **upgrade** — il ramo `CONFIG/CREATE_IF_ABSENT` di `_apply_gov_upgrade` chiama `_apply_constitution`
  invece di ritornare sempre `SKIPPED "preserved"` (così un host fermo al placeholder si ripara con
  l'upgrade; una costituzione reale resta preservata). `dry_run` → proietta l'outcome senza scrivere.
- **uninstall** — invariato: la costituzione è **preservata** (una volta data all'ospite è sua).

**Rifinitura starter (`constitution-starter.md`):** riscrittura del contenuto a **10 principi** (gli 8
attuali + 2 nuovi) mantenendo lo stile e la nota d'intestazione:
- **+ «Replaceable Details / No Vendor Lock-In»** (kernel del Principio II di Sertor): dipendenze esterne
  dietro boundary, scelta per configurazione, nessun tipo di terze parti nel dominio.
- **+ «Consume Through Stable Interfaces, Not Internals»** (generalizzazione del Principio XI): i
  consumatori usano l'API/CLI pubblica, non gli interni; gli interni restano liberi di cambiare.
- allineamento del principio di leggibilità (guard-clause/early-return; SESE non richiesto).
- versione **0.1.0 → 0.2.0**; restano esclusi i principi Sertor/RAG-specifici (X, veicoli, motori RAG).

**Contratti:** nessun contratto runtime nuovo; la "guardia di distribuzione" è un test.

**Quickstart (verifica E2E):** install governance in dir temp con un `.specify/memory/constitution.md`
placeholder pre-creato (simula `specify init`) → atteso = starter neutro; ripeti con una costituzione
reale → atteso = preservata; install pulito reale → starter neutro (CS-005).

## Fasi di implementazione (mappate alle user story)

1. **US1 (P1) — distribuzione corretta:** `_is_speckit_placeholder` + `_apply_constitution`; aggancio in
   `_apply_config` (install) e `_apply_gov_upgrade` (upgrade). 
2. **US2 (P2) — rifinitura starter:** riscrittura `constitution-starter.md` (2 principi nuovi, allineamento
   VII, bump versione).
3. **US3 (P2) — guardia:** test offline (placeholder→starter, reale→preservata, sentinel test-of-test);
   verifica non-regressione (`sertor-flow`/`kit`/`sertor`, guard no-dipendenza-core).
4. **Verifica empirica:** install pulito in dir temp (CS-005) + (opzionale) re-install su Spike.

## Constitution Check (post-design) — **PASS 11/11, nessuna deroga**

Il design non introduce nuovi `ArtifactKind`/`Surface`, non tocca `sertor-core`, non aggiunge dipendenze,
ed è il **veicolo** del Principio X (l'artefatto host-agnostico arriva davvero) + rispetta VI
(non-distruttività verso le costituzioni reali). Nessuna complessità da tracciare.

## Complexity Tracking

Nessuna deviazione costituzionale. Rischio residuo (non costituzionale): rilevamento legato al formato dei
placeholder spec-kit (R-2) → mitigato da sentinelle multiple + guardia che fallisce se il template
vendorato cambia forma.
