# Implementation Plan: Motore RAG a grafo (code-graph strutturale)

**Branch**: `014-motore-grafo` | **Date**: 2026-06-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-motore-grafo/spec.md`
(fonte EARS: `requirements/sertor-core/motore-grafo/requirements.md`, DA-1..DA-5 risolte)

## Summary

Terza capacità RAG del core, **ortogonale** ai motori di retrieval: il **code-graph
strutturale** (nodi module/class/function/method/doc; archi contains/calls/imports/inherits/
mentions) costruito **dentro `index()`** dagli stessi documenti/chunk (mai stantio), persistito
come JSON namespaced per corpus, navigato dalla settima porta `CodeGraph` (adapter networkx
dietro l'extra `graph`, importato pigramente SOLO per le query — il build non lo richiede,
research G1). I **4 tool storici** (`find_symbol`/`who_calls`/`related_docs`/`get_context`)
tornano nel server MCP come superfici sottili con warm-up eager (lezione PR #23). Copertura
**dichiarata** per tutti i 10 linguaggi (mappa `COVERAGE`: nodi/contains ovunque, archi
per-linguaggio verificati da ground-truth sintetico). Dettagli: [research.md](research.md)
G1..G10.

## Technical Context

**Language/Version**: Python ≥ 3.11 (invariato)

**Primary Dependencies**: `networkx>=3` (nuova, **extra `graph`**, lazy nei soli metodi di
query); estrazione via `tree-sitter`/`tree-sitter-language-pack` GIÀ in base (riuso del
chunking); nessun'altra dipendenza

**Storage**: nuovo artefatto **JSON `sertor.graph/1`** in `<index_dir>/graph/<corpus>.json`
(atomico, namespace per solo corpus — il grafo non dipende dal provider); store esistenti
invariati

**Testing**: pytest senza rete (NFR-03): `FakeCodeGraph` per le superfici; adapter reale su
tmp_path; ground-truth a due strati (≥5 simboli reali Python + mini-corpus sintetico per
linguaggio in `tests/fixtures/graph_corpus/`)

**Target Platform**: libreria cross-platform, come il core

**Project Type**: estensione della libreria `sertor-core` + superficie `sertor_mcp`

**Performance Goals**: NFR-04 — navigazione < 100 ms (grafo in-memory < 50k nodi),
`get_context` < 500 ms; build misurato da `graph_build.elapsed_ms` nel dogfood

**Constraints**: porte/motori/facade esistenti INVARIATI (FR-029); grafo ortogonale a
`SERTOR_ENGINE` (FR-012); errori espliciti con DUE semantiche di assenza (FR-007/FR-017);
niente cloud/embeddings (LSC-5); install ≠ run (il grafo si carica, non si ricostruisce,
all'avvio del server)

**Scale/Scope**: corpus < 50.000 nodi (MVP); dogfood sertor ~300 file

## Constitution Check

*GATE: superato pre-Phase 0 (2026-06-12) e ri-verificato post-design (Phase 1). Costituzione v1.1.0.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS. Porta `CodeGraph` nel domain;
  networkx SOLO nell'adapter (lazy nelle query); estrazione = servizio puro su entità di
  dominio; wiring esclusivo in `composition.py` (`build_graph_service`). Esercitabile con
  `FakeCodeGraph`, senza cloud/CLI.
- [x] **II — Boundary & local-first:** PASS. Tutto locale by design (LSC-5: niente embeddings
  né vector store); la modalità strutturale opera senza store, come la costituzione prescrive.
- [x] **III — YAGNI & unità piccole:** PASS. Una porta per evidenza reale (testabilità NFR-03);
  estrazione/persistenza/navigazione separate (SRP); euristica mentions non configurabile al
  MVP; networkx isolato nell'extra.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS. `GraphNotFoundError` (grafo assente),
  `ConfigError` (extra mancante, formato sconosciuto); simbolo assente = vuoto esplicito
  DISTINGUIBILE per contratto (FR-017) — nessuna degradazione silenziosa in tutta la feature.
- [x] **V — Testabilità & misure:** PASS. Ground-truth a due strati con soglie numeriche
  (precisione/recall ≥80%, LSC-2/3); tutto senza rete; la copertura dichiarata è VERIFICATA
  (un caso per linguaggio dichiarato).
- [x] **VI — Idempotenza & non-distruttività:** PASS. Id nodi stabili (`path::qualname`),
  build snapshot atomico, stesso corpus → stesso grafo; install≠run (il server carica, non
  costruisce); nessun file utente toccato.
- [x] **VII — Leggibilità:** PASS. Vocabolario di dominio (find_symbol, who_calls, mentions,
  contains); mappa `_REL`/`COVERAGE` come dichiarazione leggibile della copertura.
- [x] **VIII — Configurabilità centralizzata:** PASS. 5 manopole nuove tutte in `Settings`
  (graph_enabled, ambiguity_threshold, 3 limiti di get_context).
- [x] **IX — Osservabilità:** PASS. `graph_build` (conteggi per kind/type — un build con 0
  calls su corpus Python si diagnostica dal log) e `graph_query`; redazione esistente.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS. Nessuna assunzione sull'ospite
  (i `_pkg_prefixes` hardcoded del prototipo NON vengono portati: i simboli del corpus sono
  tutti del corpus by construction); ground-truth con path relativi; corpus solo-doc gestito
  (grafo di soli nodi doc).

**Post-design re-check (Phase 1)**: PASS 10/10 — nessuna deroga richiesta (a differenza della
013 non c'è alcun caso di degradazione: le assenze sono errori espliciti o vuoti dichiarati).

## Project Structure

### Documentation (this feature)

```text
specs/014-motore-grafo/
├── plan.md              # questo file
├── research.md          # Phase 0 — decisioni G1..G10
├── data-model.md        # Phase 1 — entità, porta, schema sertor.graph/1, Settings, eventi
├── quickstart.md        # Phase 1 — uso, config, copertura dichiarata, limiti
├── contracts/
│   ├── code-graph-port.md
│   ├── mcp-graph-tools.md
│   └── log-events.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/
│   ├── entities.py                  # + GraphNode, GraphEdge, GraphData, SymbolHit, ContextBundle
│   ├── ports.py                     # + CodeGraph (settima porta)
│   └── errors.py                    # + GraphNotFoundError
├── config/settings.py               # + graph_enabled, graph_ambiguity_threshold, 3 limiti
├── services/
│   ├── graph_extraction.py          # NUOVO: estrazione pura (nodi da chunk, archi tree-sitter, mentions) + COVERAGE
│   └── indexing.py                  # + sink grafo opzionale (extract + build dopo upsert)
├── adapters/graph/
│   ├── __init__.py
│   └── networkx_graph.py            # NetworkxCodeGraph: build=JSON atomico; query=nx lazy + indici
└── composition.py                   # + build_graph_service(); wiring sink in build_indexer()

