---
title: 03 GraphRAG (A+C — code graph leggero + Microsoft GraphRAG)
type: experiment
tags: [graphrag, code-graph, ast, networkx, microsoft-graphrag, multi-hop, query]
created: 2026-05-28
updated: 2026-05-28
status: completato (A + C + query prova eseguita)
sources: [https://github.com/fastapi/fastapi, https://github.com/microsoft/graphrag]
---

# 03 GraphRAG (A — code graph leggero)

## Obiettivo
Costruire un **code knowledge graph** dal codice (AST) per query **strutturali** e
**multi-hop** (chi-chiama, dove-definito, doc collegati) complementari al retrieval
vettoriale di [[01-baseline]] / [[02-hybrid-reranking]]. Vedi [[architettura-target]].
Scelta concordata: **A ora** (grafo custom leggero), **C in seguito** (Microsoft GraphRAG) per confronto.

## Setup
- **Sorgente:** [[fastapi]] (`fastapi/` + `docs_src/` via AST; `docs/en/` per i link doc).
- **Grafo (`networkx`):** nodi module/class/function/method/doc; archi
  `contains` (struttura), `imports` (modulo→modulo), `calls` (func→func),
  `inherits` (classe→base), `mentions` (doc→simbolo, per menzione del nome).
  Risoluzione per nome **intra-progetto** (best-effort).
- **Codice:** `03-graphrag/` (`build_graph.py`, `graph_query.py`, `evaluate.py`).

## Risultati
- **Grafo:** 1917 nodi (502 module, 732 function, 312 class, 218 method, 153 doc) /
  4868 archi (1256 contains, 1166 calls, 1651 mentions, 579 imports, 216 inherits).
- **Definizione@1 sulle query a simbolo: 6/8 (0.75).**

| simbolo | def@1 | #callers | #docs |
|---------|:-----:|---------:|------:|
| OAuth2PasswordBearer | OK | 0 | 4 |
| OAuth2PasswordRequestForm | OK | 0 | 4 |
| APIRouter | OK | 1 | 10 |
| BackgroundTasks | OK | 1 | 3 |
| HTTPException | OK | 69 | 9 |
| jsonable_encoder | OK | 15 | 9 |
| JSONResponse | — | 0 | 0 |
| WebSocketDisconnect | — | 0 | 0 |

## Learnings
- **Forza del grafo:** risposte **precise e strutturali** che il vettoriale non dà —
  definizione con `path:lineno`, call-graph (es. `HTTPException` → 69 chiamanti) e
  collegamento doc↔codice (es. `APIRouter` → 10 doc).
- **Limite onesto (re-export):** `JSONResponse` e `WebSocketDisconnect` non risultano
  "definiti" perché sono **re-esportati da Starlette** (`from starlette... import ...`):
  l'AST li vede come import, non come `ClassDef`. Servirebbe risoluzione di alias/re-export
  (o un grafo arricchito via LLM come Microsoft GraphRAG).
- **Nessuna ricerca semantica:** il grafo **non** gestisce le query in linguaggio naturale.
  È **complementare**, non sostitutivo, del retrieval vettoriale/ibrido (che infatti aveva
  trovato `JSONResponse` via testo).
- **Implicazione → fusione:** vettoriale/ibrido per fuzzy/NL e re-export; grafo per
  struttura/navigazione precisa. La combinazione è il cuore del dual-RAG target.

## Stima costi Tappa 3C (Microsoft GraphRAG)
Dimensione corpus misurata (~4 char/token): **completo ~590K token** (229K codice + 361K doc);
**subset** (`docs/en/docs/tutorial` + `fastapi/security`) **~90K token**.

L'indicizzazione GraphRAG consuma in chiamate LLM **circa 5–10× la dimensione del corpus**
(estrazione entità/relazioni per chunk + gleaning, summary delle descrizioni, community report).
Assunzioni: `chunk_size≈1200`, `max_gleanings=1`, ~80% input / 20% output.

| scenario | corpus | LLM token stimati (I/O) | costo modello *mini* | costo modello *4o* |
|----------|-------:|------------------------:|---------------------:|-------------------:|
| subset | ~90K | **~0.6–1.2M** | ~$0.15–0.30 | ~$2–4 |
| completo | ~590K | **~3.5–7.5M** | ~$1–2 | ~$15–30 |

Embeddings (text-embedding-3): trascurabili (~$0.02–0.1). Costi indicativi su prezzi pubblici
(*mini* ≈ $0.15/$0.60 per 1M in/out; *4o* ≈ $2.5/$10) — su Azure variano col listino del deployment.
**Incertezza ±2×**: dipende molto da `chunk_size` (300 → ~5× chunk e costo maggiore), gleanings,
e da quante entità/community emergono. Il tempo è limitato dal rate limit (TPM) del deployment.
**Approccio consigliato:** partire dal subset con un modello *mini*, leggere il consumo reale
dai log GraphRAG, poi estrapolare al corpus completo.

## Nota setup Tappa 3C — env isolato (non Docker)
Microsoft `graphrag` richiede un **virtualenv dedicato**, separato dal `.venv` principale,
per conflitti di dipendenze: usa `graspologic` (Leiden) → `numba`, che tipicamente vuole
**`numpy < 2.x`**, mentre il nostro `.venv` ha **numpy 2.4** → conflitto diretto. Porta anche
`lancedb`, `pyarrow`, `pandas`, `fnllm`/`tiktoken` con pin stretti.
- Setup: `uv venv 03-graphrag/.venv-grag` + `uv pip install graphrag`, oppure `uv tool install graphrag`.
- Si usa **da CLI** (`graphrag init/index/query`): legge `raw/`, scrive artefatti **parquet**.
- Gli artefatti si **rileggono dal `.venv` principale** (pandas/networkx) per il confronto col grafo AST.
- Isolamento solo dei *pacchetti Python*, non dei dati (condivisi sul filesystem).

GraphRAG usa **sia un LLM (chat, costo dominante) sia un embedding (minore)** — config separata
(`llm` / `embeddings`). Opzioni provider:
- **Cloud (Foundry):** LLM `5.5-mini` + embedding `text-embedding-3-small` → veloce, ~$0.20 sul subset.
- **Locale (no API):** Ollama via endpoint **OpenAI-compatible** `http://localhost:11434/v1`,
  LLM `qwen3:30b` + embedding `nomic-embed-text` → costo zero/privacy, più lento; la qualità
  d'estrazione dipende dal modello (i piccoli spesso danno output malformato). Claude Haiku
  resta un'API (non locale) e non è nativo in GraphRAG.
- Idea: eseguire il subset in **entrambe** le varianti e confrontare qualità/tempo/costo.

**Scelta modelli (qualità/prezzo).** Per GraphRAG conta il prezzo/token (estrazione ad alto
volume) e l'affidabilità sull'output strutturato → i *mini* OpenAI sono il punto giusto:
- Cloud consigliato: **`5.5-mini`** per l'estrazione + **`text-embedding-3-small`** (eguaglia
  quasi `-large`, vedi [[01-baseline]]). Per la 3C **non serve deployare altro**.
