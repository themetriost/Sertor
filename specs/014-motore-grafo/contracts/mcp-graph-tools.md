# Contract — I 4 tool di grafo nel server MCP

Superficie sottile (`src/sertor_mcp/server.py`): ogni tool delega al servizio di grafo del core
(`build_graph_service()` memoizzato), zero logica reimplementata (FR-020). I 3 tool di ricerca
esistenti restano INVARIATI (FR-019).

## Firme (come il prototipo, A-6)

| Tool | Firma | Risposta |
|---|---|---|
| `find_symbol` | `(name: str)` | lista di `{path, line, kind, qualname, ref}` |
| `who_calls` | `(name: str)` | lista di `{path, line, kind, qualname, ref}` |
| `related_docs` | `(name: str)` | lista di `{path, ref}` |
| `get_context` | `(name: str)` | `{definitions[], callers[], callees[], bases[], docs[]}` (sezioni limitate dai knob) |

- `ref = path#qualname` (o `path` per i doc): citabile, coerente col formato `path#chunk` dei
  tool di ricerca (FR-018/REQ-025).
- Simbolo assente → liste vuote (risposta valida, non errore).
- Docstring dei tool in italiano, descrittive per l'agente (pattern dei 3 esistenti).

## Errori (strutturati, mai crash — FR-021/FR-022)

| Condizione | Risposta |
|---|---|
| Grafo non costruito | tool error con messaggio `GraphNotFoundError`: costruire il grafo con `sertor-rag index .` |
| Extra `graph` non installato | tool error con messaggio `ConfigError`: `uv add "sertor-core[graph]"` |
| Nome vuoto | tool error di validazione (FastMCP) |

## Avvio e warm-up (lezione PR #23, R-7)

`main()` estende il warm-up eager: dopo la facade, tenta il caricamento del grafo
(`_graph()` + `exists()`/load) PRIMA di `mcp.run()` — l'init pigro dentro la prima tool call
parcheggia la risposta su Windows. Se l'extra o il grafo mancano il warm-up NON fallisce:
il server parte e l'errore esplicito arriva alla chiamata del tool (DA-5).

## Log

Ogni tool emette `mcp.<tool>` (pattern esistente); il core emette `graph_query`
(operation, symbol, results, elapsed_ms — FR-027).
