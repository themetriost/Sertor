---
title: Log del Wiki — Produzione Sertor
type: log
created: 2026-05-30
updated: 2026-05-30
---

# Registro di Produzione (append-only)

Voci in ordine cronologico. Formato: `## [YYYY-MM-DD] <operazione> | <titolo>`
(operazione ∈ setup/ingest/record/query/lint).

## [2026-05-30] setup | Apertura del wiki di produzione (chiusura del prototipo)

- **Isolamento prototipo:** codice `01–04`, `shared/`, `tests/`, corpus FastAPI (`raw/`),
  documentazione (`README/DEMOS/ESEMPI`) e il wiki storico spostati in **`prototype/`**
  (stesso repo). Il wiki del prototipo è ora **congelato** (sola lettura) in `prototype/wiki/`.
- **RAG di dogfooding:** motore reso *corpus-aware* (env `SERTOR_CORPUS`); nuovo indice separato
  `prototype/01-baseline/.index-sertor` il cui corpus è il **prototipo stesso** (codice + doc + wiki).
  L'indice FastAPI esistente **non è stato toccato**.
- **MCP ri-puntato:** `.mcp.json` → `prototype/04-agentic-rag/mcp_server.py` con
  `PYTHONPATH=prototype`, `SERTOR_CORPUS=sertor`. Ogni riferimento al prototipo passa ora dal RAG.
- **Questo `wiki/` di root** è il nuovo wiki di **produzione**; hook `SessionStart`, agente
  `wiki-keeper` e skill `.claude/` restano invariati (continuano a puntare a `wiki/`).

## [2026-05-30] record | Chiusura prototipo + RAG dogfooding + MCP ri-puntato

- **Pagina creata:** `syntheses/chiusura-prototipo-dogfooding.md` documenta in dettaglio:
  - **Motivazione:** confine netto prototipo (exploration) ↔ produzione (CLI `sertor-rag`).
  - **Isolamento fisico:** prototipo sotto `prototype/` (snapshot congelato), produzione
    a livello alto (requirements, wiki, nuovi moduli).
  - **Motore corpus-aware:** `SERTOR_CORPUS` (`fastapi` | `sertor`) in `config.py` e `loaders.py`;
    fix critico del filtro `mentions` in `build_graph.py` (era hardcoded, ora dinamico).
  - **Indici namespaced:** `.index` (FastAPI) vs `.index-sertor` (dogfooding).
  - **RAG di dogfooding:** indice Chroma `.index-sertor` su prototipo stesso.
    Corpus = 57 doc, 670 chunk (dim 3072); grafo = 240 nodi, 835 archi (415 mentions, 26 doc).
  - **MCP ri-puntato:** `.mcp.json` → `prototype/04-agentic-rag/mcp_server.py`
    (`SERTOR_CORPUS=sertor`). Tutti i tool (`find_symbol`, `search_code`, etc.) testati e funzionanti.
  - **Conseguenze operative:** sviluppo isolato da prototipo; accesso via MCP; wiki prototipo
    congelato; corpus dogfooding come acceptance test.
- **Index aggiornato:** sezione "Syntheses" con link a `[[chiusura-prototipo-dogfooding]]`.
- **Branch/commit:** `chore/isolamento-prototipo` (commit `104e666`), pagina aggiunta in questo record.
