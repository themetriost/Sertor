# Research — Aggancio della distillazione all'archivio episodico (FEAT-003)

Decisioni di design (Phase 0). Le DA-1..4 della spec sono già risolte come Assumptions; qui si fissano
le scelte implementative residue, ciascuna con Decision / Rationale / Alternatives. Ancoraggio al codice
reale verificato via `Read` su `src/sertor_core/` (path:lineno citati).

## D-1 — Dove vive il recupero della sessione intera (FR-001)

**Decision**: RIUSO di `MemoryArchive.get(session_key) -> ArchivedSession | None`, **senza nuovo codice
di lettura** per la sessione singola.

**Rationale**: `get` esiste già e fa esattamente ciò che serve — ricompone la sessione intera, turni
ordinati per `turn_index` (`src/sertor_core/adapters/memory/archive.py:104-139`), con degradazione
non-fatale (store ko → warning + `None`). Aggiungere un secondo percorso di lettura violerebbe DRY
(Principio III). Il `None` di `get` ha due significati che il consumatore CLI distingue: «sessione
assente» (→ not-found, exit non-zero, FR-009) e — separato — sessione esistente con `turns` vuoto
(→ stato vuoto esplicito, successo, edge case). Vedi D-4.

**Alternatives**:
- *Nuovo metodo `read_session`/servizio dedicato*: scartato — duplica `get` senza alcun valore aggiunto.

## D-2 — Forma dell'esposizione thin-consumer (FR-005): factory, non porta

**Decision**: una factory di composition `build_memory_reader(settings) -> MemoryArchive | None`, gated
su `memory_enabled` (ritorna `None` a memoria spenta). Ritorna **il `MemoryArchive` concreto**, non un
nuovo wrapper/servizio. **Nessuna nuova porta di dominio.**

**Rationale**: il pattern è già stabilito da `build_memory_archiver`/`build_episodic_search`
(`composition.py:353-383`): factory lazy, gate `memory_enabled`, `None` se off. `MemoryArchive` espone
già `get` + (dopo questa feature) `list_recent`: è esattamente l'interfaccia di lettura che il consumer
CLI vuole. Introdurre un `MemoryReader` wrapper aggiungerebbe un tipo senza secondo consumatore (YAGNI,
Principio III); introdurre una **porta** `Protocol` violerebbe FR-005/SC-007 (il numero di Protocol in
`domain/ports.py` deve restare invariato) e la regola «niente porta senza secondo consumatore» — stesso
profilo single-consumer di `MemoryArchive` e `EpisodicSearch`, che infatti NON hanno porta. La factory
`build_memory_archive` esiste già (`composition.py:345-350`) ma NON è gated; `build_memory_reader`
aggiunge il **gate privacy** che il consumer CLI richiede (coerenza con FR-008).

**Alternatives**:
- *Riusare `build_memory_archive` (non gated) e gating solo in CLI*: scartato — il gate vivrebbe solo nel
  veicolo, non in composition; le altre due factory memoria gating-ano in composition (Principio I: la
  policy di disponibilità sta nel core/composition, il comando la *consuma*). Coerenza > micro-riuso.
- *Nuovo servizio `MemoryReader`*: scartato (YAGNI, vedi sopra).
- *Nuova porta `Protocol`*: scartato (viola FR-005/SC-007).

## D-3 — `list_recent`: metodo additivo su `MemoryArchive` (FR-002)

**Decision**: `MemoryArchive.list_recent(limit: int) -> tuple[SessionSummary, ...]`, metodo additivo,
ordina per `captured_at DESC` con `LIMIT ?`, ritorna viste sintetiche (chiave, istante di cattura,
numero di turni) **senza** caricare il contenuto dei turni.

**Rationale**: coerente con i metodi di lettura esistenti dello stesso store (`get`/`exists`,
`archive.py:92-139`): single store, niente proliferazione di componenti. Il conteggio turni si ottiene
da `metadata.turn_count` (già persistito in `_metadata_json`, `archive.py:142-150`) oppure con un
`COUNT(*)` join su `turns`; si preferisce `turn_count` da metadata (zero join, sempre presente).
L'ordinamento per recency usa la colonna `captured_at` (presente su `sessions`); l'indice
`idx_sessions_project` non copre `captured_at` ma il volume (decine-centinaia di sessioni) rende il sort
trascurabile (RNF-3). Degradazione non-fatale identica a `get`: store ko → warning + tuple vuota.

