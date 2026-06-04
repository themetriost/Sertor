---
description: "Task list — lint semantico del wiki (FEAT-007 estensione) — scope ampliato US3/US4-scrittura/US5"
---

# Tasks: Lint semantico del wiki

**Input**: design da `specs/006-wiki-lint-semantico/` (spec/plan/research/data-model/contracts/quickstart).
**Prereq**: FEAT-007 strutturale (`maintenance.py`), porta `LLMProvider`, facade di retrieval.
**Tests**: inclusi, su wiki sandbox con **LLM scriptato** + **`FakeGit`** deterministico.

**Stato**: il **P1 è già implementato e testato** (T001–T015 ✅). Questo ciclo porta a implementazione
**US3** (incrementale git-driven), **US4-scrittura** (apply_fixes), **US5** (gate fuori dal dominio).
Re-index reale del corpus è **rinviato a FEAT-009** → in US3 vale solo il **fallback working tree** (REQ-096/097).

## Format: `[ID] [P?] [Story] Descrizione`

---

## Phase 1: Setup ✅ (P1, fatto)
- [X] T001 Verifica pacchetto `src/sertor_core/wiki/` (esistente); nessun nuovo package.

## Phase 2: Foundational (P1) ✅ (fatto)
- [X] T002 [P] Entità in `src/sertor_core/wiki/semantic.py`: `Severity`, `SemanticIssueKind`, `SemanticIssue`, `SemanticReport`, `FixProposal`.
- [X] T003 [P] Estendi `conventions.py`: `read_provenance`/`mark_provenance`.
- [X] T004 [P] `ScriptedLLM` in `tests/fixtures/mocks.py` (JSON deterministico).

## Phase 3: US1 — Rilevazione semantica (P1) ✅ (fatto)
- [X] T005 [P] [US1] Test `tests/unit/test_wiki_semantic.py`: obsolete/contradiction/coverage_gap/stale_summary; severità; nessuna scrittura.
- [X] T006 [P] [US1] Test gate/degrado: soglia, `llm=None`→skipped, copertura/`max_pages`, parsing difensivo.
- [X] T007 [P] [US1] Test idempotenza rilevazione.
- [X] T008 [US1] Implementa `semantic_lint(...)` in `semantic.py` (baseline, accetta `pages=`).

## Phase 4: US2 — Provenienza (P1) ✅ (fatto)
- [X] T009 [P] [US2] Test `tests/unit/test_wiki_provenance.py`.
- [X] T010 [US2] Wira la marcatura `generated` in `distill.py::distill_artifact` + riclassifica.

## Phase 5: US4-proposta (P2) ✅ (fatto)
- [X] T011 [P] [US4] Test `tests/unit/test_wiki_semantic_fixes.py` (proposte, solo generated, no scrittura).
- [X] T012 [US4] Implementa `propose_fixes(report, root, llm)` (proposta, no scrittura).

## Phase 6: Polish P1 ✅ (fatto)
- [X] T013 [P] Run suite + ruff; non-distruttività P1.
- [X] T014 [P] README sezione "Lint semantico del wiki" (P1).
- [X] T015 Dogfood `semantic_lint` su wiki di produzione (Ollama); aggiunta `pages_without_code_context`.

---

# NUOVO SCOPE (questo ciclo) — US3 / US4-scrittura / US5

## Phase 7: Foundational del nuovo scope (infrastruttura US3/US5) ⚙️

**Goal**: porte, adapter, mock e estensioni dati che abilitano incrementale e gate.
**Test indipendente**: importabili e unit-testabili in isolamento con `FakeGit`, senza repo/LLM reali.

- [X] T016 [P] Definisci `GitPort` (Protocol) in `src/sertor_core/domain/ports.py`: `changed_paths(scope: Literal["staged","working","since_watermark"], watermark: str | None = None) -> list[str]`, `head_commit() -> str | None`, `renamed_paths() -> list[tuple[str,str]]` (default `[]`). (FR-017, R8)
- [X] T017 [P] Implementa `SubprocessGitAdapter(GitPort)` in `src/sertor_core/adapters/git/subprocess_git.py` (+ `__init__.py` che lo esporta): `git diff --name-only` per staged/working, `git diff --name-only <watermark>..HEAD` per since_watermark, `git rev-parse HEAD`, `git diff --name-status -M` per i rename. Nessun import git nel dominio. (FR-017, R8)
- [X] T018 [P] Aggiungi `FakeGit` (GitPort deterministico) in `tests/fixtures/mocks.py`: ritorna liste di path e SHA preconfigurati, scope-aware. (R8, testabilità)
- [X] T019 [US3] Estendi `SemanticReport` in `semantic.py` con `mode: str = "baseline"` e `fallbacks: list[str]` (default `[]`); aggiorna `render()` per mostrarli. Non rompe i call site P1. (R11, data-model)
- [X] T020 [P] [US3] Helper watermark in `conventions.py`: `read_watermark(root) -> str | None` (None se assente), `write_watermark(root, sha)` (crea `wiki/.sertor/`, scrittura non distruttiva). Escludi `.sertor/` dalla scoperta pagine (`maintenance._pages`/discovery). (FR-018, R10)

