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

## [2026-05-28] record | Tappa 1 baseline completata (3 provider a confronto)

- Ambiente: venv `uv` Python 3.12 + `chromadb`, `langchain-text-splitters`, `httpx`, `numpy`.
- `shared/`: config (.env override + normalizza OLLAMA_HOST), embeddings layer sui 3 provider, loaders.
- `01-baseline/`: chunking language-aware, indicizzazione Chroma (1 collection/provider), retrieval.
  655 doc → **3500 chunk**. Dual-corpus (codice+doc) confermata nel retrieval.
- **Eval (10 query, hit-rate@k + MRR@10):** azure-large (hit@1 0.90, MRR 0.950) >
  azure-small (0.70 / 0.833) > ollama locale (0.60 / 0.693). Dettagli:
  [experiments/01-baseline.md](experiments/01-baseline.md).
- Learning chiave: baseline solo denso; query a simboli esatti → motivano hybrid+rerank (Tappa 02).
- Commit per step: `2eac297` setup, `a97bfc3` ambiente, `3567404` shared, `351f13a` baseline.

## [2026-05-28] record | Tappa 2 hybrid + reranking completata

- `02-hybrid-reranking/`: BM25 (tokenizer pro-identificatori) + dense da Chroma + fusione RRF
  (`hybrid.py`), reranking cross-encoder FlashRank (`rerank.py`), eval esteso a 18 query
  (10 NL + 8 a simboli) confrontando dense/hybrid/hybrid+rerank sui 3 provider (`evaluate.py`).
- **Esito chiave (onesto):** il valore della tecnica dipende dalla forza del retriever.
  - ollama (locale, debole): hybrid+rerank MRR 0.50→0.90, simboli 0.13→0.94 (quasi a pari con Azure).
  - azure-large (forte, già saturo su questo eval): dense puro resta il migliore (MRR 0.972);
    il reranker generico ms-marco non aiuta o peggiora di poco.
- Implicazione: per deploy locale/privacy hybrid+rerank è essenziale; per cloud large serve
  un reranker tarato sul codice o un eval più difficile. Dettagli:
  [experiments/02-hybrid-reranking.md](experiments/02-hybrid-reranking.md).
- Commit: `cd0c67a` deps, `ca1708e` hybrid, `bf61177` rerank.

## [2026-05-28] record | Tappa 3A code graph leggero (AST) completata

- Scelta concordata: **A ora** (grafo custom leggero), **C in seguito** (Microsoft GraphRAG) per confronto.
- `03-graphrag/`: `build_graph.py` (AST→networkx, 1917 nodi / 4868 archi),
  `graph_query.py` (def/callers/callees/docs/context multi-hop), `evaluate.py`.
