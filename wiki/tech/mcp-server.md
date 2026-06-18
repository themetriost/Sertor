---
title: Server MCP sertor-rag
type: tech
tags: [mcp, server, sertor-mcp, thin-consumer, retrieval, dogfooding, sertor-core]
created: 2026-06-08
updated: 2026-06-14 (+ affidabilità e segnalazione errori: _guard su tool + self-test + governance, FEAT-001 affidabilità-dogfood) · 2026-06-12 (sera: superficie a 7 tool — tornati i 4 di grafo, FEAT-005/PR #25; mattina: warm-up eager PR #23 + troubleshooting)
sources: ["src/sertor_mcp/server.py", ".mcp.json"]
---

# Server MCP sertor-rag

Il **server MCP `sertor-rag`** (`src/sertor_mcp/server.py`) è la **superficie** che rende il
[[retrieval-core]] usabile **nativamente da un agente LLM**: espone la ricerca vettoriale del nucleo come
**tool MCP** (Model Context Protocol) via stdio. È l'esempio canonico di [[thin-consumer|consumatore
sottile]] — delega tutto alla facade del core, non reimplementa retrieval — e **sostituisce** il vecchio
server del prototipo come superficie attiva (FEAT-MCP, record: [[server-mcp-produzione-feat-mcp]]).

## I sette tool

Istanza `FastMCP("sertor-rag")` con `instructions` che guidano la scelta del tool. Ogni tool delega al
metodo omonimo della [[indexing-and-retrieval|facade]]:

| Tool | Filtro | Default `k` |
|---|---|---|
| `search_code(query, k)` | solo codice | 5 |
| `search_docs(query, k)` | sola documentazione | 5 |
| `search_combined(query, k)` | codice + doc; con corpora extra configurati (`SERTOR_EXTRA_CORPORA`, es. il wiki) fonde **più collezioni** — feature 010, [[indexing-and-retrieval|dettagli]] | 6 |

Il fan-out multi-collezione arriva **gratis** al server senza toccarlo (è il senso del thin-consumer: la
capacità vive nella facade, la superficie la eredita dalla configurazione).

