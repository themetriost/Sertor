# Phase 1 — Data Model: Ricerca semantica della memoria (FEAT-004)

**Branch**: `072-ricerca-semantica-memoria` · **Data**: 2026-06-22

Entità **additive**: nessuna modifica alle entità/porte esistenti (`MemoryArchive`, `EpisodicSearch`,
`VectorStore`, `RetrievalResult`, `Settings.memory_*`). Tutto vive in `services/memory_semantic.py`
(nuovo) + estensioni mirate a `Settings`, `composition`, `cli`, `errors`.

## Entità di dominio (nuove, frozen dataclass, niente SDK)

In `services/memory_semantic.py` (gemelle di `SearchQuery`/`EpisodicHit`/`EpisodicResults`):

```
SemanticMemoryQuery        # input della ricerca semantica
  text: str                # query NL (embeddata)
  since: float | None      # bound su sessions.captured_at (None = aperto)
  until: float | None
  limit: int = 20          # REQ-011, default da SERTOR_MEMORY_SEMANTIC_LIMIT
  # nessun `order`: la semantica ordina SEMPRE per similarità (REQ-009)

SemanticMemoryHit          # unità restituita (REQ-010)
  session_key: str
  turn_index: int          # riferimento all'unità (REQ-010)
  captured_at: float       # timestamp di sessione
  role: str
  snippet: str             # estratto del turno (testo già scrubbed)
  score: float             # similarità coseno (1 - distance), higher = better

SemanticMemoryResults
  hits: tuple[SemanticMemoryHit, ...]   # () = stato vuoto esplicito (no match / indice assente)
  latency_ms: float

SemanticIndexReport        # esito di una indicizzazione/backfill (counts, mai testo)
  embedded: int            # turni nuovi embeddati
  skipped: int             # turni/sessioni già indicizzati (incrementalità)
  errors: int              # turni saltati per embedding/riga invalida (non-fatale)
```

## Identità & namespacing (REQ-006/017/030/032)

- **`chunk_id` del turno** = `f"{session_key}#{turn_index}"` — stabile e deterministico (Principio VI):
  ri-processare lo stesso turno produce lo stesso id → `upsert` idempotente, **niente duplicati**.
- **Collezione vettoriale isolata** (REQ-017, SC-009): `collection_name(memory_settings, embedder)`
  dove `memory_settings` ha `corpus` impostato a un namespace dedicato della memoria distinto dal
  corpus del progetto (es. `f"memory__{settings.corpus}"`). Garantisce che il nome collezione **non
  coincida mai** con quello del corpus codice/doc → contenuto memoria e corpus non condividono store.
- **Watermark = stato dello store** (DA-SS-4, Opzione 3): nessun registro proprio. «Già indicizzato»
  ⇔ i `chunk_id` dei turni della sessione esistono nella collezione corrente. Il **rebuild totale**
  (REQ-032, cambio provider/dim) è **implicito**: provider diverso → `embedder.name` diverso → nome
  collezione diverso → collezione vuota → ripopolata incrementalmente.

## Payload del record vettoriale (`EmbeddedChunk.payload`)

Riusa `EmbeddedChunk(chunk_id, vector, payload)` (entità esistente). `payload` (metrics/citazione,
**testo già scrubbed**, nessun segreto): `text` (snippet sorgente del turno), `session_key`,
`turn_index`, `captured_at`, `role`. Mappato a `SemanticMemoryHit` al ritorno; lo `score` viene da
`RetrievalResult.score` (coseno). Il filtro temporale (REQ-012) è applicato **post-query** sul
`captured_at` del payload (lo store non filtra per range temporale nativamente; il `k` è piccolo).

## Manopole (Settings — UNICA fonte di default, Principio VIII)

| Campo | Env | Default | Nota |
|-------|-----|---------|------|
| `memory_semantic_enabled` | `SERTOR_MEMORY_SEMANTIC` | `False` | opt-in ulteriore, distinto da `SERTOR_MEMORY` (REQ-003) |
| `memory_semantic_limit` | `SERTOR_MEMORY_SEMANTIC_LIMIT` | `20` | tetto risultati (REQ-011), gemello di `episodic_limit` |

Provider = `SERTOR_EMBED_PROVIDER` esistente (REQ-018, nessun selettore nuovo). Store = `build_store`
esistente.

## Errore di dominio (nuovo)

`SemanticMemoryUnavailableError(SertorError)` — sollevato **dal consumer CLI** (non dal core, che
resta non-fatale) quando `--semantic` è chiesto ma la factory ritorna `None` (leva spenta) o l'indice
è assente: messaggio azionabile che nomina `SERTOR_MEMORY_SEMANTIC=true` (+ `SERTOR_MEMORY=true` se è
la cattura a mancare) e `memory index-semantic` per popolare. **Nessun fallback silenzioso** alla
full-text (REQ-015). Coerente con `SessionNotFoundError`/`InvalidTimeWindowError`.

## Componenti (servizio, NO nuova porta)

- `MemorySemanticIndex` (concreto, in `services/memory_semantic.py`): incapsula embedder + store +
  nome collezione. `index_session(session)` (skip se id già presenti → embed turni nuovi → `upsert`),
  `index_all(archive)` (backfill incrementale), `search(query) -> SemanticMemoryResults`. Degradazione
  non-fatale ovunque (store/provider giù → vuoto/errore azionabile, mai crash — REQ-021/022/023).
- **Nessuna porta nuova** (Principio III, YAGNI): single backend, come `MemoryArchive`/`EmbeddingCache`.
- **Aggancio auto-index** (REQ-004/005, A-006): `MemoryArchiveService.archive_all()` riceve un
  `MemorySemanticIndex | None` opzionale (iniettato da composition solo a leva accesa); per ogni
  sessione **appena archiviata** chiama `index_session` in un `try/except` **non-fatale** (REQ-008: il
  grezzo resta, warning, il run continua). A leva spenta riceve `None` → comportamento FEAT-001
  identico (RNF-005).
