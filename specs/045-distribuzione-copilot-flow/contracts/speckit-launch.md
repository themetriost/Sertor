# Contract — Lancio dell'installer di spec-kit (`sertor-flow.speckit.launch/1`)

Sostituisce il vendoring di SpecKit. Confinato in `speckit_launch.py`, dietro il `CommandRunner` del kit.

## Comportamento

| Caso | Condizione | Esito |
|---|---|---|
| **Disponibile** | l'installer di spec-kit è eseguibile | esegue `specify init --ai <assistant> --script <ps\|sh>` a versione pinnata → deposita comandi/agenti SpecKit + `.specify/` |
| **Layout verificato** | dopo il lancio, le superfici attese per l'assistente esistono | `created` |
| **Già presente** | le superfici SpecKit esistono già (re-run) | `skipped` (idempotenza, non ri-lancia) |
| **Assente / non eseguibile** | `specify`/`uvx` non disponibile o comando fallito | **`InstallerError` fail-fast**, messaggio azionabile (come installare/eseguire manualmente), **nessuno stato parziale** |
| **Layout inatteso** | dopo il lancio mancano superfici attese | **`InstallerError`** esplicito |

## Invarianti

- **install ≠ run**: deposita file, non avvia ingestione né fasi SpecKit.
- **non distruttivo / idempotente**: non sovrascrive file utente; re-run → skip.
- **versione pinnata**: deterministico; la versione è config (Principio VIII), non hardcoded sparso.
- **testabile senza rete**: `CommandRunner` mockato; il mock simula sia il successo (emette il layout
  atteso) sia i fallimenti (assente/fallito/layout inatteso).
- **no dipendenza da `sertor-core`**.

## Proprietà verificabili (test)

1. lancio con assistant=claude → comando con `--ai claude`; layout Claude → `created`.
2. lancio con assistant=copilot → comando con `--ai copilot`; layout Copilot → `created`.
3. runner segnala assenza → `InstallerError` con istruzioni; nessun file scritto.
4. comando fallito / layout mancante → `InstallerError`.
5. superfici già presenti → `skipped` (no secondo lancio).
