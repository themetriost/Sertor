# Log del Wiki

Registro **append-only** di tutto ciò che facciamo nel workspace. Voce più recente in fondo.
Formato di ogni voce: `## [YYYY-MM-DD] <operazione> | <titolo>`
dove `<operazione>` ∈ { setup, ingest, record, query, lint }.

---

## [2026-05-28] setup | Inizializzazione workspace e wiki

- Creato `CLAUDE.md` con scopo del workspace, stack (Python; LangChain/Semantic Kernel/AutoGen;
  OpenAI/Azure OpenAI/Ollama; Azure AI Search/Cosmos DB for NoSQL/Chroma; Microsoft GraphRAG)
  e impostazione local-first con Azure opzionale.
- Inizializzato il wiki locale in stile "LLM Wiki" di Karpathy: `raw/`, `wiki/` con
  `index.md`, `log.md`, e cartelle `concepts/`, `tech/`, `experiments/` (più `sources/` e
  `syntheses/` su richiesta).
- Pagine seed: [concepts/rag-overview.md](concepts/rag-overview.md), [tech/stack.md](tech/stack.md),
  [experiments/README.md](experiments/README.md).
- Aggiunto il comando locale `/wiki` (`.claude/commands/wiki.md`) per consolidare il lavoro nel wiki.
- Configurati gli hook in `.claude/settings.json` per l'aggiornamento **implicito**:
  `SessionStart` (carica `index.md` + coda di `log.md` nel contesto) e `Stop` (promemoria
  loop-safe via `stop_hook_active` che invita ad aggiornare il wiki prima di chiudere).

## [2026-05-28] record | Hook verificati attivi dopo riavvio; nota su encoding

- Dopo riavvio di Claude Code gli hook risultano **attivi**: `SessionStart` carica lo stato
  del wiki nel contesto e `Stop` emette il promemoria a fine turno (entrambi confermati).
- Problema cosmetico noto: l'output dell'hook `SessionStart` iniettato nel contesto mostra
  gli accenti corrotti (es. `è` → carattere di sostituzione). I file del wiki restano UTF-8
  corretti; è solo l'encoding con cui l'harness cattura lo stdout PowerShell.
- Fix proposto (in attesa di autorizzazione a modificare `.claude/settings.json`): anteporre
  `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;` al comando dell'hook.

## [2026-05-28] record | Architettura target dual-RAG + roadmap

- Definito l'**obiettivo finale**: dual-RAG (Code RAG + Docs RAG) fusi e consumati da agenti
  di sviluppo (Claude Code / AutoGen / SK) che, su bug/CR/feature, leggono automaticamente
  contesto combinato codice+documentazione.
- Disegnata l'architettura target (ingestion code-aware/doc-aware, indici vector+BM25+code graph,
  retrieval orchestrator con hybrid+rerank+fusion RRF, interfaccia agenti via **MCP**) con
  diagramma Mermaid → [syntheses/architettura-target.md](syntheses/architettura-target.md).
- Decisione (adattabile): retrieval esposto come **MCP server** (multi-frontend), così non
  dobbiamo scegliere ora tra Claude Code via MCP e AutoGen separato.
- Roadmap a tappe: 0) fondamenta `shared/` + eval; 1) baseline; 2) hybrid+rerank+fusione;
  3) GraphRAG (code graph + link doc↔codice); 4) agentic + MCP (obiettivo finale).
- Decisioni aperte: layer agenti, repo/doc campione, modello embedding per il codice,
  vector store Azure target.

## [2026-05-28] record | Scelto il repo campione: fastapi/fastapi

- Confrontati 3 candidati via GitHub API: `fastapi/fastapi` (47 MB, MIT), `pallets/flask`
  (12 MB, BSD, doc in `.rst`), `pydantic/pydantic` (scartato, ~406 MB).
- **Scelto `fastapi/fastapi`**: codice `fastapi/` = 48 `.py`; doc `docs/en/` = 153 Markdown;
  `docs_src/` = 454 esempi `.py` citati dai doc → relazioni doc↔codice esplicite per la fusione.
- Fissati i default (vai-tu): layer **MCP-first**, embedding codice **`nomic-embed-text`** (Ollama),
  vector store **Chroma** locale per le prime tappe. Dettagli in
  [syntheses/architettura-target.md](syntheses/architettura-target.md) (Decisioni prese).
- Prossimo passo proposto: materializzare in `raw/` il subset (`fastapi/`, `docs/en/`, `docs_src/`).

## [2026-05-28] ingest | Corpus campione fastapi/fastapi in raw/

- Materializzato `raw/fastapi/` via sparse+shallow clone: `fastapi/` (48 `.py`), `docs/en/`
  (153 `.md`), `docs_src/` (454 `.py`); ~34 MB totali. Riassunto: [sources/fastapi.md](sources/fastapi.md).
- Aggiornata la sezione Fonti di [index.md](index.md).

## [2026-05-28] record | Embedding multi-provider + prerequisiti locali

- Decisione: confronto embedding **fin dall'inizio** tra `nomic-embed-text` (Ollama, locale)
  e Azure AI Foundry `text-embedding-3-small` e `text-embedding-3-large`, via layer intercambiabile.
- Prerequisiti verificati: git 2.53, uv 0.11, ollama 0.24 (servizio attivo). Scaricato
  `nomic-embed-text` (274 MB) e verificato l'endpoint embeddings locale → **768 dim**, OK.
- Python di sistema è 3.14 (con pywin32 rotto): l'ambiente esperimenti userà **venv `uv` + Python 3.12**.
- Aperto: configurare i deployment Azure Foundry in `.env` per abilitare il percorso cloud.

## [2026-05-28] record | Connettività embedding verificata (3 provider)

- Creato `shared/check_embeddings.py` (solo stdlib) e configurato `.env` (+ `.env.example`,
  `.gitignore`). Verificati **tutti e 3** i provider con un embedding di test:
  Ollama `nomic-embed-text` = 768 dim; Azure `text-embedding-3-small` = 1536; `-large` = 3072.
- Azure usa l'**endpoint v1** (`.../openai/v1`), route `/embeddings`, auth header `api-key`.
- Percorso Azure ora ABILITATO: il confronto multi-provider è eseguibile da subito.

## [2026-05-28] setup | Repo git locale + commit per step

- Inizializzato il workspace come **repo git locale** (no remote). Convenzione: **un commit
  dopo ogni step** di lavoro significativo (incluso l'aggiornamento del wiki).
- `.gitignore`: esclusi `.env` (contiene la API key) e il contenuto di `raw/` (fonti vendored,
  riproducibili via `sources/*.md`), mantenendo `raw/README.md`.