- Ottimizzazione: GraphRAG supporta **modelli diversi per step** → `5.5-mini` per l'estrazione
  per-chunk + un modello più forte (`5.4`) solo per i **community report** (poche chiamate, alto valore).
- Alternative catalogo: Cohere Command R (RAG/structured, buono); Phi-4 (economico ma rischio
  output malformato); Llama 3.3 70B (open). La Tappa 4 (agentic) vorrà invece un modello forte
  per il planning (esigenza opposta).

## Tappa 3C — Microsoft GraphRAG eseguita

### Setup
- **Ambiente:** venv isolato `03-graphrag/.venv-grag` (Python 3.12, uv), GraphRAG 3.1.0 installato.
  Motivazione: GraphRAG usa `graspologic`→`numba` che richiede `numpy < 2.x`; il `.venv` principale
  ha `numpy 2.4` (conflitto). Carica inoltre `lancedb`, `pandas`, `fnllm`/`tiktoken` con pin stretti.
  **Nota importante:** il conflitto con numpy è il **motivo principale** dell'env separato, non per
  evitare contaminazione diretta nel codice principale ma per proteggere dalle incompatibilità di
  stack di dipendenze.

- **Configurazione GraphRAG 3.1 (nuovo schema vs vecchie versioni):** il config usa ora
  `completion_models:` e `embedding_models:` (non più `llm:` / `type:`). Ogni modello specifica
  `model_provider: azure` e delega l'LLM al pacchetto `graphrag_llm` che usa **litellm** sotto.
  - Chat: `gpt-5.4-mini` (deployment omonimo su Azure OpenAI).
  - Embedding: `text-embedding-3-small`.
  - Endpoint e key riusati da quelli embedding (Azure Foundry), passati via env var
    `${GRAPHRAG_API_BASE}` / `${GRAPHRAG_API_KEY}` da `03-graphrag/grag/.env` (gitignored).
  - API version: `2024-10-21`.

