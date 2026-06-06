---
title: Chiusura del Prototipo e RAG di Dogfooding
type: experiment
tags: [produzione, prototipo, isolamento, dogfooding, mcp, corpus-aware]
created: 2026-05-30
updated: 2026-05-30
sources: []
---

# Chiusura del Prototipo e RAG di Dogfooding

## Motivazione e contesto

La fase di **prototipo** (4 motori RAG su FastAPI, test, corpus esterno FastAPI in `raw/`)
è stata conclusa il 2026-05-30. Razionale:

1. **Confine netto prototipo ↔ produzione:** il prototipo era una fase **esplorativa**,
   con focus su validazione di tecnologie e approcci RAG diversi (baseline, hybrid+reranking,
   GraphRAG, agentico). La fase di **produzione** (attuale) ha un target concreto:
   costruire `sertor-rag`, un **CLI + server MCP** enterprise-grade con logica di ricerca
   codice-consapevole, gestione corpus-aware, integrazione Azure opzionale, e stabilità operativa.

2. **Riuso e dogfooding:** anziché scartare il lavoro svolto, si è deciso di usare il
   **prototipo stesso come corpus di validazione** per il nuovo motore di produzione.
   Così si mantiene storia, si accelera il testing e si costruisce un **RAG di dogfooding**
   (RAG che interroga il suo stesso codice sorgente e documentazione). Questa scelta
   stabilisce una best practice: un sistema RAG enterprise dovrebbe essere in grado di
   introspezione (ricercare se stesso).

## Architettura: Isolamento fisico e logico

### Struttura di cartelle post-isolamento

```
Sertor/ (root del repo)
├─ CLAUDE.md                          # Linee guida (invariate)
├─ prototype/                         # Snapshot del prototipo (congelato, sola lettura)
│  ├─ 01-baseline/
│  ├─ 02-hybrid-reranking/
│  ├─ 03-graphrag/
│  ├─ 04-agentic-rag/
│  │  └─ mcp_server.py                # Server MCP ora ri-puntato da .mcp.json
│  ├─ shared/
│  │  ├─ config.py                    # Selettore SERTOR_CORPUS
│  │  └─ loaders.py                   # Corpus-aware
│  ├─ tests/
│  ├─ raw/                            # Corpus FastAPI (intatto)
│  ├─ wiki/                           # Wiki storico del prototipo (congelato)
│  └─ README.md, DEMOS/, ESEMPI/, etc.
│
├─ wiki/                              # NUOVO wiki di produzione
│  ├─ index.md
│  ├─ log.md
│  ├─ concepts/
│  ├─ tech/
│  ├─ experiments/
│  ├─ sources/
│  └─ syntheses/                      # Questo file
│
├─ requirements/                      # Epica + feature di produzione
│  └─ sertor-cli/epic.md
│
└─ .mcp.json                          # Ri-puntato a prototype/04-agentic-rag/mcp_server.py
```

**Conseguenze:**
- Il prototipo è immutabile: non si modifica, non si versiona oltre lo snapshot.
- Tutte le modifiche future sono isolate nel ramo di produzione (cartelle di livello alto,
  `requirements/`, `wiki/`, eventuali strumenti nuovi).
- L'accesso al prototipo avviene **via MCP** (`sertor-rag` tool), non manualmente.

### Motore RAG corpus-aware

Il motore di dogfooding è stato reso **corpus-aware** introducendo la variabile ambiente
**`SERTOR_CORPUS`** (valori: `fastapi` | `sertor`). Componenti modificate:

- **`prototype/shared/config.py`:** selettore di backend e corpus; i percorsi degli indici
  sono funzioni di `SERTOR_CORPUS`.
- **`prototype/shared/loaders.py`:** loader dell'indice, documenti e metadati filtrati
  per il corpus selezionato.
- **`prototype/03-graphrag/build_graph.py`:** construction del grafo AST filtrato per corpus;
  **fix critico:** filtro `mentions` prima hardcoded su `fastapi/`, ora dinamico
  (`SERTOR_CORPUS`-consapevole).

**Indici e namespacing:**
- Corpus **FastAPI:** indice Chroma in `prototype/01-baseline/.index` (generato precedentemente,
  ancora in uso se FastAPI viene riavviato; **lockato dal server MCP in esecuzione**).
- Corpus **Sertor (dogfooding):** indice Chroma in `prototype/01-baseline/.index-sertor` (nuovo,
  generato il 2026-05-30).

**Nota operativa:** l'indice FastAPI non è stato ricollocato fisicamente perché il server MCP
continua a servirlo. La ricollocazione è un passo **post-restart** oppure si rigenera da zero.

## RAG di Dogfooding: Numeri e Composizione

Il nuovo indice **`.index-sertor`** ha le seguenti caratteristiche:

