# Contract — Tool MCP di `sertor_mcp`

**Phase 1**. Contratto della superficie MCP esposta dal server `sertor-rag` (produzione). Il client
MCP scopre i tool via il protocollo (`list_tools`) e li invoca per nome. Trasporto: **stdio**.

## Server

- **Nome**: `sertor-rag`
- **Avvio**: `python -m sertor_mcp.server` (lo lancia il client via `.mcp.json`)
- **Instructions** (metadati): guida alla scelta del tool (codice vs doc vs combinato) e alla
  citazione dei file. *(FR-014)*

## Tool 1 — `search_code`

- **Descrizione**: cerca nel **codice** sorgente (implementazioni, funzioni, classi, usi).
- **Input**: `query: string` (obbligatorio), `k: integer` (opzionale).
- **Output**: `list[Result]` con `source == "code"` per ogni elemento.
- **Mapping**: `RetrievalFacade.search_code(query, k)`.

## Tool 2 — `search_docs`

- **Descrizione**: cerca nella **documentazione** Markdown (spiegazioni, guide, decisioni, spec, wiki).
- **Input**: `query: string` (obbligatorio), `k: integer` (opzionale).
- **Output**: `list[Result]` con `source == "doc"` per ogni elemento.
- **Mapping**: `RetrievalFacade.search_docs(query, k)`.

## Tool 3 — `search_combined`

- **Descrizione**: cerca su **codice + doc** insieme (quando servono implementazione e spiegazione).
- **Input**: `query: string` (obbligatorio), `k: integer` (opzionale).
- **Output**: `list[Result]` (`source` misto).
- **Mapping**: `RetrievalFacade.search_combined(query, k)`.

## Tipo `Result` (identico per i tre tool)

```jsonc
{
  "path":    "string",   // path del documento (= id stabile)
  "source":  "code|doc",  // tipo sorgente (doc_type)
  "chunk":   "string",   // id del chunk (path#indice)
  "score":   0.0,         // pertinenza (number, arrotondato)
  "preview": "string"    // testo, troncato a soglia con marcatore se eccede
}
```

## Comportamenti contrattuali

| Condizione | Comportamento |
|------------|---------------|
| Indice assente per il corpus configurato | Lista **vuota** + warning loggato; nessun crash. *(FR-012/REQ-050)* |
| Nessun hit per la query | Lista **vuota** (non è errore). |
| `k` omesso | Si usa il default del motore (`Settings.default_k`). |
| Testo del risultato oltre soglia | `preview` troncato + marcatore. *(FR-011)* |
| Errore interno al motore | Errore **leggibile** propagato al client; server resta vivo, nessuno stato parziale. *(FR-013/REQ-051)* |
| Tool non disponibili (grafo/ibrido) | **Non registrati**: il client vede solo i 3 tool. *(scope; FR-017 per il futuro)* |

## Invarianti di superficie (testabili)

- `list_tools()` espone esattamente `{search_code, search_docs, search_combined}` (⊇, l'MVP non
  registra altri tool). *(SC-002)*
- Le chiavi di ogni `Result` sono esattamente `{path, source, chunk, score, preview}`. *(FR-010)*
- `search_code` → tutti `source=="code"`; `search_docs` → tutti `source=="doc"`. *(FR-003)*
- Sola lettura: nessun tool muta indice/corpus/filesystem. *(FR-004)*

## Osservabilità (contratto operativo, RNF-004 / Principio IX)

Ogni invocazione emette un log strutturato con almeno: nome tool, `k` effettivo, numero di risultati,
tempo di esecuzione, backend/provider e corpus; warning dedicato su indice assente. Nessun segreto nei
log.
