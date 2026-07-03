# Implementation Plan — Installer preservante su `plan-template.md` (E15-FEAT-005 ≡ E10-FEAT-028)

**Date:** 2026-07-03 | **Spec:** [spec.md](./spec.md) | **Meccanismo:** (a) backup/restore (utente)

## Summary
In `execute_governance_plan` (`packages/sertor-flow/src/sertor_flow/install_governance.py`), **avvolgere** lo
Step 0 (`launch_speckit`, che via `specify init --force` clobbera `plan-template.md`) con un **backup/restore**:
leggi il `plan-template.md` esistente **prima**, ripristinalo **dopo** se era presente. Host-agnostico, zero
`sertor-core`.

## Technical Context
Python 3.11, stdlib (`pathlib`). Tocca **solo** `packages/sertor-flow` (installer). Test: `pytest` offline col
`FakeSpecifyRunner` esistente (già clobbera il plan-template). Nessuna dipendenza nuova.

## Constitution Check
- **I/II/XI** PASS (N/A core; è codice installer, non `sertor_core`). **III** PASS — cambiamento minimo
  (avvolge una call), nessuna astrazione nuova. **IV/XII** PASS — se il restore fallisce, l'errore emerge
  (fail-fast), mai lasciare il vanilla in silenzio. **V** PASS — test offline col fake fedele. **VI** PASS —
  restore idempotente (no-op se invariato). **X** PASS — preserva *ciò che c'è*, nessuna versione
  Sertor-specifica imposta. **VIII/VII/IX** PASS/N/A. **Missione** PASS (periferico: prerequisito del modello
  install-based). **12/12. Complexity Tracking vuoto.**

## Design (mechanism (a))
In `execute_governance_plan`, attorno a `launch_speckit` (righe 315-327):
```
plan_tpl = root / ".specify/templates/plan-template.md"
preserved = plan_tpl.read_bytes() if plan_tpl.is_file() else None      # backup PRIMA
launch_outcome = launch_speckit(profile, runner)                       # Step 0 (clobbera)
if preserved is not None and plan_tpl.read_bytes() != preserved:       # restore DOPO
    plan_tpl.write_bytes(preserved)
    report.add(ArtifactOutcome(".specify/templates/plan-template.md", Outcome.UPDATED,
                               "preserved host customization across specify init --force"))
```
- **Fresh host** (`preserved is None`): nessun restore → resta l'upstream (REQ-003).
- **Fail-loud** (REQ-005): un errore di I/O nel restore propaga (fail-fast, come il resto dell'installer).
- **Report onesto** (NFR-3): l'esito compare in `InstallReport`.
- **Upgrade:** verificare se `_apply_gov_upgrade` **ri-lancia** `specify init`; se sì, applicare lo stesso
  wrap (altrimenti l'upgrade non clobbera → nessuna azione).

## Project Structure (paths reali)
```text
packages/sertor-flow/src/sertor_flow/install_governance.py   # + backup/restore attorno a launch_speckit
packages/sertor-flow/tests/…                                 # + test: plan-template customizzato preservato
```
**Structure Decision:** nessun `sertor-core`. Solo installer `sertor-flow` + un test.

## Complexity Tracking
*(vuoto)*

## Note
Il `FakeSpecifyRunner` già clobbera il plan-template (`conftest.py:72-75`) → il test pre-piazza un
`plan-template.md` **customizzato** (contenuto distinto dal mock del fake) e asserisce che post-install è
**byte-identico** al customizzato. + un test «fresh host» (nessun plan-template pre-esistente → resta il mock).
