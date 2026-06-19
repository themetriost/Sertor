# Tasks: Distribuzione corretta della costituzione neutra + rifinitura principi

**Branch**: `058-distribuzione-costituzione` · **Plan**: `specs/058-distribuzione-costituzione/plan.md`

Ordine TDD: prima la guardia (fallisce sul comportamento attuale), poi il fix finché passa. `[P]` =
parallelizzabile (file distinti).

## Fase 1 — Foundational: guardia di distribuzione (definisce il "done")

- **[ ] T001** — `packages/sertor-flow/tests/.../test_constitution_distribution.py`: con un
  `.specify/memory/constitution.md` **placeholder** (fixture con `[PROJECT_NAME]`/`[PRINCIPLE_1_NAME]`)
  pre-creato in tmp, eseguire il flusso governance (con `specify init` **mockato** che lascia il
  placeholder) e verificare che il file finale sia lo **starter neutro** (0 sentinelle).
- **[ ] T002** — Stesso test con una **costituzione reale** (fixture senza sentinelle) → DEVE essere
  **preservata** byte-per-byte.
- **[ ] T003** — Test-of-test del predicato `_is_speckit_placeholder`: positivo sulle sentinelle, negativo
  su starter/costituzione reale. *Atteso ora:* T001 **FALLISCE** sul codice attuale (skip del placeholder).

## Fase 2 — US1 (P1): replace-if-placeholder

- **[ ] T010** — In `install_governance.py`: `_SPECKIT_PLACEHOLDER_SENTINELS` + `_is_speckit_placeholder`
  (puro) + helper `_apply_constitution(dest, starter_text, dry_run=False)` con la logica
  CREATED/UPDATED/SKIPPED-preserved del plan §Phase 1.
- **[ ] T011** — `_apply_config` (install) → delega a `_apply_constitution` (gira dopo `specify init`).
- **[ ] T012** — `_apply_gov_upgrade` ramo costituzione → delega a `_apply_constitution` (con `dry_run`),
  invece del `SKIPPED "preserved"` fisso; una costituzione reale resta preservata.
- **Checkpoint:** T001/T002/T003 verdi.

## Fase 3 — US2 (P2): rifinitura starter

- **[ ] T020** — Riscrivere `assets/constitution-starter.md`: + «Replaceable Details / No Vendor Lock-In»
  (kernel II) + «Consume Through Stable Interfaces, Not Internals» (gen. XI) + allineamento leggibilità
  (guard-clause/SESE); bump versione 0.1.0 → 0.2.0; nessun principio Sertor/RAG-specifico; nota
  d'intestazione preservata.
- **[ ] T021** — Test starter: contiene i due nuovi principi; **0** sentinelle placeholder; **0** termini
  Sertor/RAG (`sertor-rag`, `host-agnostic`-framework, RAG/hit@k) nel corpo.

## Fase 4 — US3 (P2): non-regressione + verifica

- **[ ] T030** — Suite `sertor-flow` + `kit` + `sertor` verdi; guard no-dipendenza `sertor-flow`→`sertor-core`
  verde; ruff pulito sui file toccati.
- **[ ] T031** — Verifica empirica: install governance in dir temp con placeholder pre-creato → starter
  neutro depositato (CS-005); spot-check upgrade (placeholder→starter, reale→preservata).
- **[ ] T032** — Bookkeeping: aggiornare CLAUDE.md (rif. piano), record/log wiki, EXEC roadmap; PR.

## Criteri di completamento (mappano gli SC)

SC-001 T011/T031 · SC-002 T002/T012 · SC-003 T020/T021 · SC-004 T030 · SC-005 T031.
