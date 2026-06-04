# Quickstart — Lint semantico del wiki (FEAT-007 estensione)

Funzioni di libreria del core (esposizione CLI in feature successiva).

## Rilevazione semantica (richiede LLM)
```python
from sertor_core.wiki.semantic import semantic_lint, Severity
from sertor_core.composition import build_llm, build_facade

report = semantic_lint("wiki", llm=build_llm(), facade=build_facade(),
                       threshold=Severity.HIGH, max_pages=None)
print(report.render())
print("OK" if report.ok else "FAIL", f"— {report.pages_checked}/{report.pages_total} pagine, "
      f"{report.llm_calls} chiamate LLM")
for i in report.issues:
    print(i.severity, i.kind, i.page, "—", i.claim[:80])
```
Senza LLM (`llm=None`) il report è **`skipped=True`** e non solleva errori; il lint **strutturale**
(`wiki.maintenance.lint`) resta operativo.

## Provenienza
```python
from sertor_core.wiki.conventions import read_provenance, mark_provenance
read_provenance(text)            # "generated" | "curated" (default curated)
text = mark_provenance(text, "generated")
```
`distill_artifact(...)` marca automaticamente le pagine prodotte come `generated`.

## Proposte di correzione (solo pagine generate)
```python
from sertor_core.wiki.semantic import propose_fixes
proposals = propose_fixes(report, "wiki", llm=build_llm())   # nessuna scrittura
for p in proposals:
    print(p.action, p.page, "—", p.rationale)
```

## Verifica incrementale git-driven (US3)
```python
from sertor_core.wiki.semantic import semantic_lint_incremental
from sertor_core.wiki.conventions import read_watermark, write_watermark
from sertor_core.adapters.git import SubprocessGitAdapter   # adapter fuori dal dominio

git = SubprocessGitAdapter(repo_root=".")
report = semantic_lint_incremental("wiki", llm=build_llm(), facade=build_facade(), git=git,
                                   watermark_path="wiki/.sertor/semantic-watermark",
                                   threshold=Severity.HIGH)
print(report.mode, report.fallbacks)          # "incremental" | "baseline" ; es. ["stale-index"]
if report.mode == "incremental":
    print("pagine ri-verificate:", report.pages_checked)
# a fine run completato il chiamante persiste il watermark:
if not report.skipped and report.ok:
    write_watermark("wiki", git.head_commit())
```
Senza watermark → **baseline completo** (REQ-087); senza git/working-tree → fallback baseline
**segnalato** in `report.fallbacks` (REQ-091). FEAT-009 assente → `fallbacks` include `"stale-index"`
(re-index reale inattivo, REQ-096/097).

## Auto-fix: applicazione su working tree (US4-scrittura, solo pagine generated)
```python
from sertor_core.wiki.semantic import apply_fixes
applications = apply_fixes(proposals, "wiki", dry_run=True)   # prova senza scrivere
for a in applications:
    print(a.outcome, a.page, "—", a.detail)   # applied | deleted | refused_curated | skipped_no_match
# applicazione reale (diff revisionabile via git):
apply_fixes(proposals, "wiki")
```
Le pagine **curated** sono sempre **rifiutate** (`refused_curated`); la riscrittura è **chirurgica**
(solo la claim) e la pagina riscritta **resta generated**.

## Gate pre-commit/pre-push (US5 — fuori dal dominio, layer CLI/hook)
```python
# entrypoint del gate (CLI/services), NON nel core:
from sertor_core.services.semantic_gate import run_semantic_gate
outcome = run_semantic_gate("wiki", llm=build_llm(), facade=build_facade(), git=git,
                            threshold=Severity.HIGH,
                            override=False)            # override esplicito = flag --override / env
print(outcome.status)                                  # pass | warning | blocked
import sys; sys.exit(0 if outcome.status != "blocked" else 1)
```
Equivalente CLI (trigger a monte del configuration-manager, REQ-092):
```bash
sertor wiki semantic-gate --threshold high            # exit≠0 se blocked
sertor wiki semantic-gate --override --reason "hotfix" # procede e REGISTRA l'override (REQ-095)
```

## Verifica (accettazione)
| Verifica | Atteso | Criterio |
|----------|--------|----------|
| pagina obsoleta vs codice | issue `obsolete` con la claim | SC-001 |
| nessun LLM | report skipped, strutturale ok | SC-002 |
| pagina curated | nessuna proposta/scrittura | SC-003 |
| re-run invariato (LLM deterministico) | stesse issue | SC-004 |
| run sul wiki di produzione | report leggibile con obsolescenze/lacune reali | SC-005 |
| watermark + change set su 1 pagina | incrementale verifica **solo** quella pagina | SC-006 |
| rewrite su generated | diff chirurgico, pagina resta generated | SC-007 |
| gate sopra soglia / override | exit≠0 se blocked; procede e registra se override | SC-008 |
