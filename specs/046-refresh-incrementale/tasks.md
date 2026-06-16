# Tasks — Refresh incrementale dell'indice (FEAT-009)

**Branch**: `046-refresh-incrementale` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Convenzioni: `[P]` = parallelizzabile (file diversi, nessuna dipendenza). Ogni task cita i file reali.
Gate: il **test di equivalenza** (T021) è il criterio cardine (SC-002, FR-012).

## Fase 1 — Foundational (bloccante, prereq di tutto)

- [x] **T001** — `src/sertor_core/domain/errors.py`: aggiungi `IndexLockedError` (eccezione di dominio,
  messaggio azionabile che nomina l'indice). [P]
- [x] **T002** — `src/sertor_core/domain/entities.py`: estendi `IndexReport` con `added/updated/removed/
  unchanged/cache_hits: int = 0` e `mode: str = "full"` (additivo, default retro-compatibili). [P]
- [x] **T003** — `src/sertor_core/config/settings.py`: aggiungi le manopole `index_incremental: bool`
  (`SERTOR_INDEX_INCREMENTAL`, default **True**) e `index_reconcile_every: int`
  (`SERTOR_INDEX_RECONCILE_EVERY`, default **0**). Solo in `Settings`, nessun default hardcoded altrove. [P]
- [x] **T004** — `.gitignore`: assicura che `**/index_manifest.sqlite` (e il lockfile `**/.index.lock`) siano
  ignorati (artefatti rigenerabili). [P]

## Fase 2 — Manifest store (User Story 1/2, P1) — il cuore

- [x] **T005** — `src/sertor_core/services/index_manifest.py` (NUOVO): `IndexManifest` store SQLite
  (`<index_dir>/index_manifest.sqlite`, namespaced per collezione). Schema `meta/files/documents/chunks`
  (data-model.md). Metodi: `load`, `classify(current_files)→{UNCHANGED/NEW/MODIFIED/DELETED}` (mtime
  pre-filtro + hash conferma, FR-002/003), `units_for(doc_ids)→(documents,chunks)`, `apply(added,updated,
  removed)` (transazione atomica), `chunk_ids_for(doc_ids)`, `bump_reconcile()`, `logic_version` corrente.
  stdlib `sqlite3`/`hashlib`. Versione schema incompatibile → `load` ritorna None (caller → full, FR-011).
- [x] **T006** — `FileClassification` enum (in `domain/entities.py` o `index_manifest.py`): UNCHANGED/NEW/
  MODIFIED/DELETED. [P con T005 se in file diverso]
- [x] **T007** — `src/sertor_core/services/ingestion.py`: esponi una scansione che separa **stat** (tutti i
  file, cheap) da **read+parse** (solo i candidati cambiati), riusabile dal ramo incrementale; il full
  resta invariato.

## Fase 3 — Ramo incrementale in `index()` (User Story 1/2/3, P1)

- [x] **T008** — `src/sertor_core/services/indexing.py`: introduci il **single-writer lock** (lockfile in
  `index_dir`, acquisito a inizio `index()`, rilasciato a fine anche su errore; preso → `IndexLockedError`,
  FR-020).
- [x] **T009** — `indexing.py`: ramo **incrementale** in `index()` quando `rebuild=False`, `index_incremental`
  e manifest valido: detect (T005) → process NEW/MODIFIED (chunk+embed+`upsert` mirato) → prune
  MODIFIED/DELETED (`VectorStore.delete(chunk_ids)`, FR-005) → rebuild secondari (T010) → `apply` manifest
  → report. Fallback al full se manifest assente/incompatibile (FR-011). `rebuild=True` o
  `index_incremental=False` → full (path esistente) + scrive il manifest.
- [x] **T010** — `indexing.py`: assembla l'insieme completo di unità = `units_for(UNCHANGED)` ∪ fresh(NEW/
  MODIFIED) e ricostruisci **BM25** (`LexicalIndex.build`) e **code-graph** (`extract_graph`+`CodeGraph.
  build`) pieni dal manifest (F1, FR-007/008) — niente re-chunk/re-read degli invariati.
