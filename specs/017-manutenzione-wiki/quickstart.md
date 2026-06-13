# Quickstart — Verifica feature 017 (manutenzione wiki)

**Data**: 2026-06-13 · **Branch**: `017-manutenzione-wiki`

Tutto offline, senza LLM (parte D del confine D↔N).

## SC-001/002/003/004 — `move`

Su un wiki di prova con pagine che si linkano:
```
sertor-wiki-tools move concepts/a.md experiments/a.md --dry-run   # piano, 0 file modificati
sertor-wiki-tools move concepts/a.md experiments/a.md             # esegue
sertor-wiki-tools lint --json                                     # 0 broken_links aggiuntivi
```
Verifiche: il file è nella nuova sede; ogni `[[a]]`/`[[concepts/a]]`/link relativo entrante punta alla
nuova sede (alias preservati); con `--dry-run` nessun file cambia; destinazione già esistente (con
sorgente presente) → errore, 0 modifiche; spostamento interrotto e rieseguito → stato finale identico.

## SC-005/007 — `reconcile`

```
sertor-wiki-tools reconcile --json
```
Con alcune pagine `status: superseded` → le elenca tutte e sole (path/updated/superseded_by/reason),
0 file modificati. Senza pagine superate → `candidates=[] clean=true`, exit 0.

## SC-006 — `collect` + `status`

```
sertor-wiki-tools collect --json
```
Le pagine con `status` nel frontmatter lo espongono nei metadati; un consumatore che conosce solo
`schema` continua a leggere il risultato.

## SC-008 / gruppo D — offline + trigger periodico

Tutti i comandi girano senza rete/LLM. Per il report periodico (Could), esempio di delega allo
scheduler dell'ospite (nessuno scheduler nel prodotto):
```
# cron / Task Scheduler / hook CI:
sertor-wiki-tools reconcile --json > reports/wiki-obsolete-$(date +%F).json
```
