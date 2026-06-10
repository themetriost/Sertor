---
title: Corpus & index naming (RAG)
type: tech
tags: [architettura, corpus, indice, naming, prodotto, prototipo]
created: 2026-06-04
updated: 2026-06-10 (corpus `wiki` come seconda collezione nello stesso store; .mcp.json → produzione dal 2026-06-06, claim corretto; ProviderMismatchError)
sources: ["CLAUDE.md", "prototype/shared/config.py", ".mcp.json", "src/sertor_core/config/settings.py", "src/sertor_core/composition.py"]
---

# Corpus & index naming (RAG)

Il **naming di corpora e indici** è la convenzione con cui Sertor tiene separati i dati RAG di prodotto e
di prototipo: il **corpus** (cosa si indicizza) e l'**indice** (dove vivono i vettori) sono assi
ortogonali, namespaced per `(corpus, provider)`, così demo e dogfood non si sovrascrivono.

## Contesto e motivazione

A partire dal 2026-06-04, il workspace Sertor ha due **assi ortogonali**:
- **Ramo prodotto (radice):** codebase attiva, requirements, wiki di produzione.
- **Ramo prototipo (congelato):** 4 motori RAG su FastAPI, sola lettura, consultabile via MCP.

Fino al 30-05, i **nomi di corpus e indici erano ambigui**:
- Corpus `sertor` era usato per il prototipo (dogfooding).
- Indice `.index-sertor` era nel prototipo, su disco in `.index-sertor`.

Questa ambiguità creava confusione: `sertor` è anche il **nome del prodotto**. Il 2026-06-04,
il naming è stato **riconciliato per chiarezza**.

## Schema attuale (dal 2026-06-04)

### Prodotto (Radice)

| Aspetto | Valore |
|---------|--------|
| **Corpus** | `sertor` |
| **Indice (default locale Chroma)** | `.index-sertor/` |
| **Contenuto** | Codice sorgente e docs del prodotto (FEAT-001, FEAT-002, FEAT-003, ...) |
| **Scopo** | Ricerca, RAG production sul codice di `sertor` stesso |
| **Backend** | Embeddings e store scelti **indipendentemente** (FEAT-009): `RAG_BACKEND` (Ollama \| Azure OpenAI) × `SERTOR_STORE_BACKEND` (Chroma locale \| Azure AI Search). Indice dogfood attuale: **embeddings Azure `text-embedding-3-large` + store Chroma locale**. |

### Wiki di produzione (corpus separato, stesso indice)

