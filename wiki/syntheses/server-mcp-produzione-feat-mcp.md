---
title: Server MCP di Produzione (FEAT-MCP) — Avvio e Requisiti
type: synthesis
tags: [feature, mcp, server, produzione, retrieval, superficie-finale, enabler, feat-mcp]
created: 2026-06-06
updated: 2026-06-06
sources: ["requirements/sertor-core/mcp/requirements.md", "requirements/sertor-core/epic.md"]
---

# Server MCP di Produzione — Avvio della Feature FEAT-MCP

## Sommario

Avviata la feature **FEAT-MCP** (Server MCP di produzione, `sertor_mcp`) seguendo il **flusso SpecKit completo**. La feature è stata decomposta a livello di **requisiti EARS** (`requirements/sertor-core/mcp/requirements.md`, elicitazione del 2026-06-06), con **roadmap di fasi successive** (specify → plan → tasks → implement). FEAT-MCP è l'**enabler critico** di tre capacità di produzione:

1. **Probe-RAG del lint semantico del wiki** (FEAT-003-N / N5), che oggi degrada a fallback `Read`/`Grep`;
2. **Dogfood di produzione** (interrogare Sertor su se stesso: `src/`, `specs/`, `requirements/`, `wiki/`);
3. **Entry-point dell'agente Azure** che consuma i tool di retrieval.

---

## Contesto: perché ora

Il **core (`sertor_core`)** fornisce oggi:
- FEAT-001: nucleo retrieval (ingestione, chunking, embeddings, vector store);
- FEAT-002: motore baseline vettoriale (ranking, valutazione).

Entrambi sono **librerie Python riusabili**, ma manca la **superficie finale** che li renda **nativamente usabili da un agente LLM**. Quella superficie è un **server MCP** (Model Context Protocol) — il protocollo che consente a Claude Code e altri client di **orchestrare tool** remotamente via stdio.

### Il server del prototipo è rotto

Nel **prototipo** (`prototype/04-agentic-rag/mcp_server.py`) esiste un server MCP funzionante. Però:
- Punta al motore del prototipo (i 4 approcci RAG sperimentali);
- Interroga il **corpus congelato** (FastAPI, non la produzione);
- `.mcp.json` di `master` lo referenzia, ma è **rotto** operativamente (ModuleNotFoundError, dipendenze inconciliabili).

### Soluzione: FEAT-MCP (surface sottile su `sertor_core`)

Una feature dedicata che:
- Costruisce un server MCP sulla **facade di `sertor_core`** (consumatore sottile, Principio I);
- Espone **3 tool di ricerca baseline**: `search_code`, `search_docs`, `search_combined`;
- È **host-agnostico** (Principio X): cambiando solo `.env`, opera su corpus/backend/provider diversi;
- **Sostituisce** il server del prototipo come superficie attiva di `master`;
- Abilita il **probe-RAG del lint semantico** del wiki anziché fallback `Read`/`Grep`.

---

## Scoperta importante: un'implementazione di riferimento esiste già

**Branch non mergiato:** `feat/mcp-sertor-core` (commit `53b8e43`)
- **Contenuto:** `src/sertor_mcp/server.py` + `tests/unit/test_mcp_server.py`
- **Qualità:** pulita, testata, **compatibile con `master`** (verificato: `build_facade`/`Settings`/`RetrievalFacade`/`RetrievalResult` con campo `score` tutti presenti su master).

**Decisione:** NON fare merge dei soli sorgenti (sarebbe codice orfano senza spec a monte). Si segue il **flusso SpecKit completo** usando quel codice come **RIFERIMENTO** durante la fase di implement.

**Conseguenza:** master rimane pulito da sorgenti MCP/CLI orfani; la tracciabilità da requisiti a codice rimane netta.

---

## Requisiti EARS (2026-06-06)

Decomposti in **7 gruppi funzionali + 2 domande aperte** (vedi `requirements/sertor-core/mcp/requirements.md`):

### Gruppi Must (priorità alta)

| Gruppo | Focus | Requisiti |
|--------|-------|-----------|
| **A** | Esposizione tool retrieval | REQ-001..006: 3 tool (`search_code`, `search_docs`, `search_combined`), sola lettura |
| **B** | Consumatore sottile | REQ-010..011: facade di `sertor_core`, nessuna reimplementazione |
| **C** | Config host-agnostica | REQ-020..022: corpus `sertor` (non legacy `production`/`prototype`), senza hard-code |
| **D** | Avvio/trasporto | REQ-030..032: stdio, `python -m sertor_mcp.server`, binding `.mcp.json` |
| **E** | Formato risultati | REQ-040..042: strutturato, stabile, citabile (path/tipo/chunk_id/score/preview) |
| **F** | Gestione errori | REQ-050..051: indice mancante → risultati vuoti + warning (no crash) |
| **G** | Isolamento dipendenze | REQ-060: SDK MCP come extra opzionale (non nella core library) |

### Criteri di successo (CS-1..CS-8)

- **CS-1:** client MCP vede ≥1 tool e lo invoca con successo;
- **CS-2:** 3 tool distinti con filtri osservabili;
- **CS-3:** consumatore sottile verificabile (rimozione facade → niente funzionalità);
- **CS-4:** host-agnostico (same code, config diversa);
- **CS-5:** dogfood (corpus `sertor`, results pertinenti);
- **CS-6:** degrado pulito (indice mancante → no crash);
- **CS-7:** `.mcp.json` punta a `python -m sertor_mcp.server` (non prototipo);
- **CS-8:** isolamento dipendenze (`pip install sertor-core` senza mcp SDK).

