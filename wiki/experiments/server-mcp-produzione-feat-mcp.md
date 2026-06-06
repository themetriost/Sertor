---
title: Server MCP di Produzione (FEAT-MCP) — Avvio e Requisiti
type: experiment
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

## Flusso SpecKit: completamento (2026-06-06)

La feature ha attraversato l'intero ciclo SpecKit **completo** e la **implementazione è finita**:

1. **Requirements** ✅: `requirements/sertor-core/mcp/requirements.md` (57 REQ funzionali + 8 RNF, 7 rischi, 4 DA con default).
2. **Specify** ✅: `specs/007-mcp-sertor-core/spec.md` + contratti (`contracts/mcp-tools.md`); Constitution Check **10/10 ✅** (Principi I, IV, X NON-NEGOZIABILI superati).
3. **Clarify** ✅: `specs/007-mcp-sertor-core/research.md` (analisi corpus-aware, binding).
4. **Plan** ✅: `specs/007-mcp-sertor-core/plan.md` (strategy, complexity tracking); Constitution Check pre-phase confirmato.
5. **Analyze** ✅: `specs/007-mcp-sertor-core/checklists/requirements.md` + Constitution Check riconciliato (descrizione nota VI sul Principio IV: policy errori non uniforme e voluta, coerente col core).
6. **Implement** ✅: **codice finito** (2026-06-06).

---

## Implementazione: codice finito

### Struttura e file

```
src/sertor_mcp/
├── __init__.py          # docstring di scopo (layer sottile, Principio I)
└── server.py            # FastMCP("sertor-rag") con 3 tool + formattatore + logging

tests/unit/
└── test_mcp_server.py   # 6 test: tool registrati, formato, filtro, troncamento, indice mancante, errore
```

### Dettagli implementativi

**Server core (`server.py`):**
- **Istanza MCP:** `FastMCP("sertor-rag")` con instructions che guidano la scelta del tool (code/doc/combined).
- **Facade memoizzata:** `build_facade(Settings.load())` costruita **una volta** con `@lru_cache(maxsize=1)`.
- **Formattatore:** `_fmt(RetrievalResult)` normalizza il testo e **tronca l'anteprima** a `_PREVIEW` (300 car) con marcatore `"…"`.
- **Tre tool registrati:**
  - `search_code(query, k=5)`: ristretti al codice.
  - `search_docs(query, k=5)`: ristretti alla documentazione.
  - `search_combined(query, k=6)`: codice + doc insieme.
- **Log di superficie:** `log_event(logging.INFO, f"mcp.{tool}", k=k, results=len(results))` per nominare il tool (la **facade del core logga già** `retrieve`/`no_index` a livello di providers/store); nessuna duplicazione.
- **main():** avvia `mcp.run()` (stdio).

**Test (`test_mcp_server.py`, 6 test verdi):**
- ✅ `test_three_search_tools_registered()`: i 3 tool appaiono in `list_tools()`.
- ✅ `test_tool_returns_formatted_dicts()`: formato stabile `{path, source, chunk, score, preview}`.
- ✅ `test_tool_filters_by_type()`: `search_code` → tutti `source=="code"`, etc.
- ✅ `test_preview_is_truncated()`: anteprima troncata oltre soglia.
- ✅ `test_missing_index_returns_empty_without_crash()`: indice assente → `[]` (degrado pulito, **nessun crash**).
- ✅ `test_internal_error_propagates_then_server_recovers()`: errore reale → propagato + recupero (server vivo).

**Config e binding:**
- `pyproject.toml`: extra opzionale `mcp = ["mcp>=1.2"]`; `"src/sertor_mcp"` nei packages del wheel (REQ-060, isolamento dipendenze).
- `.mcp.json` (binding): `python -m sertor_mcp.server` con env `SERTOR_CORPUS=sertor` (sostituisce il server del prototipo rotto).
- `.env.example`: nota su `SERTOR_CORPUS=sertor` per il dogfood.

### Lint e test

- **Ruff:** ✅ pulito (`uv run ruff check src/sertor_mcp tests/unit/test_mcp_server.py`).
- **Suite non-cloud:** ✅ 116 passed (le 6 del server verde, + suite core).
- **Binding venv:** entrambi `.venv` e `.venv-core` importano `mcp` + `sertor_mcp` → `.mcp.json` valido.

