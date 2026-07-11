# Tasks: Documentazione utente MVP (getting-started unico + README di valore)

**Feature**: 096-doc-utente-mvp (item A-18, E13 Fase 1) | **Branch**: `096-doc-utente-mvp`
**Input**: [spec.md](spec.md) · [plan.md](plan.md) · [research.md](research.md) · [quickstart.md](quickstart.md)

> **Natura:** authoring di **documentazione statica** (nessun codice/test automatico). I «test» sono i
> criteri di accettazione SC-001..006 (vedi `quickstart.md`) + verifica manuale/scriptata dei link
> relativi. Confine D↔N: `sertor-core`/CLI/installer **INVARIATI**. Anti-drift: ogni comando **copiato**
> dagli asset reali.

## Phase 1: Setup (fonti reali)

- [ ] T001 Estrarre l'inventario dei **comandi reali** e dei loro punti di divergenza per-assistente da
  `docs/install-claude.md`, `docs/install-copilot.md`, `docs/retrieval.md`, `docs/install.md`,
  `packages/sertor/docs/install.md` e dal `README.md` attuale (install rag, configure, index, search,
  caricamento MCP, prerequisiti). Serve da fonte verbatim per T00x — nessun comando inventato (FR-012/014,
  Decisione 4 di `research.md`). *(Già in gran parte svolto in research; questo task ne fa la checklist
  operativa prima di scrivere.)*

## Phase 2: Foundational

> Nessun prerequisito bloccante condiviso oltre al Setup: i due artefatti sono file indipendenti.
> (US1 e US2 si linkano a vicenda, ma ciascuno è scrivibile e testabile in autonomia.)

## Phase 3: User Story 1 — Percorso unico → primo valore (Priority: P1) 🎯 MVP

**Goal:** un `docs/getting-started.md` che porta «dal nulla al primo valore» in un solo percorso
host-agnostico, terminando con l'esempio code+doc.

**Independent Test:** seguendo solo `docs/getting-started.md`, un lettore raggiunge il primo retrieval
eseguendo i comandi mostrati; l'esempio finale mostra `(docs, code)` insieme (SC-001/SC-003).

- [ ] T002 [US1] Creare `docs/getting-started.md` con l'intestazione e l'**indice a 4 tappe** (Prerequisiti
  → Installa il RAG → Indicizza → Prima query) come unico viaggio lineare host-agnostico, senza scelta
  dell'assistente in cima (FR-001/FR-002).
- [ ] T003 [US1] Sezione **Prerequisiti** in `docs/getting-started.md`: Python ≥ 3.11 + `uv`, rete GitHub
  (`git+url`, no PyPI), provider embeddings (default `glove` zero-config; Azure/Ollama opzionali) —
  copiati dagli asset reali (FR-012).
- [ ] T004 [US1] Sezione **Installa il RAG** in `docs/getting-started.md` con **entrambe le varianti CLI
  affiancate** (Claude `--assistant` omesso · Copilot `--assistant copilot-cli`), più il cenno a `sertor
  configure` per Azure; **delega** il dettaglio pieno a `install-claude.md`/`install-copilot.md` senza
  ricopiarlo (FR-003/FR-011, clarify DA-1).
- [ ] T005 [US1] Sezione **Indicizza** in `docs/getting-started.md`: `uv run --project .sertor sertor-rag
  index .` con la nota `--project` (non `--directory`) e il download GloVe una-tantum; caricamento del
  server MCP (Claude: `.mcp.json`/reload · Copilot: `/mcp reload`) affiancati (FR-002/FR-011/FR-012).
- [ ] T006 [US1] Sezione finale **Prima query = fusione code+doc** in `docs/getting-started.md`: esempio
  **illustrativo generico host-agnostico** di `search_combined` che restituisce un flusso `docs` (il
  *perché*) **e** un flusso `code` (il *cosa*), con forma d'output realistica e path placeholder; + il
  `sertor-rag search` da terminale (FR-004/FR-008, clarify DA-2).
- [ ] T007 [US1] Chiusura di `docs/getting-started.md`: rimandi a `docs/install.md` (reference completo
  flag/manopole) e `docs/retrieval.md` (concetti hybrid vs graph), **assorbendo e ordinando**, non
  ripetendo (FR-005). Nessun rimando a `wiki/`/`specs/` (FR-013).

## Phase 4: User Story 2 — README valore-first (Priority: P1)

**Goal:** `README.md` che apre col differenziatore fusione code+doc + esempio concreto, preserva i fatti,
e punta al getting-started come ingresso unico.

