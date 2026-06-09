---
title: Corpus & index naming (RAG)
type: tech
tags: [architettura, corpus, indice, naming, prodotto, prototipo]
created: 2026-06-04
updated: 2026-06-09 (FEAT-009: indice dogfood `sertor` costruito; backend embeddings/store disaccoppiati)
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
- MCP `.mcp.json` configurato con `SERTOR_CORPUS=prototype` (update 2026-06-04).
- Server `prototype/04-agentic-rag/mcp_server.py` lancia con `SERTOR_CORPUS=prototype`, legge indici da `.index-prototype/`.
- Ricerca nel prototipo via tool MCP (`search_code`, `search_docs`, `get_context`, `find_symbol`, etc.) — **non** manualmente.

## Implicazioni di implementazione

### File di configurazione
- **`.env` (gitignored):**
  ```bash
  SERTOR_CORPUS=sertor              # prodotto
  SERTOR_INDEX_DIR=.index-sertor
  RAG_BACKEND=local                 # oppure azure
  ```

- **`.mcp.json` (root):**
  ```json
  {
    "env": {
      "PYTHONPATH": "prototype",
      "SERTOR_CORPUS": "prototype"
    }
  }
  ```

### Legge e loaders
- **`prototype/shared/config.py`:** selettore `SERTOR_CORPUS` (`fastapi` | `prototype`); percorsi indici funzione del corpus.
- **`prototype/shared/loaders.py`:** carica indice da `.index-<corpus>`.
- **`prototype/03-graphrag/build_graph.py`:** filter sorgenti per corpus; `SERTOR_CORPUS=prototype` → legge files `prototype/`.

### Conventions
- **Naming file indici:** `.<cartella>/.index-<corpus>/` (es. `.index-sertor`, `.index-prototype`).
- **Naming collezioni Chroma:** per backend Chroma, collezione = `<corpus>__<provider>` (es. `sertor__ollama`, `prototype__azure-large`). Il provider include il modello: l'indice dogfood di produzione è `sertor__azure_text_embedding_3_large` (FEAT-009, 191 doc / 1578 chunk, dim 3072).
- **Namespacing logico:** `SERTOR_CORPUS` isola comportamento senza duplicare config.

## Storico delle modifiche

| Data | Operazione | Dettagli |
|------|-----------|----------|
| 2026-05-30 | Isolamento prototipo | Corpus `sertor` introdotto per dogfooding (indice `.index-sertor` in prototipo). |
| 2026-06-04 | Rinomina chiarificatrice | Corpus `sertor` → prodotto (radice); corpus `prototype` → prototipo. Indice `.index-production` rimosso; `.index-sertor` → `.index-sertor` (radice per prodotto). Cartelle prototipo `.index-sertor` → `.index-prototype`. |
| 2026-06-09 | Indice dogfood costruito | Corpus `sertor` indicizzato per la **prima volta** (191 doc / 1578 chunk) in `.index-sertor/`, collezione `sertor__azure_text_embedding_3_large`. Embeddings Azure + store Chroma locale, abilitato da FEAT-009 (`store_backend` disaccoppiato). |

## Legami e riferimenti

- **[[chiusura-prototipo-dogfooding]]** — architettura di isolamento (record dal 30-05; nota: indici rinominati il 04-06).
- **`prototype/shared/config.py`** — selezione corpus-aware.
- **`.mcp.json`** — configurazione dogfooding (SERTOR_CORPUS=prototype).
- **`CLAUDE.md`** § "Riferirsi al prototipo" — updated 2026-06-04 con corpus `prototype`.

---

**Creato:** 2026-06-04 | **Stato:** IMPLEMENTATO (cartelle rinominate, non distruttivo)
