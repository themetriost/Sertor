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
   semantico; il blocco executive e la mappa-feature sottostante **non devono contraddirsi**. **Iniezione
   (non è compito del rituale):** il SessionStart hook è **sottile** — non *trasporta* il contenuto (il
   canale-hook è limitato a ~10.000 caratteri: l'indice da solo lo sforerebbe), ma **istruisce** il flusso
   principale a caricarlo a freddo con il tool `Read` (`wiki/syntheses/roadmap.md`, `wiki/index.md`, l'ultimo
   file di `wiki/log/`) — l'output del `Read` entra **intero** nel contesto, nessun cap — e poi a **mostrare
   all'utente l'executive summary** della roadmap. L'hook *innesca*, il `Read` *trasporta*, il rituale tiene
   il *contenuto* vero.
5. **Re-index del corpus toccato** —
   > **ENFORCED VIA HOOK (E10-FEAT-011):** il re-index a fine sessione è ora un hook deterministico
   > (`rag-freshness.ps1`, `SessionEnd`). Confine D↔N: l'hook re-indicizza e verifica (meccanico);
   > l'agente esegue la correzione indotta all'avvio se lo stato è degradato (giudizio). Il testo
   > seguente descrive ancora la rete agente (valida finché il buco filtro-metadata `where` non è
   > chiuso da E12 e finché l'hook non è su tutti gli ospiti).

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
   > **ENFORCED VIA HOOK (E10-FEAT-011):** la verifica di salute (`sertor-rag doctor`) è ora parte
   > dell'hook `rag-freshness.ps1` (`SessionEnd`). Il buco del filtro metadata `where` (guasto storico
   > 2026-06-19) **non** è coperto dall'hook (promosso a E12-FEAT-011 usabilità) → il rituale punto 8
   > dell'agente resta la rete per quel buco specifico.

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

9. **\<altre azioni\>** — questa lista è **estendibile**: ogni azione che l'utente chiede di rendere
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
`specs/084-speclift-self-host/plan.md` (FEAT-001 epica **speclift** — **self-hosting / dogfooding di
SpecLift su Sertor**: vendorare **SpecLift** (handoff Sinthari, `github.com/themetriost/Sinthari`
`master @ be4da28`, MVP 104 test) nel repo Sertor come nuovo membro del workspace `uv`
**`packages/speclift`**, usabile per **dogfooding** — generare requisiti EARS ancorati e riverificati dai
changeset reali di Sertor, alimentando il *lint semantico* del rituale di step con evidenza ancorata.
**ADDITIVA / vendoring, ZERO runtime di `sertor_core` (Principio XI):** `sertor_core` **byte-identico**;
SpecLift consuma il RAG **esclusivamente** via il vehicle CLI `sertor-rag search --type code --json`
(subprocess), **mai** importando il core (grep negativo verificato — uniche occorrenze = commenti
dichiarativi in `config.py:26`/`rag_sertor.py:3`). Distribuzione su ospiti esterni = **FEAT-002** (epica a
parte), fuori ambito. **9 forche di *come* risolte (research, ancoraggio clone Sinthari + MCP `sertor-rag`
senza errori):** **D-1** vendoring = **copia one-shot** pinnata a `be4da28` + nota di provenienza
`packages/speclift/VENDORING.md` (il launch-installer di SpecKit NON si applica — SpecLift ha runtime
Python proprio; sync-mechanism = over-eng III; la provenienza registra stato upstream **e** divergenze).
**D-2** `jsonschema` **runtime→dev** (verificato test-only: zero import in `src/`, usato solo in
`tests/{contract,unit}`) → runtime deps `[]` stdlib-only (divergenza documentata). **D-3** vehicle RAG =
**patch della costante** `SERTOR_RAG_VEHICLE = ("uv","run","sertor-rag")` in `config.py:27` (era `(…,
"--project",".sertor",…)`): **zero-config** per il self-host (FR-006), divergenza minima (III), env-var →
FEAT-002; la tensione **III↔X** risolta **senza deroga** (il vehicle vive in `config.py` = locus di
config centralizzata, NON nel corpo/skill → host-agnosticità preservata). Il **Must** fail-loud (exit 3 +
messaggio) è upstream invariato; il **Should** (rimedio `sertor-rag index .`) = piccola divergenza nel
messaggio `RagUnavailableError`. **D-4** Python `>=3.12`→`>=3.11` (+ `ruff target py311`): nessuna sintassi
3.12-only nel grep, `StrEnum` è 3.11+ (`domain/models.py:24`); condizione di accettazione = suite verde su
3.11 (FR-018), **piano B FR-019** se irriducibile. **D-5** lint = ruff di **root** `extend-exclude +=
packages/speclift` (precedente `prototype`), speclift tiene il proprio `[tool.ruff]` (110/`SIM`/`py311`) →
`ruff check .` (gate CI) resta verde senza riformattare il vendorato. **D-6** test = **modello
per-pacchetto** (come gli altri membri) + step CI dedicato `Tests — speclift`; marker
`contract`/`integration` nel pyproject di speclift → **nessun conflitto** col root `cloud`/`integration`
(root `testpaths=["tests"]` non colleziona speclift; pytest usa l'inifile nearest). **D-7** licenza =
Sinthari **NON ha LICENSE** a `be4da28` (**finding** segnalato, Princ. XII) → aggiunta `LICENSE` MIT
(convenzione workspace) + provenienza che registra l'assenza upstream e la natura **stessa-org**
(`themetriost`) dell'handoff (first-party). **D-8** versione **statica `0.1.0`** (upstream, non
`dynamic`/`/VERSION`) → speclift dogfood-only, **escluso** dal test di packaging distribuibile (FEAT-002).
**D-9** skill dogfood = **copia fedele** in `.claude/skills/speclift/SKILL.md` (già host-agnostica e già
onesta: NON cita `find_symbol`/`who_calls`) → l'onestà **Gruppo H** (FR-016) vive nei doc/wiki, non nella
skill. **Ancoraggio verificato:** `sertor-rag search --type code --json` = array piatto con
`path`/`chunk_id` (`cli/__main__.py:124-131`, `cli/output.py:95-109`) → combacia con `rag_sertor.py:50-58`;
`--type code` NON impattato dal breaking `--type both` (070). **Integrazione = 5 punti** (root pyproject
×2, `ci.yml`, pyproject del pacchetto, `.claude/skills/`) + 6 divergenze tracciate; grafo membri aciclico
(`speclift → ∅`). `sertor-core`/`src/sertor_mcp`/`packages/{sertor,sertor-install-kit,sertor-flow}`
**INVARIATI**. **Onestà doc↔codice (Gruppo H):** il legame runtime reale con Sertor è **UN SOLO comando
CLI** (`sertor-rag search --type code --json`), **non** i tool MCP di navigazione del code-graph che
l'handoff/wiki Sinthari descrivono (`rag_sertor.py:4-7`) — dichiarato lato Sertor, non corretto a monte.
Constitution **PASS 12/12 + missione PASS** (pre e post-design) senza deroghe (Complexity Tracking vuoto) —
allineamento **indiretto ma reale**: requisiti ancorati/riverificati tengono `requirements/`/wiki/`CLAUDE.md`
onesti rispetto al codice, rafforzando veridicità/freschezza del contesto che il RAG serve (periferico al
differenziatore, non gonfiato). **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI →
parametri per convenzione dal branch (forma da `083`); nessun hook eseguito; git non eseguito; MCP
`sertor-rag` interrogato (nessun errore tool). Branch `084-speclift-self-host`. Storico:
`specs/083-default-model-policy-copilot/plan.md` (FEAT-015 epica **sertor-cli** (E2) — **default
model-policy per i subagent Copilot CLI**: quando l'ospite è **GitHub Copilot CLI**, Sertor rende i 5
agenti Sertor-authored come `.agent.md` ma oggi **omette sempre** `model:` → modello implicito e
variabilità non voluta tra installazioni (feedback utente `wiki/sources/usersfeedback/copilot-default-models.md`).
La feature distribuisce a ciascuno un **default ragionato** (dispatcher meccanici `concierge`/
`configuration-manager` → `claude-haiku-4.5`; scrittura/reasoning/sintesi `requirements-analyst`/
`requirements`/`wiki-curator` → `claude-sonnet-4.6`) via il campo `model:` del frontmatter, da una
**fonte unica versionata** nel kit condiviso `sertor-install-kit`, restando **modificabile** dall'utente.
**ADDITIVA / distribuzione-installer pura, ZERO `sertor_core`** (Principio XI), zero LLM, verificabile
offline; **path Claude byte-identico** (`model: sonnet` di `concierge` invariato). **6 forche di *come*
risolte (research, ancoraggio MCP `search_code`/`find_symbol`/`who_calls`, nessun errore tool):**
**DA-D-1** profilo = **nuovo modulo `sertor_install_kit/model_policy.py`** (mappa costante Python
`_MODEL_POLICY` + `MODEL_POLICY_VERSION="1"` + `IN_SCOPE_AGENTS` + `resolve_model()`, riesportato dal kit;
scartati file-dati e risolutore esterno — importato non copiato = no drift). **DA-D-2** innesto =
**estendere `render_custom_agent`** (`surfaces.py:53`) sostituendo il parametro-eco `include_model: bool`
con **`model: str | None`** (sostituzione dal profilo, MAI eco dell'alias canonico); i **3 call-site**
(`install_rag._render_rag_file`, `install_wiki._render_for_target`, `install_governance._render_for_target`)
derivano il nome-agente dal basename `target_rel` e passano `resolve_model(name)`; post-processing scartato.
**DA-D-3** guardie riconciliate da «substring `haiku` assente» a «valore `model:` **non è un alias nudo**
(`haiku`/`sonnet`/`opus`) **e** = policy-id» (sottigliezza: `claude-haiku-4.5` **contiene** `haiku` → il
vecchio assert darebbe falso positivo); helper `_model_value`; **nuova real-asset guard** sui 5 depositi in
`tmp_path` + `_render_rag` parity allineato (`test_assets_copilot_guard.py`/`test_schema_copilot_frontmatter.py`/
`test_assets_copilot_parity.py`). **DA-D-4** fail-loud = **nuovo `ModelPolicyError(InstallerError)`** nominante,
materializzato al **build del piano** (prima di ogni scrittura → nessun deposito parziale), stesso
`resolve_model` del render. **DA-D-5** profilo NON è un asset → fuori dal sync-guard (`test_assets_sync.py`);
importato da entrambi i pacchetti = no drift per costruzione (scioglie R-5); guardia di coerenza `IN_SCOPE_AGENTS`
== 5 nomi depositati + pin dei 5 ID. **DA-D-6** nessun fallback strutturale nel primo taglio (documentale/globale,
YAGNI III). **DoD:** distribuzione via `sertor install rag` (concierge/wiki-curator) + `sertor-flow install`
(gli altri 3), doc utente `docs/install-copilot.md` + tabella capability `packages/sertor/docs/install.md`
aggiornate nello stesso step. **Scope promosso:** assegnazione modello agli `speckit.*` (prompt-file spec-kit,
supporto `model:` non confermato → spike) → **nuova voce backlog `FEAT-NNN` epica `sertor-cli`** (dichiarata,
edit del flusso principale). `sertor-core` **INVARIATO** (RNF-8). Constitution **PASS 12/12 + missione PASS**
(pre e post-design) senza deroghe (Complexity Tracking vuoto) — assegnare a ogni agente un modello adeguato al
compito migliora **qualità e prevedibilità** del lavoro dell'agente ospite sul corpus fuso e rende reale la
host-agnosticità (Principio X). **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI →
parametri per convenzione dal branch (forma da `082`); nessun hook eseguito; MCP `sertor-rag` interrogato
(nessun errore tool). Branch `083-default-model-policy-copilot`. Storico:
`specs/082-parity-guard-budget/plan.md` (FEAT-024 epica **debito-tecnico** (E10) — **parity guard esteso
(.ps1/.json) + budget di altitude dei blocchi CLAUDE.md in CI**: chiude due falle nei guard-rail offline
(audit ISSUE-10) con **tre guardie ADDITIVE solo-test, ZERO `sertor_core`, zero codice runtime**
(comportamento installer byte-identico). **(A, Must)** *shape-guard di presenza* del wiring Copilot rag:
eseguito `build_rag_plan`+`execute_rag_plan` per `COPILOT_CLI` in `tmp_path`, asserisce che
`sertor-hooks.json` contiene ≥1 entry sotto `SessionEnd`/`SessionStart`/`PreToolUse` (quest'ultimo con
`matcher` non vuoto) — chiude il drift silenzioso ISSUE-10 (FEAT-049: wiring in formato Claude scartato →
0 hook); **complementa, non sostituisce** `assert_valid_copilot_hook_file` (schema ≠ presenza).
**(B, Must)** *budget altitude* dei 3 `claude-md-block*.md` always-on con **soglie per-blocco costanti
DIFFERENZIATE** (decisione fissata): **wiki=60** (attuale 52) · **RAG=58** (49) · **SDLC=70** (64) — sotto
i valori pre-FEAT-021 (wiki 71/RAG 72) così la riduzione non si erode; coverage **esaustiva** (un 4° blocco
non registrato → rosso). **(C, Should)** *source-level guard* offline: i 3 script rag SessionEnd
(`rag-freshness`/`memory-capture`/`version-check.ps1`) non emettono un payload Copilot `decision` su
stdout. **3 forche di *come* risolte (research):** **DA-D-1** Gruppo A = **file nuovo**
`test_copilot_hook_presence.py` + funzione pura `assert_events_present(data, expected)` (anti-pattern via
rimozione del solo evento `PreToolUse` = unico frammento; **limite per-evento dichiarato**: `SessionEnd`
ha 3 frammenti, la guardia cattura la rimozione dell'ultimo frammento di un evento; costante
`_EXPECTED_RAG_EVENTS` con commento solidale dei 6 frammenti, pattern `_RAG_HOOKS`); riusa `_rag_wiring`
(`tmp_path`, `make_runner`) di `test_schema_copilot_hooks.py`, **non** lo importa → indipendente
(FR-004). **DA-D-2** Gruppo B = **suite root** `tests/unit/test_claude_md_block_budget.py` (cross-package
sertor+sertor-flow, precedente `test_assets_sync.py`); registro costante `_BUDGETS{(anchor,rel):soglia}`,
conteggio `len(read_asset_text(anchor,rel).splitlines())` (±1-safe), discovery esaustiva via
**walk-`Traversable`** dei due pacchetti (legge solo i `claude-md-block*.md`, evita asset binari). **DA-D-3**
Gruppo C = **file nuovo** `test_hooks_rag_no_stdout_payload.py` (offline, **nessun `pytestmark` pwsh** —
`test_hooks_script_copilot.py` ha skipif-pwsh di modulo → non vi si mette il guard offline); vieta la
**chiave `decision`** (`re` `["']?decision["']?\s*[:=]`, JSON/hashtable), **non** `reason`/`-Reason`
(false-positive sul breadcrumb FEAT-019, `Write-HookBreadcrumb -Reason`); strip `<# … #>`+`#` riusato da
`test_assets_hook_cli_invocation.py`. **Ancoraggio (MCP `search_code`, nessun errore tool; conteggi/righe
via `Read`):** `install_rag.py:695-715` (6 frammenti `_rag_hook_fragment`/`render_copilot_hooks`),
`surfaces.py:162-190` (`HookEntrySpec`/`render_copilot_hooks`), `test_schema_copilot_hooks.py:25-64`
(`assert_valid_copilot_hook_file`, `_rag_wiring`), `resources.py` (reader parametrico per-anchor). Stato
verificato wiki **52**/RAG **49**/SDLC **64**. **Ogni guardia ha anti-pattern** (non-vacuità). Guardie
esistenti **invariate** (`test_schema_copilot_hooks`/`test_assets_copilot_parity`/`test_hooks_script_copilot`/
`test_assets_sync`). Out-of-Scope: sync `assets/rag/**`↔`.claude/` + fork IT eval-skill → **FEAT-025**;
invarianti di contenuto sui `.ps1`/`.json` → Won't. Constitution **PASS 12/12 + missione PASS** (pre e
post-design) senza deroghe (Complexity Tracking vuoto) — Fail Loud (Principio XII) reso CI: ciò che
degradava in silenzio diventa rosso. **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md`
ASSENTI → parametri per convenzione dal branch (forma da `081`); nessun hook eseguito; MCP `sertor-rag`
interrogato (nessun errore tool). Branch `082-parity-guard-budget`. Storico:
`specs/081-stub-copilot/plan.md` (FEAT-023 epica **debito-tecnico** (E10) — **rimozione stub fuorviante
`assets/copilot/`**: igiene host-facing **sottrattiva**. Rimuove il tree
`packages/sertor/src/sertor_installer/assets/copilot/**` (4 `.gitkeep` + 4 dir vuote
`agents/`/`hooks/`/`instructions/`/`prompts/` + `copilot/` stessa), creato in FEAT-044 ipotizzando asset
Copilot statici e svuotato in FEAT-049 quando i JSON furono sostituiti dalla **generazione a runtime nativa**
(`render_copilot_hooks`/`render_custom_agent`/`render_prompt_file` in `sertor_install_kit.surfaces`). Lo stub
vuoto è **fuorviante** (suggerisce asset statici che non esistono); i payload Copilot sono generati
**interamente** da `assets/claude/**`+`assets/rag/**`, **zero consumatori** leggono `assets/copilot/`
(verificato grep). **ZERO `sertor_core`** (Principio XI) e **ZERO modifiche a `install_rag.py`/`surfaces.py`/
`pyproject.toml`**: generazione Copilot byte-identica (hatchling glob ricorsivo → nessun cambio packaging).
**Decisione di scope FISSATA (Opzione A):** rimozione, **nessun README di rimpiazzo** (sarebbe un body asset
in contraddizione col guard `test_no_hand_maintained_copilot_prompt_bodies`). **2 forche di *come* risolte:**
**DA-D-1** guardia anti-ricomparsa = **estensione** di `test_assets_copilot_guard.py`
(`test_no_copilot_asset_directory`, asserisce assenza dir via `asset_path("copilot").is_dir()` — riuso API
esistente, offline/deterministico, fail-loud sul ritorno dello stub) **non** un file nuovo (coesione con la
famiglia di guardie Copilot); **DA-D-2** commento esplicativo in `install_rag.py` = **NO** (violerebbe
l'out-of-scope «install_rag.py invariato» + un commento può divergere; l'intento vive nella **docstring del
test**, enforced — Principio XII). File: rimozione 4 `.gitkeep` + estensione 1 test; nessuna modifica ai test
esistenti (`test_assets_copilot_parity.py`/`test_install_rag_copilot_cli.py`/`test_packaging.py` restano
verdi). Out-of-Scope promossi: budget altitude / parity-guard `.ps1`/`.json` → **FEAT-024**; fork IT eval-skill
→ **FEAT-025**; doc editoriale architettura generativa → intervento autonomo. Constitution **PASS 12/12 +
missione PASS** (pre e post-design) senza deroghe (Complexity Tracking vuoto) — la stella polare è la realtà
del contesto reso al lettore del repo: rimuovere uno stub che comunica un'architettura inesistente. **Nota di
processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per convenzione dal branch (forma da
`080`); nessun hook eseguito; MCP `sertor-rag` non interrogato (posizioni note, eccezione «fatto puntuale») →
nessun errore MCP. Branch `081-stub-copilot`. Storico:
`specs/080-pulizia-stile-skill/plan.md` (FEAT-022 epica **debito-tecnico** (E10) — **pulizia stile delle
skill distribuite**: igiene host-facing degli asset **skill** che Sertor deposita via `sertor install rag` e
`sertor-flow install`. Quattro sintomi (audit ISSUE-08): ALL-CAPS enfatico pervasivo, sezioni «What NOT to
do»/«Hard boundary» ridondanti, `wiki-playbook.md` (281) senza ToC, wikilink orfano `[[assistant-targeting]]`
che sull'ospite punta al nulla. **ADDITIVA, solo forma/leggibilità, ZERO `sertor_core`** (Principio XI):
tocca **5 asset `.md`** (`guided-setup`/`eval-suite-author`/`eval-feedback`/`wiki-playbook` di `sertor`;
`requirements/SKILL.md` di `sertor-flow`) + 2 guardie nuove + 1 estensione; **nessun** cambiamento di
comportamento/semantica (pin load-bearing). **Decisioni di scope FISSATE (spec):** **(DA-1)** callout «How to
invoke» delle 2 eval-skill → **pointer** a `sertor-cli-reference.md` (FEAT-021), closure-safe by construction
(le eval-skill sono nel piano RAG che deposita il reference); **(DA-2)** ALL-CAPS normalizzato **anche** in
`requirements/SKILL.md` (`SEMPRE`→`sempre`), **lingua IT invariata** (IT→EN è E12); **(DA-3)** `[[assistant-targeting]]`
→ **rimozione della frase intera** (non load-bearing). **Forche di *come* risolte (research):** **(DA-D-1)**
regola operativa ALL-CAPS = parola A–Z ≥2 in prosa (corpo + `description:`), escluse code span/fenced/output
CLI + **allowlist** `RAG CLI MCP API JSON JSONL YAML TOML URL NL POSIX HTTP SDLC MRR STOP PASS FAIL PATH`
(+`EARS FEAT REQ` per A5); la **guardia** enforce il sottoinsieme `[A-Z]{4,}` post-strip, gli ≤3 (`NOT`/`DO`/`WAS`)
restano giudizio. **Inventario reale misurato** (post-strip): guided-setup `ONLY`×3/`MANDATORY`/`EVERY`/`WITHOUT`;
eval-suite `DERIVES`/`ONLY`×2/`BUILD`/`ASSISTED`/`DETERMINISTIC`×2/`DOES`×2/`DATA`/`NAVIGATION`/`DISCOVER`/`EMPTY`/`SHOULD`;
eval-feedback `OFFER`; playbook `SAME`/`JUDGMENT`; requirements `SEMPRE`. **(DA-D-2)** ToC = solo §0–§7 (8 voci,
più stabile delle subsection) sotto `## Contents` dopo il blockquote introduttivo, **anchor GitHub** della
heading reale (8 anchor esatti in `data-model.md`; il `## [YYYY-MM-DD]` è dentro un fenced block → escluso).
**(DA-D-3)** rimozione frase wikilink (il parentetico precedente copre già la parity guard). **(DA-D-4)** guardia
anti-regressione **nuova** `test_assets_skill_style.py` (per `sertor` e per `sertor-flow`): ALL-CAPS=0 post-strip
meno allowlist · zero `[[` bare · pointer eval presente/callout assente · **pin semantici** load-bearing (no
perdita regole) · meta non-vacui; + estensione `test_assets_cli_invocation.py` (`test_eval_skills_point_to_reference`);
**closure** del reference già coperta da `test_cli_reference_closure_in_rag_plan`. **(DA-D-5)** condensazione
«What NOT to do»: guided-setup **rimossa** (tutti e 7 gli item duplicano regole inline — Step 2/4/6 + Consent
gate + Hard boundary, verificati uno a uno); eval-suite tiene 2 item unici (secrets, no-invent-paths) e rimuove
il duplicato eval-run; eval-feedback **piega** l'unico item unico (secrets) nella Hard boundary. **Sync reale:**
`wiki-playbook.md` via `python -m sertor_installer.sync` (guardia `tests/unit/test_assets_sync.py`),
`requirements/SKILL.md` via `python -m sertor_flow.sync` (guardia sertor-flow). **⚠️ FINDING promosso:** i dogfood
`.claude/skills/eval-*` sono un **fork ITALIANO stantio non guardato** (drift pre-esistente su `master`, non
introdotto qui) → **fuori ambito stile**, da promuovere a debito E10 (riconciliazione lingua/sync + guardia
rag-skill dogfood). **Cross-ref durevoli:** budget altitude CI → **FEAT-024**, stub `assets/copilot/` →
**FEAT-023**, traduzione IT→EN → **E12**. `sertor-core` **INVARIATO**; installer/lifecycle invariati. Constitution
**PASS 12/12 + missione PASS** (pre e post-design) senza deroghe (Complexity Tracking vuoto) — è la stella polare
resa pulita (contesto agente più leggibile e veritiero, niente link al nulla). **Nota di processo:**
`setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per convenzione dal branch (forma da `079`); nessun
hook eseguito; MCP `sertor-rag` interrogato in apertura (nessun errore tool), conteggi/inventario via
`Read`/`Grep`/script. Branch `080-pulizia-stile-skill`. Storico:
`specs/079-altitude-claude-md/plan.md` (FEAT-021 epica **debito-tecnico** (E10) — **ridurre l'altitude
dei blocchi CLAUDE.md distribuiti + fonte unica «How to invoke»**: Sertor inietta **tre blocchi
always-on** (~208 righe) nel file di istruzione di ogni ospite — wiki-ritual (`SERTOR:WIKI-RITUAL`, 71),
SDLC-ritual (`SERTOR:SDLC-RITUAL`, 65), RAG-usage (`SERTOR:RAG-USAGE`, 72) — che mescolano **direttive
comportamentali standing** (cosa usare, cosa non importare, fail-loud MCP, flusso SpecKit) con
**dettaglio operativo lookup-on-demand** (sintassi di invocazione, troubleshooting `pywin32`/Python
3.14, enumerazioni CLI) che spreca budget di contesto a ogni sessione; la sezione «How to invoke
Sertor's commands» + Windows note è **triplicata** (RAG block `:12-38` · `guided-setup/SKILL.md:52-78`
· `wiki-playbook.md:93-112`). La feature **riduce ogni blocco a direttiva standing + pointer** ed
**estrae «How to invoke» in una fonte unica** host-agnostica citata per nome. **ADDITIVA / igiene
host-facing, ZERO `sertor_core`** (Principio XI): tocca solo asset `.md`, **un** `Artifact` FILE nel
`build_rag_plan` (`install_rag.py`, installer non-core), le copie dogfood `.claude/` e le guardie di
test; **nessun nuovo** `ArtifactKind`/`WriteStrategy`/`Surface`/seam del kit. **DA-D-r1 (dove vive il
reference) → Opzione A:** nuovo asset `rag/sertor-cli-reference.md` depositato da `sertor install rag`
in **`.sertor/sertor-cli-reference.md`** (target host-agnostico, identico Claude/Copilot; coperto
dall'owned_dir `.sertor`, aggiornato su upgrade, rimosso in blocco su uninstall). **Riframe decisivo:**
tra i tre blocchi always-on **solo il RAG block** cita il reference (il blocco wiki cita il **wiki
playbook**, REQ-014; SDLC non cita) → REQ-007 («no pointer morto su install solo-wiki/solo-governance»)
soddisfatto **per costruzione**; la tensione cross-capacità resta solo per il `wiki-playbook` (payload
di skill, dedup = REQ-009 **Should**). **Risoluzione closure-safe del `wiki-playbook`:** rimuove la
sottosezione duplicata «How to invoke the runtime CLIs» + Windows note, **tiene** la forma minima §2
(`uv run --project .sertor sertor-wiki-tools`) per l'auto-contenimento wiki-only, e usa una **frase
condizionale SENZA token di file** verso il reference RAG (`_BACKTICK_REF` non la matcha → niente
pointer morto sul piano wiki, REQ-007/NFR-5); la **sezione completa + Windows note vive in UN asset** →
**CS-2**. **DA-D-r2:** criterio qualitativo «standing inline, lookup a pointer» (NO soglia numerica = è
**FEAT-024**); contenuto minimo per blocco in `contracts/reduced-blocks.md` (RAG: vehicle-only/no-import
`sertor_core` + search-first + MCP-error + memory-gate + pointer reference; wiki: golden rule + outline
rituale + delega + D↔N + pointer `wiki-playbook.md`, estratte operazioni/convenzioni; **SDLC INVARIATO**).
**DA-D-r3:** confermato per lettura — il blocco SDLC NON contiene «How to invoke» (solo fasi SpecKit,
constitution gate, error discipline, git policy) → **nessuna modifica di contenuto** al blocco
`sertor-flow`. **DA-D-r4:** guardia di non-reintroduzione = **assert testuale** (heading «How to invoke
Sertor's commands» / `pywin32_bootstrap` / `uvx --from` assenti dai due blocchi `sertor` + assert
gemello SDLC via `kit_read("sertor_flow", …)`) + **closure del reference** (estensione di
`test_assets_copilot_parity.py`, gemella di `_usability_closure_offenders`: il basename
`sertor-cli-reference.md` citato nei body RAG è target del piano RAG per Claude **e** Copilot); **rework**
di `test_assets_cli_invocation.py` (`test_canonical_guide_present_where_first_invoked` → guida nel
reference, pointer nelle altre sedi; `test_wiki_playbook_ships_runtime_invocation_guide` → forma minima
+ assenza sottosezione; `test_rag_usage_block_uv_run_replaces_bare_search` **resta verde**; reference
aggiunto al footgun-check). **Stima CS-1:** 208 → ~166 righe always-on (RAG −24, wiki −18, SDLC 0); il
dettaglio estratto vive nel reference on-demand (~30 righe) + nel playbook. **Sync dogfood (CS-6):** solo
`wiki-playbook.md` è sotto `assets/claude/**` → `python -m sertor_installer.sync` riallinea
`.claude/skills/wiki-author/wiki-playbook.md`; gli altri asset (sotto `assets/`/`assets/rag/`) non sono
sincronizzati. **Residui promossi:** mini-note eval «How to invoke `sertor-rag`» (3 righe, fuori
triplicazione) → **FEAT-022**; budget altitude CI → **FEAT-024**; stub `assets/copilot/**` →
**FEAT-023**. **CLAUDE.md di radice Sertor FUORI ambito** (DA-1, documento autonomo non sincronizzato).
Constitution **PASS 12/12 + missione PASS** (pre e post-design) senza deroghe (Complexity Tracking
vuoto) — meno rumore always-on = più budget per il contesto fuso code+doc + una fonte unica senza
deriva. **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per
convenzione dal branch (forma da `078`); nessun hook eseguito; MCP `sertor-rag` interrogato
(`search_code` sul wiring SDLC, nessun errore tool). Branch `079-altitude-claude-md`. Storico:
`specs/078-portabilita-os-hook/plan.md` (FEAT-018 epica **debito-tecnico** (E10) — **portabilità OS
degli hook (guardia `pwsh` + gap dichiarato) + onestà sui surface inerti**: realizza i **Principi XII
«Fail Loud, Fix the Cause»** e **X (portabilità reale)** rendendo onesti due claim impliciti
dell'installer, **ADDITIVA + host-facing, ZERO codice di core** (Principio XI: nessun import di
`sertor_core`, nessun LLM). **Causa-radice (verificata):** gli hook sono tutti `.ps1`; il wiring Claude
li invoca con `"shell": "powershell"` (= `powershell.exe`, Windows PowerShell 5.1 — inesistente su
mac/Linux → hook mai eseguito, nessun messaggio, **exit 0**); il wiring Copilot usa già `pwsh -File`
(portabile **se** `pwsh` in PATH). **Strategia FISSATA (non riaperta):** guardia `pwsh` + **gap
dichiarato**, hook **PowerShell-only** (nessun gemello `.sh`, convenzione «solo PowerShell»). Onestà via
il meccanismo **esistente** `InstallReport.notes` (`sertor-install-kit/report.py:44/74`, finora
inutilizzato in produzione → **prima emissione reale**). **(1) Guardia `pwsh`:** su host non-Windows
senza `pwsh`, un `install rag`/`wiki` che deposita hook aggiunge una **nota azionabile** (surface `.ps1`
affetti + URL PowerShell Core + frase «installati ma non-operativi») in resa **umana e JSON**;
**non-fatale** (exit 0, tutti i surface non-hook installati); **nessuna** nota su Windows (FR-006) o con
`pwsh` presente (FR-004); Claude+Windows resta `report.notes == []` (non-regressione
`test_claude_report_has_no_gap_note`). **(2) Onestà Copilot:** ogni `install rag --assistant copilot-cli`
emette una nota che dichiara `memory-capture` richiedente `SERTOR_MEMORY=true` + `SERTOR_MEMORY_ADAPTER`
adapter Copilot esplicito (col default scatta ma non cattura) + **cross-ref** alla capacità pianificata
(distribuzione valore adapter nel template `.env` → **FEAT-009 epica memoria-conversazioni**, qui solo la
nota). **DA-D-r1 risolta (research D-1):** logica `pwsh` in **helper condiviso del kit** (NUOVO modulo
puro `host_env.py`: `is_windows`/`pwsh_available`/`pwsh_unavailability_note`/`maybe_note_pwsh` +
`PWSH_INSTALL_URL`, stdlib `os`/`shutil`, mockabile) — DRY (rag+wiki oggi, `sertor-flow` domani), seam
di mock unico; la nota `memory-capture` resta in `install_rag.py` (rag-specifica, single consumer). Hook
surfaces **derivate dal piano** (`[a.target_rel for a in plan if a.endswith('.ps1')]`, dichiarativo, no
hardcode). Emissione al seam `execute_rag_plan`/`execute_plan` (wiki), **dopo** `_kit_execute_plan`; CLI
thin invariata. **DA-D-r2 risolta (research D-2):** nota `memory-capture` **sempre** su install rag
Copilot CLI (anticipatoria — chi abiliterà la memoria deve saperlo ora; install-time non conosce il
`SERTOR_MEMORY` runtime), indipendente da `SERTOR_MEMORY`; + **sì** aggiornare la tabella capability
`packages/sertor/docs/install.md` (nota operatività per target). **Quesito wiring (research D-3): la
guardia RILEVA+SEGNALA, NON riscrive il wiring** — cambiare `"shell": "powershell"`→`pwsh` romperebbe
gli utenti Windows con la sola PS 5.1 (target primario, NFR-5); Copilot è già portabile (`pwsh -File`).
**Limite tecnico aperto dichiarato (non inventato):** se Claude Code non mappa `shell:"powershell"`→`pwsh`
su non-Windows, installare `pwsh` da solo potrebbe non bastare lì → la nota resta **narrow** su «`pwsh`
non trovato», i doc dichiarano l'operatività completa per-target, e «wiring hook Claude portabile su
non-Windows» è **promosso a candidata follow-up** (roadmap → *Nuove funzionalità da discutere*). **(3)
Doc utente** (DoD «setup→doc utente»): `docs/install.md` (prerequisito `pwsh` su mac/Linux + URL +
surface + sezione operatività-per-target), `docs/install-copilot.md` (hook richiedono `pwsh` +
`memory-capture` richiede config adapter), tabella capability `packages/sertor/docs/install.md`. **(4)
Guard tests** deterministici (OS mocking via `monkeypatch.setattr(host_env, …)` — CI su Windows, R-6):
nota pwsh presente/assente/Claude+Windows`==[]`, nota `memory-capture` su rag Copilot/assente su Claude;
sync dogfood↔bundle `test_assets_sync.py` **verde per costruzione** (la feature non tocca alcun asset).
**Additivo:** `sertor-core` INVARIATO; **nessun nuovo** `ArtifactKind`/`Surface`/`WriteStrategy`/porta/
seam/schema/env/dipendenza; schema `install.report/1` invariato (`notes[]` nel JSON solo se non-vuoto);
breadcrumb runtime FEAT-019 complementare (quella = «lo script gira ma fallisce dentro», questa = «lo
script non parte perché manca `pwsh`»). **Out-of-Scope promossi** (non sepolti): distribuzione adapter
`.env` → FEAT-009 memorie; visibilità SessionStart Copilot → E10-FEAT-008; wiring Claude portabile
non-Windows → candidata follow-up; nota su `upgrade` → estensione triviale futura (non FEAT); stile body
→ FEAT-021/022; gemello `.sh` + guardia `pwsh` runtime → Won't. 7 US/15 FR/6 CS. Constitution **PASS
12/12 + missione PASS** (pre e post-design) senza deroghe (Complexity Tracking vuoto) — portabilità resa
**onesta** protegge la stella polare (l'ospite non opera credendo di avere protezioni che non ha).
**Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per convenzione dal
branch (forma da `077`); nessun hook eseguito; MCP `sertor-rag` interrogato (`search_code` su
`InstallReport.notes` + wiring hook per-assistente, **nessun errore tool**). Branch
`078-portabilita-os-hook`. Storico:
`specs/077-fail-loud-hook-agent/plan.md` (FEAT-019 epica **debito-tecnico** (E10) — **fail-loud
breadcrumb negli hook + fallback «asset mancante → STOP» negli agent**: realizza il **Principio XII
«Fail Loud, Fix the Cause»** su due classi di asset first-party distribuiti agli ospiti, **ADDITIVA +
host-facing, ZERO codice di core** (gli hook continuano a NON importare `sertor_core` e a NON chiamare
un LLM — Principio XI). **(1) Hook fail-loud:** i 4 hook PowerShell in scope (`memory-capture`,
`rag-freshness` sui **soli path catastrofici**, `wiki-pending-check`, `version-check`) smettono di
inghiottire i fallimenti con `catch` vuoti/`2>$null`/`exit 0` muti: sui path degradati scrivono un
**breadcrumb ispezionabile** `.sertor/.last-hook-error` (JSON schema `hook.error/1`, campi
`hook`/`ts` UTC/`reason`, **sovrascritto** = semantica «ultimo errore», + nota minima su stderr),
**gemello esatto** di `.sertor/.rag-health.json` (stesso pattern, ignore/uninstall di runtime),
restando **non-fatali** (`exit 0` sempre, scrittura **best-effort** mai un nuovo path fatale). **(2)
Fallback agent:** i 3 body (`concierge`→`guided-setup`, `wiki-curator`→`wiki-playbook.md`/`ops/`,
`requirements-analyst`→skill `requirements`) ricevono la regola **uniforme** «asset di cui sono guscio
non risolvibile/leggibile → **STOP** e segnala», in testo **host-agnostico byte-identico
Claude↔Copilot** (no `.claude/` path, no slash-command, no nome-modello Claude). **DA-3 FISSATA in
spec** (breadcrumb = file singolo `.sertor/.last-hook-error`). **DA-D-r1 risolta (research D-2/D-3):**
convenzione = funzione PowerShell **inline `Write-HookBreadcrumb`** byte-identica nei 4 hook (NON un
file dot-sourced — i 4 hook sono asset installati indipendentemente su capacità diverse rag/wiki; la
«convenzione condivisa» REQ-009 è la funzione identica + lo schema), best-effort/secret-free; punti di
scrittura precisi: **memory-capture** = invocazione `memory archive` fallita (catch + `$LASTEXITCODE`,
nativo-PS non solleva su exit non-zero), **no-op gated** `SERTOR_MEMORY` off → niente breadcrumb
**by-construction** (il gate `exit 0` precede ogni risoluzione di root, REQ-004); **rag-freshness** =
3 path muti che **bypassano** il verdetto (spawn worker fallito · re-index fallito post-health-write ·
worker crash), MENTRE la degradazione `doctor` resta governata da `.rag-health.json` (già fail-loud,
no doppio segnale); **wiki-pending-check** = `scan` non risolvibile (catch `:70-73`); **version-check**
= catch catastrofico `:166-168` (copre anche REQ-006 lettura cieca stato proprio). Gli hook `*-start`
read-only restano **fuori scope** (fallback definito, non nascondono problemi). **DA-D-r2 risolta
(research D-4):** guardie statiche/offline modellate su `test_assets_hook_cli_invocation.py` —
**Guardia A** lint breadcrumb (ogni hook in scope definisce+invoca `Write-HookBreadcrumb`; nessun
`catch` vuoto/`exit 0`-solo eccetto il sink interno della funzione), **Guardia B** assert fallback sui
3 body (token stabili `STOP` + nome-asset + «cannot be resolved or read»), **parità host-agnostica
RIUSATA** (`test_assets_copilot_parity.py` copre già i 3 agent → fallback coperto gratis, REQ-013), +
**Guardia C** (scoperta **D-5**): i 3 hook **rag** dogfood `.claude/hooks/` sono git-tracked ma **NON**
coperti da alcuna guardia di sync (la root `test_assets_sync.py` copre solo `assets/claude/**`) → nuova
guardia byte-identità dedicata; + **Guardia D** `".sertor/.last-hook-error" in RUNTIME_IGNORES`
(gemella `test_version_check_runtime_ignores`). **Lifecycle:** unica modifica al kit = **una riga** in
`RUNTIME_IGNORES` (`gitignore_append.py`); uninstall già rimuove `.sertor/` runtime + righe
`.gitignore`; **nessun nuovo** `ArtifactKind`/`WriteStrategy`/`Surface`/seam. Cross-pacchetto: `sertor`
(4 hook + `concierge` + `wiki-curator`) e `sertor-flow` (`requirements-analyst`, senza dipendenza da
`sertor-core`). **Out-of-Scope promossi** (non sepolti): consumo attivo della traccia all'avvio →
**Could** debito-tecnico; portabilità OS hook + onestà surface Copilot → **FEAT-018**; pulizia
stile/altitude body + `CLAUDE.md` → **FEAT-021/FEAT-022**. 9 US/17 FR/6 CS. Constitution **PASS 12/12 +
missione PASS** (pre e post-design) senza deroghe (Complexity Tracking vuoto) — è il Principio XII reso
enforced (ogni rottura del macchinario host-facing si **vede** invece di marcire, anti dogfooding
cieco). **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per
convenzione dal branch (forma da `076`); nessun hook eseguito; MCP `sertor-rag` interrogato
(`search_code` su wiring rag-health/RUNTIME_IGNORES, **nessun errore tool**); scoperta D-5 da
`Read`/`git ls-files`. Branch `077-fail-loud-hook-agent`. Storico:
`specs/076-enforcement-freschezza-rag/plan.md` (FEAT-011 epica **debito-tecnico** (E10) —
**enforcement deterministico della freschezza RAG (hook)**: sposta i due passi **meccanici** del
*rituale di step* — punto 5 (re-index del corpus) e punto 8 (smoke del RAG) — dalla **discrezione
dell'agente** a un **harness deterministico** (hook del client agente), applicando il confine **D↔N**:
la parte meccanica diventa *enforced*, all'agente resta il giudizio. **ADDITIVA + host-facing, ZERO
codice di core** (Principio XI): l'hook **consuma** i vehicle `sertor-rag index .` (incrementale,
FEAT-009 + cache FEAT-019 → zero-embedding a corpus invariato) e `sertor-rag doctor` (E12-FEAT-001, 4
aree), **mai** importa `sertor_core`. **Due tempi fail-loud:** **(SessionEnd)** `rag-freshness.ps1`
re-indicizza **incondizionatamente** (skip delegato all'incrementale del core, **nessun delta-check
nell'hook** — DA-1) + `doctor` → deriva un **verdetto** sano/degradato → se degradato **persiste** lo
stato + messaggio prominente; **(SessionStart)** ripesca lo stato e, se degradato, **induce** la
correzione (re-index/reconnect MCP) **prima** del lavoro agente — l'hook **segnala/induce**, l'agente
**esegue** (FR-014, no LLM nell'hook — DA-2). **Smoke = SOLO `doctor`** (DA-3): NON esercita il filtro
metadata `where` di `search_code`/`search_docs` (guasto 2026-06-19) → **buco dichiarato e promosso** a
**nuova FEAT-011 dell'epica usabilità E12** (owner di `doctor`), non sepolto; il rituale punto 8
dell'agente resta la rete. **Hook separato/indipendente** (script + voce `SessionEnd` propri, accanto
a `memory-capture`, NON fusi), **non-fatale** (exit 0 sempre, `try/catch` gemello memory-capture),
**per-capacità `rag`**, lifecycle install/upgrade/uninstall, parità Claude / Copilot CLI (formato hook
nativo — generato via `render_copilot_hooks` su Copilot, mai formato Claude — DA-4). **DA-D-r1 risolta
(research D-1):** file di stato = **`.sertor/.rag-health.json`** (sotto la radice runtime `.sertor/`,
igiene radice feature 016), formato **JSON** schema `rag.health/1` (`verdict`/`timestamp`/`reason`
minimi + `areas`/`exit_code` additivi da `doctor --json`); a `healthy` **riscritto** (non cancellato)
→ no-op all'avvio, **niente loop** (INV-1/NFR-6); **azione necessaria**: estendere `RUNTIME_IGNORES`
(kit) con `.sertor/.rag-health.json` (oggi non coperto da `.index*`/`.env`/`.venv`). **DA-D-r2 risolta
(research D-2):** aggancio SessionStart = **voce/script dedicato** `rag-freshness-start.ps1` (Claude) +
voce `SessionStart` propria, **NON** riuso di `wiki-session-start.ps1` (isolamento FR-016 + lifecycle
granulare); su **Copilot CLI** il SessionStart è un **prompt nativo statico** (nessuno script — A-005)
che istruisce l'agente a leggere lo stato e indurre. **Ancoraggio (verificato MCP `search_code` +
`Read`):** pattern hook riusato byte-per-byte da `memory-capture.ps1`
(`.claude/hooks/memory-capture.ps1:54-63`); wiring per-assistente da `install_rag.py` (FILE
`CREATE_IF_ABSENT` + `SETTINGS_MERGE` `MERGE_DEDUP`, `:317-340`; dispatch art-aware `_rag_hook_fragment`
`:424-446`; uninstall `delete_if_empty` per `sertor-hooks.json` `:590`; `sertor_owned_paths` `:510`);
render Copilot nativo `HookEntrySpec`/`render_copilot_hooks`
(`sertor-install-kit/.../surfaces.py:145-190`, formato `version:1`/`timeoutSec`/entry piatte, lezione
FEAT-011/049). **Guardia di sync** bundlato↔dogfood **mirata agli hook rag** (FR-024): la guardia
esistente `tests/unit/test_assets_sync.py` copre solo `assets/claude/**`, gli hook rag vivono in
`assets/rag/hooks/` → guardia dedicata nuova. **Nessun nuovo** `ArtifactKind`/`Surface`/`WriteStrategy`/
seam del kit (riuso). **Reclassificazione governance** (FR-019): step 5/8 del `CLAUDE.md` annotati
«enforced via hook» con nota D↔N (riclassificati, **non** rimossi — restano la rete fino a
distribuzione completa + chiusura buco `where`). **Out-of-Scope promossi** (research D-5): smoke-`where`
→ E12; staleness forte server MCP → osservabilita (cross-ref); drift-detection → osservabilita FEAT-012
(cross-ref). `sertor-core` **INVARIATO**; unica modifica al kit = `RUNTIME_IGNORES` (additiva). 9 US/24
FR/5 CS. Constitution **PASS 12/12 + missione PASS** (pre e post-design) senza deroghe (Complexity
Tracking vuoto) — è la stella polare resa enforced (contesto reso all'agente sempre fresco/reale).
**Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per convenzione dal
branch (forma da `075`); nessun hook eseguito; MCP `sertor-rag` interrogato (`search_code` sul wiring
installer hook, nessun errore tool). Branch `076-enforcement-freschezza-rag`. Storico:
`specs/075-guided-setup/plan.md` (FEAT-002 epica **usabilità** (E12) — **guided-setup — guida agentica
install→configure→verify**: la prima feature **agentica** dell'epica. Distribuisce **ENTRAMBI** (decisione
utente, pattern `sertor-flow` = agenti + skill): una **skill** `guided-setup` (il **«come»**: le istruzioni del
flusso) **E** un **agente vero** `concierge` (la **persona/orchestratore**, dispatcher sottile a un ramo che
instrada le richieste di setup verso `guided-setup`, con **model pin** `model: sonnet` su Claude). L'**agente
frontier dell'ospite** esegue per condurre l'utente da «repo non configurato» a «**RAG verificato**» (un
`sertor-rag doctor` verde), orchestrando **solo** i vehicle deterministici (`sertor install`, `sertor configure
--set`, `sertor-rag doctor`/`index`). Confine **D↔N**: l'intelligenza vive nell'agente ospite, **il core non
chiama mai un LLM**; la skill **usa** i comandi, non li reimplementa. **Natura ADDITIVO + scope di
distribuzione:** nessun codice runtime del core, nessun motore/porta/comando nuovo — 2 asset (1 skill + 1
agente markdown) + wiring di distribuzione dual-target + estensione della guardia di parità. `sertor-core` e
`sertor-install-kit` **INVARIATI** (riuso del seam, no estensione). **DA-G1/G2/G3 risolte con l'utente** (esegue
su conferma: check sola-lettura liberi, install/configure/index/download su conferma esplicita, segreti mai a
schermo; skill + agente; euristica provider minima + conferma). **DA-D-r1/D-r2 risolte (research D-1..D-7,
RIVISTE per «agente vero»):** **(D-1)** concierge = **AGENTE vero** `concierge` (contenitori
`.claude/agents/` ↔ `.github/agents/`, `model: sonnet`) + **skill `guided-setup`** (`.claude/skills/` ↔
`.github/skills/`); lo stub-skill `concierge-setup` è RIMOSSO. **(D-2)** body `guided-setup` single-file EN a
10 sezioni (hard boundary vehicle-only · consenso/gate mutazioni · 6 step detect→provider→install→configure→index→verify
· what-NOT), riferimento-per-nome agli asset (mai `.claude/`/slash-command/nomi Claude — lezione FEAT-001/056).
**(D-3)** euristica = 3 segnali via vehicle/file (creds cloud da `doctor --json`/`.env` read-only · airgapped
conversazionale/`--online` · semantica NL conversazionale) → proposta+conferma; provider in `.env` via
`configure --set SERTOR_EMBED_PROVIDER=…`. **(D-4)** wiring in `install_rag.py`: **skill** via
`_skill_artifacts(_USABILITY_SKILL_NAMES, is_copilot)` (pattern eval 065, byte-copia); **agente** via il pattern
`sertor-flow` (`install_governance.py`) — `_concierge_artifact(assistant)` con
`AssistantProfile.render_path(Surface.AGENT, name)` + helper di render **locale** `_render_rag_file(art)` (se
`.agent.md` → `render_custom_agent`, altrimenti byte-copy). Claude: `.claude/agents/concierge.md` byte-copy
(**`model: sonnet` preservato**); Copilot: `.github/agents/concierge.agent.md` (`render_custom_agent`, **`model:`
OMESSO** — invalido su Copilot, FEAT-011/049). **Nessuna nuova `ArtifactKind`/`Surface`/`WriteStrategy`**,
**nessun nuovo seam nel kit** (`render_custom_agent`/`Surface.AGENT`/`render_path` già esportati e usati da
`sertor-flow`); lifecycle: skill=`owned_dir`, agente=`owned_file`, upgrade render-aware. Asset bundled in
`packages/sertor/.../assets/rag/{skills/guided-setup/SKILL.md, agents/concierge.md}`. **(D-5)** guardia di
parità: **punto critico** = `_render_rag` del test allineato al render reale (traduce `.agent.md`) così
(a)(b)(c) no-`.claude/`/no-slash/no-nomi-Claude coprono **anche l'agente** e il `model: sonnet` Claude **non
sfugge** su Copilot; closure (d) **mirata** «ogni asset citato per nome è depositato» (`concierge →
guided-setup`); `test_no_wiki_artifacts_created` **ristretto** da «no agente» a «no agente **wiki**» (il rag
plan ora deposita l'agente `concierge`). Agent-discovery: l'agente vive nei contenitori `agents/` nativi
(attivazione governata dal `description` mirato al setup, non auto-attivazione indebita; la cautela 056
«agente-fantasma» riguardava un payload di skill, caso diverso). **(D-6)** test di deposito offline per skill +
agente (incl. `model: sonnet` presente su Claude / assente su Copilot · routing a un ramo no-FEAT-004/007 ·
byte-parità body). **(D-7)** tracciamento durevole: FEAT-009 → «parzialmente avviata (stub agente `concierge` a
un ramo)», FEAT-002 → in progress nel backlog d'epica. **Feature completa** solo quando Claude E Copilot ricevono
**skill E agente** via `sertor install` (FR-010/011 in ambito); prova LIVE su ospite reale = follow-up, non done
automatico (il done è deposito+parità offline). 9 US/13 FR/5 CS. Constitution **PASS 12/12 + missione PASS** (pre
e post-design) senza deroghe — usabilità periferica al differenziatore ma serve adozione/portabilità (Principio
X: un agente che sa installare/configurare/verificare Sertor da solo È host-agnosticità reale). **Nota di
processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per convenzione dal branch (forma da
`074`); nessun hook eseguito; MCP `sertor-rag` interrogato (`find_symbol build_governance_plan`/`AssistantProfile`,
`search_code`, nessun errore tool). Branch `075-guided-setup`. Storico:
`specs/074-doctor-salute/plan.md` (FEAT-001 epica **usabilità** (E12) — **`sertor-rag doctor` — verifica di
salute deterministica**: la primitiva «ha funzionato?» che oggi manca. In un comando-vehicle (Principio XI)
fotografa la salute di **quattro aree** — config/env · provider embeddings · indice · server MCP — con esito
per-area pass/warn/fail, causa + rimedio per ogni problema, output umano e `--json` a **schema stabile**
(`doctor.report/1`), ed exit code non-zero se un check critico fallisce. **Sola lettura, nessun LLM** (confine
D↔N, FR-014/015): l'intelligenza/spiegazione vive nelle skill dell'ospite, il core è puramente deterministico.
**Scope esteso a 2 pacchetti** (deciso con l'utente): `sertor-core` (comando `doctor`, owner E12) + `sertor`
(wizard `configure --check`, owner E2/FEAT-003) — chiude il debito *deferred* US5: `_probe_live`
(`configure.py:369`) cambia il comando invocato da `sertor-rag check` (inesistente) a `sertor-rag doctor
--area config --json` (sottoinsieme config, DA-D3), degrado onesto preservato; `configure` senza `--check`
byte-identico. **Architettura:** comando thin in `cli/__main__.py` (`_add_doctor_parser`/`_cmd_doctor`) →
servizio **puro** nuovo `services/doctor.py` (entità di esito `HealthReport`/`AreaReport`/`Problem`/`ProviderProbe`
+ funzioni pure `check_config`/`check_provider`/`freshness_from_manifest`/`check_mcp`/`assemble`) → formatter
puro `format_health_report` in `cli/output.py`; gate exit via nuovo `DoctorCheckFailed(SertorError)` (gemello
`RegressionDetected`); helper side-effect sottili in `composition.py` (`build_provider_probe`/`read_mcp_registration`/
`current_source_stats`). **Riusa i segnali GIÀ esistenti, nessuna nuova porta/dipendenza** (SC-012): env =
`Settings.validate_backend()` (`settings.py:238`, fonte unica — l'area provider statica eredita le chiavi
provider, no lista duplicata); indice presenza+freschezza = `IndexManifest.load(collection_name(...))`
(`index_manifest.py:122`, `composition.py:168`) — presenza ⇔ `load()→None`?, freschezza = `os.stat` sui **soli
file noti** vs mtime registrato (cheap pre-filtro del refresh incrementale, **niente re-scan/re-hash**); MCP =
lettura `.mcp.json` (`mcpServers.sertor-rag`, radice host); probe = `build_embedder()`+`embed(sentinel)`.
**DA-D4 (criteri critico/warn, codificata deterministica):** CRITICO (exit≠0) = env mancante **o** indice
assente/incompatibile; WARN (exit 0) = indice stantio · MCP non registrato · provider irraggiungibile col probe;
exit 1 ⇔ ≥1 `Problem` `CRITICAL`. **DA-D5 risolta:** **(D5a probe provider)** = `build_embedder(settings,
allow_download=False)` + `embed([sentinel])` su stringa minima costante → reachable/unreachable+motivo
(scrubbed); **non-indicizzante** (nessun upsert, SC-008), **offline-safe** (saltato senza `--online`), **mai
scarica GloVe**, testa il path reale via vehicle/factory senza accoppiare il comando a SDK/URL per-provider
(Principio I/II); scartato un «ping» per-provider (riporterebbe dettagli provider nel core, non testa il path
reale). **(D5b stantio-dopo-reindex MCP)** = best-effort derivato dai segnali già disponibili (indice stantio
**e** MCP registrato → warn «riavvia il server»); la rilevazione *forte* cross-processo **non esiste oggi** →
riportata `unknown`, **non finta** (Principio XII), debito promosso a osservabilità/server MCP. **Flag rete =
`--online`** (DA-D1: comando unico, offline-safe by default); `--area {config|provider|index|mcp|all}` realizza
il sottoinsieme config senza un secondo comando. **Privacy:** ogni stringa (umano+JSON) da `scrub_text`
(`observability/scrub.py:36`, FR-013/SC-006); evento osserv. `doctor` **metrics-only** (gemello `eval`,
`runner.py:34`) — mai chiavi/valori/sentinella/motivi/path. **Knob env:** il probe è un **flag CLI, nessun
nuovo env** → template `.env` installer invariato (SC-012); se mai diventasse env va promosso (owner E2). File
toccati: `sertor-core` (`services/doctor.py` nuovo, `cli/__main__.py`, `cli/output.py`, `domain/errors.py`,
`composition.py`, `tests/unit/test_doctor.py`+`test_cli_doctor.py` nuovi) · `sertor` (`configure.py::_probe_live`
+ test). Constitution **PASS 12/12 + missione PASS** (pre e post-design) senza deroghe — `doctor` rende **reale**
la host-agnosticità (Principio X): un agente verifica da solo la salute su un ospite qualunque, prerequisito del
retrieval fuso fruibile. **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per
convenzione dal branch (forma da `073`); nessun hook eseguito; MCP `sertor-rag` interrogato
(`find_symbol`/`search_code`, nessun errore tool). Branch `074-doctor-salute`. Storico:
`specs/073-cattura-copilot-cli/plan.md` (FEAT-008 epica **memoria-conversazioni** — **cattura memoria su GitHub
Copilot CLI**: aggiunge il **secondo adapter di cattura transcript** dietro la porta esistente
`TranscriptCaptureAdapter` (8ª porta). L'MVP memoria è host-agnostico in tutto il tier (archivio FEAT-001,
full-text FEAT-002, semantica FEAT-004, distillazione FEAT-003) **tranne la cattura** (oggi un solo adapter
`claude-code`); l'hook `SessionEnd` già depositato su ospiti Copilot da FEAT-009 è **inerte** perché manca la
sorgente. Questa feature la fornisce: `CopilotCliCaptureAdapter` (`kind="copilot-cli"`, stdlib-only,
best-effort non-fatale) che legge `~/.copilot/session-state/<uuid>/events.jsonl`, ne estrae i **soli** turni
user/assistant e associa ogni sessione al progetto. **Additivo** (nessuna nuova porta/motore, tier a valle
INVARIATO); a `SERTOR_MEMORY=false` (default) costo/comportamento identici (adapter non costruito, import lazy);
default adapter invariato (`claude-code`). **Decisioni di scope fissate empiricamente (Copilot CLI 1.0.63,
2026-06-22):** sorgente = `events.jsonl`; turni = `user.message`/`assistant.message` (testo = `data.content`,
NON `transformedContent`; `toolRequests` non sono turni); ogni altro `type` scartato; associazione progetto =
cwd/gitRoot dell'evento `session.start` (JSON puro, no YAML/`session.db`/cloud); nome adapter = `copilot-cli`;
legacy `history-session-state/` ignorata; cloud-sync = sola documentazione (no avviso runtime). **4 forche
residue chiuse (research):** **DA-CM-1** testo = `data.content` così com'è (nessuno streaming/delta nel JSONL
persistito); **DA-CM-2** progetto indeterminabile = **skip** + warning `memory_capture_session_unassociated`
(NO marcatore «unknown-project» → no stato artificiale, mai misattribuzione); **DA-CM-3** override percorso =
**`SERTOR_MEMORY_COPILOT_SESSION_DIR`** (mirror esatto di `SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`, nuovo campo
`Settings.copilot_session_dir` default `~/.copilot/session-state`); **DA-CM-4** filtro = **path-containment
normalizzato** (cwd **o** gitRoot antenato-o-uguale al progetto `str(Path.cwd())`, `normcase` case-insensitive
su Windows → cattura le sessioni avviate in sottocartelle del repo via gitRoot; match lessicale se il path
catturato non esiste sulla macchina, testabilità offline). **Wiring (4 punti):** `settings.py` (1 campo + 1
lettura env), nuovo `adapters/capture/copilot_cli.py` (adapter + helper puri `_session_context`/`_paths_match`/
`_turn_from_event`/`_parse_line`/`_parse_timestamp`, eventi metrics-only `memory_capture_*` parità Claude),
`composition.py` (`_VALID_MEMORY_ADAPTERS += "copilot-cli"` + dispatch su `settings.memory_adapter` in
`build_capture_adapter`, import lazy), test (`test_copilot_capture.py` su fixture + estensioni
`test_composition`/`test_settings`). `domain/memory.py`/`domain/ports.py`/`claude_code.py`/tier INVARIATI.
Local-first (solo file locali, zero rete, no `session-store.db`/cloud-sync), idempotenza ereditata
(`session_key`=UUID + `INSERT OR IGNORE`), scrub ereditato non bypassabile. **Debito promosso (NON qui):**
distribuzione `SERTOR_MEMORY_ADAPTER=copilot-cli` (+ override) nel template `.env` installer = **FEAT-009**,
backlog d'epica — la feature non è *done* finché un ospite Copilot non riceve il valore adapter via install.
Constitution **PASS 12/12 + missione PASS** (pre e post-design) senza deroghe — host-agnosticità (Principio X)
resa reale per la memoria sul secondo assistente. **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md`
ASSENTI → parametri per convenzione dal branch (forma da `072`); nessun hook eseguito; MCP `sertor-rag`
interrogato (`find_symbol`/`search_code`, nessun errore tool). Branch `073-cattura-copilot-cli`. Storico:
`specs/072-ricerca-semantica-memoria/plan.md` (FEAT-004 epica **memoria-conversazioni** — **ricerca semantica
opzionale sull'archivio**: percorso **opt-in** che ritrova le conversazioni passate **per significato** (non per
parola), affiancando — senza sostituire — la full-text FEAT-002. **Additivo**: riusa SOLO le primitive del core
(`build_embedder`/`build_store`/`collection_name`), **nessun nuovo motore** (DA-SS-1 = store vettoriale
**dedicato**, NON `IndexingService.index()` né il manifest file-keyed di FEAT-009, che è per file mutabili —
l'archivio è append-only). A leva spenta costo/comportamento **identici a oggi** (gate `build_*`→`None`).
**4 forche risolte:** **DA-SS-2** granularità = **TURNO** (`chunk_id=session_key#turn_index`, parità con
`EpisodicSearch`/FEAT-002; NO chunking sub-turno — i locali `glove`/`hash` non hanno tetto token rigido, turno
lungo→non-fatale; NFR-003 fissata < 1 s p95 archivio tipico, provider locale); **DA-SS-3** superficie =
**`memory search --semantic`** (un comando, due modi; + `memory index-semantic` per il backfill REQ-007; parità
MCP = FEAT-010 fuori ambito); **DA-SS-4** marker watermark = **stato dello store** (Opzione 3, NO registro
proprio: «già indicizzato» ⇔ i `chunk_id` dei turni esistono nella collezione; `upsert` idempotente + skip
per-sessione → REQ-006/030/NFR-009; scartate Opzione 1 colonna in `memory.sqlite` = accoppia FEAT-001/può
divergere, Opzione 2 manifest separato = fonte di verità duplicata; **rebuild REQ-032 IMPLICITO** via
`collection_name` namespaced per provider → cambio provider/dim = collezione diversa, ripopolata
incrementalmente); **DA-SS-5** manopola **`SERTOR_MEMORY_SEMANTIC`** (+ `_LIMIT` default 20), distinta da
`SERTOR_MEMORY`, gate a 2 strati (`memory_enabled AND memory_semantic_enabled` → factory `None`). **Trigger =
automatico a fine sessione** (`MemoryArchiveService.archive_all` riceve `MemorySemanticIndex | None`, embedda le
sessioni appena archiviate, **non-fatale** REQ-008); **modo separato, NESSUN fallback silenzioso** (`--semantic`
a leva spenta/indice assente → nuovo `SemanticMemoryUnavailableError` azionabile, exit 1, REQ-015).
**Privacy/on-machine:** provider da `SERTOR_EMBED_PROVIDER` esistente (REQ-018, default locale FEAT-011 →
index+query offline, RNF-1); cloud → invio off-machine (già scrubbed) reso **esplicito** (REQ-020). **Isolamento**
(REQ-017/SC-009): collezione memoria namespace dedicato ≠ corpus codice/doc. Componente concreto **senza nuova
porta** (single backend, come `MemoryArchive`/`EmbeddingCache` — YAGNI III); 2 eventi metrics-only
`memory_semantic_index`/`_search` (query **hashata**, gemelli di `episodic_search`/`embeddings`); degradazione
**non-fatale** ovunque (indice assente→vuoto+warning, provider giù→errore azionabile, riga invalida→skip,
REQ-021/022/023). **Consumatori (8 punti):** `settings`, `errors`, `services/memory_semantic.py` (nuovo),
`services/memory_archive.py`, `composition` (`build_memory_semantic_index` gated + iniezione), `cli/__main__`,
`cli/output`, test. **Debiti promossi (NON qui):** distribuzione installer manopole/asset = **FEAT-009**
(DA-SS-6); parità MCP = **FEAT-010** — entrambi nel backlog d'epica. `sertor-core` invariato fuori dai punti
elencati. Constitution **PASS 12/12 + missione PASS** (pre e post-design) senza deroghe — è la stella polare
(qualità del contesto reso all'agente nel tempo) servita riusando il motore di retrieval, non un secondo motore.
**Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per convenzione dal branch
(forma da `071`/`070`); nessun hook eseguito; MCP `sertor-rag` interrogato (nessun errore tool). Branch
`072-ricerca-semantica-memoria`. Storico:
`specs/070-search-combined-strutturato/plan.md` (FEAT-003 epica **retrieval-qualita** — **`search_combined` a
contratto strutturato (Tempo 2)**: il Tempo 1 (`069`) ha **misurato** che la superficie fusa **non funziona**
(fusion coverage **0.17**, 1/6) per il caso-firma requisito→implementazione; questa feature **ripara la causa**
(Principio XII). **Causa-radice (verificata):** `search_combined → _search(..., "both")`
(`services/retrieval.py:166`) fonde doc+code in **una lista ranked a budget condiviso**; score code/doc
**incommensurabili** → i documenti **annegano** il codice nello stesso top-k. **Decisione fissa:**
`search_combined` ritorna una **coppia strutturata** `FusedResults(docs, code)` (frozen dataclass di dominio,
nessun SDK), **ciascuna col proprio top-k** (budget separato — è il punto), nome invariato, + helper
`flatten()`; `search_code`/`search_docs` **INVARIATI**. **BREAKING CHANGE volontario** = deviazione
dall'additività (I/III) **giustificata** da Principio XII + gate **Allineamento alla missione** (la fusione
code+doc è la stella polare, oggi rotta); ammissibile perché pre-1.0 `git+url`, **tutti i consumatori di prima
parte e nel repo** (aggiornati in blocco). **4 forche decise:** **(DA-a)** `FusedResults(docs:
tuple[RetrievalResult,...], code: tuple[...])` frozen nel domain, `flatten()` metodo. **(DA-b)** budget
**separato**, stesso `k` per entrambe (da `Settings`), nessuna manopola nuova (YAGNI); riuso dei percorsi
mono-tipo `_search(..., "doc"/"code")`. **(DA-c)** `flatten()` = **interleave per rank** deterministico
(docs[0],code[0],…; avanzi in coda); score-merge **scartato** (è la causa-radice). **(DA-d)** MCP tool
`search_combined` → output **etichettato** `{"docs":[…],"code":[…]}` (meglio per l'agente); CLI `--type both` →
**due sezioni etichettate** docs/code (+ JSON `{"docs","code"}`); formato citabile `path#chunk` preservato.
**Fusion coverage adattata alle DUE liste:** `has_doc` dalla lista `docs`, `has_code` dalla lista `code`,
`covered = has_doc AND has_code` (concettualmente invariato, ora sul contratto giusto). **Superficie IR ranked
`search_combined` RIMOSSA** dal fused-runner (`_SURFACES` 3→2: `search_code`/`search_docs`): `evaluate` esige
una lista ranked unica che il combined non fornisce più — la fusion coverage **È** la misura della superficie
fusa (la metrica giusta; il ranking cross-tipo era la metrica sbagliata, Princ. XII). **Re-baseline (passo del
piano, non del design):** `[fused_baseline]` ri-registrata (2 superfici + `fusion_coverage` > 0.17 atteso) via
`--record-baseline`; `[baseline]` IR intatto (preserve-both). **9 consumatori di prima parte** aggiornati in
blocco: entità nuova, facade, fusion coverage, fused_runner, CLI esecuzione+resa+baseline, MCP, test.
**Confini:** NON toccare `search_code`/`search_docs`/le porte/gli engine (`evaluate` invariato);
fuori ambito qualità per-superficie `search_docs`, HyDE/contextual/metadata (FEAT-005/006/007), eval cloud
(FEAT-002). Local-first/deterministico, niente LLM nel run oltre l'embedder (RNF-3); misura via vehicle
`sertor-rag eval --fused` (Princ. XI). **Costo:** la coppia esegue 2 retrieval mono-tipo (~2× sulla query del
combined; atteso, prezzo del budget separato). Constitution **PASS 12/12 + missione PASS** (pre e post-design)
con **1 deviazione tracciata** (additività I/III) nel Complexity Tracking. **Nota di processo:**
`setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI → parametri per convenzione dal branch (forma da `069`);
nessun hook eseguito; MCP `sertor-rag` interrogato (nessun errore tool). Branch
`070-search-combined-strutturato`. Storico:
`specs/069-qualita-fusione-code-doc/plan.md` (FEAT-003 epica **retrieval-qualita** — **qualità del retrieval
fuso code+doc su query NL/architetturali**: rende **misurabile e migliorabile** il differenziatore di Sertor
(fusione code+doc) **prima** di introdurre tecniche, così ogni «migliore» è ancorato a un numero (Principio V,
stella polare). **Cardine:** estensione **ADDITIVA** dell'harness IR FEAT-001 (`evaluate`/`EvalReport`
**INVARIATI**) — NON un secondo oracolo come FEAT-011 (qui la misura è rank-based; la fusion coverage è un
passaggio puro sui `RetrievalResult.doc_type`, che esiste già). Tre novità: **(1)** campo additivo `intent ∈
{code,doc,both}` su `[[case]]` (decide superficie + tipi attesi; i casi `both` **SONO** la categoria fusione,
no campo `category` ridondante; tipi letti da `doc_type` a runtime, **nessuna doppia etichettatura**); **(2)**
misura **per-superficie** (`search_code`/`search_docs`/`search_combined`) via 3 adattatori `QueryableEngine`
sottili sul `RetrievalFacade`, riusando `evaluate`; combined = test d'integrazione; **(3)** **fusion coverage**
pura/additiva (`fusion.py`): caso `both` «coperto» SOLO se top-k ha ≥1 `DOC` pertinente E ≥1 `CODE` pertinente,
riportata **accanto** a hit@k/MRR (REQ-022: hit@k non nasconde la lacuna → `hit_but_not_covered` visibile). +
**baseline per-superficie** (sezione `[fused_baseline]` nello stesso `eval/baseline.toml`, preserve-both) +
**gate** (riuso `Baseline`+tolleranza). **5 forche decise (research):** **DA-a** ordine di **valutazione**
leve metadata→contextual→query-transform deciso dai numeri (finding: query-transform/HyDE rischia RNF-3 se
porta un LLM nel run → fuori dal run deterministico o solo documentazione); **DA-b** `intent` additivo +
≥8/superficie (≥6 fusione) + genesi via skill `eval-suite-author` estesa (P2); **DA-c** baseline per-superficie
+ tolleranza 0.0 + lift +0.05 (criterio di **adozione** leva, NON gate; target assoluto fusion coverage =
Could, dopo la baseline reale); **DA-d** FEAT-004 ortogonale (no `min_score` di default nel run),
FEAT-005/006/007 = **leve candidate** (le loro feature dedicate = il «come» se adottate); **DA-e** target =
miglioramento **single-shot misurabile** (la misura serve in ogni caso; pattern agentico documentato se i dati
lo indicano; non blocca lo scope). **Phasing (vincolante):** MUST = infrastruttura di misura (schema+metrica+
baseline+gate, tutto **MECCANICO**/deterministico); SOLO DOPO Should empirico = registrare baseline reali →
valutare ≥1 leva → adottare opt-in solo con lift (**GIUDIZIO**: genesi set + scelta leva, separati dal run,
confine D↔N). **Niente LLM nel run** oltre l'embedder (RNF-3, SC-004). Additivo a leve spente (costo/comport.
identici, RNF-1); `sertor-core` invariato fuori da `services/eval/` (+`fusion.py`/`fused_runner.py` nuovi,
estensioni `models/suite_io/regression/baseline_io`) + `composition` + `cli` + `settings`. **Nessuna nuova
porta** (riuso `QueryableEngine`/facade), **nessuna nuova dipendenza** (serializzatore a mano). Evento osserv.
`fused_eval` metrics-only (gemello `eval`/`graph_eval`/OTel 061). Manopola `SERTOR_EVAL_FUSION_K` nel template
`.env`; estensione skill = **debito P2**. Constitution **PASS 12/12 + missione PASS** (pre e post-design) senza
deroghe — è la **stella polare resa misurabile** (la fusion coverage verifica che requisito→implementazione
restituisca doc+codice insieme). **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI →
parametri per convenzione dal branch (forma da `066`); nessun hook eseguito; MCP `sertor-rag` interrogato
(nessun errore tool). Branch `069-qualita-fusione-code-doc`. Storico:
`specs/068-embedder-locale/plan.md` (FEAT-011 epica **sertor-core** — **embedder locale**: due provider di
embeddings **locali e deterministici** dietro la porta `EmbeddingProvider` esistente — **`glove`** (GloVe 6B
300d, PDDL, **nuovo default**, semantica NL locale) + **`hash`** (char-n-gram stdlib, dim 512, sign-hashing
`blake2b`, pavimento airgapped/CI) — e **semplificazione della config: `RAG_BACKEND` RIMOSSO** (decisione
utente). Unica superficie del provider = manopola dedicata **`SERTOR_EMBED_PROVIDER`** (`glove|hash|ollama|
azure`, default `glove`); lo store = **`SERTOR_STORE_BACKEND`** con **default proprio `local`** (non più
derivato). **NESSUNA** logica «se RAG_BACKEND=azure → azure»; `RAG_BACKEND` residuo in env → **warning
fail-loud** (REQ-007, Princ. XII) che nomina le manopole sostitutive, mai lettura silenziosa. **8 forche
decise:** **(DA-1)** `embed_provider` da property derivata→**campo** da `SERTOR_EMBED_PROVIDER`; `store_backend`
default indipendente `local`; `validate_backend` ri-chiavata su `embed_provider`/`store_backend` (locali →
`[]`, mai blocco). **(DA-2)** `hash` = char-n-gram n=3..5 → `blake2b(digest_size=8)` sign-hashing su dim
**512** → L2-norm, `name="hash:512"`, **solo stdlib**, deterministico cross-macchina/cross-Python (mai
`hash()` salted). **(DA-3)** `glove` = media vettori token in-vocab + L2-norm; OOV via split camel/snake;
tutto-OOV→vettore zero deterministico; `name="glove:300"`; **`numpy` lazy** (già transitiva da chromadb,
nessun nuovo extra). **(DA-4)** cache utente condivisa per-macchina XDG-style **stdlib** (`%LOCALAPPDATA%`/
`~/.cache/sertor/glove`, no `platformdirs`); `glove.6B.zip` Stanford NLP via `urllib`+`zipfile`, atomic
`os.replace`; override `SERTOR_GLOVE_PATH` → mai download; download **legato alla sola indicizzazione** (non
install/query). **(DA-5)** fail-loud: nuovo errore di dominio **`GloveUnavailableError`** azionabile che
nomina ENTRAMBE le vie d'uscita (`SERTOR_GLOVE_PATH`, `SERTOR_EMBED_PROVIDER=hash`); **mai** fallback
silenzioso; avviso `hash` «NL limitata» + avviso una-tantum download (~822 MB). **(DA-6)** osservabilità: 3
eventi **metrics-only** (`embeddings_provider_selected`/`glove_download`/`glove_cache_hit`, niente segreti/
path/query). **(DA-7/8)** wiring eval/CI via vehicle (`build_embedder`/composizione, Princ. XI), nessun
nuovo seam. **Additivo** (composition `build_embedder`→4 rami + nuovi adapter `adapters/embeddings/{hashing,
glove,glove_cache}.py` + Settings + 1 errore di dominio) **salvo la rimozione mirata di `RAG_BACKEND`**;
**porta/servizi/engine INVARIATI** (REQ-050), `build_store` invariato nel corpo, `collection_name` invariato
(il `name` stabile isola le collezioni, REQ-051). **Cambiamento trasversale enumerato nel plan** (~25 punti:
`settings.py` 6 punti, `composition.py`, ~10 file di test core, template `.env` installer, wizard
`configure`/`rag_profile`/`__main__`, doc utente). **Corollario installabile:** template `.env` (- `RAG_BACKEND`,
+ `SERTOR_EMBED_PROVIDER`/`# SERTOR_GLOVE_PATH`) + doc + nota di migrazione (rimozione + cambio default) =
Must (REQ-060/061); allineamento concetto installer `backend`→`provider` (`rag_profile`/`configure`) =
**debito di completamento P2** (gruppo G Should). **CI vera = FUORI AMBITO** (FEAT-003 epica debito-tecnico;
questa feature consegna il **determinismo offline** che la abilita). Constitution **PASS 12/12 + missione
PASS** (pre e post-design) senza deroghe; gate missione: abilita retrieval **semantico locale sul versante
doc** (profilo doc-only/doc-heavy, cuore della fusione code+doc) + sblocca adozione enterprise/gate eval in
CI + semplifica la config. **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` ASSENTI →
parametri per convenzione dal branch (forma da `066`); nessun hook eseguito; MCP `sertor-rag` interrogato
(nessun errore tool). Branch `068-embedder-locale`. Storico:
`specs/066-valutazione-navigazione-grafo/plan.md` (FEAT-011 epica **retrieval-qualita** — **valutazione
della navigazione del grafo (set-based)**: rende **misurabile** la potenza relazionale del code-graph,
estendendo l'harness IR di FEAT-001 con un **secondo oracolo a insiemi** per i casi relazionali, **senza**
toccare casi/metriche path-based. Un caso = **relazione + simbolo target + insieme atteso di `ref`**
(`[[graph_case]]` nello **stesso** `eval/suite.toml`, accanto ai `[[case]]` IR); run deterministico via
vehicle **`sertor-rag graph-eval run`** → `precision`/`recall`/`F1` per **insiemi** (NIENTE rank/@k) con
dettaglio `expected`/`got`/`missing`/`extra`; gate di non-regressione sul **F1 medio** con **baseline
SEPARATA** (`eval/graph_baseline.toml`, `SERTOR_GRAPH_EVAL_TOLERANCE` default 0.0; recall/precision medi
**secondari** nel report); gate **match-esatto** opzionale (`--exact`/`SERTOR_GRAPH_EVAL_EXACT`); seam per
genesi assistita (skill `eval-suite-author` estesa). **4 forche di design decise:** **(DA-a)** gate su
`mean_f1` + baseline su file separato (riusa il *meccanismo* di tolleranza IR, file/manopola distinti);
**(DA-b)** `related_docs` (unità=documento) **fuori MVP** (Could) — schema `expected` agnostico al tipo
(tupla di stringhe) → non preclude i documenti; **(DA-c)** distinte NETTAMENTE **baseline** (pavimento
metrico, `--record-baseline`, deterministico) e **snapshot** (insiemi attesi = `[[graph_case]].expected`,
ri-autorato via skill/`amend-case` = giudizio): `--record-baseline` **non tocca mai** gli `expected`;
**(DA-d)** confermato `[[graph_case]]` nello stesso file (writer ri-architettato per **preservare entrambe**
le sezioni). **Ancoraggio (verificato MCP):** navigazione riusa la porta `CodeGraph`
(`who_calls`→chiamanti, `defines`→`find_symbol` definizioni — **non esiste** `defines` nella porta) via
`build_graph_service` (factory esistente); identità nodo = `SymbolHit.ref` (`path#qualname`); oracolo
set-based = **modulo NUOVO** `services/eval/graph_eval.py` parallelo a `evaluate` (NON dentro
`RoutedEvalEngine`, NON dentro `evaluate` rank-based); entità additive in `models.py`
(`GraphCase`/`SetMetric`/`GraphEvalReport`/`GraphBaseline`/`GraphRegressionVerdict`/`RefValidation`;
`EvalSuite + graph_cases` default `()`); `suite_io` esteso (legge/serializza `[[graph_case]]` preservando i
`[[case]]`); `graph_baseline_io`/`graph_regression`/`graph_runner` nuovi; gruppo CLI `graph-eval`
(run/add-case/amend-case/validate-ref). **Nodi:** evento osservabilità `graph_eval` **metrics-only**
(`cases`/`relations` a cardinalità chiusa/medie/regressed/tolerance — mai nomi/path/insiemi, gemello
`eval`/OTel 061); manopole `SERTOR_GRAPH_EVAL_*` nei template `.env` dell'installer; estensione skill =
**debito di completamento P2** (gruppo E/Should). **Additivo a leve spente** (costo/comportamento identici,
RNF-1); `sertor-core` invariato fuori da `services/eval/`+`composition`+`cli`+`settings`+`errors`. Nessuna
nuova **porta** (riuso `CodeGraph`), nessuna nuova **dipendenza** (serializzatore a mano). Constitution
**PASS 11/11** (pre e post-design) senza deroghe. **Nota di processo:** `setup-plan.ps1`/`speckit-plan/
SKILL.md` ASSENTI → parametri per convenzione dal branch (forma da `065`), nessun hook eseguito; MCP
`sertor-rag` interrogato (nessun errore tool). Branch `066-valutazione-navigazione-grafo`. Storico:
`specs/065-ground-truth-valutazione/plan.md` (FEAT-001 epica **retrieval-qualita** — **ground-truth &
valutazione della pertinenza**: promuove l'harness di valutazione da *fixture di test* a **capacità
host-side**: una **suite-dato versionata** del progetto (`eval/suite.toml`, **TOML**), un **run
deterministico via vehicle** (`sertor-rag eval run` → `hit-rate@k`/`MRR`, report umano + `--json` con
dettaglio per-query hit/miss), un **gate di non-regressione** (`eval/baseline.toml` + tolleranza
`SERTOR_EVAL_TOLERANCE`, exit non-zero sotto baseline oltre tolleranza), confronto **2 config locali**
(`--compare baseline,hybrid`, `evaluate` 2×), e i **seam** per genesi assistita (FEAT-008, skill) e
feedback (FEAT-009, skill) **senza** che il run dipenda mai da un LLM. **5 forche decise dall'utente,
progettate:** **(a)** formato **TOML** — `tomllib` è read-only → **serializzatore minimale a mano** per
lo schema piatto `[[case]]` (`tomli-w` scartato/rivalutabile, round-trip validato → `SuiteWriteError`
fail-safe); **(b)** non-regressione = **baseline-su-file versionato + tolleranza** (pavimento assoluto
rinviato Could); **(c)** genesi assistita = **skill NUOVA che riusa il PATTERN** (non il codice) di
`derive-entity-types` — l'agente legge il corpus via RAG/MCP e **propone**, l'utente approva; **(d)**
superficie = sottocomando **`sertor-rag eval`** (run/non-regressione/`add-case` deterministici) + skill
per genesi/feedback (confine D↔N netto); **(e)** validazione `expected_path` **write-time** contro
`IndexManifest.load(collection).files` esposto da `build_indexed_docs` (il CLI **è** il vehicle, Princ.
XI). **Ancoraggio (promozione):** riusa `evaluate`/`EvalReport`/`QueryableEngine`
(`engines/evaluation.py`) **estesi additivi non-breaking** (solo `EvalReport.per_query` + `QueryOutcome`
nuovi; `kind` resta metadato dell'artefatto/report, la firma `GroundTruth=(query,expected)` invariata);
servizio nuovo `services/eval/` (suite_io/baseline_io/regression/runner); fixture
`tests/fixtures/ground_truth.py` **migrato** a `eval/suite.toml` come esempio dogfood (non spedito agli
ospiti). **Nodi:** suite/baseline in **`eval/` versionato** (NON `.sertor/` gitignored — è dato del
progetto, non output, REQ-006); evento osservabilità `eval` **metrics-only** (no query/path, gemello
OTel 061); manopole `SERTOR_EVAL_DIR`/`_TOLERANCE` nei template `.env` dell'installer (skill P2 tracciate
come **debito di completamento** della capacità). **Additivo a leve spente** (costo/comportamento
identici, SC-009); `sertor-core` invariato fuori da `evaluation.py`+`services/eval/`+`composition`+`cli`.
Constitution **PASS 11/11** (pre e post-design) senza deroghe. **Nota di processo:** `setup-plan.ps1`/
`speckit-plan/SKILL.md` ASSENTI → parametri per convenzione dal branch, nessun hook eseguito; MCP
`sertor-rag` interrogato (nessun errore tool). Branch `065-ground-truth-valutazione`. Storico:
`specs/064-visibilita-rag-tui/plan.md` (FEAT-015 epica **osservabilità** — **visibilità del RAG nella
TUI / dimostrabilità**: nuovo opt-in **`SERTOR_OBSERVABILITY_CONTENT`** (default off, richiede lo store)
che realizza l'**opt-in raw-text REQ-E9** per **uso LOCALE** (scopo: *vedere/dimostrare* come funziona il
RAG, NON audit; decisione utente: dati locali, TUI-user ≡ LLM-user → niente da nascondere localmente).
**Cattura:** quando on, gli eventi di retrieval (`retrieve` facade + `hybrid_query` engine) portano
`query`+`results_preview`(top-k path|score)+`snippet`(top-1) **tutti scrubbati** via `scrub_text`, +
`abstained` (sempre, bool). Helper puro condiviso `content_fields()` in `services/retrieval.py` (riusato
da facade e ibrido); flag cablato dal composition (`build_facade`, `content_enabled =
observability_content_enabled AND observability_enabled`); l'ibrido legge `self._settings`. **Vista:**
nuova **scheda TUI "RAG"** (`render_rag_report` puro in `observability/live.py` + `TabPane` in `tui.py`)
con verdetto **3 stati hit/miss/astenuto** (`retrieval_verdict`, da `results`/`fused_k`+`abstained`) ·
query · top result+snippet · operazioni MCP. **Privacy:** default off ovunque (REQ-012); contenuto solo
opt-in+scrubbato; l'**export OTel resta metrics-only** (l'handler scarta query/snippet — testo libero).
**SpecKit:** requirements (6 forche risolte: hit/miss=3 stati · risultato=top-k path+score+snippet 1° ·
gate=manopola dedicata · scheda dedicata · MCP query-arg · retention by-count) + plan (Constitution
11/11). Additivo; `sertor-core` invariato fuori dai punti citati. **Verificato live** (evento porta
query/preview/snippet 200ch/abstained, verdetto=hit); 594 unit verdi, ruff clean. **Follow-up:** MCP
query-arg negli eventi `mcp.<tool>` (REQ-006, render già pronto); correlazione hard MCP↔retrieval;
retention store. Branch `064-visibilita-rag-tui`. Storico:
`specs/061-export-otel/plan.md` (FEAT-005 epica **osservabilità** — **export OpenTelemetry**: gli eventi
che il core già emette via `log_event` sono esportati **anche** verso un backend OTel esterno
(Langfuse/Phoenix/Grafana), **in aggiunta** allo store locale F1 (REQ-E4). **Design = gemello di F1:** un
secondo `logging.Handler` (`OtelExportHandler`, `observability/otel.py`) attaccato in
`enable_observability` SOLO con extra `[otel]` + manopola `SERTOR_OBSERVABILITY_OTEL` (default off);
mappa ogni event-record a uno **span** — attributi **GenAI semconv** dove applicabile
(`embeddings`→`gen_ai.operation.name=embeddings`+`gen_ai.usage.input_tokens`+`gen_ai.provider.name`;
search→`retrieval`), namespace `sertor.*` altrove (index/rerank). **Additivo** (`log_event`/call-site/F1
invariati), **non-fatale** (handleError), **non-bloccante** (BatchSpanProcessor), **privacy
metrics-only** (mai testo libero/query/path; campi già redatti). Extra OTel **lazy** (core importabile
senza OTel — verificato: 0 `opentelemetry` in sys.modules; assente+richiesto → `ConfigError` come
`[tui]`). Endpoint/trasporto dalle env **standard OTel** (`OTEL_EXPORTER_OTLP_*`), non reinventati. Mappa
attributi centralizzata (R-1). **Verifica offline** con `InMemorySpanExporter` (8 test: mapping puro,
emissione e2e, privacy, disabilitato→0 handler, extra-assente→ConfigError). Manopola nei template `.env`
dell'installer (corollario installabile). **Gap dichiarato:** span **flat post-hoc** (no tracing
nidificato → follow-up). ruff clean; 580 unit / 627 root non-cloud / sertor 292 · kit 131 · flow 134
verdi; `sertor-core` invariato salvo modulo nuovo + manopola + ramo wiring + extra. Branch
`061-export-otel`. **NB:** 2 test `test_packaging` falliscono in locale finché il branch non è pushato
(installano da `git+url@<branch>`) — artefatto, non regressione. Storico:
`specs/058-distribuzione-costituzione/plan.md` (FEAT-009 epica **debito-tecnico** — **distribuzione
corretta della costituzione neutra (replace-if-placeholder) + rifinitura principi**: la
costituzione-starter di `sertor-flow` **non arrivava** sull'ospite — `specify init` (Step 0, pivot
FEAT-045) scaffolda un `.specify/memory/constitution.md` **PLACEHOLDER** (`[PROJECT_NAME]`), poi il nostro
CONFIG `create-if-absent` (`_apply_config`) faceva **SKIP** → l'ospite riceveva il template vuoto di
spec-kit, non lo starter curato (bug scoperto con **verifica empirica** su Spike + install pulito, mentre
si esaminava quali principi della costituzione sono agnostici). **Fix:** helper puro
`_is_speckit_placeholder` (sentinelle `[PROJECT_NAME]`/`[PRINCIPLE_1_NAME]`/`[CONSTITUTION_VERSION]`) +
`_apply_constitution(dest, starter, dry_run)` **condiviso** da install (`_apply_config`) e upgrade
(`_apply_gov_upgrade`): placeholder → **sovrascrivi** con lo starter (UPDATED); costituzione **reale** →
**preserva** (SKIPPED, Principio VI); idempotente; uninstall invariato. Mock `FakeSpecifyRunner` (conftest)
reso **FEDELE** (ora deposita il placeholder create-if-absent) — era il blind-spot che nascondeva il bug
ai test offline. **Rifinitura starter:** + «Replaceable Details / No Vendor Lock-In» (kernel Principio II)
+ «Consume Through Stable Interfaces, Not Internals» (gen. Principio XI) + allineamento leggibilità SESE;
v0.1.0→0.2.0; esclusi i principi Sertor/RAG-specifici (X, veicoli, motori, hit@k). `sertor-core`
**INVARIATO**; `sertor-flow` senza dipendenza dal core. SpecKit completo (requirements→spec→plan
Constitution Check 11/11→tasks→implement); ruff clean, **sertor-flow 132 · kit 131 · sertor 292**; empirica
end-to-end placeholder→starter. Branch `058-distribuzione-costituzione`. Storico:
`specs/056-parita-asset-copilot/plan.md` (FEAT-001 epica **debito-tecnico** — **parità funzionale
completa su Copilot CLI + governance dual-target**: dal dogfooding su host Copilot reale la capacità wiki
era **ROTTA** — il payload multi-file della skill `wiki-author` (`wiki-playbook.md` + 9 `ops/` + 3 craft)
non veniva depositato dall'installer Copilot, e i body citavano `.claude/` path, comandi `/wiki`,
`CLAUDE.md` e nomi-modello Claude (Opus/Haiku) inesistenti su Copilot. **6 decisioni:** **D1**
**neutralizzare la sorgente** (body host-agnostici **byte-identici** Claude↔Copilot, **riferimento-per-nome**
al payload; NON tradurre per-target); **D2** payload in **container dedicato `.github/sertor/wiki-author/`**
(non-agente, fuori da `.github/agents/` per evitare agent-discovery; Claude invariato in `.claude/skills/`);
**D3** **riuso `iter_asset_dir`+byte-copy** in `_build_copilot_wiki_plan`, niente nuovi `Surface`/`ArtifactKind`,
`sertor_owned_paths` Copilot aggiornato (owned_dir → uninstall/upgrade in blocco); **D4** nuova **guardia di
parità offline** `test_assets_copilot_parity.py` (0 `.claude/` · 0 slash-command · 0 nomi-prodotto Claude +
**closure dei riferimenti** — ogni file citato da un body è depositato, il check che avrebbe preso il bug;
closure anche sul piano Claude); **D5** **governance dual-target** (sezione "Host-agnostic authoring" nel
playbook + voce DoD nel `claude-md-block` + sezione "Parità by construction" in `wiki/tech/assistant-targeting.md`);
**D6** **full sweep** wiki+governance(`requirements`)+rag. Nomi-modello neutralizzati preservando il tier
(Opus→main flow, Haiku→background curator); footer commit host-agnostico. **Verifica empirica** su host
puliti Claude+Copilot: payload depositato, **0 leak** di ogni classe nei resi Copilot, closure ok (l'agent
cita il playbook per nome → esiste), **R4** nessun agente-fantasma da `.github/sertor/`; ha SCOPERTO 2 classi
non coperte offline (`/wiki` nel messaggio runtime dell'hook, nomi-modello Claude), poi codificate nella
guardia. `sertor-core` **INVARIATO**; `sertor-flow` senza dipendenza dal core. SpecKit completo
specify→implement (spec `b38a1af`, impl `b6e85b7`). Constitution **PASS 11/11** senza deroghe. **Resta:**
prova live agente wiki su Copilot CLI reale (Spike, SC-008) + merge. Branch `056-parita-asset-copilot`. Storico:
`specs/052-copilot-cli-only/plan.md` (FEAT-012 epica **sertor-cli** — **consolidamento Copilot
CLI-only**: un solo target Copilot esposto, **`copilot-cli`** (la CLI); il valore `copilot` (VS Code)
non è più raggiungibile da alcun flag `--assistant`. Refactor **sottrattivo** confinato ai 3 pacchetti
installer (`sertor`/`sertor-flow`/`sertor-install-kit`); `sertor-core` **invariato** (NFR-03). 5 nodi di
*come* risolti: **(1)** rimozione TOTALE `AssistantId.COPILOT` (Q1=a) a 3 cerchi — enum value
(`assistant.py:25`), ramo `for_assistant(COPILOT)` (156-176), semplificazione consumatori `is_copilot →
is COPILOT_CLI`; l'errore nominante su `copilot` **cade dal `from_str` esistente** (Principio IV già
cablato, no logica nuova); `CommandVehicle.PROMPT_FILE`/`render_prompt_file` **restano** primitive del
kit (default+Claude, non VS-Code-specifici) ma nessun plan li richiama più. **(2)** mapping upstream =
nuova mappa `_SPECKIT_AI_FLAG = {claude:claude, copilot-cli:copilot}` in `speckit_launch.py`
(unico punto documentato, FR-015), usata in `build_specify_command`; `_EXPECTED_LAYOUT` **rinominato**
chiave `copilot → copilot-cli` mantenendo i marker che spec-kit produce per Copilot
(`.github/prompts/speckit.specify.prompt.md`) → idempotenza preservata (R-04/SC-007). **(3)** skill
`requirements` su CLI = **nessun ramo nuovo**: il profilo `copilot-cli` (FEAT-011,
`command_vehicle=CUSTOM_AGENT`) già risolve COMMAND→`.github/agents/*.agent.md`; azione concreta = solo
esporre `copilot-cli` in `sertor-flow` (`choices`) + copertura test (anti-drift via `render_custom_agent`
già garantito). **(4)** test = **tabella superficie→test** (research §Nodo 4): rimozione sottrattiva dei
rami VS Code + completamento casi unici su `copilot-cli`, **nessuna superficie scoperta** (SC-008), tutto
offline (`Fake*Runner`, NFR-05); `test_install_rag_copilot.py` eliminato (coperto da
`*_copilot_cli.py`), `test_assistant.py` aggiunge `from_str("copilot")→ConfigError`. **(5)** nota di
migrazione **inline in `docs/install-copilot.md`** (un solo percorso `copilot-cli`, cleanup manuale degli
artefatti VS Code residui — Q3=a), allineamento `docs/install.md` + `packages/sertor/docs/install.md` a
`claude|copilot-cli` (FR-020/021). Naming unificato `claude|copilot-cli` su entrambi i pacchetti e tutti
i verbi (FR-005/006/007); `sertor` valida via `from_str` (exit 1), `sertor-flow` via argparse `choices`
(exit 2). Breaking change voluta e dichiarata (Q4=a, niente alias). **Data-model = restrizione del seam**
(nessuna entità nuova): `AssistantId={CLAUDE,COPILOT_CLI}`, `for_assistant` a 2 rami. **Nota di processo:**
`.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** → parametri per
convenzione dal branch, nessun hook eseguito; MCP `sertor-rag` non interrogato (lavoro su codice locale).
Constitution **PASS 11/11** (pre e post-design) senza deroghe. Branch `052-copilot-cli-only`. Storico:
`specs/051-configurazione-wizard/plan.md` (FEAT-003 epica **sertor-cli** — wizard di configurazione
`sertor configure [rag]` nell'installer `sertor`: porta `.sertor/.env` da «segreti vuoti» a «pronto»
con un percorso guidato **ibrido CI-safe** (Q1 a: prompt con TTY, flag-driven senza TTY, **mai**
bloccante), comando **separato ri-eseguibile** (Q2 a). I campi richiesti derivano dalla **fonte unica**
`Settings.validate_backend()` (NFR-04) per il **solo** insieme che il core onora (Q4 a: embedding
Azure/Ollama; store Chroma/Azure Search) — un **catalogo `ConfigField`** di sola presentazione
(descrizione + flag-segreto + default) mappa i nomi che il validatore emette, con **test di copertura**
catalogo↔`validate_backend` (no drift). Risoluzione per campo: `--set KEY=VAL`/scorciatoie
`--backend`/`--store` → valore in `.env`/ambiente → prompt **solo** se `isatty()` su stdin+stdout e
`¬--non-interactive`; campo mancante senza TTY → `ConfigError` che lo **nomina**, **exit 1**, nessuna
scrittura parziale (FR-005). Prompt segreti via `getpass`; mascheramento centralizzato in `mask_secret`
(unico punto, anti-leak con test). Scrittura = **riuso** `merge_env` (additivo non distruttivo) +
`_replace_key_line` (overwrite solo su conferma/`--overwrite`); scaffold dal template `env.{backend}.tmpl`
se `.sertor/.env` assente (FR-015, no `uv`/indice); idempotente by construction. Validazione **statica**
di default (`validate_backend`, offline); **probe live opt-in `--check`** (Q3 a) eseguito **via il
vehicle `sertor-rag` in subprocess (Principio XI)**, MAI importando `build_embedder` — degrado onesto se
il sottocomando-probe non esiste. **Dipendenza di core promossa a backlog:** `sertor-rag` non ha oggi un
comando di probe → nuova FEAT `sertor-core` (gemella del self-test MCP) da creare prima che US5/`--check`
conti come done; il **P1 (US1/2/3) è completo con la sola validazione statica**. Report `ConfigureReport`
puro (umano + `--json`, zero segreti); exit 0 completa&valida / 1 incompleta o probe fallito / 2 usage.
Additivo: `install`/`upgrade`/`uninstall` invariati; nessuna modifica al runtime del core. Constitution
**PASS 11/11** (pre e post-design) senza deroghe. Branch `051-configurazione-wizard`. **Nota di processo:**
`.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` ASSENTI nel repo →
parametri ricavati per convenzione dal branch; nessun hook eseguito. Storico:
`specs/049-compatibilita-copilot/plan.md` (FEAT-011 epica **sertor-cli** — **hardening compatibilità
GitHub Copilot** dell'installer: corregge FEAT-007 (PR #64) e FEAT-009 (PR #65) dopo un audit di dogfooding
(Copilot CLI 1.0.63) che ha dimostrato che la "parità piena" Copilot è **falsa** su più superfici —
l'installer depositava artefatti in **formato Claude** non conformi allo schema Copilot. **Principio guida
vincolante:** supporto **NATIVO** per ogni tool, **niente hack** (no JSON con campi-di-entrambi, no formato
Claude tollerato, no veicolo sbagliato); il **riuso** è del CONTENUTO (corpo istruzionale + corpo logico
`.ps1`, fonte unica byte-for-byte), il CONTENITORE/contratto è **tradotto nativamente**. FR-014 di FEAT-007
**rilassato**: corpo `.ps1` condiviso, output nativo per assistente via `-Assistant`. **5 difetti chiusi:**
(A) hook JSON nativi (`{"version":1,"hooks":{<evento>:[entry PIATTA]}}`, `timeoutSec`, niente
`shell`/`statusMessage`/`timeout`) — senza `version:1` il file era scartato → 0 hook eseguiti; (B) output
`.ps1` **per-evento** (`agentStop`→`{decision:"allow",reason}` non-bloccante Q3=b; `preToolUse` **fail-open**
exit 0 sempre, NFR-3, è il rischio più grave perché Copilot è fail-closed; `sessionEnd`→nessun stdout
consumato, msg su stderr; **mai dual-field**); (C) SessionStart nativo (CLI `type:"prompt"` Q1=b; VS Code
`type:"command"`→`{additionalContext}`); (D) veicolo comandi **per-target** Q2=c (VS Code prompt-file +
CLI **custom-agent**, perché i prompt-file NON esistono su Copilot CLI); (E) frontmatter (`agent:` non
`mode:`; **omesso** `model:` Claude Q6=a; persona+corpo byte-for-byte). **2 nodi di design risolti:**
(1) SessionStart VS Code = `{additionalContext}` via hook `command`, con **[ASSUNTO-VSC] dichiarato** (non
verificato sul campo) + fallback nativo (direttiva statica nel blocco istruzioni) + gap dichiarato finché
non confermato; (2) seam **esteso in modo mirato** (NON revisione profonda — YAGNI): `AssistantProfile`
copilot-cli → veicolo COMMAND custom-agent; `render_prompt_file` (`agent:`); `render_custom_agent`
(no `model`); nuova `render_copilot_hooks(events)` + `HookEntrySpec` (fonte unica del wiring, gli asset
statici `copilot/hooks/*.json` in formato Claude sono SOSTITUITI dal generato); `settings_merge` dedup
**schema-aware** (riconosce forma piatta Copilot + annidata Claude, retrocompatibile). **Gruppo G:** suite
di **validità-schema OFFLINE** (FR-021..026, NFR-5) che avrebbe preso tutti i bug dell'audit (verifica
struttura, non solo presenza); reintroducendo un difetto → almeno un test fallisce (SC-007). **Gruppo H:**
onestà claim — nessuna parità non-verificata, gap espliciti nell'output d'installazione e surface-mapping
(FR-027/028); MCP CLI (FR-020/Q5) = solo documentare l'evidenza (PR #66 vs doc `~/.copilot/mcp-config.json`),
correggere solo se smentita. Vive nei pacchetti installer (`sertor-install-kit` stdlib-only + `sertor` +
`sertor-flow`); le correzioni si propagano a `sertor-flow` riusando il renderer del kit **senza** dipendenza
da `sertor-core`/`sertor` (FR-042/SC-011). `sertor-core` **invariato** (NFR-3). Invarianti: install≠run,
non-distruttività, idempotenza, **non-regressione `claude`** (gate duro, default `-Assistant claude`,
SC-010). Constitution **PASS 11/11** (pre e post-design) senza deroghe. Branch `049-compatibilita-copilot`.
Storico:
`specs/048-lifecycle-installer/plan.md` (FEAT-008 epica **sertor-cli** — **ciclo di vita** dell'installer:
i due verbi mancanti `upgrade`/`uninstall` (oggi solo procedura manuale `docs/install.md §10.1/§10.2`).
4 decisioni di prodotto chiuse: **Q1 (a)** wiki protetto (`--purge-wiki`+`--yes`); **Q2 (a)** obsoleti via
**diff a posteriori** contro lista statica di path Sertor-owned, **NO manifest**; **Q3 (c)** `sertor
uninstall` tutto-in-uno **e** per-capacità; **Q4 (a)** `sertor-flow upgrade`/`uninstall` **in ambito**
(simmetria piena). 4 ambiguità di *come* risolte nel plan: **D1** niente `ArtifactKind`/`WriteStrategy`
inversi → **verbo ortogonale** `LifecycleOp`{INSTALL/UPGRADE/UNINSTALL} + 2 `Outcome`{UPDATED/REMOVED} +
**funzioni inverse pure nel kit** (`remove_marker_block`/`update_marker_block`/`remove_settings_entries`/
`remove_gitignore_lines`/`remove_mcp_server`/`deregister_mcp_client`/`update_file_if_changed`/`remove_path`),
duali 1:1 delle additive esistenti; **D2** i plan di upgrade/uninstall **riusano lo stesso plan-builder
d'install** (UNICA fonte di verità) percorso col verbo, dispatch `apply(art, op)`; **D3** dichiarazione
path Sertor-owned = funzione pura `sertor_owned_paths(cap, assistant)` co-localizzata + **test di
copertura** (`plan ⊆ owned`) al posto del manifest; **D4** `--purge-wiki` deterministico/CI-safe (no TTY
+ no `--yes` → NON cancella, avviso; `--purge-wiki --dry-run` = usage error exit 2). Primitive **una volta
nel `sertor-install-kit`** (stdlib-only, FR-053/SC-010), consumate da `sertor`+`sertor-flow` (invariante:
`sertor-flow` NON dipende da `sertor-core`/`sertor`). `.sertor/` (tipo A) rimosso in blocco; file
condivisi (tipo C) byte-per-byte salvo porzione Sertor; MCP (tipo D) de-registrazione o solo-voce.
`install.report/1` **esteso** (no 2° schema). NESSUNA modifica a `sertor-core` (porte/adapter/composition
INVARIATI). Constitution **PASS 11/11** (pre e post-design) senza deroghe. Branch
`048-lifecycle-installer`. Storico:
`specs/047-packaging-distribuibile/plan.md` (FEAT-001 epica **sertor-cli** — packaging **distribuibile**
via distribuzione interim **`git+url`** (NO PyPI, FEAT-006). Chiude 3 lacune sui 4 pacchetti del `uv
workspace` (`sertor-core`+`sertor`+`sertor-install-kit`+`sertor-flow`, tutti hatchling): (1) **licenza** —
file `LICENSE` MIT in radice + ogni package, incluso nelle wheel, coerente coi metadati; (2)
**versione+metadati** — **versione unica** da un file `/VERSION` letto dinamicamente dai 4 pyproject via
`[tool.hatch.version]` (`dynamic=["version"]`; scartati bump2version/hatch-vcs/script-sync = YAGNI), +
metadati completi (`urls`/`classifiers`/`keywords`) per i 2 **user-facing** (`sertor`,`sertor-flow`); (3)
**verifica ripetibile** — suite pytest `@integration` `tests/integration/test_packaging.py`, 3 stage a
costo crescente: statico (licenza/metadati/versione, offline) → build `uv build` sdist+wheel (LICENSE in
wheel, `assets/**` di sertor, entry-points) → install pulito in **venv effimero** per `uv`/`uvx` (**gate**
hard) e `pip` (**soft `xfail`**, limite workspace documentato → **FEAT-010**). Verifica = **stdlib**
(`tomllib`/`zipfile`/`email.parser`/`configparser`) + **subprocess** (`uv`/`pip`/`git`), **NO import di
`sertor_core`** (Princ. XI). Due insiemi (DA-P3/P4): build-validati = tutti 4; user-facing = `sertor`/
`sertor-flow` (gli interni `sertor-core`/`sertor-install-kit` esonerati dai metadati). Decisioni onorate
DA-P1..P4. Confini: NO pubblicazione PyPI/firma/SBOM (FEAT-006), NO versioning-da-tag, NO ergonomia
avanzata pip/installer (FEAT-010). Nessuna modifica al runtime del core (porte/adapter/composition
INVARIATI, NFR-3). Constitution **PASS 11/11** (pre e post-design) senza deroghe. Branch
`047-packaging-distribuibile`. Storico:
`specs/046-refresh-incrementale/plan.md` (FEAT-009 epica **sertor-core** — refresh **incrementale**
dell'indice RAG. Oggi `index(rebuild)` ricostruisce FULL i 5 stadi (discover/chunk/embed/reset+upsert/
BM25+code-graph); solo l'embed è incrementale via cache FEAT-019 → su ospiti grandi = minuti. Introduce un
**manifest SQLite** namespaced `(corpus,provider)` (`<index_dir>/index_manifest.sqlite`, gitignored) che
persiste per file `mtime+content_hash+logic_version` **e le unità derivate (Document+Chunk)**. Run
**incrementale di DEFAULT** (decisione utente F2): classifica UNCHANGED/NEW/MODIFIED/DELETED (mtime
pre-filtro + hash conferma), riprocessa solo i cambiati, **upsert/delete MIRATI** sul `VectorStore`
(`delete(collection,ids)` **già esistente**, nessuna porta estesa), **ricostruisce BM25+code-graph DAL
MANIFEST** (decisione utente F1: mirror `build()`, niente re-chunk/re-read degli invariati). Safeguard
Must: equivalenza col full (FR-012), **fallback automatico al full** su manifest assente/incompatibile
(FR-011), invalidazione su cambio-logica `logic_version` (FR-013), conteggi delta osservabili added/
updated/removed/unchanged/cache_hits (FR-015). `--full` resta il reset sicuro. Da clarify: full di
**riconciliazione** OFF-default (`SERTOR_INDEX_RECONCILE_EVERY=0`, FR-019; il segnale di drift →
osservabilità **FEAT-012**) + **guardia single-writer** (`IndexLockedError`, FR-020; concorrenza avanzata →
epica multiutente). Manifest = store **concreto senza nuova porta** (come EmbeddingCache/MemoryArchive).
Granularità a file (embed-cache copre il chunk-level). Constitution **PASS 11/11** senza deroghe. Branch
`046-refresh-incrementale`. Storico:
`specs/045-distribuzione-copilot-flow/plan.md` (FEAT-009 epica sertor-cli — distribuzione della
**governance/SDLC** del pacchetto `sertor-flow` su **GitHub Copilot** con parità funzionale, gemella di
FEAT-007. Due leve: (1) **pivot vendoring→launch-installer** (decisione utente): `sertor-flow` smette di
vendorare SpecKit e **lancia `specify init --ai <assistant>`** via il `CommandRunner` del kit, a versione
pinnata, fail-fast se assente — refactor del path **anche per Claude** (non-regressione FR-012),
deroga giustificata al Principio II (fetch install-time, governance≠RAG); (2) **superfici
Sertor-authored** (`requirements-analyst`/`configuration-manager`/skill `requirements`/blocco SDLC)
**tradotte** per Copilot riusando il **renderer SPOSTATO nel `sertor-install-kit`** (condiviso
`sertor`↔`sertor-flow`, anti-drift). Riusa il seam `AssistantProfile` di FEAT-007. Invariante dura:
**nessuna dipendenza di `sertor-flow` da `sertor-core`** (FR-016). Constitution PASS 11/11 (1 deroga
tracciata II). Branch `045-distribuzione-copilot-flow`. Storico:
`specs/044-distribuzione-copilot/plan.md` (FEAT-007 epica sertor-cli — distribuzione delle superfici del
pacchetto `sertor` (server MCP `sertor-rag` + sistema-wiki) su **GitHub Copilot** con **parità funzionale
piena**, via un **assistente target** nell'installer. Estende il Principio X all'assistente ospite.
Decisione di design DA-2 = **IBRIDO: riuso del CONTENUTO + traduzione del CONTENITORE**, da fonte unica:
un `AssistantProfile` nel `sertor-install-kit` mappa ogni Surface logica (INSTRUCTION_BLOCK/MCP_SERVER/
COMMAND/AGENT/HOOK) → contenitore per-assistente (Claude `.claude/**`,`.mcp.json`,`CLAUDE.md` · Copilot
`.github/**`,`.vscode/mcp.json`,`.github/copilot-instructions.md`); i plan-builder diventano parametrici.
Riuso massimo delle `ArtifactKind` esistenti (MARKER_BLOCK su copilot-instructions; SETTINGS_MERGE su
`.github/hooks/*.json`; MCP_MERGE root-key parametrico `mcpServers`↔`servers`); gli script hook
(`.ps1`/`.sh`) sono riusati identici. Targeting nel kit per riuso da `sertor-flow`/FEAT-009. CLI
`--assistant claude|copilot` (default `claude`). Grounding: Copilot ha hook (stessi 8 eventi),
custom-agent, prompt-file, MCP `.vscode/mcp.json`. Invarianti: install≠run, non distruttivo, idempotente,
CLI assistant-agnostic, segreti non versionati, gap dichiarati. Ambito SOLO pacchetto `sertor`; governance
SpecKit (`sertor-flow`) = feature gemella FEAT-009 (con pivot vendoring→launch-installer). Constitution
PASS 11/11 (pre-design). Branch `044-distribuzione-copilot`. Storico:
`specs/043-plan-template-neutro/plan.md` (gruppo D dell'enforcement Principio XI — neutralizza il
plan-template spedito agli ospiti: il bundle `sertor-flow` ora vendora il plan-template GENERICO upstream
(gate derivati dalla costituzione DELL'OSPITE, placeholder `[Gates determined based on constitution
file]`) invece di quello gated di Sertor; escluso dal sync/anti-drift col dogfood (intenzionalmente
divergente, come gli script F3). Il dogfood di Sertor mantiene il suo template gated. Kit `sync_subtree`
+= param `exclude`. Constitution PASS 11/11; kit 37 · sertor-flow 107 verdi, ruff pulito. ULTIMO dei 4
gruppi del Principio XI (A ✅ PR #61, B+C ✅ PR #62). Branch `043-plan-template-neutro`. Storico:
`specs/042-enforcement-vehicles-ospite/plan.md` (gruppi B+C dell'enforcement Principio XI, lato OSPITE —
estende `sertor install rag`: (B) blocco `CLAUDE.md` a marker `SERTOR:RAG-USAGE` che istruisce l'agente
ospite a usare `sertor-rag`/MCP e a NON importare `sertor_core`; (C) hook PreToolUse host-specifico
(`sertor-rag-usage-check.ps1`) che rileva l'uso diretto della libreria fuori da vehicles/test → warning
non bloccante, exit 0 sempre, fail-open. Additivo/non-distruttivo/idempotente, thin sul toolkit kit
(generalizzato `settings_merge` per eventi hook arbitrari, retrocompatibile). Marker distinti da
wiki/SDLC; nessun nuovo ArtifactKind. Constitution PASS 11/11; sertor 104 · kit 37 · sertor-flow 106
verdi. 2° dei 4 gruppi del Principio XI (A ✅ master PR #61). Branch `042-enforcement-vehicles-ospite`.
Storico:
`specs/041-consumo-sicuro-vehicles/plan.md` (gruppo A dell'enforcement Principio XI — auto-wire dei
concern trasversali (osservabilità/config/errori) nel composition root / factory `build_*`, così OGNI
percorso d'ingresso (CLI/MCP/libreria) li applica in modo uniforme; chiude il gap del re-index via
`build_indexer().index()` diretto NON tracciato in telemetria. Helper `_wire_runtime(settings)` (chiama
`enable_observability`, idempotente, no-op se off) chiamato nelle 5 factory consumer-entry
(`build_indexer`/`build_facade`/`build_engine`/`build_baseline_engine`/`build_graph_service`); Principio I
preservato (libreria importabile, eccezione test); `__init__` NON ristretto (FR-007 rinviato). Constitution
PASS 11/11, 564 test root verdi, ruff pulito. È il 1° dei 4 gruppi (A core + B istruzione installer + C
hook + D plan-template neutro) per realizzare il Principio XI; req
`requirements/sertor-core/enforcement-principio-xi/requirements.md`. Branch `041-consumo-sicuro-vehicles`.
Storico:
`specs/037-governance-sertor-flow/plan.md` (epica sertor-cli FEAT-005 — installer di governance/SDLC
come PACCHETTO SEPARATO `sertor-flow`, ortogonale al RAG e SENZA dipendenza da `sertor-core`. Porta su un
ospite l'apparato di metodo di sviluppo: skill+agenti SpecKit (VENDORED da spec-kit MIT, pinned 0.8.18,
con NOTICE/LICENSE) + skill `requirements` e agente `requirements-analyst` (Sertor-authored) + agente
`configuration-manager` + macchinario `.specify/` (templates, scripts ps+bash, extensions/git, workflows)
+ COSTITUZIONE-STARTER NEUTRA (principi generali III/IV/VI/VII + kernel de-RAGizzati di I/V/VIII/IX +
Sicurezza/Governance; ESCLUSI II e X) + blocco rituale SDLC nel CLAUDE.md. Approccio cardine: ESTRARRE il
motore di installazione esistente (`packages/sertor/src/sertor_installer`: Artifact/ArtifactKind/
WriteStrategy/Outcome, execute_plan fail-fast, merge additivi, claude_md a marker, resources via
importlib, InstallReport, sync con guard anti-drift) in un TOOLKIT CONDIVISO `sertor-install-kit` (3°
membro workspace, stdlib-only, NO sertor-core), usato sia da `sertor` (wiki/rag) sia da `sertor-flow`.
Dipendenza da spezzare: oggi `sertor_installer` importa da `sertor-core` solo `ConfigError`/`SertorError`
+ `log_event` → il kit ridefinisce `InstallerError`/`ConfigError` + `log_event` stdlib; `sertor` avvolge
gli errori di `sertor_core.wiki_tools` al boundary (gate di NON-REGRESSIONE = suite packages/sertor
verde). Generalizzazioni: `write_marker_block(path,content,marker_start,marker_end)` (wiki usa
SERTOR:WIKI-RITUAL, sertor-flow usa SERTOR:SDLC-RITUAL, DUE blocchi distinti idempotenti); `execute_plan(
plan, apply)` a callback. Bundle = vendoring asset + plan-builder `build_governance_plan`; subset
`.specify/` distribuibile: VENDOR templates/scripts/extensions/workflows, GENERA per-host init-options/
integration/manifests (come config_gen del wiki), ESCLUDI feature.json (runtime); spedisci entrambi gli
script ps+bash. CLI `sertor-flow install [--target] [--json]`, bundle COMPLETO all-or-nothing (MVP),
install≠run/non-distruttivo/idempotente/fail-fast. `sertor install governance` = solo PUNTATORE a
sertor-flow (no dipendenza tra pacchetti). 7 DA risolte. Constitution PASS 10/10 senza deroghe. Branch
`037-governance-sertor-flow`. Storico:
`specs/036-aggancio-distillazione/plan.md` (memoria conversazioni FEAT-003 — aggancio distillazione
all'archivio: thin consumer additivo, `MemoryArchive.list_recent`→`SessionSummary`, comandi `memory
list`/`show`, factory `build_memory_reader` gated, vincolo FR-013 distillazione sempre su sessione
mirata mai automatica; PR #51, Constitution 10/10). Storico:
`specs/035-memoria-cli-hook/plan.md` (superficie CLI memoria + hook SessionEnd — THIN consumer
sull'MVP memoria già su master. Tre capacità sottili: (1) `sertor-rag memory archive` e (2)
`sertor-rag memory search <query>` = gruppo di comando `memory` con SUB-SUBPARSER argparse
(`add_subparsers` annidato, `set_defaults(handler=_cmd_memory_*)`, dispatch invariato in `main()`),
che delegano a `build_memory_archiver().archive_all()→ArchiveRunReport(archived/skipped/errors)` e
`build_episodic_search().search(SearchQuery)→EpisodicResults(EpisodicHit…)`; due funzioni PURE in
`cli/output.py` (`format_archive_report`/`format_memory_results`, umano + `--json`, stile di
`format_search_results`). (3) Hook `SessionEnd` Claude Code = script PowerShell VERSIONATO
`.claude/hooks/memory-capture.ps1` + voce in `.claude/settings.json` (accanto al wiki hook) che invoca
`sertor-rag memory archive`. GATE privacy `SERTOR_MEMORY` (default off): le factory ritornano già `None`
a memoria spenta → il comando INTERCETTA il `None` e solleva `ConfigError` azionabile (exit 1, nomina
`SERTOR_MEMORY=true`); l'hook fa PRE-CHECK dell'env → no-op silenzioso exit 0 (non avvia neppure Python).
L'hook archivia TUTTO via `archive_all()` (idempotente, costo ~nullo sui già archiviati). Non-bloccante/
non-fatale: `try/catch`, esce SEMPRE 0, ignora l'exit del comando, timeout host come cap (pattern di
`wiki-pending-check.ps1`). ADDITIVO PURO: core/CLI esistenti INVARIATI; nessuna nuova dipendenza/porta/
entità. Comandi host-agnostici (Principio X), hook host-specifico = adattatore del trigger; distribuzione
su ospiti via `sertor install` FUORI AMBITO. Test: comandi con core mockato (stile `test_cli_search`),
gate `None→ConfigError`, idempotenza, `since>until→exit 1`; hook = verifica manuale gate/no-op.
Constitution PASS 10/10 (pre e post), nessuna deroga. Branch `035-memoria-cli-hook`. Storico:
`specs/033-ricerca-episodica/plan.md` (memoria conversazioni FEAT-002 — ricerca episodica full-text
LOCALE: rende interrogabile l'archivio transcript di FEAT-001 («ne avevamo già parlato?»). Motore =
SQLite **FTS5 nativo** (DA-FT-001, verificato live nel venv: Python 3.12/sqlite 3.50 → AVAILABLE): tabella
virtuale external-content `turns_fts` su `turns.content` nello STESSO `memory.sqlite`, ranking `bm25()` +
`snippet()` nativi, ZERO dipendenze (stdlib `sqlite3`). Aggiornamento indice (DA-FT-005) = **trigger sync**
su `turns` (freschezza by construction, FR-020/SC-008) + `'rebuild'` una-tantum/recovery; indice DERIVATO
e ricostruibile → non viola non-distruttività; FEAT-001 INVARIATA (schema FTS creato lazy dal componente di
ricerca, NON da `MemoryArchive`). Seam = **componente concreto + servizio**, NESSUNA porta (come
`MemoryArchive`, single consumer — YAGNI; riuso BM25 RAG scartato = dominio diverso). Risultato per-TURNO +
ref sessione: `session_key`/`captured_at`/`role`/`turn_index`/`source_path?`/`snippet`/`score`; ordine
pertinenza (tie-break recency) o recency-first; finestra temporale su `captured_at` (`since>until` →
`InvalidTimeWindowError`, FR-007); limite/snippet via `SERTOR_EPISODIC_LIMIT`(20)/`_SNIPPET_TOKENS`(12).
PRIVACY by design: zero rete nel percorso query (SC-004), query nel log evento `episodic_search` HASHATA.
Degradazione non-fatale ovunque (archivio/indice assente/FTS5 mancante/voce malformata → stato vuoto +
warning, mai errore). Latenza budget <200ms p95 (misurato <0.1ms su 5062 turni dogfood). `services/
episodic_search.py` nuovo + `build_episodic_search` in composition (gate `memory_enabled`). Constitution
PASS 10/10 (pre e post), nessuna deroga. Branch `033-ricerca-episodica`. Storico:
`specs/031-cattura-archiviazione/plan.md` (memoria conversazioni FEAT-001 — cattura & archiviazione del
tier grezzo episodico, prima metà MVP. Cattura le conversazioni dell'agente e le conserva in un archivio
SQLite locale `<index_dir>/memory.sqlite` (gitignored via `**/.index/`, namespaced per progetto,
conservato/non-ruotato). GRANULARITÀ IBRIDA (DA-M-b): unità archiviata = sessione, ma schema a 2 tabelle
`sessions`+`turns` preserva i CONFINI DEI TURNI così FEAT-002 indicizza per-turno senza ri-parsare il
JSONL grezzo. UNA porta nuova `TranscriptCaptureAdapter` (8ª Protocol, cattura host-specifica dietro
boundary); lo STORE è concreto SENZA porta (come EmbeddingCache/SqliteObservabilityStore — nessun 2°
consumatore oggi). Adapter Claude-Code: legge `~/.claude/projects/<encoded>/<session-id>.jsonl`
(encoding sep→`-`, es. `C--Workspace-Git-Sertor`), parser BEST-EFFORT difensivo (righe non-JSON → skip +
warning, mai fatale; turni user/assistant block text/thinking; tool_use/result scartati). Idempotenza =
stem-filename + `INSERT OR IGNORE` (skip OSSERVABILE, non no-op silenzioso). PRIVACY-by-default: 4 manopole
default solo in Settings — `SERTOR_MEMORY` (false), `SERTOR_MEMORY_ADAPTER` (claude-code),
`SERTOR_MEMORY_RETENTION_DAYS` (None=nessuna scadenza, solo gancio→FEAT-006),
`SERTOR_MEMORY_SCRUB_PATTERNS`. SCRUB testuale libero = funzione PURA `scrub_text` in
`observability/scrub.py` (estende la redazione per-CHIAVE `redact()` al CONTENUTO: sk-…/AKIA…/bearer/
KEY=VALUE con hint/Authorization; ripiego conservativo redige il segmento; mai bypassabile, mai segreti
negli eventi). 3 `build_*` lazy in composition gated su `memory_enabled` (off = zero import/file).
stdlib-only nel corpo, additivo (porte/servizi esistenti invariati). FUORI AMBITO: ricerca FEAT-002,
distillazione FEAT-003, remember-this FEAT-005, enforcement retention FEAT-006, multi-assistente FEAT-008.
Constitution PASS 10/10 senza deroghe. Branch `031-cattura-archiviazione`. Storico:
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
