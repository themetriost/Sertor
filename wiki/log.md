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
