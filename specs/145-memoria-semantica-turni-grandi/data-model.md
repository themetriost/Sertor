# Data model — 145 memoria semantica: turni grandi e rifiuti del provider

Estende le entità della 072 (`specs/072-ricerca-semantica-memoria/data-model.md`); non ne introduce di
nuove nel `domain/`: tutto vive in `services/memory_semantic.py`, come le entità della 072.

## `RejectedTurn` (nuova, frozen dataclass)

```
RejectedTurn:
  session_key: str   # sessione del turno rifiutato
  turn_index: int    # indice del turno nella sessione
  reason: str        # motivo dal provider, es. "http 400" (mai testo del transcript)
```

## `SemanticIndexReport` (estesa)

```
SemanticIndexReport:
  embedded: int = 0                          # TURNI indicizzati (non pezzi) — significato invariato
  skipped: int = 0                           # turni già interamente indicizzati
  errors: int = 0                            # turni non indicizzati (rifiutati + guasti)
  rejected: tuple[RejectedTurn, ...] = ()    # NUOVO: dettaglio dei turni rifiutati (⊆ errors)
```

Invariante: `len(rejected) <= errors`; `errors − len(rejected)` sono i turni persi per provider o store
non disponibili (il motivo è nell'evento). I costruttori esistenti (`SemanticIndexReport(embedded=…,
skipped=…, errors=…)`) restano validi.

## Unità indicizzata (record nello store)

| Turno | `chunk_id` | payload |
|---|---|---|
| entro il budget | `f"{session_key}#{turn_index}"` (**invariato**) | `text, session_key, turn_index, captured_at, role` (**invariato**) |
| oltre il budget, pezzo `p` di `n` | `f"{session_key}#{turn_index}/{p}"` | come sopra con `text` = testo del pezzo, **+** `part=p`, `parts=n` |

- Pezzi da `cap_to_tokens(turn.text, settings.max_chunk_tokens, settings.chunk_overlap)`: ciascuno
  ≤ `max_chunk_tokens`. Un turno con un solo pezzo usa la riga «entro il budget».
- «Già indicizzato» ⇔ tutti i `chunk_id` del turno presenti (`contains_ids`).
- Tutto o niente per turno: i pezzi di un turno rifiutato non vengono scritti.

## Stati di un turno in un run

```
nuovo ──embed batch ok──────────────────────────▶ indicizzato (embedded)
  │
  ├─batch rifiutato (400/413/422) ─▶ ripiego per pezzo ─┬─ tutti ok ─▶ indicizzato
  │                                                      ├─ un pezzo rifiutato ─▶ rifiutato (errors + rejected)
  │                                                      └─ errore ritentabile ─▶ errore (provider_unavailable)
  └─batch: altro errore ──────────────────────────▶ errore (provider_unavailable, come oggi)
già presente ─────────────────────────────────────▶ saltato (skipped)
```

Un turno rifiutato o in errore non lascia tracce nello store: al run successivo è di nuovo «nuovo».