**Independent Test:** dalla sola apertura del README un non-addetto enuncia cos'è Sertor e il
differenziatore, trova l'esempio code+doc e l'ingresso unico (SC-002/SC-003).

- [ ] T008 [US2] Riscrivere l'**apertura** di `README.md`: prima riga/paragrafo = differenziatore **fusione
  code+doc** (*il codice dice cosa fa, la documentazione dice perché*), **prima** di ogni elenco di
  feature/status, senza gergo non spiegato (FR-006/FR-007).
- [ ] T009 [US2] Aggiungere in `README.md` **almeno un esempio concreto** del differenziatore (query
  `search_combined` → codice + documento insieme), illustrativo generico host-agnostico coerente con T006
  (FR-008, clarify DA-2).
- [ ] T010 [US2] **Preservare i fatti** di capacità/status in `README.md` (nessuna regressione informativa
  vs versione precedente), **riordinati** sotto la narrazione di valore; condensare dove ridondante
  (FR-010, R-3).
- [ ] T011 [US2] Sostituire la sezione install del `README.md` con un **puntatore all'ingresso unico**
  `docs/getting-started.md` (mantenendo i rimandi ai per-assistente/reference come dettaglio), sezione
  Development invariata (FR-009).

## Phase 5: User Story 3 — Convergenza dei doc esistenti (Priority: P2)

**Goal:** i doc esistenti convergono sul getting-started senza duplicazione né esposizione di artefatti
interni.

**Independent Test:** navigando dai doc esistenti si raggiunge il getting-started e viceversa; 0 blocchi
duplicati verbatim; 0 esposizioni di `wiki/`/`specs/` (SC-005/SC-006).

- [ ] T012 [P] [US3] Aggiungere in testa a `docs/install-claude.md` un rimando al `docs/getting-started.md`
  come punto d'ingresso «dal nulla al primo valore» (convergenza, no duplicazione).
- [ ] T013 [P] [US3] Aggiungere in testa a `docs/install-copilot.md` lo stesso rimando al
  `docs/getting-started.md`.
- [ ] T014 [P] [US3] Aggiungere in `docs/retrieval.md` un rimando al `docs/getting-started.md` (per
  «installare/prima query» prima di approfondire hybrid vs graph).
- [ ] T015 [US3] Verificare l'assenza di **duplicazione verbatim** tra `docs/getting-started.md` e i
  per-assistente (il dettaglio divergente è delegato, non copiato) — correggere se emerge (SC-006, R-1).

## Phase 6: Polish & verifica di accettazione (cross-cutting)

- [ ] T016 Eseguire il **walkthrough di accettazione** del `quickstart.md` (SC-001..003, US1/US2): il
  percorso porta al primo valore, l'esempio code+doc c'è in entrambi gli artefatti, il README apre col
  valore.
- [ ] T017 **Verifica link relativi** (SC-004): controllo manuale/scriptato che ogni `[…](….md)` in
  `README.md` e in `docs/*.md` risolva a un file esistente (0 link interni rotti). Vedi DA-4: nessun
  linter automatico per `docs/`.
- [ ] T018 **Lint semantico / anti-drift finale** (FR-012/FR-014): rileggere i comandi mostrati contro gli
  asset reali; qualunque discrepanza → **finding** segnalato (Principio XII), non mascherato nella doc.

## Dependencies & execution order

- **Setup (T001)** prima di tutto (fornisce i comandi verbatim).
- **US1 (T002–T007)** e **US2 (T008–T011)** sono indipendenti ma **US1 è l'MVP** (l'ingresso unico) → farla
  prima; US2 la referenzia (T011 → `getting-started.md` deve esistere).
- **US3 (T012–T015)**: T012/T013/T014 sono **[P]** (file diversi); T015 dopo US1.
- **Polish (T016–T018)** alla fine, quando entrambi gli artefatti esistono.

## Parallel opportunities

- T012, T013, T014 in parallelo (file distinti, nessuna dipendenza reciproca).
- US1 e US2 possono procedere in parallelo se due autori, con la sola cautela che T011 (puntatore README)
  presuppone il path `docs/getting-started.md` deciso in T002.

## Implementation strategy (MVP first)

- **MVP = US1** (`docs/getting-started.md`): da solo consegna l'ingresso unico al primo valore (CS-1).
- Poi **US2** (README di valore) e **US3** (convergenza), quindi la verifica di accettazione.
- Consegna incrementale in un solo branch/PR (`096-doc-utente-mvp`), poiché i due Must sono la coppia
  accoppiata di Fase 1.

**Task totali:** 18 · **US1:** 6 (T002–T007) · **US2:** 4 (T008–T011) · **US3:** 4 (T012–T015) ·
Setup 1 · Polish 3.
