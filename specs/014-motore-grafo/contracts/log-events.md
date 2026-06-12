# Contract — Eventi di log del motore a grafo

Emessi via `log_event` esistente (redazione segreti inclusa, FR-028). Schema additivo: gli
eventi esistenti NON cambiano.

## `graph_build` (INFO) — FR-026

Una emissione per ogni costruzione del grafo (dentro `index()`).

| Campo | Tipo | Esempio |
|---|---|---|
| `corpus` | str | `sertor` |
| `graph_path` | str | `.index-sertor/graph/sertor.json` |
| `nodes_by_kind` | dict | `{"module": 60, "class": 35, "function": 180, "method": 240, "doc": 90}` |
| `edges_by_type` | dict | `{"contains": 450, "calls": 320, "imports": 110, "inherits": 12, "mentions": 600}` |
| `elapsed_ms` | float | `850.4` |

## `graph_query` (INFO) — FR-027

Una emissione per ogni operazione di navigazione.

| Campo | Tipo | Esempio |
|---|---|---|
| `operation` | str | `who_calls` |
| `symbol` | str | `build_facade` |
| `results` | int | `3` |
| `elapsed_ms` | float | `2.1` |

## Vincoli

- Nessun campo segreto; `redact` si applica comunque.
- Campi sufficienti a diagnosticare senza leggere il codice (Principio IX): un build con
  `edges_by_type.calls == 0` su un corpus Python è immediatamente sospetto.
