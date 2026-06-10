---
title: Spec 010 — Query congiunta + upsert-index (FEAT-010, pezzi D residui Wiki)
type: experiment
tags: [feat-010, wiki, spec, specify, clarify, query-multi-collezione, upsert-index-cli]
created: 2026-06-10
updated: 2026-06-10
sources: [
  "specs/010-query-congiunta-e-upsert-index/spec.md",
  "requirements/sertor-core/query-congiunta-e-indice/requirements.md",
  "CLAUDE.md (Domande all'utente)"
]
---

# Spec FEAT-010 — Query Congiunta Multi-Collezione & `upsert-index` in CLI

Record datato (2026-06-10) della **specifica SpecKit** dei due **pezzi deterministici (D) residui della feature Wiki** (FEAT-003), consolidati in un'unica feature: la **query congiunta** e l'esposizione CLI di `upsert-index`.

## Contesto

FEAT-003 (epica `sertor-core`) ha tre pezzi: (1) query congiunta, (2) CLI `sertor wiki init`, (3) `upsert-index`. Pezzo (2) è diventato un'intera epica ("Sertor CLI"); pezzi (1) e (3) sono **deterministici** e dipendono solo dalla libreria core. Confluiscono in FEAT-010 con una spec SpecKit unica.

Requisiti a monte: [`requirements/sertor-core/query-congiunta-e-indice/requirements.md`](../../requirements/sertor-core/query-congiunta-e-indice/requirements.md) — 2 gruppi EARS (A query congiunta / B upsert-index), 7 requisiti, 3 NFR, 6 domande aperte gestite dal clarify.

## Fase: Specify + Clarify (completate 2026-06-10)

### Specify

- **User Story 1 (Priority P1):** Un consumatore interroga codice e wiki in una sola ricerca con `search_combined`, ricevendo risultati fusi ordinati per score.
  - Scope: **vero contenuto ingegneristico** della feature — il fan-out su due collezioni con merge top-k.
  - Accettanza: 5 scenari (due collezioni populate, wiki assente, entrambe assenti, single-collection regressione, osservabilità strutturata).
  
- **User Story 2 (Priority P2):** CLI expose `upsert_index()` come sottocomando, chiudendo il confine D↔N su indice.
  - Scope: piccolo, dipendenza nulla da US1.
  - Accettanza: 5 scenari (riga nuova, aggiornamento in place, idempotenza, wiki mancante, UTF-8 senza mojibake).

- **Edge case:** 7 scenari (Pertinenza concentrata, parità score, spazi vettoriali non confrontabili, newline in sommario, collezione wiki vuota, charset/locale, collezione pagina senza frontmatter).

### Clarify (4 decisioni dell'utente, Session 2026-06-10)

1. **Provider embeddings eterogenei** (Q: cosa accade se le due collezioni hanno spazi vettoriali non confrontabili?) 
   - **Risposta:** Errore esplicito + fail-fast. La fusione richiede lo **stesso provider**; con provider diversi, la ricerca combinata fallisce con errore esplicito. **Eccezione deliberata** alla policy tollerante della facade (`search_code/docs` sono tolleranti; `search_combined` è strict su questo).

2. **Individuazione seconda collezione**
   - **Risposta:** Da configurazione centrale (**`Settings`**). Una manopola dichiara i corpora aggiuntivi; il composition root cabla entrambe le collezioni. Consumatori **invariati** (thin-consumer pieno: «default solo in Settings»).

3. **Sommario multilinea a `upsert-index`**
   - **Risposta:** Errore esplicito + exit code non-zero, nessuna scrittura. No normalizzazione silenziosa; la CLI scrive sempre fedelmente (trim iniziale/finale resta scontato). *Decisione legata a [[deterministic-vs-judgment|confine deterministico-giudizio]]: giudizio dell'utente sulla forma, non riparazioni automatiche del deterministico.*

4. **Fan-out su due collezioni per `search_docs`?**
   - **Risposta:** NO. Il fan-out vale **solo per `search_combined`**. `search_code` e `search_docs` restano invariati (una collezione, filtro per tipo documento). Zero cambi di semantica per consumatori esistenti.

### Governance: Nuova regola in CLAUDE.md

**Sezione "Domande all'utente"** (introdotta nel clarify): ogni domanda all'utente va **preceduta dal contesto**:
- Origine del problema e implicazioni concrete delle opzioni.
- Raccomandazione motivata.

*(Richiesta esplicita durante il clarify per elevare la qualità delle domande nel flusso principale.)*

## Artefatti

- **Branch:** `010-query-congiunta-e-upsert-index` (produzione: branch+PR, niente push diretti su master).
- **Spec:** `specs/010-query-congiunta-e-upsert-index/spec.md` (SpecKit completo, 2 user story + edge case, 4 clarifications, checklists qualità).
- **Requisiti:** `requirements/sertor-core/query-congiunta-e-indice/requirements.md` (2 gruppi EARS, 7 requisiti, 3 NFR, 6 DA).

## Prossimo Step

**Plan** (fase SpecKit successiva) — decomposizione dei requisiti in story point, task, sequenza di implementazione, dipendenze, rischi. Nota: US1 è **blocco-critico** per la visione «una sola verità interrogabile»; US2 chiude il confine D↔N.

---

## Link correlati

- [[deterministic-vs-judgment]] — il confine che governa la decisione su sommario multilinea e fan-out.
- [[architettura-wiki-llm]] — la roadmap che colloca FEAT-010 nella visione d'insieme.
- [[retrieval-core]] — il nucleo che sarà esteso da questa feature.
- [[thin-consumer]] — il pattern di composizione che abilita il configuration-driven multi-collezione.
