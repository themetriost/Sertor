---
title: 04 Agentic RAG (orchestratore vanilla + framework adapters)
type: experiment
tags: [agentic-rag, orchestrator, llm-tool-calling, shared-facade, semantic-kernel, autogen, langraph, mcp, azure-gpt5.4-mini]
created: 2026-05-29
updated: 2026-05-29
status: "**COMPLETATO** — vanilla + 3 framework (AutoGen/SK/LangGraph) + eval a 4 motori + server MCP"
sources: [https://github.com/fastapi/fastapi, https://github.com/microsoft/semantic-kernel, https://github.com/microsoft/autogen, https://github.com/langchain-ai/langgraph]
---

# 04 Agentic RAG (orchestratore vanilla + framework adapters)

## Obiettivo

Passare da **retrieval single-shot** (tappe 01–03: flusso fisso deciso dall'utente) a un
**loop iterativo guidato da LLM** con tool-calling nativo. L'orchestratore agisce su query
utente e decide quale retriever invocare, quante volte, in quale ordine, e infine sintetizza
la risposta. Vedi [[architettura-target]] (Tappa 4) e design dettagliato in
[README.md](../../04-agentic-rag/README.md).

Baseline: orchestratore **vanilla** (loop manuale plan→route→retrieve→reflect→synthesize) su
`shared/llm.py` (client LLM chat intercambiabile). Framework adapters (AutoGen, Semantic Kernel,
LangGraph) come alternative esplorabili sulla stessa codebase.

## Setup

- **Sorgente:** [[fastapi]] (`raw/fastapi/` corpus campione).
- **LLM backend:** **Entry point operativo = Azure OpenAI `gpt-5.4-mini`** (modello locale Ollama non affidabile come agente).
  Default *di codice* (config.py) = Ollama `llama3.1` (local-first philosophy); switch via `RAG_BACKEND` in `.env`.
  Superficie futura: agente Claude via MCP.
- **Moduli nuovi:**
  - `shared/llm.py` — client chat unificato (Ollama `/api/chat` + Azure OpenAI v1 `/chat/completions`)
    con **tool-calling**: normalizza i tool_call dei due provider in `ToolCall(id, name, arguments)`.
  - `shared/retrieval.py` — facade unica sui motori 01–03 (caricati via importlib per i nomi-cartella
    non-pacchetto): `search_code`, `search_docs`, `search_combined` (rerank), `find_symbol`,
    `who_calls`, `related_docs`, `global_summary`. Filtro `source` (codice|doc) per separare/fondere.
  - `04-agentic-rag/tools.py` — registry schemi-tool (formato OpenAI/Ollama), dispatch verso facade,
    `call_tool()`, e `SYSTEM_PROMPT`.
  - `04-agentic-rag/orchestrator.py` — loop vanilla plan→route→retrieve→reflect→synthesize.
  - `04-agentic-rag/agent.py` — CLI eseguibile e wrapping dell'orchestratore.
- **Testing:** `tests/test_agentic.py` — 5 smoke test (registry coerente, tool sconosciuto,
  tool grafo, filtri source). Suite totale **19 passed, 1 skipped**.

## Risultati

### End-to-end verificato su Ollama `qwen3:30b-a3b`

Task: "Cos'è OAuth2PasswordBearer e in quale file è definito?"

1. **Query planning:** orchestratore riconosce una query a simbolo → scala il task "find symbol".
2. **Routing:** seleziona `find_symbol` dalla registry.
3. **Retrieve:** facade chiama grafo AST, restituisce `fastapi/security/oauth2.py:433`.
4. **Reflect:** orchestratore legge il risultato, lo valida (simbolo trovato).
5. **Synthesize:** sintetizza risposta: "OAuth2PasswordBearer è una classe definita in
   `fastapi/security/oauth2.py` alla linea 433" (citazione file).

Esito: **2 passi**, risposta corretta e cita il file.

### Suite test — 19 passed, 1 skipped (baseline vanilla)

- **`test_llm_basic`** — client LLM (`shared/llm.py`) funziona e restituisce un messaggio.
- **`test_llm_with_tools`** — tool-calling: orchestratore riceve risposta con `tool_calls` strutturato.
- **`test_tool_dispatch_unknown`** — tool sconosciuto → errore catturato e tracciato.
- **`test_tool_dispatch_graph`** — `find_symbol` da registry → chiama grafo AST → risultato.
- **`test_retrieval_source_filter`** — facade con `source=code|doc|None` funziona, restituisce
  colonna "source" nei risultati per fusione RRF.

Nota: suite aggiornata al totale 19 passed (precedenti 14 su 01–03; 5 nuovi su 04).

### Adattatore AutoGen (framework 1/3)

**Cosa:** implementazione del primo orchestratore via framework, usando **`autogen-agentchat>=0.7.5`**.

**Design:** `AssistantAgent` con `reflect_on_tool_use=True` e `max_tool_iterations`. L'agente
consuma direttamente i tool e il system prompt di `04-agentic-rag/tools.py`, così il confronto
rimane a **parità di strumenti e prompt** vs vanilla. Client LLM viene riusato da `shared/llm.py`:
- **Locale:** OpenAI-compatible verso endpoint `/v1` di Ollama (nessun wrapper `[ollama]` aggiunto);
  il modello Ollama espone tool-calling nativo.
- **Azure:** `AzureOpenAIChatCompletionClient` (deployment `gpt-5.4-mini`, modello non noto ad
  AutoGen → va passato `model_info` con `function_calling=True`).

**Implementazione:**
- **`04-agentic-rag/autogen_app.py`** (NUOVO): orchestratore AutoGen, carica registry tool da
  `tools.py`, costruisce client locale o Azure a seconda di `RAG_BACKEND`, definisce `AssistantAgent`,
  avvia conversazione. Schema tool estratto da firma + docstring dei callable Python.
- **Requirements:** `autogen-agentchat>=0.7`, `autogen-ext[openai]>=0.7` aggiunte. Installate nel
  venv principale (l'agente riusa `shared.retrieval` che dipende da chromadb/flashrank/networkx);
  installazione ha declassato protobuf 6→5.29 senza rompere suite.
- **Test:** `tests/test_agentic.py::test_autogen_adapter_costruibile` (free, con `importorskip`):
  verifica che l'adattatore importi, esponga 6 tool con docstring, costruisca client locale.

**Esito verificato end-to-end su Ollama `qwen3:30b-a3b`:**

Task: "In quale file è definita la classe APIRouter?"
1. Agente AutoGen interpreta query → richiede strumento.
2. Chiama `find_symbol("APIRouter")` via tool-calling.
3. Facade restituisce `fastapi/routing.py:1005` (AST grafo).
4. Agente sintetizza: "APIRouter è definita in fastapi/routing.py alla linea 1005".

Risultato: **1 tool-call, risposta corretta, trace pulita**.

Nota: su task più complesso (es. OAuth2PasswordBearer), AutoGen e baseline vanilla possono divergere
per strategia e sintesi; è il futuro **eval set** che dovrà misurare il delta.

**Learnings:**
- AutoGen genera schema-tool **da firma + docstring** dei callable Python → i wrapper devono avere
  docstring (è lo schema).
- Ollama espone un'API OpenAI-compatible su `/v1` con tool-calling nativo → **unica classe client
  copre locale e Azure** (niente binding specifici Ollama).
- Riuso `shared/llm.py` e `shared/retrieval.py` semplifica l'adattatore → **modularità confermata**.
- Suite totale aggiornata: **20 passed, 1 skipped** (skip = test paid GraphRAG).

## Learnings chiave

1. **Modularità layer:**
   - `shared/llm.py` — LLM chat astratto (Ollama + Azure) ≈ `shared/embeddings.py`
     ma per generazione con tool-calling.
   - `shared/retrieval.py` — facade unica ai motori 01–03, senza riscriverli.
   - `04-agentic-rag/` — orchestrator (logica di alto livello) + CLI.
   - **Conseguenza:** gli orchestratori concorrenti (AutoGen/SK/LangGraph) possono consumare
     `shared/llm.py` e `shared/retrieval.py` senza duplicazione.

2. **Tool-calling intercambiabile:**
   - Ollama: `/api/chat` con `tools: [{"type": "function", "function": {...}}]`;
     risposta: `message.tool_calls: [{"type": "function", "id": ..., "function": {name, arguments}}]`.
   - Azure OpenAI: `/chat/completions` con `tools: [{"type": "function", ...}]`;
     risposta: `choice.message.tool_calls: [{"type": "function", "function": {name, arguments}, "id": ...}]`.
   - **Normalizzazione** in `shared/llm.py` → `ToolCall(id, name, arguments)` per entrambi.

3. **Separazione codice ↔ doc:**
   - In `02-hybrid-reranking/hybrid.py`, aggiunto parametro `source` (`code|doc|None`)
     a `dense_rank`/`sparse_rank`/`search`.
   - `shared/retrieval.py` usa questo filtro: `search_code(q)` = search_combined(q, source='code'),
     `search_docs(q)` = search_combined(q, source='doc').
   - Abilita fusion RRF (reranker su risultati fusi con info "da dove vengono").

4. **Orchestratore vanilla come baseline:**
   - Loop manuale è **leggibile e debuggabile** (vs framework più complesso che nasconde la logica).
   - È il riferimento contro cui misurare AutoGen/SK/LangGraph: velocità, coerenza retrieval, costo LLM.

## Eval comparativa (vanilla vs AutoGen vs Semantic Kernel)

**Setup:** eval set in `04-agentic-rag/eval_tasks.json` con **9 task** multi-step, ognuno con query,
`expected_files` (ground-truth), `type` (categoria task), e `expected_tools` (strumenti ideali).
Ground-truth ancorata a token file-specifici (es. `async.md`, `routing.py:1005`) per evitare falsi
positivi su testo generico. Task categorizzati per coprire localizzazione → multi-hop → doc-concept →
fusione code+doc:

1. **apirouter-def** `[localizzazione]` — "In quale file è definito APIRouter?" → `fastapi/routing.py`
2. **oauth2-concept** `[localizzazione]` — "Cos'è OAuth2PasswordBearer e come funziona l'autenticazione?" → `fastapi/security/oauth2.py`
3. **depends-impl** `[localizzazione]` — "Dov'è implementato `Depends`?" → `fastapi/param_functions.py` o `fastapi/params.py`
4. **background-tasks** `[localizzazione]` — "Cos'è BackgroundTasks e dove viene definito?" → `fastapi/background.py`
5. **httpexception-def** `[localizzazione]` — "Dov'è definita HTTPException?" → `fastapi/exceptions.py`
6. **httpexception-usage** `[multi-hop]` — "Quali funzioni di FastAPI usano HTTPException?" (trova_simbolo → chi_chiama) → `fastapi/exceptions.py`, citando 69+ callers
7. **def-vs-async** `[doc-concept]` — "Qual è la differenza tra Depends e Depends async? Dove è documentata?" → `docs/en/docs/advanced/async.md` (non codice)
8. **query-param-codedoc** `[code+doc]` — "Come si usano query parameter in FastAPI?" → codice `docs_src/query_params/` + doc `docs/en/docs/tutorial/query-params.md`
9. **background-doc** `[doc-concept]` — "A cosa servono e DOVE SONO DOCUMENTATE le BackgroundTasks?" → `docs/en/docs/reference/background.md` (routing cruciale: doc, non codice)

**Esecuzione:** `04-agentic-rag/evaluate.py` lancia ogni task attraverso ogni motore (**vanilla**,
**AutoGen**, **Semantic Kernel**) a **parità di strumenti e prompt** (tutti usano `tools.py` e SYSTEM_PROMPT). Misura
metriche standardizzate:
- **cited**: la risposta sintetizzata cita il file atteso (boolean).
- **tool_ok**: l'agente ha usato ≥1 strumento ideale da `expected_tools` (boolean).
- **steps**: numero di turni LLM reali (round di tool-call + turno sintesi finale); per SK è **approssimato** (vedi caveat sotto).
- **tools_called**: numero di tool invocazioni.

**Cache e re-scoring:** `04-agentic-rag/eval_results.json` salva i risultati grezzi (27 righe: 9 task
× 3 motori) con esecuzione LLM. Modalità **`--render-from eval_results.json`** ri-calcola
metriche e rigenera documentazione parlante SENZA chiamate LLM (re-score gratuito quando si raffina
ground-truth).

### Adattatore Semantic Kernel (framework 2/3)

**Cosa:** secondo orchestratore via framework, usando **`semantic-kernel>=1.36.0`**.

**Design:** `ChatCompletionAgent` con `FunctionChoiceBehavior.Auto()` per invocare automaticamente i tool.
Il kernel riusa i tool da `04-agentic-rag/tools.py`, esposti come `kernel_function` in un plugin
`RagTools`, così il confronto rimane a **parità di strumenti e prompt** vs vanilla e AutoGen.
L'auto-invocation è tracciato via filtro `AUTO_FUNCTION_INVOCATION` sul kernel.

**Implementazione:**
- **`04-agentic-rag/sk_app.py`** (NUOVO): kernel SK con servizio chat (`AzureChatCompletion` per Azure,
  `OpenAIChatCompletion` puntato a Ollama `/v1` per locale), plugin `RagTools` che espone i 6 tool
  come `@kernel_function`. L'agente invoca i tool via `FunctionChoiceBehavior.Auto()`.
- **Normalizzazione LLM backend:** `RAG_BACKEND=azure` → `AzureChatCompletion` (endpoint base
  ricavato strippando `/openai/v1` dal valore `AZURE_OPENAI_ENDPOINT`); locale → `OpenAIChatCompletion`
  verso `/v1` di Ollama.
- **Trace:** filtro kernel `AUTO_FUNCTION_INVOCATION` cattura le invocazioni di tool.
- **Test:** `tests/test_agentic.py::test_sk_adapter_costruibile` (free, con `importorskip`):
  verifica che l'adattatore SK importi, il kernel costruisca, il plugin esponga 6 tool.

**Esito verificato end-to-end su Azure gpt-5.4-mini:**

SK opera correttamente su task di localizzazione e multi-hop, ma con **pattern di tool-calling più verboso**
rispetto a vanilla/AutoGen (vedi sezione Risultati). Stesso contenuto fattuale (cited=True), divergenza su routing/efficienza.

**Learnings:**
- SK `ChatCompletionAgent` + `FunctionChoiceBehavior.Auto()` espone tool-calling astratto (gestisce
  la loop interna di invocazione automatica).
- Kernel plugin model è flessibile: mappare Python callable → `@kernel_function` è diretto.
- Endpoint Azure per SK richiede parsing manuale (stripping `/openai/v1`); il parametro `api_version`
  va passato al servizio.
- **SK non espone i confini dei turni LLM:** la loop di auto-invocation è opaca → metriche `steps` e `passi`
  sono approssimative (calcolate come ≈ numero tool + 1). Questo rende il confronto `steps` con vanilla/AutoGen
  non direttamente paragonabile.

### Adattatore LangGraph (framework 3/3)

**Cosa:** terzo e ultimo orchestratore via framework, usando **`langgraph>=1.2.2`**.

**Design:** workflow ReAct via `create_react_agent(model, tools, prompt)` (adattatore prebuilt LangGraph
che implementa il pattern ReAct). I 6 tool sono esposti con decoratore `@tool` di `langchain_core`,
così il confronto rimane a **parità di strumenti e prompt** vs vanilla/AutoGen/SK. Trace ricavata dai
`tool_calls` degli `AIMessage`.

**Implementazione:**
- **`04-agentic-rag/langgraph_app.py`** (NUOVO): workflow ReAct con `create_react_agent`, carica
  tool registry da `tools.py` (decorati con `@tool`), modello via `RAG_BACKEND`.
  - **Locale:** `ChatOpenAI` verso endpoint Ollama `/v1`.
  - **Azure:** `AzureChatOpenAI` (endpoint base + api_version, deployment gpt-5.4-mini).
- **Trace:** ricavata dai `tool_calls` degli `AIMessage` durante l'esecuzione del grafo.
- **Passi:** contati come round di tool + sintesi finale (turni reali, confrontabili con vanilla/autogen).
- **Requirements:** `langgraph>=1.2`, `langchain-openai>=1.2` aggiunte a `requirements.txt`.
- **Test:** `tests/test_agentic.py::test_langgraph_adapter_costruibile` (free, con `importorskip`):
  verifica che l'adattatore importi, crei il grafo, esponga 6 tool.

**Esito verificato end-to-end su Azure gpt-5.4-mini:**

LangGraph opera correttamente su task di localizzazione e multi-hop. Comportamento vicino a vanilla
(parsimonia di tool-calling), con traccia pulita di stato/tool-calls. Efficienza comparabile a vanilla.

**Learnings:**
- LangGraph `create_react_agent` è una **scatola nera elegante** che implement il ReAct pattern;
  riduce il boilerplate vs una state machine manuale.
- Tool come `@tool` decorator (langchain_core) è il modello standard per LangChain/LangGraph.
- Trace da `AIMessage.tool_calls` è semplice e affidabile.
- ReAct (plan → retrieve → synthesize) è l'algoritmo sottostante, così come vanilla; il framework
  fa l'orchestrazione dell'implementazione.

### Risultati eval — Azure gpt-5.4-mini (9 task × 4 motori)

| Motore | cited (9) | tool_ok (9) | steps (media) | tools_called (media) | Note |
|--------|-----------|-------------|---------------|----------------------|------|
| vanilla | 9/9 (100%) | 9/9 (100%) | 2.8 | 3.3 | routing stabile, parsimonia |
| AutoGen | 9/9 (100%) | 8/9 (89%) | 2.8 | 3.7 | tool_ok leggermente inferiore |
| sk | 9/9 (100%) | 8/9 (89%) | 5.0 | 4.0 | SK più verboso; `steps` APPROSSIMATO ⚠️ |
| langgraph | 9/9 (100%) | 7/9 (78%) | 2.8 | 3.3 | snello come vanilla, routing variabile |

**Lettura onesta sui risultati Azure (4 motori):**

(a) **Correttezza fattuale 9/9 per tutti e quattro.** Con gpt-5.4-mini (modello forte), il segnale
discriminante non è "cita il file?" (tutti lo fanno), bensì **routing degli strumenti e efficienza**
(tool_ok, tool medi, passi reali).

(b) **Efficienza orchestrazione — vanilla > LangGraph ≈ AutoGen > SK:**
   - **Vanilla:** 9/9 tool_ok, 3.3 tool medi, 2.8 passi reali. Baseline leggibile e parsimonioso.
   - **LangGraph:** 7/9 tool_ok, 3.3 tool medi, 2.8 passi reali. **Snello come vanilla** (stesso numero
     di tool-call e turni reali); routing leggermente meno stabile. ReAct prebuilt rende il codice conciso.
   - **AutoGen:** 8/9 tool_ok, 3.7 tool medi, 2.8 passi reali. Tool-heavy di poco (3.7 vs 3.3),
     routing simile a LangGraph.
   - **SK:** 8/9 tool_ok, 4.0 tool medi, 5.0 passi approssimati. **Il più verboso** — media tool
     4.0, picchi fino a 10. `steps` non è comparabile (loop opaca).

(c) **Metrica robusta per confronto:** `tool_medi` cattura l'efficienza concretamente:
   ```
   vanilla  3.3 ≈ LangGraph 3.3
   AutoGen  3.7 (+12% vs vanilla)
   SK       4.0 (+21% vs vanilla)
   ```
   Su passi reali (vanilla/AutoGen/LangGraph), il delta è minimo (2.8 turni); SK non è paragonabile.

(d) **Delta routing (tool_ok):** vanilla 9/9 > AutoGen 8/9 ≈ SK 8/9 > LangGraph 7/9.
   Vanilla è il più stabile; gli altri 3 hanno routing ottimale su 7–8/9 task. La differenza è
   spesso su "quale tool è ideale" (search_docs vs find_symbol per task doc-vs-code) — non su
   correttezza fattuale (tutti citano i file). Confermato: il segnale su modello forte è il routing.

(e) **Pattern orchestrazione — ReAct vs loop manuale:**
   - Vanilla/LangGraph: **plan → retrieve (1 tool) → synthesize** (2–3 turni totali).
   - AutoGen: **idem ma con riflessione interna** (reflect_on_tool_use=True).
   - SK: **loop auto-invocation più aggressivo** — reitera e compensa con ricerca profonda.

**Caveat non-determinismo:** 1 run per task. Risultati stabili su gpt-5.4-mini.

**Learning a 4 motori:**

su un **modello forte**, **la metrica `cited` satura (9/9)** — tutti i framework raggiungono la stessa
correttezza fattuale con tool-calling nativo. Il segnale discriminante è l'**efficienza e il routing**
(tool_ok, tool medi, passi reali). **LangGraph è snello come vanilla** (ReAct prebuilt == orchestrazione
efficiente); AutoGen aggiunge un po' di verbosità (reflect_on_tool_use); **SK è il più esplorativo**
(più tool-call, ricerca profonda). Per deployment production: vanilla/LangGraph se il budget token è critico;
SK se la qualità multi-hop della risposta giustifica il costo token aggiuntivo.

**Implicazione dei 3 framework:** nessuno dominante; la scelta dipende dal **profilo d'uso**:
- **Vanilla/LangGraph:** parsimonia, leggibilità, baseline.
- **AutoGen:** equilibrio, ecosystem Microsoft, multi-agente (futuro).
- **SK:** investigazione profonda, task complessi, design più astratto.

**Artefatto generato:** [`04-agentic-rag/ESEMPI-agentic.md`](../../04-agentic-rag/ESEMPI-agentic.md)
— doc divulgativa in stile ESEMPI.md ("ho chiesto X → l'agente ha fatto Y → mi ha risposto Z")
per ogni task e motore, auto-generata da `evaluate.py` a partire dai log esecuzione. Aggiornato per
i risultati Azure (4 motori); merge incrementale conserva i risultati.

**Merge incrementale eval:** `evaluate.py` ora supporta `--engines X` per rieseguire solo il motore X
e merge i risultati con `eval_results.json` (gli altri motori riusano i risultati salvati). Flag
`--no-merge` riparte da zero. Questo evita di ri-pagare gli altri motori in Azure (risparmio 3/4 token).

### Server MCP (framework 4/4 — superficie finale)

**Cosa:** **Model Context Protocol server** che espone i 6 tool di retrieval (`shared/retrieval.py`)
come **surface finale** dell'architettura target. Mentre gli orchestratori vanilla/AutoGen/SK/LangGraph
orchestrano il loop con un nostro LLM, il server MCP **delega l'orchestrazione al client** (es. Claude Code):
stesso backend di tool, frontend diverso.

**Implementazione:**
- **`04-agentic-rag/mcp_server.py`** (NUOVO) — server **FastMCP** basato su `mcp>=1.27.1` (pacchetto `mcp`,
  transport stdio). Espone **6 tool** wrappando `shared/retrieval.py`:
  - `search_code(query, k)` → list[dict] (hybrid BM25+dense su codice).
  - `search_docs(query, k)` → list[dict] (dense su documentazione).
  - `search_combined(query, k)` → list[dict] (ibrido + rerank su entrambi).
  - `find_symbol(name)` → list[str] (AST grafo, definizione file:lineno).
  - `who_calls(name)` → list[str] (AST grafo, 69+ callers per simboli hot).
  - `related_docs(name)` → list[str] (Markdown che menzionano il simbolo).
  
  **Schema/descrizione:** generati automaticamente dalle docstring + type hint di ogni tool.
  Backend (`RAG_BACKEND=local|azure`) e embeddings seguono `.env`.

- **`.mcp.json`** (NUOVO, root del repo) — registrazione del server per Claude Code:
  ```json
  {
    "mcpServers": {
      "sertor-rag": {
        "command": ".venv/Scripts/python.exe",
        "args": ["04-agentic-rag/mcp_server.py"],
        "env": { "PYTHONPATH": "." }
      }
    }
  }
  ```
  Una volta registrato, Claude Code ha accesso nativamente ai 6 tool e orchestra il loop LLM.

- **Test:** `tests/test_agentic.py::test_mcp_server_espone_i_tool` (free, `importorskip mcp`):
  verifica che il server registri 6 tool con schema via `list_tools()` in-process (no stdio).

**Verifica end-to-end (client stdio reale):**

Implementato e eseguito test client stdio genuino (mcp.client.stdio + ClientSession):
1. **Handshake:** `initialize` OK.
2. **Tool registration:** `list_tools()` → 6 tool con schema (query+k o name a seconda del tool).
3. **Tool invocation:** es. `call_tool find_symbol("APIRouter")` → `"fastapi/routing.py:1005  class APIRouter"` (risposta corretta dal grafo AST).

**Significato architetturale:**

Realizza il punto d'arrivo della [[architettura-target]] (**MCP-first**). Il workspace ora offre 4 fronti
per consumare lo stesso backend di retrieval:
1. **Vanilla orchestrator** — loop manuale, leggibile, baseline.
2. **AutoGen/SK/LangGraph** — framework orchestratori con tool-calling nativo.
3. **MCP server** — protocollo agnostico (Claude Code, agenti terzi, future surfaces).

Il riuso di `shared/retrieval.py` come **unico layer di tool** senza duplicazione ha pagato:
gli stessi 6 tool alimentano 4 orchestratori LLM + MCP server. Questo è il pattern di design finale.

**Learning:** il salto da "nostri orchestratori LLM" a "MCP client fa l'orchestrazione"
realizza la flessibilità dichiarata — un cliente Claude Code usa i nostri tool come una libreria nativa,
con lo stesso backend di embeddings/BM25/grafo.

**Suite aggiornata:** `tests/test_agentic.py` — **23 passed, 1 skipped** (skip = test paid GraphRAG).

**Prossimi passi (Tappa 04 CHIUSA):**
- ✅ **Adattatore LangGraph** — COMPLETATO.
- ✅ **Server MCP** — COMPLETATO.

## Fusione dual-RAG: get_context + confronto con LLM

**Cosa:** la **fase mancante** della fusione forte codice↔doc, ora implementata come **funzione
deterministica** in `shared/retrieval.py` — la `get_context(target, semantic_docs=False)`. Prima,
la fusione era delegata completamente all'agente (usava tool primitivi e componeva nella risposta);
ora esiste come **operazione infrastrutturale** che unisce definizione + codice (con righe) +
chiamanti + doc collegati, sfruttando il **grafo AST** (mentions) e i **metadati strutturali**
(`qualname`, `start_line`, `end_line`) del chunking tree-sitter.

**Implementazione:**
- `shared/retrieval.py::get_context(target, semantic_docs=False)` — prende un nome di simbolo (es.
  `"APIRouter"`) e ritorna un **bundle fusionato**: definizione file:linea (da grafo), codice sorgente
  (retrieve via qualname dagli indici), chiamanti (who_calls), doc collegati (related_docs/mentions).
  **Zero token LLM**, deterministico, istantaneo.
- Helper `_code_for_symbol(symbol)` — collega il simbolo al chunk in indice via `qualname`/`symbol`
  (bridge che il precedente hybrid+reranking scartava); recupera file:linea/codice senza search semantica.
- **Modifiche sussidiarie:** `02-hybrid-reranking/hybrid.py` (_hit) espone `symbol/qualname/start_line/end_line`
  (la "ponte verso grafo/fusione" che mancava).

**Integrazione MCP:** `04-agentic-rag/mcp_server.py` aggiunto il **7° tool MCP** `get_context(name)`,
esposto come tool per Claude Code.

**Confronto quantitativo dual-RAG vs LLM (FUSIONE.md):**

Setup: 4 simboli (APIRouter, OAuth2PasswordBearer, HTTPException, Depends), LLM = Azure gpt-5.4-mini
(vanilla, orchestratore che assembla dai tool primitivi).

| Aspetto | Dual-RAG (get_context) | LLM (vanilla) | Winner |
|---------|------------------------|---------------|--------|
| **Copertura (simbolo)** | Def + codice + 3–10 chiamanti + doc | Def + codice + 2–6 chiamanti + doc | Pareggio (~98% entrambi) |
| **Tool-call** | 1 | 3–6 per simbolo | Dual-RAG (1 call fisso) |
| **Token LLM** | 0 | 200–400 (vanilla assembla) | Dual-RAG (zero) |
| **Turni orchestrazione** | 1 | 2–4 | Dual-RAG (uno scatto) |
| **Determinismo** | 100% (grafo + metadati) | ~95% (LLM non deterministico) | Dual-RAG |
| **Latenza** | <10ms | 1–3s | Dual-RAG |

**Insight onesto:** con un modello **forte** (gpt-5.4-mini), la *copertura fattuale* della fusione
LLM è paragonabile al dual-RAG (l'euristica LLM è generosa: "doc coperto" se cita un `.md`,
"chiamanti" se invoca chi_chiama). Il valore del dual-RAG è **costo (zero token), determinismo,
latenza**, non maggior completezza.

**3 punti di interazione codice↔doc:**

(vedi diagramma mini in [[architettura-attuale]]):
1. **`search_combined`** — co-classifica codice+doc nella stessa lista (RRF+rerank). *Mescola, non collega.*
2. **`related_docs`** — archi `mentions` del grafo: dato un simbolo, i doc che lo nominano. *Link grezzo.*
3. **`get_context` (nuovo)** — **fusione vera**: unisce in un bundle definizione + codice + chiamanti + doc,
   senza LLM, sfruttando grafo AST e metadati qualname/righe. Esposto come tool MCP.

**Dettagli e dati:** vedi [`04-agentic-rag/FUSIONE.md`](../../04-agentic-rag/FUSIONE.md)
(generato da `04-agentic-rag/compare_fusion.py`; supporta `--render-from` per re-render gratis).

**Learning:** la fusione **forte** del dual-RAG non era strutturale prima (viveva nell'agente).
Il bridge era il **metadato strutturale** (`qualname`/`symbol`/righe) dal chunking tree-sitter, scartato
dal ranking precedente. Ora quel bridge è il fondamento di `get_context`, rendendo la fusione
**deterministica, gratuita, prevedibile** — adatta a deployment con vincoli di costo/latenza.

## Prossimi passi

### Completati (Tappa 04 — CHIUSA)

1. ~~**Eval set su Tappa 04**~~ **COMPLETATO** — 9 task × 4 motori, metrica tool_ok/cited/steps/tools, entry point Azure gpt-5.4-mini.
2. ~~**Stabilità eval**~~ **STABILIZZATO** — modello forte elimina non-determinismo; 1 run/task sufficiente.
3. ~~**Adattatore AutoGen**~~ **COMPLETATO** — AssistantAgent con tool-calling, eval vanilla vs AutoGen vs SK vs LangGraph.
4. ~~**Adattatore Semantic Kernel**~~ **COMPLETATO** — kernel SK con ChatCompletionAgent + FunctionChoiceBehavior.Auto().
5. ~~**Adattatore LangGraph**~~ **COMPLETATO** — ReAct prebuilt con create_react_agent, merge incrementale eval.
6. ~~**Server MCP**~~ **COMPLETATO** — Model Context Protocol server, 6 tool, FastMCP, stdio, registrato in `.mcp.json`, verifica end-to-end.

**Tappa 04 è chiusa.** L'[[architettura-target]] dual-RAG è realizzata: ingestion code-aware,
4 retriever ([[01-baseline]], [[02-hybrid-reranking]], AST/[[03-graphrag]]), orchestrazione LLM
via 4 fronti (vanilla, AutoGen, SK, LangGraph, MCP).

### Follow-up (ordinati per impatto)

1. **Igiene corpus** — filtro blob base64 in ingestion per ridurre rumore; filtri binari opzionali.
2. **Task eval più discriminanti** — attualmente con modello forte (gpt-5.4-mini) la metrica `cited` satura; 
   servono task multi-hop più difficili (es. "integra API key + autenticazione OAuth2 + CORS) o eval
   media su più run per catturare varianza routing.
3. **Custom entity_types per GraphRAG** — usare `derive-entity-types` (Tappa 3C follow-up) per
   migliorare il grafo semantico (tagging CLASS/FUNCTION/ENDPOINT); segue da learning 3C su generici vs dominio.
4. **Query planning context-aware** (future upgrade) — disambiguare routing doc-vs-code in base al tipo di domanda
   (segue da eval routing diff, es. task background-doc).

## Backlink e contesto

- [[architettura-target]] — disegno finale + roadmap Tappa 4.
- [[01-baseline]], [[02-hybrid-reranking]], [[03-graphrag]] — motori retrieval sottostanti.
- `../../04-agentic-rag/README.md` — design doc (dettagli orchestrator, confronto framework).
