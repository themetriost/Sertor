# Research — Ricerca episodica full-text locale (FEAT-002, feature 033)

**Branch**: `033-ricerca-episodica` · **Data**: 2026-06-14 · **Fase**: 0 (Outline & Research)

Risolve gli ignoti del Technical Context e le decisioni di design `DA-FT-*` poste dalla spec
(`spec.md` §Assumptions A-005..A-009). Ogni decisione è ancorata al codice reale del core (citato
`path:lineno`) interrogato via RAG di dogfooding + lettura diretta. Vincolo trasversale: **privacy
by design** (full-text locale, zero cloud nel percorso query) e **additività** (FEAT-001 e core
invariati).

> **Nota MCP**: il tool `mcp__sertor-rag__find_symbol("MemoryArchive")` ha restituito lista vuota
> (il simbolo non è nel code-graph del corpus dogfood). NON degradato in silenzio: `search_code` lo
> ha localizzato correttamente (`src/sertor_core/adapters/memory/archive.py`) e ho letto i file reali
> con `Read`. Nessun altro errore MCP.

---

## DA-FT-001 — Motore full-text (decisione cardine)

**Decisione: SQLite FTS5 nativo**, tabella virtuale `turns_fts` che indicizza `turns.content`,
**external-content** (`content='turns'`) per non duplicare il testo, con ranking `bm25()` e snippet
`snippet()` nativi. L'indice FTS vive nello **stesso file** `<index_dir>/memory.sqlite` dell'archivio
di FEAT-001.

**Verifica di disponibilità (eseguita live, 2026-06-14)** — gate posto dalla spec A-005 e dal
prompt:

- Nel venv del progetto (`uv run python`, Python 3.12.13, SQLite 3.50.4): `CREATE VIRTUAL TABLE …
  USING fts5(content)` → **AVAILABLE**; `bm25()` e `snippet(t,0,'[',']','…',8)` funzionanti
  (`'decidiamo [Azure] per il backend'`, score `-1e-06`).
- Misura sull'archivio dogfood reale (`.index-sertor/memory.sqlite`, **36 sessioni / 5062 turni /
  ~4 MB** di contenuto): build FTS5 dell'intero archivio in **~38 ms**, query `'Azure'` (355 match)
  in **<0.1 ms**.

**Razionale**:

- **Zero dipendenze, stdlib-only** (Principio III): FTS5 è una funzionalità di compilazione del
  modulo `sqlite3` della stdlib. L'archivio è **già** SQLite (`MemoryArchive`,
  `adapters/memory/archive.py:24`), quindi la ricerca vive accanto ai dati senza aprire un secondo
  store né un secondo file.
- **Ranking + snippet nativi**: `bm25()` dà la pertinenza lessicale (FR-008) e `snippet()` dà lo
  snippet di contesto evidenziato (FR-002/FR-011) **senza** codice di tokenizzazione/scoring nostro.
- **On-machine, privacy by design** (FR-003/SC-004): è una query SQL locale, nessun traffico di
  rete possibile.
- **Filtro temporale efficiente** (FR-005): un JOIN su `sessions.captured_at` riusa l'indice già
  presente; lo stesso pattern di `SqliteObservabilityStore.query_events(operation, since, until)`
  (`observability/store.py:57`) è il precedente diretto di "query SQLite per finestra temporale".

**Fallback documentato se FTS5 assente** (A-005, robustezza host-agnostica): se il `sqlite3` di un
host esterno è compilato **senza** FTS5 (raro ma possibile su build minimali), `CREATE VIRTUAL TABLE
… USING fts5` solleva `sqlite3.OperationalError`. La ricerca tratta questo come **degradazione
non-fatale**: log `episodic_search_unavailable` (reason) + **stato vuoto** (coerente con FR-014,
"indice assente → stato vuoto con avviso"). La disponibilità è probata una volta alla costruzione
dell'indice; non si ripiega su una scansione `LIKE` (sarebbe un secondo motore da mantenere — YAGNI,
e non darebbe ranking/snippet). Un host che vuole la ricerca episodica usa un Python con FTS5 (la
norma su CPython ufficiale, Debian/Ubuntu, macOS, Windows).

