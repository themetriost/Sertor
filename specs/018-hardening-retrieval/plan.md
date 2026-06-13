# Implementation Plan: Hardening di produzione del livello retrieval (Must)

**Branch**: `018-hardening-retrieval` | **Date**: 2026-06-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/018-hardening-retrieval/spec.md`

## Summary

Chiudere i due **Must** del RAG audit sul livello di Sertor, in modo additivo e retro-compatibile:
**(US1)** resilienza degli embedder con retry+backoff esponenziale+jitter sugli errori transitori
(429/5xx/rete), via un helper condiviso `with_retry` + `RetryPolicy`, manopole in `Settings`, default
attivo e disattivabile (`attempts=1`); **(US2)** segnale di confidenza con una soglia di similarità
opzionale (`SERTOR_MIN_SCORE`, default off) che esclude i risultati deboli e — quando svuota l'esito —
emette un log `low_confidence`, dando all'agente il materiale per astenersi. Nessuna modifica al
contratto `RetrievalResult` né alle porte: la soglia agisce sul ramo a similarità (denso/baseline/facade)
e, nell'ibrido, sul **pool denso prima di RRF** (lo score RRF non è una similarità). Dettaglio decisioni
in [research.md](./research.md); contratto in [contracts/library-contract.md](./contracts/library-contract.md).

## Technical Context

**Language/Version**: Python ≥ 3.11 (stdlib `random`/`time`; nessuna nuova dipendenza).

**Primary Dependencies**: nessuna nuova. Si riusano `httpx` (già negli adapter) e l'eccezione di
dominio `EmbeddingError` con il flag `retriable` già presente.

**Storage**: invariato (Chroma locale / Azure AI Search dietro la porta `VectorStore`).

**Testing**: `pytest` (unit, offline). Provider mock 429→200 e store/embedder mock con score
controllati; `sleep`/`rng` iniettati (nessuna attesa reale, deterministico).

**Target Platform**: libreria importabile (core), consumata da MCP/CLI. Locale e Azure.

**Project Type**: single project (libreria `src/sertor_core/`).

**Performance Goals**: con i default il costo è ~0 sul percorso felice (un solo tentativo, nessun
filtro). Tempo di retry limitato dal numero di tentativi (≲ ~2.5s con i default, SC-002).

**Constraints**: retro-compatibilità totale ai default (SC-004/006); offline-capable (SC-005); nessun
segreto nei log (Principio IX).

**Scale/Scope**: ~3 manopole `Settings`, 1 modulo nuovo (`_retry.py`), 1 funzione pura
(`apply_min_score`), tocchi mirati a 2 embedder + facade + 2 motori + composition.

## Constitution Check

*GATE: Phase 0 e ri-valutato post Phase 1.* Costituzione v1.1.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il retry vive in `adapters/embeddings/`
  (boundary), non nel core di dominio; cattura solo l'eccezione di dominio `EmbeddingError` (nessun SDK
  nel core). Il filtro soglia è una funzione pura in `services/`. Il wiring (RetryPolicy da Settings,
  min_score alla facade) sta SOLO in `composition.py`. PASS.
- [x] **II — Boundary & local-first:** nessuna nuova dipendenza esterna; retry/soglia funzionano
  identici in locale (Ollama/Chroma) e Azure. PASS.
- [x] **III — YAGNI & unità piccole:** helper di retry **condiviso** (no duplicazione tra azure/ollama,
  DRY); nessuna libreria esterna per ~15 righe; soglia = una funzione pura riusata. Nessuna astrazione
  speculativa (il flag-esito ricco è esplicitamente differito). PASS.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** a tentativi esauriti si solleva `EmbeddingError`
  (tipo preservato), non `None`. La lista vuota da soglia è un **segnale intenzionale e loggato**
  (`low_confidence`) su indice **esistente**, non un null silenzioso. PASS.
- [x] **V — Testabilità & misure:** tutto offline con mock; `sleep`/`rng`/`client`/store iniettati;
  retro-compat verificata come regressione (SC-004/006). PASS.
- [x] **VI — Idempotenza & non-distruttività:** il retry non cambia l'idempotenza dell'indicizzazione
  (rebuild-from-scratch invariato); nessun nuovo effetto collaterale. PASS.
- [x] **VII — Leggibilità:** naming di dominio (`with_retry`, `RetryPolicy`, `apply_min_score`,
  `low_confidence`); commenti solo sull'asimmetria voluta (denso vs RRF). PASS.
- [x] **VIII — Configurabilità centralizzata:** i 3 parametri hanno default SOLO in `Settings`, con env
  override; nessun cap/numero hardcoded nei componenti (il tetto del tempo = `max_attempts`). PASS.
- [x] **IX — Osservabilità:** nuovi eventi `embeddings_retry` e `low_confidence`, entrambi via
  `redact()` (nessun segreto). PASS.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** nessuna assunzione sull'ospite; tutto guidato da config;
  funziona su qualunque corpus/ospite senza modifiche al corpo. PASS.

**Esito gate: PASS 10/10, nessuna deroga.** (Ri-valutato dopo il design Phase 1: invariato — il design
non introduce SDK nel core, non rompe contratti, non aggiunge dipendenze.)

## Project Structure

### Documentation (this feature)

```text
specs/018-hardening-retrieval/
├── plan.md              # questo file
├── research.md          # D1..D7 (decisioni risolte)
├── data-model.md        # RetryPolicy, campi Settings, apply_min_score, invarianti
├── quickstart.md        # scenari → comandi/test
├── contracts/
│   └── library-contract.md   # env, with_retry, comportamento retrieval, eventi log
├── checklists/
│   └── requirements.md  # qualità spec (tutti PASS)
└── tasks.md             # generato da /speckit-tasks (non da plan)
```

### Source Code (repository root)

```text
src/sertor_core/
├── config/
│   └── settings.py                 # + embed_retry_attempts, embed_retry_base_s, retrieval_min_score (+ parsing env)
├── adapters/embeddings/
│   ├── _retry.py                   # NUOVO: RetryPolicy + with_retry (helper condiviso)
│   ├── azure.py                    # + retry/sleep/rng nel costruttore; embed() avvolge _embed_batch
│   └── ollama.py                   # idem (stessa logica condivisa)
├── services/
│   └── retrieval.py                # + apply_min_score (pura) ; facade: param min_score + filtro denso/multi + log
├── engines/
│   ├── baseline.py                 # query() filtra per self._settings.retrieval_min_score + log
│   └── hybrid.py                   # retrieve() filtra il pool DENSO prima di RRF + log
└── composition.py                  # build_embedder→RetryPolicy ; build_facade→min_score

tests/unit/
├── test_embed_retry.py             # NUOVO: 429→200, esaurimento→EmbeddingError, non-ritentabile, backoff/jitter deterministico, attempts=1
└── test_confidence_threshold.py    # NUOVO: in-dominio vs fuori-dominio, log low_confidence, soglia None = regressione, baseline+hybrid+facade
```

**Structure Decision**: single project, libreria `src/sertor_core/`. Tocchi mirati e additivi ai file
esistenti elencati; un solo modulo nuovo (`_retry.py`) e due file di test nuovi. Allineato all'attuale
layout (domain/services/adapters/engines/config/composition).

## Complexity Tracking

> Nessuna violazione del Constitution Check: sezione non necessaria.