- **Corpus:** codice sorgente + documentazione + wiki del **prototipo stesso**.
  Cioè: cartelle `01–04`, `shared/`, `tests/`, README, DEMOS, ESEMPI,
  `prototype/wiki/` (intera documentazione storica del prototipo).
- **Backend:** Chroma (embedding Azure Large, `text-embedding-3-large`).
- **Statistiche:**
  - **Documenti:** 57
  - **Chunk totali:** 670 (dim 3072)
  - **Indice grafo AST:** 240 nodi, 835 archi
    - Edge `mentions`: 415
    - Edge `doc`: 26
    - Edge (altro): 394

Questo indice funziona come **canary** e **validation** per il nuovo motore di produzione:
- Permette test funzionali degli strumenti RAG (retrieval, ranking, navigazione grafo)
  su un corpus noto e eterogeneo (codice Python + documentazione MD + logica RAG).
- Quando il CLI `sertor` sarà lanciato su un nuovo repository, userà lo stesso pipeline
  di ingestion + indice, garantendo comportamento coerente.

## MCP ri-puntato: Accesso al Prototipo

Il file `.mcp.json` (configurazione dei tool MCP) è stato ri-puntato:

```json
{
  "command": "python",
  "args": ["prototype/04-agentic-rag/mcp_server.py"],
  "env": {
    "PYTHONPATH": "prototype",
    "SERTOR_CORPUS": "sertor"
  }
}
```

**Conseguenze:**
- Il server MCP (`sertor-rag`) avvia il motore con `SERTOR_CORPUS=sertor`, quindi usa
  l'indice Chroma `.index-sertor` (dogfooding).
- I tool del server (`find_symbol`, `search_code`, `search_docs`, `search_combined`,
  `who_calls`, `related_docs`, `get_context`) interrogano il **prototipo stesso** e ne
  restituiscono risultati contextualizzati.

**Tool disponibili (mappatura):**
- `find_symbol(symbol: str)` → ricerca un simbolo Python nel prototipo (es. `HybridIndex`
  → file `02-hybrid-reranking/hybrid.py`, riga 50).
- `search_code(query: str)` → ricerca semantica nel codice (es. "embedding retrieval").
- `search_docs(query: str)` → ricerca semantica nella documentazione (es. "GraphRAG",
  "semantic reranking").
- `search_combined(query: str)` → unione di code + docs.
- `who_calls(symbol: str)` → navigazione: chi chiama un simbolo?
- `related_docs(topic: str)` → documenti correlati a un tema.
- `get_context(symbol: str)` → contesto esteso di un simbolo (includesource).

**Verifica funzionale (2026-05-30):** tutti i tool rispondono correttamente con risultati
dal prototipo. Esempio:
```
find_symbol("HybridIndex") 
→ 02-hybrid-reranking/hybrid.py:50 (classe)
```

## Conseguenze operative

1. **Sviluppo:** il nuovo codice di produzione (cartelle a livello alto, `sertor-cli/`,
   eventualmente nuovi moduli) non tocca `prototype/`. Se serve integrare o iterare sul
   prototipo, si consulta via MCP.

2. **Wiki:** il wiki storico del prototipo (`prototype/wiki/`) è **congelato**. Il nuovo
   wiki (`wiki/`) è il centro di documentazione di produzione. Se serve riferire un
   concetto o tecnologia dal prototipo, si linkano le pagine di produzione e si cita il
   MCP (es. concetto di architettura da `prototype/wiki/`, accedi via `sertor-rag`).

3. **Test e validazione:** il corpus di dogfooding funge da **automated acceptance test**
   per il motore RAG. Ogni modifica al pipeline di ingestion, embedding, ranking dovrebbe
   mantenere i risultati stabili sul prototipo; varianze eccessive segnalano regressioni.

4. **Evoluzione verso la produzione:**
   - Fase A (ora): validazione funzionale su corpus dogfooding.
   - Fase B: hardening della CLI (`sertor ingest`, `sertor search`, `sertor export`).
   - Fase C: integrazione Azure opzionale e multi-backend (Chroma, Azure AI Search, Cosmos).
   - Fase D: stabilità operativa, strumenti DevOps, distribuibilità.

## Backlink e riferimenti

- **[[epiche-sertor-core-e-cli]]** — epiche di produzione (requirements/sertor-{core,cli}/epic.md).
- **prototype/wiki/** — wiki storico del prototipo (consultabile via `sertor-rag` tool).
- **`.mcp.json`** (root) — configurazione del server MCP.
- **`prototype/shared/config.py`** — implementazione della selezione corpus-aware.
- **`prototype/01-baseline/.index-sertor`** — indice dogfooding (Chroma, non commitato).

---

**Data:** 2026-05-30 | **Stato:** CONFERMATO (branch `chore/isolamento-prototipo`, commit `104e666`)
