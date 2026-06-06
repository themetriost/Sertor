# Quickstart — Server MCP di produzione (`sertor_mcp`)

Come configurare, indicizzare e usare il server MCP di Sertor su un client come Claude Code.

## 1. Installazione (con l'extra MCP)

```bash
uv sync --extra mcp           # installa l'SDK MCP isolato (oltre al core)
# o, in alternativa: uv sync --extra mcp --extra dev   (per i test)
```

> Senza `--extra mcp` la libreria core resta installabile **senza** l'SDK MCP (isolamento, REQ-060).

## 2. Configurazione (`.env`)

Il server legge la configurazione centralizzata del core. Esempio locale:

```bash
RAG_BACKEND=local             # local (Chroma+Ollama) | azure
SERTOR_CORPUS=sertor          # corpus di prodotto (dogfood su Sertor stesso)
# (provider/endpoint Azure se RAG_BACKEND=azure — mai committare i segreti)
```

## 3. Costruzione dell'indice di produzione (precondizione, FUORI da questa feature)

I tool restituiscono risultati solo se esiste un indice per il corpus `sertor`. La costruzione è del
**nucleo/CLI** (FEAT-001/FEAT-009); finché non c'è, i tool restituiscono `[]` + warning (degrado
pulito). Indicizzare i sorgenti di produzione: `src/`, `specs/`, `requirements/`, `wiki/`.

> Senza indice il server **parte comunque** e non crasha (US2/FR-012).

## 4. Binding del client (`.mcp.json` alla radice del repo)

```json
{
  "mcpServers": {
    "sertor-rag": {
      "command": ".venv-core/Scripts/python.exe",
      "args": ["-m", "sertor_mcp.server"],
      "env": { "SERTOR_CORPUS": "sertor" }
    }
  }
}
```

> Sostituisce il binding del **prototipo** (`prototype/04-agentic-rag/mcp_server.py`,
> `SERTOR_CORPUS=prototype`): da ora il client interroga la **produzione** (FR-015/SC-007).

## 5. Uso dai tool (dal client MCP)

- `search_code("come viene costruita la facade di retrieval")` → hit di **codice**.
- `search_docs("policy di errore del nucleo")` → hit di **documentazione/spec/wiki**.
- `search_combined("idempotenza dell'indicizzazione")` → **codice + doc** insieme.

Ogni risultato: `path`, `source` (`code`/`doc`), `chunk`, `score`, `preview` (troncata).

## 6. Verifica rapida

```bash
uv run pytest tests/unit/test_mcp_server.py        # tool registrati, formato, filtro per tipo (mock)
```

Acceptance manuale (US1): con un indice `sertor` presente, dal client invocare i 3 tool e verificare
che restituiscano risultati pertinenti e citabili; (US2) senza indice, verificare lista vuota +
warning e che il server resti vivo.
