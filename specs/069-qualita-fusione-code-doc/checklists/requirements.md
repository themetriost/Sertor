# Checklist di qualità — Specifica (requirements)

Feature: `069-qualita-fusione-code-doc` · Spec: `specs/069-qualita-fusione-code-doc/spec.md`
Iterazione: 1 (2026-06-21)

## Content Quality

- [x] **Valore utente, non implementazione** — la spec descrive COSA/PERCHÉ (misurare onestamente la
  fusione code+doc su query NL, presidiare la non-regressione per-superficie, scegliere le leve solo coi
  numeri); i riferimenti a `evaluate`/`EvalReport`/`services/eval`/`search_*`/`hybrid.py` sono
  **ancoraggi** all'esistente, marcati «dato di partenza, non dettaglio da progettare». Il *come*
  (quale leva, schema, soglie esatte, struttura) è demandato al plan. **PASS**
- [x] **Linguaggio neutro rispetto allo stack** — corpo normativo in termini di artefatti (set NL,
  baseline per-superficie, fusion coverage, report) e di intenti; nessuno SDK/API/codice prescritto nei
  requisiti. **PASS**
- [x] **Niente dettagli implementativi prescrittivi** — quale tecnica/leva, schema dell'artefatto, nomi
  di comando/manopola, formula delle soglie di «miglioramento» sono **forche di design** rinviate, non
  decise. **PASS**
- [x] **Orientata agli stakeholder** — owner/maintainer (vuole doc+codice fusi e un numero a riprova),
  agente LLM consumatore via MCP (beneficiario + strumento di genesi), la suite di valutazione
  (strumento esteso). **PASS**

## Requirement Completeness

- [x] **Ogni REQ EARS della fonte è mappato** — i gruppi A–E (REQ-001..043) e RNF-1..5 sono coperti dalla
  sezione Requirements (mappatura per gruppo con REQ citati) e dagli SC. **PASS**
- [x] **Requisiti funzionali testabili** — ogni User Story porta un *Independent Test* e Acceptance
  Given/When/Then verificabili (misura ripetuta = numeri identici; caso fusione hit@k ma miss su fusion
  coverage; gate exit non-zero sul degrado per-superficie; leva senza lift = non adottata). **PASS**
- [x] **Success criteria misurabili e tech-agnostici** — SC-001..011 esprimono esiti osservabili (set
  intent-typed esistente, baseline distinte registrate, fusion coverage accanto alle metriche, numeri
  identici tra run, exit non-zero sul degrado, delta per-superficie) senza riferimenti tecnologici
  prescrittivi. **PASS**
- [x] **Ambito in/out esplicito** — sezione *Fuori ambito* con FEAT-002/004/005/006/007 e il rinvio del
  *come* al design; *In ambito* nelle 5 User Story (misura, baseline, leve opt-in, miglioramento
  per-superficie, genesi assistita). **PASS**
- [x] **Edge case identificati** — 7 edge case (query NL senza atteso d'intento → esclusa; hit@k ma miss
  fusion; leva che rompe la fusione; leva troppo costosa; overfitting/hold-out; determinismo;
  casi/baseline esistenti protetti). **PASS**
- [x] **Assunzioni documentate** — indice presente, «LLM»=agente via skill, riuso/estensione
  dell'esistente, fasatura empirica (misura prima delle leve), dipendenza installer. **PASS**

## Decision Consistency

- [x] **Decisioni di prodotto già prese riflesse e non riaperte** — P1.c (baseline+miglioramento
  per-superficie, combined come integrazione) → US2/US4, REQ-010/013, SC-002/005; P2.b (fusion coverage
  ≥1 doc E ≥1 source, accanto a hit@k/MRR) → US1, gruppo C, SC-003; P3.a (categoria dedicata
  cross-artefatto, expected intent-typed) → gruppo A, Key Entities, SC-001. **PASS**
- [x] **Natura empirica / ordine di valore esplicito** — blocco vincolante in testa + Assumptions
  «fasatura empirica»: il Must è l'infrastruttura di misura; le leve (Should) si scelgono **dopo** le
  baseline; «migliorare» = misura → confronto → adotta solo ciò che mostra lift (US3, REQ-031/014). **PASS**
- [x] **Confine D↔N coerente** — run deterministico via vehicle, nessun LLM oltre l'embedder (blocco
  confine, REQ-041/042/043, SC-004/008) vs genesi set/giudizio leva = skill/utente (US5, REQ-043,
  US3). **PASS**
- [x] **Principio II local-first / RNF-3** → blocco additività, REQ-041, SC-004/009; cloud fuori ambito
  (FEAT-002). **PASS**
- [x] **Principio V misurabilità («nessun migliore senza numero»)** → REQ-014, RNF-2, SC-006, US3
  scenario 2. **PASS**
- [x] **Principio XI (misura via vehicle `sertor-rag eval`)** → REQ-042, SC-008, blocco confine. **PASS**
- [x] **Additività Principi I/III (a leve spente, comportamento+costo identici)** → REQ-030, RNF-1,
  SC-009, US3 scenario 3. **PASS**
- [x] **Gate «Allineamento alla missione» v1.4.0 (rafforza la fusione code+doc)** → blocco stella polare
  in testa, RNF-4, SC-011 (caso requisito→implementazione misurato come coperto). **PASS**
- [x] **MoSCoW riflesso nelle priorità delle User Story** — P1=Must (US1 set+fusion coverage+misura,
  US2 baseline per-superficie+gate+combined integrazione); P2=Should (US3 leve guidate-da-misura, US4
  miglioramento effettivo per-superficie, US5 genesi assistita); ogni US è testabile indipendentemente.
  **PASS**
- [x] **Ancoraggio all'esistente come estensione, non reinvenzione** — harness FEAT-001/011, `services/
  eval/`, `eval/suite.toml`, `search_code/docs/combined`, `hybrid.py` citati come dato di partenza;
  fusion coverage e categoria fusione marcate **additive**. **PASS**
- [x] **Tracciamento scope (Out-of-Scope promossi)** — tecniche avanzate già FEAT-005/006/007 nel
  backlog d'epica; hold-out tracciato come Could nei requisiti; nota esplicita nella spec. **PASS**

## Forche di design (non requisiti) segnalate, non risolte

- [x] **DA-a quali leve per prime** — segnalata, non risolta (design, decisa dai numeri). **PASS**
- [x] **DA-b costruzione del set NL** (numerosità, etichettatura intento/«needs both», hold-out) —
  segnalata, non risolta. **PASS**
- [x] **DA-c soglie di «miglioramento»** (delta minimo / soglia fusion coverage) — segnalata; il
  principio (nessun migliore senza numero) è requisito, le costanti sono design. **PASS**
- [x] **DA-d rapporto con FEAT-004/005/006/007** — segnalata, non risolta. **PASS**
- [x] **DA-e valore single-shot vs pattern agentico** — segnalata; chiarito che non cambia lo scope Must.
  **PASS**

## Esito

**PASS** su tutte le voci alla iterazione 1. Nessun `[NEEDS CLARIFICATION]` di scope residuo: le
decisioni di prodotto critiche (P1.c per-superficie, P2.b fusion coverage, P3.a categoria intent-typed,
leve opt-in additive scelte per misura, gate/local-first/vehicle) sono **già prese** nei requisiti e
riflesse nella spec. Le 5 forche aperte (DA-a..e) sono **questioni di design** (come), non ambiguità di
cosa/perché, e **nessuna cambia lo scope**: inoltrate a `plan`. Spec pronta per `/speckit-plan` (o
`/speckit-clarify` per un giro extra sulle forche — non necessario per procedere).
