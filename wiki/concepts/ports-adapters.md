---
title: Porte e adapter (boundary del retrieval-core)
type: concept
tags: [ports, adapters, protocol, hexagonal, clean-architecture, sertor-core, composition]
created: 2026-06-08
updated: 2026-10-07
sources: ["src/sertor_core/domain/ports.py", "src/sertor_core/composition.py", "src/sertor_core/adapters/**", "requirements/sertor-core/epic.md"]
---

# Porte e adapter (boundary del retrieval-core)

Le **porte** del [[retrieval-core]] sono i **boundary astratti** dietro cui vivono i provider concreti: il
nucleo dipende **solo** da esse (Principio I/II della [[constitution|Costituzione]]), gli **adapter** in
`adapters/` le implementano importando gli SDK esterni. Vivono in `domain/ports.py`, definite come
**`Protocol`** (structural typing): un adapter è conforme se ha i metodi giusti, **senza ereditare nulla** —
così è banale da mockare nei test (tutte `@runtime_checkable`). Le porte sono **otto**: le due
fondative qui sotto, le tre della FEAT-004 ([[hybrid-retrieval]]), la `CodeGraph` della
FEAT-005 ([[code-graph]]), la `ObservabilityStore` della feature 020 (osservabilità) e la
`TranscriptCaptureAdapter` della [[memoria-conversazioni|memoria episodica]] (feature 031, cattura
host-specifica dei transcript).

## Le due porte fondative

- **`EmbeddingProvider`** — trasforma testo in vettori. Metodo `embed(texts) -> list[list[float]]` (a batch,
  ordine preservato, `[]` per input vuoto) + attributi `name`, `dim` (dimensione del vettore, scoperta al
  primo batch se inizialmente `None`), `batch_size`. **Cinque adapter**, due locali deterministici e tre
  verso un servizio:
  `GloveEmbedder` (FEAT-011, 6B 300d PDDL, lazy numpy, cache XDG) = default;
  `HashingEmbedder` (FEAT-011, char-n-gram blake2b 512d stdlib, zero-download, pavimento airgapped/CI);
  `OllamaEmbedder` (Ollama locale, API nativa `/api/embed`);
  `AzureEmbedder` (Azure OpenAI, intestazione `api-key`, `api-version` fuori dalla superficie v1);
  `OpenAIEmbedder` (API OpenAI diretta o servizio compatibile, `Authorization: Bearer`, FEAT-012 /
  `specs/137-provider-openai/`).
  **Azure e OpenAI condividono una base**, `OpenAIProtocolEmbedder` (`adapters/embeddings/_openai_protocol.py`):
  il protocollo `/embeddings` è lo stesso, quindi lotti, classificazione degli errori, retry per lotto e
  segnale dei token vivono una volta sola; le sottoclassi fissano solo URL, credenziale, query e nome.
  Gli adapter ritentano gli errori transitori (retry+backoff, 018) ed emettono un evento di log
  `embeddings` col **conteggio token** quando disponibile (`usage.total_tokens` Azure/OpenAI, `prompt_eval_count`
  Ollama; assente per glove/hash) — segnale di costo, 019/REQ-H5.
  Un **decoratore della stessa porta**, `CachingEmbedder` (`adapters/embeddings/cache.py`), aggiunge la
  [[indexing-and-retrieval|cache per content-hash]] senza che servizi o porta cambino — è l'esempio canonico
  di come si estende un comportamento di provider (adapter + composition, mai i servizi).
- **`VectorStore`** — persiste e cerca. `upsert(collection, records)` (idempotente sugli stessi id),
  `query(collection, vector, k, doc_type) -> list[RetrievalResult]` (top-k per similarità, filtro su
  `DocTypeFilter` = `code|doc|both` **senza** indici separati), più `delete`, `reset` (per il rebuild),
  `exists` e `list_collections()` (elenco delle collezioni — serve alla ricerca combinata multi-collezione
  per distinguere un corpus mai indicizzato, tollerato, da uno indicizzato con un **altro provider** →
  `ProviderMismatchError`, [[spec-010-query-congiunta-e-upsert-index|feature 010]]). Una collezione assente → `query` restituisce `[]` ed
  `exists()==False`; un backend irraggiungibile → `VectorStoreError` (Principio IV).

## Le tre porte della FEAT-004 ([[hybrid-retrieval]])

- **`LexicalIndex`** — indice lessicale del motore ibrido: `build` (snapshot integrale, atomico),
  `query` (ranking di chunk_id, filtro doc_type pre-taglio), `lookup` (materializzazione delle
  voci), `exists`/`reset`. Namespacing per collezione, come il vettoriale.
- **`Reranker`** — secondo stadio opzionale: `model` + `rerank(query, results, k)`; l'adapter è
  dietro l'extra `rerank` (import lazy).
- **`RetrieverStrategy`** — il seam con cui il composition root **inietta** la strategia di
  retrieval nella facade (`retrieve(query, k, doc_type)`): i consumatori non cambiano quando
  cambia il motore.

## La porta della FEAT-005 ([[code-graph]])

- **`CodeGraph`** — navigazione strutturale: `build` (snapshot atomico, NON richiede la libreria
  di grafi), `find_symbol`/`who_calls`/`related_docs`/`get_context`, `exists`/`reset`.
  Namespace per **solo corpus** (il grafo non dipende dagli embeddings). Due semantiche di
  assenza: grafo non costruito → `GraphNotFoundError`; simbolo assente → vuoto esplicito.

## La porta dell'osservabilità (feature 020, F1 epica osservabilità)

