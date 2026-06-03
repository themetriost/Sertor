# Quickstart — manutenzione del wiki (FEAT-007)

Funzioni di libreria (l'esposizione CLI `sertor wiki …` è una feature successiva).

## Lint (report di igiene + coperture) — sola lettura
```python
from sertor_core.wiki.maintenance import lint

report = lint("repo/wiki", expected=["syntheses/architettura.md"])
print(report.ok, f"{len(report.issues)} problemi su {report.pages} pagine")
for i in report.issues:
    print(i.kind, i.page, i.detail)
```
Non scrive nulla. `report.ok` è l'esito **pass/fail** del gate.

## Gate a fine feature
```python
import sys
sys.exit(0 if lint("repo/wiki").ok else 1)   # non interattivo, idempotente, veloce
```
Da agganciare a un hook di fase / CI (meccanismo = design, DA-8).

## Rigenerare l'indice (idempotente, non distruttivo) / fix
```python
from sertor_core.wiki.maintenance import regenerate_index
regenerate_index("repo/wiki")          # aggiorna solo il blocco tra marcatori
lint("repo/wiki", fix=True)            # lint + unico fix sicuro (= rigenera indice)
```

## Distillare un artifact in documentazione ufficiale (con LLM)
```python
from sertor_core.wiki.distill import distill_artifact
from sertor_core.composition import build_llm

distill_artifact("repo/wiki", source="specs/001-nucleo-retrieval/spec.md",
                 kind="synthesis", title="Architettura del nucleo", llm=build_llm())
```
Crea la pagina se assente, con **backlink** alla fonte; **non** sovrascrive una pagina curata a mano;
senza LLM → `LLMNotConfiguredError`.

## Verifica (accettazione)
| Verifica | Atteso | Criterio |
|----------|--------|----------|
| lint su wiki con problemi | issue elencate, nessuna scrittura | SC-001 |
| re-run | esito identico | SC-002 |
| regenerate_index | resto di index.md intatto | SC-003 |
| distill_artifact | pagina con backlink, non sovrascrive il curato | SC-004 |
| contraddizioni marcate | elencate | SC-005 |
| gate | pass/fail non interattivo | SC-006 |
