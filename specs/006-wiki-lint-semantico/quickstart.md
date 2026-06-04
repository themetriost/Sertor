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

## Gate (pass/fail)
```python
import sys
sys.exit(0 if report.ok else 1)   # blocca sopra soglia (override esplicito nella fase pre-commit)
```

## Verifica (accettazione)
| Verifica | Atteso | Criterio |
|----------|--------|----------|
| pagina obsoleta vs codice | issue `obsolete` con la claim | SC-001 |
| nessun LLM | report skipped, strutturale ok | SC-002 |
| pagina curated | nessuna proposta di modifica | SC-003 |
| re-run invariato (LLM deterministico) | stesse issue | SC-004 |
| run sul wiki di produzione | report leggibile con obsolescenze/lacune reali | SC-005 |