**Alternatives**:
- *`COUNT(*) FROM turns GROUP BY session_key`*: scartato — `turn_count` è già in metadata, un join in più
  senza valore.
- *Servizio separato di listing*: scartato (D-2: il reader è il MemoryArchive concreto).

## D-4 — Distinzione not-found ↔ sessione vuota (FR-003/FR-009, edge case)

**Decision**: la CLI distingue tre esiti di `memory show`:
1. **`get` → `None`** = sessione assente → messaggio azionabile «sessione non trovata: <key>» su stderr
   + **exit non-zero** (sollevando un `SertorError` → exit 1 via `main()`).
2. **`get` → `ArchivedSession` con `turns` vuoti** = sessione esistente ma vuota → stato vuoto esplicito
   (es. `(empty session)` / JSON con `turns: []`) + **exit 0** (successo).
3. **`get` → `ArchivedSession` con N turni** = transcript intero (FR-001).

**Rationale**: FR-003/FR-009 e l'edge case «sessione esistente ma vuota» richiedono esplicitamente che i
due casi siano distinti e non collassino in un `None` ambiguo (Principio IV: niente null silenzioso). La
distinzione vive **nel consumer CLI** perché è semantica di presentazione/exit-code; il core resta
neutro (`get` ritorna `None` per assenza, una `ArchivedSession` vuota per sessione vuota — già il suo
comportamento naturale). Per il not-found si introduce un'eccezione di dominio dedicata
`SessionNotFoundError(session_key)` (sottoclasse di `SertorError`) — coerente con `IndexNotFoundError`/
`InvalidTimeWindowError`: messaggio azionabile, exit 1 via il `main()` esistente
(`cli/__main__.py:294-296`), nessuna duplicazione di gestione errori.

**Alternatives**:
- *`get` ritorna un sentinel diverso per i due casi*: scartato — cambierebbe il contratto di `get`
  (rischio di toccare FEAT-001/002, non additivo); la distinzione è puramente di presentazione.
- *Stampare not-found su stdout + exit 0*: scartato — viola FR-009 (exit non-zero richiesto).

## D-5 — Output: due funzioni pure in `cli/output.py` (FR-006/FR-007)

**Decision**: `format_session_transcript(session, *, json)` e `format_session_list(summaries, *, json)`,
funzioni **pure** (nessuna logica di retrieval, Principio I) nello stile di `format_memory_results`
(`cli/output.py:118-153`). `captured_at`/`ts` resi ISO-8601 UTC nella vista umana (riuso `_iso_utc`,
`output.py:113-115`) ed epoch float in JSON. Transcript: tutti i turni in ordine, ciascuno con `index`,
`role`, `ts`, `text` **completo** (nessuna troncatura, FR-001/SC-001 — niente `--full`, niente
`preview`, perché qui il punto è il testo intero per la distillazione). List: per ogni voce
`session_key`/`captured_at`/`turn_count`. Equivalenza informativa umano↔JSON (invariante SC-002 dei
`format_*` esistenti).

**Rationale**: riuso esatto del pattern già consolidato (purezza, testabilità senza terminale,
`_iso_utc`); coerenza di stile con `format_memory_results`/`format_search_results`. Il transcript NON
usa `_preview`: la spec impone testo intero (la sessione è già mirata; restringere prima è compito di
`memory search`).

**Alternatives**:
- *Riusare `format_memory_results`*: scartato — quella funzione formatta `EpisodicHit` (snippet
  troncati), semantica diversa (snippet per-turno vs transcript intero).

## D-6 — FR-011: asset installabile `claude-md-block.md` (no-op documentato)

**Decision**: FR-011 (riflettere la guida «attingi all'archivio» nell'asset installabile) si risolve
come **no-op documentato**: `packages/sertor/src/sertor_installer/assets/claude-md-block.md` **non
contiene** la procedura `distill` «from conversation» — cita `distill` solo come voce di una riga
(`claude-md-block.md:46`: «extracts durable entities surfaced by a piece of work into dedicated pages»).
La procedura dettagliata con le tre modalità (e il vincolo «never the raw transcript») vive **solo** in
`.claude/skills/wiki-author/ops/distill.md`, che NON è parte dell'asset installato.