### Alternative considerate

- **(b) Riuso del BM25 esistente `Bm25LexicalIndex`** (`adapters/lexical/bm25.py:42`) — **scartata**.
  Profilo diverso e disallineato:
  - Corpus RAG con **sidecar JSON** namespaced `(corpus, provider)` e dipendenza terza `rank_bm25`
    (`bm25.py:98`), non stdlib → violerebbe il vincolo "stdlib-only nel corpo".
  - Tokenizer **snake_case-aware** pensato per query di simboli di codice (`tokenize`, `bm25.py:29`),
    non per prosa conversazionale italiana/inglese di un transcript.
  - Modella `LexicalEntry(chunk_id, text, doc_type, path)`: non ha il concetto di turno/sessione né
    il timestamp di sessione per il filtro temporale → andrebbe forzato. Riusarlo significherebbe
    duplicare il testo dei turni in un secondo artefatto JSON (FTS external-content lo evita).
  - Conclusione: condivide il nome "lessicale" ma non il dominio. Riusarlo sarebbe accoppiamento
    accidentale, non DRY reale.
- **(c) Indice dedicato custom** (inverted index in Python o nuovo store) — **scartata** per YAGNI
  (Principio III): reimplementerebbe a mano ciò che FTS5 dà nativo (tokenizzazione, BM25, snippet,
  persistenza), con più codice e più rischio, senza alcun vantaggio presente.

---

## DA-FT-005 — Aggiornamento dell'indice FTS rispetto all'archivio

**Decisione: tabella FTS5 external-content mantenuta sincrona da TRIGGER su `turns`**
(`AFTER INSERT`, e `AFTER DELETE`/`AFTER UPDATE` per completezza/contratto FTS), creata **una volta**
in modo idempotente accanto allo schema dell'archivio.

**Razionale**:

- **FR-020 / SC-008 (no divergenza indice↔archivio)**: con i trigger, ogni `INSERT` di turno fatto
  da `MemoryArchive.upsert` (`archive.py:78`) aggiorna l'indice FTS **nella stessa transazione**.
  Una sessione appena archiviata è ricercabile alla **prima** ricerca successiva, automaticamente,
  senza un passo di "rebuild" che l'host debba ricordarsi di lanciare. È il pattern standard
  external-content di FTS5.
- **VI — Idempotenza/non-distruttività**: l'archivio resta **append-only** (`INSERT OR IGNORE`,
  nessun `DELETE`/`REPLACE` — `archive.py:6-11`); i trigger seguono quel flusso. L'indice FTS è un
  artefatto **derivato e ricostruibile**: si può rigenerare in toto da `turns` (`INSERT INTO
  turns_fts(turns_fts) VALUES('rebuild')`) → non viola la non-distruttività (è un indice, non una
  sorgente).
- **Idempotenza dello schema**: la creazione di `turns_fts` + trigger è `IF NOT EXISTS` /
  best-effort, coerente con `_connect()` di `MemoryArchive` e `SqliteObservabilityStore` (entrambi
  costruiscono lo schema in modo idempotente, `archive.py:31`, `store.py:30`).

**Punto di creazione (additività)**: lo schema FTS NON viene aggiunto dentro `MemoryArchive`
(FEAT-001 deve restare **invariata**). Viene garantito (lazy, idempotente) dal **componente di
ricerca** alla sua prima connessione: se i turni esistono ma l'indice no (archivio creato da una
FEAT-001 precedente a questa feature), la prima connessione crea `turns_fts` + trigger e fa un
`'rebuild'` una tantum per popolare l'indice dai turni già presenti. Da lì in poi i trigger lo
tengono sincrono. Questo rende la feature **puramente additiva** e retrocompatibile con archivi
esistenti.

