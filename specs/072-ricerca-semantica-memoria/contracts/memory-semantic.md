# Contract — `memory.semantic/1` (FEAT-004)

**Branch**: `072-ricerca-semantica-memoria` · **Data**: 2026-06-22

Contratto del percorso semantico della memoria: indicizzazione (auto + backfill) e ricerca. Vehicle =
CLI `sertor-rag memory` (Principio XI). Tutto **gated** da `memory_enabled AND memory_semantic_enabled`.

## Servizio: `MemorySemanticIndex` (services/memory_semantic.py)

### `search(query: SemanticMemoryQuery) -> SemanticMemoryResults`
- Embedda `query.text` (provider da `SERTOR_EMBED_PROVIDER`), interroga lo store (collezione memoria),
  ordina per similarità, applica il filtro temporale `since`/`until` sul `captured_at`, taglia a `limit`.
- `query.text` vuoto/whitespace → `SemanticMemoryResults(hits=(), latency_ms=0.0)` (stato vuoto).
- `since > until` → `InvalidTimeWindowError` (Principio IV, riuso, parità con FEAT-002).
- **Indice assente / collezione vuota** → `hits=()` + warning `memory_semantic_unavailable`
  (reason=`index_absent`), **non** errore (REQ-021).
- **Provider giù a query-time** → errore azionabile (`EmbeddingError` avvolto) o stato vuoto+warning;
  il chiamante non va in crash (REQ-022). Una **riga/embedding invalido** è saltato con warning (REQ-023).
- Emette `memory_semantic_search` (metrics-only): `query_hash`, `query_len`, `since`, `until`, `limit`,
  `results`, `latency_ms`. Query **mai** in chiaro (REQ-027). Emissione non-fatale (REQ-028).

### `index_session(session: ArchivedSession) -> SemanticIndexReport`
- Calcola i `chunk_id` (`session_key#turn_index`) dei turni; **salta** quelli già presenti nella
  collezione (incrementalità, REQ-030); embedda solo i nuovi; `upsert` idempotente (REQ-006).
- Sessione interamente già indicizzata → `embedded=0, skipped=N` (zero chiamate di embedding, NFR-009).
- Guasto store/provider → report con `errors`, warning, **non-fatale** (REQ-008).

### `index_all(archive: MemoryArchive) -> SemanticIndexReport`
- Backfill incrementale (REQ-007): itera le sessioni archiviate, `index_session` su ciascuna; embedda
  solo le unità non ancora indicizzate. Non ri-archivia nulla (REQ-029: l'indice è derivato).
- Emette `memory_semantic_index` (metrics-only): `embedded`, `skipped`, `errors`, `provider`, `latency_ms`.

## Vehicle CLI

### `sertor-rag memory search <query> --semantic [--since] [--until] [-k]`
- `--semantic` assente → percorso **full-text** FEAT-002 invariato (default, REQ-013/016/017).
- `--semantic` con leva accesa → instrada a `MemorySemanticIndex.search` (REQ-014).
- `--semantic` con leva spenta o indice assente → **`SemanticMemoryUnavailableError`** (exit 1):
  messaggio che nomina `SERTOR_MEMORY_SEMANTIC=true` (+ `SERTOR_MEMORY=true` se serve) e `memory
  index-semantic`. **Nessun** fallback silenzioso (REQ-015, SC-005).
- Output umano + `--json`: per ogni hit `session_key`, `turn_index`, `captured_at` (ISO), `role`,
  `snippet`, `score` (REQ-010). Limite di default da `SERTOR_MEMORY_SEMANTIC_LIMIT` (REQ-011).

### `sertor-rag memory index-semantic [--json]` (backfill)
- Gate spento → `SemanticMemoryUnavailableError` (exit 1). Acceso → `index_all` → `SemanticIndexReport`
  (umano + JSON: `embedded`/`skipped`/`errors`). Idempotente: una seconda esecuzione senza nuove
  sessioni → `embedded=0` (SC-006).

### Auto-index a fine sessione (`memory archive` / hook `SessionEnd`)
- A leva semantica accesa, `memory archive` embedda anche le sessioni appena archiviate
  (`MemoryArchiveService` riceve l'indice semantico). Fallimento embedding → grezzo intatto + warning +
  prosegue (REQ-008). A leva spenta → comportamento FEAT-001 identico (REQ-005, RNF-005).

## Invarianti
- **Additività a leva spenta** (RNF-005, SC-011): default off → nessun embedding, nessun import del
  path semantico, nessun file/indice nuovo, costo identico a oggi.
- **Isolamento** (REQ-017, SC-009): collezione memoria ≠ collezione corpus; mai stessi risultati.
- **On-machine col locale** (REQ-019, SC-003): provider locale → zero rete su index+query.
- **Host-agnostico** (REQ-024/025): il corpo opera su `memory.sqlite`, mai branch sull'assistente.
- **Riuso, no nuovo motore** (REQ-016, SC-008): solo `build_embedder`/`build_store`/`collection_name`.