### Rischi e mitigazioni

| Rischio | Prob | Impatto | Mitigazione |
|---------|------|---------|-------------|
| Indice assente | Media | Medio | REQ-050, warning, documentare build indice |
| Naming corpus legacy | Media | **Alto** | REQ-021 (riconciliazione esplicita a `sertor`) |
| Aspettativa tool di grafo | Media | Basso | Fuori ambito, REQ-032 chiarifica |
| Dipendenza MCP inquina core | Bassa | Medio | REQ-060 (extra isolato) |
| Divergenza facade | Bassa | Medio | Layer sottile, test con mock |
| Payload eccessivo | Bassa | Basso | REQ-041 (anteprima troncata) |

---

## Domande aperte (con default assunto)

| ID | Domanda | Default assunto |
|----|---------|-----------------|
| DA-MCP1 | Naming corpus: default di `Settings` è `"default"`, il prodotto usa `"sertor"`. Si cambia il default, o solo via `.env`/`.mcp.json`? | Impostare `sertor` solo via configurazione (non toccare default del core in questa feature). |
| DA-MCP2 | Tool di health/status (indice presente, corpus)? | No nell'MVP; warning di REQ-050 + log (RNF-004) bastano. |
| DA-MCP3 | Cap su `k` (max risultati)? | No cap rigido; default da facade; anteprima già troncata. |
| DA-MCP4 | Tre tool distinti vs un unico tool parametrico? | Tre tool distinti (DX migliore, coerente col riferimento). |

---

## Roadmap: prossimi step (variante D↔N deterministico↔giudizio)

La feature segue il **flusso SpecKit completo**:

1. **Requirements** ✅ (elicitazione 2026-06-06, EARS in `mcp/requirements.md`)
2. **Specify** (decisioni di design, contratti, modello dati MCP)
3. **Clarify** (chiarimento di vincoli/assumzioni)
4. **Plan** (piano di implementazione a livello task)
5. **Analyze** (Constitution Check sui requisiti; dovrebbe essere ✅ per Principio I+X)
6. **Implement** (coding su `src/sertor_mcp/`, test, integration con `.mcp.json`)

**Blocchi/sequenza consigliata:**
- **Aggancio facade** (REQ-010) **→** **3 tool** (REQ-001..006) **→** **formato** (REQ-040..042);
- Poi **config/corpus** (REQ-020..022) **→** **avvio/binding** (REQ-030..032) **→** **degrado** (REQ-050..051) **→** **extra isolato** (REQ-060).

---

## Legami architetturali

### Dipendenze (a monte)
- **[[implementazione-nucleo-retrieval]]** (FEAT-001): fornisce `build_facade` e metodi di ricerca.
- **[[motore-baseline-feat002]]** (FEAT-002): il motore su cui la facade si appoggia.

### Abilita (a valle)
- **[[rituale-step-e-allineamento-wiki]]** (FEAT-003-N, N5): il probe-RAG del lint semantico anziché fallback `Read`/`Grep`.
- **[[architettura-wiki-llm]]** (roadmap item 5a): FEAT-MCP è il primo step della superficie finale.
- **Agente Azure** (futuro): entry-point di invocazione dei tool.

### Rimpiazza
- **[[chiusura-prototipo-dogfooding]]**: il server del prototipo, rotto, che `.mcp.json` referenzia.

### Legato a
- **[[naming-corpora-indici]]**: riconciliazione naming corpus `sertor` (non legacy).

---

## Note di processo

### SpecKit completo, non "merge-sorgenti-orfani"

La decisione di seguire SpecKit full invece di mergere il branch già implementato riflette il vincolo di **tracciabilità**:
- Requisiti → spec → plan → task → codice (catena visibile);
- NON: codice → estrai requisiti (post-hoc).

Questo vale **specialmente per il nucleo di produzione**, dove ogni feature è modello per le capacità downstream (wiki, CLI, agenti).

### Riconciliazione corpus naming critica (DA-MCP1 / R-02)

Il cambio `production` → `sertor` è **non banale**:
- Codice del core di produzione usa `"sertor"` come default corpus;
- Server del prototipo usa `"production"` e il branch feature potrebbe ereditare.
- **REQ-021** lo formalizza: il server **deve** riconciliare a `"sertor"` (non legacy).

---

## Stato e timestamp

- **Stato:** in progress (requirements ✅, specify in agenda).
- **Elicitazione:** 2026-06-06.
- **Requisiti:** `requirements/sertor-core/mcp/requirements.md` (57 REQ + 8 RNF, 7 rischi, 4 DA).
- **Epica:** `requirements/sertor-core/epic.md` §8, priorità **Should**.
- **Riferimento:** branch `feat/mcp-sertor-core` (commit `53b8e43`, codice di riferimento, non per merge diretto).

---

## Checklist successiva

- [ ] Specify: decisioni su contratti MCP, modello dati tool, struttura `sertor_mcp/`;
- [ ] Clarify: conferma DA-MCP1..4, vincoli aggiuntivi;
- [ ] Plan: scomposizione in user story e task;
- [ ] Analyze: Constitution Check (atteso ✅ Principi I/X);
- [ ] Implement: coding, test, `.mcp.json` puntato a `python -m sertor_mcp.server`.
