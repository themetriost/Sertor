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

## Stella polare (mission) — regola SEMPRE attiva

Ogni cosa che facciamo serve la **missione** di Sertor: dotare qualsiasi progetto di auto-conoscenza
interrogabile, **portabile e senza lock-in**, il cui **differenziatore** è la **fusione di codice e
documenti** (requisiti/spec/wiki) in **un unico corpus** reso all'agente — *il codice dice cosa fa, la
documentazione dice perché*. Generare e servire sono **delegati per design** (agente frontier + MCP):
il fronte di valore è la **qualità del retrieval reso all'agente** (precisione/recall, segnale di
confidenza, freschezza). **A ogni step/design chiediti: questo rafforza la fusione code+doc e la qualità
resa all'agente, o deriva su concern periferici?** È la *stella polare* della costituzione (sezione
*Missione & stella polare*; fonte di verità `README.md`, sintesi [[mission-vision]]); il **Constitution
Check** la verifica a ogni `plan`.

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

> **Errori MCP = segnale, non rumore (regola standing).** Se un tool `mcp__sertor-rag__*` ritorna un
> errore (es. `http 401` per key scaduta, `No module named …` per venv `.venv` non sincronizzato, indice
> assente), **non degradare in silenzio** su `Read`/`Grep`: ripiega pure per non bloccarti, ma
> **segnala esplicitamente** l'errore (è dogfooding — un nostro strumento rotto va visto, non sepolto).
> Il server stesso ora persiste ogni errore tool come evento `mcp.<tool>.error` e fa un self-test
> all'avvio (vedi `src/sertor_mcp/server.py`): i guasti compaiono nel report affidabilità e a
> reconnect. La stessa regola è nelle definizioni degli agenti che usano `sertor-rag`.

## Accesso a Sertor: solo via vehicles (regola SEMPRE attiva — Principio XI)

A **runtime**, l'agente / gli script / qualunque consumatore accedono alle capacità di Sertor **solo**
via i **vehicles**: la **CLI** (`sertor-rag`, `sertor-wiki-tools`) o il **server MCP**. **Mai**
importare e invocare `sertor_core` direttamente (es. `build_indexer().index(...)`, `build_facade()`).
**Unica eccezione: gli unit/integration test**, che esercitano libreria e funzioni direttamente.

*Perché:* i vehicles cablano in modo uniforme osservabilità (`enable_observability`), config centralizzata
ed errori; l'accesso diretto li **bypassa silenziosamente** (caso reale: un re-index via
`build_indexer().index()` non finisce in telemetria). Codificato nella costituzione (Principio XI,
v1.2.0) e nel gate del `plan-template`. Operativamente: per re-index usa `sertor-rag index .`, per query
usa `sertor-rag search`/MCP, per il wiki `sertor-wiki-tools`.

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
uv sync --all-packages --extra dev  # crea/sincronizza l'UNICO venv (.venv): membri del workspace +
                                    # dipendenze di sviluppo + server MCP (mcp) + code-graph (graph).
                                    # Per il dogfood-su-Azure aggiungi --extra azure (extra pesante opt-in).
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
`pip install -e` necessario per i test). **Un solo venv** `.venv/` (E10-FEAT-002): è il default del
workspace `uv`, popolato da `uv sync --all-packages --extra dev` (+ `--extra azure` per il dogfood),
e fa girare anche il server MCP (`.mcp.json` lo punta). Il vecchio `.venv-core/` è stato eliminato.

**Machinery SpecKit (setup).** Il dogfood ottiene la machinery SpecKit — skill native `speckit-*`,
`.specify/scripts/`, template — **come un ospite**, eseguendo il **vero installer sul dogfood**
(`sertor-flow install --assistant claude` → `specify init`, E15-FEAT-001 scope B / *process-fidelity*):
è la stessa via di un client. È **rigenerabile e git-ignorata** (come il `.venv`).

> **Nota (E15 asset-install):** la **fonte** degli asset host-facing (machinery `.specify/`, `.claude/`,
> blocchi `CLAUDE.md`, wiring `settings.json`) è **il vero install**, non gli script dev. Lo script
> `scripts/dev/materialize-speckit.ps1` (specify init isolato + copia selettiva) resta solo come
> **dev-tool / bootstrap fallback** e come propagazione della guardia byte — **non** è più il modo con cui
> il dogfood *ottiene* la machinery. `specify init` è idempotente/skip-if-present.

