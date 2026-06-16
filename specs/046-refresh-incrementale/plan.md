# Implementation Plan: Refresh incrementale dell'indice RAG

**Branch**: `046-refresh-incrementale` | **Date**: 2026-06-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/046-refresh-incrementale/spec.md` (FEAT-009, epica `sertor-core`)

## Summary

Oggi `IndexingService.index(root, rebuild=False)` ricostruisce **da zero** l'intero indice a ogni
invocazione: 5 stadi (discover → chunk → embed → reset+upsert → BM25+code-graph), tutti full; solo
l'embed è incrementale via cache content-hash (FEAT-019). Su ospiti grandi è minuti.

L'approccio: introdurre un **manifest persistito** (`(corpus, provider)`-namespaced, SQLite locale) che
ricorda per ogni file sorgente `mtime + content-hash + logic-version` e **conserva le unità derivate
(Document+Chunk)**. Un run **incrementale di default** (F2) classifica i file (invariato/nuovo/modificato/
cancellato), riprocessa **solo i cambiati**, fa **upsert/delete mirati** sul `VectorStore` (il metodo
`delete(collection, ids)` **esiste già**), e **ricostruisce BM25 e code-graph dall'insieme completo di
unità del manifest** (F1: niente re-chunk/re-read degli invariati — le porte `LexicalIndex`/`CodeGraph`
restano mirror, le si nutre con tutte le unità). Safeguard nel Must: equivalenza col full (FR-012),
fallback automatico al full su manifest assente/incompatibile (FR-011), invalidazione su cambio-logica
(FR-013), conteggi delta osservabili (FR-015). Full su `--full` resta il reset sicuro. Aggiunte di
clarify: full di **riconciliazione** off-default (FR-019) e **guardia single-writer** (FR-020). Raggiunto
via il vehicle CLI `sertor-rag index` (Principio XI).

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: stdlib (`sqlite3`, `hashlib`, `pathlib`, `os.stat`); nessuna nuova dipendenza
esterna. Riusa `EmbeddingCache` (FEAT-019), porte `VectorStore`/`LexicalIndex`/`CodeGraph` esistenti.

**Storage**: manifest SQLite locale `<index_dir>/index_manifest.sqlite` (namespaced per collezione
`(corpus, provider)`), gitignored — accanto a `embed_cache.sqlite`/`observability.sqlite`.

**Testing**: pytest (unit con mock delle porte; integration end-to-end con Chroma locale + embedder mock);
test cardine di **equivalenza** incrementale ≡ full (SC-002).

**Target Platform**: qualunque ospite (Principio X); local-first.

**Project Type**: libreria `sertor-core` consumata via vehicles (CLI `sertor-rag`, MCP).

**Performance Goals**: run incrementale con poche modifiche ≪ full (SC-001); run a vuoto ≈ costo del solo
`stat` dei file (NFR-4).

**Constraints**: correttezza > velocità (NFR-1, in dubbio riprocessa); equivalenza col full (FR-012);
nessun segreto nel manifest (NFR-3); idempotenza (FR-017).

**Scale/Scope**: corpora da pochi file a centinaia di MB / decine di migliaia di file.

## Constitution Check

*GATE: pre-Phase 0 e post-Phase 1. Costituzione v1.2.0 (11 principi).*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il manifest è uno **store concreto senza SDK**
  (stdlib `sqlite3`), come `EmbeddingCache`/`MemoryArchive`; la logica di diff è un **service**; nessun
  import di CLI/SDK nel dominio. Il core resta esercitabile con porte mock.
- [x] **II — Boundary & local-first:** manifest locale stdlib, zero cloud; riusa le porte esistenti dietro boundary.
- [x] **III — YAGNI & unità piccole:** **nessuna nuova porta** (riusa `VectorStore.delete` già presente;
  `LexicalIndex`/`CodeGraph` restano mirror). Manifest concreto senza porta (single consumer = indexing,
  come `EmbeddingCache`). SRP: diff/prune/reconcile come funzioni piccole.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** `IndexLockedError` (concorrenza), manifest
  incompatibile → **fallback esplicito al full** (no None silenzioso); fallimento a metà file → segnalato,
  niente stato parziale (FR-014). Errori di dominio avvolti al boundary.
- [x] **V — Testabilità & misure:** test F.I.R.S.T. con porte mock; **test di equivalenza** incrementale≡full
  (SC-002); misura del guadagno (SC-001). Una feature senza la misura di equivalenza non è "fatta".
- [x] **VI — Idempotenza & non-distruttività:** incrementale idempotente su sorgente invariata (FR-017);
  ID chunk stabili (`doc_id#index`) preservati; il full su `--full` è il reset atomico esistente; il
  manifest è additivo/rigenerabile (non distrugge).
