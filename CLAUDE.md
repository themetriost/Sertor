# CLAUDE.md

Guida per Claude Code in questo workspace.

## Scopo del workspace

Workspace di **esplorazione e apprendimento** per confrontare diversi approcci RAG
(Retrieval-Augmented Generation) in Python, con focus sull'ecosistema
**Microsoft/Azure**. Ogni approccio vive in una sotto-cartella auto-contenuta ed è
eseguibile **in locale** (local-first), con i servizi **Azure attivabili via config**.

## Approcci RAG da esplorare

| Cartella | Approccio | Note |
|----------|-----------|------|
| `01-baseline/` | Baseline (vector retrieval) | chunking + embeddings + similarity search |
| `02-hybrid-reranking/` | Hybrid + reranking | keyword/BM25 + dense + reranking |
| `03-graphrag/` | GraphRAG | retrieval su knowledge graph |
| `04-agentic-rag/` | Agentic RAG | retrieval iterativo / multi-agente, query planning |

## Stack tecnologico

Lo stack ha due "tracce" intercambiabili via config (vedi `RAG_BACKEND` sotto):

- **Linguaggio:** Python >= 3.11.
- **Orchestrazione:** LangChain (generale), **Semantic Kernel** (Microsoft),
  **AutoGen** (multi-agente Microsoft).
- **LLM / embeddings:**
  - Locale / aperto: **Ollama** (es. `llama3.x`, `nomic-embed-text`), OpenAI pubblico.
  - Azure: **Azure OpenAI Service** (deployment GPT + `text-embedding-3-*`).
- **Retrieval / vector store:**
  - Locale: **Chroma** (embedded) come default.
  - Azure: **Azure AI Search** (hybrid search + semantic ranker + vector index) e
    **Azure Cosmos DB for NoSQL** (vector search integrato).
  - GraphRAG: store a grafo (`networkx` in-memory in locale; Neo4j opzionale).
- **Reranking:** Azure AI Search semantic ranker (Azure); cross-encoder locale
  (`sentence-transformers` / FlashRank) in locale.
- **GraphRAG:** pacchetto **Microsoft GraphRAG** (`graphrag`).

### Mappa approcci → tecnologie

- **Baseline:** LangChain + Chroma + embeddings Ollama/OpenAI; variante Azure con
  Azure OpenAI embeddings + Azure AI Search **o** Cosmos DB for NoSQL.
- **Hybrid + reranking:** Azure AI Search (hybrid + semantic ranker) come riferimento;
  variante locale BM25 + dense + cross-encoder.
- **GraphRAG:** pacchetto Microsoft `graphrag` con Azure OpenAI o Ollama come backend LLM.
- **Agentic RAG:** AutoGen e/o Semantic Kernel per orchestrazione multi-step/multi-agente;
  agenti LangChain come alternativa.

## Struttura del progetto

Convenzione **"una cartella per approccio"**, ciascuna auto-contenuta. Lo switch tra
backend locale e Azure è guidato da **config**, non da cartelle duplicate.

```
RAG/
├─ CLAUDE.md
├─ 01-baseline/            # chunk + embed + similarity search
├─ 02-hybrid-reranking/    # hybrid retrieval + reranking (Azure AI Search / locale)
├─ 03-graphrag/            # Microsoft GraphRAG
├─ 04-agentic-rag/         # AutoGen / Semantic Kernel
└─ shared/                 # config, loaders, eval comuni (opzionale)
```

Ogni cartella dovrebbe avere un proprio `README.md`, i requirements e un entry-point eseguibile.

## Setup ed esecuzione

- **Ambiente / dipendenze:** preferire **`uv`** (fallback `venv` + `pip`). Usare
  ambienti **isolati per esperimento** per evitare conflitti di dipendenze (es. `graphrag`).
- **Segreti:** sempre via file **`.env`** (mai committare). Variabili tipiche:

  ```bash
  # Locale / OpenAI pubblico
  OPENAI_API_KEY=
  OLLAMA_HOST=http://localhost:11434

  # Azure OpenAI
  AZURE_OPENAI_ENDPOINT=
  AZURE_OPENAI_API_KEY=
  AZURE_OPENAI_DEPLOYMENT=

  # Azure AI Search
  AZURE_SEARCH_ENDPOINT=
  AZURE_SEARCH_API_KEY=

  # Azure Cosmos DB for NoSQL
  COSMOS_ENDPOINT=
  COSMOS_KEY=

  # Selettore backend: local | azure
  RAG_BACKEND=local
  ```

- **Switch backend:** la variabile `RAG_BACKEND` (`local` | `azure`) alterna
  local-first ↔ Azure senza modificare il codice.
- **Ollama in locale:** avviare il servizio (`ollama serve`) e fare il pull dei modelli
  (es. `ollama pull llama3.1`, `ollama pull nomic-embed-text`) prima di lanciare gli esperimenti locali.

## Convenzioni di codice

- Codice leggibile; **config centralizzata** per lo switch provider/backend/modelli.
- Nessuna over-engineering: aggiungere astrazioni solo quando un esperimento le richiede.
- Mantenere ogni esperimento eseguibile in locale senza dipendere da Azure.

## Git & versionamento (regola SEMPRE attiva)

