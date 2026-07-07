# Contract — comportamento della dedup (Phase 1)

L'interfaccia esterna della feature non è una nuova API pubblica: è un **cambio di comportamento** delle
superfici di retrieval esistenti (`search_code`/`search_docs`/`search_combined` via CLI/MCP) + la manopola
`SERTOR_DEDUP`. Qui il contratto osservabile.

## C1 — Dedup pre-cut (FR-001/003, US1)

**Contratto:** con `SERTOR_DEDUP=true`, per ogni superficie, il top-k restituito **non** contiene due
risultati con contenuto normalizzato identico; il pool viene deduplicato **prima** del taglio a k, così gli
slot liberati sono riempiti dal contenuto distinto successivo del pool.

- **Precondizione:** il pool materializzato prima del cut ha dimensione `P ≥ k` (D1: `max(k, rerank_pool)`).
- **Postcondizione:** `∀ i≠j nel top-k: normalize(text_i) ≠ normalize(text_j)`.
- **Test:** corpus con lo stesso testo in ≥2 path → una query che li matcha restituisce **1** istanza; un
  doc distinto pertinente che era a rank>k rientra nel top-k (SC-001 + US1.2 sul dogfood).

## C2 — No-op sui distinti (FR-003, US1.3)

**Contratto:** su risultati già distinti, la dedup **non** cambia ordine né contenuto del top-k.
- **Test:** input senza duplicati → output byte-identico (INV-2). Nessuna regressione su `search_code`
  (SC-004).

## C3 — Bypassabile e host-agnostico (FR-005/006, US2)

**Contratto:**
- `SERTOR_DEDUP=false` → comportamento **identico** al pre-feature (nessuna dedup); metriche eval invariate
  (SC-003).
- La capacità gira su un progetto ospite diverso senza modifiche al corpo (X); nessun asset distribuito
  cambia oltre la riga `SERTOR_DEDUP` nel template `.env`.

## C4 — Lift misurato (FR-testabile via eval, SC-002)

**Contratto:** con la dedup on, il gate `sertor-rag eval run --fused` (oggi **rosso**) torna **verde** a
**ground-truth fissa** (nessun `--record-baseline` finché il lift non è reale):
- `search_docs` hit@3 ≥ 0.75 (baseline), union hit-rate ≥ baseline pertinente;
- `search_code` non regredisce (MRR ~0.74).

## C5 — Osservabilità & core invariato (FR-007/008, SC-005)

**Contratto:**
- Il log della query riporta `deduped=<n>` (rimossi), senza segreti (IX).
- L'indicizzazione è **invariata** (query-time only); `git diff` di ingestione/indexing = vuoto.
- `sertor-core` toccato solo nei siti di retrieval + `Settings`; suite `-m "not cloud"` + `ruff` verdi
  pre-merge.

## Mappa contratto → criteri

| Contratto | Copre |
|-----------|-------|
| C1 | SC-001, US1.1/1.2 |
| C2 | SC-004, US1.3 |
| C3 | SC-003, US2 |
| C4 | SC-002 (lift, gate verde) |
| C5 | SC-005 (core invariato, osservabilità) |
