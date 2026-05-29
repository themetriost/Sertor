---
title: 04 Agentic RAG (orchestratore vanilla + framework adapters)
type: experiment
tags: [agentic-rag, orchestrator, llm-tool-calling, shared-facade, autoboxed, semantic-kernel, langraph, mcp]
created: 2026-05-29
updated: 2026-05-29
status: "vanilla + AutoGen + eval comparativa completati; SK/LangGraph + MCP da fare"
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
- **LLM backend:** Ollama `llama3.1` (locale) o Azure OpenAI `gpt-5.4-mini` / `gpt-4-turbo`
  (cloud). Switch via `RAG_BACKEND` in `shared/config.py`.
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

## Eval comparativa (vanilla vs AutoGen)

**Setup:** eval set in `04-agentic-rag/eval_tasks.json` con 5 task multi-step, ognuno con query,
`expected_files` (ground-truth) e descrizione uso-case:
1. **apirouter-def** — "In quale file è definito APIRouter?" → `fastapi/routing.py`
2. **oauth2-concept** — "Cos'è OAuth2PasswordBearer e come funziona l'autenticazione?" → `fastapi/security/oauth2.py`
3. **depends-impl** — "Dov'è implementato `Depends`?" → `fastapi/param_functions.py` o `fastapi/params.py`
4. **background-tasks** — "Cos'è BackgroundTasks e dove viene definito?" → `fastapi/background.py`
5. **httpexception-def** — "Dov'è definita HTTPException?" → `fastapi/exceptions.py`

**Esecuzione:** `04-agentic-rag/evaluate.py` lancia ogni task attraverso ogni motore (**vanilla**,
**AutoGen**) a **parità di strumenti e prompt** (entrambi usano `tools.py` e SYSTEM_PROMPT), misura
metriche standardizzate:
- **cited**: la risposta sintetizzata cita il file atteso (boolean).
- **steps**: numero di passi del loop orchestratore (plan → retrieve → reflect → synthesize).
- **tools_called**: numero di tool invocazioni.

**Risultati eval (Ollama `qwen3:30b-a3b`, 5 task × 2 motori):**

| Motore | cited (%) | steps (media) | tools_called (media) |
|--------|-----------|---------------|----------------------|
| vanilla | 5/5 (100%) | 2.0 | 1.0 |
| AutoGen | 5/5 (100%) | 1.4 | 1.4 |

Entrambi i motori risolvono correttamente i 5 task di localizzazione; la differenza è nella
**strategia e numero di passi**:
- **vanilla:** segue il loop plan→route→retrieve→reflect→synthesize letteralmente (più esplicito).
- **AutoGen:** ottimizza passi iterativi, spesso non-linear; su BackgroundTasks ha una traiettoria
  più ricca (find_symbol → search_docs → related_docs), producendo una risposta con riferimenti
  anche alla documentazione (non solo alla posizione nel codice).

**Osservazione qualitativa:** su BackgroundTasks vanilla fa 1 tool-call (`find_symbol`),
AutoGen ne fa 3 (find_symbol + search_docs + related_docs) e fornisce un contesto
documentativo più ricco (descrive cosa sia BackgroundTasks, non solo il file). Suggerisce che
i due framework, **a parità di strumenti**, divergono per **orchestrazione interna**.

**Learning:** con un eval set standardizzato (stessi tool, prompt, modello LLM), il confronto
tra orchestratori diventa **misurabile** e non aneddotico. La "documentazione parlante"
(generata da `evaluate.py`) rende il confronto leggibile ai non-tecnici. I task attuali
sono di localizzazione (single-symbol queries), che favoriscono `find_symbol`; per
**discriminare meglio** i framework serviranno task più aperti e multi-hop (es.
"Quali funzioni usano FastAPI Depends?", "Come fluisce l'autenticazione?").

**Artefatto generato:** [`04-agentic-rag/ESEMPI-agentic.md`](../../04-agentic-rag/ESEMPI-agentic.md)
— doc divulgativa in stile ESEMPI.md ("ho chiesto X → l'agente ha fatto Y → mi ha risposto Z")
per ogni task e motore, auto-generata da `evaluate.py` a partire dai log esecuzione.

**Prossimi passi (eval discriminante):**
- Task multi-hop (es. "Quali funzioni usano `APIRouter.post`?").
- Task doc-concept (es. "Come funziona il sistema di dependency injection?").
- Estensione a Semantic Kernel e LangGraph (adattatori già sul roadmap).

## Prossimi passi

1. ~~**Eval set su Tappa 04**~~ **COMPLETATO** — 5 task × 2 motori, metriche, ESEMPI-agentic.md.
2. **Adattatore Semantic Kernel** — kernel SK con skill mapping su `tools.py` + orchestrazione K.
3. **Adattatore LangGraph** — graph workflow plan→retrieve→synthesize via LangGraph state machine.
4. **MCP server** — esporre `shared/retrieval.py` come MCP tools (`search_code`, `search_docs`,
   `find_symbol`, `who_calls`) per Claude Code e agenti.
5. **Custom entity_types per GraphRAG** — usare `derive-entity-types` (Tappa 3C follow-up) per
   migliorare il grafo semantico.
6. **Query planning context-aware** — leveraging AST metadati (symbol_kind, qualname, lineno)
   per disambiguare query a simboli.

## Backlink e contesto

- [[architettura-target]] — disegno finale + roadmap Tappa 4.
- [[01-baseline]], [[02-hybrid-reranking]], [[03-graphrag]] — motori retrieval sottostanti.
- `../../04-agentic-rag/README.md` — design doc (dettagli orchestrator, confronto framework).
