# Contract — MCP tool `search_combined` (070, DA-d)

Server `sertor-rag` (`src/sertor_mcp/server.py`). Breaking change della **forma di output** del solo
tool `search_combined`; `search_code`/`search_docs` e gli altri 4 tool invariati.

## Firma

```python
@mcp.tool()
def search_combined(query: str, k: int = 6) -> dict
```

## Output (NUOVO — oggetto etichettato)

```json
{
  "docs": [ { "path": "...", "source": "doc",  "chunk": "...#3", "score": 0.41, "preview": "…" } ],
  "code": [ { "path": "...", "source": "code", "chunk": "...#7", "score": 0.38, "preview": "…" } ]
}
```

| Aspetto | Contratto |
|---|---|
| Forma | `{"docs": [...], "code": [...]}` (era `list[dict]`) — i due flussi etichettati per l'agente (FR-005/SC-007) |
| Elemento | invariato: `_fmt(r)` (`path`/`source`/`chunk`/`score`/`preview`), formato citabile `path#chunk` |
| Budget | ogni lista fino a `k` (default 6), budget separato |
| Una lista vuota | la chiave esiste comunque con `[]` (forma sempre strutturata) |
| Errore | `_guard` invariato: persiste `mcp.search_combined.error` e **ri-solleva** (visibilità, Principio XII) |
| `search_code`/`search_docs` | `list[dict]` invariato |

## Note

- La docstring del tool e le `instructions` del server menzionano che `search_combined` rende i due
  flussi etichettati (testo aggiornato; semantica «use when both are needed» invariata).
- `_run` per il combined adatta la serializzazione (consuma `FusedResults`, serializza le due liste);
  il log di superficie `mcp.search_combined` resta (può riportare `docs`/`code` counts).

## Test attesi

- `test_mcp_server.py`: il tool ritorna un `dict` con chiavi `docs`/`code`, ciascuna lista di dict con
  i campi `_fmt`; una superficie vuota → chiave con `[]`.
- errore del facade → evento `mcp.search_combined.error` + ri-sollevato (invariato).