| Aspetto | Valore |
|---------|--------|
| **Corpus** | `wiki` (da `wiki.config.toml`, sezione `[rag]`) |
| **Indice** | lo **stesso** `.index-sertor/` del prodotto (l'`index_dir` viene dai medesimi `Settings`): una **seconda collezione** nello stesso store, `wiki__<provider>` |
| **Contenuto** | le pagine del wiki di produzione (`wiki/`), indicizzate da `sertor-wiki-tools index` (op. `rag-sync`) |
| **Scopo** | rendere il wiki interrogabile via RAG **separatamente** dal codice; con `SERTOR_EXTRA_CORPORA=wiki` la **ricerca combinata fonde** i due corpora (feature 010 — vedi [[indexing-and-retrieval]]) |

Avvertenza nota: il corpus `sertor` indicizza **anche** `wiki/` al proprio interno → nella combinata
compaiono quasi-duplicati (stessa pagina dai due corpora). Mitigazione possibile: escludere `wiki/` dal
corpus primario via `SERTOR_EXCLUDE_PATTERNS` (scelta di config dell'ospite, aperta).

**Note operazionali:**
- La cartella `.index-production` (epoch locale-backend, 39M, with stale collections) è stata **eliminata** il 2026-06-04 (non più rilevante).
- Il corpus `sertor` determina il **nome logico** nel contesto di `SERTOR_CORPUS` e il **nome fisico della cartella** degli indici.
- Env: `SERTOR_CORPUS=sertor`, `SERTOR_INDEX_DIR=.index-sertor` (in `.env`, gitignored).

### Prototipo (Congelato)

| Aspetto | Valore |
|---------|--------|
| **Corpus** | `prototype` |
| **Indice (Chroma)** | `prototype/01-baseline/.index-prototype/`, `prototype/03-graphrag/.index-prototype/` |
| **Contenuto** | Codice + docs dei 4 motori RAG, wiki storico (cartelle `01–04`, `shared/`, `tests/`, `wiki/`, raw corpus `raw/`) |
| **Scopo** | Validazione/dogfooding; RAG che interroga il prototipo stesso |
| **Backend** | Chroma (embedding Azure Large, `text-embedding-3-large`) |

**Note operazionali:**
- Rename `01-baseline/.index-sertor` → `01-baseline/.index-prototype/` (2026-06-04).
- Rename `03-graphrag/.index-sertor` → `03-graphrag/.index-prototype/` (2026-06-04).
- Dal **2026-06-06** (FEAT-MCP, PR #15) il server MCP attivo è quello di **produzione**
  ([[mcp-server|`sertor_mcp`]]) e `.mcp.json` è puntato al **corpus `sertor`** — il server del prototipo
  (`prototype/04-agentic-rag/mcp_server.py`, con `find_symbol`/`get_context`) non è più quello dichiarato;
  per interrogare il prototipo si ri-punta temporaneamente `SERTOR_CORPUS=prototype`.

## Implicazioni di implementazione

### File di configurazione
- **`.env`** (gitignored) — il prodotto: `SERTOR_CORPUS=sertor`, `SERTOR_INDEX_DIR=.index-sertor`, più i
  selettori di backend `RAG_BACKEND` / `SERTOR_STORE_BACKEND`.
- **`.mcp.json`** (root) — il server `sertor-rag` per il dogfood: imposta `SERTOR_CORPUS` sul corpus da
  servire e il `PYTHONPATH` corrispondente.

### Legge e loaders
- **`prototype/shared/config.py`:** selettore `SERTOR_CORPUS` (`fastapi` | `prototype`); percorsi indici funzione del corpus.
- **`prototype/shared/loaders.py`:** carica indice da `.index-<corpus>`.
- **`prototype/03-graphrag/build_graph.py`:** filter sorgenti per corpus; `SERTOR_CORPUS=prototype` → legge files `prototype/`.

### Conventions
- **Naming file indici:** `.<cartella>/.index-<corpus>/` (es. `.index-sertor`, `.index-prototype`).
- **Naming collezioni Chroma:** per backend Chroma, collezione = `<corpus>__<provider>` (es. `sertor__ollama`, `prototype__azure-large`). Il provider include il modello: nello store dogfood `.index-sertor/` convivono `sertor__azure_text_embedding_3_large` (codice+doc del prodotto) e `wiki__azure_text_embedding_3_large` (pagine del wiki). Il namespacing per provider è anche ciò che rende **rilevabile** un corpus indicizzato con un provider diverso (`ProviderMismatchError` nella ricerca combinata, feature 010).
- **Namespacing logico:** `SERTOR_CORPUS` isola comportamento senza duplicare config.

## Legami e riferimenti

La cronologia datata delle rinomine e della costruzione dell'indice dogfood vive nei record:
[[store-backend-disaccoppiato-feat009]] (indice `sertor` costruito) e nei log di `wiki/log/`.


- **[[chiusura-prototipo-dogfooding]]** — architettura di isolamento (record dal 30-05; nota: indici rinominati il 04-06).
- **`prototype/shared/config.py`** — selezione corpus-aware.
- **`.mcp.json`** — configurazione del dogfood di produzione (`SERTOR_CORPUS=sertor`, server [[mcp-server]]).
- **`CLAUDE.md`** § "Riferirsi al prototipo" — il corpus `prototype` per consultare il prototipo congelato.
