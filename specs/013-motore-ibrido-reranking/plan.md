# Implementation Plan: Motore RAG ibrido + reranking

**Branch**: `013-motore-ibrido-reranking` | **Date**: 2026-06-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/013-motore-ibrido-reranking/spec.md`
(fonte EARS: `requirements/sertor-core/motore-ibrido/requirements.md`, rev. 2026-06-11)

## Summary

Secondo motore RAG del core: **retrieval ibrido** che fonde la via densa (vettoriale, esistente)
con una via **lessicale BM25** tramite **Reciprocal Rank Fusion**, più un **reranking
cross-encoder opzionale** (extra isolato). Architettura: nuova porta `LexicalIndex` (adapter BM25
con sidecar JSON nell'index dir namespaced), `HybridEngine` con la stessa interfaccia del
baseline, selezione via `Settings.engine` (`SERTOR_ENGINE`, default **hybrid**) risolta solo nel
composition root; la facade riceve la strategia per iniezione (parametro opzionale additivo) — i
consumatori (MCP, CLI) non cambiano. Corpus pre-ibrido → **degradazione a dense-only + warning
strutturato** (mai errore). Qualità dimostrata da ground-truth versionato (≥10 coppie, 6 fissate
in research) che converte i 2 test `xfail` in strict, **senza rete** (embedder mock + lessicale
reale). Dettaglio decisioni: [research.md](research.md) D1..D12.

## Technical Context

**Language/Version**: Python ≥ 3.11 (vincolo d'epica, invariato)

**Primary Dependencies**: `rank-bm25` (nuova, base — BM25Okapi, pura Python; numpy già transitiva
via chromadb); `flashrank` (nuova, **extra `rerank`**, lazy — ONNX, niente torch); esistenti
invariate (chromadb, httpx, python-dotenv, tree-sitter)

**Storage**: vector store esistenti (Chroma locale / Azure AI Search) invariati; nuovo **sidecar
lessicale** JSON in `<index_dir>/lexical/<collection>.json` (atomico, namespaced per
corpus+provider)

**Testing**: pytest, suite `not cloud` senza rete (mock: `FakeEmbedder`, `InMemoryStore`, nuovo
`InMemoryLexicalIndex`); 2 test integrazione ex-`xfail` → strict su ground-truth versionato

**Target Platform**: libreria cross-platform (Windows/Linux/macOS), come il core

**Project Type**: libreria (`sertor-core`) — estensione del nucleo esistente

**Performance Goals**: NFR-04 qualitativo — nessuna attesa percettibile per uso interattivo da
agente su corpus <10k chunk; caricamento BM25 una volta per processo, scoring per query in ms;
misura empirica nel dogfood via `elapsed_ms` (research D11)

**Constraints**: porte `EmbeddingProvider`/`VectorStore` invariate (V-1); baseline immutato
(REQ-070); facade interfaccia invariata per i consumatori (REQ-032); scelte solo nel composition
root (REQ-031); niente segreti nei log (REQ-062)

**Scale/Scope**: corpus tipico < 10.000 chunk (dogfood sertor: ~2.000); ground-truth ≥ 10 coppie

## Constitution Check

*GATE: superato pre-Phase 0 (2026-06-12) e ri-verificato post-design (Phase 1). Costituzione v1.1.0.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS. `HybridEngine` dipende solo
  dalle porte (`EmbeddingProvider`, `VectorStore`, nuove `LexicalIndex`/`Reranker`) e dalle entità;
  `rank_bm25`/`flashrank` importati SOLO negli adapter (lazy nel composition root per flashrank);
  wiring esclusivo in `composition.py` (`build_engine`). Esercitabile con mock, senza cloud/CLI.
- [x] **II — Boundary & local-first:** PASS. BM25 è locale by design; FlashRank è ONNX locale;
  la scelta motore/reranker è da config; nessun tipo di terze parti trapela (la porta lessicale
  ritorna `list[str]` di chunk_id, il reranker ritorna `RetrievalResult`).
- [x] **III — YAGNI & unità piccole:** PASS. Una porta per esigenza reale (lessicale = Must,
  reranker = Should opzionale); delega nativa per-store NON implementata (solo seam, research
  D12); `rank-bm25` minuscola; funzioni pure per tokenize/rrf.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS con deroga deliberata e tracciata:
  la degradazione di REQ-034 (decisione utente DA-1b) è loggata a WARNING, mai silenziosa — vedi
  Complexity Tracking. Tutto il resto è strict: `IndexNotFoundError` (corpus mai indicizzato),
  `ConfigError` (engine invalido; rerank configurato senza extra), sidecar corrotto → errore.
- [x] **V — Testabilità & misure:** PASS. Mock per tutte le porte; ground-truth versionato e
  misura comparativa hit@k/MRR (REQ-051); i 2 `xfail` diventano strict e girano senza rete
  (research D10); baseline di confronto = motore baseline sul medesimo set.
- [x] **VI — Idempotenza & non-distruttività:** PASS. Rebuild congiunto idempotente (stessi
  chunk id); sidecar scritto atomicamente (tmp+rename); nessuna modifica ai file dell'utente;
  install≠run invariato.
- [x] **VII — Leggibilità:** PASS. Vocabolario di dominio: `retrieve`, `fuse`/`rrf`, `rerank`,
  `LexicalIndex`; commenti per intenzione (formula RRF, deroga REQ-034).
- [x] **VIII — Configurabilità centralizzata:** PASS. 5 manopole nuove tutte in `Settings`
  (engine, rrf_c, rrf_pool, rerank_enabled, rerank_pool) con env e default SOLO lì (NFR-05).
- [x] **IX — Osservabilità:** PASS. Eventi `hybrid_query`/`rerank`/`lexical_index_missing`
  (contracts/log-events.md) via `log_event` con redazione; campi diagnostici completi.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS. Nessuna assunzione sull'ospite nel corpo
  del motore; ground-truth come path relativi POSIX (REQ-053) — è una *fixture di test di questo
  repo*, non parte della capacità; il motore opera su qualunque corpus indicizzato dal nucleo.

**Post-design re-check (Phase 1)**: PASS 10/10 — il design (porte/adapter/composition/sidecar)
non ha introdotto violazioni; l'unica deroga (degradazione REQ-034 vs Principio IV) resta quella
giustificata in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/013-motore-ibrido-reranking/
├── plan.md              # questo file
├── research.md          # Phase 0 — decisioni D1..D12
├── data-model.md        # Phase 1 — porte, sidecar, Settings, HybridEngine, ground-truth
├── quickstart.md        # Phase 1 — uso, config, migrazione, limiti dichiarati
├── contracts/
│   ├── lexical-index-port.md
│   ├── hybrid-engine.md
│   └── log-events.md
└── tasks.md             # Phase 2 (/speckit-tasks — NON creato da /speckit-plan)
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/
│   ├── ports.py                     # + LexicalIndex, Reranker, RetrieverStrategy (Protocol)
│   └── entities.py                  # + LexicalEntry (dataclass frozen) — entità esistenti INVARIATE
├── config/settings.py               # + engine, rrf_c, rrf_pool, rerank_enabled, rerank_pool
├── adapters/
│   ├── lexical/
│   │   ├── __init__.py
│   │   └── bm25.py                  # Bm25LexicalIndex: tokenize, sidecar JSON, BM25Okapi lazy
│   └── rerank/
│       ├── __init__.py
│       └── flashrank.py             # FlashRankReranker (extra `rerank`, import lazy)
├── engines/
│   ├── hybrid.py                    # HybridEngine + rrf() pura; baseline.py INVARIATO
│   └── evaluation.py                # generalizzazione type hint (Protocol query+provider)
├── services/
│   ├── indexing.py                  # + parametro opzionale lexical (sink, default None)
│   └── retrieval.py                 # + parametro opzionale retriever (strategia, default None)
└── composition.py                   # + build_engine(); wiring lexical/rerank/facade

tests/
├── unit/
│   ├── test_bm25_lexical_index.py   # tokenizer, sidecar, namespacing, atomicità, determinismo
│   ├── test_rrf_fusion.py           # formula, pareggi, pool, c
│   ├── test_hybrid_engine.py        # retrieve, degradazione REQ-034, strict FR-004, log
│   ├── test_engine_selection.py     # SERTOR_ENGINE, ConfigError, build_engine/build_facade
│   └── test_rerank.py               # pool, opzionalità, ConfigError senza extra (REQ-022)
├── integration/
│   ├── test_baseline_quality.py     # ex xfail → strict (ground-truth, ibrido vs baseline)
│   ├── test_precision_at_k.py       # ex xfail → strict
│   └── test_hybrid_end_to_end.py    # index→query su corpus fixture, facade+MCP invarianza
└── fixtures/
    ├── mocks.py                     # + InMemoryLexicalIndex
    └── ground_truth.py              # ≥10 coppie (6 da research D10), kind symbol|nl

pyproject.toml                       # + rank-bm25 (base); extra rerank = ["flashrank>=0.2"]
```

**Structure Decision**: estensione in-place della libreria `sertor-core` (stessa Clean
Architecture: porte nel dominio, implementazioni in `adapters/`, scelta in `composition.py`).
Nessun pacchetto nuovo; consumatori (`src/sertor_mcp/`, `src/sertor_core/cli/`) **non toccati**
(LSC-3/REQ-032 — la loro invarianza è verificata dai test end-to-end esistenti).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Degradazione silenziosa-per-il-chiamante su sidecar assente (REQ-034) vs Principio IV (errori espliciti) | Decisione utente DA-1b (2026-06-11): col default `hybrid`, ogni indice pre-esistente deve continuare a rispondere senza azioni manuali; lo stato è onesto via WARNING strutturato `lexical_index_missing` (Principio IX) | Errore esplicito (`LexicalIndexNotFoundError`): romperebbe ogni consumatore esistente al primo upgrade — retro-compatibilità (NFR-09) impossibile col default `hybrid`; default `baseline`: scartato dall'utente in D1 («il motore migliore è il default») |
