# Tasks — Ricerca semantica opzionale sull'archivio (FEAT-004)

**Branch**: `072-ricerca-semantica-memoria` · **Generato**: 2026-06-22
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/memory-semantic.md`](contracts/memory-semantic.md) ·
**Requisiti**: `requirements/memoria-conversazioni/ricerca-semantica/requirements.md`

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO a leva spenta.** Con `SERTOR_MEMORY_SEMANTIC=false` (default),
> comportamento e costo sono identici a oggi: nessun embedding, nessun indice nuovo, nessun import del
> percorso semantico. La factory `build_memory_semantic_index` ritorna `None` → `build_memory_archiver`
> si comporta come FEAT-001 (RNF-005/SC-011). Il gate a due strati (REQ-001/002/003) è la garanzia
> centrale di privacy: accendere la cattura non accende mai l'embedding.
>
> **Strategia MVP/incrementale.**
> - **Setup** (TASK-S01–S02): manopole e errore di dominio. Prerequisiti zero; bloccanti per tutto.
> - **Fondazionale** (TASK-F01): entità additive + `MemorySemanticIndex` nel nuovo servizio; zero
>   consumatori toccati; testabile in isolamento con mock.
> - **Story 1 — Ricerca semantica** (TASK-US1-01..04): composition + aggancio archivio + CLI search
>   + output. Storie priorità P1 Must.
> - **Story 2 — Privacy a strati** (TASK-US2-01..02): gate doppio in composition + test gate.
> - **Story 3 — Indicizzazione automatica e incrementale** (TASK-US3-01..02): auto-index in
>   `archive_all` + test incrementalità.
> - **Story 4 — Modo separato, no fallback silenzioso** (TASK-US4-01..02): routing CLI + errore.
> - **Story 5 — On-machine col provider locale** (TASK-US5-01): verifica offline/rete zero.
> - **Story 6 — Degradazione non-fatale e backfill** (TASK-US6-01..03): backfill CLI + degradazione.
> - **Polish/cross-cutting** (TASK-P01–P03): suite verde, lint, additività residua.
>
> L'ordine tra le User Story P1 (1–5) è orientato al valore: le fondamenta (servizio) abilitano
> prima la ricerca (US1), poi la privacy (US2), poi l'indicizzazione automatica (US3), poi il
> routing (US4), poi l'on-machine (US5). US6 (P2) costruisce sopra le P1.

---

## Fase 0 — Setup: manopole ed errore di dominio (2 task)

> Prerequisiti: nessuno. Bloccante per tutte le fasi successive.

### TASK-S01 — Aggiungi `memory_semantic_enabled` e `memory_semantic_limit` in `config/settings.py`
**File**: `src/sertor_core/config/settings.py`
→ dipende da: nessuno
- [ ] Aggiungi il campo `memory_semantic_enabled: bool = False` letto da
      `SERTOR_MEMORY_SEMANTIC` (default `False`). Il campo è **distinto** da `memory_enabled`
      (`SERTOR_MEMORY`) — accendere la cattura non deve mai accendere l'embedding (REQ-003/FR-003).
- [ ] Aggiungi il campo `memory_semantic_limit: int = 20` letto da `SERTOR_MEMORY_SEMANTIC_LIMIT`
      (default `20`, gemello di `episodic_limit`), tetto risultati della ricerca (REQ-011/FR-014).
- [ ] Aggiorna il metodo `load()` (o la logica di lettura env) per includere i due nuovi campi,
      seguendo il pattern degli altri campi `SERTOR_MEMORY_*` già presenti.
- [ ] Posiziona i due campi nella sezione `memory_*` di `Settings`, ordinati dopo i campi
      `memory_` esistenti; nessun default hardcodato altrove (Principio VIII).
- [ ] Verifica: `Settings()` costruito senza env → `memory_semantic_enabled=False`,
      `memory_semantic_limit=20`; con `SERTOR_MEMORY_SEMANTIC=true` nel env →
      `memory_semantic_enabled=True`; test parametrici aggiornati (o nuovo test unitario se
      la suite esiste già per `Settings`).

### TASK-S02 [P] — Aggiungi `SemanticMemoryUnavailableError` in `domain/errors.py`
**File**: `src/sertor_core/domain/errors.py`
→ dipende da: nessuno
- [ ] Definisci `SemanticMemoryUnavailableError(SertorError)` come errore di dominio azionabile
      (REQ-015/FR-018, Principio IV). Il messaggio nomina esplicitamente:
      - `SERTOR_MEMORY_SEMANTIC=true` (se la semantica è off),
      - `SERTOR_MEMORY=true` (se è la cattura a mancare — REQ-002),
      - `sertor-rag memory index-semantic` (per popolare l'indice se assente).
- [ ] **Nessun fallback silenzioso**: questo errore è sollevato dal consumer CLI quando
      `--semantic` è richiesto ma la factory ritorna `None` o l'indice è assente (data-model §Errore).
- [ ] Il core (`MemorySemanticIndex`) resta non-fatale (degradazione via `hits=()` + warning):
      l'errore azionabile è sollevato **solo nel CLI** (confine D↔N — REQ-015 vs REQ-021).
- [ ] Coerente con `SessionNotFoundError`/`InvalidTimeWindowError` già presenti nello stesso file.
- [ ] Verifica: importabile da `sertor_core` come le altre eccezioni; nessun import circolare.

---

## Fase 1 — Fondazionale: servizio `MemorySemanticIndex` (1 task)

> Prerequisiti: TASK-S01 (manopole), TASK-S02 (errore). Bloccante per tutte le storie.
> Testabile in isolamento completo con embedder e store mock.

### TASK-F01 — Crea `services/memory_semantic.py` con entità + `MemorySemanticIndex`
**File**: `src/sertor_core/services/memory_semantic.py` (NUOVO)
→ dipende da: TASK-S01
- [ ] Definisci le quattro entità frozen dataclass di dominio (data-model §Entità, nessun SDK):
      - `SemanticMemoryQuery(text: str, since: float | None, until: float | None, limit: int = 20)`
      - `SemanticMemoryHit(session_key: str, turn_index: int, captured_at: float, role: str,
        snippet: str, score: float)` — porta almeno i 6 campi richiesti (REQ-010/FR-013).
      - `SemanticMemoryResults(hits: tuple[SemanticMemoryHit, ...], latency_ms: float)` —
        `hits=()` è lo stato vuoto esplicito (contratto §search).
      - `SemanticIndexReport(embedded: int, skipped: int, errors: int)` — counts, mai testo.
- [ ] Implementa `MemorySemanticIndex` (componente concreto, **NO nuova porta** — Principio III):
      ```
      class MemorySemanticIndex:
          def __init__(self, embedder: EmbeddingProvider, store: VectorStore,
                       collection: str, settings: Settings): ...
          def search(query: SemanticMemoryQuery) -> SemanticMemoryResults: ...
          def index_session(session: ArchivedSession) -> SemanticIndexReport: ...
          def index_all(archive: MemoryArchive) -> SemanticIndexReport: ...
      ```
- [ ] **`search`** (REQ-009/010/011/012/FR-012..015, contratto §search):
      - Query NL → `embedder.embed([query.text])` → `store.query(collection, vector, k=query.limit)`
        → mappa `RetrievalResult` → `SemanticMemoryHit` (campi da `payload`: `session_key`,
        `turn_index`, `captured_at`, `role`, snippet; `score` da `RetrievalResult.score`).
      - Filtro temporale `since`/`until` applicato **post-query** sul `captured_at` del payload
        (data-model §Payload); `since > until` → `InvalidTimeWindowError` (riuso, parità FEAT-002).
      - `query.text` vuoto/whitespace → `SemanticMemoryResults(hits=(), latency_ms=0.0)`.
      - Indice assente/collezione vuota → `hits=()` + `log_event(warning, memory_semantic_unavailable,
        reason="index_absent")` — **non errore** (REQ-021/FR-024).
      - Provider giù → errore azionabile avvolto o stato vuoto + warning, chiamante non crasha
        (REQ-022/FR-025, Principio IV).
      - Unità corrotta/embedding invalido → salta con warning, restanti serviti (REQ-023/FR-026).
      - Emette `memory_semantic_search` metrics-only: `query_hash` (sha256[:16], mai in chiaro),
        `query_len`, `since`/`until`, `limit`, `results`, `latency_ms` (REQ-027/FR-030).
      - Emissione non-fatale (try/except, REQ-028/FR-031).
- [ ] **`index_session`** (REQ-006/030/031, contratto §index_session):
      - Calcola `chunk_id = f"{session_key}#{turn_index}"` per ogni turno (stabile e deterministico,
        data-model §Identità, Principio VI).
      - Determina le unità nuove: recupera gli id già presenti nella collezione per questa sessione
        (watermark = stato dello store, DA-SS-4/Opzione 3); salta quelli già presenti → `skipped`.
      - Embedda solo i turni nuovi: `embedder.embed([turn.content for turn in new_turns])`.
      - Costruisce `EmbeddedChunk(chunk_id, vector, payload)` con payload = `{text: snippet,
        session_key, turn_index, captured_at, role}` (testo già scrubbed da FEAT-001, A-007).
      - `store.upsert(collection, chunks)` — idempotente sugli stessi id (REQ-006/FR-006).
      - Sessione interamente già indicizzata → `SemanticIndexReport(embedded=0, skipped=N, errors=0)`
        con **zero chiamate di embedding** (NFR-009/RNF-6).
      - Guasto store/provider → `SemanticIndexReport(embedded=0, skipped=0, errors=N)` + warning,
        non-fatale (REQ-008/FR-010).
- [ ] **`index_all`** (REQ-007/030, contratto §index_all):
      - Backfill incrementale: itera le sessioni dall'archivio via `archive.list_sessions()` (o
        equivalente), chiama `index_session` su ciascuna; aggrega i `SemanticIndexReport`.
      - Non ri-archivia nulla (REQ-029/FR-032): l'indice è derivato, il grezzo è intatto.
      - Emette `memory_semantic_index` metrics-only: `embedded`, `skipped`, `errors`, `provider`,
        `latency_ms` (REQ-026/FR-029). Emissione non-fatale.
- [ ] **Collezione isolata** (REQ-017/FR-020, data-model §Namespacing):
      - Il nome collezione è `collection_name(memory_settings, embedder)` dove `memory_settings`
        ha `corpus` impostato al namespace memoria (es. prefisso `memory__`), **distinto** dal
        corpus del progetto. Garantisce che contenuto memoria e corpus non si mescolino mai.
      - Provider diverso → `embedder.name` diverso → nome collezione diverso → rebuild implicito
        (REQ-032/FR-011, DA-SS-4). Nessun caso di ri-embed in-place.
- [ ] **Privacy on-machine** (REQ-018/019, FR-021/022, RNF-1):
      - Provider locale di default (da `SERTOR_EMBED_PROVIDER`, REQ-018): nessun new selettore.
      - Con provider cloud: il percorso è il medesimo (embedding via `build_embedder` esistente);
        il warning di invio off-machine è documentato (REQ-020/FR-023) in quickstart/doc.
- [ ] **Host-agnostico** (REQ-024/025/FR-027/028): nessun branch sull'assistente; opera su
      `memory.sqlite` indipendentemente dalla provenienza.
- [ ] **Nessun import di SDK esterni**: dipende solo dalle porte `EmbeddingProvider`/`VectorStore`
      + entità/errori esistenti (Principio I); le scelte concrete sono in `composition.py`.
- [ ] Aggiungi test unitari in `tests/unit/test_memory_semantic.py` (NUOVO, offline con mock):
      - `search` su indice vuoto → `hits=()` + warning (REQ-021, US6-AC1).
      - `search` con risultati → mapping corretto `SemanticMemoryHit` (6 campi, REQ-010, US1-AC2).
      - `search` con filtro `since`/`until` → solo hit nel range (REQ-012, US1-AC1).
      - `search` query vuota → `hits=()` (contratto §search edge case).
      - `index_session` su sessione nuova → `embedded=N`, `skipped=0`, `upsert` chiamato (REQ-006).
      - `index_session` su sessione già indicizzata → `embedded=0`, `skipped=N`, **zero embed**
        (REQ-030/NFR-009, US3-AC2/SC-006).
      - `index_session` due volte stessa sessione → niente duplicati (idempotenza, REQ-006, US3-AC3).
      - `index_all` su archivio misto (alcune sessioni indicizzate, altre no) → embedda solo le nuove
        (incrementalità tra esecuzioni, REQ-031, US3-AC4/SC-006).
      - Provider giù durante `search` → stato vuoto/errore azionabile, nessun crash (REQ-022, US6-AC2).
      - Embedding fallito su singolo turno → skippato, report con `errors=1`, resto servito
        (REQ-023, US6-AC3).
      - Tutti i test: `not cloud`, embedder mock (RNF-5/NFR-007), zero rete.

---

## Fase 2 — Storia 1: Ricerca semantica (P1, Must) (4 task)

> Prerequisiti: TASK-F01 (servizio). Questa fase espone la ricerca semantica tramite CLI.
> TASK-US1-01 (composition) è bloccante per TASK-US1-02/03. TASK-US1-02 e TASK-US1-03 [P].

### TASK-US1-01 — `composition.py`: `build_memory_semantic_index()` gated + iniezione in `build_memory_archiver`
**File**: `src/sertor_core/composition.py`
→ dipende da: TASK-F01, TASK-S01
- [ ] Aggiungi la factory `build_memory_semantic_index(settings: Settings) -> MemorySemanticIndex | None`:
      - Gate: ritorna `None` se `NOT (settings.memory_enabled AND settings.memory_semantic_enabled)`.
      - Se gate off: **non** costruisce embedder né store, nessun import del path semantico
        (additività, RNF-005/NFR-005/SC-011).
      - Se gate acceso: costruisce `embedder = build_embedder(settings, allow_download=False)`
        (solo query — il download GloVe è consentito solo sul path d'indicizzazione), costruisce
        `store = build_store(settings)`, deriva `collection` via `collection_name` con namespace
        memoria, ritorna `MemorySemanticIndex(embedder, store, collection, settings)`.
      - Per l'indicizzazione (`index_session`/`index_all`): usa `build_embedder(settings,
        allow_download=True)` — coerente col pattern `build_indexer` del corpus principale.
      - Se `memory_enabled=False` ma `memory_semantic_enabled=True`: ritorna `None` + warning
        che segnala la dipendenza da `SERTOR_MEMORY` (REQ-002/FR-002, data-model §Errore).
- [ ] Aggiorna la firma di `build_memory_archiver`:
      ```python
      def build_memory_archiver(
          settings: Settings,
          semantic_index: MemorySemanticIndex | None = None,
      ) -> MemoryArchiveService | None:
      ```
      Passa `semantic_index` a `MemoryArchiveService.__init__` (aggancio auto-index, REQ-004).
      Quando `semantic_index=None` (leva spenta o non passato): comportamento FEAT-001 identico
      (REQ-005/FR-005/RNF-005).
- [ ] L'iniezione avviene **solo in composition**: composition è l'unico luogo che conosce gli
      adapter concreti (Principio I). `MemoryArchiveService` non importa `build_*`.
- [ ] Verifica: con `SERTOR_MEMORY=false` → `build_memory_semantic_index` ritorna `None` (gate);
      con `SERTOR_MEMORY=true, SERTOR_MEMORY_SEMANTIC=false` → `None` (gate); con entrambi true
      → ritorna `MemorySemanticIndex`. Testabile in `tests/unit/test_composition_memory.py` con
      Settings mock senza adapter reali.

### TASK-US1-02 [P] — `cli/__main__.py`: flag `--semantic` su `memory search` + handler
**File**: `src/sertor_core/cli/__main__.py`
→ dipende da: TASK-US1-01
- [ ] Aggiungi il flag booleano `--semantic` al subparser `memory search` (DA-SS-3):
      ```
      parser_memory_search.add_argument("--semantic", action="store_true", default=False,
                                         help="Ricerca semantica (richiede SERTOR_MEMORY_SEMANTIC=true)")
      ```
      Lascia `--since`, `--until`, `-k` (o `--limit`) **invariati**: riusati per la semantica
      (filtro temporale REQ-012 + limit REQ-011).
- [ ] Routing nell'handler `_cmd_memory_search`:
      - `--semantic` assente → percorso full-text FEAT-002 **invariato** (REQ-013/014/FR-016/017,
        SC-004). **Non toccare** `_require_episodic_search` né il percorso FTS esistente.
      - `--semantic` presente:
        1. `semantic_index = build_memory_semantic_index(settings)` (da composition).
        2. Se `semantic_index is None` → solleva `SemanticMemoryUnavailableError` (TASK-S02) con
           messaggio azionabile che nomina `SERTOR_MEMORY_SEMANTIC=true` + `SERTOR_MEMORY=true` se
           serve + `memory index-semantic` (REQ-015/FR-018/SC-005). Exit 1 via `main()`.
        3. Se `semantic_index` valido → costruisce `SemanticMemoryQuery(text, since, until, limit)`
           → `semantic_index.search(query)` → `format_semantic_results(results, json=args.json)`.
- [ ] Consuma `SemanticMemoryResults` (da TASK-F01): nessuna logica di mapping nel CLI thin
      (Principio I/VII); tutta la logica di formattazione in `cli/output.py` (TASK-US1-03).
- [ ] Exit code: 0 = ricerca completata (anche con `hits=()`); 1 = leva spenta/indice assente
      (`SemanticMemoryUnavailableError`) (contratto §Vehicle CLI).

### TASK-US1-03 [P] — `cli/output.py`: `format_semantic_results` + `format_semantic_index_report`
**File**: `src/sertor_core/cli/output.py`
→ dipende da: TASK-F01
- [ ] Aggiungi la funzione pura `format_semantic_results(results: SemanticMemoryResults,
      json: bool = False) -> str`:
      - Output umano: per ogni `SemanticMemoryHit` riporta `session_key`, `turn_index`,
        `captured_at` (ISO 8601), `role`, `snippet`, `score` (REQ-010). Nessun risultato →
        riga onesta `(nessun risultato)`, non silenzio.
      - Output JSON (`--json`): lista di dict con gli stessi 6 campi, wrapped in `{"hits": [...]}`
        o simile (contratto §Vehicle CLI).
      - Funzione **pura** (zero I/O, zero side-effect): testabile senza adapter (RNF-5).
- [ ] Aggiungi la funzione pura `format_semantic_index_report(report: SemanticIndexReport,
      json: bool = False) -> str`:
      - Output umano: `embedded`, `skipped`, `errors` come conteggi leggibili.
      - Output JSON: `{"embedded": N, "skipped": N, "errors": N}`.
      - Funzione pura; zero segreti/testo di transcript.
- [ ] Gemelle delle funzioni `format_archive_report`/`format_memory_results` già presenti
      (`services/memory_archive.py`/`output.py`): seguire la stessa convenzione stilistica.

### TASK-US1-04 — Test CLI: routing `--semantic`, gate, resa (unit)
**File**: `tests/unit/test_cli_memory_semantic.py` (NUOVO) o estensione di `test_cli_memory*.py`
→ dipende da: TASK-US1-01, TASK-US1-02, TASK-US1-03
- [ ] `memory search "query"` (senza `--semantic`) → percorso full-text invariato; `SemanticMemoryIndex`
      **non** costruito/chiamato (SC-004/REQ-013, US4-AC1).
- [ ] `memory search "query" --semantic` con leva accesa e index mock → exit 0, output umano
      contiene snippet + score; `--json` → JSON con chiave `hits` (o simile) e 6 campi per hit
      (REQ-010, US1-AC2/AC3).
- [ ] `memory search "query" --semantic` con `SERTOR_MEMORY_SEMANTIC=false` → exit 1,
      messaggio contiene `SERTOR_MEMORY_SEMANTIC` (REQ-015, US4-AC3/SC-005).
- [ ] `memory search "query" --semantic` con `SERTOR_MEMORY=false` → exit 1, messaggio contiene
      `SERTOR_MEMORY` (REQ-002/FR-002, US2-AC2).
- [ ] `memory search "query" --semantic --since T1 --until T2` → filtro temporale passato
      correttamente alla query (REQ-012, US1-AC1).
- [ ] `memory search "query" --semantic` con `hits=()` → exit 0, output `(nessun risultato)` onesto
      (REQ-021, contratto §search edge case).
- [ ] `format_semantic_results` con `hits` mock → output umano e JSON corretti (unit puro).
- [ ] `format_semantic_index_report` → output umano e JSON corretti (unit puro).
- [ ] Tutti `not cloud`, mock core (RNF-5).

---

## Fase 3 — Storia 2: Opt-in di privacy a strati (P1, Must) (2 task)

> Prerequisiti: TASK-US1-01 (factory gated). Verifica il gate a due strati (REQ-001/002/003).
> TASK-US2-01 e TASK-US2-02 [P] dopo il prerequisito.

### TASK-US2-01 [P] — Test gate a due strati: cattura off / semantica off
**File**: `tests/unit/test_composition_memory.py` (NUOVO o estensione)
→ dipende da: TASK-US1-01
- [ ] `SERTOR_MEMORY=false`, `SERTOR_MEMORY_SEMANTIC=true` → `build_memory_semantic_index` ritorna
      `None`; nessun embedder né store costruiti; nessun embedding eseguito (REQ-001/002, US2-AC1/2).
- [ ] `SERTOR_MEMORY=true`, `SERTOR_MEMORY_SEMANTIC=false` → `build_memory_semantic_index` ritorna
      `None`; `build_memory_archiver` riceve `semantic_index=None` → comportamento FEAT-001
      identico (REQ-005/FR-005/RNF-005, US2-AC1).
- [ ] `SERTOR_MEMORY=true`, `SERTOR_MEMORY_SEMANTIC=true` → `build_memory_semantic_index`
      ritorna un'istanza `MemorySemanticIndex` (gate acceso, US2-AC3).
- [ ] Con la semantica off: dopo aver simulato l'archiviazione di sessioni, nessun file/indice
      vettoriale della memoria è stato creato (SC-002/REQ-001); il test verifica che lo store
      non sia stato chiamato con `upsert` (mock capture).
- [ ] Tutti `not cloud`, Settings mock, nessun adapter reale.

### TASK-US2-02 [P] — Verifica manopola distinta: default off, naming separato
**File**: `tests/unit/test_settings.py` (estensione) o `test_composition_memory.py`
→ dipende da: TASK-S01
- [ ] `Settings()` default → `memory_semantic_enabled=False` (default off, REQ-003/FR-003).
- [ ] `Settings()` con `SERTOR_MEMORY=true` e senza `SERTOR_MEMORY_SEMANTIC` →
      `memory_semantic_enabled=False` (accendere la cattura non accende embedding, US2-AC3/SC-002).
- [ ] `SERTOR_MEMORY_SEMANTIC_LIMIT` non impostato → `memory_semantic_limit=20` (default finito
      documentato, REQ-011).
- [ ] I due campi sono **distinti** in `Settings`: verifica che non ci sia aliasing o derivazione
      (non c'è un `memory_semantic_enabled = memory_enabled and ...` nel modello).

---

## Fase 4 — Storia 3: Indicizzazione automatica e incrementale (P1, Must) (2 task)

> Prerequisiti: TASK-US1-01 (composition con iniezione). Aggancia l'auto-index al percorso
> di archiviazione e verifica incrementalità. TASK-US3-01 e TASK-US3-02 [P].

### TASK-US3-01 — `services/memory_archive.py`: aggancio auto-index in `archive_all`
**File**: `src/sertor_core/services/memory_archive.py`
→ dipende da: TASK-F01, TASK-US1-01
- [ ] Aggiorna `MemoryArchiveService.__init__` per ricevere un parametro opzionale:
      ```python
      def __init__(self, ..., semantic_index: MemorySemanticIndex | None = None): ...
      ```
      A leva spenta (`semantic_index=None`): comportamento FEAT-001 identico, zero side-effect
      (REQ-005/FR-005/RNF-005). Nessuna modifica al percorso esistente.
- [ ] Aggiorna `archive_all()` per chiamare `index_session` su ogni sessione **appena archiviata**,
      in un `try/except` **non-fatale** (REQ-008/FR-010):
      ```python
      if self._semantic_index is not None:
          try:
              self._semantic_index.index_session(session)
          except Exception as exc:
              log_event("warning", "memory_semantic_index_failed",
                        session_key=session.session_key, error=str(exc))
              # grezzo intatto, run continua
      ```
      Il grezzo della sessione resta intatto; è loggato un warning; il run di cattura continua
      (REQ-008/FR-010, US6-AC4/SC-010).
- [ ] Solo le sessioni **appena archiviate** (non già presenti, per idempotenza) scatenano
      `index_session`: coerente con `archive_all` che usa `INSERT OR IGNORE`.
- [ ] Verifica: `memory archive` con semantica opt-in → sessione archiviata **e** indicizzata
      → recuperabile per significato senza passo manuale (REQ-004/FR-004, US3-AC1/SC-007).

### TASK-US3-02 [P] — Test incrementalità e auto-index
**File**: `tests/unit/test_memory_archive_semantic.py` (NUOVO o estensione di `test_memory_archive.py`)
→ dipende da: TASK-US3-01
- [ ] Archivio una sessione con `semantic_index` mock iniettato → `index_session` chiamato una
      volta (auto-index, REQ-004, US3-AC1).
- [ ] Senza `semantic_index` (None iniettato) → `archive_all` si comporta come FEAT-001: nessuna
      chiamata all'embedder (REQ-005, US2-AC1/RNF-005).
- [ ] Embedding fallisce a fine archiviazione → la sessione è nel grezzo, warning loggato, run
      non abortito, `archive_all` ritorna normalmente (REQ-008, US6-AC4).
- [ ] `index_session` chiamata due volte sulla stessa sessione (via `index_all` dopo auto-index) →
      seconda chiamata: `embedded=0`, `skipped=N`, zero chiamate embedder (incrementalità tra
      run, REQ-030/031, US3-AC2/AC4/SC-006).
- [ ] Tutti `not cloud`, mock embedder/store/archivio, nessun file su disco (RNF-5).

---

## Fase 5 — Storia 4: Modo separato, no fallback silenzioso (P1, Must) (2 task)

> Prerequisiti: TASK-US1-02 (CLI routing). Verifica che full-text resti il default e che il
> modo semantico senza opt-in non faccia fallback silenzioso.
> TASK-US4-01 e TASK-US4-02 [P].

### TASK-US4-01 [P] — Verifica full-text default invariata
**File**: test esistente `test_cli_memory*.py` (estensione)
→ dipende da: TASK-US1-02
- [ ] `memory search "query"` (senza `--semantic`) con semantica opt-in (entrambe le leve accese) →
      percorso FTS invariato; `MemorySemanticIndex.search` **non** chiamato (REQ-013/014/FR-016/017,
      US4-AC1). Verifica con mock che `_require_episodic_search` è l'unico path attivato.
- [ ] `memory search "query"` (senza `--semantic`) con semantica **off** → stessa cosa: full-text,
      nessun percorso semantico (SC-004).
- [ ] Abilitare `SERTOR_MEMORY_SEMANTIC=true` non modifica il comportamento di `memory search`
      senza `--semantic` (REQ-013/FR-016: la semantica è additiva, non sostituisce il default).

### TASK-US4-02 [P] — Verifica no-fallback e messaggio azionabile
**File**: test esistente `test_cli_memory_semantic.py` (estensione di TASK-US1-04)
→ dipende da: TASK-US1-02, TASK-S02
- [ ] `memory search "query" --semantic` con `SERTOR_MEMORY_SEMANTIC=false` → exit 1, messaggio
      contiene `SERTOR_MEMORY_SEMANTIC` **e** `memory index-semantic` (REQ-015/FR-018/SC-005,
      US4-AC3). **Nessun risultato full-text** nell'output (no fallback silenzioso).
- [ ] `memory search "query" --semantic` con indice semantico assente (leva accesa ma `index_all`
      mai eseguito) → exit 1 con `SemanticMemoryUnavailableError` (o `hits=()` + warning onesto
      a seconda del punto di rilevamento — vedi contratto §search: il core ritorna vuoto + warning,
      il CLI solleva l'errore azionabile se vuole distinguere). Messaggio nomina `memory index-semantic`.
- [ ] Il messaggio di errore **non** contiene risultati full-text mascherati da risultati semantici
      (invariante assoluta SC-005).

---

## Fase 6 — Storia 5: On-machine col provider locale (P1, Must) (1 task)

> Prerequisiti: TASK-F01 (servizio). Verifica che con provider locale il percorso sia offline.
> Questo task è [P] rispetto a TASK-US4-01/02.

### TASK-US5-01 [P] — Verifica offline con provider locale (mock/unit)
**File**: `tests/unit/test_memory_semantic.py` (estensione di TASK-F01)
→ dipende da: TASK-F01, TASK-S01
- [ ] Con embedder mock (locale, nessuna rete) + store mock: `index_session` e `search` completano
      senza effettuare chiamate HTTP (RNF-1/NFR-001, US5-AC1/SC-003). Verifica via mock capture
      che `embed()` è chiamato sul mock e non viene creata nessuna connessione di rete.
- [ ] Il provider locale (`glove`/`hash`) è il default da `SERTOR_EMBED_PROVIDER` (REQ-018/FR-021):
      nessun selettore nuovo per la memoria. Verifica che `build_memory_semantic_index` non
      imponga un provider fisso, ma lo legga da `Settings.embed_provider` (esistente, FEAT-011).
- [ ] Con provider cloud configurato (mock che simula Azure embedder): il percorso funziona;
      l'implicazione off-machine (REQ-020/FR-023) è documentata in `quickstart.md` o in un
      commento/warning nel codice. Test di verifica documentale (se non c'è un quickstart, nota
      nel task di Polish). Questo non è un test di rete: verifica solo che il warning/doc esista.
- [ ] Tutti `not cloud`, nessun traffico reale; il test di isolamento rete è sulla coerenza del
      mock (nessuna chiamata HTTP fuori dal mock), non su un monitor di rete live.

---

## Fase 7 — Storia 6: Degradazione non-fatale e backfill (P2, Should) (3 task)

> Prerequisiti: TASK-F01 (servizio), TASK-US1-01/02/03 (CLI). Storie P2 costruite sopra le P1.
> TASK-US6-01 e TASK-US6-02 [P]; TASK-US6-03 dipende da TASK-US6-01.

### TASK-US6-01 [P] — `cli/__main__.py`: nuovo subcommand `memory index-semantic` (backfill)
**File**: `src/sertor_core/cli/__main__.py`
→ dipende da: TASK-US1-01, TASK-US1-03
- [ ] Aggiungi il subcommand `memory index-semantic [--json]` (contratto §Vehicle CLI/backfill):
      ```
      parser_memory_index_semantic = memory_subparsers.add_parser("index-semantic",
          help="Indicizza semanticamente le sessioni di backlog (backfill incrementale)")
      parser_memory_index_semantic.add_argument("--json", action="store_true")
      ```
- [ ] Handler `_cmd_memory_index_semantic`:
      1. `semantic_index = build_memory_semantic_index(settings)`.
      2. Se `None` → `SemanticMemoryUnavailableError` (REQ-007/FR-009, exit 1).
      3. `archive = build_memory_archiver(settings)` (per accedere alle sessioni).
      4. `report = semantic_index.index_all(archive._archive)` (o via l'archivio iniettato).
      5. `format_semantic_index_report(report, json=args.json)` → stdout.
- [ ] Idempotente per costruzione: una seconda esecuzione senza nuove sessioni → `embedded=0`,
      `skipped=N` (incrementalità, REQ-007/030/FR-009, US6-AC5/SC-006).
- [ ] Exit 0 se l'operazione si completa (anche parzialmente con `errors>0`); exit 1 solo se
      la leva è spenta (`SemanticMemoryUnavailableError`).

### TASK-US6-02 [P] — Test degradazione non-fatale (estensione test_memory_semantic.py)
**File**: `tests/unit/test_memory_semantic.py` (estensione di TASK-F01)
→ dipende da: TASK-F01
- [ ] Indice semantico assente alla query (store mock con collezione vuota) → `hits=()` + warning
      (REQ-021/FR-024, US6-AC1). Nessuna eccezione propagata al chiamante.
- [ ] Provider giù a query-time (embedder mock che solleva eccezione) → stato vuoto/errore
      azionabile; il chiamante non va in crash (REQ-022/FR-025, US6-AC2).
- [ ] Unità con embedding invalido nello store (payload mancante/malformato) → quella unità
      saltata con warning; le unità valide servite (REQ-023/FR-026, US6-AC3).
- [ ] Tutti `not cloud`, nessuna rete.

### TASK-US6-03 — Test CLI `memory index-semantic`: backfill e idempotenza
**File**: `tests/unit/test_cli_memory_semantic.py` (estensione)
→ dipende da: TASK-US6-01, TASK-US6-02
- [ ] `memory index-semantic` con semantica opt-in e archivio mock → `index_all` chiamato; output
      contiene `embedded`, `skipped`, `errors`; exit 0 (US6-AC5/REQ-007).
- [ ] `memory index-semantic --json` → JSON con i tre campi (contratto §backfill).
- [ ] `memory index-semantic` con leva spenta → exit 1, messaggio nomina
      `SERTOR_MEMORY_SEMANTIC=true` (contratto §backfill gate).
- [ ] `memory index-semantic` senza nuove sessioni → `embedded=0`, exit 0 (idempotenza, SC-006).
- [ ] Tutti `not cloud`, mock archivio e index.

---

## Fase 8 — Polish e cross-cutting (3 task)

> Prerequisiti: tutte le Fasi 0–7. TASK-P01 e TASK-P02 [P]; TASK-P03 dipende da entrambi.

### TASK-P01 [P] — Suite non-cloud verde + lint ruff pulito
→ dipende da: tutti i task delle Fasi 0–7
- [ ] Esegui `uv run pytest -m "not cloud" tests/unit/` → verde (inclusi i test pre-esistenti
      di `memory_archive`, `episodic_search`, `cli_memory` che devono restare invariati — RNF-5).
- [ ] Esegui `uv run pytest -m "not cloud" tests/` → verde (suite completa escludendo `@cloud`).
- [ ] Esegui `uv run ruff check .` → zero errori sui file nuovi/modificati
      (regole E,F,I,UP,B; line-length 100). Correggi eventuali errori prima del merge.
- [ ] Verifica che i test esistenti FEAT-001 (`test_memory_archive.py`), FEAT-002
      (`test_episodic_search.py`), CLI memoria (`test_cli_memory*.py`) siano **invariati**
      (additività/non-regressione SC-011/RNF-2).

### TASK-P02 [P] — Verifica additività residua: porte/engine/adapter/FTS invariati
→ dipende da: tutti i task delle Fasi 0–7
- [ ] Verifica che **nessuno** dei seguenti file sia stato modificato (RNF-005/SC-011):
      - Porte: `src/sertor_core/domain/ports.py` (EmbeddingProvider, VectorStore, …)
      - Engine: `src/sertor_core/engines/` (hybrid, baseline, evaluation — tutti)
      - Adapter: `src/sertor_core/adapters/` (tutti)
      - `services/episodic_search.py` (FTS full-text FEAT-002 invariata)
      - `services/memory_archive.py` salvo il solo aggancio auto-index (TASK-US3-01)
- [ ] Verifica comportamenti CLI invariati (spot check):
      - `uv run sertor-rag memory search "test"` (senza `--semantic`) → full-text invariata.
      - `uv run sertor-rag memory archive` senza `SERTOR_MEMORY_SEMANTIC` → comportamento FEAT-001.
      - `uv run sertor-rag eval run` (IR, senza `--fused`) → invariato.
      - `uv run sertor-rag search "test" --type both` → invariato (FusedResults, FEAT-003).
- [ ] Verifica che con `SERTOR_MEMORY_SEMANTIC=false` (default): nessun import del percorso
      semantico, nessun file/indice nuovo creato, costo identico a prima (NFR-005/SC-011).

### TASK-P03 — Osservabilità: verifica eventi metrics-only
→ dipende da: TASK-P01, TASK-P02
- [ ] Esegui (o verifica nei test) che `memory_semantic_index` emesso da `index_all`:
      - Contiene: `units`/`embedded`, `skipped`, `errors`, `provider`, `latency_ms`.
      - **Non** contiene: testo di transcript, `query`, snippet, `session_key` singoli
        (metrics-only, REQ-026/FR-029/SC-012/RNF-8).
- [ ] Verifica che `memory_semantic_search` emesso da `search`:
      - Contiene: `query_hash` (sha256[:16]), `query_len`, `since`, `until`, `limit`,
        `results`, `latency_ms`.
      - **Non** contiene: `query` in chiaro, snippet, session_key (REQ-027/FR-030/SC-012).
- [ ] Verifica che un guasto nell'emissione dell'evento non abortisca il risultato (REQ-028/FR-031):
      test con `log_event` mockato che solleva eccezione → `search`/`index_session` completano
      comunque e ritornano il risultato corretto (non-fatale).
- [ ] Verifica coerenza con l'archivio (REQ-029/FR-032): cancellare/ricostruire l'indice non
      altera `memory.sqlite`; `index_all` su un archivio noto produce lo stesso report
      (equivalenza, non bit-identità — l'ordine degli upsert può variare).

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01 (manopole Settings) ─────────────────────────────────────────────────┐
TASK-S02 (SemanticMemoryUnavailableError) [P] ────────────────────────────────┤
                                                                               │
         └──────────────────────────────────────────────────────────────────── TASK-F01 (servizio + entità + test unit)
                                                                               │
         TASK-US1-01 (composition: factory gated + iniezione) ← F01, S01     │
                  │                                                             │
                  ├── TASK-US1-02 [P] (CLI search --semantic) ← US1-01        │
                  │         └── TASK-US1-04 (test CLI search) ← US1-01..03    │
                  ├── TASK-US1-03 [P] (output.py: format_semantic_*) ← F01    │
                  │                                                             │
                  ├── TASK-US2-01 [P] (test gate due strati) ← US1-01         │
                  ├── TASK-US2-02 [P] (test manopola distinta) ← S01          │
                  │                                                             │
                  ├── TASK-US3-01 (memory_archive.py: auto-index) ← F01, US1-01
                  │         └── TASK-US3-02 [P] (test auto-index + increm.) ← US3-01
                  │                                                             │
                  ├── TASK-US4-01 [P] (test FTS default invariata) ← US1-02   │
                  ├── TASK-US4-02 [P] (test no-fallback) ← US1-02, S02        │
                  │                                                             │
                  └── TASK-US5-01 [P] (test offline provider locale) ← F01, S01
                                                                               │
         TASK-US6-01 [P] (CLI memory index-semantic) ← US1-01, US1-03         │
         TASK-US6-02 [P] (test degradazione) ← F01                            │
         TASK-US6-03 (test CLI backfill) ← US6-01, US6-02                     │
                                                                               │
         TASK-P01 [P] (suite verde + lint) ← tutti i task                      │
         TASK-P02 [P] (additività residua) ← tutti i task                      │
         TASK-P03 (osservabilità metrics-only) ← P01, P02                      │
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (ricerca semantica funzionante) | `search` su indice mock popola `SemanticMemoryResults` con ≥1 hit che riporta i 6 campi REQ-010; filtro temporale applicato; query NL embeddata via `embedder.embed`; full-text non coinvolta. | TASK-F01, TASK-US1-01..04 | MECCANICO |
| **US2** (opt-in a strati) | Con `SERTOR_MEMORY=false` o `SERTOR_MEMORY_SEMANTIC=false`: factory ritorna `None`, nessun embedder costruito, nessun `upsert` sullo store, `archive_all` = comportamento FEAT-001. | TASK-S01, TASK-US1-01, TASK-US2-01..02 | MECCANICO |
| **US3** (indicizzazione automatica e incrementale) | `archive_all` con index iniettato → `index_session` chiamato; seconda indicizzazione stessa sessione → `embedded=0`, zero chiamate embedder; `index_all` su archivio misto → embedda solo le unità nuove. | TASK-F01, TASK-US3-01..02 | MECCANICO |
| **US4** (modo separato, no fallback) | `memory search` senza `--semantic` → full-text invariata; con `--semantic` e leva spenta → exit 1 con `SemanticMemoryUnavailableError` + messaggio azionabile; nessun risultato FTS nell'output dell'errore. | TASK-US1-02, TASK-US4-01..02, TASK-S02 | MECCANICO |
| **US5** (on-machine col locale) | Con embedder mock: `index_session` e `search` completano senza chiamate HTTP; `build_memory_semantic_index` legge provider da `Settings.embed_provider` senza imporne uno fisso. | TASK-F01, TASK-US5-01 | MECCANICO |
| **US6** (degradazione + backfill, P2) | Indice assente → `hits=()` + warning; provider giù → errore azionabile, nessun crash; embedding fallisce a fine archiviazione → grezzo intatto + warning; `memory index-semantic` idempotente; backfill embedda solo le unità nuove. | TASK-F01, TASK-US6-01..03 | MECCANICO |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 (senza prerequisiti — tutto parallelizzabile):**
- TASK-S01 (manopole `Settings`)
- TASK-S02 (errore di dominio)

**Sprint 2 (dopo Sprint 1 — blocco fondazionale):**
- TASK-F01 (servizio `MemorySemanticIndex` + entità + test unitari): bloccante per tutto

**Sprint 3 (dopo Sprint 2 — P1 Must, parallelizzabile in blocchi):**
- TASK-US1-01 (composition factory gated)
- TASK-US1-03 [P] (output.py — dipende solo da F01, non da US1-01)
- TASK-US2-02 [P] (test manopola distinta — dipende solo da S01)
- TASK-US5-01 [P] (test offline — dipende solo da F01+S01)

**Sprint 4 (dopo Sprint 3 — consumi della factory):**
- TASK-US1-02 (CLI search --semantic) ← US1-01
- TASK-US2-01 [P] (test gate) ← US1-01
- TASK-US3-01 (memory_archive auto-index) ← F01+US1-01

**Sprint 5 (dopo Sprint 4 — test delle storie P1):**
- TASK-US1-04 (test CLI search) ← US1-01..03
- TASK-US3-02 [P] (test auto-index+increm.) ← US3-01
- TASK-US4-01 [P] (test FTS default invariata) ← US1-02
- TASK-US4-02 [P] (test no-fallback) ← US1-02+S02

**Sprint 6 (storie P2 Should):**
- TASK-US6-01 [P] (CLI index-semantic)
- TASK-US6-02 [P] (test degradazione)

**Sprint 7 (dopo Sprint 6):**
- TASK-US6-03 (test CLI backfill)

**Sprint finale (suite verde — Polish):**
- TASK-P01 [P] (suite verde + lint)
- TASK-P02 [P] (additività residua)
- TASK-P03 (osservabilità metrics-only)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per FEAT-004 — ricerca semantica opzionale sull'archivio

Fase SpecKit "tasks" completata per specs/072-ricerca-semantica-memoria.
22 task in 9 fasi:
  Fase 0 Setup              : 2 task  (TASK-S01/S02 — manopole + errore dominio)
  Fase 1 Fondazionale       : 1 task  (TASK-F01 — servizio MemorySemanticIndex + entità)
  Fase 2 Storia 1 (P1 Must) : 4 task  (TASK-US1-01..04 — composition + CLI search + output)
  Fase 3 Storia 2 (P1 Must) : 2 task  (TASK-US2-01..02 — gate privacy a due strati)
  Fase 4 Storia 3 (P1 Must) : 2 task  (TASK-US3-01..02 — auto-index incrementale)
  Fase 5 Storia 4 (P1 Must) : 2 task  (TASK-US4-01..02 — modo separato, no fallback)
  Fase 6 Storia 5 (P1 Must) : 1 task  (TASK-US5-01 — on-machine, offline)
  Fase 7 Storia 6 (P2 Should): 3 task (TASK-US6-01..03 — backfill + degradazione)
  Fase 8 Polish              : 3 task  (TASK-P01..P03 — suite verde, lint, osservabilità)

Tutti i task MECCANICI (22): eseguibili offline con mock, nessun indice attivo richiesto.
Copertura: REQ-001..032, NFR-001..009, SC-001..013, US1..6.
Gate privacy a due strati (REQ-001/002/003): task dedicati US2-01/02.
Incrementalità O(nuovo): verificata in TASK-F01 + TASK-US3-02 (zero embed su sessioni già indicizzate).
Additività a leva spenta: verificata in TASK-P02 (porte/engine/FTS/adapter invariati).

Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/072-ricerca-semantica-memoria/tasks.md` (questo file, nuovo)
