---
title: "Costituzione di Progetto per Fase Produzione — Proposta (NON ratificata)"
type: synthesis
tags: [governance, costituzione, speckit, produzione, principi, ratifica-aperta]
created: 2026-05-30
updated: 2026-05-30
---

# Costituzione di Progetto per Fase Produzione — Proposta (NON ratificata)

## Contesto

La **costituzione SpecKit** (file `.specify/memory/constitution.md`) è oggi un template vuoto. Questa pagina contiene una **proposta** di costituzione per la fase di produzione del workspace Sertor, da **rivedere e ratificare** formalmente.

La **costituzione** è il livello sopra il `CLAUDE.md`: i principi non-negoziabili contro cui il piano (`plan.md`) e ogni decision point del flusso SpecKit fanno il "Constitution Check" (rubrica canonicaSpecKit).

### Perché una costituzione

- **Chiarezza:** raccoglie i vincoli overarching una volta; non si ripetono in ogni decision.
- **Governance:** il Constitution Check di SpecKit (`speckit-plan`) si basa su questi articoli per validare design/trade-off.
- **Arbitrato:** quando due proposte di design competono, la costituzione fornisce il criterio decisorio.

---

## Principio chiave emerso dalla discussione

> **"Il prototipo è EVIDENZA, non PROGETTO."**

Il prototipo Sertor (tappe 01–04 complete) **dimostra COSA è utile** (e funge da fixture di dogfooding su Sertor stesso), **NON detta il COME**. Le scelte di design (tecnologie, pattern, tradeoff) per la produzione si prendono nel `plan.md` di ogni feature, guidate dalla costituzione; non si ereditano dal codice esplorativo.

---

## I 8 Principi proposti (how-agnostici)

### I. Repo-agnostico & riusabile

- **Scope:** il workspace genera un **toolset RAG riproducibile**, consumabile su qualunque codebase (FastAPI è il campione, ma la pipeline non dipende da FastAPI).
- **Design implication:** ogni componente (chunking, embeddings, retrieval, orchestratore) è parametrizzato e testabile isolatamente.
- **Decision rubric:** "Se una feature la rende NON-portabile su altro repo, riconsiderare il design."

### II. Local-first & provider-agnostico

- **Scope:** il sistema funziona **in locale senza dipendenze Azure/cloud**, con Azure **attivabile via config** (`RAG_BACKEND=azure` in `.env`).
- **Design implication:** scelta provider (Ollama vs OpenAI vs Azure) NON entra nel codice; è config + `.env`.
- **Decision rubric:** "Se una feature richiede Azure hardcoded, aggiungere un percorso locale (magari degradato, ma funzionante)."

### III. Semplicità giustificata (YAGNI)

- **Scope:** ogni astrazione, ogni framework, ogni astensione viene aggiunta **solo quando un'evidenza (feature, eval, use case reale) lo richiede**. No "architecture astronauting".
- **Design implication:** vanilla orchestratore → AutoGen → SK → LangGraph è il percorso: ogni framework aggiunto per valore dimostrato, non per "future-proofing".
- **Decision rubric:** "Prima di aggiungere dipendenza/modulo, verificare: esiste un tale use case oggi? Quale problema risolve? Quanto costo?"

### IV. Qualità dimostrata da misure (non claim)

- **Scope:** il valore di una tecnica (hybrid search, reranking, graph navigation, agent routing) è **misurato con eval set concreto**, non dato per scontato. Claims aziendali ≠ evidenza.
- **Design implication:** ogni tappa mantiene `evaluate.py`, `eval_tasks.json`, metriche concrete (hit@k, MRR, cited, tool_ok, passi, latenza, token).
- **Decision rubric:** "Se una feature non ha una metrica, non è 'completata' — è prototype."

### V. Sicurezza di segreti & artefatti

- **Scope:** nessun `.env` o `.key` committato. Artefatti generati/rigenerabili (indici, grafo, embedding cache) vanno in `.gitignore`.
- **Design implication:** il repo è sempre "pubblico-ready", nessun leak accidentale.
- **Decision rubric:** ".gitignore è il primo file controllato in ogni PR; se dubbio, escludere."

### VI. Costo & determinismo consapevoli

- **Scope:** ogni feature che chiama un LLM ha una **stima token/cost/latenza beforehand** (vedi Tappa 3C: regola empirica 5–10× corpus, stima, esecuzione, delta reale registrato).
- **Design implication:** fusion get_context è preferita a fusion LLM-based (0 token vs 200–400, determinismo 100% vs ~95%).
- **Decision rubric:** "Se una feature costa token, documentare la stima; se il costo reale devia >2× stima, investigare e documentare il delta."

### VII. Governance via SpecKit (branch/PR, git delegato, wiki)

- **Scope:** in **prototipo** (adesso) commit/push direttamente su `master`; in **produzione** (target) niente push diretto su main — solo branch + PR, mediate da SpecKit + configuration-manager.
- **Design implication:** il `CLAUDE.md` policy rispecchia questa transizione; .claude/agents controllano il flusso (niente git diretto da agenti); wiki-keeper mantiene il registro.
- **Decision rubric:** "Dopo la ratifica di questa costituzione, il flusso produzione DEVE passare a SpecKit; commit/push diretti diventano una violazione."