- **`ObservabilityStore`** — l'archivio persistente degli eventi: `record_event(ts, operation, fields)`
  + `query_events(operation, since, until) -> list[ObservedEvent]`. È il **seam** tra *dove vivono gli
  eventi* (ci scrive l'handler di cattura) e *chi li interroga* (la futura aggregazione/report FEAT-002).
  Adapter `SqliteObservabilityStore` (SQLite stdlib, `<index_dir>/observability.sqlite`, gitignored).
  Degrado **non-fatale** (guasto → no-op/`[]` + warning, mai un errore dell'operazione osservata).

  **Meccanismo di cattura (osservatore puro).** A differenza delle altre porte (cablate nelle `build_*`
  come dipendenze dei servizi), questa è alimentata da un `logging.Handler` (`EventPersistenceHandler`)
  che il composition root **attacca al logger `sertor_core`** solo se `SERTOR_OBSERVABILITY=true`. Il
  logger *è* il bus pub/sub: `log_event` emette e non sa chi ascolta → **zero modifiche all'emitter**
  (additività massima), **non-fatalità gratis** (il framework logging non propaga le eccezioni di un
  handler), **redazione gratis** (i campi su `LogRecord.extra` sono già `redact`-ati). Guardia di
  re-entrancy perché l'avviso di guasto dello store è a sua volta un evento. Default off = nessun handler,
  nessuno store, comportamento odierno. Vedi l'explainer [[il-pannello-di-controllo]].

Le porte parlano in termini di [[domain-model|entità di dominio]] (`EmbeddedChunk`,
`RetrievalResult`, `LexicalEntry`): è ciò che impedisce a uno schema di backend di risalire nel
nucleo.

## Gli adapter (le implementazioni concrete)

| Porta | Adapter locale (default) | Adapter Azure |
|---|---|---|
| `EmbeddingProvider` | `adapters/embeddings/glove.py` (`GloveEmbedder`, **default FEAT-011**) · `adapters/embeddings/hashing.py` (`HashingEmbedder`) · `adapters/embeddings/ollama.py` (`OllamaEmbedder`) | `adapters/embeddings/azure.py` (`AzureEmbedder`) · cloud non-Azure: `adapters/embeddings/openai.py` (`OpenAIEmbedder`) |
| `VectorStore` | `adapters/vectorstores/chroma.py` (`ChromaStore`) | `adapters/vectorstores/azure_search.py` (`AzureSearchStore`) |
| `LexicalIndex` | `adapters/lexical/bm25.py` (`Bm25LexicalIndex`, sidecar JSON) | — (delega nativa per-store = Could, Gruppo E) |
| `Reranker` | `adapters/rerank/flashrank.py` (`FlashRankReranker`, extra `rerank`) | — |
| `CodeGraph` | `adapters/graph/networkx_graph.py` (`NetworkxCodeGraph`, extra `graph` solo per le query) | — |

## Il composition root sceglie

`composition.py` è l'**unico** componente che conosce gli adapter concreti: le `build_*` (`build_embedder`,
`build_store`, `build_indexer`, `build_facade`, `build_baseline_engine`) leggono `Settings` e cablano
l'implementazione. Provider di **embeddings** è scelto da **una sola manopola** (FEAT-011):
`SERTOR_EMBED_PROVIDER` (default `glove` — un valore di `EMBED_PROVIDERS` in `config/settings.py`: `glove|hash|ollama|azure|openai`) governa l'embedder;
il backend del **vector store** è scelto dalla **manopola indipendente** `SERTOR_STORE_BACKEND` (default
`local` — valori `local|azure`). Sono **combinabili e ortogonali** — es. embeddings Azure con store Chroma
locale (la combinazione usata per l'indice di dogfooding `sertor` fino al 2026-10-07, quando la chiave
Azure è stata rifiutata con `http 401` e il dogfood è passato a `glove`) — fedeli al local-first del
Principio II.

**Provider locali deterministici (FEAT-011):** `glove` (GloVe 6B 300d PDDL, vettori statici, semantica NL,
lazy numpy) è il nuovo default (acquisisce il file on-demand a prima indicizzazione, cache XDG per
macchina); `hash` (char-n-gram blake2b 512d, stdlib-only, zero-download, cross-macchina) è il pavimento
per ambienti airgapped/offline/CI quando la semantica non serve e la determinismo cross-piattaforma è
fondamentale. Entrambi abilitano la **local-first** (niente cicli di autorizzazione Ollama/Azure in CI).

**Conseguenze di design:**

- **Import lazy.** Gli SDK pesanti sono importati **dentro** le `build_*`, solo sul ramo che li usa: l'extra
  `azure` non serve in locale (isolamento delle dipendenze), numpy per glove è lazy (costo ~zero se
  `SERTOR_EMBED_PROVIDER != glove`).
- **Fail-loud su RAG_BACKEND (Principio XII).** La manopola legacy `RAG_BACKEND` non è più onorata; se
  presente in ambiente, l'avvio emette **fail-loud** `ConfigError` suggerendo di rimuoverla (nessun cambio
  silenzioso).
- **Estendere qui, non nei servizi.** Aggiungere un provider/backend significa toccare il composition root e
  scrivere un adapter — **non** modificare i servizi, che vedono solo le porte.

Il composition root calcola anche il nome di **collezione namespaced** per `(corpus, provider)` via
`collection_name()`: poiché il provider determina la dimensione del vettore, includerlo evita di mescolare
embedding di dimensioni diverse (vedi [[corpus-index-naming]]).

## Vedi anche
- L'architettura che le ospita: [[retrieval-core]].
- Cosa scambiano: [[domain-model]].
- Chi le cabla in pipeline: [[indexing-and-retrieval]].
- Perché i consumatori entrano dalle `build_*`: [[thin-consumer]].
- Il principio di local-first e la scelta di glove come default: [[mission-vision]].
