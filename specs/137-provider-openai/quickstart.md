# Quickstart — provider `openai`

Verifica end-to-end della feature (PowerShell, dalla radice del progetto ospite).

1. Nel `.env` del runtime (`.sertor/.env` per un ospite installato):

   ```
   SERTOR_EMBED_PROVIDER=openai
   OPENAI_API_KEY=sk-...
   # facoltative:
   # OPENAI_EMBED_MODEL=text-embedding-3-large
   # OPENAI_BASE_URL=https://api.openai.com/v1
   ```

   ⚠️ **Solo a mano.** Il wizard `sertor configure` (installer congelato, perimetro Kaelen) conosce
   solo i profili `azure`/`local`: con `--set` scrive **solo** i campi del proprio catalogo, quindi
   `--set OPENAI_API_KEY=…` e `--set SERTOR_EMBED_PROVIDER=openai` verrebbero **ignorati senza avviso**
   (verificato in `configure.py:267-275`).

2. Controllo statico e sonda:

   ```powershell
   uv run --project .sertor sertor-rag doctor
   uv run --project .sertor sertor-rag doctor --online
   ```

   Atteso: `provider pass`; con `--online` la sonda raggiunge il servizio.

3. Re-index (il cambio di provider crea una collezione nuova, quelle esistenti restano):

   ```powershell
   uv run --project .sertor sertor-rag index .
   ```

   Atteso: `collection=<corpus>__openai_text-embedding-3-large`, `embedding_dim=3072`.

4. Ricerca da CLI e, dopo aver riavviato il server MCP (`/mcp` → reconnect), da agente:

   ```powershell
   uv run --project .sertor sertor-rag search "dove si sceglie il provider di embedding"
   ```

5. Guasti attesi:
   - chiave vuota → `doctor` fallisce sull'area *provider* nominando `OPENAI_API_KEY`;
   - chiave errata → errore `provider=openai:text-embedding-3-large, reason=http 401`, senza la chiave.

Costo indicativo: `text-embedding-3-large` ≈ 0,13 $ per milione di token; un re-index completo di un
repository di medie dimensioni costa centesimi, e la cache degli embedding evita di ripagare i chunk
invariati.
