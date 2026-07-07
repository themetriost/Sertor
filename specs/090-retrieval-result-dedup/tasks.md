---
description: "Task list — E5-FEAT-003 dedup risultati near-duplicate (leva A-07)"
---

# Tasks: Dedup dei risultati near-duplicate nel retrieval

**Input**: Design da `/specs/090-retrieval-result-dedup/` (plan, research, data-model, contracts, quickstart)
**Branch**: `090-retrieval-result-dedup` · **Tests**: unit sul puro + integrazione motori + **misura del lift**

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi) · **[Story]**: US1/US2 · Setup/Foundational/Polish senza label
- Il criterio di «fatto» è il **lift misurato** (gate `eval --fused` rosso→verde), non l'intenzione.

---

## Phase 1: Setup

- [X] T001 Catturare la **misura di partenza**: `uv run --project .sertor sertor-rag eval run --fused` → salvare l'output (gate rosso: `search_docs` hit@3 0.625, union 0.833) come riferimento A/B in scratch

---

## Phase 2: Foundational (BLOCCANTE — usato da tutti i siti)

**Purpose**: la funzione pura + la manopola, prerequisiti di ogni sito d'inserimento.

- [X] T002 Creare la funzione pura `dedup_results(results) -> tuple[list[RetrievalResult], int]` in `src/sertor_core/services/dedup.py`: normalizza il testo (collasso whitespace, case-preserving), chiave = `sha1(norm)`, tiene la **prima** occorrenza per chiave (rank più alto), ritorna `(deduped, removed)` (D2/D3/D7)
- [X] T003 [P] Unit test `tests/unit/test_dedup.py` (F.I.R.S.T., no rete): INV-1 collasso N→1, INV-2 no-op su distinti, INV-3 determinismo/tie-break, INV-4 conteggio (`len(in)==len(out)+removed`), normalizzazione EOL/whitespace (byte-copy CRLF↔LF)
- [X] T004 Aggiungere `dedup_enabled: bool = True` a `Settings` (`src/sertor_core/config/settings.py`) letto con `_bool_env("SERTOR_DEDUP", True)`, stesso pattern di `rerank_enabled`; test di copertura in `tests/unit/test_settings.py`

**Checkpoint fase 2:** funzione pura verde + manopola; nessun sito ancora cablato.

---

## Phase 3: US1 — dedup pre-cut in tutti i siti di retrieval (P1) 🎯 MVP

**Goal**: il top-k non contiene contenuto duplicato; il pool è deduplicato **prima** del cut, con **pool > k**.
**Independent test**: su un corpus con contenuto ripetuto in ≥2 path, il top-k ha 1 istanza; un doc distinto pertinente rientra nel top-k (SC-001).

- [X] T005 [US1] `engines/hybrid.py::retrieve` (path principale): materializzare un pool `P = max(k, rerank_pool)` **anche con reranker off** quando `dedup_enabled` (D1), applicare `dedup_results` su `candidates` **prima** di rerank/`[:k]`, poi cut a k; loggare `deduped=<n>` in `_log_query` (D6)
- [X] T006 [US1] `engines/hybrid.py::retrieve` (fallback dense-only, ramo «no lexical»): fetch pool `P` (non `k`) → `dedup_results` → `[:k]` quando `dedup_enabled`
- [X] T007 [US1] `services/retrieval.py::_search` (fallback senza retriever): fetch pool `P` → dedup → `[:k]`
- [X] T008 [US1] `services/retrieval.py` (fused multi-collezione, ~riga 265): `dedup_results` su `candidates` **prima** di `[:k]`
- [X] T009 [US1] `engines/baseline.py`: dedup del pool prima del cut (stesso pattern; pool `P` quando dedup on)
- [X] T010 [US1] Integrazione `tests/unit/test_hybrid_engine.py` (mock store): dedup pre-cut collassa i duplicati, pool>k backfilla con contenuto distinto, path reranker on/off, `deduped` loggato
- [X] T011 [US1] Test no-op & no-regressione: input distinti → output invariato; `search_code` non regredisce (SC-004)

