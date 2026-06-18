# Checklist di qualità della specifica — `056-parita-asset-copilot`

**Spec**: `specs/056-parita-asset-copilot/spec.md`
**Feature**: FEAT-001 (epica `debito-tecnico`) — parità funzionale completa su Copilot CLI + governance dual-target
**Data validazione**: 2026-06-18
**Iterazione**: 1

> Legenda: PASS = soddisfatto · FAIL = non soddisfatto · N/A = non applicabile.

## A. Orientamento al valore (COSA/PERCHÉ, niente COME)

- [x] **A1** — La spec descrive bisogni utente e risultati, non scelte implementative. **PASS** (si parla
  di "payload di supporto", "container del payload", "body host-agnostico", "guardia di parità",
  "closure dei riferimenti" come artefatti/comportamenti, non come simboli di codice).
- [x] **A2** — Ogni user story ha un *Why this priority*. **PASS** (5 storie, tutte motivate).
- [x] **A3** — Nessun riferimento a stack/API/codice nei requisiti funzionali. **PASS** (es. "enumerazione
  dinamica della fonte unica" anziché `iter_asset_dir`; "container dedicato non-agente" descritto come
  comportamento; il path `.github/sertor/` compare solo nel confine vincolante e negli Assumptions come
  decisione, non come dettaglio dei FR).

## B. Requisiti funzionali testabili

- [x] **B1** — Ogni FR è verificabile in modo binario. **PASS** (19 FR, ciascuno con esito osservabile:
  presenza/assenza di file, assenza di stringa, byte-identità, fallimento di un controllo).
- [x] **B2** — Le condizioni EARS sono coerenti. **PASS** (derivano dai REQ EARS della fonte; gli
  event-driven sono espressi con "Quando…", gli unwanted con "SE… ALLORA…").
- [x] **B3** — Nessun requisito ambiguo lasciato implicito. **PASS** ("byte-identico", "closure", "per
  nome di file", "0 occorrenze" sono definiti).
- [x] **B4** — Copertura completa dei 19 REQ della fonte. **PASS** (mappatura 1:1 — sezione F).

## C. Criteri di successo misurabili e tech-agnostici

- [x] **C1** — Ogni SC è misurabile (conteggio/presenza/byte-identità). **PASS** (gli SC usano "0 casi",
  "tutti i moduli", "riesce", "byte-identici").
- [x] **C2** — Gli SC non menzionano tecnologie/implementazione. **PASS** (parlano di file resi,
  artefatti, container, prima azione dell'agente).
- [x] **C3** — Gli SC coprono i criteri di successo della fonte (CS-1…CS-8). **PASS** (CS-1→SC-001,
  CS-2→SC-002, CS-3→SC-003, CS-4→SC-004, CS-5→SC-005, CS-6→SC-006, CS-7→SC-007, CS-8→SC-008).

## D. Scenari utente e accettazione

- [x] **D1** — Ogni user story ha *Acceptance Scenarios* Given/When/Then. **PASS** (5 storie, 2-3 scenari
  ciascuna).
- [x] **D2** — Ogni user story ha un *Independent Test* eseguibile in isolamento. **PASS**.
- [x] **D3** — Gli *Edge Cases* coprono i rischi della fonte (R1–R4) + le tensioni di design. **PASS**
  (byte-identico vs path diversi, frontmatter nei supporti, falso positivo slash, dangling, container
  agent-discovery, host già installato, divieto di traduzione per-target).
- [x] **D4** — Le priorità (P1/P2/P3) sono coerenti col MoSCoW della fonte. **PASS** (US1/US2 = P1 ⊇ i
  Must core; US3/US4 = P2 (full sweep + guardia); US5 = P3 (governance, Should)).

## E. Entità, ipotesi, ambito

- [x] **E1** — Le *Key Entities* sono concettuali. **PASS** (payload, container, body host-agnostico,
  riferimento-per-nome, guardia, closure, sedi di governance).
- [x] **E2** — Le *Assumptions* dichiarano le decisioni D1–D6/Q1–Q5 e i `[ASSUNTO]` aperti. **PASS**
  (D1–D6 codificate; A-1..A-4 marcati `[ASSUNTO]`, incl. il rischio container `.github/sertor/`).
- [x] **E3** — *In/Out of scope* esplicito e coerente con la fonte. **PASS** (fuori ambito: commenti
  "Claude Code" negli .ps1, rename copilot, promozione derive-entity-types, payload RAG residui).
- [x] **E4** — Gli "Out of Scope" che sono capacità future hanno casa durevole. **PASS** (rename →
  E10-FEAT-007; promozione derive-entity-types → backlog separato già concordato; payload RAG → stessa
  FEAT-001 se trovati — nessun rinvio orfano introdotto).

## F. Tracciabilità fonte → spec (19 REQ + 7 NFR + 8 CS)

- [x] **F1** — REQ-001..004 (deposito payload) → FR-001..004 / US1 / SC-001,006. **PASS**
- [x] **F2** — REQ-005..009 (neutralizzazione body) → FR-005..009 / US2,US3 / SC-002,003,005. **PASS**
- [x] **F3** — REQ-010..014 (guardia + closure) → FR-010..014 / US4 / SC-004. **PASS**
- [x] **F4** — REQ-015..018 (governance dual-target + ri-sync) → FR-015..018 / US5 / SC-007. **PASS**
- [x] **F5** — REQ-019 (non-regressione) → FR-019 / US1,US4 / SC-005. **PASS**
- [x] **F6** — NFR-01..07 (Claude invariato, no nuovi Surface/ArtifactKind, sertor-flow no-core,
  install≠run, guardia offline, byte-identica verde, upgrade per host esistenti) → Assumptions +
  Confine + SC-005 + Edge Cases. **PASS**
- [x] **F7** — CS-1..CS-8 → SC-001..SC-008 (incl. CS-8 empirico Spike = SC-008). **PASS**

## G. Decisioni chiuse non riaperte

- [x] **G1** — La spec non riapre D1–D6/Q1–Q5 e non introduce domande di scope nuove. **PASS** (codificate
  come vincoli; le aperture residue sono esplicitamente di *come* → `/speckit-plan`).

---

## Esito complessivo: **PASS** (22/22 voci, 0 FAIL, 0 N/A)

Nessun `[NEEDS CLARIFICATION]`: le decisioni di scope (D1–D6, Q1–Q5) sono risolte a monte e codificate.
Le aperture residue sono ambiguità di *come* (forma del riferimento-per-nome, collocazione del container
e del loop di deposito, regex anti-slash della guardia, collocazione delle tre sedi di governance) — di
pertinenza di `/speckit-plan`.
