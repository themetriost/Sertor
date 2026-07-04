# Contract — `scripts/dev/relock-runtime.ps1`

Contratto CLI dello script dogfood-only. Deterministico, check-then-act, fail-loud.

## Invocazione

```powershell
.\scripts\dev\relock-runtime.ps1            # check-then-act (default)
.\scripts\dev\relock-runtime.ps1 -WhatIf    # solo check + report, nessuna mutazione (dry-run)
```

Eseguito dalla **root del repo** (dove vivono `.sertor/` e `.git/`). Nessun altro argomento richiesto.

## Comportamento (check-then-act)

1. **Preflight (fail-loud):** verifica che `uv` sia sul PATH e che `.sertor/pyproject.toml` esista. In caso
   contrario → messaggio azionabile + `exit 2` (setup mancante: F1 non eseguita o `uv` assente).
2. **Fetch:** `git fetch origin master --quiet` (aggiorna il ref remoto; fail-loud su errore rete → `exit 3`).
3. **Check:** estrae lo SHA lockato da `.sertor/uv.lock` (regex `Sertor\.git#([0-9a-f]+)`) e lo confronta con
   `git rev-parse origin/master`.
   - **Uguali** → stampa `runtime già a HEAD (<sha7>): no-op` e `exit 0`.
   - **Diversi o lock assente** → procede al re-lock.
4. **Re-lock (solo se behind):** `uv lock --upgrade-package sertor-core --project .sertor` poi
   `uv sync --project .sertor`. Fail-loud su errore (rete/risoluzione/sync) → messaggio azionabile + `exit 3`;
   non lascia un runtime parziale spacciato per aggiornato.
5. **Report:** stampa `re-lock: <old_sha7> -> <new_sha7>` e `exit 0`.

## Exit codes

| Code | Significato |
|---|---|
| `0` | successo — runtime a HEAD (no-op) **o** re-lock completato |
| `2` | preflight fallito (`uv` assente o `.sertor/pyproject.toml` mancante) — setup |
| `3` | operazione fallita (rete/`git fetch`/`uv lock`/`uv sync`) — fail-loud, runtime resta all'ultimo lock |

## Invarianti

- **Solo vehicle:** usa `uv` e `git`, mai `python -c "import sertor_core…"` (Principio XI).
- **Non-distruttivo oltre il runtime:** tocca solo `.sertor/uv.lock` e `.sertor/.venv/`; nessun file utente.
- **Dogfood-only:** vive in `scripts/dev/`, non è bundlato da alcun installer; assente dagli asset distribuiti.
- **`-WhatIf`:** esegue preflight + fetch + check e riporta l'azione che *farebbe*, senza eseguire re-lock.