**Checkpoint US1:** dedup attiva su tutte le superfici; contenuto distinto nel top-k.

---

## Phase 4: US2 — configurabile & host-agnostico (P2)

**Goal**: bypassabile via manopola; funziona su ogni host; nessun asset Sertor-specifico.

- [X] T012 [US2] Aggiungere `SERTOR_DEDUP=true` (documentata) al **template `.env`** dell'installer (`packages/sertor/src/sertor_installer/assets/rag/…`), poi `uv run python -m sertor_installer.sync` + guardia byte; è l'unico tocco host-facing (X)
- [X] T013 [US2] Test bypass: con `SERTOR_DEDUP=false` i risultati/metriche sono **identici** al pre-feature (SC-003) — call-site non invoca la dedup
- [X] T014 [US2] Verifica host-agnosticità: nessuna assunzione sul contenuto ospite nel corpo di `dedup_results`/siti (Principio X); pin/test che gira su un corpus di test generico

**Checkpoint US2:** manopola + host-agnostico.

---

## Phase 5: Polish & misura

- [X] T015 **Misura del lift (SC-002, il gate)**: `eval run --fused` A/B (`SERTOR_DEDUP` off vs on) sul dogfood; confermare gate **verde** (`search_docs` hit@3 ≥ 0.75, union risale, `search_code` non regredisce). **NO `--record-baseline`** finché il lift non è reale (XII)
- [X] T016 [P] Doc utente: menzionare `SERTOR_DEDUP` nella sezione config/provider di `docs/install.md` (host-facing → regola §Feature completa 3)
- [X] T017 **Promuovere il fuzzy near-duplicate** (MinHash/shingling) al backlog E5 (`requirements/retrieval-qualita/epic.md` + roadmap → *Nuove funzionalità*) — non seppellire l'Out-of-Scope
- [X] T018 **Gate pre-merge (SC-005)**: `uv run pytest -m "not cloud"` + `uv run ruff check .` verdi; `git diff --stat` su ingestione/indicizzazione = **vuoto** (query-time only, FR-007)
- [X] T019 Wiki record + roadmap (A-07 → ✅ con lift misurato; E5-FEAT-003 aggiornata); distill/lint dichiarati
- [X] T020 Commit + PR (delega `configuration-manager`, mai master diretto); post-merge: re-lock → re-index → `eval --fused` verde → smoke MCP → EXEC roadmap

---

## Dependencies & ordine

- **Phase 2 (funzione + manopola) BLOCCA Phase 3+** (i siti la usano).
- **US1 (T005–T011)** è l'MVP: i 5 siti sono indipendenti fra loro (file diversi) ma condividono `dedup_results`; T005 (ibrido main) è il path **misurato** → prioritario.
- **T015 (misura) richiede US1 completo** (almeno il path ibrido) sul runtime installato.
- **T018 (gate) e T019/T020 (chiusura)** ultimi.

## Parallel opportunities

- T003 ∥ T004 (test puro ∥ Settings).
- Dentro US1: T007/T008 (facade) ∥ T009 (baseline) — file diversi; T005/T006 su `hybrid.py` sequenziali.
- T016 (doc) ∥ gran parte di Polish.

## MVP scope

**MVP = Phase 2 + US1 path ibrido principale (T002–T005, T010–T011) + T015 misura.** Se il lift è reale sul
path ibrido (il caldo/misurato), la feature consegna valore; gli altri siti (T006–T009) completano la
coerenza FR-004; US2 e Polish rifiniscono.

## Independent test per storia

- **US1**: corpus con contenuto ripetuto → top-k con 1 istanza + doc distinto risalito (SC-001); lift eval (SC-002).
- **US2**: `SERTOR_DEDUP=false` → metriche pre-feature (SC-003); gira su host generico (X).
