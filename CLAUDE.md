# CLAUDE.md

Guida per Claude Code in questo workspace.

## Scopo del workspace

Il workspace è entrato nella **fase di produzione**: si costruisce il CLI **`sertor`**
(pacchetto installabile `uv`/`pip`; requisiti in
[`requirements/sertor-cli/epic.md`](requirements/sertor-cli/epic.md)).

Il precedente **prototipo di esplorazione** (4 approcci RAG su corpus FastAPI, focus
Microsoft/Azure, local-first) è stato **isolato e congelato** in [`prototype/`](prototype/):
non si modifica più a mano, lo si consulta tramite il **RAG di dogfooding** (vedi
*Riferirsi al prototipo* sotto). La radice ospita la produzione (`requirements/`, nuovo
`wiki/`, governance `.claude/` + `.specify/`).

## Approcci RAG del prototipo (riferimento, in `prototype/`)

| Cartella | Approccio | Note |
|----------|-----------|------|
| `prototype/01-baseline/` | Baseline (vector retrieval) | chunking + embeddings + similarity search |
| `prototype/02-hybrid-reranking/` | Hybrid + reranking | keyword/BM25 + dense + reranking |
| `prototype/03-graphrag/` | GraphRAG | retrieval su knowledge graph |
| `prototype/04-agentic-rag/` | Agentic RAG | retrieval iterativo / multi-agente, query planning |

## Riferirsi al prototipo (RAG di dogfooding)

Il prototipo è **congelato**: per consultarlo **non** si leggono i file a mano, si **interroga il
RAG**. Il server MCP **`sertor-rag`** (in `.mcp.json`) è puntato sul **prototipo come corpus**
(`SERTOR_CORPUS=prototype`) — facciamo *dogfooding* del nostro stesso strumento. Tool: `search_code` /
`search_docs` / `search_combined` (codice e doc del prototipo), `find_symbol` / `who_calls` /
`related_docs` (relazioni nel code-graph), `get_context` (fusione codice↔doc). Ricostruzione indici
dogfood: `SERTOR_CORPUS=prototype python prototype/01-baseline/index.py --provider azure-large`
(Chroma) e `… prototype/03-graphrag/build_graph.py` (grafo AST).

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

Confine netto **prototipo (congelato) ↔ produzione (attiva)**:

```
Sertor/
├─ CLAUDE.md                # questa guida
├─ requirements/           # PRODUZIONE: requisiti (epica sertor-cli, EARS) — fase a monte
├─ wiki/                   # PRODUZIONE: wiki nuovo e attivo (LLM Wiki)
├─ .claude/  .specify/     # governance: skill/agenti, SpecKit
├─ .mcp.json               # server MCP `sertor-rag` → corpus dogfood (prototype)
└─ prototype/              # PROTOTIPO CONGELATO (sola lettura, indicizzato nel RAG dogfood)
   ├─ 01-baseline/ … 04-agentic-rag/   # i 4 motori RAG
   ├─ shared/              # config, loaders, embeddings, retrieval (motore corpus-aware)
   ├─ tests/  raw/         # smoke test + corpus FastAPI
   └─ wiki/                # wiki storico del prototipo (congelato)
```

Il motore in `prototype/shared/` è **corpus-aware** (env `SERTOR_CORPUS`: `fastapi` = demo del
prototipo · `prototype` = dogfooding sul prototipo stesso); gli indici sono namespaced per corpus
(`.index` vs `.index-prototype`), così demo FastAPI e dogfood coesistono senza sovrascriversi.

## Il nucleo di produzione: `sertor-core` (`src/`)

La produzione vive in `src/sertor_core/` (pacchetto `sertor-core`, `pyproject.toml` a root): una
libreria di retrieval **importabile**, costruita in **Clean Architecture** sotto i principi della
costituzione (`.specify/memory/constitution.md`). È **il prodotto** — il CLI/MCP ne sarà un
consumatore sottile.

