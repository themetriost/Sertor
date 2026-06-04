---
description: "Task list — lint semantico del wiki (FEAT-007 estensione)"
---

# Tasks: Lint semantico del wiki

**Input**: design da `specs/006-wiki-lint-semantico/`. **Prereq**: FEAT-007 strutturale (`maintenance.py`),
porta `LLMProvider`, facade di retrieval. **Tests**: inclusi, su wiki sandbox con **LLM scriptato**.

**Scope di questo ciclo**: P1 completo + test (US1 rilevazione baseline, US2 provenienza) e US4 in forma
**proposta**. US3 (incrementale git/watermark) e US5 (hook pre-commit/scrittura) sono **dichiarati** e
lasciati alla fase successiva (task marcati ⏭️).

## Format: `[ID] [P?] [Story] Descrizione`

---

## Phase 1: Setup
- [X] T001 Verifica pacchetto `src/sertor_core/wiki/` (esistente); nessun nuovo package.

## Phase 2: Foundational
- [X] T002 [P] Definisci entità in `src/sertor_core/wiki/semantic.py`: `Severity` (ordinale), `SemanticIssueKind`, `SemanticIssue`, `SemanticReport` (con `ok`/copertura), `FixProposal` (data-model)
- [X] T003 [P] Estendi `src/sertor_core/wiki/conventions.py`: `read_provenance(text)` (default curated) + `mark_provenance(text, value)` (non distruttivo) (REQ-076/077c)
- [X] T004 [P] Aggiungi `ScriptedLLM` in `tests/fixtures/mocks.py`: LLM mock che ritorna risposte JSON predefinite in sequenza (deterministico)

**Checkpoint**: entità + provenienza + mock pronti

---

## Phase 3: User Story 1 — Rilevazione semantica (P1) 🎯 MVP
### Tests
- [X] T005 [P] [US1] Test `tests/unit/test_wiki_semantic.py`: con ScriptedLLM, `semantic_lint` produce issue `obsolete` con la **claim** (REQ-071/098), `semantic_contradiction` (072), `coverage_gap` (073), `stale_summary` (074); ogni issue ha severità; **nessuna scrittura** sul wiki (Principio VI)
- [X] T006 [P] [US1] Test gate/degrado: `report.ok` falso se issue ≥ soglia, vero altrimenti (REQ-082); `llm=None` → `SemanticReport(skipped=True)` senza errore (REQ-081); copertura `pages_checked/pages_total` e `max_pages` rispettato (REQ-083); parsing difensivo di JSON malformato (voci saltate, no crash)
- [X] T007 [P] [US1] Test idempotenza rilevazione: due run con ScriptedLLM identico → stesso insieme issue/severità (REQ-084)
### Implementation
- [X] T008 [US1] Implementa `semantic_lint(root, llm, facade=None, *, threshold, k_code, max_pages, pages=None) -> SemanticReport` in `semantic.py`: scoperta pagine (riusa `maintenance._pages`), contesto codice via facade, prompt JSON per-claim, parsing difensivo, severità, `ok` su soglia, copertura, log strutturati (REQ-071..075/082/083/098, NFR-06)

**Checkpoint**: US1 eseguibile sul wiki reale (baseline)

---

## Phase 4: User Story 2 — Provenienza (P1)
### Tests
- [X] T009 [P] [US2] Test `tests/unit/test_wiki_provenance.py`: `read_provenance` default curated; `mark_provenance` inserisce/aggiorna senza distruggere il resto; pagina prodotta da `distill_artifact` risulta **generated**; modifica manuale → riclassifica curated (REQ-076/077/077b/077c)
### Implementation
- [X] T010 [US2] Wira la marcatura in `src/sertor_core/wiki/distill.py::distill_artifact` (marca `generated`); implementa la regola di riclassifica (helper) e la classificazione iniziale opzionale (REQ-077/077b/086)

**Checkpoint**: US2 (provenienza) testabile

---

## Phase 5: User Story 4 — Proposte di correzione (P2, forma proposta)
### Tests
- [X] T011 [P] [US4] Test `tests/unit/test_wiki_semantic_fixes.py` (ScriptedLLM): `propose_fixes` genera `FixProposal` per issue su pagine **generated** (rewrite_claim / delete_page) con motivazione (REQ-078/085); su pagine **curated** **nessuna** proposta di modifica (REQ-080); **nessuna scrittura** (Principio VI)
### Implementation
- [X] T012 [US4] Implementa `propose_fixes(report, root, llm) -> list[FixProposal]` in `semantic.py`: filtra per provenienza generated, chiede all'LLM la riscrittura chirurgica della claim o propone la cancellazione; non scrive (REQ-078/080/085)

**Checkpoint**: US4 (proposte) testabile

---

## Phase 6: Polish & Cross-Cutting
- [X] T013 [P] Run full suite + ruff; verifica non-distruttività (rilevazione e proposte non scrivono)
- [X] T014 [P] Aggiorna `src/sertor_core/README.md`: sezione "Lint semantico del wiki" allineata a quickstart
- [X] T015 Dogfood: eseguito `semantic_lint` sul **wiki di produzione** con LLM reale **Ollama qwen3:30b** (Azure chat non configurato) su 6/17 pagine. Esito: il run funziona end-to-end; ha rivelato che il **corpus codice locale non è indicizzato** (collezione nomic vuota; `.index-production` è solo Azure 3072), quindi l'obsolescenza-vs-codice è degradata a coerenza interna → **aggiunta la segnalazione esplicita** `pages_without_code_context` nel report (REQ-083/097). Modello locale rumoroso (contraddizioni dubbie) → conferma auto-fix gated.

---

## Fase successiva (dichiarata, NON in questo ciclo)
- ⏭️ T100 [US3] Verifica incrementale git-driven: watermark, mappa entità↔pagine, change-set staged/commit, fallback baseline (REQ-087..091)
- ⏭️ T101 [US3] Re-index incrementale del change set prima del confronto (sinergia FEAT-009), fallback working tree (REQ-096/097)
- ⏭️ T102 [US4] Applicazione assistita su working tree + cancellazione, diff revisionabile (REQ-079)
- ⏭️ T103 [US5] Trigger pre-commit/pre-push a monte del configuration-manager; gate blocco sopra soglia + override tracciato (REQ-092..095)

---

## Dependencies
- Setup → Foundational (T002/T003/T004 [P]).
- US1 (T005..T008) usa T002/T004. US2 (T009/T010) usa T003. US4 (T011/T012) usa T002/T008 + provenienza T003/T010.
- Polish dopo le user story; T015 (dogfood) richiede LLM reale configurato.

## Mapping
US1=REQ-071..075/082/083/084/098 · US2=REQ-076/077/077b/077c/086 · US4=REQ-078/080/085 ·
US3=REQ-087..091/096/097 (⏭️) · US5=REQ-092..095 (⏭️).
