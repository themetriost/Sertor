---
title: 04 Agentic RAG (orchestratore vanilla + framework adapters)
type: experiment
tags: [agentic-rag, orchestrator, llm-tool-calling, shared-facade, semantic-kernel, autogen, langraph, mcp, azure-gpt5.4-mini]
created: 2026-05-29
updated: 2026-05-29
status: "vanilla + AutoGen + Semantic Kernel + eval a 3 motori su Azure gpt-5.4-mini; LangGraph + MCP da fare"
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

### Risultati eval — Azure gpt-5.4-mini (9 task × 3 motori)

| Motore | cited (9) | tool_ok (9) | steps (media) | tools_called (media) | Note |
|--------|-----------|-------------|---------------|----------------------|------|
| vanilla | 9/9 (100%) | 9/9 (100%) | 2.7 | 3.2 | routing sempre stabile |
| AutoGen | 9/9 (100%) | 7/9 (78%) | 2.7 | 3.4 | 2 "tool✗" su routing (search_code vs find_symbol) |
| sk | 9/9 (100%) | 8/9 (89%) | 5.0 | 4.0 | SK più verboso; `steps` APPROSSIMATO ⚠️; cfr `tool_medi` robusto |

**Lettura onesta sui risultati Azure:**

(a) **Correttezza fattuale 9/9 per tutti e tre.** Con gpt-5.4-mini (modello forte), il segnale discriminante
non è più "cita il file?" (tutti lo fanno), bensì **routing degli strumenti e efficienza** (tool_ok, tool medi).

(b) **Vanilla vs AutoGen vs SK:**
   - **Vanilla:** routing sempre corretto (tool_ok 9/9), media tool 3.2.
   - **AutoGen:** 2 routing subottimali su localizzazione (tool_ok 7/9), media tool 3.4.
   - **SK:** 1 routing subottimale, **ma con pattern di tool-calling più aggressivo** (media tool 4.0, picchi
     fino a 10 su query-param-codedoc e 8 su httpexception-usage). SK itera e reitera il loop auto-invocation
     più che vanilla/AutoGen.

(c) **Metrica `steps` per SK è approssimata ⚠️:** SK non espone i confini dei turni LLM (la loop di
auto-invocation è opaca nel framework). Il valore 5.0 è calcolato come media di (numero tool + 1) per task.
Non è direttamente comparabile a vanilla/AutoGen che contano turni reali. **La metrica robusta per confronto è
`tool_medi`:** vanilla 3.2 < AutoGen 3.4 < SK 4.0.

(d) **Implicazione:** SK con `ChatCompletionAgent + Auto()` tende a fare **più chiamate-tool** degli altri due
a parità di task/prompt/modello. È una differenza di orchestrazione concreta (non un bug): SK ripete la loop
di funzione astratta finché non reputa il task concluso. Vanilla e AutoGen si fermano prima. Per task
localizzazione diretta (find_symbol → sintesi), SK aggiunge passaggi di search_combined/related_docs.

(e) **Delta routing:** vanilla > SK > AutoGen su tool_ok (9 vs 8 vs 7). Ma la differenza è sottile:
tutti citano i file giusti; è il percorso che diverge. Tool_ok=8/9 per SK su task diverso da vanilla/AutoGen,
suggerisce un pattern di auto-invocation coerente ma con scelte diverse.

**Caveat non-determinismo:** 1 run per task (non mediato). Con modello forte, results sono stabili.

**Learning:** su un **modello forte**, la metrica `cited` satura (9/9 per tutti); il segnale discriminante
è l'**efficienza/routing** (tool_ok, tool medi). SK è strutturalmente il più verboso (more tool calls),
vanilla è il più parsimonioso. Questo è un trade-off di design: SK compensa con investigazione più profonda
(riesce a sintetizzare risposte con più contesto), vanilla è più diretto. Per deployment production, la scelta
dipende dal budget token e dalla tolleranza di latenza.

**Implicazione SK:** il pattern di auto-invocation rende SK interessante per **task complessi che richiedono
ricerca multi-hop naturale**, ma meno efficiente per localizzazione diretta. Vanilla è il baseline leggibile;
AutoGen è nel mezzo.

**Artefatto generato:** [`04-agentic-rag/ESEMPI-agentic.md`](../../04-agentic-rag/ESEMPI-agentic.md)
— doc divulgativa in stile ESEMPI.md ("ho chiesto X → l'agente ha fatto Y → mi ha risposto Z")
per ogni task e motore, auto-generata da `evaluate.py` a partire dai log esecuzione. Aggiornato per i risultati Azure (3 motori).

**Prossimi passi (eval e framework):**
- **Adattatore LangGraph** — graph workflow plan→retrieve→synthesize via LangGraph state machine (3° framework).
- **Query planning context-aware** — disambiguare routing doc-vs-code in base al tipo di domanda.
- **MCP server** — esporre `shared/retrieval.py` come MCP tools per Claude Code.

## Prossimi passi

1. ~~**Eval set su Tappa 04**~~ **COMPLETATO su Azure** — 9 task × 3 motori, metrica tool_ok, entry point gpt-5.4-mini.
2. ~~**Stabilità eval**~~ **STABILIZZATO** — modello forte (gpt-5.4-mini) elimina non-determinismo locale; 1 run sufficiente per metrica.
3. ~~**Adattatore Semantic Kernel**~~ **COMPLETATO** — kernel SK con ChatCompletionAgent + FunctionChoiceBehavior.Auto(), eval a 3 motori.
4. **Adattatore LangGraph** — graph workflow plan→retrieve→synthesize via LangGraph state machine (3° framework).
5. **Query planning context-aware** — disambiguare routing doc-vs-code in base al tipo di domanda (segue da eval routing diff).
6. **MCP server** — esporre `shared/retrieval.py` come MCP tools (`search_code`, `search_docs`,
   `find_symbol`, `who_calls`) per Claude Code e agenti. Superficie futura: agente Claude via MCP.
7. **Custom entity_types per GraphRAG** — usare `derive-entity-types` (Tappa 3C follow-up) per
   migliorare il grafo semantico.

## Backlink e contesto

- [[architettura-target]] — disegno finale + roadmap Tappa 4.
- [[01-baseline]], [[02-hybrid-reranking]], [[03-graphrag]] — motori retrieval sottostanti.
- `../../04-agentic-rag/README.md` — design doc (dettagli orchestrator, confronto framework).