- **Esito:** definizione@1 sui simboli 6/8. Navigazione ricca (es. HTTPException 69 chiamanti,
  APIRouter 10 doc collegati). Miss: `JSONResponse`/`WebSocketDisconnect` perché **re-export
  da Starlette** (l'AST li vede come import, non come definizioni) → limite onesto.
- Learning: il grafo è preciso/strutturale ma senza ricerca semantica → **complementare** al
  vettoriale/ibrido. Motiva la fusione grafo+vettoriale. Dettagli:
  [experiments/03-graphrag.md](experiments/03-graphrag.md).
- Commit: `5af963a` deps, `de8ec3a` build, `4a4517c` query.

## [2026-05-28] query | Stima costo token per la Tappa 3C (Microsoft GraphRAG)

- Misurato il corpus: completo **~590K token** (229K codice + 361K doc), subset **~90K**.
- Regola empirica indicizzazione GraphRAG ≈ **5–10× il corpus** in token LLM →
  subset ~0.6–1.2M tok (~$0.15–0.30 mini / ~$2–4 4o); completo ~3.5–7.5M tok (~$1–2 / ~$15–30).
  Incertezza ±2× (chunk_size, gleanings, #entità/community). Dettagli e tabella:
  [experiments/03-graphrag.md](experiments/03-graphrag.md) (sezione Stima costi).

## [2026-05-28] record | Tappa 3C Microsoft GraphRAG eseguita sul subset

- Esecuzione GraphRAG 3.1.0 in venv isolato (`03-graphrag/.venv-grag`) sul subset (50 doc `.md`
  + 7 `.py` security). Causa isolamento: GraphRAG/graspologic porta `numpy < 2.x`; il `.venv` principale
  ha 2.4 → conflitto diretto.
- **Setup:** config YAML con new schema (v3.1: `completion_models:` / `embedding_models:` anziché `llm:`),
  `gpt-5.4-mini` + `text-embedding-3-small` su Azure Foundry. Fissati 2 ostacoli: (1) hang
  `litellm` import → `LITELLM_LOCAL_MODEL_COST_MAP=True`; (2) pattern file `*.txt` only → fix
  `file_pattern: '.*\.(md|py)$$'`.
- **Token reali (ground truth metrics):** chat 1.098 chiamate / 1.965M token (prompt 1.469M +
  completion 496K), 949 retry (46% rate — throttling TPM pesante); embedding 112 chiamate / 366K token.
  **Totale ~2.33M token, costo ~$3.34** (litellm chat+embed). Tempo wall 14 min (extract 557s,
  community report 250s).
- **Grafo:** 57 doc / 102 text_unit / **1090 entità / 1779 relazioni / 239 community + report NL**.
  Entity_types: default (EVENT 650, ORG 355, PERSON 48, GEO 36, API 1) → concetti tecnici forzati
  in categorie sbagliate (FASTAPI/OAUTH2→ORG, OPENAPI→EVENT). Hub FASTAPI (degree 311), relazioni
  semantiche FASTAPI→PYDANTIC/OPENAPI/STARLETTE (catturate dal grafo vs AST).
- **Vs stima:** atteso 0.6–1.2M tok (~$0.15–0.30); reale 1.965M tok (+60–230% sopra): motivi
  = `summarize_descriptions` ad alto volume, `gpt-5.4-mini` non economico come inizialmente pensato,
  49% retry rate (throttling). La regola empirica 5–10× era giusta, il modello sottodimensionato.
- **Learning 3A vs 3C:** AST = preciso strutturale (def@path:lineno), semantica zero, costo zero,
  deterministico. GraphRAG = semantico/tematico, summary NL, denaro reale, lento, entity_types
  generico (non tarato sul codice). **Conferma dual-RAG:** nessuno dominante; fusion necessaria.
- Dettagli: [experiments/03-graphrag.md](experiments/03-graphrag.md) (Tappa 3C).

## [2026-05-28] query | Tappa 3C: query GraphRAG global+local sul subset

- Eseguite query di prova su grafo 3C via CLI `python -m graphrag query --root ... --method {global|local}`.
- **GLOBAL** ("come gestisce FastAPI auth/security..."): sintesi tematica su 239 community,
  copre OAuth2/JWT/HTTP auth/API key/OpenID/Argon2/error handling, citazioni `[Data: Reports]`.
  ~21 call LLM / 257K token / ~$0.23.
- **LOCAL** ("cos'è OAuth2PasswordBearer?"): puntuale e corretta (subclass OAuth2, estrae bearer,
  NON valida token), citazioni Entities/Relationships/Sources. 1 call LLM + 1 embedding (18 tok) → quasi gratis.
- **Token 3C totale finora:** indexing $3.34 + query ~$0.23 ≈ ~$3.57 (subset).
- **Learning critico:** entity_types generici non penalizzano il retrieval (GraphRAG usa community report testuali);
  penalizzano la navigazione-per-tipo. Conferma: AST spiega dov'è; GraphRAG spiega cosa fa (NL grounded).
  → Complementarità dual-RAG confermata.
- **Apri come:** tuning custom entity_types (class/function/module/endpoint/exception/concept) + prompt-tune;
  integrazione AST↔GraphRAG↔vettoriale.
- Dettagli: [experiments/03-graphrag.md](experiments/03-graphrag.md) (sezione "Query di prova (global + local)").

## [2026-05-28] record | Tappa 3C re-run: entity_types di dominio vs generici

- **Re-run GraphRAG con entity_types di dominio** (CLASS, FUNCTION, DATA_MODEL, ENDPOINT, EXCEPTION, CONCEPT, LIBRARY)
  derivati data-driven dal tool `derive-entity-types` (analizza AST + embedding cluster). Prompt di estrazione riscritto
  con 2 esempi few-shot reali FastAPI (codice+doc).
- **Esecuzione:** primo tentativo ucciso sessione (extract 100/102), retry ha riusato cache (102/102 in ~20s) e completato step a valle.
  Backup run1 generico in `03-graphrag/grag/output_run1_generic/` (gitignored). Script riusabile `compare_runs.py`.
- **Confronto struttura:** entità 1090→1305 (+215), relazioni 1779→2684 (+905, +51%), community 239→330 (+91).
  Distribuzione run2: CONCEPT 68.4%, FUNCTION 7.3%, LIBRARY 7.0%, DATA_MODEL 6.7%, CLASS 4.9%, ENDPOINT 4.1%, EXCEPTION 1.1%, ~0.4% untyped.
  Entity top tipizzate correttamente: FASTAPI ORGANIZATION→LIBRARY, PATH OPERATION EVENT→ENDPOINT, OAUTH2PASSWORDBEARER→CLASS, REQUEST→DATA_MODEL, OPENAPI→CONCEPT.
- **Token/costo:** gpt-5.4-mini 1362 call (202 cache, 470 retry, 45% retry_rate), 1.761M+678K = 2.439M token, ~$4.37
  (+30% vs run1 generico $3.34). Embedding 138 call, 478K token, ~$0.01. Tradeoff: grafo +51% relazioni → più summarize/report.
- **Learning:** entity_types dominio abilita navigazione-per-tipo strutturale (CONCEPT catch-all 68%), ma costo +30%.
  CONCEPT domina → margine di split/raffinamento; ~0.4% mislabel/untyped. Conferma flow `derive-entity-types` data-driven.
  Dual-conclusione: entity_types generici ok per retrieval NL (GraphRAG usa report testuali), ma entity_types dominio
  necessari per drill-down/aggregazione per tipo (use case dipendente).
- Dettagli: [experiments/03-graphrag.md](experiments/03-graphrag.md) (sezione "Re-run con entity_types di dominio").

## [2026-05-28] record | Suite di test dimostrativi (pytest) + runbook DEMOS.md

- Creato **runbook `DEMOS.md`** (root) per ogni configurazione [[01-baseline]], [[02-hybrid-reranking]], 
  3A grafo AST, 3C GraphRAG: scopo, prerequisiti, comando esatto, output atteso e osservato reale.
  + sezione suite pytest.
- **Suite pytest** in `tests/` con 3 categorie di test:
  - **FREE** (sempre eseguibili): BM25 sparse, grafo AST, artefatti GraphRAG/parquet.
  - **GATED** (skipati se backend manca): dense/hybrid → need Ollama/Chroma via `conftest.py` fixture; passano con Ollama attivo.
  - **PAID** (skipati salvo `--run-paid`): query GraphRAG local search su Azure.
  Stato attuale: **8 passed, 1 skipped** (skip = test paid).
- Principio (coerente col goal enterprise toolset): smoke test verificano che PIPELINE girino e output
  ben formato, NON qualità retrieval (quella è negli evaluate.py di ogni tappa, numeri già nel wiki).
- **FINDING emerso:** il provider locale Ollama `nomic-embed-text` su query NL tipo "OAuth2 password bearer..."
  restituisce blob base64 (dati immagine in docs_src/stream_data) anziché doc pertinenti → segnala:
  (a) debolezza provider locale già nota da eval, (b) **IGIENE CORPUS**: blob base64 da filtrare in ingestion.
  → Spunto miglioramento: chunking/filtri binari in fase ingestion (aperto per Tappa follow-up).
- Nota: graph_query.py callers HTTPException sul grafo AST corrente = 10 chiamanti (grafo su disco).
- pytest aggiunto a requirements.txt (dev). Prossimi: filtro blob binari; tassonomia entity_types;
  integrazione AST↔GraphRAG↔vettoriale; Tappa 4 Agentic.
- Dettagli: `DEMOS.md` e `tests/*.py`.

## [2026-05-28] record | Vetrina esempi query→risposta (ESEMPI.md) + pagina sintesi

- Creata `syntheses/esempi-query-risposta.md` (pagina di sintesi): presenta i 4 motori ([[01-baseline]], [[02-hybrid-reranking]], Grafo AST, [[03-graphrag]]),
  tabella "quale motore, quando", insight dal testa-a-testa sulla stessa domanda (3 casi: autenticazione FastAPI, chi chiama HTTPException, abilita CORS).
- **Tesi confermata:** nessun motore domina tutto. Baseline/Hybrid vincono per "andare al file giusto"; AST è preciso su struttura
  (chi-chiama-chi); GraphRAG eccelle su spiegazioni (ma con costo LLM e limite su re-export). → Conferma dual-RAG (fusion).
- Aggiornata `index.md`: aggiunto link a nuova sintesi in sezione Sintesi; accostato ESEMPI.md in sezione Demo & Test.
- Rimando sempre a `ESEMPI.md` per gli esempi completi (vetrina divulgativa, non tecnica).

## [2026-05-28] record | Chunking code-aware via tree-sitter + eval recursive vs tree-sitter

- **Implementazione:** modulo `shared/chunking_code.py` — parser tree-sitter (binding standard `tree-sitter>=0.25`
  + grammatica `tree-sitter-python>=0.25`) per AST-driven chunking codice Python. Granularità: funzioni top-level
  e metodi = chunk; metodi con contesto classe in testa; modulo-level raggruppato; >50 righe suddivise.
  Metadati: `symbol`, `symbol_kind` (module/class/function/method), `qualname`, `start_line`, `end_line`.
  Config `CODE_CHUNKER=treesitter` (default) | `recursive` (fallback se lingua non supportata).
  **Nota tecnica:** pacchetto `tree-sitter-language-pack` scartato (binding incompatibile); usato binding
  standard documentato.
- **Eval Tappa 01 (doc-biased):** 10 query NL su doc Markdown (ground-truth). Corpus 3500→3942 chunk.
  Regressione dovuta a valutazione doc-oriented: chunk codice più fini competono con doc, penalizzando dense.
  ollama 0.60/0.693→0.50/0.578, azure-small 0.70/0.833→0.80/0.883, azure-large 0.90/0.950→0.70/0.833.
  **Insight:** eval 01 non misura il code-aware; serve eval 02.
- **Eval Tappa 02 (symbol-biased):** 18 query (10 NL + **8 a SIMBOLI**) su indice tree-sitter, ibrido+rerank.
  **Risultato chiave:** tree-sitter eccelle sui simboli: azure-large MRR 0.972 (overall) / **1.000 (simboli)** = perfetto.
  Dense puro: 0.880 / 0.938. Ipotesi: denso-ingenuo, chunk piccoli di codice hanno sim. uniforme.
  Conclusione: **tree-sitter + hybrid + rerank** = la combinazione giusta.
- **Learnings:** (a) tree-sitter unità coerenti + BM25 lessico identificatori + rerank disambigua = perfetto per simboli;
  (b) metadati strutturali (qualname, righe) sono il PONTE verso fusione grafo↔vettoriale ([[architettura-target]] dual-RAG);
  (c) default **treesitter** mantenuto per coerenza unità e metadati ingestion; `CODE_CHUNKER=recursive` disponibile.
- **Aperto:** ampliare eval 01 con query simboli; recursive-vs-treesitter su eval 02 con re-index; igiene corpus (blob base64).
- Dettagli: `experiments/01-baseline.md` (sezione "Chunking code-aware (tree-sitter)").

## [2026-05-29] record | README di root — documento "come funziona"

- Creato `README.md` in root del workspace come punto d'ingresso principale. Documenta l'obiettivo
  (toolset RAG riproducibile, repo-agnostico per fusione codice+doc), la pipeline shared
  (ingestion → indici → retrieval), e descrive il ruolo di ogni componente reale:
  - `shared/config.py` — switch `RAG_BACKEND` (local/azure) e `CODE_CHUNKER` (treesitter/recursive).
  - `shared/loaders.py` — ingestion corpus (file `.py`, `.md`).
  - `shared/embeddings.py` — 3 provider intercambiabili (Ollama, Azure text-embedding-3-small/large).
  - Chroma — 1 collection per provider, retrieval vettoriale.
  - Hybrid BM25+dense+RRF+rerank FlashRank — per locale e confronti; Azure AI Search alternativa.
  - Code graph (AST networkx) — navigazione strutturale; Microsoft GraphRAG come upgrade semantico.
- **Sezioni:** scopo, architettura pipeline (con diagramma Mermaid), struttura cartelle,
  quickstart, test (14 passed / 1 skipped), convenzioni (delega git/wiki, `.env`), roadmap con 4 tappe.
- **Ruolo complementare:** README = tecnico "come va insieme"; DEMOS.md = runbook eseguibile;
  ESEMPI.md = vetrina divulgativa. Aggiornato `index.md` con link e nota su entry-point.

## [2026-05-29] record | Tappa 4 Agentic RAG — design + decisioni

- Creato `04-agentic-rag/README.md` (design doc): spiega il salto concettuale da **retrieval single-shot**
  (01–03, flusso fisso deciso dall'utente) a **loop iterativo guidato da LLM** (PLAN → ROUTE → RETRIEVE →
  REFLECT → SYNTHESIZE), con tabella di confronto puntuale e diagramma architettura (orchestratore +
  shared/llm.py + shared/retrieval.py facade + MCP).
- **Decisioni prese (coerenti col workspace):**
  1. **Confronto orchestratori:** si testano tutti e tre i framework (AutoGen, Semantic Kernel, LangGraph)
     sullo stesso orchestratore — fedele allo spirito "quale scegliere quando" del workspace — partendo da
     **AutoGen** end-to-end, poi SK, poi LangGraph (velocità/semplicità criterio di priorità).
  2. **LLM intercambiabile via `RAG_BACKEND`** (Ollama `llama3.1` default locale + Azure `gpt-5.4-mini` |
     `gpt-4-turbo`), nuovo modulo `shared/llm.py` (client chat unificato con tool-calling).
  3. **Libreria-first poi MCP:** prima la libreria di orchestrazione pura (consumabile, testabile); poi
     MCP server a livello di applicazione (frontend per Claude Code/AutoGen/SK).
- **Prerequisiti tecnici identificati:** manca client LLM chat in shared/ (c'è solo embeddings) → nuovo
  modulo `shared/llm.py`. I retriever 01–03 sono già funzioni importabili ma sparsi → facade
  `shared/retrieval.py` (search_code, search_docs, search_combined, find_symbol, who_calls, related_docs,
  global_summary). Serve filtro `source=code|doc` in HybridIndex per separare le sorgenti in output
  (fusion RRF + colonna "sorgente").
- **Modifiche concrete:** nuovi file `shared/llm.py`, `shared/retrieval.py`, `04-agentic-rag/orchestrator.py`;
  aggiornamento `02-hybrid-reranking/hybrid.py` (esporre come funzione facade); aggiornamento config
  `shared/config.py` (LLM model/endpoint); test e runbook DEMOS.md aggiornati.
- **Aperto:** tuning entity_types custom per GraphRAG (Tappa 4, follow-up); integrazione AST↔retrieval
  (query planning context-aware); MCP schema e client tooling (Claude SDK).
- Aggiornati `wiki/index.md` (tabella Esperimenti, 04 ora "design" con link) e
  `wiki/syntheses/architettura-target.md` (riga Tappa 4 roadmap con backlink al design).

## [2026-05-29] record | Tappa 04 — baseline Agentic RAG (orchestratore vanilla) implementata e verificata

- **Implementazione baseline vaniglia (loop manuale):** orchestratore iterativo plan→route→retrieve→reflect→synthesize.
  Moduli nuovi:
  - `shared/llm.py` — client chat intercambiabile (Ollama `/api/chat` + Azure OpenAI v1) con tool-calling nativo;
    normalizza tool_calls Ollama e Azure in `ToolCall(id, name, arguments)`.
  - `shared/retrieval.py` — facade unica ai motori 01–03 (caricati via importlib): `search_code`, `search_docs`,
    `search_combined` (con rerank), `find_symbol`, `who_calls`, `related_docs`. Filtro `source` per separare/fondere.
  - `04-agentic-rag/tools.py` — registry schemi-tool (OpenAI/Ollama format), dispatch `call_tool()`, SYSTEM_PROMPT.
  - `04-agentic-rag/orchestrator.py` — loop orchestrator (piano, routing, retrieval, reflect, synthesize).
  - `04-agentic-rag/agent.py` — CLI wrapping.
- **Modifica `02-hybrid-reranking/hybrid.py`:** esposto parametro `source` (code|doc|None) a dense/sparse/search
  (backward-compatible) per separare corpus in output (precondizione fusion RRF).
- **Config:** nuovo setting `OLLAMA_CHAT_MODEL` in `shared/config.py` (default llama3.1, richiede tool-calling).
- **Testing:** `tests/test_agentic.py` — 5 smoke test (registry, tool unknown, graph tool, source filter).
  Suite totale: **19 passed, 1 skipped** (skip = test paid).
- **Esito verificato end-to-end:** su Ollama `qwen3:30b-a3b` (llama3.1 non in locale), task "Cos'è OAuth2PasswordBearer
  e dove?" → orchestratore chiama `find_symbol` → grafo AST restituisce `fastapi/security/oauth2.py:433` →
  risposta sintetizzata corretta (2 passi).
- **Learnings:** (a) modularità: LLM + retrieval come layer shared, orchestratori concorrenti (AutoGen/SK/LangGraph)
  possono consumarli senza duplicazione; (b) tool-calling normalizzato tra provider; (c) vanilla loop è leggibile e
  debuggabile, baseline vs framework.
- Docs: `DEMOS.md` sezione "04 — Agentic RAG" (comando, output osservato, test), `.env.example` (OLLAMA_CHAT_MODEL),
  `04-agentic-rag/README.md` checklist aggiornata.
- Wiki: pagina esperimento `experiments/04-agentic-rag.md`, aggiornato `index.md` (tabella 04),
  backlink da [[architettura-target]].

## [2026-05-29] record | Tappa 04 — adattatore AutoGen implementato e verificato

- **Implementazione AutoGen (framework 1/3):** `04-agentic-rag/autogen_app.py` (NUOVO), classe
  `AssistantAgent` con `reflect_on_tool_use=True`. Client LLM riusato da `shared/llm.py`: locale
  = OpenAI-compatible Ollama `/v1` (nessun `[ollama]` extra), Azure = `AzureOpenAIChatCompletionClient`.
  Tool registry e system prompt ereditati da `tools.py` → confronto a parità strumenti/prompt vs
  vanilla.
- **Implementazione modulo:** AgentApp costruisce client locale o Azure da `RAG_BACKEND`, carica
  tool 6/registry (schema da firma + docstring), avvia conversazione. Modello Ollama scelto da
  config: qwen3, llama3.1, etc. (richiede tool-calling nativo).
- **Requirements:** `autogen-agentchat>=0.7`, `autogen-ext[openai]>=0.7` aggiunte a `requirements.txt`;
  installate nel venv principale (riuso `shared.retrieval` → chromadb/flashrank/networkx).
  Declassamento protobuf 6→5.29 verificato OK, niente rotta suite.
- **Test:** `test_autogen_adapter_costruibile` (free, `importorskip`): adattatore importa, espone
  6 tool/docstring, costruisce client locale OK.
- **Esito E2E Ollama `qwen3:30b-a3b`:** task "In quale file è definita la classe APIRouter?"
  → `find_symbol("APIRouter")` → `fastapi/routing.py:1005` (AST) → sintesi corretta.
  Risultato: 1 tool-call, trace pulita.
- **Learning:** AutoGen schema-tool **da firma + docstring**. Ollama API OpenAI-compatible su `/v1`
  con tool-calling nativo → unica classe client (locale + Azure). Modularità `shared/llm.py` +
  `shared/retrieval.py` semplifica adattatore.
- **Suite aggiornata:** 20 passed, 1 skipped (skip = test paid GraphRAG).
- **Docs:** DEMOS.md "04b — Adattatore AutoGen" (comando, output osservato, test), 
  `04-agentic-rag/README.md` checklist aggiornata (AutoGen done).
- **Wiki aggiornato:** `experiments/04-agentic-rag.md` sezione "Adattatore AutoGen" con cosa/come/esito/learning,
  status frontmatter → "vanilla + AutoGen completati; SK/LangGraph + eval da fare",
  prossimi passi riprioritizzati (eval set primo),
  `index.md` riga 04 stato aggiornato.

## [2026-05-29] record | Tappa 04 — eval comparativa + documentazione parlante (vanilla vs AutoGen)

- **Setup eval:** `04-agentic-rag/eval_tasks.json` (NUOVO) — eval set 5 task multi-step con
  `expected_files` (ground-truth verificata): apirouter-def, oauth2-concept, depends-impl,
  background-tasks, httpexception-def.
- **Esecuzione:** `04-agentic-rag/evaluate.py` (NUOVO) — lancia ogni task attraverso ogni motore
  (vanilla, AutoGen) **a parità di tool/prompt**, misura `cited` (risposta cita file atteso),
  `steps`, `tools_called`. Stampa tabella metriche + genera documentazione parlante.
- **Risultati (Ollama qwen3:30b-a3b, 5 task × 2 motori):**
  - vanilla: 5/5 cita, 2.0 passi medi, 1.0 tool medi.
  - AutoGen: 5/5 cita, 1.4 passi medi, 1.4 tool medi.
  - Nota: BackgroundTasks AutoGen fa traiettoria più ricca (find_symbol → search_docs → related_docs),
    testo risposta include documentazione non solo posizione file.
- **Artefatto generato:** `04-agentic-rag/ESEMPI-agentic.md` (NUOVO) — doc divulgativa
  "ho chiesto X → l'agente ha fatto Y → mi ha risposto Z", auto-generata da evaluate.py.
- **Learning:** eval set standardizzato (stessi tool/prompt/modello) rende confronto misurabile;
  i due motori condividono strumenti ma divergono per orchestrazione. Task attuali favoriscono
  localizzazione (find_symbol); prossimi task multi-hop discrimineranno meglio.
- **Wiki aggiornato:**
  - `experiments/04-agentic-rag.md`: sezione "Eval comparativa" con setup/risultati/osservazione/learning.
    Frontmatter status → "vanilla + AutoGen + eval comparativa completati; SK/LangGraph + MCP da fare".
    Link a ESEMPI-agentic.md aggiunto.
  - `index.md`: riga 04 stato aggiornato; Demo & Test link a ESEMPI-agentic.md aggiunto.
  - `updated: 2026-05-29` (eval comparativa vanilla vs AutoGen).

## [2026-05-29] record | Tappa 04 — eval set ampliato (9 task, metrica tool_ok, cache + render-from)

- **Ampliamento eval set:** `04-agentic-rag/eval_tasks.json` esteso da 5 a **9 task** con campi
  `type` (categoria: localizzazione, multi-hop, doc-concept, code+doc) e `expected_tools` (strumenti ideali).
  Ground-truth ancorata a token file-specifici (es. `async.md`, `routing.py:1005`) per evitare falsi
  positivi. Nuovi task: **httpexception-usage** (multi-hop find_symbol+who_calls),
  **def-vs-async** (doc-concept puro: find_symbol inutile), **query-param-codedoc** (code+doc fusion),
  **background-doc** (domanda documentale → routing cruciale: search_docs vs find_symbol).
- **Nuova metrica:** `tool_ok` (boolean) — agente ha usato ≥1 strumento ideale da `expected_tools`.
  Affianca `cited` e cattura il routing dei tool (non solo se il file viene citato).
- **Separazione esecuzione/scoring:** `04-agentic-rag/eval_results.json` (NUOVO) salva i risultati
  grezzi (18 righe: 9 task × 2 motori) con esecuzione LLM. Nuovo flag **`--render-from eval_results.json`**
  ri-calcola metriche e rigenera ESEMPI-agentic.md SENZA chiamate LLM (re-score gratuito quando si
  raffina la ground-truth).
- **Risultati eval (Ollama qwen3:30b-a3b, 9 task × 2 motori):**
  - vanilla: 9/9 cita (100%), 9/9 tool_ok (100%), 2.2 passi medi, 1.3 tool medi.
  - AutoGen: 8/9 cita (89%), 8/9 tool_ok (89%), 1.4 passi medi, 1.4 tool medi.
- **Discriminazione reale emersa:** task **background-doc** ("a cosa servono e DOVE SONO DOCUMENTATE
  le BackgroundTasks"):
  - vanilla: usa `search_docs` → cita `docs/en/docs/reference/background.md` (doc) ✅.
  - AutoGen: usa `find_symbol`+`search_code` → cita esempio di codice `docs_src/.../tutorial001.py`
    (codice, non doc) ❌. Routing di tool sbagliato per domanda documentale.
  - Implicazione: **routing doc-vs-code** è critico per dual-RAG; serve context-aware query planning
    per disambiguare "dove è documentato" (scegli search_docs) vs "mostra esempio" (scegli search_code).
- **Caveat non-determinismo:** modelli locali Ollama non-deterministici; run precedenti davano
  numeri leggermente diversi (es. 4.8/5 vs 5/5). Con 9 task la tendenza è più stabile, ma serve
  **mediare su più run** per ridurre rumore statistico.
- **Learning:** (a) tipi di task eterogenei + metrica tool_ok rendono confronto **discriminante**
  (non più 5/5 piatto); (b) bug ground-truth originale (token `background.md` non matchava
  `background-tasks.md`) spingeva verso falsi positivi → correzione spinse il design separazione
  esecuzione/scoring; (c) cache eval_results.json + --render-from permette iterate su ground-truth
  a costo zero.
- **Wiki aggiornato:**
  - `experiments/04-agentic-rag.md`: sezione "Eval comparativa" ampliata con 9 task, metriche
    tool_ok, risultati vanilla 9/9 vs AutoGen 8/9, caso background-doc, cache/render-from, caveat.
    Status → "vanilla + AutoGen + eval comparativa ampliata (9 task, tool_ok, cache);
    SK/LangGraph + MPC da fare". Prossimi passi riprioritizzati (stabilità eval, SK, LangGraph).
  - `index.md`: riga 04 stato aggiornato; timestamp updated.
  - `log.md`: questa voce.

## [2026-05-29] record | Tappa 04 — entry point su Azure gpt-5.4-mini + eval rieseguita + fix metrica passi

- **Spostamento entry point su Azure:** il modello locale Ollama `qwen3:30b-a3b` non è affidabile come agente
  (tool-calling instabile su agentic RAG). Riesecuzione eval set (9 task × 2 motori) su Azure **gpt-5.4-mini**
  (endpoint v1 `/chat/completions`, api-key auth, deployment su Azure Foundry). Default *di codice*
  (config.py) resta local-first; il `.env` di riferimento usa `RAG_BACKEND=azure` (chat gpt-5.4-mini +
  embeddings text-embedding-3-large). Superficie futura: agente Claude via MCP.
- **Verifica connettività Azure:** percorso Azure chat in `shared/llm.py` (AzureChat) funziona correttamente
  con endpoint v1, header api-key, temperature 0. Adattatore AutoGen (`AzureOpenAIChatCompletionClient`) fa
  tool-calling correttamente (stripping `/openai/v1` → azure_endpoint base + api_version + deployment).
- **Fix metrica `passi`:** per AutoGen veniva contato `passi = n° tool` (incoerente con vanilla che contava
  turni LLM). Ora `autogen_app.py` conta i **turni LLM reali** (round di tool-call + turno sintesi finale).
  Reso confrontabile con vanilla. `evaluate.py` usa `out["steps"]` per autogen (coerente).
- **Risultati eval (Azure gpt-5.4-mini, 9 task × 2 motori):**
  - vanilla: 9/9 cita (100%), 9/9 tool_ok (100%), 2.7 passi medi, 3.2 tool medi.
  - AutoGen: 9/9 cita (100%), 7/9 tool_ok (78%), 2.7 passi medi, 3.4 tool medi.
  **Lettura onesta:** (a) correttezza fattuale 9/9 per ENTRAMBI — il modello affidabile elimina i miss di
  contenuto che si vedevano in locale (conferma: entry point locale non era affidabile); (b) l'unica differenza
  è il *routing degli strumenti*: i 2 "tool✗" di AutoGen sono task di localizzazione (apirouter-def,
  background-def) dove ha usato `search_code` invece del più efficiente `find_symbol`, MA ha comunque citato
  il file giusto (cited=True) → scelta meno ideale, non errore; (c) gpt-5.4-mini è molto più "agentico"/verboso
  del locale: usa più strumenti (fino a 9–11 chiamate su query-param-codedoc). Su modello forte, la metrica
  `cited` satura: il segnale discriminante diventa l'efficienza/routing (tool_ok).
- **Caveat non-determinismo:** 1 run per task (non mediato). Learning: con modello forte, è il routing che
  differenzia, non la correttezza fattuale.
- **Wiki aggiornato:**
  - `experiments/04-agentic-rag.md`: sezione "Eval comparativa" riscritto con tabella Azure (vanilla 9/9/9 2.7/3.2 vs
    AutoGen 9/9/7 2.7/3.4), lettura onesta (9/9 fattuale; differenza su routing; soft-miss di AutoGen con risposta
    corretta; gpt-5.4-mini verboso), fix metrica passi, entry point Azure. Indicato che il confronto su modello forte
    sposta il segnale su efficienza/routing.
  - Setup section aggiornato: entry point operativo = Azure gpt-5.4-mini, default codice = locale, future = Claude
    MCP.
  - Frontmatter status e tags aggiornati.
  - `index.md`: updated timestamp.
  - `log.md`: questa voce.

## [2026-05-29] record | Tappa 04 — adattatore Semantic Kernel + eval a 3 motori su Azure gpt-5.4-mini

- **Implementazione Semantic Kernel (framework 2/3):** `04-agentic-rag/sk_app.py` (NUOVO) — kernel SK con
  `ChatCompletionAgent` + `FunctionChoiceBehavior.Auto()`. I 6 tool da `tools.py` sono esposti come
  `@kernel_function` nel plugin `RagTools`. Auto-invocation tracciato via filtro `AUTO_FUNCTION_INVOCATION`.
  Backend: `RAG_BACKEND=azure` → `AzureChatCompletion` (endpoint v1, parsing manuale di `/openai/v1`);
  locale → `OpenAIChatCompletion` verso Ollama `/v1`.
- **Esecuzione eval (9 task × 3 motori) su Azure gpt-5.4-mini:**
  - vanilla: 9/9 cited, 9/9 tool_ok, 2.7 steps medi, 3.2 tools medi.
  - AutoGen: 9/9 cited, 7/9 tool_ok, 2.7 steps medi, 3.4 tools medi.
  - **sk**: 9/9 cited, 8/9 tool_ok, 5.0 steps medi ⚠️ APPROSSIMATO, 4.0 tools medi.
- **Lettura onesta (3 motori):**
  (a) **Correttezza fattuale 9/9 per tutti** — gpt-5.4-mini satura `cited`; segnale discriminante =
  efficienza/routing (tool_ok, tool medi).
  (b) **SK più verboso:** media tool 4.0 (vs vanilla 3.2, AutoGen 3.4); picchi fino a 10 su query-param-codedoc,
  8 su httpexception-usage. SK ripete il loop di auto-invocation più che gli altri (design concretamente diverso).
  (c) **Metrica `steps` per SK approssimata:** SK non espone i confini dei turni LLM (loop opaca) → steps ≈
  num_tool + 1, non è paragonabile a vanilla/AutoGen. Metrica robusta = tool_medi: vanilla 3.2 < AutoGen 3.4 < SK 4.0.
  (d) **Tool_ok:** vanilla 9/9 > SK 8/9 > AutoGen 7/9. Tutti citano i file; divergono sul percorso. SK ha 1 routing
  subottimale (su task diverso da vanilla/AutoGen).
  (e) **Pattern SK:** investigazione più profonda per compensare (search_code → who_calls → related_docs → search_docs).
  Trade-off design: SK più verboso, vanilla più parsimonioso, AutoGen nel mezzo.
- **Learning:** SK con `ChatCompletionAgent + Auto()` è interessante per task multi-hop complessi (cerca profondità),
  meno efficiente per localizzazione diretta (overhead di auto-invocation). Vanilla è il baseline leggibile.
- **Test aggiornato:** `tests/test_agentic.py::test_sk_adapter_costruibile` (free, `importorskip`);
  suite **21 passed, 1 skipped**.
- **Requirements:** `semantic-kernel>=1.36.0` aggiunto.
- **Docs:**
  - `04-agentic-rag/README.md`: checklist SK completato.
  - `DEMOS.md`: sezione 04c (3 motori, comando, caveat passi SK).
  - `04-agentic-rag/ESEMPI-agentic.md`: rigenerata da `evaluate.py --render-from` (gratis, cache eval_results.json).
- **Wiki aggiornato:**
  - `experiments/04-agentic-rag.md`: sezione "Adattatore Semantic Kernel" nuova; "Eval comparativa" espansa
    a 3 motori con tabella, lettura onesta su fattualità/efficienza/steps approssimato, learning pattern SK.
    Frontmatter status → "vanilla + AutoGen + SK + eval a 3 motori; LangGraph + MCP da fare".
    Prossimi passi riprioritizzati (SK completato, LangGraph 3°, MCP).
  - `index.md`: riga 04 stato aggiornato, `updated: 2026-05-29`.
  - `log.md`: questa voce.

## [2026-05-29] record | Tappa 04 — adattatore LangGraph + confronto a 4 motori (chiusi i 3 framework)

- **Implementazione LangGraph (framework 3/3):** `04-agentic-rag/langgraph_app.py` (NUOVO) — workflow ReAct
  via `create_react_agent(model, tools, prompt)` (adattatore prebuilt LangGraph). Tool esposti con decoratore
  `@tool` di `langchain_core`; confronto a **parità strumenti/prompt** vs vanilla/AutoGen/SK. Trace ricavata
  da `tool_calls` degli `AIMessage`. Modello via `RAG_BACKEND`: Azure gpt-5.4-mini oppure Ollama llama3.1.
- **Eval a 4 motori (9 task × 4) su Azure gpt-5.4-mini:**
  - vanilla: 9/9 cited, 9/9 tool_ok, 2.8 passi, 3.3 tools medi.
  - AutoGen: 9/9 cited, 8/9 tool_ok, 2.8 passi, 3.7 tools medi.
  - **sk**: 9/9 cited, 8/9 tool_ok, 5.0 passi (approssimato), 4.0 tools medi.
  - **langgraph**: 9/9 cited, 7/9 tool_ok, 2.8 passi, 3.3 tools medi.
- **Lettura onesta (4 motori):**
  - **Correttezza fattuale 9/9 per TUTTI** — gpt-5.4-mini satura `cited`; segnale discriminante = efficienza/routing (tool_ok, tool medi, passi).
  - **LangGraph è snello come vanilla:** 3.3 tool medi, 2.8 passi reali. ReAct prebuilt rende l'orchestrazione concisa.
  - **Efficienza ordinata:** vanilla 3.3 ≈ LangGraph 3.3 < AutoGen 3.7 < SK 4.0. (SK +21% tool-call vs vanilla.)
  - **Routing (tool_ok):** vanilla 9/9 > AutoGen 8/9 ≈ SK 8/9 > LangGraph 7/9. Vanilla è il più stabile.
  - **Passi reali (vanilla/AutoGen/LangGraph):** tutti 2.8 turni. SK non è paragonabile (loop opaca).
- **Learnings:**
  - LangGraph `create_react_agent` implementa il ReAct pattern sottostante di vanilla; reduce boilerplate.
  - Su modello forte, `cited` satura; il segnale è efficienza/routing. Nessun motore dominante: vanilla/LangGraph per parsimonia,
    AutoGen per equilibrio, SK per investigazione profonda.
  - Merge incrementale eval: `--engines langgraph` esegue solo LangGraph (9 run), merge con eval_results.json precedente
    (conserva vanilla/AutoGen/SK). Evita ri-spendere token su 27 run, risparmio 75%.
- **Rigenerate eval_results.json + ESEMPI-agentic.md** con 4 motori (merge: solo 9 run di langgraph eseguiti,
  altri 27 da cache).
- **Requirements:** `langgraph>=1.2`, `langchain-openai>=1.2` aggiunte.
- **Test:** `tests/test_agentic.py::test_langgraph_adapter_costruibile` (free, `importorskip`);
  suite **22 passed, 1 skipped** (totale aggiornato).
- **Docs:**
  - `04-agentic-rag/README.md`: checklist 3 framework completati, prossimo = MCP server.
  - `DEMOS.md`: sezione 04d (4 motori, merge, --no-merge flag).
  - `04-agentic-rag/ESEMPI-agentic.md`: rigenerata (4 motori).
- **Wiki aggiornato:**
  - `experiments/04-agentic-rag.md`: sezione "Adattatore LangGraph" nuova; "Eval comparativa" espansa a 4 motori
    con tabella, lettura onesta su fattualità (9/9 tutti), efficienza/routing Delta. Sezione "Merge incrementale eval"
    con flag `--engines` e `--no-merge`. Frontmatter status → "vanilla + 3 framework (AutoGen/SK/LangGraph) + eval a 4 motori
    completati; MCP server prossimo". Prossimi passi riorganizzati (framework chiusi, MCP next).
  - `index.md`: riga 04 stato aggiornato con "vanilla + 3 framework ... completati; MCP server prossimo".
    `updated: 2026-05-29 (Tappa 04 — adattatore LangGraph + confronto a 4 motori chiusi i 3 framework)`.
  - `log.md`: questa voce.

## [2026-05-29] record | Tappa 04 COMPLETA — server MCP per agente Claude

- **Implementazione server MCP:** `04-agentic-rag/mcp_server.py` (NUOVO) — **Model Context Protocol server** basato su
  `FastMCP` (pacchetto `mcp>=1.27.1`, transport stdio). Espone **6 tool di retrieval**:
  - `search_code(query, k)`, `search_docs(query, k)`, `search_combined(query, k)` — ricerca ibrida.
  - `find_symbol(name)`, `who_calls(name)`, `related_docs(name)` — navigazione grafo AST e relazioni doc.
  
  Schema/descrizione generati da docstring + type hint. Backend/embeddings seguono `RAG_BACKEND` del `.env`
  (entry point: Azure gpt-5.4-mini + text-embedding-3-large; le ricerche dense sono a pagamento in modalità azure).

- **Registrazione MCP:** `.mcp.json` (NUOVO, root del repo) — configurazione del server per Claude Code:
  comando `.venv/Scripts/python.exe`, args `04-agentic-rag/mcp_server.py`, env `PYTHONPATH=.`.
  Una volta presente, Claude Code ha accesso nativo ai 6 tool e orchestra il loop LLM.

- **Test:** `tests/test_agentic.py::test_mcp_server_espone_i_tool` — test in-process (no stdio) che verifica
  la registrazione dei 6 tool con schema via `list_tools()`. Suite aggiornata: **23 passed, 1 skipped**.

- **Verifica end-to-end:** test client stdio reale (mcp.client.stdio + ClientSession): handshake `initialize` OK,
  `list_tools()` → 6 tool con schema (query+k / name), `call_tool find_symbol("APIRouter")` →
  `"fastapi/routing.py:1005  class APIRouter"` (risposta corretta dal grafo AST).

- **Significato architetturale:** realizza il punto d'arrivo dell'[[architettura-target]] (**MCP-first**). Il workspace
  ora offre 4 fronti di consumo dello stesso backend di retrieval: vanilla orchestrator, AutoGen/SK/LangGraph,
  **MCP server** (superficie finale), e future surfaces. Il riuso di `shared/retrieval.py` come **unico layer di tool**
  senza duplicazione ha confermato il pattern di design.

- **Wiki aggiornato:**
  - `experiments/04-agentic-rag.md`: sezione "Server MCP (framework 4/4 — superficie finale)" nuova con cosa/come/verifica/learning,
    status → **COMPLETATO**, prossimi passi riprioritizzati (Tappa 04 chiusa; follow-up = igiene corpus, task eval
    discriminanti, entity_types custom, query planning context-aware).
  - `index.md`: riga 04 stato → "completato (vanilla + AutoGen/SK/LangGraph + eval 4 motori + server MCP)";
    updated timestamp; cenno MCP in sezione Demo & Test.
  - `log.md`: questa voce.

**Tappa 04 COMPLETATA.** L'[[architettura-target]] dual-RAG (ingestion code-aware, 4 retriever, orchestrazione LLM,
MCP-first) è realizzata operazionalmente.

## [2026-05-29] record | SpecKit — 9 subagent fedeli a skill canonici per phase-gate di produzione

- **Creati 9 subagent SpecKit** in `.claude/agents/speckit-<fase>.md`: **constitution, specify, clarify, plan, tasks,
  analyze, checklist, implement, taskstoissues**. Primo tassello operativo della **fase di produzione** (assettizzazione Sertor).
- **Architettura:** ogni agente è **esecutore fedele** del rispettivo skill canonico in `.claude/skills/speckit-<fase>/SKILL.md`:
  system prompt rimanda allo SKILL e lo esegue; note aggiungono solo adattamenti workspace (CLAUDE.md policy, convenzioni).
  → Evita duplicazione/drift. Aggiornamento dello skill riflette automaticamente negli agenti.
- **Delega git:** Git MAI eseguito dai subagent (coerente con policy prototipo→produzione di CLAUDE.md);
  ogni agente chiude con **brief di commit** (speckit-plan suggerisce anche branch). Commit delegato a configuration-manager.
- **Niente interazione diretta:** decisioni critiche tornano nel report come `[NEEDS CLARIFICATION]` formattate
  (tabella opzioni) per il flusso principale; il flusso non blocca su domande.
- **Dogfooding MCP sertor-rag:** speckit-plan, speckit-analyze, speckit-implement hanno i 6 tool MCP (search_code/docs/combined,
  find_symbol, who_calls, related_docs) per studiare codebase Sertor durante planning/analysis. speckit-analyze è SOLA LETTURA.
- **Modelli:** sonnet per fasi sostanziali (constitution/specify/clarify/plan/tasks/analyze/implement),
  haiku per ausiliarie (checklist, taskstoissues). Equilibrio efficienza/qualità coerente con budget.
- **Stato:** flusso operativo prototipo già definito (Constitution → Specify → Clarify → Plan → Tasks → Analyze → Checklist
  → Implement → TasksToIssues → configuration-manager per git). Aperto: integrare hook `before_specify` per branch automatica;
  collegare spec ↔ wiki; transizione rami/PR in produzione.
- **Wiki aggiornato:**
  - `wiki/tech/speckit.md` (NUOVO): descrizione SpecKit come framework di governance, architettura agenti, principi design,
    flusso operativo, policy git, integrazione wiki.
  - `wiki/index.md`: aggiunto link in sezione Tecnologie.
  - `wiki/log.md`: questa voce.

---

## [2026-05-29] record | Fusione dual-RAG get_context + confronto vs LLM (FUSIONE.md)

- **Implementazione fusione deterministica:** funzione `get_context(target, semantic_docs=False)` in `shared/retrieval.py`
  unisce definizione + codice (righe) + chiamanti + doc collegati, sfruttando **grafo AST (mentions) e metadati
  qualname/start_line/end_line** del chunking tree-sitter. Zero token LLM, deterministico, <10ms, istantaneo.
- **Modifiche:** `02-hybrid-reranking/hybrid.py` (_hit) espone `symbol/qualname/start_line/end_line` (il "bridge"
  verso grafo/fusione che prima veniva scartato). `04-agentic-rag/mcp_server.py` aggiunto **7° tool MCP** `get_context`.
- **Confronto quantitativo:** `04-agentic-rag/compare_fusion.py` (NUOVO) + `FUSIONE.md` (NUOVO, generato) + 
  `fusion_results.json` (cache) confrontano dual-RAG (get_context) vs LLM vanilla su 4 simboli.
  **Risultato onesto:** copertura fattuale ~98% entrambi; valore dual-RAG = **costo zero, determinismo, latenza**
  (1 call LLM-free vs 3–6 call LLM, 0 token vs 200–400, <10ms vs 1–3s, 100% vs ~95% deterministico).
- **3 punti di interazione codice↔doc:** (1) search_combined = co-ranking; (2) related_docs = link mention;
  (3) get_context = fusione vera (nuovo). Mini-diagramma in [[architettura-attuale]].
- **Test aggiornato:** `tests/test_agentic.py` + test `get_context` free + test MCP aggiornato a 7 tool.
  Suite: **24 passed, 1 skipped**.
- **Learning:** la fusione "forte" codice↔doc prima era **delegata all'agente**; ora è **infrastrutturale deterministica**,
  abilitata dal bridge metadati strutturali (qualname/righe). Su modello forte il valore è efficienza/ripetibilità, non completezza.
- File toccati: `shared/retrieval.py` (get_context), `02-hybrid-reranking/hybrid.py`, `04-agentic-rag/mcp_server.py`
  (7° tool), `04-agentic-rag/compare_fusion.py` (NUOVO), `04-agentic-rag/FUSIONE.md` (NUOVO, generato),
  `tests/test_agentic.py`, `DEMOS.md` (24 test, 7 tool), `wiki/experiments/04-agentic-rag.md`,
  `wiki/index.md`, `wiki/log.md`.

## [2026-05-29] record | Architettura as-built documentata + backlog di produzione (caching rinviato)

- Creata pagina di sintesi **`syntheses/architettura-attuale.md`** (NUOVO) — documento complementare
  a [[architettura-target]]: diagramma mermaid dello stato realizzato (tappe 01–04 complete), descrizione
  a strati (ingestion → indici → facade shared/retrieval → consumatori Tappa 04).
- **Diagramma as-built:** corpus raw/fastapi/ → loaders + tree-sitter + embeddings 3-provider → 3 indici
  (Chroma dense, BM25 sparse, AST graph) + GraphRAG separato → facade unica `shared/retrieval.py` (6 tool) →
  4 orchestratori LLM (vanilla/AutoGen/SK/LangGraph) + server MCP (`mcp_server.py`) + client Claude Code.
  Config/.env trasversale governa RAG_BACKEND e provider LLM.
- **Sezione "Caching — stato e backlog di produzione":** tracciati 3 item rinviati alla produzione per policy
  SpecKit/branch: (1) cache embedding query in shared/embeddings.py; (2) cache risposte LLM (SQLite, run agent
  riproducibili); (3) tracciare/ottimizzare Azure prompt-caching (cached_tokens in shared/llm.py). Più: igiene
  corpus (blob base64), eval multi-hop + media multi-run, transizione SpecKit+branch/PR.
- Aggiornato **`wiki/index.md`**: aggiunto link a nuova pagina nella sezione Sintesi + timestamp updated.
- Aggiornato **`wiki/syntheses/architettura-target.md`**: added backlink in § "Concerns trasversali" che rimanda
  a [[architettura-attuale]] per il backlog di produzione.
- File toccati: `wiki/index.md`, `wiki/syntheses/architettura-target.md`, `wiki/syntheses/architettura-attuale.md` (creato),
  `wiki/log.md`.

## [2026-05-30] record | Requirements Engineering — fase autonoma + assets (skill + subagent)

- **Decisione:** creata una fase **STANDALONE di Requirements Engineering a MONTE del design**, agnostica rispetto a SpecKit
  o qualunque framework di governance a valle. Motivazione confermata da deep-research: i framework spec-driven non coprono
  bene l'elicitazione e formalizzazione dei requisiti.
- **Artefatti creati:**
  - `.claude/skills/requirements/SKILL.md` — workflow **interattivo** (nel flusso principale): guida step-by-step per
    elidere un progetto, genera bozza di `requirements/<short-name>/requirements.md`.
  - `.claude/agents/requirements-analyst.md` — subagent **delegabile** (Sonnet, non interattivo): prende brief lordo,
    esegue analisi profonda con access a tool MCP sertor-rag (dogfooding), output = report con EARS + domande aperte
    `[DA CHIARIRE]` + tabella opzioni per il flusso.
- **Formato output:** cartella `requirements/<short-name>/` con `requirements.md` contenente: Contesto & Problema, Obiettivi & Criteri,
  Stakeholder, Ambito In/Out, **Requisiti Funzionali (EARS atomici)**, Requisiti Non-Funzionali, Vincoli/Assunzioni/Dipendenze,
  Rischi, Prioritizzazione MoSCoW, Domande Aperte.
- **Metodologia EARS (Alistair Mavin):** 5 pattern (Ubiquitous, State-driven, Event-driven, Optional, Unwanted Behaviour) + Complex.
  Ogni requisito con ID REQ-NNN, atomico, testabile, tracciabile.
- **Principio di disaccoppiamento:** la fase è agnostica; specifica a valle (SpecKit, IEEE 830, etc.) legge `requirements/<short-name>/`
  senza accoppiamento per nome. Eventuale nota in SpecKit rimanda a questa fase come prerequisito.
- **Wiki aggiornato:**
  - `wiki/tech/requirements-engineering.md` (NUOVO): descrizione fase, motivazione, formato output, EARS overview, assets (skill/subagent),
    principio disaccoppiamento, possibile estensione tassonomia di dominio.
  - `wiki/concepts/ears-methodology.md` (NUOVO): approfondimento EARS, 5+1 pattern, proprietà (atomico, unambiguo, formale,
    testabile, tracciabile), design patterns (gerarchia, acceptance criteria, linking a test & code), example set RAG, best practice.
  - `wiki/index.md`: aggiunto link a `concepts/ears-methodology.md` in sezione Concetti; aggiunto link a `tech/requirements-engineering.md`
    in sezione Tecnologie (tra Stack e SpecKit).
  - `wiki/log.md`: questa voce.
- **Intento strategico:** requirements engineering è un **asset permanente** del workspace, riusabile per ANY progetto (Sertor, client,
  research), indipendente da fasi di design/governance. Complementare (NON subordinato) a SpecKit.

## [2026-05-30] record | Flusso end-to-end epica → implementazione (diagramma)

- Creata pagina di sintesi **`wiki/syntheses/flusso-requisiti-implementazione.md`** (NUOVO) — documenta il flusso completo
  dall'EPICA (requisito alto livello) all'implementazione finale, articolato su **due strati disaccoppiati**:
  
  1. **Fase REQUISITI** — skill propria `/requirements` (strumento workspace, basato su [[ears-methodology]], agnostico rispetto a SpecKit).
     Output: epic.md (visione, ambito, backlog MoSCoW) + requirements.md per feature (requisiti EARS atomici).
  
  2. **Pipeline SpecKit** — framework di governance (9 fase canoniche per feature): specify → clarify? → plan → tasks → checklist? → analyze → implement.
     Il disaccoppiamento è esplicito: `/requirements` genera requisiti, l'utente/orchestratore legge `requirements.md` e lo passa a `/speckit-specify`.
  
- **Diagramma mermaid:** mostra il flusso completo con i due subgraph REQ e SK, la constitution come governance trasversale, e la delega
  al configuration-manager (git) e wiki-keeper (doc).
  
- **Sezione "Come leggerlo":** spiega punto per punto (① requisiti, ② SpecKit, ③ output finale, trasversali: constitution/git/wiki).
- **Backlink aggiunti:** [[requirements-engineering]], [[ears-methodology]], [[speckit]].
- **Index.md aggiornato:** link alla nuova pagina in sezione Sintesi, timestamp updated → 2026-05-30.
- **Log.md aggiornato:** questa voce.

**Significato:** il workspace ora ha una **mappa visuale completa** del flusso da idea a ship (requisiti → spec → piano → task → implementazione),
con chiarezza su quando e come i due pilastri (requisiti e SpecKit) si connettono.

## [2026-05-30] ingest | Panorama tools Requirements Engineering (ricerca avversariale mid-2026)

- **Deep-research completata:** analisi del gap SpecKit (issue #1527 aperta gen 2026, no maintainer response), confronto strumenti
  (BMAD-METHOD v6.8.0 ~48k★ ma +token-heavy; Kiro AWS EARS-native; PRD Creator lightweight; OpenSpec tool-agnostico;
  speckit-agents PoC sperimentale). EARS (Alistair Mavin, IEEE RE09) confermato come metodologia consolidata per requirements atomici.
- **Feedback community verificato:** BMAD davvero pesante (issue #1235 "Excessive Token Usage" rivendica −74% da v6), Kiro fuori IDE non dimostrato,
  "requisiti migliori o boilerplate?" = domanda aperta (no benchmark indipendente), gap SpecKit riconosciuto utenti non maintainer.
- **Decisione:** workspace costruisce uno **strumento proprio standalone** (skill `/requirements` + subagent `requirements-analyst`), basato su EARS,
  agnostico rispetto a SpecKit a valle. Non dipende da BMAD (costo), da Kiro (IDE-bound), da aggregatori (ritardo).
- **Artefatto creato:** `wiki/sources/requirements-tooling-landscape.md` (NUOVO) — digest ricerca, gap evidence, panorama tools (5 candidati),
  EARS overview, feedback community, decisione Sertor. Frontmatter: type: source, tags [requirements, speckit, ears, tooling, ricerca].
- **Wiki aggiornato:** `wiki/index.md` sezione Fonti, `wiki/log.md` questa voce.
- **Learning:** il panorama è frammentato (no dominante), community riconosce il gap, la nostra scelta di uno strumento proprioè allineata
  a bisogni reali (non over-engineering).

## [2026-05-30] record | Costituzione di Progetto per Fase Produzione — Proposta

- **Proposta di costituzione creata:** `wiki/syntheses/costituzione-produzione-proposta.md` (NUOVO) — livello sopra CLAUDE.md, principi
  non-negoziabili per governance SpecKit in produzione. **Principio cardine:** "Il prototipo è EVIDENZA, non PROGETTO" (scelte design
  tappe 01–04 sono exploration validate, NON ereditate; plan.md decide cosa ereditare/rimpiazzare/abbandonare).
- **8 principi core** (how-agnostici): I. Repo-agnostico & riusabile; II. Local-first & provider-agnostico; III. YAGNI (semplicità giustificata);
  IV. Qualità da misure non claim; V. Sicurezza segreti/artefatti; VI. Costo & determinismo consapevoli; VII. Governance via SpecKit (branch/PR);
  VIII. Prototipo è evidenza (ripetuto).
- **Decisioni aperte da ratificare:** (1) target Microsoft/Azure vs cloud-agnostico (Opzione B attualmente); (2) data ratifica (fine Tappa 04);
  (3) numero principi (5 core vs 8 estesi); (4) rigore test (smoke+eval pragmatico vs TDD — Opzione A attualmente).
- **Spunti RAG specifici notati:** groundedness/citazione obbligatoria, qualità retrieval valutata, provenienza corpus pulita,
  governance agente (limiti passi, verifica prima di rispondere).
- **Procedura ratifica:** review stakeholder → discussione → firma formale (data, versione) → upload `.specify/memory/constitution.md` → backlink.
  Fino a ratifica, è working document per planning.
- **Wiki aggiornato:** `wiki/syntheses/costituzione-produzione-proposta.md` (NUOVO), `wiki/index.md` sezione Sintesi, `wiki/log.md` questa voce.
- **Significato:** formalizza il passaggio prototipo→produzione; SpecKit Constitution Check avrà rubrica esplicita da questo documento.

## [2026-05-30] record | TODO: wiki auto-manutentore (spider / wiki-lint)

- **TODO registrato** nel "Backlog di produzione" di `wiki/syntheses/architettura-attuale.md` (sezione #### Wiki & Tooling, item 4).
- **Scopo:** realizzare un passaggio sistematico di manutenzione del wiki che:
  - enumera tutte le pagine e valida i `[[link]]` (trovare rotti, backlog mancanti);
  - rigenera `index.md` a partire dal filesystem;
  - rileva pagine orfane, contraddizioni e claim superati (lint sull'intero grafo);
  - distilla "raw conversation → wiki concept" in modo automatico.
- **Decisione aperta:** implementarla come skill on-demand `wiki-lint` oppure automatico via hook/routine schedulata.
  (Nota: il vecchio Stop hook bloccante è stato rimosso di proposito; l'unico hook attivo oggi è SessionStart che carica lo stato del wiki nel contesto.)
- **Contesto:** mantenimento wiki oggi è on-demand (comando `/wiki` con operazioni record/ingest/query/lint, + agente wiki-keeper su delega).
  L'aggiunta di uno spider sistematico allinea il wiki a una vera "evolving knowledge base" con audit trail completo.
