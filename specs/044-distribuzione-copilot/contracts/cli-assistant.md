# Contract — CLI `sertor install … --assistant` (`sertor.install.assistant/1`)

Contratto della superficie CLI dell'installer rispetto alla scelta dell'assistente target. Estende i
comandi esistenti `sertor install wiki` / `sertor install rag` (non li sostituisce).

## Opzione

```
sertor install <wiki|rag> [--assistant <claude|copilot>] [altre opzioni esistenti]
```

- `--assistant` è **opzionale**. Assente → default **`claude`** (documentato, FR-002).
- Valore non in `{claude, copilot}` → **errore esplicito** (exit ≠ 0) con messaggio azionabile che
  elenca i valori validi (Principio IV). `codex` NON è valido in questa feature.
- L'opzione è accettata da **entrambe** le capacità (`wiki`, `rag`).

## Comportamento (post-condizioni)

| Dato | Quando | Allora |
|---|---|---|
| `--assistant copilot` | install `rag` | server `sertor-rag` registrato in `.vscode/mcp.json` (chiave `servers`); parte non segreta senza editing manuale (FR-004/005) |
| `--assistant copilot` | install `wiki` | blocco istruzioni in `.github/copilot-instructions.md`; comandi wiki in `.github/prompts/`; agente in `.github/agents/`; hook in `.github/hooks/` (FR-008…012) |
| `--assistant copilot` | install `rag` | hook anti-bypass Principio XI reso lato Copilot, non bloccante/fail-open (FR-013) |
| qualunque assistente | sempre | nessuna ingestione automatica (install ≠ run, FR-018); non distruttivo su file utente (FR-017); idempotente (FR-020); segreti non versionati (FR-006) |
| qualunque assistente | sempre | le CLI `sertor-rag`/`sertor-wiki-tools` restano identiche: nessuna variante per-assistente (FR-019) |

## Report

Il report d'installazione **dichiara l'assistente target** e, per ogni Surface in ambito, l'esito
(creato/merge/skip/block) oppure un **gap esplicito** se priva di resa sull'assistente (FR-015/016). Mai
omissione silenziosa.

## Non-obiettivi

- Non introduce comandi nuovi né varianti per-assistente delle CLI di esecuzione.
- Non installa le superfici di governance/SpecKit (pacchetto `sertor-flow` → FEAT-009).
- Non supporta `codex` né client Copilot diversi da VS Code agent mode (fuori taglio).
