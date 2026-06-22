# Phase 0 — Research: Ricerca semantica opzionale sull'archivio (FEAT-004)

**Branch**: `072-ricerca-semantica-memoria` · **Data**: 2026-06-22

> Risolve le forche di design (DA-SS-2..5) ancorando ogni decisione al codice reale (verifica via MCP
> `sertor-rag`, nessun errore tool). Le decisioni di scope fissate (DA-SS-1 = store dedicato, trigger
> auto a fine sessione, modo separato opt-in, privacy `SERTOR_MEMORY_SEMANTIC`, incrementalità a
> watermark) **non** si riaprono: qui si chiude il *come* di dettaglio.

## Ancoraggio verificato (dato di partenza, non da progettare)

- **Archivio** = `MemoryArchive` (`src/sertor_core/adapters/memory/archive.py`): tabelle
  `sessions(session_key PK, project_id, captured_at, adapter_kind, metadata)` e
  `turns(session_key, turn_index, role, ts, content, PRIMARY KEY (session_key, turn_index))`.
  Append-only (`INSERT OR IGNORE`, nessun `DELETE`/`REPLACE`), `content` **già scrubbed**. Componente
  concreto, NO porta (single consumer).
- **Full-text** = `EpisodicSearch` (`src/sertor_core/services/episodic_search.py`): FTS5 su
  `turns.content` nello STESSO `memory.sqlite`, granularità **turno**, `SearchQuery`/`EpisodicHit`/
  `EpisodicResults`, evento `episodic_search` (query **hashata**), `InvalidTimeWindowError` su
  `since>until`, degradazione non-fatale (`archive_absent`/`fts5_unavailable` → vuoto+warning).
