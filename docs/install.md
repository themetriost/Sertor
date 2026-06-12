# Installare Sertor su un altro repository

> **Stato.** Sertor non è ancora su PyPI: la distribuzione interim è **`git+url`** (decisione DA-4
> dell'epica CLI). La guida copre: **capacità RAG completa** (indicizzazione + ricerca + server MCP),
> **tooling wiki deterministico** e — dalla feature 012 — l'**installer guidato `sertor install
> wiki`** che porta sull'ospite l'intero sistema-wiki (skill agentiche, rituale, config, struttura)
> con un solo comando.

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

**Motore di retrieval (FEAT-004):** il default è il motore **ibrido** (BM25 lessicale + vettoriale
fusi con RRF) — migliora nettamente le query a simbolo/termine esatto:

```bash
SERTOR_ENGINE=hybrid       # baseline | hybrid (default: hybrid)
SERTOR_RRF_C=60            # costante della fusione RRF
SERTOR_RRF_POOL=30         # candidati per fonte prima della fusione
SERTOR_RERANK=false        # secondo stadio cross-encoder (richiede l'extra `rerank`)
SERTOR_RERANK_POOL=15      # pool fuso passato al reranker (~3×k)
```

> **Migrazione:** un corpus indicizzato **prima** dell'ibrido continua a funzionare (degradazione
> a solo-vettoriale con warning nei log); un **re-index** (`sertor-rag index .`) costruisce anche
> l'indice lessicale e abilita l'ibrido. Per il reranking opzionale: installare l'extra
> (`uv add "sertor-core[rerank] @ git+…"`) e impostare `SERTOR_RERANK=true` — senza extra,
> `SERTOR_RERANK=true` produce un errore esplicito con l'istruzione d'installazione.

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

## 5. Sistema-wiki completo: `sertor install wiki`

Col pacchetto installer (`sertor`, fornito dal workspace — arriva con l'install `git+url`), un solo
comando porta sull'ospite l'intero sistema-wiki:

```bash
uv run sertor install wiki                          # nella radice del repo target
uv run sertor install wiki --target C:\path\repo    # oppure su un path esplicito
uv run sertor install wiki --language it --source-dirs src,docs   # override dei default
```

Cosa installa (tutto **senza** avviare indicizzazioni, LLM o rete — install ≠ run):

| Artefatto | Comportamento se esiste già |
|---|---|
| Skill `wiki-author` (playbook + moduli ops), comando `/wiki`, agente `wiki-curator`, hook di sessione | skip **file-per-file** (mai sovrascritti) |
| Voci hook in `.claude/settings.json` | **merge additivo** con deduplicazione (gli hook tuoi restano) |
| Sezione *rituale di step* nel `CLAUDE.md` | inserita in un **blocco a marker** `SERTOR:WIKI-RITUAL`; tutto il resto del file è intoccato |
| `wiki.config.toml` | generato con default inferiti (lingua `en`, `source_dirs` dalle cartelle standard presenti); mai sovrascritto |
| Struttura `wiki/` (tassonomia, indice, log) | `structure init` idempotente |

Il comando stampa un **report** per artefatto (`created`/`skipped`/`merged`/`block`) ed esce con
`0` (successo), `1` (errore di dominio, fail-fast con stato parziale esplicito — il re-run completa
i buchi) o `2` (uso errato). Rieseguirlo è sicuro: stato identico, zero duplicati. Prerequisito per
l'hook di sessione: PowerShell (`pwsh`) sull'ospite; senza, il wiki resta pienamente usabile (i
promemoria automatici non scattano).

### Tooling wiki deterministico (già incluso nel pacchetto core)

`sertor-wiki-tools` (scan/lint/structure/collect/index/append-log/…) funziona su qualunque ospite a
partire dalla **`wiki.config.toml`** (quella generata dall'installer, o scritta a mano usando quella
di Sertor come esempio). I sottocomandi `install rag` e `install governance` sono pianificati ma non
ancora disponibili.
