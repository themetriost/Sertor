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
