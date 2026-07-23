---
title: Server MCP sertor-rag
type: tech
tags: [mcp, server, sertor-mcp, thin-consumer, retrieval, dogfooding, sertor-core]
created: 2026-06-08
updated: 2026-07-23
sources: ["src/sertor_mcp/server.py", ".mcp.json"]
---

# Server MCP sertor-rag

Il **server MCP `sertor-rag`** (`src/sertor_mcp/server.py`) è la **superficie** che rende il
[[retrieval-core]] usabile **nativamente da un agente LLM**: espone la ricerca vettoriale del nucleo come
**tool MCP** (Model Context Protocol) via stdio. È l'esempio canonico di [[thin-consumer|consumatore
sottile]] — delega tutto alla facade del core, non reimplementa retrieval — e **sostituisce** il vecchio
server del prototipo come superficie attiva (FEAT-MCP, record: [[server-mcp-produzione-feat-mcp]]).

## I dieci tool

Istanza `FastMCP("sertor-rag")` con `instructions` che guidano la scelta del tool. Il server espone
**10 tool**: i **3 di ricerca** + i **4 di navigazione** sul [[code-graph]] + i **3 di memoria**
conversazionale (E4, gated). I tool di ricerca/grafo delegano al metodo omonimo della
[[indexing-and-retrieval|facade]] / `build_graph_service()`:

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

Dal 2026 (E4-FEAT-010/013) ci sono i **3 tool di memoria conversazionale** — parità sola-lettura con i
comandi `memory` della [[sertor-rag-cli|CLI]], sugli stessi servizi del core (`MemoryArchive`,
`EpisodicSearch`, indice semantico):

| Tool | Domanda a cui risponde |
|---|---|
| `memory_list(limit)` | quali sessioni passate sono archiviate (recency-first) |
| `memory_show(session_key)` | mostra i turni di una sessione (index, role, ts, text) |
| `memory_search(query, k, semantic)` | «ne abbiamo già parlato?» — full-text FTS5 (default) o per **significato** (`semantic=true`) |

Sono **opt-in per privacy** (gate `SERTOR_MEMORY`; il semantico richiede anche
`SERTOR_MEMORY_SEMANTIC`): con la leva spenta — il default — i builder ritornano `None` e il tool
risponde `{"status": "disabled"}` con l'hint della leva giusta (mai una lista vuota che fingerebbe
«nessun risultato», mai un errore che inonderebbe `mcp.*.error`). Sola lettura: nessun path di
cattura/scrittura nel server (la `archive` resta sulla CLI e sul session-end).

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

Trasporto **stdio**: lo lancia il client MCP via `.mcp.json`
(`uv run --project .sertor python -m sertor_mcp.server`) con env `SERTOR_CORPUS=sertor` → fa
**[[dogfooding]]** sul corpus di produzione. Dal 2026-07-03 (E15) il server gira dal **runtime
install-based `.sertor/`** (il pacchetto installato via `sertor install rag`, che segue HEAD e viene
re-locked a ogni merge), **non** più dall'editable del workspace. Le promesse del 2026-06-08
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

**Nota operativa (runtime install-based, dal 2026-07-03, E15):** `.mcp.json` **non** punta più a un
interprete di venv (`command: "uv"`, `args: ["run", "--project", ".sertor", "python", "-m",
"sertor_mcp.server"]`): `uv run --project .sertor` risolve il server dentro il **runtime `.sertor/`**,
il pacchetto `sertor-core` **installato** via `sertor install rag` (da `git=<repo>` HEAD, re-locked a
ogni merge — è il dogfood come client fedele). Supera il modello precedente (E10-FEAT-002, 2026-06-18)
in cui c'era **un solo venv** `.venv` puntato direttamente da `.mcp.json` (`.venv/Scripts/python.exe`);
quel `.venv` resta l'ambiente di **sviluppo** (test/lint via `uv sync --all-packages --extra dev`), ma
il **server servito ai client gira dal `.sertor/`**, non dall'editable del workspace.

## Troubleshooting (metodo collaudato, 2026-06-12; aggiornato 2026-06-19)

Quando una chiamata MCP sembra appesa o il server pare morto:

1. **Log lato client (la fonte migliore):** Claude Code scrive un file per sessione in
   `%LOCALAPPDATA%\claude-cli-nodejs\Cache\C--Workspace-Git-Sertor\mcp-logs-sertor-rag\*.jsonl` —
   handshake, ogni `Calling MCP tool`, i `still running (Ns elapsed)`, gli errori e le risposte
   scartate (`unknown message ID`). In sessione: comando `/mcp` per lo stato del server.
2. **Log lato server:** i `log_event` del core (`op=retrieve`, `op=mcp.<tool>`) escono su **stderr**
   del subprocess — visibili solo lanciando il server a mano. I guasti sono ora anche tracciati nel
   report di affidabilità se `SERTOR_OBSERVABILITY=true`.
3. **Client Chroma stantio dopo re-index (dal 2026-06-19):** se `search_code` e `search_docs` tornano
   `InternalError` mentre `search_combined` regge, il client Chroma del server è divergente dallo store
   riscritto su disco (il process mantiene in memoria una connessione che non vede le modifiche). Sintomo
   gemello: `find_symbol` ritorna righe obsolete. **Rimedio immediato:** riconnettere il server (nuova
   sessione o comando `/mcp` + riconnessione). **Il client si auto-guarisce** — è il pattern
   [[auto-heal-staleness]], oggi su **quattro** fronti: `ChromaStore.query()` ricrea il client su errore e
   riprova (PR #89); il **code-graph** è cachiato su `(mtime_ns, size)` e si ricarica a cambio disco (PR
   #90); l'**indice lessicale BM25** ricarica i token su cambio disco (A-03); il **lock d'indice** stantio
   con PID morto viene reclamato (FEAT-035). Così la staleness non dovrebbe più accadere. Se persiste:
   riconnetti il server o avvia una nuova sessione.
4. **Probe fuori sessione:** pilotare il server con un driver JSON-RPC su stdio (initialize →
   initialized → tools/call) misurando i tempi, tenendo stdin aperto; se la risposta arriva solo
   chiudendo stdin, l'esecuzione era parcheggiata nell'event loop (la firma dell'episodio
   2026-06-12). Per bisezionare: server FastMCP minimo + un tool per componente (Settings / Chroma /
   embed / facade). Driver usati: `%TEMP%\mcp_probe.py`, `mcp_probe2.py`, `mini_mcp*.py`.
5. **Ricordare:** il server gira dal **runtime `.sertor/`** (pacchetto installato, `git=<repo>` HEAD)
   → serve il codice del **commit su cui il runtime è lockato**, non l'editable del workspace. Dopo un
   merge su `master` va **re-locked** (`scripts/dev/relock-runtime.ps1`) e il server **riavviato** (nuova
   sessione o riconnessione) per servire codice nuovo. L'artefatto del code-graph è invece auto-refreshed
   su cambio disco (mtime/size), quindi nessuna staleness del grafo nemmeno tra re-index e riavvio — solo
   il codice del server resta stantio finché non si re-locka + riavvia.

## Vedi anche
- Il pattern che incarna: [[thin-consumer]]. Cosa consuma: [[indexing-and-retrieval]] · [[retrieval-core]].
- Guida ai tool di ricerca vs grafo: [[retrieval-vs-graph]] — quando usare ricerca (scopri) vs grafo (naviga).
- A cosa serve: [[dogfooding]]. Naming del corpus: [[corpus-index-naming]].