**Checkpoint**: porta+adapter+FakeGit pronti; report esteso; watermark read/write; `.sertor/` esclusa.

---

## Phase 8: US3 — Verifica incrementale git-driven (P2) 🎯

**Goal**: dopo un baseline, ri-verificare solo le pagine collegate alle entità del change set.
**Test indipendente**: con `FakeGit`+`ScriptedLLM`, baseline vs incrementale selezionano set di pagine diversi; no-op e fallback segnalati.

### Tests
- [X] T021 [P] [US3] Test `tests/unit/test_wiki_incremental.py`: **baseline** (no watermark → tutte le pagine, `mode="baseline"`, REQ-087); **incrementale** (watermark + changed_paths → solo pagine collegate, `mode="incremental"`, REQ-088/090 → **SC-006**); **no-op** (change set non tocca pagine → 0 pagine, 0 chiamate LLM, REQ-093).
- [X] T022 [P] [US3] Test fallback/segnalazione: git assente o watermark invalido → **baseline segnalato** (`fallbacks` non vuoto, REQ-091); FEAT-009 assente → `fallbacks` include `"stale-index"` (REQ-096/097); watermark `read/write` round-trip.

### Implementation
- [X] T023 [US3] `_entity_page_map(root) -> dict[str, set[str]]` in `semantic.py`: deriva l'associazione file-codice→pagine dal frontmatter `sources:` e dai wikilink/backlink (no indice persistito). (REQ-090, R9)
- [X] T024 [US3] `semantic_lint_incremental(root, llm, facade, git, *, watermark_path=None, threshold=Severity.HIGH, k_code=5, max_pages=None) -> SemanticReport` in `semantic.py`: legge watermark; senza watermark/git → `semantic_lint` baseline + `fallbacks`; con watermark → `git.changed_paths` → `_entity_page_map` → `semantic_lint(pages=…)`, `mode="incremental"`; no-op se nessuna pagina; aggiunge `"stale-index"` ai `fallbacks` (re-index reale inattivo, FEAT-009). (REQ-087..091/096/097, R11/R12)

**Checkpoint**: US3 eseguibile con FakeGit; il chiamante può persistere il watermark a run completato.

---

## Phase 9: US4 — Auto-fix: applicazione su working tree (P2)

**Goal**: applicare le proposte SOLO su pagine generated, in modo chirurgico e revisionabile.
**Test indipendente**: con proposte sintetiche su wiki sandbox; verifica scrittura/cancellazione/rifiuto e dry_run.

### Tests
- [X] T025 [P] [US4] Test `tests/unit/test_wiki_apply_fixes.py`: `rewrite_claim` su **generated** → file cambia **solo** nella claim e **resta generated** (REQ-078/079 → **SC-007**); `delete_page` su generated → file rimosso (REQ-085); pagina **curated** → `refused_curated`, nessuna scrittura (REQ-080); claim non trovata → `skipped_no_match`; `dry_run=True` → nessuna modifica al filesystem.

### Implementation
- [X] T026 [P] [US4] Entità `FixApplication` (+ enum esito `applied|deleted|refused_curated|skipped_no_match`) in `semantic.py`. (data-model)
- [X] T027 [US4] `apply_fixes(proposals, root, *, dry_run=False) -> list[FixApplication]` in `semantic.py`: per ogni proposta legge la provenienza della pagina; **curated → refused**; `rewrite_claim` = sostituzione esatta della claim col `proposed_text` preservando il resto e il marcatore `generated`; `delete_page` = rimozione file; claim assente → `skipped_no_match`; `dry_run` non tocca il filesystem. (REQ-078/079/080/085, R13)

**Checkpoint**: US4-scrittura completa; diff revisionabile via git; mai tocca le curated.

---

