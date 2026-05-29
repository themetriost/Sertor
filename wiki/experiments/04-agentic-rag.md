---
title: 04 Agentic RAG (orchestratore vanilla + framework adapters)
type: experiment
tags: [agentic-rag, orchestrator, llm-tool-calling, shared-facade, autoboxed, semantic-kernel, langraph, mcp, azure-gpt5.4-mini]
created: 2026-05-29
updated: 2026-05-29
status: "vanilla + AutoGen + eval su Azure gpt-5.4-mini (entry point operativo); SK/LangGraph + MCP da fare"
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

## Eval comparativa (vanilla vs AutoGen)

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
**AutoGen**) a **parità di strumenti e prompt** (entrambi usano `tools.py` e SYSTEM_PROMPT). Misura
metriche standardizzate:
- **cited**: la risposta sintetizzata cita il file atteso (boolean).
- **tool_ok**: l'agente ha usato ≥1 strumento ideale da `expected_tools` (boolean).
- **steps**: numero di turni LLM reali (round di tool-call + turno sintesi finale); ora coerente tra vanilla e AutoGen (fix 2026-05-29).
- **tools_called**: numero di tool invocazioni.

**Cache e re-scoring:** `04-agentic-rag/eval_results.json` salva i risultati grezzi (18 righe: 9 task
× 2 motori) con esecuzione LLM. Nuova modalità **`--render-from eval_results.json`** ri-calcola
metriche e rigenera documentazione parlante SENZA chiamate LLM (re-score gratuito quando si raffina
ground-truth).

### Risultati eval — Ollama locale vs Azure gpt-5.4-mini

**Locale (Ollama `qwen3:30b-a3b`, 9 task × 2 motori):**

| Motore | cited (9) | tool_ok (9) | steps (media) | tools_called (media) | Note |
|--------|-----------|-------------|---------------|----------------------|------|
| vanilla | 9/9 (100%) | 9/9 (100%) | 2.2 | 1.3 | routing stabile |
| AutoGen | 8/9 (89%) | 8/9 (89%) | 1.4 | 1.4 | miss su background-doc |

**Azure (gpt-5.4-mini, 9 task × 2 motori, 2026-05-29):**

| Motore | cited (9) | tool_ok (9) | steps (media) | tools_called (media) | Note |
|--------|-----------|-------------|---------------|----------------------|------|
| vanilla | 9/9 (100%) | 9/9 (100%) | 2.7 | 3.2 | routing sempre stabile; più tool-call (modello verboso) |
| AutoGen | 9/9 (100%) | 7/9 (78%) | 2.7 | 3.4 | cita sempre; 2 "tool✗" su routing (search_code vs find_symbol) |

**Lettura onesta sui risultati Azure:**

(a) **Correttezza fattuale 9/9 per entrambi.** Con gpt-5.4-mini (modello forte), il segnale discriminante
non è più "cita il file?" (entrambi lo fanno), bensì **routing degli strumenti** (tool_ok): vanilla
9/9, AutoGen 7/9. L'entry point locale non era affidabile su correttezza dei contenuti; quella
problema scompare con il modello grande.

(b) **Delta su routing:** i 2 "tool✗" di AutoGen sono task di localizzazione (apirouter-def, background-def).
Su questi, l'agente ha scelto `search_code` quando l'ideale era `find_symbol`, oppure ha percorso
multi-hop non ottimale. Tuttavia: **ha comunque citato il file giusto** (cited=True). È una scelta
meno ideale (tool subottimale), non un errore di contenuto.

(c) **gpt-5.4-mini è più "agentico"/verboso del locale:** usa più strumenti per step (media 3.2–3.4 vs
1.3–1.4 su Ollama), fino a 9–11 tool-call su singola query (es. query-param-codedoc). Il modello sceglie
di investigare a fondo (search_code → who_calls → related_docs → search_docs) per sintetizzare risposta
completa. Locale era più parsimonioso (early-exit se trova il simbolo).

(d) **Metrica `passi` ora coerente:** prima di questa run, `passi` per AutoGen contava il numero di tool
(incoerente con vanilla che contava turni). Fix: ora entrambi contano i **turni LLM reali** (round di
tool-call + turno finale di sintesi). Vanilla: 2.7 passi = 1 round tool + 1 sintesi + padding. AutoGen:
stesso conteggio.

**Caveat non-determinismo (persistente):** il modello locale Ollama non è deterministico; run precedenti
davano leggeri delta. Azure gpt-5.4-mini è più stabile su questa eval (1 run).

**Learning:** su un **modello forte**, la metrica `cited` satura (9/9 per entrambi); il segnale discriminante
diventa il routing e l'efficienza (tool_ok, quanti strumenti per sintetizzare). La correttezza fattuale non
differenzia più i framework: è la *qualità del routing* che conta per una soluzione production-grade.

**Implicazione entry point:** il modello locale non è affidabile come agente; **l'entry point operativo è
Azure gpt-5.4-mini**. Il default *di codice* in `config.py` resta local-first (local-first philosophy
del workspace), ma il `.env` di riferimento usa `RAG_BACKEND=azure` (chat gpt-5.4-mini + embeddings
text-embedding-3-large). Superficie futura prevista: agente Claude via MCP.

**Artefatto generato:** [`04-agentic-rag/ESEMPI-agentic.md`](../../04-agentic-rag/ESEMPI-agentic.md)
— doc divulgativa in stile ESEMPI.md ("ho chiesto X → l'agente ha fatto Y → mi ha risposto Z")
per ogni task e motore, auto-generata da `evaluate.py` a partire dai log esecuzione. Aggiornato per i risultati Azure.

**Prossimi passi (eval e framework):**
- **Adattatore Semantic Kernel** — kernel SK con skill mapping su `tools.py` + orchestrazione K.
- **Adattatore LangGraph** — graph workflow plan→retrieve→synthesize via LangGraph state machine.
- **Query planning context-aware** — disambiguare routing doc-vs-code in base al tipo di domanda.

## Prossimi passi

1. ~~**Eval set su Tappa 04**~~ **COMPLETATO su Azure** — 9 task × 2 motori, metrica tool_ok, entry point gpt-5.4-mini.
2. ~~**Stabilità eval**~~ **STABILIZZATO** — modello forte (gpt-5.4-mini) elimina non-determinismo locale; 1 run sufficiente per metrica.
3. **Adattatore Semantic Kernel** — kernel SK con skill mapping su `tools.py` + orchestrazione K (2° framework).
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