**Rationale**: l'asset distribuito agli ospiti descrive il *rituale di step* a grana grossa, non le
procedure di dettaglio delle singole operazioni; FR-011 è *Optional feature* (EARS «Where…»: si applica
**solo dove** la procedura è effettivamente shippata come asset). Non essendo shippata, non c'è nulla da
allineare nell'asset. Va però **segnalato** (questo è il segnale): la procedura `distill.md` è
Sertor-coupled e non ancora host-agnostica (è nel backlog «refactor host-agnostico delle skill wiki»,
citato nel SYNC IMPACT della costituzione). Quando quella procedura diventerà un asset installabile,
FR-011 dovrà essere riaperto.

**Alternatives**:
- *Copiare la procedura «from conversation» dentro `claude-md-block.md`*: scartato — gonfierebbe l'asset
  con dettaglio di un'operazione che oggi non è distribuita, e introdurrebbe drift fra due copie. Il
  comando `sertor-rag memory show/list` che la procedura userebbe è comunque host-agnostico (Principio
  X), quindi la guida resterà valida quando l'asset la includerà.

**Azione concreta per FR-011**: aggiungere una nota nel `claude-md-block.md` **non** è richiesto; si
documenta lo stato qui e nel plan. (Se in fase di tasks si preferisce un mini-allineamento, basta
estendere la riga `distill` con «(può attingere a una sessione archiviata via `sertor-rag memory
show`)» — è additivo e host-agnostico; lasciato come opzione, non obbligo.)

## D-7 — Manopola `memory_list_limit` (FR-002, Principio VIII)

**Decision**: nuova manopola `Settings.memory_list_limit: int = 20`
(`SERTOR_MEMORY_LIST_LIMIT`), letta in `Settings.load()` accanto a `episodic_limit`
(`settings.py:129,257`). Il flag CLI `-k/--limit` la sovrascrive per-invocazione (default = la manopola).

**Rationale**: Principio VIII (default solo in `Settings`, nessun hardcode nei componenti); coerenza
esatta con `episodic_limit` (stesso ruolo per `memory search`). `list_recent` riceve il limite risolto
dal consumer, non lo legge da sé (il core non hardcoda default).

**Alternatives**:
- *Riusare `episodic_limit`*: scartato — è la cardinalità dei risultati di una *ricerca* full-text,
  semantica diversa dall'elenco delle sessioni; accoppiarle confonderebbe due manopole indipendenti.
- *Limite hardcoded in `list_recent`*: scartato (viola Principio VIII).

## D-8 — Osservabilità del percorso di lettura (Principio IX, RNF-2)

**Decision**: `show`/`list` emettono un evento `log_event` informativo con **conteggi**, mai contenuto
in chiaro: per `show` `session_key` + `turn_count` + `found` (bool); per `list` `count` + `limit`. I
guasti store riusano l'evento esistente `memory_archive_unavailable` (`archive.py:89,101,138`).

**Rationale**: Principio IX (ogni operazione runtime loggata) + RNF-2 (nessun testo in chiaro negli
eventi; coerente con `episodic_search` che hasha la query, `episodic_search.py:255-274`). `session_key`
è una chiave opaca (filename stem), non contenuto conversazionale → loggabile.

**Alternatives**:
- *Nessun log*: scartato (viola Principio IX).
- *Loggare un estratto del transcript*: scartato (viola RNF-2/sicurezza segreti).

## Sintesi delle scelte

| ID | Scelta | Principio guida |
|----|--------|-----------------|
| D-1 | Riuso `MemoryArchive.get` per la sessione intera | III (DRY) |
| D-2 | Factory `build_memory_reader` → `MemoryArchive`, gated; niente porta | I, III, FR-005/SC-007 |
| D-3 | `list_recent(limit)` additivo su `MemoryArchive` + `SessionSummary` | III |
| D-4 | not-found (`SessionNotFoundError`, exit≠0) ≠ sessione vuota (exit 0) | IV |
| D-5 | `format_session_transcript`/`format_session_list` pure | I, VII |
| D-6 | FR-011 = no-op documentato (asset non contiene la procedura) | X, segnalazione |
| D-7 | `memory_list_limit` in `Settings` | VIII |
| D-8 | Eventi di lettura con conteggi, mai testo in chiaro | IX, RNF-2 |
