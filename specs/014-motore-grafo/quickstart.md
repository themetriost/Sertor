# Quickstart — Motore RAG a grafo (014)

## Per chi usa Sertor

Il grafo si costruisce **da solo** a ogni indicizzazione (default `SERTOR_GRAPH=true`):

```bash
uv run sertor-rag index .     # indici vettoriale + lessicale + GRAFO, in un passaggio
```

L'artefatto vive in `<index_dir>/graph/<corpus>.json` (namespace per corpus: indipendente dal
provider di embeddings). Per **navigarlo** serve l'extra:

```bash
uv add "sertor-core[graph]"   # networkx — solo per la navigazione, non per il build
```

## I 4 tool nel server MCP

Al riavvio del server (`/mcp` → reconnect) compaiono accanto ai 3 di ricerca:

| Tool | Domanda a cui risponde |
|---|---|
| `find_symbol(name)` | dove è definito X? (path, riga, kind, qualname) |
| `who_calls(name)` | chi chiama X? |
| `related_docs(name)` | quali doc parlano di X? |
| `get_context(name)` | tutto il contesto: definizioni + chiamanti + chiamate + basi + doc |

Risposte citabili (`ref = path#qualname`). Simbolo assente → liste vuote; grafo non costruito →
errore che dice di indicizzare; extra assente → errore con l'istruzione d'installazione.

## Configurazione (default in `Settings`)

```bash
SERTOR_GRAPH=true               # build del grafo dentro index() (default)
SERTOR_GRAPH_AMBIGUITY=2        # soglia: nomi più ambigui di così non generano archi calls
SERTOR_GRAPH_LIMIT_DEFS=10      # limiti per sezione di get_context
SERTOR_GRAPH_LIMIT_RELS=8
SERTOR_GRAPH_LIMIT_DOCS=8
```

## Copertura per-linguaggio (dichiarata, FR-003)

Nodi e gerarchia (`contains`): **tutti i 10 linguaggi** del chunking sintattico. Archi
relazionali: dichiarati dalla mappa `COVERAGE` (persistita nell'artefatto e documentata) —
Python con calls/imports/inherits (parità col prototipo); gli altri linguaggi con i `calls`
via i node-type di invocazione validati dal ground-truth per-linguaggio. Ciò che non è
dichiarato non esiste — mai assenza silenziosa.

## Verifica

```bash
uv run pytest tests/integration/test_graph_ground_truth.py -q   # ≥5 simboli reali, soglie 80%
uv run pytest tests/unit -k graph -q                            # estrazione, porta, tool
```

## Esito misurato (implementazione, 2026-06-12)

- **CI senza rete:** ground-truth reale (6 simboli di `src/sertor_core`): definizioni esatte,
  caller recall **8/8 = 1.00**, doc recall **2/2 = 1.00**; mini-corpus chiuso dei 10 linguaggi:
  copertura dichiarata tutta vera, precisione **1.00** (82 archi, 0 spuri).
- **Dogfood live (corpus `sertor`, 327 doc):** grafo costruito da `index()` nello stesso
  passaggio — 1.180 nodi (559 function, 213 method, 81 class, 134 module, 193 doc) e 1.202
  archi `calls`; `find_symbol("build_facade")` → `composition.py` riga esatta;
  `who_calls("log_event")` → 36 chiamanti; `get_context("RetrievalFacade")` → definizione +
  chiamanti + doc collegati (requirements/contracts reali). Latenza: ~195 ms il primo load
  (artefatto+networkx), poi **<0.1 ms** per query (NFR-04 ampiamente rispettato).
- **Nota R-3 realizzata e gestita:** per C/C++ il chunker non nomina i simboli
  (`function_definition` senza field `name`) → fallback dichiarato sul `declarator` nel
  passaggio AST del grafo: nodi e chiamate funzionano per tutti i 10 linguaggi.

## Limiti dichiarati di questa iterazione

- Risoluzione `calls`/`imports` **best-effort intra-corpus per nome**: niente call esterne;
  nomi ambigui → archi omessi (precisione > completezza).
- Profondità relazionale dei linguaggi non-Python oltre la copertura dichiarata: incrementale
  (si estende la mappa, non l'architettura).
- Knowledge graph LLM (Microsoft GraphRAG), multi-repo, fusione retrieval+grafo in una query:
  fuori ambito (FEAT-006+).