---

## Scoperte cruciali

### Osservabilità: il core logga già (Principio IX confermato)

**Gap iniziale sospetto:** il piano menzionava "osservabilità (RNF-004)" come possibile lacuna. 

**Verità rilevata:** la **facade del core logga già** le operazioni di `retrieve` (provider, k, numero risultati, elapsed) e anche il warning `no_index` quando l'indice manca. **Il Principio IX è già coperto dal nucleo.** Non era necessario duplicare a livello server. 

**Scelta implementativa:** aggiunto comunque un log di **superficie per-tool** (`op=mcp.search_*`) per nominare quale tool è stato invocato nel contesto MCP, senza logiche di retrieval duplicate. ✅ Coerente.

### Degrado pulito: ereditato dalla policy del core

**Comportamento "indice mancante → `[]` + warning":** non è silenzioso né inghiottito. È la **policy tollerante e voluta** della facade (per composabilità del core), ben diversa da un null silenzioso. Lo stato è osservato, loggato e segnalato — nessuno stato parziale.

**Allineamento con il design progettuale** (CLAUDE.md): il core ha una "policy errori non uniforme e voluta" — la facade è tollerante (per composabilità), il motore baseline è strict (per usabilità del consumatore). Il server è un consumatore sano del nucleo, non il motore, quindi eredita il comportamento tollerante.

### Corpus naming `sertor` riconciliato

**DA-MCP1 (naming corpus legacy):** Risolto. Il server **non hardcoded** il corpus; legge da `Settings` (che la legge da `SERTOR_CORPUS` env). Il binding `.mcp.json` imposta `SERTOR_CORPUS=sertor` (non `production`), **sostituendo il legacy** del prototipo. REQ-021 ✅.

---

## Note di processo: SpecKit completo vs merge-sorgenti-orfani

La scelta di seguire **SpecKit completo** invece di mergere il branch `feat/mcp-sertor-core` è stata **strategica e verificata**:
- **Input:** branch con codice pulito (`server.py` + test).
- **Decisione:** usare come **RIFERIMENTO** durante implement, non come merge diretto.
- **Motivo:** tracciabilità da requisiti → spec → plan → tasks → codice (catena visibile), coerente col vincolo di governance (FEAT-010 dismesso, FEAT-003 consolidato). 
- **Esito:** codice finale conforme a spec, test ✅, Constitution Check superato, nessun codice orfano su master.

---

## Stato e timestamp

- **Stato:** ✅ **COMPLETATO** (implementation finita 2026-06-06).
- **Elicitazione requisiti:** 2026-06-06.
- **Requisiti:** `requirements/sertor-core/mcp/requirements.md` (57 REQ + 8 RNF, 7 rischi, 4 DA).
- **Spec:** `specs/007-mcp-sertor-core/spec.md` + plan + analyze ✅.
- **Codice:** `src/sertor_mcp/{__init__,server}.py` + `tests/unit/test_mcp_server.py` (6 test verdi, ruff pulito).
- **Config:** `pyproject.toml` (extra + package), `.mcp.json` (binding), `.env.example`.
- **Suite test:** 116 passed (non-cloud).
- **Constitution Check:** 10/10 ✅ (Principi I, IV, X NON-NEGOZIABILI superati).
- **Acceptance note:** T023 (validazione live con client MCP) e T024 (dogfood index) NON eseguiti — richiedono un indice del corpus `sertor` (fuori dal codice della feature; creazione dipende da entry-point CLI).

---

## Prossimi step della roadmap

Dopo FEAT-MCP ✅:

1. **[[architettura-wiki-llm]]** item **5a** (enabler RAG): COMPLETATO (il server MCP è il primo step della superficie finale).
2. **FEAT-005** (GraphRAG): estensione del server con tool di grafo (`find_symbol`, `who_calls`, `related_docs`, `get_context`), registrabili non-breaking (REQ-061).
3. **FEAT-004** (Hybrid RAG + reranking): tool aggiuntivo o variante per ricerca ibrida.
4. **Dogfood di produzione:** indice del corpus `sertor` per esercitare la suite end-to-end (blocca la valutazione completa di FEAT-MCP e il lint semantico N5 con probe-RAG).
5. **Agente Azure:** entry-point di invocazione dei tool del server MCP.
