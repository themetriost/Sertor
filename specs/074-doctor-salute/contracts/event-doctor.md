# Contract — Observability event `doctor` (E12-FEAT-001)

Gemello di `eval` (`services/eval/runner.py:34`). **Metrics-only** (Principio IX): mai testo libero,
chiavi env, valori, sentinella del probe, path o motivi d'errore. Emesso una volta per invocazione,
catturato dallo store solo se `SERTOR_OBSERVABILITY=true` (handler già cablato da
`enable_observability`).

## Campi

| Campo | Tipo | Note |
|-------|------|------|
| `overall` | str | `pass` \| `warn` \| `fail` |
| `online` | bool | il flag `--online` era attivo |
| `n_fail` | int | aree con esito `fail` |
| `n_warn` | int | aree con esito `warn` |
| `n_pass` | int | aree con esito `pass` |
| `areas` | str | etichette area→esito compatte (es. `config=pass,provider=pass,index=warn,mcp=pass`) — **cardinalità chiusa**, nessun dato libero |

## Vietato (RNF-4/FR-013)

Nomi di chiavi env, valori, la stringa sentinella del probe, motivi d'errore del provider, path
dell'indice, `--corpus`. La privacy è garantita per costruzione: l'evento porta solo conteggi ed
etichette a cardinalità chiusa.
