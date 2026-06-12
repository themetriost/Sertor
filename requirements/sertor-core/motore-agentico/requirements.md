# Requisiti — Motore RAG agentico
<!-- Deriva da: FEAT-006 (backlog epica sertor-core) -->
<!-- Stato: elicitato — 2026-06-12; FEATURE RINVIATA lo stesso giorno (decisione utente, vedi banner) -->

> **⏸ FEATURE RINVIATA (decisione utente, 2026-06-12).** Durante la risoluzione di DA-1 è
> emersa la presa d'atto che **l'agentic RAG composito esiste già**: l'agente è il *client*
> MCP (Claude Code, domani Copilot) che pianifica le query, sceglie tra i 7 tool, itera e
> sintetizza con citazioni — ed è un modello frontier, migliore nel tool use di un loop
> incorporato con un modello minore. L'**agenzia incorporata** elicitata qui (porta
> `LLMProvider`, loop vanilla, `ask` per CLI/script senza assistente, digest MCP per economia
> di contesto) resta valida come **dote per la ripresa**, quando uno di quei casi d'uso
> diventerà prioritario. DA-2..DA-5 restano aperte e si risolvono alla ripresa; il documento
> NON è stato spec-ato.

## 1. Contesto e problema (perché)

Le tre capacità di retrieval già consegnate — vettoriale (`BaselineEngine`,
`src/sertor_core/engines/baseline.py`), ibrido (`HybridEngine`, FEAT-004) e navigazione
strutturale del code-graph (FEAT-005, quattro tool MCP `find_symbol`/`who_calls`/
`related_docs`/`get_context` in `src/sertor_mcp/server.py:3-6`) — rispondono ciascuna a
una **singola strategia di retrieval** per query. Quando la domanda è semplice e diretta,
questo è sufficiente; quando è **complessa o multi-parte** — «come si configura il backend
ibrido, e chi chiama la factory del composition root?» — l'agente LLM che usa il server MCP
deve orchestrare manualmente sequenze di chiamate a strumenti diversi.

Il prototipo (`prototype/04-agentic-rag/`) ha già dimostrato che questa orchestrazione può
essere **delegata a un loop agentico interno**: l'LLM decide quali strumenti usare
(`tools.py:17-60`), li invoca iterativamente (`orchestrator.py:24-49`), accumula contesto
e sintetizza una **risposta con citazioni** — senza che il consumatore esterno debba
gestire il ciclo. I 9 task dell'eval set (`eval_tasks.json`) hanno ottenuto **9/9 citazioni
corrette** su tutti e quattro i motori (vanilla, autogen, sk, langgraph) con 2.8–5.0 passi
medi (`ESEMPI-agentic.md:9-13`). Il valore è dimostrato: serve portare la capacità in
produzione.

Questa feature introduce la **prima capacità del core che richiede un LLM generativo a
runtime** (non solo un provider di embeddings). Fino ad oggi `src/sertor_core/` usa LLM
solo per gli embeddings; i motori di retrieval sono deterministici. Il motore agentico
aggiunge un nuovo tipo di dipendenza esterna — un provider LLM chat/completion con
tool-calling — che va dietro una **porta `LLMProvider`** (Principio I/II), con adapter
concreti per Ollama locale e Azure OpenAI, testabile tramite un `FakeLLM` deterministico
(Principio V), con **budget esplicito** (max step, max tool call, timeout — Principio IV)
e con **log del consumo** (Principio VI/IX).

**Disambiguazione delle due nature dell'«agentico»** (questione fondamentale di scope):

- **(a) Retrieval agentico** — il loop agentico migliora il *retrieval* stesso: decompone
  la query, esegue retrieval multipli, fonde i risultati → ritorna una lista di
  `RetrievalResult` migliori al consumatore. Potenziale terzo valore di `SERTOR_ENGINE`;
  consumatori invariati.
- **(b) Risposta agentica (ask/research)** — il loop usa i tool esistenti (i 7 del server
  MCP) e produce una **risposta sintetizzata con citazioni** in linguaggio naturale, come
  ha dimostrato il prototipo. Richiede una superficie *nuova* (`ask` nel server MCP, comando
  `sertor-rag ask`); il consumatore non riceve `RetrievalResult` ma testo sintetizzato.

Il prototipo implementa **(b)**: ogni risposta dell'eval cita il file atteso in forma di
testo, non restituisce una lista di chunk. Questa feature elicita i requisiti del **motore
agentico come risposta sintetizzata (b)**; la natura (a) è trattata come variante/Could.

---

## 2. Obiettivi e criteri di successo (LSC)

