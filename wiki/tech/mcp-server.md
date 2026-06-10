---
title: Server MCP sertor-rag
type: tech
tags: [mcp, server, sertor-mcp, thin-consumer, retrieval, dogfooding, sertor-core]
created: 2026-06-08
updated: 2026-06-10 (search_combined eredita il fan-out multi-collezione della feature 010 via config, server invariato)
sources: ["src/sertor_mcp/server.py", ".mcp.json"]
---

# Server MCP sertor-rag

Il **server MCP `sertor-rag`** (`src/sertor_mcp/server.py`) è la **superficie** che rende il
[[retrieval-core]] usabile **nativamente da un agente LLM**: espone la ricerca vettoriale del nucleo come
**tool MCP** (Model Context Protocol) via stdio. È l'esempio canonico di [[thin-consumer|consumatore
sottile]] — delega tutto alla facade del core, non reimplementa retrieval — e **sostituisce** il vecchio
server del prototipo come superficie attiva (FEAT-MCP, record: [[server-mcp-produzione-feat-mcp]]).

## I tre tool

Istanza `FastMCP("sertor-rag")` con `instructions` che guidano la scelta del tool. Ogni tool delega al
metodo omonimo della [[indexing-and-retrieval|facade]]:

| Tool | Filtro | Default `k` |
|---|---|---|
| `search_code(query, k)` | solo codice | 5 |
| `search_docs(query, k)` | sola documentazione | 5 |
| `search_combined(query, k)` | codice + doc; con corpora extra configurati (`SERTOR_EXTRA_CORPORA`, es. il wiki) fonde **più collezioni** — feature 010, [[indexing-and-retrieval|dettagli]] | 6 |

Il fan-out multi-collezione arriva **gratis** al server senza toccarlo (è il senso del thin-consumer: la
capacità vive nella facade, la superficie la eredita dalla configurazione).

La facade è costruita **una volta** con `build_facade(Settings.load())` memoizzata via `@lru_cache(maxsize=1)`
e riusata da tutti i tool.

## Formato dei risultati (citabile)

`_fmt` mappa ogni `RetrievalResult` su un dict a campi stabili — `{path, source, chunk, score, preview}` —
con `score` a 4 decimali e `preview` normalizzata e **troncata** a 300 caratteri (`_PREVIEW`, parametro di
presentazione del server, non di dominio). Pensato per essere **citato** dal client (`path#chunk`).

## Sottigliezza voluta

- **Eredita la tolleranza del core.** Indice mancante → `[]` (nessun crash): è la policy *tollerante* della
  facade, non un null silenzioso. Il server è un consumatore *sano* del nucleo, non il motore strict.
- **Niente osservabilità duplicata.** La facade del core logga già `retrieve`/`no_index`; il server aggiunge
  solo un log di **superficie per-tool** (`mcp.<tool>`) per nominare quale tool è stato invocato.
- **Isolamento dipendenze.** L'SDK `mcp` è un **extra opzionale** del package (REQ-060): `pip install
  sertor-core` non lo trascina.

## Avvio e binding

Trasporto **stdio**: lo lancia il client MCP via `.mcp.json` (`python -m sertor_mcp.server`) con env
`SERTOR_CORPUS=sertor` → fa **[[dogfooding]]** sul corpus di produzione. I tool di **grafo**
(`find_symbol`/`who_calls`/`related_docs`/`get_context`) e il **reranking ibrido** torneranno coi motori
GraphRAG (FEAT-005) e ibrido (FEAT-004), registrabili non-breaking.

## Vedi anche
- Il pattern che incarna: [[thin-consumer]]. Cosa consuma: [[indexing-and-retrieval]] · [[retrieval-core]].
- A cosa serve: [[dogfooding]]. Naming del corpus: [[corpus-index-naming]].
