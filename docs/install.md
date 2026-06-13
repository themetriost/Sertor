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

**Code-graph strutturale (FEAT-005):** ogni `sertor-rag index .` costruisce anche il **grafo del
codice** (nodi modulo/classe/funzione/metodo/doc; archi contains/calls/imports/inherits/mentions),
persistito in `<index_dir>/graph/<corpus>.json` — il build non richiede dipendenze extra. Per
**navigarlo** (i 4 tool MCP `find_symbol` / `who_calls` / `related_docs` / `get_context`) serve
l'extra:

```bash
uv add "sertor-core[graph] @ git+https://github.com/themetriost/Sertor"   # networkx
```

```bash
SERTOR_GRAPH=true               # build del grafo dentro index() (default)
SERTOR_GRAPH_AMBIGUITY=2        # nomi più ambigui di così non generano archi calls
SERTOR_GRAPH_LIMIT_DEFS=10      # limiti per sezione di get_context
SERTOR_GRAPH_LIMIT_RELS=8
SERTOR_GRAPH_LIMIT_DOCS=8
```

Simbolo assente → liste vuote; grafo non costruito → errore che dice di indicizzare; extra
assente → errore con l'istruzione d'installazione. La copertura degli archi per linguaggio è
**dichiarata**: nodi e gerarchia per tutti i 10 linguaggi sintattici, chiamate per tutti,
import/ereditarietà per Python.

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
di Sertor come esempio). Il sottocomando `install governance` è pianificato ma non ancora disponibile.

## 6. Capacità RAG con un comando: `sertor install rag`

`sertor install rag` porta l'intera capacità RAG su un repo ospite — **anche non-Python** (es. .NET):
il runtime Python vive **isolato** in una dotfolder `.sertor/` (i tuoi sorgenti non vengono toccati),
in radice restano solo il `.mcp.json` (il ponte verso Claude/client MCP) e il `.gitignore` aggiornato.

```bash
# da una macchina con `uv`, nella radice del repo target (Azure embeddings):
uv run sertor install rag --backend azure
# varianti:
uv run sertor install rag --backend local --no-rerank   # Ollama, senza reranker
uv run sertor install rag --no-deps                      # solo scaffold di config (no uv add)
uv run sertor install rag --mcp-scope local              # niente .mcp.json nel repo (registra nel client)
uv run sertor install rag --target C:\path\repo --corpus mioprogetto --json
```

Cosa fa (tutto **senza** indicizzare — install ≠ run):

| Artefatto | Dove | Comportamento se esiste già |
|---|---|---|
| Progetto Python + dipendenze (`uv init --bare` + `uv add sertor-core[azure,mcp,graph,rerank]`) | `<target>/.sertor/` | `uv add` idempotente; `uv init` saltato se già inizializzato |
| `.env` (template per backend, **segreti vuoti** da riempire) | `<target>/.sertor/.env` | merge additivo per-chiave (mai sovrascrive i tuoi valori) |
| `.mcp.json` (server `sertor-rag` via `uv run --directory .sertor`) — scope `project` (default) | **radice host** | merge additivo (preserva gli altri server MCP) |
| Registrazione MCP nel client (`claude mcp add-json … --scope local`) — scope `local` | **fuori dal repo** (`~/.claude.json`) | idempotente (skip se già registrato); fail-fast se `claude` manca |
| `.gitignore` (`.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env`) | **radice host** | append dedup |

Default: backend `azure`, tutti gli extra (`mcp`+`graph`+`rerank`) + quello del backend; `--no-graph`
/`--no-rerank` per alleggerire, `--no-deps` per il solo scaffold. Exit `0`/`1` (errore di dominio,
fail-fast: `uv` assente o `uv add` fallito)/`2` (uso). Rieseguirlo è sicuro (stato identico).

Dopo l'install (passo esplicito separato — riempi prima i segreti in `.sertor/.env`):

```bash
uv run --directory .sertor sertor-rag index ..   # indicizza i sorgenti host, esclude `.sertor/`
# poi ricarica il client MCP: approva il server `sertor-rag` → search_code/docs/combined (+ grafo)
```

> Il server e la CLI girano con cwd `.sertor/`, quindi caricano `.sertor/.env` e tengono indice e
> grafo dentro `.sertor/`. **Disinstallare** ≈ cancellare `.sertor/` e la voce `sertor-rag` da `.mcp.json`.

> **Nota distribuzione (interim).** L'esecuzione standalone via `uvx --from "git+…#subdirectory=packages/sertor"`
> è **verificata**: `uv` risolve `sertor-core` scoprendo il workspace dal checkout git (lo costruisce
> dallo stesso repo, non da PyPI). In sviluppo dal repo Sertor si usa `uv run sertor install rag`.

## 7. Igiene della radice host: cosa resta e perché

L'installer tiene la **radice dell'ospite minima e prevedibile**. Dopo `install wiki`/`install rag`
in radice restano **solo** questi residenti, ciascuno per un motivo:

| Residente | Perché è in radice |
|---|---|
| `.claude/`, `CLAUDE.md` | li legge il client (Claude Code) lì; posizione non configurabile |
| `wiki/` | documentazione del progetto, by-design; **contiene** `wiki/wiki.config.toml` (la config del wiki non è più sparsa in radice) |
| `.gitignore` | append delle voci di runtime |
| `.sertor/` | **unica** sede del runtime RAG (progetto, `.venv`, indice, `.env`): nulla del runtime finisce in radice |
| `.mcp.json` | **solo** con `--mcp-scope project` (default): il project-scope di Claude Code DEVE stare in radice. Con `--mcp-scope local` non c'è alcun file MCP nel repo |

**Config del wiki in `wiki/`.** Gli strumenti la localizzano con `--config wiki/wiki.config.toml
--root .` oppure, dalla radice host, senza flag (auto-discovery: `sertor-wiki-tools <op>` cerca
`./wiki.config.toml` e poi `./wiki/wiki.config.toml`).

> **Migrazione di ospiti già installati**: fuori ambito. Su un ospite con un vecchio
> `wiki.config.toml` in radice, l'installer non lo sposta né lo rimuove; per adottare il nuovo layout
> sposta il file in `wiki/` a mano (i path interni — `root = "wiki"` — restano validi con `--root .`).
