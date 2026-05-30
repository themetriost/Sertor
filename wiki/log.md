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
