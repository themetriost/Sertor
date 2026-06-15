# Contract — CLI `sertor-flow install --assistant` (`sertor-flow.install.assistant/1`)

Estende il comando `sertor-flow install` con la scelta dell'assistente target (riuso del meccanismo
FEAT-007).

## Opzione

```
sertor-flow install [--assistant <claude|copilot>] [--target <path>] [--json] [opzioni esistenti]
```

- `--assistant` opzionale; assente → default **`claude`** (allineato a FEAT-007).
- Valore non in `{claude, copilot}` → errore esplicito (exit ≠ 0), valori validi elencati. `codex` non
  valido in questa feature.

## Post-condizioni

| Dato | Quando | Allora |
|---|---|---|
| `--assistant copilot` | install | SpecKit ottenuto via `specify init --ai copilot` (comandi `.github/prompts/`, agenti `.github/agents/`, `.specify/` condiviso) |
| `--assistant copilot` | install | superfici Sertor-authored rese per Copilot (agenti `.github/agents/*.agent.md`, skill `.github/prompts/`), blocco SDLC in `.github/copilot-instructions.md` |
| `--assistant claude` | install | governance **funzionalmente equivalente** a oggi (non-regressione, FR-012), ora ottenuta via launch invece che vendoring |
| qualunque | sempre | costituzione-starter identica; install ≠ run; non distruttivo; idempotente; **no dipendenza da `sertor-core`** |
| spec-kit assente/non eseguibile | install | **fail-fast** esplicito, nessuno stato parziale (FR-004) |

## Report

Dichiara assistente target, esito del **launch** di spec-kit (versione, assistant), e per ogni superficie
Sertor-authored l'esito o un **gap esplicito**. Mai omissione silenziosa.
