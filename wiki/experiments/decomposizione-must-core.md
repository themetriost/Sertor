---
title: Decomposizione dei Must di sertor-core + decisioni di ambito MVP
type: experiment
tags: [requisiti, sertor-core, decomposizione, mvp, ears]
created: 2026-05-31
updated: 2026-05-31
sources: ["requirements/sertor-core/epic.md", "requirements/sertor-core/nucleo-retrieval/requirements.md", "requirements/sertor-core/rag-baseline/requirements.md", "requirements/sertor-core/wiki-creazione/requirements.md"]
---

# Decomposizione dei Must di sertor-core + decisioni di ambito MVP

## Cosa

Decomposte le 3 feature **Must** dell'epica primaria [[epiche-sertor-core-e-cli|sertor-core]] in documenti di requisiti EARS, ancorati al prototipo via il [[chiusura-prototipo-dogfooding|RAG di dogfooding]]:

### FEAT-001: Nucleo di retrieval
**File:** `requirements/sertor-core/nucleo-retrieval/requirements.md`  
**Scope:** 32 REQ + 8 NFR  
**Descrizione:** Nucleo condiviso dalle capacità RAG:
- Ingestione **repo-agnostica** (layout arbitrario, estensioni note, fallback testuale)
- Chunking **code-aware** (14 linguaggi MVP + fallback)
- Embeddings **multi-provider** (locale Ollama, Azure OpenAI)
- Astrazione **vector store** (Chroma locale, Azure AI Search, Cosmos DB for NoSQL)
- Facade di **retrieval unificato** (query vettoriale, ibrido, similarity)
- Metadata + iterabilità (indici, store, corpus)

### FEAT-002: RAG baseline (vettoriale)
**File:** `requirements/sertor-core/rag-baseline/requirements.md`  
**Scope:** 16 REQ + 8 NFR  
**Descrizione:** Motore RAG vettoriale per la line-of-business:
- Indicizzazione sorgenti su vector store (via FEAT-001)
- Query vettoriale + ranking di similarità
- Valutazione pertinenza (groundedness, relevance scoring)
- Dipendenza su FEAT-001 per l'astrazione di storage e embeddings

### FEAT-003: Wiki — creazione e indicizzazione
**File:** `requirements/sertor-core/wiki-creazione/requirements.md`  
**Scope:** 26 REQ + 7 NFR  
**Descrizione:** Skill LLM di creazione e manutenzione wiki:
- Invocazione via brief umano (agente LLM riceve input condensato)
- Distillazione wiki: record, ingest, query, lint, syntheses
- Indicizzazione nel RAG (via FEAT-001/002)
- Struttura directory fissa (concepts/, tech/, experiments/, sources/, syntheses/)
- Dipendenza su FEAT-001 per indicizzazione post-creazione
- **Perimetro MVP vincolato da [[wiki-role-da-w1|DA-W1/DA-2]]:** creare + indicizzare; niente spider/superficie nativa

---

## Decisioni di ambito MVP (elicitazione 2026-05-31)

### 1. Chunking multilinguaggio da subito

**Set MVP di 14 linguaggi:** Python, JavaScript/TypeScript, Java, C#, Go, C/C++, PHP, Ruby, PowerShell, Bash, T-SQL, PL/SQL.

**Razionale:** non differire il supporto dei linguaggi al post-MVP. Incalzato da requisito [[epiche-sertor-core-e-cli|sertor-cli]] (agnosticità di corpus).

**Estensibilità:** fallback testuale per gli altri; set incrementabile post-MVP senza riprogettazione (pattern plugin in `chunking.py`).

**FEAT-001 REQ-011.**

### 2. Full re-index nell'MVP (idempotente)

**Decisione:** l'MVP esegue un **full re-index** dell'indice sorgenti a ogni invocazione. Aggiornamento **incrementale** rinviato a **manutenzione post-MVP**.

**Razionale:** 
- Semplicità logica (niente tracciamento delta).
- Idempotenza garantita.
- Corpus MVP piccolo (accettabile in tempo).

**Conseguenza:** nuova feature **FEAT-009 — Manutenzione/refresh incrementale dell'indice RAG sui sorgenti** (Could, backlog §8), pendant per i sorgenti di FEAT-007 (manutenzione del wiki post-MVP).

**Nota wiki:** la distillazione wiki (FEAT-003) avrà la **stessa policy** (full re-index dell'indice wiki nell'MVP).