## Phase 10: US5 — Gate pre-commit/pre-push (P2, FUORI dal dominio)

**Goal**: orchestrare incrementale + auto-fix + soglia in un gate con exit code e override, fuori dal core.
**Test indipendente**: con FakeGit+ScriptedLLM, esiti pass/warning/blocked e override registrato; exit code a livello CLI.

### Tests
- [X] T028 [P] [US5] Test `tests/unit/test_semantic_gate.py`: issue ≥ soglia dopo auto-fix → `status="blocked"` (REQ-094); issue < soglia → `status="warning"` (non blocca); change set irrilevante → `status="pass"` no-op (REQ-093); `override=True` → `status="pass"` con `override_record` valorizzato (REQ-095 → **SC-008**).
- [X] T029 [P] [US5] Test CLI `tests/unit/test_cli_semantic_gate.py`: `blocked` → **exit ≠ 0**; `pass`/`warning` → exit 0; `--override --reason` → exit 0 e override registrato nel log.

### Implementation
- [X] T030 [US5] Entità `GateOutcome` (`status: pass|warning|blocked`, `report`, `applied`, `override`, `override_record`) + `run_semantic_gate(root, llm, facade, git, *, threshold=Severity.HIGH, override=False, override_reason=None) -> GateOutcome` in **nuovo** `src/sertor_core/services/semantic_gate.py` (NON nel dominio wiki): incrementale → `apply_fixes` su generated → valuta `report.ok` vs soglia → status; override registra `override_record` (log strutturato + record). (REQ-092..095, R14)
- [X] T031 [US5] Esposizione CLI: sottocomando `sertor wiki semantic-gate` (in `cli/`) con `--threshold`, `--override`, `--reason`; costruisce git/llm/facade via `composition`, chiama `run_semantic_gate`, mappa `status` → exit code (`blocked`→≠0). Trigger a monte del configuration-manager (REQ-092). (R14)

**Checkpoint**: gate invocabile da CLI; blocca sopra soglia; override esplicito tracciato.

---

## Phase 11: Polish & Cross-Cutting (nuovo scope)
- [X] T032 [P] Run full suite + ruff; verifica non-distruttività (scrittura solo su generated, dry_run, watermark) e **Constitution Check 9/9**.
- [X] T033 [P] Aggiorna `src/sertor_core/README.md`: sezione lint semantico con **incrementale + scrittura + gate** (allineata a quickstart).
- [ ] T034 Dogfood (opzionale, **non eseguito** in questo ciclo — passo manuale): esegui `sertor wiki semantic-gate` in modalità incrementale sul **wiki di produzione** (LLM Ollama); registra esito, `mode`, `fallbacks` (atteso `stale-index`).

---

## Dependencies
- **Phase 7 (Foundational)** blocca US3/US5: T016/T017/T018 (porta+adapter+fake) e T019/T020 (report+watermark) prima di T021..T024 e T028..T031.
- **US3 (Phase 8)**: T023 prima di T024; test T021/T022 [P] in parallelo, validano dopo T024.
- **US4-scrittura (Phase 9)**: T026 prima di T027; usa `propose_fixes` (T012, già fatto) e provenienza (T003/T010, già fatti).
- **US5 (Phase 10)**: dipende da US3 (T024) + US4-scrittura (T027); T030 prima di T031; CLI test T029 dopo T031.
- **Polish (Phase 11)** dopo tutte le storie.

## Parallel execution (esempi)
- Foundational: `T016`, `T017`, `T018`, `T020` in parallelo (file diversi); `T019` tocca `semantic.py` (serializza con T023/T024/T026/T027).
- Test [P]: `T021`/`T022`/`T025`/`T028`/`T029` scrivibili in parallelo (file di test distinti).

## Mapping US→REQ
- **US3** = REQ-087..091/096/097 (T019..T024) + FR-017/018 (T016/T017/T020).
- **US4-scrittura** = REQ-078/079/080/085 (T025..T027).
- **US5** = REQ-092..095 (T028..T031); confine CLI/hook (finding A1/C1).
- P1 (fatto): US1=REQ-071..075/082..084/098 · US2=REQ-076/077/086 · US4-proposta=REQ-078/080/085.

## MVP scope (questo ciclo)
US3 (incrementale baseline+fallback) è il cuore del nuovo valore; US4-scrittura e US5 lo rendono
azionabile come gate. Re-index reale e wiring fisico dell'hook restano fuori (FEAT-009 / setup governance).