### Alternativa considerata

- **Rebuild on-demand/lazy a ogni ricerca** — **scartata**: rebuild di ~38 ms su 5k turni è
  trascurabile **oggi**, ma cresce linearmente con l'archivio e si paga **a ogni query** invece che
  **a ogni insert** (gli insert sono rari, le query frequenti in una sessione). I trigger spostano il
  costo dove è ammortizzabile e garantiscono la freschezza "by construction" invece che per
  convenzione. Resta comunque disponibile il `'rebuild'` come operazione di **recovery** (indice
  cancellato/corrotto).

---

## DA — Porta Protocol vs componente concreto

**Decisione: componente concreto + servizio di ricerca, NESSUNA porta Protocol** dedicata.

**Razionale (YAGNI, Principio III + coerenza)**:

- `MemoryArchive` (FEAT-001) è **deliberatamente senza porta** — "concrete component, NO port
  (single consumer today — D2)" (`archive.py:6`). La ricerca episodica ha lo **stesso profilo**: un
  solo consumatore oggi (la superficie d'uso è altrove, fuori ambito), un solo backend (SQLite/FTS5),
  nessuna intercambiabilità local↔cloud da rappresentare (Principio II non si applica: non c'è una
  dipendenza esterna da astrarre — è stdlib).
- Una porta `EpisodicSearchIndex` astrarrebbe **un'unica implementazione** senza un secondo
  candidato presente → sarebbe astrazione speculativa. Se in futuro FEAT-004 (semantica) volesse un
  seam comune, lo si introdurrà allora (evidenza presente, non anticipata).
- Coerenza di stile: la 7ª porta `ObservabilityStore` esiste perché ha **due** consumatori reali (il
  persistence handler scrive, FEAT-002 reports legge) — un seam con evidenza. Qui quel seam non c'è.

**Forma del wiring**: un `build_episodic_search(settings) -> EpisodicSearch | None` in
`composition.py`, accanto a `build_memory_archive` (`composition.py:345`), che ritorna `None` quando
la memoria è disattivata (`settings.memory_enabled is False`) — stesso gate privacy-by-default di
`build_memory_archiver` (`composition.py:353-364`). Senza opt-in: nessun file aperto, nessun indice
costruito.

---

## DA — Forma del risultato, ordinamento, filtro temporale

**Decisione** (entità in `data-model.md`, contratto in `contracts/episodic-search.md`):

- **Risultato per turno** (`EpisodicHit`): `session_key`, `captured_at` (timestamp sessione),
  `role`, `turn_index`, `source_path | None`, `snippet` (con marcatori di match), `score` (segnale
  di pertinenza = `-bm25()`, dove più alto = più pertinente). Granularità = **turno** con
  riferimento alla sessione padre (FR-021, A-002), mantenuta come **parametro** del comportamento,
  non cablata.
- **Ordinamento default**: pertinenza lessicale discendente, **tie-break su `captured_at`
  discendente** (più recente prima) — FR-008. Realizzato in SQL `ORDER BY bm25(turns_fts),
  s.captured_at DESC` (bm25 nativo è "più basso = più pertinente", quindi crescente).
- **Ordinamento recency-first** (opt-in, FR-009): `ORDER BY s.captured_at DESC` ignorando il segnale
  di pertinenza relativa.
- **Limite risultati** (FR-010): `SearchQuery.limit` con default finito e documentato (proposto
  **20**) via `SERTOR_EPISODIC_LIMIT`; mai l'intero archivio incondizionato.
- **Snippet** (FR-011): `snippet()` FTS5 con lunghezza-token configurabile (default proposto **12**
  token) via `SERTOR_EPISODIC_SNIPPET_TOKENS`; coerente ai bordi del testo (edge case spec §Edge).
- **Filtro temporale** (FR-005/006/007): JOIN `turns`↔`sessions` con `WHERE captured_at >= since`
  (solo inizio = "da quella data in poi") e/o `captured_at <= until` (solo fine = "fino a data
  inclusa"); `since > until` → **errore esplicito** `InvalidTimeWindowError` (Principio IV, FR-007).
  Stesso pattern di filtro temporale di `query_events(since, until)` (`store.py:57-72`).
- **Source path**: l'archivio FEAT-001 non persiste `source_path` nelle righe `sessions`
  (`archive.py:37-39` registra `session_key, project_id, captured_at, adapter_kind, metadata`); il
  `SessionRef.source_path` esiste a monte (cattura) ma non è conservato. Quindi `source_path` nel
  risultato è **opzionale e oggi `None`** (FR-002 "se disponibile", edge case "sessione priva di
  path"); resta un campo del contratto, popolabile in futuro senza cambiarlo.

---

## DA-FT-003 — Soglia di latenza (SC-006)

**Decisione: soglia indicativa < 200 ms** (p95) per la singola query su archivio di dimensione
tipica, **ben dentro** il "percettivamente immediato < 2 s" della spec.

**Razionale (ancorato a misura reale)**: sull'archivio dogfood reale (36 sessioni / 5062 turni /
~4 MB) la query FTS5 misurata è **<0.1 ms**; il build una-tantum dell'intero indice è ~38 ms (e con
i trigger non si paga in query). Anche con un archivio 10–100× più grande (centinaia di migliaia di
turni), FTS5 con indice B-tree resta nell'ordine dei millisecondi. La soglia di **200 ms p95** è
un budget conservativo che include overhead di connessione/JOIN/serializzazione e lascia margine
amplissimo. Il test di latenza (US per SC-006) verifica l'ordine di grandezza su archivio sintetico,
non un numero fragile.

---

## DA-FT-004 — Osservabilità della query (FR-017/FR-018)

**Decisione**: al completamento, `log_event(INFO, "episodic_search", …)` con: query **già redatta
dalla strategia esistente**, `since`/`until` (epoch o `None`), `order` (relevance|recency), `limit`,
`results` (conteggio), `latency_ms`. Guasto di osservabilità **non-fatale** (FR-018): il risultato
è già pronto prima di loggare; `log_event` usa il `logging` stdlib (`observability/logging.py:38`)
che non propaga errori di handler.

**Redazione della query** (FR-017): `redact()` (`logging.py:33`) maschera per **nome di campo** che
"sembra segreto", non per contenuto. La query è un valore arbitrario dell'utente → per non far
trapelare un eventuale segreto digitato, si emette il campo come `query_hash` (sha256 troncato,
stdlib `hashlib`) **e** una `query_len`, evitando il testo in chiaro nel log (coerente con la
strategia di FEAT-001 che già evita segreti nel persistito). Il **risultato** restituito al
chiamante contiene gli snippet reali (è il contenuto richiesto, on-machine); è solo il **log
strutturato** a essere redatto.

---

## Sintesi delle scelte

| Tema | Decisione | Principio guida |
|------|-----------|-----------------|
| Motore FTS | **SQLite FTS5 nativo** (external-content su `turns`), `bm25()`+`snippet()` | III (stdlib), II (local-first) |
| Disponibilità FTS5 | Probata live: AVAILABLE (3.12.13/sqlite 3.50.4); fallback = stato vuoto + warning | IV, X |
| Aggiornamento indice | **Trigger sync** su `turns` + `'rebuild'` una-tantum/recovery | VI, FR-020 |
| Seam | **Componente concreto + servizio**, nessuna porta (come `MemoryArchive`) | III (YAGNI) |
| Risultato | turno + ref sessione + snippet + score; ordine pertinenza/recency; finestra temporale | I, IV |
| Latenza | budget **< 200 ms p95** (misurato <0.1 ms su 5062 turni) | V |
| Osservabilità | evento `episodic_search`, query **hashed**, non-fatale | IX, FR-017/018 |