- **Progetto GraphRAG:** `03-graphrag/grag/` con `settings.yaml`, 13 prompt di default,
  `.env` (gitignored). Input staged in `grag/input/` (50 doc tutorial `.md` + 7 `fastapi/security/*.py`).
  Helper script `03-graphrag/check_config.py` (validazione offline) e `03-graphrag/summarize.py`
  (token + struttura grafo).

### Ostacoli risolti
1. **CLI hang su `litellm` import:** il CLI `graphrag` tenta di scaricare cost-map dal web
   all'avvio; con rete sandbox ristretta → timeout infinito. **Fix:** env var
   `LITELLM_LOCAL_MODEL_COST_MAP=True` (forza la mappa bundled locale). **Workaround init:**
   chiamare `graphrag.cli.initialize.initialize_project_at` da Python instead del CLI.

2. **Pattern file input:** `input: type: text` di default matcha solo `*.txt` → 0 documenti letti.
   **Fix:** `file_pattern: '.*\.(md|py)$$'` (doppio dollaro perché GraphRAG interpola env con
   `string.Template`, che usa `$` come escape; serve escaping anche nei commenti).

### Risultati token reali (ground truth via `metrics` nativo di GraphRAG 3.1)
GraphRAG 3.1 espone `writer: file` → jsonl in `grag/metrics/` aggregati ad atexit con dettagli
per modello.

- **Chat `gpt-5.4-mini`** (estrazione grafo + community reports):
  - Chiamate: 1098; fallite: 0; **retry: 949 (retry_rate 46%)** ← forte throttling TPM del deployment.
  - Token: prompt 1.469M + completion 496K = **1.965M token**.
  - Tempo: extract_graph 557s, community_reports 250s.

- **Embedding `text-embedding-3-small`:**
  - Chiamate: 112; token: **366K**.

- **TOTALE: ~2.33M token** (1.836M prompt + 0.496M completion).
  - Costo da registry litellm: **~$3.34** (chat $3.33 + embed $0.007 arrotondati).
    Nota: litellm prezza `gpt-5.4-mini` ~$0.75/$4.50 per 1M (in/out); il costo reale dipende dal
    listino del deployment Azure dell'utente. **I TOKEN sono esatti**, il costo è derivato.
  - Tempo wall: ~14 min (834s total); embeddings 26s.

### Struttura del grafo prodotto
Output parquet in `grag/output/`:
- **57 documenti, 102 text_units.**
- **1090 entità, 1779 relazioni, 239 community + 239 community report** (con summary NL).
- **Attenzione:** NON confrontabile numericamente con 3A (3A: completo `fastapi/`+`docs_src/`;
  3C: solo subset tutorial+security).

**Distribuzione entità per tipo** (entity_types generici di default):
- EVENT 650, ORGANIZATION 355, PERSON 48, GEO 36, API 1.
- **Learning critico:** GraphRAG usa i **type di default pensati per news/prosa** (organization/person/geo/event);
  ha forzato concetti tecnici in categorie sbagliate: FASTAPI/PYDANTIC/OAUTH2/HTTPEXCEPTION → ORGANIZATION;
  OPENAPI/PATH OPERATION → EVENT. Per codice/doc tecnica serve **custom entity_types** + prompt tarato.

**Hub e relazioni semantiche:**
- Hub: FASTAPI (degree 311).
- Top relazioni (per weight): FASTAPI→PYDANTIC 257, →OPENAPI 199, →STARLETTE 112, →DEPENDS 73,
  →HTTPEXCEPTION 72.
- **Osservazione:** sono relazioni **semantiche/concettuali** che il grafo AST (3A) non poteva
  dare (es. FastAPI "si basa su" Starlette/Pydantic); l'AST le vedeva solo come import.

**Community report tematici** (sample):
- "FastAPI OAuth2 Authorization Utilities"
- "JWT and JSON Web Tokens Authentication Community"
- "FastAPI Request Body and Body Parameters"

### Confronto 3A vs 3C — learning chiave
| Aspetto | AST (3A) | GraphRAG (3C) |
|---------|----------|--------------|
| **Precisione strutturale** | ✓ deterministico (def/callers@path:lineno) | — ricerca semantica via NL |
| **Semantica/relazioni concettuali** | — niente | ✓ cattura relazioni "si basa su" ecc. |
| **Summary NL community** | — | ✓ tematico |
| **Costo** | zero (locale) | **denaro reale** (~$3.34 subset) |
| **Velocità** | rapido | lento (14 min subset; throttling TPM pesante) |
| **Tipizzazione entità** | N/A | generica (inadatta a codice tecnico) |
| **Determinismo** | ✓ | — dipende dalle retry LLM |