### VIII. Il prototipo è evidenza non progetto

(Ripetiamo per enfasi)

- **Scope:** le scelte di design nel codice 01–04 (tree-sitter per chunking, networkx per AST, Chroma locale, cross-encoder FlashRank, ...) sono state **scelte per il campione FastAPI, in quel momento**. Non sono "design decisions" per produzione; sono **esplorazioni validate da eval**.
- **Design implication:** quando si passa alla produzione (Tappa 5), il **piano (plan.md)** decide quali scelte ereditare (es. tree-sitter conferma valore per symbol navigation), quali rimpiazzare (es. Azure AI Search invece di Chroma per scalabilità), quali abbandondere (es. AST networkx in memoria → Neo4j opzionale).
- **Decision rubric:** "Se il plan dice 'manteniamo albero-sitter perché funziona', è decisione; se il code ha tree-sitter e plan non lo menziona, è débris."

---

## Versioning semantico

- **Major (X.0.0):** cambio architecture (es. passaggio da Chroma a Azure AI Search come default).
- **Minor (0.Y.0):** feature/capability nuova (es. nuovo tool di retrieval, nuovo orchestratore).
- **Patch (0.0.Z):** bugfix, performance tuning, documentation.

---

## Spunti RAG-specifici da valutare (dalla ricerca Agentic-RAG)

Appunti da integrare nel piano se rilevanti:

1. **Groundedness & citazione obbligatoria:** ogni risposta agente deve citare le fonti (file, linee, chunk). Non è solo "buona pratica"; è **requisito funzionale** di fiducia.
   
2. **Qualità del retrieval valutata:** il retrieval NON è "black box"; serve una metrica (hit@k, nDCG) per ogni motore e orchestratore.

3. **Provenienza/igiene del corpus:** i dati in ingestion devono essere "puliti" (blob binari filtrati, no garbage). Linea nel backlog di produzione ([[architettura-attuale]]).

4. **Governance del retrieval agentico:** se un agente usa 10 tool-call per rispondere a una domanda semplice, è inefficiente. Serve **limite design** (es. max 5 passi) e **verifica prima di rispondere** (es. confidence score).

---

## Decisioni aperte (da ratificare)

### 1. Ecosistema target: Microsoft/Azure vs cloud-agnostico?

- **Opzione A (Microsoft-first):** il workspace è design per Azure OpenAI + Azure AI Search + Azure Cosmos DB; locale è fallback.
  - **Pro:** tight integration, supporto Microsoft, pattern "native" Azure.
  - **Contro:** lock-in, costo Azure, learning curve.

- **Opzione B (cloud-agnostico):** il workspace è neutrale (Ollama == OpenAI pubblico == Azure); provider è config pura.
  - **Pro:** portabilità, libertà di scelta, price competition.
  - **Contro:** nessun "nativo"; integrazione Azure/AWS/GCP è sforzo.

**Status attuale:** Opzione B (codice attuale è agnostico, Azure è un percorso su `.env`). **Proposta:** mantenere Opzione B (Principio II).

### 2. Data di ratifica

- **Proposta:** ratifica formale al termine della Tappa 04 (come dogfooding prove-of-concept), prima di Tappa 05 (produzione branch/PR).

### 3. Numero di principi (5 vs 8)?

- **Proposta:** i 5 core sono: repo-agnostico, local-first, YAGNI, qualità-misurata, segreti. Gli altri 3 (versioning, RAG-specifici, governance) sono **articoli di dettaglio**, no core.
  - **Versione sintetica (5):** per visibilità rapida.
  - **Versione estesa (8):** per decision-making complesso.

### 4. Rigore test

- **Opzione A (Smoke + eval pragmatico):** test verificano il funzionamento (no crashing), eval set misura la qualità (hit@k, MRR), coerente con lo stato attuale.

- **Opzione B (TDD non-negoziabile):** ogni feature parte da test case fallente, design passa, test passa. Overhead di cicli di development.

**Status attuale:** Opzione A. **Proposta:** mantenere A per prototipo; B per produzione (Principio III: semplicità fino a evidenza).

---

## Riferimenti a vincoli Azure (se si sceglie target Azure in futuro)

Se il piano futuro decide **Opzione A (Microsoft-first)**, il template `Azure-Samples/azure-speckit-constitution` fornisce una rubrica di vincoli Azure specifici (compliance, networking, service limits). Collegare come **estensione della costituzione**, no sostituzione.

---

## Link correlati

- [[speckit]] — descrizione SpecKit e flusso operativo.
- [[architettura-attuale]] — as-built diagram e backlog di produzione.
- [[requirements-engineering]] — fase autonoma di elicitazione requisiti (complementare, pre-governance).

---

## Nota di procedura

Questa pagina è una **proposta**, non ratificata. La ratifica avviene tramite:

1. Review da stakeholder (chi ha autorità di decision).
2. Discussione su ambiguità / modifiche proposte.
3. Firma formale (data, version number, chi firma).
4. Upload a `.specify/memory/constitution.md` (source of truth SpecKit).
5. Backlink aggiunto qui e da `index.md`.

Fino a ratifica, questa pagina serve da **working document** per il flusso principale e team di planning.