Il vero install (e il fallback) richiedono rete (`uvx` scarica spec-kit al pin `SPECKIT_VERSION`). Su un
clone fresco/CI la machinery è assente finché non si esegue l'install — le fasi SpecKit che usano gli
script lo richiedono.

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

## Feature completa & tracciamento dello scope (regola SEMPRE attiva)

Tre regole che impediscono di **perdere pezzi di una feature** — il valore consegnato, lo scope
rinviato e la sua **comprensibilità per l'utente**.

### 1. Una feature è completa SOLO se è installabile su un ospite

**Vale SEMPRE.** Una feature **non è "done"** finché un **ospite** (un progetto terzo, non solo il
dogfood di Sertor) può **ottenerla e usarla attraverso il percorso di installazione** (`sertor
install`). È il corollario operativo del **Principio X** (host-agnostico) e della mission (framework
*installabile ovunque*): se vive solo nel `.claude/`/`.env` di Sertor, è un prototipo, non una feature.

Concretamente, prima di dichiarare completa una feature:
- **Ogni artefatto host-facing** che introduce — hook, voci di `settings.json`, manopole nel template
  `.env`, skill/agenti/comandi, asset, voci del `claude-md-block` — **DEVE essere cablato in `sertor
  install`** (e nei suoi template/asset), **non** lasciato "solo per il dogfood".
- Le capacità di **sola libreria/CLI** (un motore, un comando `sertor-rag`) sono installabili **per
  costruzione** (viaggiano col pacchetto `sertor-core`): il criterio è soddisfatto **ma va
  verificato** — es. una nuova manopola env DEVE comparire nel template `.env` dell'installer.
- **«Distribuzione su ospiti FUORI AMBITO» NON è uno stato finale accettabile.** Al più è un **debito
  di completamento tracciato** (vedi regola 2), da chiudere prima che la feature conti come *done*. Una
  spec può rinviarlo a una feature successiva, ma la **capacità resta incompleta** finché quella non
  arriva.

### 2. Gli «Out of Scope» si PROMUOVONO, non restano appesi nella feature

L'*Out of Scope* di una `spec.md` (e le *Estensioni* di `research.md`) è un **confine di scope di
quella feature**, **non** un meccanismo di tracciamento: ciò che vi resta è **sepolto** e si perde. Al
`plan`/decomposizione, ogni voce rinviata che sia una **capacità futura reale** va **promossa subito**
a una casa **durevole**:
- mappa su una capacità d'epica → riga **`FEAT-NNN` nel backlog** (`requirements/<epica>/epic.md`, con
  MoSCoW + stato);
- idea ancora informe → riga in **roadmap → *Nuove funzionalità da discutere*** (`wiki/syntheses/roadmap.md`);
- "non qui, ma già `FEAT-X`" → **cita** la FEAT esistente (nessuna voce nuova).

Mai lasciare un rinvio reale a vivere **solo** dentro `specs/<feat>/`. I due livelli durevoli (backlog
epica + roadmap) sono le **uniche** fonti di verità per "cosa manca"; l'Out-of-Scope di spec è solo il
confine locale.

### 3. Una modifica al setup non è "done" finché la documentazione UTENTE non è aggiornata

**Vale SEMPRE.** Ogni modifica **host-facing al setup** — installer (`sertor install`/`upgrade`/
`uninstall`), asset distribuiti (skill/agenti/hook/comandi), voci `settings.json`, manopole/template
`.env`, blocchi `claude-md-block`, comandi d'installazione/esecuzione, layout `.sertor/` — **non è
completa finché la documentazione UTENTE non riflette il cambiamento, nello stesso step**. È il
complemento della regola 1: una capacità non solo dev'essere *installabile*, ma anche *comprensibile*
da chi la installa/usa.

La **documentazione utente** è `docs/` (riferimento completo `install.md` + quick-start per-assistente
`install-claude.md`/`install-copilot.md`), `README.md` e la tabella capability di
`packages/sertor/docs/install.md` — **distinta** dalla *documentazione interna* (il wiki in `wiki/`,
vedi la distinzione standing). Concretamente: una nuova capacità/hook/manopola/comando che l'utente
installa o vede DEVE comparire nel punto giusto di `docs/install.md` (e nei quick-start se cambia il
flusso percepito) + tabella capability dove pertinente. Se la doc non è aggiornabile nello stesso
step, è un **debito di completamento tracciato** (regola 2), non uno stato "done".

