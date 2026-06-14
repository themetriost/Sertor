# Tasks — Cache embeddings per content-hash + token nei log (feature 019)

**Branch**: `019-hardening-cache-token` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Task ordinati per dipendenze, organizzati per user story. `[P]` = parallelizzabile (file diversi, nessuna
dipendenza). MVP = **US1** (cache). US2 (token nei log) è indipendente e può procedere in parallelo a US1
dopo il foundational.

Convenzioni: tutti i test sono **offline** (Principio V), niente rete. Suite: `uv run pytest -m "not cloud"`;
lint: `uv run ruff check .`.

---

## Phase 1 — Setup

- **T001** — Verifica baseline verde: `uv run pytest -m "not cloud"` e `uv run ruff check src/ tests/`
  passano sullo stato attuale del branch (punto di partenza pulito prima di toccare gli embedder).

## Phase 2 — Foundational (prerequisiti condivisi US1/US2)

- **T002** [P] — Estendi `tests/fixtures/mocks.py` con due fake embedder che soddisfano la porta
  `EmbeddingProvider` (`name`/`dim`/`batch_size`/`embed`):
  - `CountingEmbedder`: ritorna vettori deterministici (es. da hash del testo) e **conta** quante volte
    `embed` viene chiamato e con quanti testi (per misurare cache hit/miss → SC-001/002/004).
  - `TokenReportingEmbedder` **non** serve qui (i token escono dai veri Azure/Ollama via log): per US2 si
    testano direttamente Azure/Ollama con un fake `httpx.Client`. Documenta in commento perché il fake
    embedder non riporta token.

## Phase 3 — US1: Cache embeddings per content-hash (Priority P1, MVP)

**Obiettivo**: re-index di corpus invariato → zero ri-embedding (SC-001).
**Test indipendente**: `test_embedding_cache.py` con `CountingEmbedder` + `tmp_path`.

- **T003** — `config/settings.py`: aggiungi il campo `embed_cache_enabled: bool = False` e il wiring in
  `load()` (`_bool_env("SERTOR_EMBED_CACHE", False)`). Commento d'intenzione (manopola di costo,
  default off = rebuild full odierno). [FR-007]
- **T004** — `adapters/embeddings/cache.py` (NUOVO): classe `EmbeddingCache(index_dir)` — store SQLite
  `<index_dir>/embed_cache.sqlite`, tabella `embeddings(model, content_hash, vector BLOB, PK(model,
  content_hash))` con `CREATE IF NOT EXISTS` lazy; `get(model, hashes) -> dict[str, list[float]]`
  (`SELECT … WHERE content_hash IN (…)`, deserializza `array('d')`); `put(model, items)`
  (`INSERT OR IGNORE … executemany`, serializza `array('d').tobytes()`). **Degrado non-fatale**: cattura
  `sqlite3.Error` in get/put → `{}` / no-op + `log_event(WARNING, "embeddings_cache_unavailable",
  reason=…)`, mai solleva. [FR-002/003/004/006, data-model §1]
- **T005** — Nello stesso `cache.py`: classe `CachingEmbedder(inner, cache)` che implementa
  `EmbeddingProvider`. `embed(texts)`: calcola `sha256` per testo, `cache.get` in blocco, raccoglie i
  **miss unici** (dedup in-call), chiama `inner.embed(miss_unici)`, `cache.put` dei nuovi, ricostruisce
  l'output nell'ordine originale (mappa hash→vettore), aggiorna `self.dim` dal primo vettore prodotto,
  emette `log_event(INFO, "embeddings_cache", provider=inner.name, hits, misses, total)`. `name`/
  `batch_size` delegati all'inner; `[]` su input vuoto. [FR-001/005/010, contracts/embedding-cache.md, D8]
- **T006** — `composition.py`: `build_embedder(settings, *, cache: bool = False)` — dopo aver costruito
  l'embedder concreto, se `cache` avvolgilo in `CachingEmbedder(inner, EmbeddingCache(settings.index_dir))`
  (import lazy del modulo cache). `build_indexer` passa `cache=settings.embed_cache_enabled`;
  facade/baseline/`build_engine` restano a `build_embedder(settings)` (cache=False). [FR-007, D7]