- [x] **T011** — `indexing.py`: gestione errore a metà file (FR-014): segnala, non lasciare stato parziale
  (rollback della transazione manifest + nessun upsert/delete parziale del file fallito).
- [x] **T012** — `src/sertor_core/composition.py`: `build_indexer` costruisce e inietta `IndexManifest` +
  il lock; mantiene il wiring `_wire_runtime` (osservabilità). Default incrementale governato da Settings.

## Fase 4 — Correttezza su cambio-logica (User Story 4, P2)

- [x] **T013** — `index_manifest.py`/`indexing.py`: calcola `logic_version` da parametri chunking + versione
  estrazione grafo; se differisce dal manifest → tratta i file interessati come MODIFIED (FR-013).

## Fase 5 — Osservabilità del delta (User Story 5, P3)

- [x] **T014** — `indexing.py`: popola `IndexReport` con i conteggi delta e `mode`; emetti l'evento `index`
  esteso via `log_event` (added/updated/removed/unchanged/cache_hits, FR-015/016). Nessun segreto.

## Fase 6 — Riconciliazione + vehicle

- [x] **T015** — `indexing.py`: full di **riconciliazione** quando `reconcile_every>0` e il contatore scatta
  (FR-019); off di default. [P con T016]
- [x] **T016** — `src/sertor_core/cli/__main__.py`: flag `--full` sul comando `index` (vehicle); default
  incrementale; mappa su `rebuild=True`. Aggiorna l'help. [P con T015]
- [x] **T017** — template `.env` dell'installer (se presente nel pacchetto `sertor`): aggiungi
  `SERTOR_INDEX_INCREMENTAL`/`SERTOR_INDEX_RECONCILE_EVERY` (regola «feature installabile»). [P]

## Fase 7 — Test

- [x] **T018** — `tests/unit/test_index_manifest.py`: `classify` (mtime cambiato+hash uguale → UNCHANGED;
  hash diverso → MODIFIED; assente → NEW; sparito → DELETED), `apply` atomico, schema incompatibile →
  None, `logic_version` mismatch → MODIFIED. Porte mock. [P]
- [x] **T019** — `tests/unit/test_incremental_index.py`: ramo incrementale con porte mock — upsert/delete
  mirati chiamati sui soli cambiati; unchanged saltati; fallback al full su manifest assente; lock →
  `IndexLockedError` su run concorrente; idempotenza (2° run = 0 modifiche). [P]
- [x] **T020** — `tests/unit/test_incremental_report.py`: conteggi delta corretti + `mode` + evento osservabile. [P]
- [x] **T021** — `tests/integration/test_incremental_equivalence.py` **(GATE, SC-002/FR-012)**: con Chroma
  locale + embedder mock, indicizza un corpus; (a) modifica un file, (b) cancella un file, (c) aggiungi un
  file → l'indice (vector+BM25+graph) dopo il run **incrementale** è **identico** a un full rebuild sulla
  stessa sorgente; query coerenti. Misura il guadagno (SC-001).

## Fase 8 — Polish

- [x] **T022** — `uv run ruff check --fix .` + `uv run pytest -m "not cloud"` verdi (tutta la suite root). [P]
- **T023** — wiki/distill + re-index dogfood: rinviati al rituale post-merge (non in tasks di codice).

## Esecuzione parallela (esempio)
T001–T004 in parallelo (file diversi). Poi T005→T007 (manifest). Poi T008–T012 (sequenziali, stesso
`indexing.py`). T013/T014 dopo. T015/T016/T017 in parallelo. Test T018–T020 in parallelo; T021 dopo T009–T014.

## Dipendenze chiave
Foundational (T001–T004) → Manifest (T005–T007) → Ramo incrementale (T008–T012) → cambio-logica (T013) →
osservabilità (T014) → riconciliazione/vehicle (T015–T017) → test (T018–T021) → polish (T022).
