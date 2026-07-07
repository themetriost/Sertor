# Implementation Plan: Dedup dei risultati near-duplicate nel retrieval

**Branch**: `090-retrieval-result-dedup` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/090-retrieval-result-dedup/spec.md` — leva A-07 / epica
`retrieval-qualita` (E5-FEAT-003). Diagnosi: `wiki/log/2026-07-07.md`.

## Summary

`search_docs` degrada con la crescita del corpus perché lo **stesso contenuto** vive in più path (i blocchi
`CLAUDE.md` byte-identici alle copie del bundle `assets/**`) e satura il top-k, seppellendo le pagine
canoniche. La feature introduce una **dedup a query-time** dei risultati **prima del cut finale**: una
funzione **pura** `dedup_results(results) → results` che, per ogni gruppo a **contenuto normalizzato
identico**, tiene l'istanza col **rank più alto** e scarta le altre, liberando gli slot per contenuto
distinto. MVP **esatto** (content-hash, zero LLM); il *fuzzy* è rinviato.

**Punto critico (dal codice):** la dedup è efficace **solo con un pool > k**. Nel path ibrido, quando il
reranker è **off** (default), `fused_k = k` → i candidati sono già solo `k`: rimuovere duplicati li
porterebbe **sotto k** senza backfill. Quindi, **quando la dedup è on**, il pool fuso/materializzato PRIMA
del cut deve avere dimensione **`P > k`** (riuso della logica `rerank_pool`, o nuova manopola
`SERTOR_DEDUP_POOL`), poi dedup, poi `[:k]`.

**Approccio:** una funzione pura condivisa (DRY) applicata a **tutti** i siti di retrieval che assemblano
un pool e tagliano al top-k — `HybridEngine.retrieve` (path principale + fallback dense-only),
`BaselineEngine`, e i due path della facade (fallback senza retriever + fused multi-collezione) — dietro la
manopola `SERTOR_DEDUP` (default on). Indicizzazione **invariata** (query-time). `sertor-core` toccato solo
nei siti di retrieval + `Settings`; nessun asset distribuito reso Sertor-specifico (solo la manopola nel
template `.env`).

## Technical Context

**Language/Version**: Python ≥ 3.11 (`sertor-core`).

**Primary Dependencies**: nessuna nuova — `hashlib`/stdlib per il content-hash, `RetrievalResult` di
dominio. **Zero LLM, zero embedding aggiuntivi** (RNF-1).

**Storage**: N/A (query-time; il corpus indicizzato e gli id chunk restano invariati — FR-007).

**Testing**: `pytest` — unit sul puro `dedup_results` (F.I.R.S.T., no rete) + integrazione sui motori con
mock store; **misura del lift** via `sertor-rag eval run --fused` a ground-truth fissa (SC-002).

**Target Platform**: libreria core, consumata via CLI/MCP su qualunque host.

**Project Type**: single project (`src/sertor_core/`).

**Performance Goals**: overhead trascurabile — un passaggio O(n) sul pool (n = dimensione pool, ~decine)
con hashing del testo; nessuna chiamata di rete.

**Constraints**: deterministico (VI), zero LLM (RNF-1), host-agnostico (X), config-driven (VIII), no
re-baseline dell'eval finché il lift non è reale.

**Scale/Scope**: 1 funzione pura + manopola/e in `Settings` + 4-5 siti d'inserimento nel retrieval. Nessun
cambio a ingestione/indicizzazione.

## Constitution Check

*GATE: pass prima di Phase 0, re-check dopo Phase 1.* Costituzione v1.4.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS. La dedup è una **funzione pura di dominio/
  servizio** nel core; i motori la usano. Nessun SDK, nessun import di CLI. Esercitabile con mock.
- [x] **II — Boundary & local-first:** N/A. Nessun provider/backend/store toccato (solo i risultati).
- [x] **III — YAGNI & unità piccole:** PASS. **Una** funzione pura condivisa (DRY) applicata ai siti di
  cut; MVP esatto, fuzzy rinviato. Nessuna astrazione nuova oltre l'helper.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS. La dedup restituisce **meno** risultati in modo
  onesto; nessun `None` silenzioso; il segnale low-confidence esistente resta invariato.
- [x] **V — Testabilità & misure:** PASS. Puro → unit test F.I.R.S.T.; **lift misurato** sull'eval a GT
  fissa (SC-002), gate `--fused` da rosso a verde. Una feature senza misura non è "fatta".
- [x] **VI — Idempotenza & determinismo:** PASS. Chiave deterministica (testo normalizzato), tie-break
  stabile (rank poi `chunk_id`), **no-op** sui risultati già distinti (US1.3). Idempotente.
- [x] **VII — Leggibilità:** PASS. Nome di dominio (`dedup_results`), intento chiaro; helper piccolo.
- [x] **VIII — Configurabilità centralizzata:** PASS. `SERTOR_DEDUP` (default on) + eventuale
  `SERTOR_DEDUP_POOL` in `Settings` (unica fonte); nessun default hardcoded nei componenti.
- [x] **IX — Osservabilità:** PASS. Il log della query riporta il **conteggio dei duplicati rimossi**
  (senza segreti), coerente con l'osservabilità del retrieval esistente.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS. Nessuna assunzione sul contenuto dell'ospite; opera
  su qualunque progetto. **Non** è un fix dogfood-specifico (a differenza dell'escludere `assets/**`, che è
  *Out of Scope* proprio perché blunt/dogfood). Unico tocco host-facing: la manopola nel template `.env`.
- [x] **XI — Consumo via vehicles:** PASS. La dedup vive **dentro** la libreria; i consumatori restano su
  CLI/MCP (facade). Nessun cambio al confine dei vehicles. La misura via `sertor-rag eval` (vehicle).
- [x] **XII — Fail Loud, Fix the Cause:** PASS. **Ripara la causa** (duplicazione nel top-k) invece di
  sopprimere il segnale (no re-baseline del gate rosso finché il lift non è reale). La regressione emersa
  resta visibile finché la fix non la risolve davvero.
- [x] **Allineamento alla missione:** PASS (**forte**). Rafforza direttamente `search_docs` — la **metà
  debole** della **fusione code+doc**, il differenziatore. Migliora la qualità del retrieval reso
  all'agente (precisione del top-k), non deriva su concern periferici.

**Esito: 12/12 + missione PASS.** Nessuna violazione → nessun *Complexity Tracking*.

## Project Structure

### Documentation (this feature)

```text
specs/090-retrieval-result-dedup/
├── plan.md              # questo file
├── research.md          # Phase 0: pool>k, normalizzazione, siti d'inserimento, tie-break
├── data-model.md        # Phase 1: dedup_results (contratto), chiave, manopole Settings
├── quickstart.md        # Phase 1: come misurare il lift (eval --fused) + toggle
├── contracts/
│   └── dedup-behavior.md # Phase 1: contratto semantico della dedup (input→output, invarianti)
├── checklists/requirements.md   # (già presente)
└── tasks.md             # Phase 2 (/speckit-tasks — NON qui)
```

### Source Code (repository root)

```text
src/sertor_core/
├── config/settings.py            # + dedup_enabled (SERTOR_DEDUP, default True) [+ dedup_pool opz.]
├── services/retrieval.py         # dedup nel fallback (no-retriever) + nel fused multi-collezione
├── engines/hybrid.py             # dedup su `candidates` PRIMA del cut; pool>k quando dedup on
├── engines/baseline.py           # dedup sul pool prima del cut
└── services/dedup.py (NUOVO) o domain/util  # `dedup_results()` puro (casa decisa in research)

packages/sertor/src/sertor_installer/assets/rag/…env template   # + manopola SERTOR_DEDUP (host-facing)

tests/unit/test_dedup.py (NUOVO)        # puro: dup esatti collassati, no-op su distinti, determinismo
tests/unit/test_hybrid_engine.py        # dedup pre-cut + pool>k + reranker path
eval/                                    # misura del lift (nessun re-baseline finché il lift non è reale)
```

**Structure Decision.** Single project. Il cuore è **una funzione pura** (`dedup_results`) + il suo
cablaggio ai **siti di cut** del retrieval, dietro una manopola centralizzata. La casa esatta della
funzione (`services/dedup.py` vs un util di dominio) e la sizing del pool (`rerank_pool` riusato vs nuovo
`SERTOR_DEDUP_POOL`) si fissano in `research.md`. Indicizzazione e vehicles invariati.

**Fuori ambito → da promuovere a tasks:** il *fuzzy near-duplicate* (MinHash/shingling) va **promosso al
backlog E5** (roadmap → E5-FEAT-003 follow-up o nuova FEAT), non sepolto nell'Out-of-Scope della spec.

## Complexity Tracking

> Nessuna violazione costituzionale → sezione vuota.