- **Composition** (`src/sertor_core/composition.py`): `build_embedder` (4 rami, lazy, `allow_download`
  solo sul path d'indicizzazione), `build_store` (Chroma locale di default), `collection_name(settings,
  embedder)` namespaced per `(corpus, provider)` (provider name include la dimensione vettore →
  collezioni di dimensioni diverse non si mescolano). `build_episodic_search`/`build_memory_archiver`/
  `build_memory_reader` ritornano **`None`** a `SERTOR_MEMORY=false` (gate privacy).
- **Servizio di archiviazione** = `MemoryArchiveService.archive_all()` (`services/memory_archive.py`):
  discovery → read → scrub → `upsert`. È il **punto di aggancio** dell'auto-index (US3/A-006).
- **Porte** (`domain/ports.py`): `EmbeddingProvider.embed(texts)->vectors`, `VectorStore`
  (`upsert`/`query(collection, vector, k, doc_type)`/`delete`/`reset`/`exists`/`list_collections`).
  `RetrievalResult(text, path, chunk_id, doc_type, score, metadata)` con `score = 1 - distance` (coseno).
- **Precedente «store concreto senza porta»**: `EmbeddingCache` (`adapters/embeddings/cache.py`) e
  `SqliteObservabilityStore` — SQLite stdlib, lazy, degradazione non-fatale. È il pattern da seguire.
- **Manopole memoria in `Settings`**: `memory_enabled` (`SERTOR_MEMORY`), `memory_adapter`,
  `memory_retention_days`, `memory_scrub_patterns`, `episodic_limit`, `episodic_snippet_tokens`,
  `memory_list_limit`.

## Decisioni di design

### DA-SS-2 — Granularità dell'unità indicizzata → **TURNO**

- **Decisione:** l'unità embeddata/restituita è il **turno** (`(session_key, turn_index)`), in parità
  con `EpisodicSearch` (FEAT-002 indicizza per turno). `chunk_id` semantico = `f"{session_key}#{turn_index}"`.
- **Razionale:** (1) **coerenza** con la full-text (stessa unità citabile, stessi campi di risultato
  → US1/REQ-010 con `session_key`+`turn_index`+`captured_at`+`snippet`+`score`); (2) lo schema `turns`
  **è già** a quel grano; (3) il watermark append-only è naturale sul turno (un turno, una volta
  scritto, non muta — REQ-030/031). La sessione intera diluirebbe il segnale e perderebbe la citazione
  al turno; il chunk sub-turno è over-engineering per uno Should (YAGNI, Principio III).
- **Tetto token (turni lunghi):** i provider locali di default (`glove`/`hash`) **non hanno un tetto
  token rigido** — `glove` fa media dei vettori token, `hash` è char-n-gram: un turno lungo non rompe
  l'embedding, al più ne diluisce il segnale. I provider cloud (Azure/Ollama) hanno un limite, ma il
  default è locale e la mitigazione è documentale. **Decisione:** **nessun chunking sub-turno** nel MVP
  (Principio III); se un turno eccede, l'embedder lo gestisce (locale) o l'errore di embedding è
  **non-fatale** per quel turno (REQ-023/008, US6). Un chunking token-cap resta leva futura (roadmap),
  non MVP.
- **Soglia di latenza (NFR-003, ora fissata):** scelta la granularità turno e il limite di default
  (`SERTOR_MEMORY_SEMANTIC_LIMIT=20`, gemello di `episodic_limit`), si fissa la soglia a **< 1 s p95**
  per una query semantica su un archivio tipico (≤ qualche migliaio di turni), col provider locale —
  coerente col profilo di `EpisodicSearch` (misurato < 0.1 ms su 5062 turni FTS; l'embedding della
  query col provider locale è il costo dominante, sub-secondo su CPU). Verificabile in test con embedder
  mock (latenza dello store, non della rete).

### DA-SS-3 — Superficie utente → **`sertor-rag memory search --semantic`**

- **Decisione:** estendere il comando esistente `memory search` con un flag booleano `--semantic`
  (un comando, due modi). Default (assente) = full-text FEAT-002 invariata; `--semantic` = instrada
  alla ricerca semantica. **Nessun fallback silenzioso** (REQ-015): `--semantic` con la leva semantica
  spenta (factory → `None`) → `ConfigError` azionabile che nomina `SERTOR_MEMORY_SEMANTIC=true` (exit
  1 via `main()`), come `_require_episodic_search` fa già col gate `SERTOR_MEMORY`.
- **Razionale:** meno superficie, coerenza con i flag già presenti su `memory search` (`--since`,
  `--until`, `--order`, `-k`); il filtro temporale (REQ-012) riusa gli stessi argomenti. Un
  sotto-comando dedicato duplicherebbe parsing e args senza valore. La **parità MCP** (esporre
  `--semantic` via server MCP) è **FEAT-010**, fuori ambito.
- **Backfill (REQ-007, US6):** nuovo sotto-comando `memory index-semantic` (gemello di `memory
  archive`) che embedda le sessioni di backlog non ancora indicizzate (incrementale per costruzione,
  vedi DA-SS-4). Stesso gate; senza opt-in → `ConfigError`.

### DA-SS-4 — Forma del marker di watermark → **derivare dallo stato del vector store (Opzione 3)**

- **Decisione:** **nessun marker proprio**; il «già indicizzato» è **derivato dallo store**. La
  collezione vettoriale è namespaced `(corpus-memoria, provider)` via `collection_name`; il `chunk_id`
  di un turno è **stabile e deterministico** (`f"{session_key}#{turn_index}"`). L'incrementalità =
  **`upsert` idempotente** (la porta `VectorStore.upsert` è idempotente sugli stessi id) + **skip a
  livello di sessione**: prima di embeddare una sessione si interroga lo store per i `chunk_id` dei
  suoi turni; se sono già presenti, si salta (zero chiamate di embedding → REQ-030/NFR-009). La
  presenza si verifica con un `query`/lookup per id sui turni della sessione candidata.
- **Perché non Opzione 1 (colonna in `memory.sqlite`):** scriverebbe su una tabella di FEAT-001
  (l'archivio è append-only e di proprietà di un'altra feature) — accoppiamento indesiderato e
  violazione del confine. Inoltre renderebbe il marker e lo store **divergibili** (un reset dello store
  lascerebbe il flag «true» a torto).
- **Perché non Opzione 2 (manifest SQLite separato):** è il pattern di FEAT-009, ma quello è
  **file-keyed per file mutabili** (mtime+hash, change/delete detection). Qui l'archivio è
  **append-only** e gli id sono **stabili e già nello store**: un secondo registro sarebbe una **fonte
  di verità duplicata** che può divergere dallo store (Principio III/VI — niente stato ridondante).
  Lo store **è già** il registro durevole. (Costo: un lookup per id allo store per sessione candidata;
  trascurabile e sulla macchina.)
- **Rebuild totale (REQ-032) = IMPLICITO via `collection_name`.** Cambiare provider/dimensione vettore
  cambia il segmento `_sanitize(embedder.name)` del nome collezione → **collezione diversa**, vuota →
  l'incrementale la riempie da zero ai prossimi archivi/backfill. È **esplicito e osservabile** perché
  l'evento di indicizzazione porta `provider` e l'utente lancia `memory index-semantic` per popolare.
  **Nessun caso di ri-embed «in-place»**: o l'id esiste nella collezione corrente (skip), o non esiste
  (embed). Confermato il punto del prompt: il namespacing rende il rebuild di REQ-032 implicito.
- **Idempotenza (REQ-006):** garantita dall'`upsert` su id stabili + dallo skip; ri-processare una
  sessione già indicizzata non produce duplicati né nuove chiamate di embedding.

### DA-SS-5 — Nome manopola → **`SERTOR_MEMORY_SEMANTIC`** (booleana, default off)

- **Decisione:** campo `Settings.memory_semantic_enabled` da `SERTOR_MEMORY_SEMANTIC` (default
  `False`), accanto alle manopole memoria. + `SERTOR_MEMORY_SEMANTIC_LIMIT` (default 20, gemello di
  `episodic_limit`) per il tetto risultati (REQ-011). **Nessun nuovo selettore provider** (REQ-018):
  si riusa `SERTOR_EMBED_PROVIDER`.
- **Gate a due strati (REQ-002/003):** la factory del percorso semantico ritorna `None` se
  `NOT (memory_enabled AND memory_semantic_enabled)`. Accendere la sola cattura non accende mai
  l'embedding (REQ-003); accendere la sola semantica senza cattura → inattiva + dipendenza segnalata
  (REQ-002: con `SERTOR_MEMORY=false` non c'è archivio da embeddare → factory `None`, warning).

## Privacy & on-machine (REQ-018..020)

- Con provider locale di default (`glove`/`hash`, FEAT-011), index + query sono **offline** (RNF-1):
  l'embedder locale non fa rete, lo store Chroma è su disco. Verificabile con embedder mock (nessuna
  rete) in test (RNF-5).
- Con provider cloud (Azure/Ollama remoto), l'auto-index a fine sessione manda contenuto (già
  scrubbed) fuori macchina: implicazione **esplicita** (REQ-020) via warning all'attivazione del path
  cloud + nota in doc/quickstart. Nessun selettore nuovo (REQ-018): è l'`SERTOR_EMBED_PROVIDER` esistente.

## Riuso vs nuovo motore (REQ-016, SC-008)

Si riusano **solo le primitive**: `build_embedder`, `build_store`, `collection_name` (+ la porta
`VectorStore`). **Nessun nuovo engine di retrieval** (no `BaselineEngine`/`HybridEngine` per la
memoria): il servizio semantico embedda la query e chiama `store.query(collection, vector, k)`
direttamente, poi mappa i `RetrievalResult` ai risultati semantici della memoria (sessione+turno).
L'indicizzazione **non** usa `IndexingService.index()` (file-oriented, manifest file-keyed) — DA-SS-1.

## Osservabilità (REQ-026..028)

Due eventi metrics-only via `log_event`, gemelli di `episodic_search`/`embeddings`:
- `memory_semantic_index` (a indicizzazione): `units` (turni embeddati), `provider`, `latency_ms`,
  `skipped` (già indicizzati). **Mai** testo di transcript.
- `memory_semantic_search` (a query): `query_hash` (sha256[:16], mai in chiaro), `query_len`,
  `since`/`until`, `limit`, `results`, `latency_ms`. Coerente con `episodic_search`.
- Emissione **non-fatale** (try/except, come `_emit_event` di `EpisodicSearch`).

## Isolamento dal corpus (REQ-017, SC-009)

La collezione della memoria usa un **corpus namespace dedicato** distinto da quello del progetto:
`collection_name` con `settings.corpus` impostato a un valore-memoria (es. prefisso `memory:`), così
il nome collezione differisce sempre da quello del corpus codice/doc. Contenuto memoria e corpus non
condividono mai collezione → mai negli stessi risultati. (Vedi data-model per la regola esatta.)

## Estensioni / debiti (promossi, non sepolti)

- **Distribuzione via installer** (DA-SS-6): manopole `.env` + asset hook → **FEAT-009** (owner
  `sertor install`). Debito di completamento, da chiudere prima del *done* della capacità. Non risolto
  qui.
- **Parità MCP** del `--semantic` → **FEAT-010** (backlog epica). Fuori ambito.
- **Chunking token-cap dei turni lunghi** → leva futura (roadmap *Nuove funzionalità da discutere*),
  solo se i numeri mostrano turni troppo lunghi per i provider cloud.
- **Retention/cancellazione** dell'indice semantico → **FEAT-006**; qui solo il gancio di
  ricostruibilità (REQ-029: l'indice è derivato e ricostruibile dall'archivio).
