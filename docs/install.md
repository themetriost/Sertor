# Installare Sertor su un altro repository

> **Stato: guida-ponte (interim).** Sertor non è ancora su PyPI: la distribuzione ufficiale interim è
> **`git+url`** (decisione DA-4 dell'epica CLI). L'installer guidato — `sertor install <capacità>` —
> è in roadmap; finché non arriva, questa guida copre il percorso manuale: **capacità RAG completa**
> (indicizzazione + ricerca + server MCP) e **tooling wiki deterministico**. Il sistema-wiki completo
> (skill agentiche + rituale) oggi richiede copia manuale, non documentata qui: arriverà con
> `sertor install wiki`.

## Prerequisiti

- **Python ≥ 3.11** e [`uv`](https://github.com/astral-sh/uv) (consigliato; in alternativa `pip`).
- Un provider di **embeddings**, a scelta:
  - **locale** — [Ollama](https://ollama.com) in esecuzione (`ollama serve`) con un modello di
    embedding: `ollama pull nomic-embed-text`;
  - **cloud** — un deployment **Azure OpenAI** di `text-embedding-3-*`.

## 1. Installazione del pacchetto

Nel repository target:

```bash
# base (locale: Ollama + Chroma)
uv add "sertor-core @ git+https://github.com/themetriost/Sertor"

# con gli extra cloud e/o server MCP
uv add "sertor-core[azure,mcp] @ git+https://github.com/themetriost/Sertor"
```

Con `pip`: `pip install "sertor-core @ git+https://github.com/themetriost/Sertor"`.

L'installazione porta **tre cose**: la libreria `sertor_core` (importabile) e i due console-script
**`sertor-rag`** (esecuzione RAG) e **`sertor-wiki-tools`** (nucleo wiki deterministico).

> **install ≠ run**: installare o importare non avvia mai indicizzazioni — ogni operazione richiede
> un comando esplicito.

## 2. Configurazione (`.env` nel repo target, mai committato)

Tutte le scelte operative si leggono dalla configurazione centralizzata (env e/o `.env`). Minimo
indispensabile:

**Locale (default):**
```bash
RAG_BACKEND=local
OLLAMA_HOST=http://localhost:11434     # default, omettibile
SERTOR_CORPUS=nome-progetto            # namespace della collezione (consigliato)
```

**Azure (embeddings cloud + store Chroma locale — combinazione consigliata):**
```bash
RAG_BACKEND=azure
SERTOR_STORE_BACKEND=local             # vector store Chroma locale
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large
SERTOR_CORPUS=nome-progetto
```

Se la configurazione del backend scelto è incompleta, ogni comando si **blocca prima di contattare
qualunque servizio**, elencando le variabili mancanti. Opzionali utili: `SERTOR_INDEX_DIR` (cartella
dell'indice, default `.index` — aggiungila al `.gitignore` dell'ospite), `SERTOR_EXCLUDE_PATTERNS`,
`DEFAULT_K`, `SERTOR_PREVIEW_CHARS`.

## 3. Primi comandi

```bash
uv run sertor-rag index .                          # indicizza il repository (full rebuild)
uv run sertor-rag search "come funziona X?"        # top-k con path, tipo, score, anteprima
uv run sertor-rag search "build pipeline" -k 10 --type code --json   # per script/agenti
uv run sertor-rag index . -v                       # con log strutturati visibili
```

Exit code: `0` successo · `1` errore di dominio (messaggio leggibile su stderr) · `2` uso errato.
Guida completa della CLI: [`specs/011-cli-esecuzione-rag/quickstart.md`](../specs/011-cli-esecuzione-rag/quickstart.md).

## 4. Server MCP (per Claude Code e altri client MCP)

Con l'extra `mcp` installato, aggiungi al repo target un `.mcp.json`:

```json
{
  "mcpServers": {
    "sertor-rag": {
      "command": "uv",
      "args": ["run", "python", "-m", "sertor_mcp.server"],
      "env": { "SERTOR_CORPUS": "nome-progetto" }
    }
  }
}
```

Il server espone `search_code` / `search_docs` / `search_combined` sullo stesso indice della CLI
(stessi risultati a parità di configurazione).

## 5. Tooling wiki (deterministico)

`sertor-wiki-tools` (scan/lint/structure/collect/index/append-log/…) funziona su qualunque ospite a
partire da una **`wiki.config.toml`** alla radice del progetto (vedi quella di Sertor come esempio).
Bootstrap della struttura: `uv run sertor-wiki-tools structure init`.

Il **sistema-wiki completo** (skill `wiki-author`+playbook, comando `/wiki`, agente `wiki-curator`,
rituale di step nel `CLAUDE.md` dell'ospite) sarà installato da **`sertor install wiki`** — feature
in elicitazione; fino ad allora la parte agentica va copiata a mano da `.claude/` di questo repo.