Dal 2026-06-12 (FEAT-005, PR #25) sono **tornati i 4 tool di navigazione strutturale** sul
[[code-graph]] — la promessa del docstring è mantenuta:

| Tool | Domanda a cui risponde |
|---|---|
| `find_symbol(name)` | dove è definito il simbolo (path, riga, kind, qualname) |
| `who_calls(name)` | chi lo chiama (chiamanti diretti) |
| `related_docs(name)` | quali documenti lo menzionano |
| `get_context(name)` | bundle multi-hop: definizioni + chiamanti + chiamate + basi + doc |

Delegano al servizio `build_graph_service()` del core (memoizzato come la facade); risposte
citabili `ref = path#qualname`; simbolo assente → liste vuote; grafo non costruito o extra
`graph` assente → errore strutturato azionabile (mai crash).

La facade è costruita **una volta** con `build_facade(Settings.load())` memoizzata via `@lru_cache(maxsize=1)`
e riusata da tutti i tool. Dal 2026-06-12 (PR #23) il warm-up è **eager**: `main()` costruisce la facade
**prima** di `mcp.run()`, perché l'init pigro di Chroma dentro la prima tool call ne **parcheggia la
risposta su Windows** — il task non riprende finché stdin non riceve un altro evento (prima query di
sessione appesa indefinitamente; sbloccata solo dal cancel del client). Costo: ~1s all'avvio, dentro il
timeout di connect del client (30s). Test di guardia: `test_main_warms_facade_before_stdio_loop`.

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
`SERTOR_CORPUS=sertor` → fa **[[dogfooding]]** sul corpus di produzione. Le promesse del 2026-06-08
sono state mantenute entrambe il 2026-06-12: il retrieval **ibrido** arriva gratis dalla facade
([[hybrid-retrieval]], PR #24) e i tool di **grafo** sono registrati (FEAT-005, PR #25). Il warm-up
di `main()` copre facade E grafo (tollerante ad assenze).

## Affidabilità e segnalazione dei guasti (dal 2026-06-14)

A partire da 2026-06-14, il server implementa una strategia di **segnalazione esplicita degli errori su tre
strati** (vedi record nel log del 2026-06-14):

1. **Helper `_guard` sui tool:** ogni tool è avvolto in un wrapper che cattura gli errori, emette un evento
   `mcp.<tool>.error` nello store di osservabilità ([[ports-adapters|FEAT-020]]) e **ri-solleva l'errore
   invariato** (non lo inghiotte). Così gli errori compaiono nei report e nei pannelli TUI.
2. **Self-test allo startup:** `_self_test()` esercita una ricerca end-to-end (embedding + BM25). Un guasto
   (key invalida, extra mancante, store rotto) emerge immediatamente su stderr al reconnect; indice assente
   NON è un errore (degrada a lista vuota per coerenza con la policy della facade).
3. **Governance anti-silenzio:** i tool agenti (`requirements-analyst`, `speckit-plan`, ecc.) e il rituale
   in `CLAUDE.md` impongono di **segnalare esplicitamente gli errori MCP** invece di degradare silenziosamente
   a fallback (Read/Grep manuale).

**Nota operativa:** dal 2026-06-18 (E10-FEAT-002) c'è **un solo venv** `.venv` e `.mcp.json` lo punta
(`.venv/Scripts/python.exe`). Si mantiene coerente con `uv sync --all-packages --extra dev` (+ `--extra
azure` per il dogfood): l'extra `dev` include ora `mcp` e `graph`, quindi lo stesso comando che prepara
test e lint prepara anche il server. Il vecchio `.venv-core` (costruito a mano, sorgente della divergenza
silenziosa) è stato eliminato.

## Troubleshooting (metodo collaudato, 2026-06-12)

Quando una chiamata MCP sembra appesa o il server pare morto:

1. **Log lato client (la fonte migliore):** Claude Code scrive un file per sessione in
   `%LOCALAPPDATA%\claude-cli-nodejs\Cache\C--Workspace-Git-Sertor\mcp-logs-sertor-rag\*.jsonl` —
   handshake, ogni `Calling MCP tool`, i `still running (Ns elapsed)`, gli errori e le risposte
   scartate (`unknown message ID`). In sessione: comando `/mcp` per lo stato del server.
2. **Log lato server:** i `log_event` del core (`op=retrieve`, `op=mcp.<tool>`) escono su **stderr**
   del subprocess — visibili solo lanciando il server a mano. I guasti sono ora anche tracciati nel
   report di affidabilità se `SERTOR_OBSERVABILITY=true`.
3. **Probe fuori sessione:** pilotare il server con un driver JSON-RPC su stdio (initialize →
   initialized → tools/call) misurando i tempi, tenendo stdin aperto; se la risposta arriva solo
   chiudendo stdin, l'esecuzione era parcheggiata nell'event loop (la firma dell'episodio
   2026-06-12). Per bisezionare: server FastMCP minimo + un tool per componente (Settings / Chroma /
   embed / facade). Driver usati: `%TEMP%\mcp_probe.py`, `mcp_probe2.py`, `mini_mcp*.py`.
4. **Ricordare:** il server gira da `.venv` (editable su `src/`) → serve il codice del **branch
   correntemente checked-out**; va riavviato (nuova sessione o riconnessione) per servire codice nuovo.

## Vedi anche
- Il pattern che incarna: [[thin-consumer]]. Cosa consuma: [[indexing-and-retrieval]] · [[retrieval-core]].
- Guida ai 7 tool: [[retrieval-vs-graph]] — quando usare ricerca (scopri) vs grafo (naviga).
- A cosa serve: [[dogfooding]]. Naming del corpus: [[corpus-index-naming]].