**Doppio cappello:** è **usabilità** (E12 — l'utente capisce cosa succede al setup) **e**
**documentazione** (E13). *Origine (2026-06-26):* l'auto-updater (E2-FEAT-013) era implementato e
installabile ma **non documentato** in `docs/` — gap colto solo a posteriori; questa regola lo previene.

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

**Apertura dello step — MCP-first (dogfooding prioritario, regola SEMPRE attiva).** Quando uno step
richiede di **orientarsi nel codice o nella documentazione del corpus** (`src/`, `specs/`,
`requirements/`, `wiki/`, doc di radice), la **prima mossa è interrogare il RAG** via il server MCP
`sertor-rag` (`search_combined`/`search_code`/`search_docs`, `find_symbol`/`who_calls`/`related_docs`/
`get_context`), **non** leggere i file a mano. Solo *dopo* che il RAG ha indicato i file, si usa `Read`
per leggerli interi: il RAG **trova**, `Read` **trasporta**. **Perché è prioritario e non cerimonia:**
ogni uso è il **test del valore dello strumento** — è così che misuriamo se il RAG è *conveniente* o
*inutile*, ed è così che i guasti **emergono** invece di marcire invisibili. *Se Sertor non usa Sertor,
chi dovrebbe?* Corollari operativi:
- **Errori MCP = finding, mai rumore** (regola standing, vedi *Riferirsi al prototipo* sopra): un tool
  `mcp__sertor-rag__*` che erra (key scaduta, indice stale, `InternalError` dello store) va **segnalato
  esplicitamente**; ripiega pure su `Read`/`Grep` per non bloccarti, ma il guasto **si vede**. *(Caso
  reale 2026-06-19: `search_code` rotto con `chroma InternalError`, e drift di riga in `find_symbol` —
  emersi **solo** perché si è usato l'MCP invece di leggere a mano.)*
- **Unica eccezione:** un **fatto puntuale** di cui conosco già file e posizione esatti (es. «che default
  ha `default_k`?») → `Read`/`Grep` diretti sono leciti. **Nel dubbio, MCP-first.**
- **Confine Principio XI invariato:** si accede a Sertor **solo via vehicles** (MCP/CLI), mai importando
  `sertor_core`. Questa regola è *in-flow* (apertura); la checklist numerata qui sotto resta la
  *chiusura* (Definition of Done).

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
   semantico. **Fonte unica dello stato «consegnato» (regola A-12, 2026-07-10):** l'**EXEC è l'unica fonte**
   di verità sullo stato delle feature; le colonne `Stato` degli `epic.md` e le voci di *«Nuove funzionalità
   da discutere»* **puntano** all'EXEC per le feature consegnate, **non ne duplicano** merge/PR/date (è la
   duplicazione che va in deriva). Al merge si aggiorna **solo** l'EXEC; l'`epic.md` marca ✅ + «vedi EXEC».
   L'EXEC e gli `epic.md` **non devono contraddirsi**. **Iniezione
   (non è compito del rituale):** il SessionStart hook è **sottile** — non *trasporta* il contenuto (il
   canale-hook è limitato a ~10.000 caratteri: l'indice da solo lo sforerebbe), ma **istruisce** il flusso
   principale a caricarlo a freddo con il tool `Read` (`wiki/syntheses/roadmap.md`, `wiki/index.md`, l'ultimo
   file di `wiki/log/`) — l'output del `Read` entra **intero** nel contesto, nessun cap — e poi a **mostrare
   all'utente l'executive summary** della roadmap. L'hook *innesca*, il `Read` *trasporta*, il rituale tiene
   il *contenuto* vero.
5. **Re-index del corpus toccato** —
   > **Enforced via hook** `rag-freshness.py` (`SessionEnd`) — vedi E10-FEAT-011. Il testo seguente descrive la rete agente complementare.

   > **DOGFOOD-ONLY — re-lock del runtime PRIMA del re-index (dopo un merge su `master`, E15-FEAT-008).** Il
   > runtime `.sertor/` installa `sertor-core` da `git=<repo>` **HEAD** ma il lock fissa il commit: dopo un
   > merge resta stantio. Quando uno step si chiude con un **merge su `master`**, esegui
   > **`scripts/dev/relock-runtime.ps1`** (check-then-act: no-op se già a HEAD; re-lock via `uv` se indietro;
   > fail-loud) **prima** di re-indicizzare, così l'indice si ricostruisce sul runtime aggiornato. È
   > **dogfood-only** (gli ospiti pinnano versioni + auto-updater E2-FEAT-013): lo script vive in `scripts/dev/`,
   > **non** è distribuito e **non** va nell'hook `rag-freshness.py` né nei blocchi `claude-md-block`.

   se lo step ha modificato **file indicizzati nel corpus RAG**,
   ricostruisci l'indice, così il RAG di dogfooding non serve mai contesto stantio (è l'essenza:
   contesto dell'agente sempre reale). **Modello a corpus unico (decisione 2026-06-10):** il wiki vive
   **dentro** il progetto ospite *by design* (lo crea così l'install della futura CLI) → è parte del
   corpus primario come documentazione (`doc_type=doc`); niente corpus separato per il retrieval, niente
   `SERTOR_EXTRA_CORPORA` sul dogfood. Quindi: **qualsiasi** modifica indicizzata (`src/`, `specs/`,
   `requirements/`, `wiki/`, doc di radice) → rebuild del corpus **`sertor`** **via la CLI**:
   `uv run sertor-rag index .` (Principio XI — il re-index si fa via vehicle, NON con
   `build_indexer().index()` diretto: la CLI chiama `enable_observability` e l'evento `index` finisce in
   telemetria; il percorso libreria lo bypassa). Il rebuild è **full ma sicuro**: `reset` della
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

8. **Smoke test del RAG di dogfooding** —
   > **Enforced via hook** `rag-freshness.py` (`SessionEnd`) — vedi E10-FEAT-011. Il buco del filtro metadata `where` non è coperto dall'hook → il punto 8 resta la rete dell'agente.

   **allo stesso momento del commit** dello step (specie dopo
   un re-index), il flusso principale **esercita il server MCP `sertor-rag`** per verificare che sia
   *vivo e fresco*, non solo che l'indice su disco esista. Il test DEVE colpire il **path del filtro
   metadata**: `search_code` **e** `search_docs` — **non basta `search_combined`** (la query con `where`
   è proprio ciò che cede quando il server è **stantio** dopo un re-index, mentre la solo-vettore regge:
   è il guasto reale del 2026-06-19) — più un `find_symbol` su un **simbolo a posizione nota** come
   controllo di **freschezza** del code-graph (la riga deve combaciare col file reale). Un tool in errore
   o un indice stantio → **segnala** (regola *errori-MCP = finding, mai rumore*), **riconnetti** il server
   e **ri-verifica**; mai degradare in silenzio. È il **complemento di chiusura** della regola MCP-first
   di apertura: ogni step verifica che lo strumento sia usabile. Esecuzione **meccanica**, ma l'esito
   («fresco?») è **giudizio** → flusso principale. **Calibra al valore:** gli step che non toccano il
   corpus possono saltarlo; **obbligatorio dopo un re-index / merge su `master`**. *(Mitigazione manuale
   in attesa del fix di prodotto: il server che rileva lo store riscritto e re-inizializza il client.)*

9. **Archivia le richieste da altri agenti processate** — quando una richiesta arrivata nel canale
   `wiki/sources/input-other-agents/` (handoff/feedback/reply da un altro agente o progetto) è stata
   **elaborata** — cioè letta e portata a una casa durevole (backlog/requirements/implementazione) o a
   una decisione — **spostala** in `wiki/sources/input-other-agents/processed/`, così **non la si
   rielabora** in una sessione futura (gemella della convenzione `usersfeedback/ → processed/`).
   Aggiorna i riferimenti relativi che la citano; le nostre analisi derivate (recon, note di risposta
   in uscita) possono restare o seguirla, a giudizio. **Regola *locale* di Sertor: NON va nei blocchi
   `claude-md-block` distribuiti agli ospiti** (è dogfood/governance interna, non una pratica dell'ospite).
10. **\<altre azioni\>** — questa lista è **estendibile**: ogni azione che l'utente chiede di rendere
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

Questo workspace è un **repo git con remote `origin`** (ci si pusha regolarmente). **Policy di branching (produzione):** si lavora a **branch + PR**, **mai push diretti su `master`/`main`** (invariante del `configuration-manager`). Convenzione: **un commit dopo ogni step** di lavoro significativo (incluso l'aggiornamento del wiki); git delegato al `configuration-manager`. **Gate pre-merge (VINCOLANTE, E15-FEAT-008):** prima di mergiare una PR su `master`, la **suite completa** (`uv run pytest -m "not cloud"`) **e** il lint (`uv run ruff check .`) devono essere **verdi** — non ci si fida di run locali mirati. *Origine (2026-07-03): un merge senza rigirare la suite ha lasciato una guardia stantia e rotto la CI di `master`; poi un commit senza `ruff check` l'ha rotta di nuovo.* Messaggi in stile
**Conventional Commits in italiano** (`tipo(scope): sommario`; scope tipici `01-baseline`,
`prototype`, `requirements`, `cli`, `shared`, `wiki`), corpo che spiega il *perché*, footer
`Co-Authored-By`. **Mai committare** `.env`, `*.key`, il contenuto di `raw/`, i virtualenv o gli
artefatti rigenerabili (`output/`, `cache/`, `logs/`, `metrics/`, indici/store vettoriali): sono
coperti da `.gitignore`.

**Versioning di `/VERSION` (policy A-15, 2026-07-10):** `/VERSION` è **SemVer con bump MANUALE**, e si
tocca **solo a una release user-facing** (quando si pubblica qualcosa che gli ospiti dovrebbero prendere
via `uvx --refresh`) — **non** a ogni merge. Il tracking per-merge è compito del **dogfood** (runtime
`.sertor/` che segue HEAD, re-lock a ogni merge, E15); confondere i due farebbe scattare l'avvisatore
d'aggiornamento (E2-FEAT-013) a ogni commit. Corollario: un `/VERSION` fermo mentre i commit avanzano
**non è drift** — è «nessuna release esterna ancora», e l'avvisatore è correttamente
**dormiente-fino-alla-release** (diventa vivo al primo bump). *(Bump automatico da conventional-commit =
scartato come YAGNI finché non c'è una cadenza di release / ospiti esterni reali.)*

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
  `created`/`updated` sono **date secche** (`YYYY-MM-DD`), **mai** changelog: `updated` porta solo l'ultima
  data di modifica, la **storia vive nel log** (`wiki/log/`), non appesa al frontmatter (regola A-13,
  2026-07-10).
- **Backlink** in stile wikilink `[[nome-pagina]]` (compatibile Obsidian); i link relativi
  Markdown vanno bene per la navigazione da editor/GitHub. Mantieni i cross-reference aggiornati.
- **Naming** file: kebab-case descrittivo (es. `azure-ai-search.md`, `hybrid-search.md`).
- **Voce di log**: `## [YYYY-MM-DD] <operazione> | <titolo>` (operazione ∈ setup/structure/record/distill/ingest/query/lint/reorg/generate/rag-sync; elenco autorevole nel playbook §6).
- Crea una **nuova** pagina per un concetto/entità nuovo; **aggiorna** quella esistente altrimenti.
- Quando una fonte nuova contraddice una pagina, **segnala esplicitamente** la contraddizione.

Per innescare manualmente un consolidamento usa il comando **`/wiki`** (lavora nel flusso
principale) oppure delega all'agente `wiki-curator` (in background).

**Hook (trigger automatici, vedi `.claude/hooks/wiki-pending-check.py`):**
- `SessionStart` — carica indice + coda log a inizio sessione (contesto iniettato).
- `Stop` — a fine turno, se rileva lavoro non ancora registrato (file di `src/specs/requirements/.claude`
  più recenti dell'ultima voce di log), inietta un **promemoria non bloccante** a delegare al
  `wiki-curator`. Non intrappola il turno; si auto-silenzia appena il wiki è aggiornato.
- `SessionEnd` — riepilogo finale del lavoro non registrato, come rete di sicurezza tra sessioni.

I trigger **non orchestrano da soli** (un hook non può avviare un subagent): rendono *automatica* la
delega che resta affidata al `wiki-curator`.

## Blocchi installati vs prosa dogfood (come leggere questo file)

Da qui in giù vivono i **blocchi marker `SERTOR:*`** (più il riferimento SpecKit): sono il **contratto
client-form generico** che *ogni* ospite riceve installando Sertor — depositati e rigenerati dai **veri
installer** (`sertor install rag`/`wiki`, `sertor-flow install`), in **inglese** e host-agnostici,
**posseduti dai marker** (un ri-install li aggiorna in place, non li duplica). La **prosa italiana sopra**
è la governance **propria di questo progetto** (il dogfood): elabora, localizza e arricchisce quei
contratti con le regole dogfood-specifiche (corpus del prototipo, rituale di step a 10 punti, re-lock del
runtime, gate pre-merge, ecc.). **Dove i due si sovrappongono, per il dogfood vince la prosa** (è
l'applicazione operativa, più ricca); i blocchi **restano** perché il dogfood è un **client fedele** — ha
esattamente ciò che riceve ogni ospite (process-fidelity: E15 asset-install). Il file è dunque **bilingue
per costruzione** (blocchi EN + prosa IT), senza contraddizione: contratto generico sotto, applicazione
dogfood sopra. *(Non riconciliare cancellando la prosa: i blocchi sono rigenerati dall'installer, la prosa
è la conoscenza dogfood — vanno tenuti entrambi.)*

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/097-rituale-anti-skip/plan.md` (**E10 / FEAT-026** epica **debito-tecnico** — *rituale wiki
resistente allo skip silenzioso di distill/lint*). MVP parte 1+3: (1) **nuovo sottocomando deterministico**
`ritual-check` in `sertor-wiki-tools` (`src/sertor_core/wiki_tools/`) che, dato lo scope dello step
(**git-diff vs base**, fallback `--pages`/fail-loud), elenca **candidati a distillazione** (gruppi di pagine
changed con ≥2 nuovi backlink incrociati e 0 nuove pagine `concepts/`/`tech/`) + **candidati a drift**
(`stale-updated` · `neighbor-of-change` · `capability-exec` config-driven) + emette lo **scaffold di
dichiarazione** `Rituale: record · distill · lint`; output JSON `wiki.ritual_check/1` + summary. (2)
**contratto di dichiarazione forzata** a fine step nel blocco host-facing `SERTOR:WIKI-RITUAL` + playbook
(verdetto esplicito, «non serve» incluso), distribuito via installer + guardia sync. **Confine D↔N:** il
tool **trova** (deterministico, zero-LLM, sola lettura), l'agente **giudica** (Principio XI). Host-agnostico
(config da `wiki.config.toml`, no path hardcodati — Principio X); fail-loud su scope indeterminabile
(Principio XII). Gemella lato-giudizio di FEAT-011. **Fuori scope:** parte 2 (wiki-curator) + parte 4
(propagazione `ops/*.md`). Constitution **12/12 + missione PASS**. Branch `097-rituale-anti-skip`.

<!-- SPECKIT END -->

<!-- SERTOR:SDLC-RITUAL START -->
## Development method (SDLC) — always active

This project follows a spec-driven development method (SpecKit) with an explicit
constitution gate and disciplined version control. These rules are standing: apply
them on every significant change, without being asked.

### The SpecKit flow

Significant work flows through these phases, in order; each consumes the artifacts
of the previous one:

1. **requirements** — capture the need (EARS-style requirements) before designing.
2. **specify** — write the feature specification (`spec.md`): what and why, scope,
   out-of-scope, acceptance criteria.
3. **clarify** — resolve open questions in the spec before planning; never guess on
   a real design fork — ask, with context.
4. **plan** — produce the implementation plan (`plan.md`), data model, contracts,
   and research decisions.
5. **tasks** — decompose the plan into ordered, dependency-aware tasks (`tasks.md`).
6. **analyze** — cross-check spec ↔ plan ↔ tasks for consistency and coverage.
7. **implement** — execute the tasks in order, producing real code and tests.

The phases are driven by the SpecKit skills installed for your assistant (the `speckit-*` skills)
and the templates/scripts under `.specify/`.

### Constitution Check (gate)

The project constitution lives in `.specify/memory/constitution.md`. It is a **gate**,
not decoration:

- Re-check the constitution at `plan` time and again after design: list each
  principle and mark PASS / N/A, justifying any deviation explicitly.
- A change that violates a principle is reworked or its complexity is justified in
  writing — it does not ship silently.
- Amend the constitution through its own flow (semantic versioning), never by drift.

### Error discipline — fix, don't suppress

When something errors, remove the cause. **Never disable, mute, or route around a
capability just to silence its error** — early, visible feedback is a value. Graceful
degradation is acceptable only when it *reports* the failure (a warning/finding);
silent suppression, or turning a feature off to dodge its error, is not. Disabling a
capability is a deliberate, recorded decision, never a reflex. (Constitution: *Fail
Loud, Fix the Cause*.)

### Version control discipline (owner of git/commit rules)

This block is the **owner** of git and commit discipline for the project.

- **Branch + PR workflow.** Significant work happens on a feature branch and merges
  via pull request. **No direct pushes to the default branch** (`main`/`master`).
- **Conventional Commits.** Commit messages follow `type(scope): summary`; the body
  explains the *why*; one commit per significant step.
- **Never commit secrets or regenerable artifacts.** `.env`, key files, virtual
  environments, caches, build output, logs, and indexes stay out of version control
  (covered by `.gitignore`).
- **Delegate git operations to the `configuration-manager` agent.** All version
  control actions (staging, commit, branch, merge, tag, push, pull) are delegated to
  the `configuration-manager` agent rather than performed inline, so the main flow is
  never blocked on bookkeeping. Pass it a self-contained brief (what was done, which
  files, why, the requested operation). Destructive/irreversible operations
  (`push --force`, `reset --hard`, history rewrite, `branch -D`, `clean -fd`) run
  **only when explicitly requested** in the brief; otherwise the agent stops and
  reports.
<!-- SERTOR:SDLC-RITUAL END -->

<!-- SERTOR:RAG-USAGE START -->
## Sertor RAG — How to use it

This project has the **Sertor RAG** capability installed. When you need to search or retrieve from
the indexed corpus (code and documentation), use one of the provided **vehicles**:

- **CLI** — run `uv run --project .sertor sertor-rag` (e.g.
  `uv run --project .sertor sertor-rag search "<query>"`). It is the supported entry point: the bare
  command is NOT on `PATH` (it lives in `.sertor/.venv`), so always route it through `uv run --project
  .sertor`.
- **MCP tools** — the `sertor-rag` MCP server exposes search/navigation tools (`search_code`,
  `search_docs`, `search_combined`, `find_symbol`, `who_calls`, `get_context`).

For the full invocation reference — the two levels (runtime CLIs via `uv run`, installer via `uvx`),
the venv fallback, and the Windows setup notes — see `sertor-cli-reference.md` (deposited under
`.sertor/` by `sertor install rag`).

**Do NOT import `sertor_core` directly in your own scripts.** The library is meant to be consumed
through its vehicles (CLI / MCP), which wire in the cross-cutting concerns — configuration,
observability, error handling — for you. Importing `sertor_core` by hand bypasses them and is not a
supported way to use the capability.

### Search first, read second

When you need to understand code or docs in this corpus, **query the Sertor RAG before reading files
by hand**: run `uv run --project .sertor sertor-rag search` or use the MCP search/navigation tools,
let the results point you to the relevant files, then read those. It keeps your answers anchored to
what is actually indexed.

If a Sertor RAG tool returns an **error** (unreachable backend, missing or stale index), treat it as
a **signal**, not noise: say so instead of silently falling back to a blind file read. A broken
retrieval tool is worth surfacing, not burying.

### Conversation memory (optional)

This capability also ships **conversation memory** — a local, opt-in episodic archive of past
sessions. When it is enabled (`SERTOR_MEMORY=true` in `.sertor/.env`) you can recall earlier work:

- `uv run --project .sertor sertor-rag memory search "<query>"` — full-text search over archived
  sessions ("did we discuss X?").
- `uv run --project .sertor sertor-rag memory list` / `… memory show <key>` — browse and read an
  archived session.
- `uv run --project .sertor sertor-rag memory archive` — capture the current sessions (also runs
  automatically at session end).

Memory is **off by default** (privacy): the commands and the automatic capture do nothing until you
set `SERTOR_MEMORY=true`. Content is stored locally and scrubbed of secrets; nothing leaves the machine.

This is a **usage instruction**, not a constraint on your project: your own code and tests are
unaffected.
<!-- SERTOR:RAG-USAGE END -->

<!-- SERTOR:WIKI-RITUAL START -->
## Step Ritual / Definition of Done (LLM Wiki)

This project maintains a **local wiki** in `wiki/`, inspired by Karpathy's "LLM Wiki" pattern:
a persistent, cumulative artifact that grows with each session instead of rebuilding
knowledge from scratch every time. Configuration lives in `wiki.config.toml` (the single source of
host-specific settings: root, taxonomy, source folders, language).

> **Golden rule:** every significant thing that is done must be documented in the wiki — experiments, decisions,
> concepts/technologies explored, ingested sources. Do not wait for the user to ask.
> Purely mechanical, minor changes do not require a log entry.

A **step** is a meaningful unit of work (a feature, a fix, a decision, a research task,
an analysis). **At the end of each step**, the main flow executes — on its own initiative — this
checklist:

1. **Record** (`record`) — create/update the impacted pages, backlinks, and `index.md`, and append
   the log entry (today's file in `wiki/log/`). Structural work → delegatable to the
   `wiki-curator` agent.
2. **Distill entities** (`distill`) — identify the durable entities/concepts the step surfaced
   and, if they have their own identity and are referenced from multiple points, give each a
   dedicated page in `concepts/`/`tech/`; the dated record stays lean and points to them. This is **judgment** → stays
   in the main flow.
3. **Semantic lint** (`lint` level B) — verify that the wiki has not drifted away from the
   reality of the project (code, requirements, VCS state): flag every claim the repo contradicts,
   fix on confirmation. This is **judgment** → stays in the main flow.
4. **Plain-language summary (explainer)** — when a step develops or plans a **significant capability**
   (a requirement, a feature, a product capability), produce or update a **plain-language description**
   under `wiki/explainers/` (for non-technical readers): what it does and why, with an everyday analogy
   and no jargon, each pointing to the corresponding technical page. This is **judgment** → stays in the
   main flow. **Calibrate to value (optional):** only for capabilities worth explaining to a
   non-technical stakeholder — not for mechanical or tooling-only steps. It applies both to what is
   *done* and to what is *about to be built* (the page marks the status).

**Forced declaration (anti-silent-skip).** The closure of every significant step MUST emit an explicit
declaration — `Ritual: record <verdict> · distill: <verdict> · lint: <verdict>` — with a verdict for each
judgment step; "not needed" is fine but MUST be **declared, never omitted** (a silent skip is the failure
this prevents). To keep candidate *discovery* off memory, run `sertor-wiki-tools ritual-check` first: it
lists the step's distill/drift candidates (via git diff) + a declaration scaffold — the **tool finds, you
judge** (read-only, zero-LLM).

**Delegation.** That these actions happen is the main flow's responsibility; executing or delegating them
is merely a choice to avoid blocking. The `record` (structured transcription) is delegatable to the
`wiki-curator` agent; distillation and semantic lint, being judgment, stay in the main flow.
To manually trigger a consolidation, invoke the wiki capability of your assistant (main flow)
or delegate to `wiki-curator` (background).

**When to record:** at the same moment as the step commit. The log entry is
not deferrable: a step is not closed until both the commit **and** the log entry are done.

**Definition of Done — host-agnostic assets.** Touching a distributable asset (a skill, agent,
command, instruction block, or its support payload) requires verifying **parity across assistants**:
the body must stay host-agnostic (no literal assistant paths, no slash-command invocations, payload
referenced by name) so the SAME body works on every assistant. A step that edits such an asset is not
done until that parity holds (a parity guard enforces it where available).

For the full list of wiki operations (`record`/`distill`/`ingest`/`query`/`lint`/`reorg`/`generate`/
`rag-sync`/`structure`), the page conventions (frontmatter, wikilink backlinks, kebab-case naming) and
the log-entry format, see `wiki-playbook.md` — the single source of truth bundled with the wiki
capability, read on demand.
<!-- SERTOR:WIKI-RITUAL END -->
