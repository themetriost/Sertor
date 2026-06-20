# Checklist di qualità — Specifica (requirements)

Feature: `065-ground-truth-valutazione` · Spec: `specs/065-ground-truth-valutazione/spec.md`
Iterazione: 1 (2026-06-20)

## Content Quality

- [x] **Valore utente, non implementazione** — la spec descrive COSA/PERCHÉ (misurare la pertinenza,
  presidiare la non-regressione, creare/raffinare la suite); i riferimenti a `evaluate`/`EvalReport`/
  fixture sono **ancoraggi** all'esistente esplicitamente marcati «dato di partenza, non dettaglio da
  progettare», non prescrizioni implementative. Il *come* (formato, comandi, schema) è demandato al plan.
  **PASS**
- [x] **Linguaggio neutro rispetto allo stack** — corpo normativo in italiano in termini di artefatti
  (suite, riferimento, report) e contratti; nessuno stack/API/codice Sertor prescritto nei requisiti.
  **PASS**
- [x] **Niente dettagli implementativi prescrittivi** — formato file (TOML/JSON), nomi comandi (`sertor-rag
  eval`), schema, skill-vs-estensione sono **forche di design** esplicitamente rinviate, non decise.
  **PASS**
- [x] **Orientata agli stakeholder** — owner/maintainer dell'ospite, agente LLM (beneficiario+strumento),
  il core (fornitore della misura), epica osservabilità (consumatore a valle). **PASS**

## Requirement Completeness

- [x] **Ogni REQ EARS della fonte è mappato** — i 7 gruppi A–G (REQ-001..062) e RNF-1..6 sono coperti dalla
  sezione Requirements (mappatura per gruppo con REQ citati) e dagli SC. **PASS**
- [x] **Requisiti funzionali testabili** — ogni User Story porta un *Independent Test* e Acceptance
  Given/When/Then verificabili (esecuzione comando, ispezione artefatto, sessione skill). **PASS**
- [x] **Success criteria misurabili e tech-agnostici** — SC-001..010 esprimono esiti osservabili (metriche
  identiche tra run, exit non-zero sul degrado, suite non vuota, 0 import del codice di test) senza
  riferimenti tecnologici interni. **PASS**
- [x] **Ambito in/out esplicito** — sezione *Fuori ambito* con FEAT-002/003/004/005/006/007 e osservabilità
  FEAT-009, più il rinvio del *come* al design; *In ambito* implicito nelle 5 User Story. **PASS**
- [x] **Edge case identificati** — 7 edge case (path inesistente→conferma, rebase root, idempotenza,
  suite assente, segreti, generazione senza indice, determinismo). **PASS**
- [x] **Assunzioni documentate** — indice presente, «LLM»=agente via skill, riuso dell'esistente,
  dipendenza installer, FEAT-018, confine osservabilità. **PASS**

## Decision Consistency

- [x] **Chiarimento terminologico «LLM» = agente via skill riflesso ovunque** — blocco vincolante in testa;
  US2 scenario 4, REQ-023, RNF-4, SC-006 e Assumptions lo ribadiscono (core/CLI non chiama mai un LLM).
  **PASS**
- [x] **Confine D↔N coerente** — run deterministico via vehicle (US1, REQ-031, SC-006) vs genesi/feedback =
  giudizio skill (US2/US3, REQ-023/051); non si mescolano. **PASS**
- [x] **Principio XI (run via vehicle, no engine fuori test)** → REQ-031, SC-006, blocco confine. **PASS**
- [x] **Principio X + «installabile su ospite»** → US5, REQ-060/061, SC-002/008. **PASS**
- [x] **Additività Principi I/III (a leve spente, comportamento+costo identici)** → US5 scenario 3,
  REQ-062, RNF-2, SC-009. **PASS**
- [x] **Local-first, cloud fuori ambito** → blocco additività, US4/SC-007 (confronto locale), Fuori ambito
  FEAT-002. **PASS**
- [x] **MoSCoW riflesso nelle priorità delle User Story** — P1=Must (US1 run/non-regressione/metriche +
  US5 host/installabile), P2=Should (US2 genesi assistita→FEAT-008, US4 confronto 2 config), P3=Should
  (US3 feedback→FEAT-009); ogni US è testabile indipendentemente. **PASS**
- [x] **Ancoraggio all'esistente come promozione, non reinvenzione** — `evaluate`/`EvalReport`/
  `QueryableEngine`, fixture `ground_truth.py`, `test_baseline_quality.py` citati come dato di partenza in
  testa e nelle Key Entities/Assumptions. **PASS**
- [x] **Tracciamento scope (Out-of-Scope promossi)** — Gruppi C/F promossi a FEAT-008/FEAT-009 nel backlog
  d'epica, nota esplicita nella spec. **PASS**

## Forche di design (non requisiti) segnalate, non risolte

- [x] **DA-a formato artefatto (TOML/JSON/YAML)** — segnalata, non risolta. **PASS**
- [x] **DA-b riferimento non-regressione (baseline-file vs soglia assoluta)** — segnalata, non risolta. **PASS**
- [x] **DA-c genesi assistita (skill nuova vs estende `derive-entity-types`)** — segnalata, non risolta. **PASS**
- [x] **DA-d superficie comando (CLI run vs skill authoring)** — segnalata, non risolta. **PASS**
- [x] **DA-e validazione `expected_path` contro l'indice** — segnalata, non risolta. **PASS**

## Esito

**PASS** su tutte le voci alla iterazione 1. Nessun `[NEEDS CLARIFICATION]` residuo nella spec: le scelte
critiche di scope/sicurezza/UX hanno default ragionevoli documentati (Assumptions); le 5 forche aperte sono
**questioni di design** (come), non ambiguità di cosa/perché, inoltrate a `plan`. Spec pronta per
`/speckit-plan` (o `/speckit-clarify` se si vuole un giro extra sulle forche di design — non necessario per
procedere).
