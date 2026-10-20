# Quickstart — verificare la 145

## Test automatici (offline)

```powershell
uv run pytest tests/unit/test_memory_semantic.py tests/unit/test_cli_memory_semantic.py tests/unit/test_memory_archive_semantic.py -q
uv run pytest -m "not cloud"
uv run ruff check .
```

Il caso di Kaelen è riprodotto in `tests/unit/test_memory_semantic.py` con un embedder finto che
**rifiuta con `http 400` ogni testo oltre un budget** — la stessa regola del servizio reale — su una
sessione di 181 turni con un turno da ~290.000 caratteri:

- prima della correzione: `embedded=0 errors=181`;
- dopo: `embedded=181 errors=0`, e la ricerca di un termine presente solo nella coda del turno grande lo
  restituisce una volta.

## Verifica sul dogfood (provider `openai`, memoria accesa)

```powershell
uv run --project .sertor sertor-rag memory index-semantic
uv run --project .sertor sertor-rag memory index-semantic --json
```

Atteso: nessun `rejected`; un secondo run riporta `embedded=0` (incrementalità). Se il dogfood ha la
memoria semantica spenta, la verifica sul campo resta a Kaelen, a cui si risponde in bacheca.
