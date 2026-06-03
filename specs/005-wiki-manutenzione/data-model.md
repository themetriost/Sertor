# Phase 1 — Data Model: manutenzione del wiki

Entità di FEAT-007 (in `src/sertor_core/wiki/maintenance.py`). Riusa le convenzioni di FEAT-003.

## Issue (problema rilevato dal lint)
| Campo | Tipo | Note |
|-------|------|------|
| `kind` | `enum {broken_link, orphan, index_missing, coverage_missing, contradiction}` | tipo di problema |
| `page` | `str` | path relativo della pagina coinvolta (o area, per coverage) |
| `detail` | `str` | dettaglio (es. target del link rotto, area mancante) |

## LintReport (esito del lint)
| Campo | Tipo | Note |
|-------|------|------|
| `issues` | `list[Issue]` | problemi tipizzati |
| `pages` | `int` | pagine analizzate |
| `ok` | `bool` (proprietà) | **pass** se non ci sono issue bloccanti → guida il **gate** |

Reso anche in forma leggibile; `ok=False` → exit ≠ 0 a livello di gate/CLI futuro.

## CoverageRequirement (set atteso — input configurabile)
| Campo | Tipo | Note |
|-------|------|------|
| `area` / `path` | `str` | pagina/area attesa (es. `syntheses/architettura.md`, o "una pagina per feature") |

`expected: list[...]` con default ragionevole; override via config/parametro (DA-7).

## Blocco catalogo (in `index.md`)
Regione gestita tra `CATALOG_BEGIN` (`<!-- sertor:catalog -->`) e `CATALOG_END`
(`<!-- /sertor:catalog -->`); contiene una riga per pagina (`- [[slug]] — sommario`). Rigenerata in
modo idempotente; il resto di `index.md` è preservato.

## Pagina di documentazione (distillata)
Pagina wiki conforme (frontmatter, kebab-case, cartella tematica) con **backlink** alla fonte in
`sources` (path relativo dell'artifact) + riga di rimando; **non** duplica il contenuto della fonte.

## Riuso / estensioni
- Riusa `Brief`, `WikiArea`, `render_page`, `slugify`, `page_relpath`, `_write_page_if_changed` (FEAT-003).
- Estende `conventions.py` con i marcatori del catalogo e un helper "rimpiazza blocco gestito".
- `distill_artifact` (in `distill.py`) riusa la porta `LLMProvider` e la logica non-distruttiva.

## Relazioni
```text
lint(root, expected) ─> LintReport(issues[], pages, ok)        [US1/US2/US5]
regenerate_index(root) ─> aggiorna blocco catalogo (idempotente, non distruttivo)  [US3]
lint(root, fix=True) ─> regenerate_index (unico fix sicuro)    [US3/DA-4]
distill_artifact(root, source, kind, title, llm) ─> pagina doc + backlink (crea-se-assente)  [US4]
```