**Conclusione:** confermano la tesi della **fusione dual-RAG**: GraphRAG per navigazione
tematica/semantica + summary; grafo AST per struttura di codice precisa; vettoriale/ibrido
per fuzzy/NL. Nessuno è dominante.

### Confronto vs stima costi (Sezione precedente)
- **Stima:** 0.6–1.2M token LLM per il subset → ~$0.15–0.30.
- **Reale:** 1.965M token LLM (~1.6–3× sopra) → ~$3.34.
- **Motivo overstimate:** `summarize_descriptions` fa molte chiamate per entità/relazione + gleaning
  + community report (più alto volume dell'estrazione base). Inoltre `gpt-5.4-mini` non è prezzato
  come un "mini" economico in litellm (più costoso di gpt-3.5). La **stima 5–10× del corpus** era
  corretta, ma il modello scelto era sottodimensionato nei parametri di prezzo.

### Query di prova (global + local)
Eseguite due query di prova sul grafo della Tappa 3C via CLI:

**Comandi (riproducibili):**
```bash
export LITELLM_LOCAL_MODEL_COST_MAP=True
python -m graphrag query --root 03-graphrag/grag --method global "come gestisce FastAPI auth/security e quali componenti?"
python -m graphrag query --root 03-graphrag/grag --method local "cos'è OAuth2PasswordBearer?"
```
(Query è argomento POSIZIONALE in GraphRAG 3.1, non `--query`; argomenti dopo il path.)

**GLOBAL ("come gestisce FastAPI auth/security...")**
- Tipo di ricerca: sintesi tematica (map-reduce su 239 community).
- Qualità output: **eccellente**. Ha sintetizzato un testo coerente coprendo OAuth2 bearer, JWT (PyJWT/HS256/scopes), HTTP auth (Basic/Bearer/Digest), API key (header/query/cookie), OpenID Connect, hashing password (Argon2 + dummy-hash anti timing-attack), error handling HTTPException/401.
- Citazioni: `[Data: Reports (...)]` che riconducono ai community report originali.
- Token reali: **~21 chiamate LLM** (aggregate reduce), **~257K token** (248K prompt + 9K completion), **~$0.23**.
  - Motivo del costo: la global è un map-reduce su tutte le 239 community → moltiplicazione delle prompt.

**LOCAL ("cos'è OAuth2PasswordBearer?")**
- Tipo di ricerca: puntuale (nearest-neighbor su entità/relazioni, sintesi breve).
- Qualità output: **corretta e concisa**. Risposta accurata: subclass di OAuth2, estrae bearer da header Authorization, usa Depends()+tokenUrl→/token+OAuth2PasswordRequestForm, restituisce 401 se manca, e coglie che **non valida il token** (delegato al caller).
- Citazioni: Entities/Relationships/Sources nativi del grafo.
- Token reali: **1 chiamata LLM** (streaming, token non contati nel metrics di GraphRAG) + **1 embedding** (18 token) → **quasi gratis**.

**Token totale Tappa 3C finora:** Indexing $3.34 + Query ~$0.23 ≈ **~$3.57** (mini subset).

### Learning: entity_types generici non penalizzano il retrieval
Anche con entity_types di default (ORGANIZATION/EVENT/PERSON/GEO/API) **generici/sbagliati per il codice**, la qualità delle risposte della GLOBAL rimane alta. Motivo: GraphRAG si appoggia ai **community report testuali** (descrizioni NL delle entità + testo originale dei doc) e alle **relazioni**, non alle etichette di tipo. I tipi generici penalizzano la **navigazione-per-tipo** (filtrare entità ORGANIZATION), non il retrieval semantico.

Confronto vs Tappa 3A (AST):
- **AST (3A):** trovava `OAuth2PasswordBearer` dove è definito (dov'è nel file) + doc collegati, ma non lo spiegava (pura struttura).
- **GraphRAG (3C):** lo spiega in linguaggio naturale grounded su doc+codice + lo contextualizza nelle community (auth flow).
→ Conferma della **complementarità** e della tesi della **fusione dual-RAG** (AST + GraphRAG + vettoriale).

## Prossimi passi
- **Tuning entity_types:** ri-run con custom entity_types per codice tecnico (class/function/module/endpoint/exception/concept) + prompt specializzati per il contesto FastAPI.
- **Integrazione sistematica:** confronto AST ↔ GraphRAG ↔ vettoriale (fusion retrieval con RRF / LLM).
- **Tappa 04:** agentic RAG con AutoGen / Semantic Kernel.
