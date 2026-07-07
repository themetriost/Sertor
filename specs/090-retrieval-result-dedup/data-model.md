# Data model — dedup risultati (Phase 1)

Nessuna nuova entità di dominio persistita. Il «modello» è la funzione pura + la chiave + la manopola.

## Funzione pura

```text
dedup_results(results: list[RetrievalResult]) -> tuple[list[RetrievalResult], int]
```

- **Input:** lista di `RetrievalResult` **già ordinata** per rilevanza (rank), tipicamente un pool `P ≥ k`.
- **Output:** `(deduped, removed)` — la lista senza duplicati (ordine preservato) e il numero di rimossi.
- **Purezza:** nessun I/O, nessuna dipendenza da `Settings` (il *se* è al call-site).

## Chiave di dedup

- `key(r) = sha1( normalize(r.text) )` dove `normalize` = collasso del whitespace (sequenze di spazi/tab/
  newline → singolo spazio) + trim, **case-preserving**, encoding UTF-8.
- Due risultati con la **stessa chiave** sono un **gruppo di duplicati**. Nel gruppo sopravvive la **prima**
  occorrenza nell'ordine d'ingresso (= rank più alto).

## Entità di riferimento

| Entità | Campi rilevanti | Ruolo nella dedup |
|--------|-----------------|-------------------|
| `RetrievalResult` | `text` (base della chiave), `score`, `chunk_id`, `path` | l'unità deduplicata |
| Gruppo di duplicati | chiave condivisa | ne sopravvive 1 (rank più alto) |
| `Settings.dedup_enabled` | `bool`, default `True` (`SERTOR_DEDUP`) | abilita/disabilita al call-site |

## Invarianti (i «test» del modello)

- **INV-1 (collasso):** N risultati con chiave identica → **1** nel risultato (rank più alto). *(SC-001)*
- **INV-2 (no-op):** input senza duplicati → output **identico** all'input (stesso ordine, stessi elementi).
  *(US1.3 / SC-004 no regressione)*
- **INV-3 (determinismo):** stesso input → stesso output; tie-break ereditato dall'ordine `(-score, chunk_id)`
  già stabile. *(Principio VI)*
- **INV-4 (conteggio):** `len(input) == len(deduped) + removed`. *(FR-008, osservabilità)*
- **INV-5 (bypass):** con `dedup_enabled=False` il call-site NON invoca la dedup → risultati pre-feature.
  *(SC-003)*