- **T007** — `tests/unit/test_embedding_cache.py` (NUOVO): 
  1. **hit/miss**: due `embed` consecutivi sugli stessi testi → il secondo non chiama l'inner (counter
     invariato), output identico. [SC-001]
  2. **miss parziale**: cambia un sottoinsieme dei testi → l'inner è chiamato solo coi cambiati/nuovi. [SC-002]
  3. **dedup in-call**: testi duplicati nello stesso `embed` → l'inner riceve una sola occorrenza. [D8]
  4. **cross-model**: due `CachingEmbedder` con `inner.name` diverso sullo stesso store → nessun hit
     incrociato (ri-embedda col secondo modello). [SC-004]
  5. **equivalenza**: vettori da cache == vettori dall'inner (round-trip float64 esatto). [FR-005]
  6. **dim all-hit**: con tutto in cache, `embedder.dim` è valorizzato (l'inner non è chiamato). [D8]
  7. **degrado non-fatale**: store corrotto/illeggibile (file spazzatura o dir read-only simulata) →
     `embed` funziona come tutto-miss, nessuna eccezione, warning emesso. [FR-004]
  8. **persistenza tra istanze**: nuova `EmbeddingCache` sullo stesso `index_dir` vede i vettori scritti
     prima (rebuild successivo). [FR-006]

## Phase 4 — US2: Token nei log (Priority P2)

**Obiettivo**: l'evento di embedding logga i token quando disponibili (REQ-H5).
**Test indipendente**: `test_embedding_token_log.py` con fake `httpx.Client`.

- **T008** [P] — `adapters/embeddings/azure.py`: estrai `_embed_batch` per restituire
  `(vettori, tokens | None)` (legge `r.json().get("usage", {}).get("total_tokens")`); aggiorna
  `_embed_batch_resilient` e `embed()` per propagare la tupla, accumulare i token tra i batch ed emettere
  **un** `log_event(INFO, "embeddings", provider=self.name, texts=len(texts), **({"tokens": t} if have else {}))`.
  Il percorso d'errore (`embeddings_error`, `EmbeddingError`) resta invariato. [FR-008/009, D5]
- **T009** [P] — `adapters/embeddings/ollama.py`: stessa modifica; tokens best-effort da
  `r.json().get("prompt_eval_count")` (può mancare → `None` → campo omesso). [FR-008/009, D5]
- **T010** — `tests/unit/test_embedding_token_log.py` (NUOVO): con un fake `httpx.Client` che ritorna un
  JSON con `usage.total_tokens` → l'evento `embeddings` contiene `tokens` (cattura via `caplog`/handler);
  con un JSON **senza** usage → evento emesso senza il campo `tokens`, nessun errore; verifica anche
  Ollama con/senza `prompt_eval_count`. [SC-005]

## Phase 5 — Polish & chiusura

- **T011** [P] — Verifica che `embed_cache.sqlite` sia git-ignored: vivendo sotto `index_dir` (`.index*`)
  è già coperto dai pattern esistenti; aggiungi un'asserzione/nota se necessario. Aggiorna i template
  `.env` (`packages/sertor/assets/rag/env.*.tmpl`) e `docs/install.md` con la manopola `SERTOR_EMBED_CACHE`
  (commento in inglese, coerente col tema lingua). [FR-007, costituzione §Sicurezza]
- **T012** — Suite completa verde + ruff pulito: `uv run pytest -m "not cloud"` (root + packages) e
  `uv run ruff check src/ tests/ packages/`. Retro-compatibilità: con cache off e nessun token, comportamento
  invariato (SC-003). [SC-003]
- **T013** — Aggiorna `quickstart.md` se emergono scostamenti dal vivo; **T post-merge** (non in questa
  fase): abilitare `SERTOR_EMBED_CACHE=true` sul `.env` del corpus `sertor` e re-index dogfood.

---

## Coverage FR → task

| FR | Task |
|---|---|
| FR-001 (hit non ri-embeddano) | T005, T007.1 |
| FR-002 (chiave contenuto+modello) | T004, T007.4 |
| FR-003 (persistenza tra run) | T004, T007.8 |
| FR-004 (degrado non-fatale) | T004, T005, T007.7 |
| FR-005 (equivalenza indice) | T005, T007.5 |
| FR-006 (aggiorna cache coi miss) | T004, T005, T007.8 |
| FR-007 (manopola, default off) | T003, T006, T011 |
| FR-008 (token quando disponibili) | T008, T009, T010 |
| FR-009 (omesso se assente) | T008, T009, T010 |
| FR-010 (distingue cache-hit) | T005 (evento `embeddings_cache`), T007.1 |
| FR-011 (additivo, porta invariata) | T005, T008, T009 (firma `embed` invariata) |
| FR-012 (testabile senza rete) | T002, T007, T010 |
| FR-013 (no regressione default) | T006, T012 |

## Percorso critico

Setup (T001) → Foundational (T002) → **US1** T003→T004→T005→T006→T007 (MVP). **US2** (T008/T009/T010)
parallelizzabile dopo T001/T002 (file diversi: azure.py/ollama.py vs cache.py). Polish (T011-T013) alla
fine. T004/T005 nello stesso file (`cache.py`) → in serie.