| ID | Criterio (misurabile, tech-agnostico) | Collegamento |
|----|---------------------------------------|--------------|
| LSC-1 | Su un eval set di almeno 9 task (domande di tipo `localizzazione`, `multi-hop`, `doc-concept`, `code+doc` — replica dell'eval del prototipo sul corpus sertor), il motore agentico cita il file atteso nel **≥ 8/9 task** con `FakeLLM` deterministico che seleziona strumenti preconfigurati. | CS-2 epica, Principio V |
| LSC-2 | Il motore agentico è **invocabile tramite il server MCP** (tool `ask`) e tramite la **CLI `sertor-rag ask`** senza modificare i tool esistenti (`search_code`/`search_docs`/`search_combined`/`find_symbol`/`who_calls`/`related_docs`/`get_context`). | CS-2 epica |
| LSC-3 | Il motore agentico funziona in **locale** con Ollama (`RAG_BACKEND=local`), senza richiedere alcun servizio cloud; il cloud (Azure OpenAI) è configurabile come alternativa. | REQ-E4 epica, Principio II |
| LSC-4 | Il **budget** (max step, max tool call, timeout per query) è **configurabile** e il loop si **ferma esplicitamente** quando il budget è esaurito, emettendo una risposta parziale con un indicatore di troncamento esplicito (non un'eccezione non gestita). | Principio IV, VI |
| LSC-5 | Il motore agentico è **testabile senza rete** con un `FakeLLM` deterministico che simula un ciclo di tool-calling e una sintesi finale; i test unitari del loop, del budget e delle citazioni passano con `pytest -m "not cloud"`. | Principio V |
| LSC-6 | Ogni risposta prodotta dal motore cita **solo file recuperati nel corso del loop** (nessun path inventato); il test di accettazione verifica che ogni path citato sia presente nella traccia dei tool call. | Principio IV (no null silenzioso: le citazioni false sono il corrispettivo a livello di risposta) |
| LSC-7 | Il log strutturato emesso per ogni query agentifica include: numero di passi, tool chiamati (nome+argomento), token/LLM-call se disponibili, elapsed_ms totale; il log non contiene segreti. | Principio IX |
| LSC-8 | Il motore agentico funziona su **qualunque corpus** indicizzato col nucleo sertor, senza assunzioni sulla struttura dell'ospite. | Principio X |

---

## 3. Stakeholder e attori

| Attore | Ruolo |
|--------|-------|
| **Agente LLM (Claude Code / client MCP)** | Beneficiario principale: invoca `ask` per ottenere una risposta sintetizzata a domande complesse sulla codebase, senza orchestrare il loop manualmente. |
| **Owner/maintainer** | Configura il provider LLM e il budget; verifica la qualità delle risposte; fissa l'eval set. |
| **Server MCP `sertor-rag`** (`src/sertor_mcp/server.py`) | Consumatore diretto: aggiunge il tool `ask` che delega al motore agentico del core. |
| **CLI `sertor-rag`** | Consumatore: aggiunge il sottocomando `ask` che delega al motore agentico. |
| **`sertor-core` (dipendenza a monte)** | Nucleo su cui il motore agentico si appoggia: le sue porte, la facade, il graph service, il composition root, Settings, log_event. |
| **Provider LLM (Ollama / Azure OpenAI)** | Dipendenza esterna dietro la porta `LLMProvider`; interscambiabile via config. |
| **Codebase target** | Il corpus su cui il loop recupera contesto; non presupposta nella struttura. |

---

## 4. Ambito

### In ambito

- **Porta `LLMProvider`** nel domain (`src/sertor_core/domain/ports.py`): astrazione del
  provider LLM chat/completion con tool-calling; contratto minimo: metodo `chat(messages,
  tools)` → risposta con eventuale lista di tool call e contenuto testuale. Definita come
  `Protocol` (structural typing), coerente con le 6 porte esistenti.
- **Adapter `LLMProvider`** per Ollama locale e Azure OpenAI, cablati nel composition root
  (`src/sertor_core/composition.py`), con import lazy (Principio III). La scelta del provider
  avviene via `Settings` (nuovo campo, coerente con `embed_provider`/`store_backend`).
- **`FakeLLM` deterministico** nelle fixture di test (`tests/fixtures/mocks.py` o equivalente):
  simula sequenze preconfigurate di tool call + risposta finale; nessuna rete, nessun cloud.
- **Loop agentico vanilla** (nessun framework di orchestrazione): implementazione
  in-house basata sul pattern dell'orchestratore del prototipo (`orchestrator.py:24-49`).
  Il loop: invoca `LLMProvider.chat(messages, tools)` → se tool call → esegui → accoda
  risultato → ripeti; se risposta finale → ritorna; se budget esaurito → sintetizza con
  avviso. Zero dipendenze da AutoGen, LangGraph, Semantic Kernel.
- **Tool set del loop**: le capacità già esistenti del core — `RetrievalFacade` (search_code,
  search_docs, search_combined) e `CodeGraph` service (find_symbol, who_calls, related_docs,
  get_context) — esposte al loop come descrittori di tool (nome, descrizione, schema
  parametri) nello stesso formato `TOOLS` del prototipo (`tools.py:17-60`). L'agente NON
  reimplementa retrieval.
- **Risposta strutturata** contenente: testo sintetizzato + lista di riferimenti citati
  (path#chunk o path:lineno) estratti dalla traccia dei tool call + traccia del loop (per
  logging/test). La struttura è un tipo di dominio (`AgenticResponse`) distinto da
  `RetrievalResult`.
- **Regola anti-allucinazione**: le citazioni nella risposta finale sono filtrate alla
  traccia dei risultati effettivamente recuperati nel loop; il motore NON aggiunge path
  fuori dalla traccia.
- **Comportamento su «non trovato»**: se nessun tool restituisce risultati utili, la
  risposta è esplicita («non trovato nel corpus»), non inventata (coerente col system prompt
  del prototipo: «Non inventare: se non trovi nulla, dichiaralo» — `tools.py:103`).
- **Budget configurabile** in `Settings`: `max_steps` (cicli LLM, default 6 come nel
  prototipo `orchestrator.py:24`), `max_tool_calls` (totale call nel loop), `agent_timeout_s`
  (timeout della query agentifica); tutti con default centralizzati.
- **Stop esplicito a budget esaurito**: il loop emette un messaggio di sintesi forzata (come
  nel prototipo `orchestrator.py:45-49`), non un'eccezione non gestita.
- **Tool MCP `ask`** nel server MCP (`src/sertor_mcp/server.py`): tool aggiunto ai 7
  esistenti, sottile wrapper sul motore agentico del core; restituisce un oggetto con testo
  + citazioni.
- **Sottocomando CLI `sertor-rag ask`**: superficie sottile sul motore agentico.
- **Eval set** sul corpus sertor: almeno 9 task (replica strutturata dell'eval del prototipo
  `eval_tasks.json`: almeno 3 tipi di domanda — localizzazione, multi-hop, doc-concept — con
  file atteso e strumenti ideali dichiarati), come fixture versionata per i test di
  accettazione.
- **Log strutturati** per ogni query agentifica (Principio IX): passi, tool call, elapsed_ms,
  provider LLM, e token se esposti dall'adapter.
- **Configurazione Settings**: nuovi campi per provider LLM chat (`llm_provider`,
  `llm_deployment`/`ollama_chat_model`, temperature, max_steps, timeout), coerenti con il
  campo `embed_provider` esistente; default centralizzati.
- **Retro-compatibilità**: i 7 tool MCP esistenti e il comportamento di tutti i motori
  retrieval (`SERTOR_ENGINE`) rimangono invariati.

### Fuori ambito

- **Retrieval agentico (natura a)**: il loop agentico come terzo valore di `SERTOR_ENGINE`
  che restituisce `RetrievalResult` migliorati (decomposizione query → retrieval multipli →
  fusione) è fuori da questa feature. È Could (vedi §9); richiede un design separato
  dell'interfaccia.
- **Framework di orchestrazione** (AutoGen, LangGraph, Semantic Kernel): il prototipo li ha
  confrontati a parità di tool e i risultati sono equivalenti (`ESEMPI-agentic.md:9-13`);
  la differenza è di orchestrazione, non di qualità. Il loop vanilla in-house è il Must; i
  framework sono dipendenze pesanti (Principio III) fuori ambito qui.
- **Multi-agente / agenti paralleli**: il loop agisce come singolo agente sequenziale.
- **Memoria persistente tra sessioni**: il loop ha stato solo per la durata di una query.
- **Generazione di codice o modifiche al repo**: il motore è di *sola lettura*.
- **Ottimizzazione del numero di token / compressione del contesto**: out of scope al MVP.
- **GUI/web**.
- **Distribuzione del pacchetto** (epica `sertor-cli`).
- **Modifica della `RetrievalFacade` o dei motori esistenti** (sono consumati come tool,
  non modificati).

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Porta `LLMProvider` e architettura

**REQ-001 (Ubiquitous)** *The system shall expose an `LLMProvider` port (Protocol) in
`src/sertor_core/domain/ports.py` defining at minimum the following: a `chat(messages,
tools)` method that accepts a list of messages and an optional list of tool descriptors,
and returns a response object containing at minimum a text content field and a list of
tool calls (each with tool name and arguments); and a `name` attribute identifying the
provider.*

> Principio I/II: il domain non importa SDK concreti di LLM. Pattern già consolidato per le
> 6 porte esistenti (`EmbeddingProvider`, `VectorStore`, `LexicalIndex`, `Reranker`,
> `CodeGraph`, `RetrieverStrategy` in `src/sertor_core/domain/ports.py:23-192`).

**REQ-002 (Ubiquitous)** *The concrete LLM adapters shall live in a dedicated subdirectory
under `src/sertor_core/adapters/` and shall be wired exclusively in
`src/sertor_core/composition.py`; no service, engine, or other adapter shall import an LLM
adapter directly.*

> Principio I: wiring solo nel composition root, come già per embedder (`build_embedder`),
> store (`build_store`) e graph service (`build_graph_service`) in `composition.py:49-127`.

**REQ-003 (Ubiquitous)** *The LLM adapter dependencies (OpenAI/Azure SDK, Ollama SDK)
shall be importable lazily inside the composition root builder functions, so that the base
`sertor-core` package is importable without any LLM SDK installed.*

> Principio III: dipendenze pesanti isolabili, import lazy. Pattern già applicato per
> `azure` e `rerank` in `composition.py:53-66`.

**REQ-004 (Ubiquitous)** *The system shall provide a `FakeLLM` implementation of the
`LLMProvider` port in the test fixtures (`tests/fixtures/mocks.py` or equivalent) that
accepts a pre-configured sequence of responses (tool-call sequences and a final text answer)
and replays them deterministically, without any network access.*

> Principio V: testabilità senza rete. Il `FakeLLM` è il corrispettivo di `FakeEmbedder`
> e `InMemoryStore` già presenti nelle fixture di test del core.

**REQ-005 (Ubiquitous)** *The system shall expose a new Settings field selecting the LLM
provider for the agentic engine (`llm_provider`: `local` or `azure`), defaulting to the
same value as `embed_provider` (i.e., inheriting the `backend` choice) with the ability to
override independently; all LLM-specific parameters (deployment/model name, temperature,
max tokens) shall be centralised in `Settings` with no hardcoded defaults in the engine.*

> Principio VIII: configurabilità centralizzata. La scelta indipendente di LLM provider
> vs embeddings provider è coerente con la manopola distinta `store_backend` (già separata
> da `embed_provider` in `composition.py:70-87`).

**REQ-006 (Ubiquitous)** *The agentic engine shall be constructed via a dedicated
`build_agentic_engine(settings)` factory in `src/sertor_core/composition.py`, which wires
the `LLMProvider`, the `RetrievalFacade`, and the `CodeGraph` service without duplicating
their construction logic.*

> Principio I: factory dedicata, non duplicazione dei build. Il pattern è già stabilito per
> `build_graph_service`, `build_facade`, `build_indexer` in `composition.py:108-203`.

### Gruppo B — Loop agentico vanilla

**REQ-010 (Event-driven)** *When the agentic engine receives a question, the system shall
execute a tool-use loop: invoke `LLMProvider.chat(messages, tool_descriptors)`, inspect the
response for tool calls, dispatch each tool call to the appropriate core capability
(`RetrievalFacade` or `CodeGraph`), append the result to the message context, and repeat
until the LLM returns a final answer (no tool calls) or the configured budget is exhausted.*

> Ancora: `prototype/04-agentic-rag/orchestrator.py:24-49`. Il loop vanilla in-house è il
> riferimento diretto; nessun framework di orchestrazione.

**REQ-011 (Ubiquitous)** *The tool dispatch within the agentic loop shall delegate
exclusively to existing core capabilities: `RetrievalFacade.search_code`,
`RetrievalFacade.search_docs`, `RetrievalFacade.search_combined` (for similarity retrieval)
and the `CodeGraph` service's `find_symbol`, `who_calls`, `related_docs`, `get_context`
(for structural navigation); no retrieval logic shall be re-implemented in the agentic
engine.*

> Principio I/III: DRY. Il prototipo dimostra lo stesso principio con `tools.py:62-69`
> (dispatch verso `retrieval.search_code`, `retrieval.find_symbol`, ecc.).

**REQ-012 (Ubiquitous)** *The tool descriptors exposed to the LLM shall use the same
semantic descriptions and parameter schemas as defined in the prototype
(`prototype/04-agentic-rag/tools.py:17-60`), adapted to the production corpus; they shall
be defined as a versioned constant, not inline in the loop.*

> Ancora: `tools.py:17-60`. La descrizione di ogni tool orienta la strategia dell'LLM
> (es. «usa `find_symbol` per localizzare un simbolo, `search_docs` per concetti»).

**REQ-013 (Ubiquitous)** *The system shall include a default system prompt for the agentic
engine that instructs the LLM to: decompose the question into sub-goals, choose appropriate
tools iteratively, synthesise a final answer citing files with the format `path#chunk` or
`path:lineno`, and explicitly declare when nothing is found rather than inventing citations.*

> Ancora: `prototype/04-agentic-rag/tools.py:94-104` (SYSTEM_PROMPT). La regola «non
> inventare» e il formato di citazione sono comportamenti di qualità verificabili nei test.

**REQ-014 (Ubiquitous)** *The system prompt shall be configurable (overridable via
`Settings` or as a parameter to the engine constructor), so that corpus-specific
customisation is possible without modifying the engine code.*

> Principio VIII. Il corpus-target può avere convenzioni diverse (es. lingua, naming) che
> richiedono adattamento del prompt senza toccare la logica del loop.

### Gruppo C — Budget e stop esplicito

**REQ-020 (Ubiquitous)** *The system shall enforce a configurable step budget (`max_steps`,
default: 6) and a configurable per-query timeout (`agent_timeout_s`); both shall be
centralised in `Settings` with no hardcoded values in the engine.*

> Principio IV/VIII. La costante `max_steps=6` è il valore del prototipo
> (`orchestrator.py:24`); il timeout protegge dalla latenza incontrollata di provider LLM
> lenti o non rispondenti.

**REQ-021 (Unwanted behaviour)** *If the step budget is exhausted before the LLM returns a
final answer without tool calls, then the system shall send a final forced-synthesis message
to the LLM requesting a response with citations and without further tool calls, and return
the LLM's reply as the answer; the budget exhaustion shall be recorded in the structured log
and in the `AgenticResponse` metadata.*

> Ancora: `prototype/04-agentic-rag/orchestrator.py:45-49`. Il prototipo dimostra questa
> strategia: «Sintetizza ora la risposta finale con le citazioni, senza usare altri
> strumenti.» Il log di budget exhaustion consente al consumatore di sapere che la risposta
> è parziale.

**REQ-022 (Unwanted behaviour)** *If the per-query timeout elapses, then the system shall
abort the loop, return a structured error response indicating the timeout (not an unhandled
exception), and emit a structured log event recording `agent_timeout`.*

> Principio IV: errore esplicito, azionabile. Il consumatore (tool MCP `ask`) può
> propagarlo all'utente/agente client in forma comprensibile.

**REQ-023 (Ubiquitous)** *The system shall also enforce a configurable `max_tool_calls`
budget (total tool calls across all steps, default: 15); if exceeded within a step, the
loop shall behave as in REQ-021 (forced synthesis), recording `max_tool_calls_exceeded` in
the log.*

> Principio IV. Un LLM che in un singolo step richiede decine di tool call (comportamento
> anomalo) non deve propagare costi illimitati.

### Gruppo D — Risposta strutturata e citazioni

**REQ-030 (Ubiquitous)** *The system shall define a domain entity `AgenticResponse`
containing at minimum: a `text` field (the synthesised answer in natural language), a
`citations` field (list of references `path#chunk` or `path:lineno` actually retrieved
during the loop), a `trace` field (list of tool calls with name, arguments, and result
preview), `steps` and `tool_calls_count` integers, and a `truncated` boolean (True if
budget was exhausted).*

> Entità di dominio distinta da `RetrievalResult` (che è una lista di chunk, non una
> risposta sintetizzata). Il pattern di definizione è in
> `src/sertor_core/domain/entities.py`.

**REQ-031 (Ubiquitous)** *The `citations` field of `AgenticResponse` shall contain only
path references that appear in the results of at least one tool call in the `trace`; the
engine shall filter out any path that the LLM introduces in its text but was not retrieved
during the loop.*

> Principio IV: la regola anti-allucinazione a livello di citazioni è verificabile
> automaticamente (test: ogni citation è nel trace). Non impedisce che il testo della
> risposta contenga inferenze, ma le citazioni devono essere ancorate a evidenza reale.

**REQ-032 (Unwanted behaviour)** *If no tool call in the loop returns any result (all tools
return empty results), then the system shall return an `AgenticResponse` with an explicit
`text` stating that nothing was found for the question in the corpus, with `citations` empty
and `truncated` False.*

> Ancora: `prototype/04-agentic-rag/tools.py:76` («(nessun risultato)») e SYSTEM_PROMPT:
> «Non inventare: se non trovi nulla, dichiaralo.»

### Gruppo E — Superfici: tool MCP `ask` e CLI `ask`

**REQ-040 (Event-driven)** *When the MCP client invokes the `ask` tool with a `question`
parameter, the system shall execute the agentic loop via the core's agentic engine and
return a structured response containing at minimum the synthesised text and the list of
citations, without modifying the behavior of the existing 7 MCP tools.*

> Non-breaking additive: i 7 tool esistenti rimangono invariati (coerente col pattern
> `add_without_modifying` già seguito in FEAT-005 per i 4 tool di grafo, `server.py:3-6`).

**REQ-041 (Ubiquitous)** *The `ask` tool in the MCP server shall be a thin wrapper on the
core's agentic engine: no agentic logic shall be re-implemented in `src/sertor_mcp/`.*

> Principio I: thin-consumer, come per tutti gli altri tool del server MCP
> (`server.py:9-10`: «Consumatore sottile»).

**REQ-042 (Unwanted behaviour)** *If the `LLMProvider` is not configured (no provider
selected or no credentials available) when the `ask` tool or the `sertor-rag ask` command
is invoked, then the system shall return a structured error response stating that a
configured LLM provider is required, not a crash or a silent empty answer.*

> Principio IV / REQ-E3 epica: «The system shall require a configured LLM target before
> performing any operation that needs generation/agentic reasoning.»

**REQ-043 (Event-driven)** *When the `sertor-rag ask <question>` CLI command is invoked,
the system shall run the agentic loop, print the synthesised text to stdout, and print the
citations as a list of references to stdout; the exit code shall be 0 on success and non-zero
on error (timeout, missing LLM config).*

> Superficie sottile sulla CLI esistente (`src/sertor_core/cli/` o `packages/sertor/`), per
> consentire l'uso interattivo dal terminale (dogfooding e test manuali).

### Gruppo F — Osservabilità e costo

**REQ-050 (Event-driven)** *When the agentic loop completes (or is truncated by budget),
the system shall emit a structured log event (via `log_event`,
`src/sertor_core/observability/logging.py`) recording at minimum: question (first 120 chars),
steps, tool_calls_count, truncated, elapsed_ms, llm_provider, and — where the provider
exposes them — prompt_tokens and completion_tokens.*

> Principio IX. Il log dei token è il proxy del costo per query (Principio VI: «il
> costo/latenza delle chiamate LLM MUST essere considerato»). Se il provider non espone i
> token (es. Ollama in alcuni modi), il campo è assente senza errore.

**REQ-051 (Event-driven)** *When each tool call is dispatched within the loop, the system
shall emit a structured log event recording: tool_name, argument summary (first 80 chars of
the serialised arguments), result_count or result_preview, elapsed_ms.*

> Principio IX. Consente di ricostruire la traccia di ogni query senza rileggere il codice.

**REQ-052 (Ubiquitous)** *Log records shall never contain secret values (API keys,
credentials, full system prompt if it contains sensitive data); redaction follows the
existing `log_event` pattern (`src/sertor_core/observability/logging.py`).*

### Gruppo G — Misura della qualità e eval set

**REQ-060 (Ubiquitous)** *The system shall include a versioned eval set for the sertor
corpus containing at least 9 task entries, each specifying: a question, at least one
expected file path (relative), at least one expected tool (from the 7 available), and a
task type (`localizzazione`, `multi-hop`, `doc-concept`, `code+doc`); the set shall cover
at least 3 of the 4 task types.*

> Principio V. L'eval set è la replica strutturale di `prototype/04-agentic-rag/
> eval_tasks.json` sul corpus sertor. Il minimo di 9 task garantisce copertura per tipo e
> confrontabilità con i risultati del prototipo (9 task, 4 motori, 9/9 citazioni).

**REQ-061 (Event-driven)** *When the agentic eval runs on the eval set (with `FakeLLM` for
the unit path and with a real provider for the acceptance path), the system shall report for
each engine run: cited_count / total_tasks, tool_ok_count / total_tasks, avg_steps,
avg_tool_calls; the `cited` criterion is the acceptance gate (LSC-1: ≥ 8/9 with FakeLLM).*

> Ancora: `prototype/04-agentic-rag/evaluate.py:110-121` (`_metrics_table`): le stesse
> metriche (cita atteso, tool giusto, passi medi, tool medi) adattate al corpus sertor.

**REQ-062 (Ubiquitous)** *The eval set entries shall use relative file paths and shall not
encode assumptions about the internal structure of the sertor project beyond what is
directly verifiable in the corpus.*

> Principio X: host-agnostico anche per le fixture.

**REQ-063 (Ubiquitous)** *The eval with `FakeLLM` shall run without network access (`pytest
-m "not cloud"`); the eval with a real provider shall be gated by the `cloud` marker.*

> Principio V: la CI locale (senza cloud) deve coprire la logica del loop, del budget, e
> delle citazioni; la qualità della sintesi (che dipende dal modello reale) è misurabile
> solo col provider reale e resta fuori dalla CI obbligatoria.

### Gruppo H — Retro-compatibilità e non-distruttività

**REQ-070 (Ubiquitous)** *The introduction of the agentic engine and the `ask` tool shall
not modify the interfaces of `BaselineEngine`, `HybridEngine`, `RetrievalFacade`,
`CodeGraph`, or any existing MCP tool; all changes are additive.*

**REQ-071 (Ubiquitous)** *The agentic engine shall be non-destructive on the target
repository: it performs read-only operations (queries to existing indexes and graphs); it
shall not write, modify, or delete any file in the corpus.*

**REQ-072 (Ubiquitous)** *Setting `SERTOR_ENGINE=baseline` or `SERTOR_ENGINE=hybrid` shall
produce behavior identical to the current system for all existing consumers; the agentic
engine is orthogonal to the `SERTOR_ENGINE` selection.*

> Il motore agentico è una capacità distinta dalla selezione `SERTOR_ENGINE` (che riguarda
> il retrieval deterministico). La relazione è analoga a quella del graph service (FEAT-005,
> REQ-013/062 di quel documento).

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| NFR-01 | **Dipendenze verso l'interno** (Principio I) | Il motore agentico dipende solo dalle porte del dominio (`LLMProvider`, `RetrievalFacade` come facade, porta `CodeGraph`) e dalle entità (`AgenticResponse`, `RetrievalResult`, `SymbolHit`); non importa SDK concreti di LLM né framework di orchestrazione. |
| NFR-02 | **Isolamento dipendenze pesanti** (Principio III) | Gli SDK LLM (OpenAI, Ollama client) sono installabili separatamente come extra `llm` (o come dipendenza del composition root); la loro assenza non impedisce l'installazione del pacchetto base né l'uso dei motori vettoriale/ibrido/grafo. |
| NFR-03 | **Testabilità senza rete** (Principio V) | Il motore agentico (loop, budget, citazioni, anti-allucinazione) è testabile con `FakeLLM` deterministico, senza cloud, senza rete; i test unitari passano con `pytest -m "not cloud"`. |
| NFR-04 | **Costo per query** (Principio VI) | Il costo di una query agentifica (chiamate LLM) è ordini di grandezza superiore al retrieval deterministico; il log dei token (REQ-050) e il budget esplicito (REQ-020) sono i meccanismi di controllo. Il sistema non deve incentivare loop lunghi: il budget di default (`max_steps=6`) deve essere sufficiente per il 90% dei task dell'eval set. |
| NFR-05 | **Latenza** | Una query agentifica tipica (3-5 passi, provider cloud) deve completarsi in un tempo accettabile per uso interattivo da un agente LLM (< 30 s); la soglia si verifica empiricamente nel dogfood. Il timeout configurabile (REQ-020) è il meccanismo di protezione. |
| NFR-06 | **Configurabilità centralizzata** (Principio VIII) | Tutti i parametri del motore agentico (provider LLM, deployment, budget, timeout, system prompt) sono in `Settings`; nessun default hardcodato nei componenti. |
| NFR-07 | **Osservabilità** (Principio IX) | Ogni query agentifica emette log strutturati sufficienti a ricostruire il ciclo senza leggere il codice (REQ-050/051/052); in particolare il log dei token è fondamentale per monitorare il costo. |
| NFR-08 | **Host-agnosticità** (Principio X) | Il motore agentico non presuppone la struttura interna del progetto ospite: il corpus target, le collezioni, il grafo sono passati come configurazione, non come costanti. |
| NFR-09 | **Retro-compatibilità** | Nessun consumatore esistente (facade, MCP, CLI, engine baseline, engine hybrid, graph service) richiede modifiche di codice o di configurazione per continuare a funzionare dopo l'introduzione del motore agentico. |
| NFR-10 | **Local-first** (Principio II) | Il motore agentico deve funzionare interamente in locale con Ollama (chat + tool calling supportato); il cloud è configurabile ma non obbligatorio. L'adapter Ollama è il primo target di test locale (REQ-003/LSC-3). |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli

- **V-1**: Il motore agentico è **ortogonale a `SERTOR_ENGINE`**: non viene selezionato via
  quella manopola (Principio I, REQ-072).
- **V-2**: Il wiring del motore agentico avviene **solo nel composition root**
  (`src/sertor_core/composition.py`, Principio I, REQ-002/006).
- **V-3**: Nessun segreto su file versionati (REQ-E5 epica); le chiavi LLM transitano via
  `.env`.
- **V-4**: Python ≥ 3.11 (vincolo d'epica).
- **V-5**: L'eval set (REQ-060) è scritto come fixture nel repo con path relativi; non
  dipende da file esterni non versionati.
- **V-6**: I motori baseline, ibrido e il graph service restano pienamente funzionanti e
  invariati (REQ-070/072).
- **V-7**: Il loop agentico è **solo lettura** sul corpus: non modifica indici, sorgenti o
  il grafo (REQ-071).
- **V-8**: Il provider LLM **deve supportare tool calling** (function calling nel senso
  OpenAI/Ollama). Modelli Ollama che non supportano tool calling non possono essere usati
  come `LLMProvider` per il loop agentico; la porta deve segnalarlo (REQ-042).

### Assunzioni

- **A-1**: Il prototipo `orchestrator.py` (loop vanilla) è il riferimento funzionale di
  qualità accettabile: 9/9 citazioni su 9 task in 2.8 passi medi con gpt-5.4-mini.
  La produzione mantiene la qualità misurando sullo stesso set adattato al corpus sertor.
- **A-2**: Il provider LLM di riferimento per il dogfooding è Azure OpenAI (da CLAUDE.md:
  `RAG_BACKEND=azure`; `gpt-5.4-mini` usato nel prototipo); il provider locale di
  riferimento è Ollama con un modello che supporta tool calling (es. `llama3.1` o
  equivalente disponibile nel setup).
- **A-3**: Il loop vanilla (nessun framework) è sufficiente per il MVP; i framework
  (AutoGen, LangGraph, SK) sono comparabili nel prototipo e non aggiungono qualità
  misurabile a parità di tool. L'overhead di dipendenza è ingiustificato (Principio III).
- **A-4**: Il `FakeLLM` deterministico è sufficiente per validare la logica del loop,
  del budget, e delle citazioni. La qualità della sintesi (la capacità di formulare risposte
  pertinenti) richiede il provider reale ed è coperta dall'eval `cloud` (REQ-063).
- **A-5**: Il set di 7 tool (3 retrieval + 4 grafo) del server MCP è il catalogo completo
  degli strumenti disponibili al loop agentivo nel MVP; tool aggiuntivi (es. `ask` stesso
  come tool interno — meta-agente) sono fuori scope.
- **A-6**: La porta `LLMProvider` è definita per tool calling (chat con lista di tool +
  risposta con tool call); non è richiesto streaming della risposta al MVP.
- **A-7**: Sull'eval set con `FakeLLM`, la metrica `cited` (LSC-1: ≥ 8/9) si ottiene
  preconfigurandoo il `FakeLLM` per selezionare i tool giusti per ciascun task; la metrica
  non valuta la qualità della sintesi ma la correttezza della logica del loop e delle
  citazioni.

### Dipendenze

- **D-1**: `sertor-core` in `master` — nucleo retrieval (FEAT-001), motore ibrido (FEAT-004,
  default), graph service (FEAT-005), porte (`domain/ports.py`), entità (`domain/entities.py`),
  `Settings` (`config/settings.py`), composition root (`composition.py`), `log_event`
  (`observability/logging.py`).
- **D-2**: `RetrievalFacade` in `src/sertor_core/services/retrieval.py` — fornisce
  `search_code`, `search_docs`, `search_combined` al loop.
- **D-3**: `CodeGraph` service (FEAT-005, `build_graph_service` in `composition.py:108-127`)
  — fornisce `find_symbol`, `who_calls`, `related_docs`, `get_context` al loop.
- **D-4**: `src/sertor_mcp/server.py` — consumatore del tool `ask`; i 7 tool esistenti
  devono restare invariati.
- **D-5** (opzionale, extra `llm`): SDK LLM (OpenAI/Azure client e/o Ollama client); deve
  essere installabile separatamente senza impattare il pacchetto base.
- **D-6**: `prototype/04-agentic-rag/orchestrator.py`, `tools.py`, `evaluate.py`,
  `eval_tasks.json` — riferimento funzionale; la produzione ne è la riscrittura
  production-grade con porta LLM, entità di dominio, test e eval set proprio.

---

## 8. Rischi

| ID | Rischio | Prob. | Impatto | Mitigazione |
|----|---------|-------|---------|-------------|
| R-1 | **Qualità della sintesi dipendente dal modello**: il motore produce testo sintetizzato il cui contenuto dipende dal modello LLM. Un modello debole (piccolo Ollama) può citare file sbagliati o non citare. | Alta | Medio | LSC-1: la metrica `cited` misura la qualità sul corpus sertor con provider reale. Il `FakeLLM` testa la logica; il provider reale testa la qualità. L'utente può scegliere un modello più potente via config. |
| R-2 | **Costo per query non controllato**: senza budget, un loop che non converge genera un numero illimitato di chiamate LLM. | Media | Alto | REQ-020/021/023: budget `max_steps` + `max_tool_calls` + timeout; tutti configurabili e con default prudenti. Il log dei token (REQ-050) consente monitoraggio. |
| R-3 | **Tool calling non supportato da tutti i modelli Ollama**: non tutti i modelli di Ollama implementano la specifica di function calling in modo affidabile. | Alta | Medio | REQ-042: se il provider non supporta tool calling la porta lo segnala con errore esplicito. La scelta del modello compatibile è responsabilità della configurazione. Vincolo V-8. |
| R-4 | **Dipendenza SDK LLM pesante inquina il pacchetto base**: il client OpenAI/Azure introduce dipendenze transitive (httpx, pydantic v2) che possono creare conflitti. | Media | Medio | NFR-02: extra isolato, import lazy (REQ-003); la CI base (`pytest -m "not cloud"`) non installa l'extra LLM. |
| R-5 | **Latenza inaccettabile su provider locale**: Ollama con modelli grandi su hardware consumer può avere latenze di 30-120 s per query, rendendo il motore inutilizzabile in interattivo. | Media | Basso | NFR-05: timeout configurabile; il default del cloud rimane l'opzione primaria per l'uso interattivo. L'utente locale può scegliere un modello più leggero. |
| R-6 | **Violazione Principio I**: logica agentica fuori dal composition root o dipendenze concrete LLM nel domain. | Bassa | Alto | REQ-001/002/006: vincoli espliciti; Constitution Check al momento del design. |
| R-7 | **Allucinazione di citazioni**: l'LLM potrebbe citare file non recuperati se la regola di filtro (REQ-031) non è robusta. | Media | Alto | REQ-031: filtro delle citazioni alla traccia, verificabile automaticamente nei test unitari con `FakeLLM`. LSC-6: test esplicito che ogni citation è nel trace. |
| R-8 | **Eval set non rappresentativo del corpus sertor**: se i 9 task sono tutti di tipo `localizzazione` (facile per il grafo), non misurano la qualità multi-hop o doc-concept. | Media | Medio | REQ-060: obbligo di coprire almeno 3 dei 4 tipi, con distribuzione ispirata al prototipo (5 localizzazione + 2 multi-hop + 1 doc-concept + 1 code+doc). |

---

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivazione |
|----------|-----------|-------------|
| **Must** | REQ-001..006 (porta + architettura), REQ-010..014 (loop vanilla), REQ-020..023 (budget), REQ-030..032 (risposta strutturata + anti-allucinazione), REQ-040..042 (tool MCP ask + error handling), REQ-060, REQ-062..063 (eval set + marker), REQ-070..072 (retro-compatibilità), NFR-01..04, NFR-06, NFR-08..10 | Il ciclo minimo dimostrabile: porta LLM + loop + budget + risposta citata + tool MCP `ask` + eval set = la feature è «fatta» (Principio V). |
| **Should** | REQ-043 (CLI `ask`), REQ-050..052 (osservabilità), REQ-061 (metriche eval completo), NFR-05 (latenza), NFR-07 (osservabilità) | Completano la qualità, le superfici e l'osservabilità; essenziali per uso in produzione ma non bloccanti per la dimostrazione del valore core. |
| **Could** | Retrieval agentico (natura a — terzo valore di `SERTOR_ENGINE` che restituisce `RetrievalResult` da loop multi-step); adapter LangGraph/AutoGen come alternativa framework al loop vanilla (valido solo se la qualità è dimostrativamente superiore sul corpus sertor e il costo di dipendenza è giustificato); log token dettagliato per provider Ollama (ove disponibile via API). | Valore incrementale; richiedono infrastruttura aggiuntiva o evidenza comparativa. |
| **Won't (questa feature)** | Memoria persistente tra sessioni, modifica di file nel corpus, generazione di codice, multi-agente/parallelo, compressione del contesto, GUI/web, distribuzione pacchetto, framework AutoGen/SK/LangGraph come Must. | Fuori ambito dichiarato. |

---

## 10. Domande aperte

Le seguenti questioni richiedono decisione prima del design. Per ciascuna: contesto dal
codice reale, opzioni con pro/contro, raccomandazione motivata.

---

### DA-1 — Decomposizione dell'«agentico»: risposta sintetizzata (b) come Must, retrieval agentico (a) come Could

**Contesto.** L'epica descrive FEAT-006 come «retrieval iterativo/multi-step, query
planning» — formulazione ambigua che può indicare sia (a) un motore di retrieval migliore
sia (b) una risposta sintetizzata. Il prototipo implementa chiaramente (b) (risposta in
linguaggio naturale con citazioni, `orchestrator.py:36`). La distinction impatta l'interfaccia:
(a) restituisce `list[RetrievalResult]` (consumatori invariati, terzo valore di
`SERTOR_ENGINE`); (b) restituisce `AgenticResponse` (superficie nuova, tool MCP `ask`).

- **Opzione A — (b) as Must, (a) as Could** (come questo documento): il valore primario è
  la risposta sintetizzata; il retrieval agentico è una variante futura.
  - Pro: allineato al prototipo, al caso d'uso principale (agente LLM che vuole una risposta
    contestuale), alla dimostrazione di valore più immediata.
  - Contro: introduce una superficie nuova (`ask`) e un tipo di risposta nuovo
    (`AgenticResponse`); i consumatori esistenti non ne beneficiano automaticamente.
- **Opzione B — (a) as Must, (b) as Could**: il loop agentico migliora il retrieval
  (terzo valore `SERTOR_ENGINE=agentic`); la risposta sintetizzata è una variante.
  - Pro: consumatori invariati (la facade restituisce sempre `RetrievalResult`); più
    coerente con il modello di selezione engine.
  - Contro: non è quanto dimostra il prototipo; il valore per l'agente LLM (risposta
    contestuale) richiede comunque la sintesi.
- **Opzione C — Entrambi as Must**: implementare sia (a) sia (b).
  - Pro: copertura completa.
  - Contro: ambito molto più largo; rischio di sotto-stimare lo sforzo (R-4 epica).

**Raccomandazione**: **Opzione A**. Il prototipo dimostra che la risposta sintetizzata (b)
è il valore osservabile; il retrieval agentico (a) è un miglioramento tecnico interno che
richiede un design separato della fusione multi-step. La superficie `ask` è additive e non
rompe nulla.

[DA CHIARIRE: conferma o emendamento prima del design.]

---

### DA-2 — Provider LLM: manopola autonoma o eredita da `embed_provider`/`backend`?

**Contesto.** Oggi `Settings` ha `embed_provider` (`local`/`azure`) e `store_backend`
(idem), manopole distinte (confermato utile in FEAT-004). Il provider LLM chat può essere
una terza manopola autonoma o un alias di `embed_provider`. Nel dogfooding attuale
(`RAG_BACKEND=azure`), sia gli embeddings sia il LLM generativo puntano ad Azure OpenAI;
tuttavia uno scenario comune è embeddings Azure + LLM Ollama locale (risparmio costi).

- **Opzione A — Manopola autonoma `llm_provider`** (come REQ-005): default = stesso valore
  di `embed_provider`, ma sovrascrivibile indipendentemente.
  - Pro: flessibilità; consente embeddings cloud + LLM locale (es. per risparmio token);
    coerente con il pattern `store_backend` già separato da `embed_provider`.
  - Contro: un campo in più in `Settings`; la configurazione diventa più complessa per
    l'utente che vuole «tutto Azure» o «tutto locale».
- **Opzione B — Alias di `embed_provider`**: il provider LLM chat è sempre lo stesso del
  provider embeddings; un solo campo governa tutto.
  - Pro: configurazione più semplice; meno da documentare.
  - Contro: non permette lo scenario embeddings cloud + LLM locale; viola il Principio II
    (intercambiabilità guidata da configurazione).

**Raccomandazione**: **Opzione A**. La coerenza con il pattern `store_backend` (già separato
da `embed_provider`, decisione FEAT-004) e il caso d'uso embeddings-cloud/LLM-locale
(risparmio significativo su query frequenti) giustificano la manopola autonoma. Il default
`embed_provider` garantisce «zero config aggiuntiva» per chi usa tutto Azure.

[DA CHIARIRE: conferma o preferenza per Opzione B prima del design.]

---

### DA-3 — Orchestrazione: loop vanilla in-house (Must) vs framework (Could)?

**Contesto.** Il prototipo ha confrontato 4 motori (vanilla, AutoGen, SK, LangGraph) a
parità di tool e system prompt. I risultati dell'eval (`ESEMPI-agentic.md:9-13`):

| Motore | cita atteso | tool giusto | passi medi | tool medi |
|--------|-------------|-------------|------------|-----------|
| vanilla | 9/9 | 7/9 | 2.8 | 3.3 |
| autogen | 9/9 | 8/9 | 2.8 | 3.7 |
| sk | 9/9 | 8/9 | 5.0 | 4.0 |
| langgraph | 9/9 | 7/9 | 2.8 | 3.3 |

Le differenze sono marginali; vanilla è paragonabile ai framework con meno dipendenze.
AutoGen e LangGraph richiedono dipendenze pesanti che possono creare conflitti (Principio
III). SK ha passi medi più alti (5.0 vs 2.8: più costoso).

- **Opzione A — Vanilla loop as Must, framework as Won't**: no framework; il loop è
  in-house. Zero dipendenze aggiuntive.
  - Pro: massimo controllo, zero dipendenze extra, facilità di test, coerente con
    Principio III (YAGNI).
  - Contro: nessun tool ecosystem dei framework (middleware, traccing, ecc.).
- **Opzione B — Vanilla as Must, framework adapter as Could**: il core ha un adapter
  intercambiabile per framework (LangGraph come alternativa dimostrabile).
  - Pro: apre la porta ai framework senza forzarli; utile se un framework dovesse
    dimostrarsi superiore su un caso d'uso futuro.
  - Contro: più lavoro architetturale; richiede una porta `AgentOrchestrator` separata.

**Raccomandazione**: **Opzione A** per questa feature. I numeri del prototipo non
giustificano il costo di dipendenza. Se in futuro emerge un caso d'uso dove un framework
produce risultati misurabilmente migliori, si introduce l'adapter alla luce di quell'evidenza
(Principio III). Confermare o emendare.

[DA CHIARIRE: la scelta è molto inclinata verso Opzione A; segnalare solo se si ha un caso
d'uso concreto per un framework specifico.]

---

### DA-4 — Strumenti disponibili al loop: i 7 esistenti o un sottoinsieme?

**Contesto.** Il prototipo espone 6 tool (`tools.py:17-60`): `search_code`, `search_docs`,
`search_combined`, `find_symbol`, `who_calls`, `related_docs` (assente: `get_context`). Il
core di produzione ha 7 tool (incluso `get_context`). In produzione si può dare all'agente
tutti e 7, o solo quelli con dimostrato uso nell'eval set.

- **Opzione A — Tutti i 7 tool**: catalogo completo; l'agente sceglie liberamente.
  - Pro: copertura massima; `get_context` (multi-hop: definizioni + chiamanti + doc)
    è il tool più potente per task `multi-hop` e può ridurre il numero di passi.
  - Contro: un agente può fare scelte subottimali su un catalogo più grande (es. usare
    `get_context` quando basta `find_symbol`).
- **Opzione B — Solo i 6 del prototipo** (senza `get_context`): replica conservativa.
  - Pro: eval set del prototipo è già validato con 6 tool.
  - Contro: `get_context` è il tool più ricco; escluderlo per conservatorismo non è
    giustificato se il modello lo usa correttamente.

**Raccomandazione**: **Opzione A (tutti i 7 tool)**. Il prototipo non includeva
`get_context` perché il graph service non esisteva al momento della sua scrittura
(`prototype/04-agentic-rag/tools.py` non include `get_context` nella lista). La produzione
ha il tool; includerlo è naturale e l'eval set dovrà coprire almeno un task `multi-hop` che
lo esercita. Confermare.

[DA CHIARIRE: se si preferisce un sottoinsieme configurabile (es. `agent_tools` in
Settings), da valutare nel design.]

---

### DA-5 — Comportamento del tool MCP `ask` se il graph non è costruito

**Contesto.** Il loop agentico usa i tool di navigazione del grafo (`find_symbol`, ecc.).
Se il grafo non è stato costruito per il corpus corrente, le chiamate a questi tool
restituiscono `GraphNotFoundError` (FEAT-005 REQ-007). Il motore agentico può:

- **Opzione A — Propagare l'errore del tool all'LLM come contesto**: il tool call ritorna
  il messaggio d'errore come stringa («grafo non costruito — eseguire sertor-rag index»);
  l'LLM sceglie di non usare quel tool per la query e prosegue con gli altri strumenti.
  - Pro: l'LLM può adattarsi; il loop non si interrompe; il consumatore riceve una risposta
    (parziale, ma con testo).
  - Contro: la risposta è degradata senza che il consumatore sappia perché; il sistema
    premia un comportamento non configurato correttamente.
- **Opzione B — Errore esplicito a livello di query**: se il graph service non è disponibile
  e un tool di grafo viene chiamato nel loop, l'intera query fallisce con `GraphNotFoundError`
  propagato.
  - Pro: errore esplicito, azionabile (Principio IV); il consumatore sa che deve fare `index`.
  - Contro: il loop si interrompe anche se il task potrebbe essere risolto con i soli
    tool di retrieval.
- **Opzione C — Catalogo adattivo**: se il grafo non è costruito, i 4 tool di grafo non
  sono inclusi nel catalogo dei tool disponibili al loop per quella query.
  - Pro: l'LLM non vede tool non disponibili; il comportamento è coerente.
  - Contro: la logica di costruzione del catalogo dipende dallo stato runtime del grafo;
    più complessa da implementare e testare.

**Raccomandazione**: **Opzione A**. Coerente con la policy tollerante della `RetrievalFacade`
(indice mancante → `[]` + warning, non eccezione) per i tool di retrieval, e con il fatto
che il sistema prototipo gestisce già gli errori dei tool come stringhe all'LLM
(`tools.py:84-91`: `except Exception as e: return f"(errore nel tool {name}: {e})"`).
L'errore viene loggato strutturato, il `AgenticResponse.trace` lo registra, e il consumatore
può ispezionare la traccia. L'Opzione B è valida se il workflow canonico richiede sempre il
grafo: da decidere in base al caso d'uso prevalente.

[DA CHIARIRE: questa è la decisione più soggetta a preferenza d'utente; le tre opzioni hanno
trade-off diversi di robustezza vs informatività. Confermare prima del design.]

