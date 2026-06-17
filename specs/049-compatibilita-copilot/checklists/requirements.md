# Checklist di qualità — Specifica (requirements)

Feature: `049-compatibilita-copilot` · Spec: `specs/049-compatibilita-copilot/spec.md`
Iterazione: 1 (2026-06-17)

## Content Quality

- [x] **Valore utente, non implementazione** — la spec descrive COSA/PERCHÉ (hook che partono, contesto
  iniettato, comandi raggiungibili, claim onesti); evita di prescrivere il COME tecnico. Riferimenti a
  meccanismi (campo di versione di schema, tipo "prompt") sono **contratti del tool target** (vincoli di
  prodotto noti dall'audit), non scelte implementative interne; nessuno stack/API/codice Sertor è
  prescritto. **PASS**
- [x] **Linguaggio neutro rispetto allo stack** — descritto in italiano in termini di artefatti e contratti,
  senza nomi di classi/funzioni/file Sertor nel corpo normativo (ancorati solo come ground-truth audit e nei
  Nodi di design). **PASS**
- [x] **Niente dettagli implementativi prescrittivi** — il "come" (refactor del seam, parametro `-Assistant`
  concreto, struttura test) è demandato al plan; la spec fissa il contratto, non la realizzazione. **PASS**
- [x] **Orientata agli stakeholder** — owner/maintainer, team Copilot, suite di test come primo rilevatore.
  **PASS**

## Requirement Completeness

- [x] **Ogni REQ EARS della fonte è mappato** — i 28 REQ (gruppi A–H) + i 7 NFR sono coperti da FR-001..043
  (gruppi A–I); NFR-1/3/7 mappati su FR-040/041/042; il seam (vincolo architetturale) su FR-043. **PASS**
- [x] **Requisiti funzionali testabili** — ogni FR è verificabile (ispezione di artefatto, invocazione
  script, esecuzione test); molti hanno un test di schema dedicato (gruppo G). **PASS**
- [x] **Success criteria misurabili e tech-agnostici** — SC-001..011 esprimono soglie (100%/0%/almeno un
  test fallisce) senza riferimenti tecnologici interni. **PASS**
- [x] **Criterio CS-7 presente** — SC-007 codifica esplicitamente «i bug dell'audit avrebbero fatto fallire
  i test»: reintroduzione artificiale di ciascun difetto → almeno un test fallisce; suite offline. **PASS**
- [x] **Ambito in/out esplicito** — sezione Assumptions con fuori-ambito (smoke-test runtime, nuove
  superfici, backend, Codex, Copilot-come-LLM, PyPI) e perimetro `claude` invariato. **PASS**
- [x] **Edge case identificati** — 9 edge case (schema scartato, dual-field, pre-tool fail-closed, comando
  solo-prompt-file su CLI, modello Claude, stringa semplice, regressione Claude, schema in evoluzione, nuovo
  asset senza test). **PASS**
- [x] **Assunzioni documentate** — ground-truth audit, principio guida, Q1–Q6, A-1..A-4, fuori-ambito. **PASS**

## Decision Consistency

- [x] **Principio guida "nativo, niente hack" riflesso ovunque** — blocco vincolante in testa; FR-002/003
  (no campi Claude-only), FR-010 (no campo Claude come unico canale), FR-011 (no dual-field), FR-016/017
  (frontmatter nativo), FR-043 (seam), SC-008 (0 dual-field). **PASS**
- [x] **Q1 (avvio-sessione nativo per target)** → FR-006, US3, SC-003. **PASS**
- [x] **Q2 (piano comandi per-target)** → FR-013/014/015, US5, SC-004. **PASS**
- [x] **Q3 (stop non-bloccante)** → FR-007, US2 scenario 1, SC-002. **PASS**
- [x] **Q4 (script condiviso, output nativo per parametro, no dual-field)** → FR-011/012, US4, SC-008. **PASS**
- [x] **Q5 (verifica empirica MCP CLI inclusa)** → FR-020, US8 scenario 3. **PASS**
- [x] **Q6 (omettere modello Claude)** → FR-017, US6 scenario 2, SC-005. **PASS**
- [x] **FR-014 di FEAT-007 rilassato correttamente** — citato nel principio guida e in FR-011 (corpo
  condiviso, output nativo per assistente). **PASS**

## Nodi di design (non requisiti) segnalati, non risolti

- [x] **Meccanismo nativo avvio-sessione su Copilot VS Code** — segnalato come nodo di design in US3
  scenario 2 e nelle Assumptions; non risolto. **PASS**
- [x] **Eventuale revisione del seam profilo-assistente/superficie** — segnalata nelle Assumptions con la
  ground-truth (oggi il seam rende prompt-file per entrambi i target Copilot e copia il modello); non
  risolta. **PASS**

## Esito

**PASS** su tutte le voci alla iterazione 1. Nessun `[NEEDS CLARIFICATION]` residuo nella spec: le 6
decisioni Q1–Q6 sono chiuse a monte; restano due **nodi di design** (non ambiguità di cosa/perché) inoltrati
alla fase `plan`. Spec pronta per `/speckit-plan` (o `/speckit-clarify` se si vuole un giro extra sui nodi
di design, non necessario).
