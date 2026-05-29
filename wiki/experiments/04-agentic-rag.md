---
title: 04 Agentic RAG (orchestratore vanilla + framework adapters)
type: experiment
tags: [agentic-rag, orchestrator, llm-tool-calling, shared-facade, autoboxed, semantic-kernel, langraph, mcp]
created: 2026-05-29
updated: 2026-05-29
status: "baseline (vanilla orchestrator) completata; framework adapters (AutoGen/SK/LangGraph) da fare"
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

### Suite test — 19 passed, 1 skipped

- **`test_llm_basic`** — client LLM (`shared/llm.py`) funziona e restituisce un messaggio.
- **`test_llm_with_tools`** — tool-calling: orchestratore riceve risposta con `tool_calls` strutturato.
- **`test_tool_dispatch_unknown`** — tool sconosciuto → errore catturato e tracciato.
- **`test_tool_dispatch_graph`** — `find_symbol` da registry → chiama grafo AST → risultato.
- **`test_retrieval_source_filter`** — facade con `source=code|doc|None` funziona, restituisce
  colonna "source" nei risultati per fusione RRF.

Nota: suite aggiornata al totale 19 passed (precedenti 14 su 01–03; 5 nuovi su 04).

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

## Prossimi passi

1. **Adattatore AutoGen** — wrappare orchestratore vanilla in `groupchat` AutoGen + agent.
2. **Adattatore Semantic Kernel** — kernel SK con skill mapping su `tools.py` + plugin MCP.
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
