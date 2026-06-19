---
title: Code-graph strutturale (navigazione del codice)
type: concept
tags: [code-graph, graphrag, find-symbol, who-calls, navigazione, tree-sitter, networkx, sertor-core, feat-005]
created: 2026-06-12
updated: 2026-06-19 (auto-reload su artefatto cambiato: cache chiavata su mtime_ns+size, niente staleness dopo re-index)
sources: ["src/sertor_core/services/graph_extraction.py", "src/sertor_core/adapters/graph/networkx_graph.py", "specs/014-motore-grafo/**"]
---

# Code-graph strutturale (navigazione del codice)

Il **code-graph** è la terza capacità RAG di Sertor (FEAT-005, feature 014, PR #25) ed è
**ortogonale** ai motori di retrieval: non risponde a «cosa tratta questo codice?» (similarità —
[[vector-retrieval]]/[[hybrid-retrieval]]) ma a «**dove è definito X? chi chiama Y? quali doc
parlano di Z?**» — lookup esatti su un grafo AST deterministico, senza LLM, senza embeddings,
senza cloud. Non è il GraphRAG "alla Microsoft" (knowledge graph LLM): quello è dichiarato fuori
ambito.

## Nodi, archi, copertura dichiarata

Nodi `module / class / function / method / doc`; archi `contains` (gerarchia), `calls`,
`imports`, `inherits` (best-effort intra-corpus per nome: gli ambigui oltre soglia sono
**omessi**, precisione > completezza) e `mentions` (doc→simbolo per token distintivi). I nodi
derivano dai **metadati già prodotti dal chunker** sintattico; gli archi relazionali da un walk
tree-sitter dedicato guidato dalla mappa **`COVERAGE`** — la dichiarazione per-linguaggio di ciò
che è supportato, persistita nell'artefatto e **verificata dai test** (un mini-corpus chiuso per
i 10 linguaggi): nodi+gerarchia ovunque, chiamate per tutti, import/ereditarietà per Python.
Per C/C++ il chunker non nomina i simboli → fallback dichiarato sul `declarator` (R-3 gestito).

## Mai stantio: build dentro `index()` e reload su cambio disco

Il grafo si costruisce **nello stesso passaggio dell'indicizzazione** (sink opzionale in
`IndexingService`, default `SERTOR_GRAPH=true`): un solo comando tiene freschi retrieval e grafo
— scelta DA-2, stessa dell'indice lessicale della 013, motivata dall'essenza «contesto agente
sempre reale». Artefatto **JSON `sertor.graph/1`** atomico in `<index_dir>/graph/<corpus>.json`,
namespace per **solo corpus** (il grafo non dipende dal provider di embeddings — diverso da
collezioni vettoriali e sidecar lessicale).

Dal 2026-06-19, l'adapter `NetworkxCodeGraph` non cacheia il grafo indefinitamente: la **cache è
chiavata su `(st_mtime_ns, st_size)` dell'artefatto su disco**. Se il file viene riscritto (es. da
un re-index in parallelo), la prossima query lo rileva e **ricarica** il grafo aggiornato, senza
riavvio del server. Questo elimina il rischio di staleness tra re-index e riavvio.

## Porta, adapter e l'asimmetria chiave

Porta **`CodeGraph`** nel dominio ([[ports-adapters]]), adapter `NetworkxCodeGraph`.
L'asimmetria di design (G1): il **build è JSON puro** — funziona SENZA l'extra `graph`, quindi
`index()` produce sempre l'artefatto; **networkx serve solo alla navigazione** (import pigro nei
metodi di query → extra assente = `ConfigError` azionabile). **Due semantiche di assenza**:
grafo non costruito → `GraphNotFoundError` esplicito; simbolo assente → **vuoto esplicito**
(legittimo) — mai silenzi.

## Le quattro operazioni (e i 7 tool del server MCP)

`find_symbol` (definizioni con path/riga/kind/qualname) · `who_calls` (chiamanti diretti) ·
`related_docs` (doc che menzionano il simbolo) · `get_context` (bundle multi-hop: definizioni +
chiamanti + chiamate + basi + doc, sezioni limitate dai knob). Risposte **citabili**
(`ref = path#qualname`). I 4 tool storici sono **tornati nel [[mcp-server]]** (promessa
dell'epica mantenuta): superficie a 7 tool, con warm-up eager esteso al grafo (lezione PR #23).

## Qualità misurata

Senza rete: ground-truth reale (6 simboli di `src/sertor_core`) — definizioni esatte, caller
recall 8/8, doc recall 2/2; mini-corpus chiuso dei 10 linguaggi — copertura dichiarata tutta
vera, precisione 1.00. Dogfood live: **1.180 nodi / 1.202 archi calls** sul corpus sertor,
`get_context("RetrievalFacade")` fonde definizione, chiamanti e i requirements/contracts reali
che la citano; query **<0.1 ms** (primo load ~195 ms).

## Vedi anche
- Le modalità di retrieval che affianca: [[vector-retrieval]] · [[hybrid-retrieval]].
- Guida di scelta ibrida vs grafo: [[retrieval-vs-graph]] — pattern scopri (pertinenza) → naviga (struttura).
- Le porte: [[ports-adapters]] · le superfici: [[mcp-server]] · [[thin-consumer]].
- Naming di corpus e artefatti: [[corpus-index-naming]]. Stato: [[roadmap]].
