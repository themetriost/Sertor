---
title: Scegliere — ricerca ibrida vs code-graph (scopri → naviga)
type: concept
tags: [retrieval, code-graph, hybrid, mcp, usage, decisione]
created: 2026-06-14
updated: 2026-07-23
sources: ["wiki/concepts/hybrid-retrieval.md", "wiki/concepts/code-graph.md", "wiki/tech/mcp-server.md", "src/sertor_mcp/server.py"]
---

# Scegliere: ricerca ibrida vs code-graph

Sertor espone **due superfici di interrogazione ortogonali**, non due alternative da scegliere a
priori: la **ricerca ibrida** (motore di *pertinenza*) e il **code-graph** (mappa *strutturale* del
codice). Rispondono a domande di natura diversa, e il loro vero valore è **combinarle**: la ricerca
**scopre** (trova per significato ciò di cui non conosci il nome), il grafo **naviga** (dato un nome,
dà fatti esatti su definizioni e relazioni). Sono ortogonali by design (il code-graph si costruisce
dentro `index()` ed è indipendente dal motore di ricerca scelto via `SERTOR_ENGINE`).

## Le due superfici

### Ricerca ibrida — «trova per significato»
Semantico (embedding) + lessicale (BM25) fusi con RRF, reranking opzionale ([[hybrid-retrieval]]). È
il motore di **default** dietro i tool `search_code` / `search_docs` / `search_combined` (CLI
`sertor-rag search`, tool MCP di ricerca). Tollerante a query in linguaggio naturale e sfocate;
restituisce i chunk **più pertinenti** per significato + parole chiave. Costo a query: **un solo
embedding** (la query) — i chunk sono già indicizzati.

### Code-graph — «naviga per struttura»
Grafo AST **deterministico** (nodi: simboli/doc; archi: `calls`, `contains`, `imports`, `inherits`,
`mentions`) ([[code-graph]]). Backing dei 4 tool MCP `find_symbol` / `who_calls` / `related_docs` /
`get_context`. Risposte **esatte e relazionali**, non per somiglianza. Costo a query: **zero token**
(nessun embedding a query-time).

## La regola pratica: scopri → naviga

| Domanda | Superficie | Tool |
|---|---|---|
| «trova qualcosa per argomento» (non so il nome) | **ibrida** | `search_code` |
| «spiegami / dove si parla di X» (concetto) | **ibrida** | `search_docs` / `search_combined` |
| «dov'è definito X» (so il nome) | **grafo** | `find_symbol` |
| «chi usa X / cosa rompo se lo cambio» | **grafo** | `who_calls` |
| «quali doc spiegano X» | **grafo** | `related_docs` |
| «contesto completo di X (codice+doc)» | **grafo** | `get_context` |

Il flusso tipico dell'agente (e di chi lavora sul codice):

1. **Scopri con l'ibrida** — non sai dove vive una capacità → `search_code "recupero sessioni
   archiviate"` ti porta al file/simbolo giusto per *significato*.
2. **Naviga col grafo** — ora che hai il **nome** → `who_calls <simbolo>` per i consumatori
   (impact analysis), `get_context <simbolo>` per il quadro completo codice↔doc.

L'errore da evitare è usare la ricerca ibrida per domande **strutturali** («chi chiama X») — la
somiglianza di argomento non risponde a una relazione esatta — o il grafo per domande **concettuali**
(«come funziona il chunking») quando non si conosce ancora il simbolo da cui partire.

## Perché ortogonali, non alternative
Il motore di ricerca (`SERTOR_ENGINE`: `baseline` | `hybrid`, default `hybrid`) sceglie **come si
cerca per pertinenza**; il grafo (`SERTOR_GRAPH`, default on) è una capacità **a parte**, costruita
nello stesso `index()` e interrogata dai suoi 4 tool a prescindere dal motore. Convivono nello stesso
server MCP `sertor-rag` ([[mcp-server]]): **10 tool = 3 di ricerca + 4 di grafo + 3 di memoria**
(`memory_list`/`memory_show`/`memory_search`, memoria episodica opt-in), tutti locali.

## Vedi anche
- [[hybrid-retrieval]] — il motore di pertinenza (default).
- [[code-graph]] — la mappa strutturale e i 4 tool.
- [[vector-retrieval]] — la baseline vettoriale (il «solo significato» del punto 1).
- [[mcp-server]] — la superficie a 10 tool che le espone entrambe (più la memoria).
- [[i-modi-di-cercare]] — la versione in parole semplici (explainer).