- [x] **VII — Leggibilità:** vocabolario di dominio (manifest, stale, prune, reconcile, single-writer);
  funzioni piccole con guard clause.
- [x] **VIII — Configurabilità centralizzata:** nuove manopole solo in `Settings`
  (`SERTOR_INDEX_INCREMENTAL`, `SERTOR_INDEX_RECONCILE_EVERY`), nessun default hardcoded nei componenti.
- [x] **IX — Osservabilità:** evento `index` esteso con i conteggi delta (added/updated/removed/unchanged/
  cache_hits, FR-015/016) via `log_event`; nessun segreto.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** manifest namespaced per `(corpus, provider)`, nessuna
  assunzione sull'ospite; gira su code+doc / solo-doc / solo-code senza modifiche al corpo.
- [x] **XI — Consumo via vehicles:** la capacità è raggiunta via CLI `sertor-rag index [--full]` / MCP;
  l'orchestrazione vive nel **service** cablato dal composition root (`build_indexer` → `_wire_runtime`);
  nessun percorso di sola libreria a runtime (eccezione test).

**Esito: PASS 11/11, nessuna deroga** → Complexity Tracking vuoto.

## Project Structure

### Documentation (this feature)

```text
specs/046-refresh-incrementale/
├── plan.md              # questo file
├── research.md          # decisioni di design (3 Q clarify-plan + manifest + secondary rebuild + lock)
├── data-model.md        # IndexManifest, schema SQLite, IndexReport esteso, errori
├── quickstart.md        # uso: incrementale di default, --full, riconciliazione
├── contracts/
│   └── index-incremental.md   # contratto CLI `index [--full]` + semantica service + schema manifest
└── tasks.md             # (output di /speckit-tasks)
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/
│   ├── entities.py          # + campi delta in IndexReport (added/updated/removed/unchanged/cache_hits)
│   └── errors.py            # + IndexLockedError (Principio IV)
├── services/
│   ├── indexing.py          # index() esteso: ramo incrementale (detect → prune → process → rebuild secondari)
│   ├── index_manifest.py    # NUOVO: store concreto SQLite del manifest (no porta) + diff/classify
│   └── ingestion.py         # discover: separare stat (tutti) da read (solo cambiati)
├── config/
│   └── settings.py          # + SERTOR_INDEX_INCREMENTAL, SERTOR_INDEX_RECONCILE_EVERY
├── composition.py           # build_indexer cabla manifest + lock; default incrementale quando manifest valido
└── cli/__main__.py          # flag --full sul comando index (vehicle)

tests/
├── unit/
│   ├── test_index_manifest.py    # diff/classify, hash vs mtime, logic-version
│   └── test_incremental_index.py # ramo incrementale con porte mock; lock; fallback
└── integration/
    └── test_incremental_equivalence.py  # SC-002: incrementale ≡ full (Chroma locale + embedder mock)
```

**Structure Decision**: progetto singolo (libreria `sertor-core`). Il grosso vive in `services/`
(orchestrazione + nuovo `index_manifest.py`), additivo sulle entità/errori/config/composition esistenti;
il vehicle CLI espone `--full`. Nessun nuovo package, nessuna nuova porta.

## Complexity Tracking

> Nessuna violazione costituzionale: tabella vuota.
