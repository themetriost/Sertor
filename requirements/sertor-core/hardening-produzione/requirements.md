# Requisiti — Hardening di produzione del livello retrieval

<!-- Origine: RAG Production Audit di Sertor (2026-06-13), rubrica freeCodeCamp "Production RAG".
     Sertor è la metà retrieval/indicizzazione + superficie MCP/CLI; la generazione è dell'agente
     client (RAG agentico composito). Qui solo i gap che ricadono sul LIVELLO DI SERTOR. -->
<!-- STATO: elicitato dall'audit — da portare in SpecKit per priorità. -->

## 1. Contesto e problema (perché)

L'audit di produzione (rubrica "Production RAG") ha promosso il livello retrieval di Sertor come
**production-ready** ma ha isolato **gap di hardening** che oggi lasciano il sistema a
**Pre-production** su pochi assi: affidabilità delle chiamate provider, **segnale di confidenza**
per l'abstention dell'agente, e costo dell'indicizzazione. Questo documento li raccoglie come
requisiti azionabili, ancorati al codice reale.

> **Confine ribadito:** generazione, serving HTTP, model routing, difesa prompt-injection del passo
> di generazione, guardrail sull'output generato sono **del consumer** (l'agente client) — NON gap di
> Sertor (vedi `tema-lingua-runtime` e l'epica per il modello composito). Qui solo ciò che è di Sertor.

## 2. Obiettivi e criteri di successo

- **OB-1 — Affidabilità provider.** Un errore transitorio (429/5xx/timeout) di embeddings non fa
  fallire l'operazione al primo colpo. *SC-1:* con un provider che restituisce 429 e poi 200, l'embed
  riesce senza intervento; esauriti i tentativi → `EmbeddingError` esplicito.
- **OB-2 — Grounding abilitato.** Il consumer può astenersi su query fuori-dominio. *SC-2:* su una
  query con top-score sotto soglia, la facade non restituisce contesto spurio (lista vuota o flag di
  bassa confidenza), in modo osservabile.
- **OB-3 — Costo dell'indicizzazione controllato.** Re-indicizzare un corpus invariato non ri-paga
  l'embedding. *SC-3:* un secondo `index()` su corpus invariato non emette chiamate di embedding per i
  chunk identici (cache hit), misurabile.

## 3. Ambito

### In ambito (livello Sertor)
Soglia di score + segnale di confidenza; retry/backoff negli embedder; cache embeddings per
content-hash; conteggio token nei log; (opzionali) tracing distribuito, metriche aggregate, query
transformation, filtro metadata esteso, contextual retrieval.

### Fuori ambito
Generazione/prompt/abstention-nella-risposta, serving HTTP+auth+rate-limit, model routing, guardrail
output, difesa prompt-injection del passo di generazione → **consumer**. Refresh incrementale
dell'indice = **FEAT-009 d'epica** (qui solo collegato). Prototipo congelato.

## 4. Requisiti funzionali (EARS)

### Gruppo A — Segnale di confidenza / soglia di score (grounding)

- **REQ-H1 (Optional/Config):** *Where a similarity score threshold is configured, the retrieval
  facade and engines shall exclude results whose score is below the threshold (no top-k regardless).*
  Ancora: oggi `retrieval.py:72`/`baseline.py:78`/`hybrid.retrieve` restituiscono top-k senza soglia;
  lo score esiste (`chroma.py:145`, `score=1-distance`) ma non è filtrato.
- **REQ-H2 (Event-driven):** *When the best result's score is below the configured threshold, the
  system shall signal low confidence (empty result and/or an explicit flag) in a way the consumer
  can use to abstain, and shall log it.* Razionale: è l'anello di grounding che spetta a Sertor nel
  modello composito (l'astensione-nella-risposta resta dell'agente).

### Gruppo B — Affidabilità delle chiamate provider

- **REQ-H3 (Unwanted/Reliability):** *If an embedding call fails with a retriable condition
  (HTTP 429/5xx or a network error), then the embedder shall retry with exponential backoff + jitter
  up to a configurable maximum before raising `EmbeddingError`.* Ancora: `azure.py:61-73` marca
  `retriable=True` ma **non ritenta**; idem `ollama.py`. Manopola `Settings` (max tentativi/base).

### Gruppo C — Costo dell'indicizzazione

- **REQ-H4 (Optional):** *Where embedding caching is enabled, re-indexing an unchanged corpus shall
  not re-embed chunks whose content is unchanged (content-hash cache).* Ancora: `indexing.py:63-85`
  fa sempre rebuild full (re-embed totale; su Azure è costo per rebuild).
- **REQ-H5 (Ubiquitous):** *The embedding log event shall include the token count returned by the
  provider when available, as a cost signal.* Ancora: oggi `embeddings_error`/`index` non loggano i
  token; il JSON Azure espone `usage.total_tokens`.
- **REQ-H6 (link):** Refresh incrementale (solo file cambiati) = **FEAT-009 d'epica** — non
  ri-elicitato qui; REQ-H4 (cache) è il mitigante immediato.

### Gruppo D — Recall e filtro (Could)

- **REQ-H7 (Optional, Could):** *Where query transformation is enabled, the system shall expand a
  query (multi-query / HyDE) before retrieval to lift recall on short/ambiguous NL queries.*
- **REQ-H8 (Optional, Could):** *The facade shall allow scoping retrieval by metadata beyond
  `doc_type` (e.g. `source`, `language`), reusing the store's `where` filter (`chroma.py:86`).*

### Gruppo E — Osservabilità avanzata (Could)

- **REQ-H9 (Optional, Could):** *Where distributed tracing is configured, retrieval/index operations
  shall emit spans (OpenTelemetry/Langfuse) behind a port, in addition to structured logs.*
- **REQ-H10 (Optional, Could):** *The system shall be able to expose aggregated metrics (latency
  p95/p99, cache-hit rate) for the operations it already logs.*

### Gruppo F — Maturità (Could)

- **REQ-H11 (Optional, Could):** *Where contextual retrieval is enabled, the chunker shall prepend
  chunk-specific context before embedding (Anthropic contextual retrieval) to fight context loss on
  fragmented documents.*

## 5. Requisiti non funzionali
- **RNF-1:** retry/cache/tracing dietro porte/manopole `Settings` (Principio VIII); default
  retro-compatibili (soglia assente = comportamento attuale; retry attivo ma conservativo).
- **RNF-2:** tutto testabile senza rete (provider mock che simula 429→200; embedder mock per la cache).
- **RNF-3:** nessun cambio del contratto `RetrievalResult` che rompa i consumer (il flag di confidenza
  è additivo/forward-compatible).

## 6. Prioritizzazione (MoSCoW)
| Item | REQ | MoSCoW | Perché |
|---|---|---|---|
| Retry+backoff embedder | REQ-H3 | **Must** | Critical dell'audit (F1): i provider falliscono in produzione |
| Soglia score + segnale confidenza | REQ-H1/H2 | **Must** | Abilita l'abstention (B1): l'unico gap che indebolisce il grounding composito |
| Cache embeddings (content-hash) | REQ-H4 | **Should** | Taglia il costo Azure dei rebuild (A5/E2) |
| Token nei log | REQ-H5 | **Should** | Segnale di costo #1, oggi assente (D3) |
| Query transformation | REQ-H7 | **Could** | Recall su NL corte (B3) |
| Filtro metadata esteso | REQ-H8 | **Could** | Scoping/freshness (B6) |
| Tracing distribuito / metriche | REQ-H9/H10 | **Could** | Debug sessioni d'agente (D1/D3) |
| Contextual retrieval | REQ-H11 | **Could** | Uplift di recall su doc frammentati (I2) |

## 7. Azione operativa (fuori EARS, immediata)
- **🔴 Ruotare la API key Azure** comparsa nel transcript della sessione del 2026-06-13 (il codice è
  pulito — key solo da `.env`, redatta nei log — ma una key uscita in chat è compromessa). Non è un
  requisito di codice: è igiene operativa, da fare subito.

## 8. Riferimenti
RAG Production Audit (2026-06-13, skill `rag-production-audit`); codice: `services/retrieval.py`,
`engines/baseline.py`, `engines/hybrid.py`, `adapters/embeddings/azure.py`,
`adapters/vectorstores/chroma.py`, `services/indexing.py`, `observability/logging.py`.
Collegamenti: FEAT-009 (refresh incrementale), modello agentico composito (`motore-agentico/`).
