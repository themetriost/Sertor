---
description: "Task list — manutenzione del wiki (FEAT-007)"
---

# Tasks: Skill — manutenzione del wiki (lint / indice / documentazione)

**Input**: Design da `specs/005-wiki-manutenzione/`. **Prereq**: FEAT-003 + porta `LLMProvider` in `master`.

**Tests**: INCLUSI; tutti su **wiki sandbox** in temp (mai produzione). Distillazione con `FakeLLM`.

**Organization**: estende `src/sertor_core/wiki/`. Foundational = convenzioni (marcatori catalogo) +
entità report. Scope: Must + Should (lint+gate, indice+fix, documentazione, contraddizioni marcate).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup
- [ ] T001 Verifica struttura pacchetto `src/sertor_core/wiki/` (esistente); nessun nuovo package.

## Phase 2: Foundational
- [ ] T002 Estendi `src/sertor_core/wiki/conventions.py`: costanti marcatori catalogo (`CATALOG_BEGIN`/`CATALOG_END` = `<!-- sertor:catalog -->` / `<!-- /sertor:catalog -->`) + helper `replace_managed_block(text, begin, end, new_block)` (non distruttivo: rimpiazza solo il blocco, lo appende se assente) (REQ-010/011, DA-1)
- [ ] T003 [P] Definisci in `src/sertor_core/wiki/maintenance.py` le entità `IssueKind` (enum), `Issue`, `LintReport` (con proprietà `ok`) (data-model)
- [ ] T004 [P] Aggiungi fixture in `tests/conftest.py`/fixtures: `wiki_with_issues` (wiki sandbox con un link rotto, una pagina orfana, una pagina non in indice, una pagina con marcatore di contraddizione)

**Checkpoint**: convenzioni + entità + fixture pronte

---

## Phase 3: User Story 1 - Lint: report di igiene e coperture (P1) 🎯 MVP
### Tests
- [ ] T005 [P] [US1] Test in `tests/unit/test_wiki_maintenance.py`: lint rileva link rotti (REQ-002), orfani con `index.md`/`log.md` esenti (REQ-003), pagine non in indice (REQ-004), coperture mancanti su `expected` (REQ-064), pagine con marcatore di contraddizione (REQ-020); **nessuna scrittura** (REQ-005); `report.ok` riflette la presenza di problemi
### Implementation
- [ ] T006 [US1] Implement `lint(root, *, expected=None, fix=False) -> LintReport` in `src/sertor_core/wiki/maintenance.py`: scoperta pagine, parsing wikilink `[[...]]`, grafo riferimenti, derivazione issue tipizzate, coperture vs `expected`, contraddizioni via marcatore; sola lettura se `fix=False`; log strutturato (REQ-001..005/020/052/064/051)

**Checkpoint**: US1 testabile (lint + report)

---

## Phase 4: User Story 2 - Gate ricorrente pass/fail (P1)
### Tests
- [ ] T007 [P] [US2] Test in `tests/unit/test_wiki_maintenance.py` (parte gate): wiki sano → `report.ok is True`; wiki con problemi → `report.ok is False`; due run su wiki invariato → report equivalente (idempotente, nessun side-effect) (REQ-053/040)
### Implementation
- [ ] T008 [US2] Garantire in `lint` un esito **non interattivo** e `report.ok` (pass/fail) come gate; documentare l'uso `sys.exit(0 if report.ok else 1)` (REQ-053)

**Checkpoint**: US2 verificata (gate)

---

## Phase 5: User Story 3 - Rigenerazione idempotente dell'indice + --fix (P1)
### Tests
- [ ] T009 [P] [US3] Test in `tests/unit/test_wiki_index_rebuild.py`: `regenerate_index` aggiorna solo il blocco tra marcatori e preserva il resto (REQ-011); re-run → `index.md` identico (REQ-012); pagina nuova compare nel catalogo (REQ-010); `lint(fix=True)` applica solo la rigenerazione indice, mai i link (REQ-006)
### Implementation
- [ ] T010 [US3] Implement `regenerate_index(root) -> bool` in `maintenance.py`: costruisce il catalogo (link + sommario per pagina, ordinato) e rimpiazza il blocco gestito via `replace_managed_block` (idempotente, non distruttivo); collega `fix=True` di `lint` a questa operazione (REQ-006/010..013)

**Checkpoint**: US3 testabile (indice + fix)

---

## Phase 6: User Story 4 - Documentazione ufficiale distillata (P2, Should)
### Tests
- [ ] T011 [P] [US4] Test in `tests/unit/test_wiki_distill_doc.py` (FakeLLM): `distill_artifact` crea una pagina conforme con **backlink** alla fonte (REQ-061/062/063); su pagina già esistente **non** sovrascrive (assistita/non distruttiva, DA-3); senza LLM → `LLMNotConfiguredError` (REQ-065)
### Implementation
- [ ] T012 [US4] Implement `distill_artifact(root, source, kind, title, llm, today=None) -> WikiOpResult` in `src/sertor_core/wiki/distill.py`: legge la sorgente (artifact path o brief), `llm.generate(...)` → corpo, scrive pagina conforme con `sources=[source]` + riga di rimando; **crea-se-assente** (non sovrascrive il curato); senza LLM → errore esplicito (REQ-060..065)

**Checkpoint**: US4 testabile (distillazione documentale)

---

## Phase 7: User Story 5 - Contraddizioni marcate (P2)
### Tests
- [ ] T013 [P] [US5] Test in `tests/unit/test_wiki_maintenance.py` (parte contraddizioni): pagina con marcatore → issue `contradiction`; senza LLM nessun errore (semantiche saltate) (REQ-020/022)

> Impl: coperta da `lint` (T006, rilevazione marcatori). Le contraddizioni semantiche (LLM) sono Could → fuori scope ora.

**Checkpoint**: US5 verificata

---

## Phase 8: Polish & Cross-Cutting
- [ ] T014 Integration test idempotenza in `tests/integration/test_wiki_maintenance_idempotence.py`: lint + regenerate_index rieseguiti su wiki invariato → esito identico, hash file invariati (REQ-040, SC-002)
- [ ] T015 [P] Run full suite + ruff; verifica non-distruttività (lint non scrive; index-rebuild preserva il curato)
- [ ] T016 [P] Aggiorna `src/sertor_core/README.md` con sezione "Manutenzione del wiki" (lint/regenerate_index/distill_artifact) allineata a quickstart.md

---

## Dependencies & Execution Order
- Setup → Foundational (T002 prima di T006/T010; T003/T004 [P]).
- US1 (T005/T006) → US2 (T007/T008, usa report.ok) ; US3 (T009/T010, usa T002).
- US4 (T011/T012) indipendente (distill.py). US5 (T013) verifica su T006.
- Polish dopo le user story.

## Notes
- Riusa convenzioni FEAT-003 (DRY); idempotenza/non-distruttività cardine.
- LLM solo per `distill_artifact`; lint/indice/coperture/contraddizioni-marcate LLM-free.
- Test su wiki sandbox; commit per checkpoint (delega al `configuration-manager`).
- **Mapping**: US1=REQ-001..005/052/064; US2=REQ-053/040; US3=REQ-006/010..013; US4=REQ-060..065; US5=REQ-020/022.
