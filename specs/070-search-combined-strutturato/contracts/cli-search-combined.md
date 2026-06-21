# Contract — CLI `sertor-rag search --type both` (070, DA-d)

`src/sertor_core/cli/__main__.py` (`_cmd_search`) + `src/sertor_core/cli/output.py`
(`format_search_results`). Cambia la resa del solo `--type both`; `code`/`docs` invariati.

## Comportamento

| `--type` | Sorgente | Resa |
|---|---|---|
| `code` | `facade.search_code` | una sezione (invariato) |
| `doc`  | `facade.search_docs` | una sezione (invariato) |
| `both` | `facade.search_combined` → `FusedResults` | **due sezioni etichettate** `docs` / `code` |

## Resa umana (`--type both`)

```
docs:
  <risultati doc, formato esistente>

code:
  <risultati code, formato esistente>
```

- Ciascuna sezione resa con la logica `format_search_results` esistente (no duplicazione, Principio
  III/VII), preceduta dall'etichetta del flusso.
- Una sezione senza risultati → etichetta + riga «(nessun risultato)» (degrado onesto, niente
  silenzio).

## Resa JSON (`--type both --json`)

```json
{ "docs": [ {…} ], "code": [ {…} ] }
```

Gemello del MCP (forma etichettata). `code`/`doc` mono-tipo restano la lista JSON odierna.

## Invarianti

- Il path strict (`build_baseline_engine().ensure_index()` → `IndexNotFoundError` su indice assente)
  resta per ogni `--type` (FR-012, invariato).
- Formato citabile `path#chunk` preservato.

## Test attesi

- `_cmd_search` con `--type both` consuma `FusedResults` e stampa le due sezioni; `--json` produce
  `{"docs":…,"code":…}`.
- `--type code`/`--type doc` invariati (stesso output di prima) — SC-002.