**Architettura (le dipendenze puntano verso l'interno):**

```
domain/         entità (Document, Chunk, RetrievalResult, GraphNode, …), SEI porte Protocol
                (EmbeddingProvider, VectorStore, LexicalIndex, Reranker, CodeGraph,
                RetrieverStrategy), errori — NESSUN import di SDK
services/       ingestion · chunking (code/markdown/fallback + dispatch) · indexing · retrieval
                (facade) · graph_extraction (code-graph multi-linguaggio, COVERAGE dichiarata)
adapters/       embeddings/{ollama,azure} · vectorstores/{chroma,azure_search} · lexical/bm25
                · rerank/flashrank (extra `rerank`) · graph/networkx (extra `graph`, lazy solo query)
engines/        baseline (vettoriale) · hybrid (BM25+RRF+rerank opzionale, DEFAULT via
                SERTOR_ENGINE) · evaluation (hit_rate@k, MRR)
config/         Settings — config centralizzata (UNICA fonte di default; legge env + .env)
observability/  logging strutturato
composition.py  composition root: l'UNICO posto che conosce gli adapter concreti e li cabla da
                Settings (build_facade/build_indexer/build_engine/build_graph_service/…)
```

Regole architetturali da rispettare quando si estende il core:
- **Il `domain` non importa SDK esterni.** I provider concreti vivono in `adapters/` dietro le SEI
  porte `Protocol` di `domain/ports.py` (`EmbeddingProvider`, `VectorStore`, `LexicalIndex`,
  `Reranker`, `CodeGraph`, `RetrieverStrategy`); structural typing → si mockano senza ereditarietà
  (vedi `tests/fixtures/mocks.py`).
- **Si sceglie l'implementazione SOLO in `composition.py`**: l'embedder da `Settings.backend`
  (`local`→Ollama · `azure`→Azure OpenAI) e lo store da `Settings.store_backend` (`local`→Chroma ·
  `azure`→Azure AI Search) — **manopole distinte** (FEAT-009, `store_backend` default = `backend`): si
  combinano, es. embeddings Azure + store Chroma locale (l'indice dogfood `sertor`). Per aggiungere un
  provider/backend si estende il composition root e gli adapter, **non** i servizi. Gli import degli SDK
  pesanti sono **lazy** dentro le `build_*` (NFR isolamento dipendenze: l'extra `azure` non serve in locale).
- **Default solo in `Settings`**, mai hardcodati nei componenti. I consumatori entrano da
  `build_facade()` / `build_indexer()` / `build_engine()` / `build_graph_service()` /
  `build_baseline_engine()` (riesportati da `__init__.py`). Il motore si sceglie con
  `SERTOR_ENGINE` (default `hybrid`); il code-graph è ORTOGONALE ai motori e si costruisce
  dentro `index()` (default `SERTOR_GRAPH=true`).
- **Policy errori non uniforme e voluta:** il nucleo è *tollerante* (indice mancante → `[]` + warning,
  per composabilità); il motore baseline è *strict* (solleva `IndexNotFoundError`, per usabilità del
  consumatore). Non "uniformare" questa differenza.
- **Idempotenza:** `engine.index()` fa rebuild-from-scratch; l'`upsert` è idempotente sugli stessi id.
- Le collezioni sono namespaced per `(corpus, provider)` via `collection_name()` — provider diversi
  (→ dimensioni vettore diverse) non si mescolano nella stessa collezione.

## Sviluppo (`sertor-core`): build, test, lint

Si usa **`uv`** (il progetto ha `uv.lock`). Anteporre `uv run` esegue nel venv del progetto.

```bash
uv sync --extra dev                 # crea/sincronizza l'env con le dipendenze di sviluppo
uv run pytest                       # intera suite (i test cloud/integration partono se l'env c'è)
uv run pytest -m "not cloud"        # salta i test che richiedono credenziali/servizi cloud
uv run pytest tests/unit            # solo unit test (veloci, no rete)
uv run pytest tests/unit/test_baseline_engine.py::test_query_returns_results_with_fields  # singolo test
uv run ruff check .                 # lint (regole E,F,I,UP,B; line-length 100)
uv run ruff check --fix .           # lint con autofix
```

I marker pytest sono definiti in `pyproject.toml`: `cloud` (richiede credenziali Azure/servizi) e
`integration` (end-to-end). La CI locale gira **senza cloud**: i test devono passare con
`RAG_BACKEND=local` e adapter mock, senza rete. `pythonpath` include già `src` e root (nessun
`pip install -e` necessario per i test). Esistono due venv: `.venv-core/` (nucleo) e `.venv/`.

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

  # Motore di retrieval (FEAT-004): baseline | hybrid (default hybrid). Manopole opzionali:
  # SERTOR_RRF_C, SERTOR_RRF_POOL, SERTOR_RERANK (richiede extra `rerank`), SERTOR_RERANK_POOL
  SERTOR_ENGINE=hybrid

  # Code-graph strutturale (FEAT-005): build dentro index() (default true). Navigazione = extra
  # `graph`. Manopole: SERTOR_GRAPH_AMBIGUITY, SERTOR_GRAPH_LIMIT_{DEFS,RELS,DOCS}
  SERTOR_GRAPH=true
  ```

- **Switch backend:** la variabile `RAG_BACKEND` (`local` | `azure`) alterna
  local-first ↔ Azure senza modificare il codice.
- **Ollama in locale:** avviare il servizio (`ollama serve`) e fare il pull dei modelli
  (es. `ollama pull llama3.1`, `ollama pull nomic-embed-text`) prima di lanciare gli esperimenti locali.

## Convenzioni di codice

- Codice leggibile; **config centralizzata** per lo switch provider/backend/modelli.
- Nessuna over-engineering: aggiungere astrazioni solo quando un esperimento le richiede.
- Mantenere ogni esperimento eseguibile in locale senza dipendere da Azure.

## Domande all'utente (regola SEMPRE attiva)

Ogni volta che si pone una domanda all'utente (bivi di design, clarify, scelte di scope, conferme),
**prima** della domanda va dato il **contesto**: da dove nasce il problema (file/meccanismo reale),
cosa comporta concretamente ciascuna opzione (pro/contro, impatti su consumatori e convenzioni del
repo) e la raccomandazione motivata. Mai una domanda "secca" con sole etichette: l'utente deve poter
decidere senza dover chiedere "spiegami meglio". Vale anche per le domande poste dentro i flussi
SpecKit (`clarify`, `specify`, ecc.).

## Rituale di step / Definition of Done (regola SEMPRE attiva)

Uno **step** è un'unità di lavoro significativa (una feature, un fix, una decisione, una ricerca,
un'analisi). **Alla fine di ogni step**, il flusso principale (Claude) esegue — **di propria
iniziativa, senza che l'utente debba chiederlo** — questa checklist. Sono **azioni da LLM nel loop**:
le eseguo io, qui, esattamente come già scrivo le voci di log. **Non** dipendono da hook né da
automazione *unattended*: la distinzione è netta —

- *automatico unattended* = far scattare qualcosa **quando non c'è nessuno** (timer/evento → script o
  `claude -p` headless; un hook non ragiona, non avvia un subagent in-loop);
- *comportamento standing* = ciò che faccio **sistematicamente mentre lavoriamo**, perché è il mio modo
  di operare. Il rituale qui sotto è di questo secondo tipo: per esso **non esiste alcun limite tecnico**.

1. **Registra** — appende la voce nel log (con la rotazione attiva, il **file del giorno**
   `wiki/log/<data>.md` via `append-log`) + pagine impattate e `index.md`: operazione `record` del
   playbook. *(già attivo)*
2. **Distilla le entità** — non lasciare la conoscenza durevole **sepolta nel record datato**: identifica le
   **entità/concetti** che lo step ha toccato o fatto emergere (entità di dominio, porte, adapter, servizi,
   decisioni, tecnologie) e dà a ciascuna — se ha **identità propria** ed è **referenziata da più punti** —
   una **pagina propria** ricca e ben fatta in `concepts/`/`tech/` (page-craft + lente di prodotto di
   wiki-craft); il record `experiment` resta **magro** e vi *punta*. È l'operazione `distill` del playbook
   (N2). **È giudizio → resta nel flusso principale (Opus), non a Haiku**, come il lint semantico. Il **caso
   tipico** è una **feature appena implementata** (il record nasce magro, le entità in pagine). Calibra al
   valore: uno step che non tocca entità durevoli non la innesca.
3. **Lint semantico di allineamento** — verifica che il wiki **non sia andato alla deriva** rispetto
   alla realtà del progetto (codice in `src/`, `specs/`, `requirements/`, stato git): **segnala
   esplicitamente ogni claim che il repo contraddice**; correggi su conferma. Va **oltre** il `lint`
   meccanico (link rotti/orfani/frontmatter): è il confronto *contenuto del wiki ↔ realtà del progetto*.
   **Metodo ripetibile:** operazione `lint`, livello B (semantico) del playbook — estrai claim → ground truth
   (git via VCS, RAG/`Read`+`Grep`, test) → giudizio → report con severità → correggi su conferma.
   **È giudizio, non trascrizione: resta nel flusso principale (Opus) e NON si delega a Haiku** — il
   flusso principale ha già il contesto dello step, mentre un agente lo rileggerebbe a freddo (più
   costoso e più lossy). Se in casi pesanti va proprio delegato, usa un override `sonnet`
   per-invocazione, **mai** il default Haiku del `wiki-curator`.
4. **Executive Summary della roadmap** — a inizio sessione il contesto deve aprirsi con un **riassunto
   executive** dello stato di prodotto. Vive in testa a `wiki/syntheses/roadmap.md`, tra i marker
   `<!-- EXEC:START -->` e `<!-- EXEC:END -->`, ed è **responsabilità del flusso principale** tenerlo
   vero. **Forma (vincolante):** *executive* — sta in una schermata, scansionabile, basta a un agente
   che riprende **a freddo** per sapere «dove siamo e cosa fare adesso»; niente narrazione/storia (sta
   nei record/log). Tre bucket in quest'ordine: **🔄 IN PROGRESS** (per ogni voce, in dettaglio: *cosa* ·
   *dove* (branch/`specs/`/file) · *prossimo passo concreto* · *blocco/decisione aperta*) · **📋 PLANNED**
   (deciso ma non iniziato, una riga, per priorità) · **✅ DONE** (capacità su `master`, una riga, solo le
   rilevanti — non un changelog). **Quando:** nello stesso commit dello step, ogni volta che lo step
   **cambia lo stato di una capacità** (planned→in progress→done; cambia il *prossimo passo* o si
   scioglie/apre un blocco di un IN PROGRESS; una voce entra/esce dal PLANNED); gli step che non toccano
   lo stato di prodotto **non** lo innescano. **Confine:** è **giudizio** ancorato alla realtà del repo
   (git, `specs/`, `src/`) → resta nel **flusso principale (Opus)**, non a Haiku, come distill e lint
   semantico; il blocco executive e la mappa-feature sottostante **non devono contraddirsi**. **Iniezione
   (non è compito del rituale):** il SessionStart hook è **sottile** — non *trasporta* il contenuto (il
   canale-hook è limitato a ~10.000 caratteri: l'indice da solo lo sforerebbe), ma **istruisce** il flusso
   principale a caricarlo a freddo con il tool `Read` (`wiki/syntheses/roadmap.md`, `wiki/index.md`, l'ultimo
   file di `wiki/log/`) — l'output del `Read` entra **intero** nel contesto, nessun cap — e poi a **mostrare
   all'utente l'executive summary** della roadmap. L'hook *innesca*, il `Read` *trasporta*, il rituale tiene
   il *contenuto* vero.
5. **Re-index del corpus toccato** — se lo step ha modificato **file indicizzati nel corpus RAG**,
   ricostruisci l'indice, così il RAG di dogfooding non serve mai contesto stantio (è l'essenza:
   contesto dell'agente sempre reale). **Modello a corpus unico (decisione 2026-06-10):** il wiki vive
   **dentro** il progetto ospite *by design* (lo crea così l'install della futura CLI) → è parte del
   corpus primario come documentazione (`doc_type=doc`); niente corpus separato per il retrieval, niente
   `SERTOR_EXTRA_CORPORA` sul dogfood. Quindi: **qualsiasi** modifica indicizzata (`src/`, `specs/`,
   `requirements/`, `wiki/`, doc di radice) → rebuild del corpus **`sertor`**
   (`build_indexer().index(root, rebuild=True)`). Il rebuild è **full ma sicuro**: `reset` della
   collezione *dopo* l'embedding (atomico) e namespaced. È **meccanico** → delegabile/in background;
   richiede l'ambiente di embeddings attivo (oggi Azure: centesimi a rebuild). **Calibra al valore:**
   step ravvicinati → basta un re-index a fine giornata/sessione; momento *obbligato*: dopo un **merge
   su `master`**. Mitigante operativo in attesa della FEAT-009 d'epica (refresh incrementale, Could).
   NB: il server MCP legge l'indice da disco ma va **riavviato** per servire *codice* nuovo, non per
   indici nuovi. La query congiunta multi-collezione (feature 010) resta capacità di prodotto per
   ospiti con corpora **davvero disgiunti**; il rag-sync del wiki (`sertor-wiki-tools index`) resta
   esercitabile come test della capacità, non è parte del rituale.

6. **Mostra la roadmap dopo il merge su main** — **quando** uno step si chiude con un **merge su
   `master`/`main`** (consegna di una feature/fix), a valle del rituale **mostra all'utente
   l'executive summary** della roadmap (il blocco tra i marker `<!-- EXEC:START -->` e
   `<!-- EXEC:END -->` di `wiki/syntheses/roadmap.md`), così dopo ogni consegna si vede subito *dove
   siamo e cosa fare adesso*. È **giudizio del flusso principale** (presuppone che lo step 4 abbia già
   reso vero l'EXEC). **Fallback:** se `wiki/syntheses/roadmap.md` **non esiste**, non inventarla a
   freddo — **chiedi all'utente** (con contesto: cosa contiene una roadmap di prodotto, perché serve)
   e, su conferma, **creala** (struttura: blocco EXEC con tabella a colpo d'occhio + IN PROGRESS /
   PLANNED / DONE, poi mappa feature × stato). Si innesca **solo** al merge, non a ogni step.

7. **Riassunto non tecnico (explainer)** — quando uno step **sviluppa o pianifica una capacità
   significativa** (un requisito/epica, una feature, una capacità di prodotto), produci o aggiorna una
   **descrizione in linguaggio comune** nell'area `wiki/explainers/` (per non tecnici): cosa fa e
   perché, con un'immagine quotidiana e zero gergo, e un rimando «dettaglio tecnico» alla pagina di
   concetto/feature corrispondente. **È giudizio** (scrivere per chi non è tecnico, lente di prodotto)
   → resta nel **flusso principale** come distill/lint, non a Haiku. **Calibra al valore (opzionale):**
   solo per capacità che vale spiegare a uno stakeholder non tecnico — non per lo step meccanico o di
   solo tooling. Vale sia per ciò che è *fatto* sia per ciò che si *sta per sviluppare* (la pagina
   marca lo stato). Fa parte dell'**asset installabile** (`claude-md-block.md`): gli ospiti ricevono
   questa pratica con il sistema-wiki. Vedi [[step-ritual]] e la panoramica [[sertor-in-parole-semplici]].

8. **\<altre azioni\>** — questa lista è **estendibile**: ogni azione che l'utente chiede di rendere
   *standing* va aggiunta qui, e da quel momento fa parte del rituale a ogni step.

**Responsabilità & delega.** Che queste azioni **avvengano** a ogni step è responsabilità del flusso
principale. Eseguirle direttamente oppure **delegarle** è solo una scelta per non bloccare il flusso —
la delega **non è un modo per saltarle**. **Confine di delega netto:** il `record` (trascrizione
strutturata: pagine, backlink, `index.md`, voce di log) si delega al `wiki-curator` (Haiku),
perché è lavoro di forma rette dal brief; la **distillazione** (punto 2) e il **lint semantico** (punto 3),
essendo **giudizio**, **restano nel flusso principale**, non a Haiku. Git si delega al `configuration-manager`. Gli hook `SessionStart`/`Stop`
restano **promemoria vincolanti**, non opzionali.

**Calibra al valore:** modifiche puramente meccaniche o di poco conto non innescano il rituale (vedi
*regola aurea* del wiki). Lo step è "significativo" quando produce conoscenza, decisioni o codice.
Vedi [[step-ritual]].

**Quando registrare (VINCOLANTE): nello stesso momento del commit.** La voce di log **non è
posticipabile**: si scrive **insieme al commit** dello step — un passo non è "chiuso" finché commit **e**
voce di log non sono **entrambi** fatti. Con `sertor-wiki-tools append-log` (corpo curato da stdin) è **un
comando**: non c'è attrito che giustifichi il rinvio. **Cosa si registra:** ogni step *significativo*,
**incluse le evoluzioni di tooling/governance** (sistema-wiki, `CLAUDE.md`, playbook) — il log registra
*cosa abbiamo fatto*, non solo i contenuti del wiki; «il tooling non è una *pagina*» **non** significa «il
tooling non si *logga*». Resta esente **solo** il triviale/meccanico. Il promemoria dello `Stop` hook è una
**rete di sicurezza**: se scatta, vuol dire che ho già mancato il momento giusto (il commit) — non è il
meccanismo che fa la registrazione.

## Git & versionamento (regola SEMPRE attiva)

Questo workspace è un **repo git con remote `origin`** (ci si pusha regolarmente). **Policy di branching durante la fase di prototipo (attuale):** commit e push **direttamente su `master`/`main`** (autorizzato). Al passaggio in produzione si adotterà **SpecKit** e si lavorerà a **branch + PR** (niente più push diretti su main). Convenzione: **un commit dopo ogni step** di lavoro significativo (incluso l'aggiornamento del wiki). Messaggi in stile
**Conventional Commits in italiano** (`tipo(scope): sommario`; scope tipici `01-baseline`,
`prototype`, `requirements`, `cli`, `shared`, `wiki`), corpo che spiega il *perché*, footer
`Co-Authored-By`. **Mai committare** `.env`, `*.key`, il contenuto di `raw/`, i virtualenv o gli
artefatti rigenerabili (`output/`, `cache/`, `logs/`, `metrics/`, indici/store vettoriali): sono
coperti da `.gitignore`.

> **Delega (SEMPRE, non bloccante):** **tutte** le operazioni git (staging, commit, branch,
> merge, tag, push, pull, ...) vanno **delegate all'agente `configuration-manager`**
> (modello Haiku, vedi `.claude/agents/configuration-manager.md`), lanciato **in background** durante
> o dopo uno step, così il flusso principale non si blocca sul versionamento. **Non** eseguire git
> direttamente (nemmeno per step piccoli o meccanici). Passagli un brief autocontenuto (cosa è stato
> fatto, file/percorsi, motivo, operazione richiesta). L'agente fa staging selettivo + commit con
> messaggio convenzionale e riporta hash e file inclusi. Le operazioni **distruttive/irreversibili**
> (`push --force`, `reset --hard`, riscrittura di storia, `branch -D`, `clean -fd`, ...) le esegue
> **solo se richieste esplicitamente** nel brief; altrimenti si ferma e segnala.

## Wiki & documentazione (regola SEMPRE attiva)

Questo workspace mantiene un **wiki locale** in [`wiki/`](wiki/), ispirato al pattern
"LLM Wiki" di Karpathy. Lo scopo: il wiki è un artefatto persistente e cumulativo che
cresce a ogni sessione, invece di ricostruire la conoscenza ogni volta.

> **Regola aurea:** ogni cosa di rilievo che facciamo va documentata nel wiki. Non aspettare
> che l'utente lo chieda: l'aggiornamento è implicito. Vale per esperimenti eseguiti, decisioni
> prese, concetti/tecnologie approfonditi e fonti ingerite. Modifiche puramente meccaniche e di
> poco conto non richiedono una voce.

> **Delega (non bloccante):** l'aggiornamento del wiki va **delegato all'agente `wiki-curator`**
> (modello Haiku, vedi `.claude/agents/wiki-curator.md`), lanciato **in background** durante o
> dopo un'attività di progetto, così il flusso principale non si blocca sul bookkeeping.
> Passagli un brief autocontenuto (cosa è stato fatto, file/percorsi, numeri/esiti, commit).
> Quando l'agente ha finito, includi le modifiche al wiki nel commit dello step. Per attività
> piccole o puramente meccaniche puoi non delegare.

### Struttura
- `prototype/raw/` — corpus **immutabile** del prototipo (FastAPI). Nuove fonti di produzione andranno in un `raw/` a root quando servirà.
- `wiki/index.md` — catalogo globale (link + summary). **Leggilo per primo**; aggiornalo a ogni modifica.
- `wiki/log/` — registro **append-only**, un file per giorno (`YYYY-MM-DD.md`, rotazione FEAT-008); scritto via `append-log`.
- `wiki/concepts/` — concetti RAG. `wiki/tech/` — tecnologie. `wiki/experiments/` — un file per esperimento.
- `wiki/sources/` — riassunti di fonti esterne. `wiki/syntheses/` — confronti/sintesi trasversali (creati su richiesta).

### Operazioni
> **Fonte operativa unica:** procedure, convenzioni e tassonomia di dettaglio vivono nel
> **Wiki Playbook** (`.claude/skills/wiki-author/wiki-playbook.md`). Skill `wiki-author`, comando `/wiki`
> e agente `wiki-curator` lo leggono e lo seguono. Qui sotto solo la sintesi. Il **meccanico** (scan,
> lint, collect, index, structure) è la CLI `sertor-wiki-tools` (host-agnostica, da `wiki.config.toml`).

- **record** — registra lavoro/decisioni svolti: crea/aggiorna le pagine, backlink e `index.md`, voce di log (file del giorno via `append-log`).
- **distill** — estrae le **entità/concetti durevoli** che un lavoro fa emergere in pagine proprie (`concepts/`/`tech/`), assottigliando i record datati che le contenevano. Giudizio → flusso principale; parte del rituale di step (punto 2).
- **ingest** — acquisisci una fonte esterna (file/PDF/URL) → riassunto in `sources/`, integra nelle pagine collegate, segnala contraddizioni.
- **query** — rispondi citando le pagine; se l'esplorazione è preziosa, archiviala come nuova pagina.
- **lint** — verifica di coerenza a tre livelli: A strutturale (CLI: frontmatter/wikilink rotti/orfani/naming), B semantico (claim ↔ realtà del repo), C organizzativo (collocazione/atomicità/link). Report con severità; non auto-corregge.
- **reorg** — applica il refactoring organizzativo emerso dal lint C (sposta pagine, corregge `type`, riallinea i link), su conferma. Solo flusso principale; mai automatico.
- **generate** — genera il wiki dal repo, a due ingressi: **da-zero** (bootstrap su un ospite privo di wiki — config + struttura + piano-pagine bounded + prima ondata) o **da-diff** (aggiorna solo le pagine impattate dalle modifiche recenti; il `git log/diff` è delegato al `configuration-manager`). Profondità di ricognizione a preset: `leggera` (default) / `media` / `massiva`.
- **rag-sync** — ri-indicizza il wiki nel RAG con corpus dedicato (via `sertor-wiki-tools index`, corpus da `[rag]` in config), così il wiki diventa interrogabile via RAG. Solo flusso principale.
- **structure** — bootstrap idempotente della struttura del wiki (cartelle della tassonomia + index + log) via `sertor-wiki-tools structure init`; non sovrascrive l'esistente.

### Convenzioni
- **Frontmatter YAML** in ogni pagina: `title`, `type`, `tags`, `created`, `updated`, `sources`.
- **Backlink** in stile wikilink `[[nome-pagina]]` (compatibile Obsidian); i link relativi
  Markdown vanno bene per la navigazione da editor/GitHub. Mantieni i cross-reference aggiornati.
- **Naming** file: kebab-case descrittivo (es. `azure-ai-search.md`, `hybrid-search.md`).
- **Voce di log**: `## [YYYY-MM-DD] <operazione> | <titolo>` (operazione ∈ setup/structure/record/distill/ingest/query/lint/reorg/generate/rag-sync; elenco autorevole nel playbook §6).
- Crea una **nuova** pagina per un concetto/entità nuovo; **aggiorna** quella esistente altrimenti.
- Quando una fonte nuova contraddice una pagina, **segnala esplicitamente** la contraddizione.

Per innescare manualmente un consolidamento usa il comando **`/wiki`** (lavora nel flusso
principale) oppure delega all'agente `wiki-curator` (in background).

**Hook (trigger automatici, vedi `.claude/hooks/wiki-pending-check.ps1`):**
- `SessionStart` — carica indice + coda log a inizio sessione (contesto iniettato).
- `Stop` — a fine turno, se rileva lavoro non ancora registrato (file di `src/specs/requirements/.claude`
  più recenti dell'ultima voce di log), inietta un **promemoria non bloccante** a delegare al
  `wiki-curator`. Non intrappola il turno; si auto-silenzia appena il wiki è aggiornato.
- `SessionEnd` — riepilogo finale del lavoro non registrato, come rete di sicurezza tra sessioni.

I trigger **non orchestrano da soli** (un hook non può avviare un subagent): rendono *automatica* la
delega che resta affidata al `wiki-curator`.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/023-osservabilita-tui-report/plan.md` (osservabilità F4 — pannello TUI report sfogliabili, ULTIMO
Must dell'epica: ESTENDE F3 (stessa app `sertor-rag observe`, stesso extra `[tui]`) trasformandola a
SCHEDE `TabbedContent` (Live/Cache/Cost/Corpus). Funzioni di resa PURE in `observability/live.py`
(`render_cache_report`/`render_cost_report`/`render_corpus_report(now)` — testabili senza terminale) +
finestra temporale pura `time_window(preset, now)`/`next_window` (preset all/7d/24h, ciclo con binding
`t`, mostrato in sub-title). Freschezza = `now - last_index_ts` (no confronto repo). Rende i report di F2
(thin consumer), sola lettura, degradazione onesta (store vuoto → stato vuoto; € assente → ripiego
token). Nessuna nuova dipendenza/manopola (riusa F2/F3). Constitution PASS 10/10. Branch
`023-osservabilita-tui-report`. Storico:
`specs/022-osservabilita-tui-live/plan.md` (osservabilità F3 — pannello TUI vista live: prima superficie
VISIBILE. Due strati: (1) modello di stato PURO `LiveSnapshot` + `live_snapshot(reports)` in
`observability/live.py` (compone i report di F2, testabile SENZA terminale); (2) guscio Textual
`ObservabilityApp` + `run_live_panel(settings)` in `observability/tui.py`, refresh su timer rileggendo i
report (DA-O-c = pull periodico, `SERTOR_OBSERVABILITY_REFRESH` default 2s). Textual = extra OPZIONALE
`[tui]` (import lazy; assente → ConfigError azionabile come rerank/graph; + textual nel dev per i test
headless via Pilot). Avvio: sottocomando `sertor-rag observe`. Sola lettura; persistenza spenta → stato
vuoto onesto (no crash). +`ObservabilityReports.recent_events` (additivo su F2). Constitution PASS 10/10.
Branch `022-osservabilita-tui-live`. Storico:
`specs/021-osservabilita-report/plan.md` (osservabilità F2 — servizio di aggregazione/report: servizio
`ObservabilityReports` in `services/observability_report.py` che legge gli eventi via la porta
`ObservabilityStore` di F1 (già su master) e produce 5 report con funzioni PURE/deterministiche —
cache (hit/miss+risparmio stimato), costo (token per provider/bucket), salute corpus (ultimo index),
latenze (p50/p95 nearest-rank per operation), affidabilità (errori/retry/low_confidence + abstention
rate). Bucket temporali per giorno UTC (default, `SERTOR_OBSERVABILITY_BUCKET`). Dati assenti → report
VUOTO esplicito (zeri), mai eccezione. Solo stdlib, no UI (F3/F4 renderanno), no persistenza (F1), no €
(FEAT-007 si appoggia a CostReport). `build_observability_reports` in composition riusa
`build_observability_store`. Constitution PASS 10/10. Branch `021-osservabilita-report`. Storico:
`specs/020-osservabilita-persistente/plan.md` (osservabilità F1 — strato di osservabilità persistente:
archivio locale interrogabile degli eventi che il core GIÀ emette via `log_event`. Meccanismo (DA-O-f
risolta): un `logging.Handler` (`EventPersistenceHandler` in `observability/capture.py`) attaccato dal
composition root al logger `sertor_core` SOLO se abilitato, che legge i campi già strutturati+redatti dal
`LogRecord` (`operation`+`extra`, ts da `record.created`) → store. Vantaggi: zero modifiche a `log_event`/
call-site (additivo), non-fatale GRATIS (logging `handleError` non propaga), default-off = nessun handler/
store, redazione già applicata in `extra`. Store: SQLite `<index_dir>/observability.sqlite` (stdlib,
gitignored), tabella `events(id,ts,operation,fields json)` con indici `(operation,ts)`/`(ts)`,
dimensionato per le aggregazioni di FEAT-002 (bucket via funzioni data, `json_extract` dei campi).
7ª porta `ObservabilityStore` (record_event/query_events) in `domain/ports.py` = seam con FEAT-002.
Manopola `Settings.observability_enabled` (`SERTOR_OBSERVABILITY`, default False); gancio retention
(DA-O-b rinviata). Insert sincrono (bassa cardinalità eventi per-operazione), `QueueHandler` via di fuga.
Constitution PASS 10/10 senza deroghe. Branch `020-osservabilita-persistente`. Storico recente:
`specs/019-hardening-cache-token/plan.md` (hardening produzione — i due Should del gruppo C dal RAG
audit, costo indicizzazione: (US1) cache embeddings per content-hash = decoratore `CachingEmbedder` +
store SQLite `EmbeddingCache` in `adapters/embeddings/cache.py`, chiave `(embedder.name, sha256(text))`,
vettore float64 (`array('d')`, round-trip esatto), file `<index_dir>/embed_cache.sqlite`, degrado
non-fatale su guasto store, dedup in-call; wiring SOLO sul percorso d'indicizzazione via
`build_embedder(..., cache=True)` da `build_indexer`, manopola `Settings.embed_cache_enabled`
(`SERTOR_EMBED_CACHE`, default False → rebuild full odierno); `services/indexing.py` INVARIATO
(decoratore trasparente); (US2) token nei log = `_embed_batch` Azure/Ollama → `(vettori, token|None)`,
`embed()` emette evento `embeddings` (provider, texts, tokens? — omesso se assente, indipendente dalla
cache). Osservabilità: evento `embeddings_cache` (hits/misses/total) misura il risparmio (SC-006).
Additivo: porta `EmbeddingProvider`/contratti invariati; stdlib-only (sqlite3/hashlib/array), zero
extra. Constitution PASS 10/10 senza deroghe. Branch `019-hardening-cache-token`. Fonte:
`requirements/sertor-core/hardening-produzione/` (Could H7-H11 + refresh incrementale FEAT-009 fuori
ambito). Storico recente:
`specs/018-hardening-retrieval/plan.md` (hardening produzione — i due Must dal RAG audit 2026-06-13:
(US1) resilienza embedder = retry+backoff esponenziale+jitter su errori transitori (429/5xx/rete) via
helper condiviso `with_retry`+`RetryPolicy` in `adapters/embeddings/_retry.py`, manopole `Settings`
`SERTOR_EMBED_RETRY_ATTEMPTS`(3)/`SERTOR_EMBED_RETRY_BASE`(0.5), `attempts=1` disattiva, `EmbeddingError`
preservato a esaurimento; (US2) segnale di confidenza = soglia similarità opzionale `SERTOR_MIN_SCORE`
(default off) che esclude i risultati sotto soglia ed emette log `low_confidence`, funzione pura
`apply_min_score` in `services/retrieval.py`; nell'ibrido la soglia agisce sul **pool denso prima di RRF**
(lo score RRF non è una similarità). Additivo: `RetrievalResult`/porte invariati; default = comportamento
odierno (SC-004/006). Constitution PASS 10/10 senza deroghe. Branch `018-hardening-retrieval`. Fonte:
`requirements/sertor-core/hardening-produzione/` (Should/Could fuori ambito). Storico recente:
`specs/017-manutenzione-wiki/plan.md` (FEAT-007 residuo — manutenzione wiki deterministica:
`sertor-wiki-tools move` (sposta pagina + riscrive wikilink/link relativi entranti, form-preserving
via `_link_targets`, `--dry-run`, idempotente/recovery, errore su collisione, contratto `wiki.move/1`),
`reconcile` (detection read-only pagine `status: superseded` + `superseded_by`, `wiki.reconcile/1`),
`collect`+campo `status`; gruppo D trigger periodico = solo doc (scheduler ospite). stdlib-only, zero
LLM, non-distruttivo. Constitution PASS 10/10 senza deroghe. Branch `017-manutenzione-wiki`. Gruppi
E/F (seed+asset EN) già consegnati a parte; gruppo A (probe) Won't. Storico recente:
`specs/016-igiene-radice-host/plan.md` (igiene radice ospite — asse DOVE/collocazione, epica
`sertor-cli`: radice host pulita e prevedibile. (1) `wiki.config.toml` spostato in `wiki/` + ogni
invocazione `sertor-wiki-tools` la localizza via convenzione `--config wiki/wiki.config.toml
--root .` E via auto-discovery del CLI (`wiki_tools/__main__`: cerca `./wiki.config.toml` poi
`./wiki/wiki.config.toml`, root=CWD); (2) `.sertor/` confermata unica sede runtime (guardia di test);
(3) nuovo `--mcp-scope project|local` su `install rag` (project=`.mcp.json` in radice; local=registra
via `claude` CLI dietro `CommandRunner`, niente file nel repo, fail-fast `McpRegistrationError` +
nuovo `ArtifactKind.MCP_REGISTER`); (4) doc residenti a root. Fix Sertor stesso ONE-SHOT (git mv +
ri-sync `.claude/` + `CLAUDE.md`); retrocompat ospiti esterni FUORI AMBITO (D4). Constitution Check
PASS 10/10 senza deroghe. Branch `016-igiene-radice-host`. In `master`: FEAT-001
`specs/001-nucleo-retrieval/plan.md`, FEAT-002 `specs/002-rag-baseline/plan.md`, FEAT-003-D
`specs/006-nucleo-wiki-deterministico/plan.md`, FEAT-MCP `specs/007-mcp-sertor-core/plan.md`, FEAT-011
`specs/011-cli-esecuzione-rag/plan.md`, FEAT-012 `specs/012-sertor-install-wiki/plan.md`, FEAT-004
`specs/013-motore-ibrido-reranking/plan.md`, FEAT-005 `specs/014-motore-grafo/plan.md`, FEAT-002-rag
`specs/015-sertor-install-rag/plan.md`; feature 010
(query congiunta + `upsert-index`) `specs/010-query-congiunta-e-upsert-index/plan.md`.
<!-- SPECKIT END -->
