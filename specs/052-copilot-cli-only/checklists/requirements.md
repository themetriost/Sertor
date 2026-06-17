# Checklist di qualità della specifica — `052-copilot-cli-only`

**Spec**: `specs/052-copilot-cli-only/spec.md`
**Feature**: FEAT-012 (epica `sertor-cli`) — consolidamento Copilot CLI-only
**Data validazione**: 2026-06-17
**Iterazione**: 1

> Legenda: PASS = soddisfatto · FAIL = non soddisfatto · N/A = non applicabile.

## A. Orientamento al valore (COSA/PERCHÉ, niente COME)

- [x] **A1** — La spec descrive bisogni utente e risultati, non scelte implementative. **PASS**
  (nessun nome di classe/funzione/file di codice nei requisiti; si parla di "enumerazione degli
  assistenti", "profilo di assistente", "veicolo dei comandi", "file di configurazione MCP" in termini
  di artefatto/comportamento, non di simbolo di codice).
- [x] **A2** — Ogni user story ha un *Why this priority* che motiva il valore. **PASS** (7 storie, tutte
  con razionale).
- [x] **A3** — Nessun riferimento a stack/API/codice nei requisiti funzionali. **PASS**
  (es. "file di configurazione MCP in formato VS Code" anziché `.vscode/mcp.json`; "argomento di
  assistente upstream `copilot`" anziché `--ai copilot` come flag implementativo — il valore stringa è
  parte del contratto upstream, non un dettaglio interno).

## B. Requisiti funzionali testabili

- [x] **B1** — Ogni FR è verificabile in modo binario. **PASS** (22 FR, ciascuno con esito osservabile:
  errore esplicito, presenza/assenza di artefatto, identità degli artefatti, valore upstream).
- [x] **B2** — Le condizioni EARS (When/If/Where/Ubiquitous) sono coerenti. **PASS** (i FR derivano dai
  REQ EARS della fonte; gli event-driven sono espressi con "Quando…").
- [x] **B3** — Nessun requisito ambiguo o non misurabile lasciato implicito. **PASS** (i confini "un
  solo target", "errore esplicito", "identici" sono definiti).
- [x] **B4** — Copertura completa dei 22 REQ della fonte. **PASS** (mappatura 1:1 — vedi sezione F).

## C. Criteri di successo misurabili e tech-agnostici

- [x] **C1** — Ogni SC è misurabile (conteggio/identità/presenza), non vago. **PASS** (SC usano "0
  casi", "esattamente `claude|copilot-cli`", "identici", "un unico punto").
- [x] **C2** — Gli SC non menzionano tecnologie/implementazione. **PASS** (parlano di artefatti,
  comandi, valori, documentazione — non di file/classi specifici).
- [x] **C3** — Gli SC coprono tutti i criteri di successo della fonte (CS-1…CS-6). **PASS** (CS-1→SC-001,
  CS-2→SC-002, CS-3→SC-003, CS-4→SC-005, CS-5→SC-006, CS-6→SC-009; aggiunti SC-004/007/008/010 per
  artefatti VS Code, idempotenza, copertura test, anti-drift/core).

## D. Scenari utente e accettazione

- [x] **D1** — Ogni user story ha *Acceptance Scenarios* in forma Given/When/Then. **PASS** (7 storie,
  2-3 scenari ciascuna).
- [x] **D2** — Ogni user story ha un *Independent Test* eseguibile in isolamento. **PASS**.
- [x] **D3** — Gli *Edge Cases* coprono i rischi della fonte (R-01…R-04). **PASS** (rottura silente VS
  Code, mapping incompleto, test rimossi senza equivalente, layout-check non aggiornato — tutti presenti
  + il divieto di codice morto/alias).
- [x] **D4** — Le priorità (P1/P2) sono assegnate e coerenti col MoSCoW della fonte. **PASS** (Story
  1-5 = P1 ⊇ i Must; Story 6 migrazione = P2 (REQ-022 Could→narrato come P2); Story 7 doc = P2 (REQ
  Should)).

## E. Entità, ipotesi, ambito

- [x] **E1** — Le *Key Entities* sono concettuali (no schemi di dati implementativi). **PASS**.
- [x] **E2** — Le *Assumptions* dichiarano le decisioni Q1–Q4 e i `[ASSUNTO]` aperti. **PASS** (Q1–Q4
  codificate; A-1/A-2/A-3 marcati `[ASSUNTO]`).
- [x] **E3** — *In/Out of scope* esplicito e coerente con la fonte. **PASS** (fuori ambito: VS Code
  futuro, nuovi assistenti, Codex, migrazione automatica, `sertor-rag check`, runtime core).
- [x] **E4** — Gli "Out of Scope" che sono capacità future hanno una casa durevole. **PASS** (VS Code
  futuro = eventuale nuova feature; `sertor-rag check` = FEAT-003; provider/store = epica core — tutti
  già citati, nessun rinvio orfano introdotto da questa spec).

## F. Tracciabilità fonte → spec (22 REQ + 6 NFR + 6 CS)

- [x] **F1** — REQ-001..004 (rimozione VS Code) → FR-001..004 / Story 1 / SC-001,004. **PASS**
- [x] **F2** — REQ-005..008 (naming uniforme) → FR-005..008 / Story 2 / SC-002. **PASS**
- [x] **F3** — REQ-009..012 (skill requirements) → FR-009..012 / Story 3 / SC-003. **PASS**
- [x] **F4** — REQ-013..015 (mapping upstream) → FR-013..015 / Story 4 / SC-006,007. **PASS**
- [x] **F5** — REQ-016..019 (non-regressione + test) → FR-016..019 / Story 5 / SC-005,008. **PASS**
- [x] **F6** — REQ-020..022 (doc + migrazione) → FR-020..022 / Story 6,7 / SC-009. **PASS**
- [x] **F7** — NFR-01..06 (non-distruttività, breaking esplicita, core invariato, anti-drift, test
  offline, idempotenza) → Assumptions + SC-005/007/010 + Story 4/5. **PASS**

## G. Decisioni chiuse non riaperte

- [x] **G1** — La spec non riapre Q1–Q4 e non introduce domande di scope nuove. **PASS** (le decisioni
  sono codificate come vincoli; le aperture residue sono esplicitamente di *come* → `/speckit-plan`).

---

## Esito complessivo: **PASS** (24/24 voci, 0 FAIL, 0 N/A)

Nessun `[NEEDS CLARIFICATION]`: le 4 domande di scope (Q1–Q4) sono risolte a monte e codificate. Le
aperture residue sono ambiguità di *come* (forma della rimozione, punto del mapping, aggiornamento del
layout-check, sostituzione dei test, collocazione della nota) — di pertinenza di `/speckit-plan`, non
della fase specify.