Questo workspace è un **repo git locale** (al momento senza remote). Convenzione: **un commit
dopo ogni step** di lavoro significativo (incluso l'aggiornamento del wiki). Messaggi in stile
**Conventional Commits in italiano** (`tipo(scope): sommario`; scope tipici `01-baseline`,
`02-hybrid-reranking`, `03-graphrag`, `shared`, `wiki`), corpo che spiega il *perché*, footer
`Co-Authored-By`. **Mai committare** `.env`, `*.key`, il contenuto di `raw/`, i virtualenv o gli
artefatti rigenerabili (`output/`, `cache/`, `logs/`, `metrics/`, indici/store vettoriali): sono
coperti da `.gitignore`.

> **Delega (non bloccante):** le operazioni git vanno **delegate all'agente `configuration-manager`**
> (modello Haiku, vedi `.claude/agents/configuration-manager.md`), lanciato **in background** durante
> o dopo uno step, così il flusso principale non si blocca sul versionamento. Passagli un brief
> autocontenuto (cosa è stato fatto, file/percorsi, motivo, operazione richiesta). L'agente fa
> staging selettivo + commit con messaggio convenzionale e riporta hash e file inclusi. Le operazioni
> **distruttive/irreversibili** (`push --force`, `reset --hard`, riscrittura di storia, `branch -D`,
> `clean -fd`, ...) le esegue **solo se richieste esplicitamente** nel brief; altrimenti si ferma e
> segnala. Per step piccoli o puramente meccanici puoi committare direttamente.

## Wiki & documentazione (regola SEMPRE attiva)

Questo workspace mantiene un **wiki locale** in [`wiki/`](wiki/), ispirato al pattern
"LLM Wiki" di Karpathy. Lo scopo: il wiki è un artefatto persistente e cumulativo che
cresce a ogni sessione, invece di ricostruire la conoscenza ogni volta.

> **Regola aurea:** ogni cosa di rilievo che facciamo va documentata nel wiki. Non aspettare
> che l'utente lo chieda: l'aggiornamento è implicito. Vale per esperimenti eseguiti, decisioni
> prese, concetti/tecnologie approfonditi e fonti ingerite. Modifiche puramente meccaniche e di
> poco conto non richiedono una voce.

> **Delega (non bloccante):** l'aggiornamento del wiki va **delegato all'agente `wiki-keeper`**
> (modello Haiku, vedi `.claude/agents/wiki-keeper.md`), lanciato **in background** durante o
> dopo un'attività di progetto, così il flusso principale non si blocca sul bookkeeping.
> Passagli un brief autocontenuto (cosa è stato fatto, file/percorsi, numeri/esiti, commit).
> Quando l'agente ha finito, includi le modifiche al wiki nel commit dello step. Per attività
> piccole o puramente meccaniche puoi non delegare.

### Struttura
- `raw/` — fonti esterne **immutabili** (solo lettura): `articles/`, `papers/`, `assets/`.
- `wiki/index.md` — catalogo globale (link + summary). **Leggilo per primo**; aggiornalo a ogni modifica.
- `wiki/log.md` — registro **append-only** di tutto ciò che facciamo.
- `wiki/concepts/` — concetti RAG. `wiki/tech/` — tecnologie. `wiki/experiments/` — un file per esperimento.
- `wiki/sources/` — riassunti di fonti esterne. `wiki/syntheses/` — confronti/sintesi trasversali (creati su richiesta).

### Operazioni
- **record** — dopo aver costruito/eseguito qualcosa o preso una decisione: crea/aggiorna
  la pagina rilevante (es. `experiments/01-baseline.md`), aggiorna i backlink e `index.md`,
  e appendi una voce a `log.md`.
- **ingest** — nuova fonte in `raw/`: scrivi un riassunto in `sources/`, integra nelle pagine
  concept/tech collegate, segnala contraddizioni, aggiorna `index.md` e `log.md`.
- **query** — domande sul wiki: rispondi citando le pagine; se l'esplorazione è preziosa,
  archiviala come nuova pagina (le query si cumulano in conoscenza).
- **lint** — verifica periodica: contraddizioni, claim superati, pagine orfane, cross-ref mancanti.

### Convenzioni
- **Frontmatter YAML** in ogni pagina: `title`, `type`, `tags`, `created`, `updated`, `sources`.
- **Backlink** in stile wikilink `[[nome-pagina]]` (compatibile Obsidian); i link relativi
  Markdown vanno bene per la navigazione da editor/GitHub. Mantieni i cross-reference aggiornati.
- **Naming** file: kebab-case descrittivo (es. `azure-ai-search.md`, `hybrid-search.md`).
- **Voce di log**: `## [YYYY-MM-DD] <operazione> | <titolo>` (operazione ∈ setup/ingest/record/query/lint).
- Crea una **nuova** pagina per un concetto/entità nuovo; **aggiorna** quella esistente altrimenti.
- Quando una fonte nuova contraddice una pagina, **segnala esplicitamente** la contraddizione.

Per innescare manualmente un consolidamento usa il comando **`/wiki`** (lavora nel flusso
principale) oppure delega all'agente `wiki-keeper` (in background). Un hook `SessionStart`
carica lo stato del wiki a inizio sessione. Non c'è più uno `Stop` hook bloccante: la
manutenzione è garantita dalla delega al `wiki-keeper`, non dal blocco del turno.