src/sertor_mcp/server.py             # + 4 tool sottili + warm-up esteso (grafo)

tests/
├── unit/
│   ├── test_graph_extraction.py     # nodi da chunk, contains da qualname, calls/imports/inherits, mentions, ambiguità, determinismo, COVERAGE
│   ├── test_networkx_graph.py       # build atomico/idempotente, formato versionato, query, due semantiche di assenza, extra mancante
│   ├── test_graph_composition.py    # build_graph_service, wiring sink da graph_enabled, ortogonalità SERTOR_ENGINE
│   └── test_mcp_graph_tools.py      # 4 tool con FakeCodeGraph, errori strutturati, 3 tool invariati
├── integration/
│   ├── test_graph_ground_truth.py   # ≥5 simboli reali su src/sertor_core (soglie 80%)
│   └── test_graph_languages.py      # mini-corpus per linguaggio ↔ COVERAGE dichiarata
└── fixtures/
    ├── mocks.py                     # + FakeCodeGraph
    ├── graph_ground_truth.py        # simboli reali con attesi
    └── graph_corpus/                # un file minimo per ciascuno dei 10 linguaggi

pyproject.toml                       # + extra graph = ["networkx>=3"]
docs/install.md                      # sezione grafo (T polish)
```

**Structure Decision**: estensione in-place coerente con la Clean Architecture esistente;
unica novità strutturale: il primo servizio puro con conoscenza per-linguaggio
(`graph_extraction.py`) — accettabile nel layer services perché tree-sitter è già lì
(precedente: `chunking/code.py`).

## Complexity Tracking

> Nessuna violazione da giustificare: zero deroghe costituzionali in questa feature.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