### 3. File non-testo (PDF/DOCX/notebook) fuori MVP

**Scope MVP:** sorgenti testuali: codice + Markdown/testo generico.

**Esclusi:** PDF, DOCX, notebook (Jupyter, R Markdown).

**Razionale:** focus sulla line-of-business (codice). PDF/DOCX/notebook sono post-MVP se il cliente lo chiede.

### 4. Soglie di performance/qualità non fissate ora

**Decisione:** métriche (latenza, hit@5, MAP, NDCG, latency SLA) **non fissate nella specifica** ma misurate in **fase di design** su corpus campione con **ground-truth**.

**Baseline:** il [[chiusura-prototipo-dogfooding|prototipo]] (corpus dogfood; il RAG di produzione lo consultano per metriche storiche).

**Local vs Cloud:** per **Ollama locale** si accetta una **soglia ridotta** (coerente col prototipo):
- Cloud (Azure OpenAI embeddings): hit@5 ≈ 0.80 (baseline storico).
- Local (Ollama `nomic-embed-text`): hit@5 ≈ 0.67 (degradazione accettata).

**Criteri**: qualità soddisfacente se superiore alla soglia del proprio provider, non confronto assoluto cloud vs local.

### 5–6. Wiki skill: agente LLM primario, niente chunking input

**Attore primario:** **agente LLM** (skill prodotto FEAT-003) invocato da umano via **brief condensato** (non trascrizione grezza).

**Input processing:** l'agente riceve il brief **già curato** → **niente chunking dell'input** nel MVP. Il brief è compatto (max 1–2 KiB); agente estrae diretta il significato.

**Struttura directory wiki:** **fissa** nell'MVP (concepts/, tech/, experiments/, sources/, syntheses/). Riorganizzazione post-MVP se richiesta.

**Invocazione:** umano passa il brief tramite lo **stesso canale** (non API separate; coerente con il workflow di produzione).

---

## Conseguenza sull'epica: FEAT-009

Dalla decisione #2 (full re-index MVP, incrementale post-MVP) emerge una **nuova feature nel backlog:**

**FEAT-009 — Manutenzione/refresh incrementale dell'indice RAG sui sorgenti** (Could)
- **Scope:** tracking delta di repository; update incrementale dell'indice sorgenti.
- **Dipendenza:** post-MVP (FEAT-001/002 base).
- **Razionale:** una volta stabilizzato l'MVP, le repository di sorgenti cambiano continuamente; full re-index diventa costoso.
- **Pendant:** specchiato in FEAT-007 (manutenzione wiki post-MVP).

Aggiunta in `requirements/sertor-core/epic.md` §8 (backlog).

---

## Stato domande aperte

Tutti i §10 dei tre documenti (`nucleo-retrieval/requirements.md`, `rag-baseline/requirements.md`, `wiki-creazione/requirements.md`) sono **risolti o rinviati a design**:

- **Risolte:** tutte le domande su chunking, ingestion flow, vector store astratti, wiki creazione (decisioni 1–6 sopra).
- **Rinviate a design:**
  - Estensione linguaggi oltre il set MVP di 14.
  - Supporto formati non-testo (PDF, DOCX, notebook).
  - Formato standardizzato del campo `sources` nei frontmatter wiki (JSON vs elenco libero).
  - Ground-truth condiviso per le metriche (sarà costruito in fase di design).
  - Test su Linux nativo (MVP + Windows nativo; Linux post-MVP o su richiesta).
  - Extra di pacchetto (`sertor-core` extras, pip `install sertor-core[azure]` vs `[local]`): rinviato all'epica secondaria **sertor-cli**, che decide packaging/distribuzione.

---

## Riferimenti

- **`requirements/sertor-core/epic.md`** — backlog §8 (FEAT-009 aggiunta); stato FEAT-001/002/003 = decomposte.
- **Tre documenti EARS:**
  - `requirements/sertor-core/nucleo-retrieval/requirements.md` — FEAT-001
  - `requirements/sertor-core/rag-baseline/requirements.md` — FEAT-002
  - `requirements/sertor-core/wiki-creazione/requirements.md` — FEAT-003
- **Collega:** [[epiche-sertor-core-e-cli|epiche-sertor-core-e-cli]], [[wiki-role-da-w1|ruolo-wiki-da-w1]]
