# DEMOS — test dimostrativi delle configurazioni RAG

Runbook riproducibile delle configurazioni esplorate (Tappe 01–03). Per ogni demo:
**scopo · prerequisiti · comando · output atteso · output osservato**.

La controparte automatica è la suite `tests/` (smoke test pytest): vedi
[§ Suite di test](#suite-di-test-pytest). Obiettivo (vedi [`CLAUDE.md`](CLAUDE.md)): tooling
**riproducibile e repo-agnostico** verso un toolset RAG portabile in un progetto enterprise.

## Prerequisiti generali

| Risorsa | Serve a | Come ottenerla |
|---|---|---|
| venv principale `.venv` | Tappe 01/02/03A | `uv venv .venv --python 3.12 && uv pip install -r requirements.txt` |
| indice Chroma `01-baseline/.index` | retrieval dense/hybrid | `python 01-baseline/index.py --provider all` |
| grafo AST `03-graphrag/.index/code_graph.graphml` | Tappa 3A | `python 03-graphrag/build_graph.py` |
| Ollama in esecuzione | embedding locale (provider `ollama`) | `ollama serve` + `ollama pull nomic-embed-text` |
| chiavi Azure in `.env` | provider `azure-*` (qualità migliore) | vedi `.env.example` |
| venv isolato `03-graphrag/.venv-grag` + artefatti `grag/output` | Tappa 3C | vedi [§ 3C](#3c--microsoft-graphrag) |

> Tutti i comandi si lanciano dalla **root del repo** con `PYTHONPATH=.` (i moduli usano `shared/`).
> Su Windows: `PYTHONPATH=. .venv\Scripts\python.exe <script> ...`.

---

## 01 — Baseline (dense vector retrieval)

**Scopo:** similarity search densa su Chroma, una collection per provider di embedding.
**Prerequisiti:** indice Chroma + un backend embedding (Ollama locale o Azure).

```bash
PYTHONPATH=. python 01-baseline/search.py "OAuth2 password bearer token authentication" --provider ollama -k 3
```

**Atteso:** 3 risultati numerati nel formato `N. [source/kind] path#chunk (d=…)`.
**Osservato (provider `ollama`):** la pipeline gira ma il provider locale (nomic-embed-text, il
più debole — vedi eval sotto) qui pesca **blob base64** (dati immagine in `docs_src/stream_data/`)
invece di `security/oauth2`:

```
1. [code/example] docs_src/stream_data/tutorial002_py310.py#3  (d=0.4322)
   AgdGlmZjpJbWFnZUxlbmd0aD0iMjki...   (← base64, rumore)
```

> **Finding:** (1) il provider locale è debole su query NL; (2) il corpus contiene blob base64 da
> ripulire in ingestion. La **qualità** per provider è misurata da `evaluate.py`:
>
> ```bash
> PYTHONPATH=. python 01-baseline/evaluate.py      # hit-rate@k + MRR@10 sui 3 provider
> ```
>
> Risultati documentati: `azure-large` hit@1 0.90 / MRR 0.950 > `azure-small` 0.70 / 0.833 >
> `ollama` 0.60 / 0.693 (vedi `wiki/experiments/01-baseline.md`).

---

## 02 — Hybrid + reranking (BM25 + dense + RRF)

**Scopo:** fondere BM25 (sparse, lessicale) e dense via Reciprocal Rank Fusion; il ramo sparse
eccelle sui **simboli esatti** del codice.
**Prerequisiti:** indice Chroma. Il `--mode sparse` è **offline** (nessun embedding/rete).

```bash
PYTHONPATH=. python 02-hybrid-reranking/hybrid.py "OAuth2PasswordBearer" --provider ollama --mode sparse -k 3
```

**Atteso:** in cima i file che contengono il simbolo esatto `OAuth2PasswordBearer`.
**Osservato:** deterministico, centra gli esempi `docs_src/security/` e il tutorial security:

```
1. [code/example] docs_src/security/tutorial001_py310.py#0
   from fastapi import Depends, FastAPI from fastapi.security import OAuth2PasswordBearer ...
3. [doc/markdown] docs/en/docs/tutorial/security/first-steps.md#5
   ## **FastAPI**'s `OAuth2PasswordBearer` ...
```

Fusione completa (richiede Ollama): `--mode hybrid`. Eval comparativa dense/hybrid/+rerank:
`PYTHONPATH=. python 02-hybrid-reranking/evaluate.py` (vedi `wiki/experiments/02-hybrid-reranking.md`).

---

## 03A — Code graph (AST)

**Scopo:** query **strutturali/deterministiche** sul grafo AST (definizioni, chiamanti, doc
collegati) — gratis, nessun LLM.
**Prerequisiti:** grafo AST.

```bash
PYTHONPATH=. python 03-graphrag/graph_query.py def     OAuth2PasswordBearer
PYTHONPATH=. python 03-graphrag/graph_query.py callers HTTPException
PYTHONPATH=. python 03-graphrag/graph_query.py docs    APIRouter
```

**Atteso:** definizione con `path:lineno`; lista chiamanti; doc Markdown collegati.
**Osservato:**

```
Definizioni di 'OAuth2PasswordBearer':
   - fastapi/security/oauth2.py:433  class OAuth2PasswordBearer
Chi chiama 'HTTPException':           (10 chiamanti, es. docs_src/app_testing/.../main.py)
Doc che menzionano 'APIRouter':       (es. advanced/custom-response.md, openapi-callbacks.md)
```

> I conteggi riflettono il **grafo corrente** su disco (`build_graph.py` risolve le chiamate in
> modo conservativo). Limite noto: i re-export da Starlette (`JSONResponse`) non risultano
> "definiti" (vedi `wiki/experiments/03-graphrag.md`).

---

## 3C — Microsoft GraphRAG

GraphRAG gira in un **venv isolato** (`03-graphrag/.venv-grag`) per conflitti di dipendenze
(numpy<2 di `graspologic`). Tutti i comandi richiedono `LITELLM_LOCAL_MODEL_COST_MAP=True`
(altrimenti `litellm` si blocca sul fetch della cost-map).

**Setup (una tantum):**
```bash
uv venv 03-graphrag/.venv-grag --python 3.12 && uv pip install --python 03-graphrag/.venv-grag graphrag
# config: 03-graphrag/grag/settings.yaml (entity_types di dominio) + grag/.env (key/endpoint)
```

**Indicizzazione (a pagamento, ~$3–4, ~14 min sul subset):**
```bash
LITELLM_LOCAL_MODEL_COST_MAP=True 03-graphrag/.venv-grag/Scripts/python.exe -m graphrag index --root 03-graphrag/grag
```

**Ispezione artefatti (gratis):**
```bash
PYTHONPATH=. 03-graphrag/.venv-grag/Scripts/python.exe 03-graphrag/summarize.py     # token + struttura
PYTHONPATH=. 03-graphrag/.venv-grag/Scripts/python.exe 03-graphrag/compare_runs.py \
    --a 03-graphrag/grag/output_run1_generic --a-label generico \
    --b 03-graphrag/grag/output            --b-label dominio
```

**Osservato (generico vs dominio):** entità 1090→1305, relazioni 1779→2684 (+51%), community
239→330. Tipi: generico 92% EVENT/ORGANIZATION → dominio CONCEPT/CLASS/FUNCTION/DATA_MODEL/
ENDPOINT/EXCEPTION/LIBRARY (vedi `wiki/experiments/03-graphrag.md`). Derivazione tipi data-driven:
skill `/derive-entity-types`.

**Query (a pagamento):**
```bash
# local search ≈ 1 chiamata (economica); global search ≈ map-reduce su tutte le community (~$0.23)
LITELLM_LOCAL_MODEL_COST_MAP=True 03-graphrag/.venv-grag/Scripts/python.exe -m graphrag query \
    --root 03-graphrag/grag --method local "What is OAuth2PasswordBearer?"
```

---

## 04 — Agentic RAG (orchestratore vanilla)

**Scopo:** un **LLM-orchestratore** interroga da solo i motori 01–03 come *tool*
(`search_code`, `search_docs`, `search_combined`, `find_symbol`, `who_calls`,
`related_docs`), itera finché ha contesto a sufficienza e **sintetizza una risposta
citando i file**. È la versione *framework-agnostica* (loop manuale su `shared/llm.py`),
riferimento per i futuri adattatori AutoGen / SK / LangGraph. Vedi
[`04-agentic-rag/README.md`](04-agentic-rag/README.md).

**Prerequisiti:** indice Chroma + grafo AST + un LLM con **tool-calling**:
- locale (`RAG_BACKEND=local`): Ollama con un modello tool-capable in `OLLAMA_CHAT_MODEL`
  (es. `llama3.1`, `qwen3`, `mistral-nemo`);
- Azure (`RAG_BACKEND=azure`): deployment `AZURE_OPENAI_CHAT_DEPLOYMENT` (es. `gpt-5.4-mini`).

```bash
PYTHONPATH=. python 04-agentic-rag/agent.py "Cos'è OAuth2PasswordBearer e in quale file è definito?" -v
PYTHONPATH=. python 04-agentic-rag/agent.py "..." --backend azure --max-steps 5 --json
```

**Osservato (locale, `qwen3:30b-a3b`):** l'agente sceglie `find_symbol`, ottiene
`fastapi/security/oauth2.py:433` e risponde citando il file:

```
== passi dell'agente ==
  [1] find_symbol({'name': 'OAuth2PasswordBearer'}) -> - fastapi/security/oauth2.py:433  class OAuth2PasswordBearer
=== RISPOSTA === (ollama:qwen3:30b-a3b)
OAuth2PasswordBearer è una classe di FastAPI ... definita in fastapi/security/oauth2.py:433
— passi: 2 · tool chiamati: find_symbol
```

> Il loop LLM end-to-end **non** è in pytest (lento e dipendente dal modello): la verifica
> è il comando qui sopra. La suite testa invece la **facade** e il **registry** dei tool.

### 04b — Adattatore AutoGen (1° framework a confronto)

Stesso compito della baseline, ma il loop di tool-use è orchestrato da **AutoGen**
(`AssistantAgent`), riusando **gli stessi tool e system prompt** (`tools.py`). Usa il client
OpenAI-compatible verso Ollama (`/v1`) o `AzureOpenAIChatCompletionClient`.

```bash
PYTHONPATH=. python 04-agentic-rag/autogen_app.py "In quale file è definita la classe APIRouter?" -v
```

**Osservato (locale, `qwen3:30b-a3b`):**

```
== tool chiamati ==
  - find_symbol({"name":"APIRouter"})
=== RISPOSTA (AutoGen) ===
La classe APIRouter è definita nel file fastapi/routing.py alla riga 1005.
```

> Confronto a parità (stessi tool/prompt/modello): la **baseline vanilla** e **AutoGen**
> possono divergere per *strategia* (numero di tool, sintesi).

### 04c — Eval comparativa + documentazione parlante

`evaluate.py` esegue un eval set di task (`eval_tasks.json`) attraverso ogni motore e misura
se la risposta **cita il file atteso**, con passi e n° tool. Oltre alle metriche, **genera**
la doc divulgativa [`ESEMPI-agentic.md`](04-agentic-rag/ESEMPI-agentic.md) ("ho chiesto X →
l'agente ha fatto Y → mi ha risposto Z"), controparte di `ESEMPI.md` per la Tappa 04.

Metriche: **cita atteso** (la risposta nomina il file giusto), **tool giusto** (ha usato uno
strumento ideale per quel tipo di task), passi e tool medi. L'eval set (`eval_tasks.json`)
copre tipi diversi — *localizzazione, multi-hop, doc-concept, code+doc* — per discriminare le
strategie dei framework.

```bash
PYTHONPATH=. python 04-agentic-rag/evaluate.py                  # tutti i task: vanilla+autogen+sk+langgraph
PYTHONPATH=. python 04-agentic-rag/evaluate.py --engines langgraph   # solo 1 motore: si FONDE con la cache
# Re-score + rigenera la doc SENZA ri-eseguire l'LLM (gratis, dai risultati salvati):
PYTHONPATH=. python 04-agentic-rag/evaluate.py --render-from 04-agentic-rag/eval_results.json
```

> 4 motori a parità (stessi tool + prompt): `vanilla` (loop manuale), `autogen`, `sk`
> (Semantic Kernel), `langgraph`. **Merge incrementale**: rieseguire `--engines X` aggiorna
> solo X e conserva gli altri in `eval_results.json` (usa `--no-merge` per ripartire da zero).
> `passi` è confrontabile tra vanilla/autogen/langgraph (turni reali); per `sk` è approssimato
> → per il costo guarda `tool medi`.

> L'esecuzione salva `eval_results.json` (cache dei risultati grezzi): raffinare la
> ground-truth dei task e rigenerare `ESEMPI-agentic.md` via `--render-from` **non ricosta**
> chiamate al modello. A pagamento solo con `RAG_BACKEND=azure`; in locale usa Ollama.
> I modelli locali non sono perfettamente deterministici: conta la *tendenza* tra i run.

---

## Suite di test (pytest)

Smoke test che invocano gli **stessi comandi** qui sopra e ne verificano output/return code.
Test **free** (BM25 sparse, grafo AST, artefatti GraphRAG) sempre eseguibili; test **gated**
(dense/hybrid → Ollama; GraphRAG query → Azure) **skippati** se l'ambiente non è pronto; test
**`paid`** skippati salvo flag.

```bash
.venv/Scripts/python.exe -m pytest tests/ -v            # suite free + gated (skip se mancano backend)
.venv/Scripts/python.exe -m pytest tests/ --run-paid    # include la query GraphRAG a pagamento
```

**Stato corrente:** `20 passed, 1 skipped` (l'1 skip è il test `paid`; con Ollama attivo i gated passano).

| Test | Config | Tipo | Verifica |
|---|---|---|---|
| `test_chunking_code.py` | chunking | free | chunk per simbolo (module/class/method), qualname, righe, contesto classe |
| `test_graph_ast.py` | 03A | free | def/callers/docs su simboli noti |
| `test_graphrag_artifacts.py` | 3C | free | tipi ⊆ tassonomia di dominio; grafo ricco |
| `test_hybrid.py::...sparse` | 02 | free | BM25 trova il simbolo esatto |
| `test_agentic.py::test_registry*` | 04 | free | registry tool ↔ dispatch 1:1; tool sconosciuto gestito |
| `test_agentic.py::test_graph_tools` | 04 | free | facade `find_symbol`/`who_calls` sul grafo |
| `test_agentic.py::...autogen*` | 04b | free | adattatore AutoGen importabile, 6 tool con docstring, client locale costruibile |
| `test_baseline.py` | 01 | gated (Ollama) | forma output dense (k risultati) |
| `test_hybrid.py::...fusione` | 02 | gated (Ollama) | la fusione RRF gira |
| `test_agentic.py::test_search_*` | 04 | gated (Ollama) | filtri facade `source=code\|doc` |
| `test_graphrag_query.py` | 3C | paid (Azure) | local search risponde su `OAuth2PasswordBearer` |

> **Chunking del codice** selezionabile via `CODE_CHUNKER` (`treesitter` default | `recursive`).
> Il tree-sitter spezza ai confini sintattici (funzioni/metodi/classi) con metadati
> `symbol`/`qualname`/righe — vedi `shared/chunking_code.py`. Effetto misurato: con la pipeline
> **hybrid+rerank** porta il recupero a simboli al massimo (azure-large MRR simboli **1.000**);
> col **dense puro** la frammentazione più fine penalizza le query NL-doc (vedi wiki).

> Gli smoke test verificano **che le pipeline girino e producano output ben formato**, non la
> *qualità* del retrieval (misurata dagli `evaluate.py` di ogni tappa, con numeri nel wiki).
