# Data Model — E15-FEAT-008

Feature di tooling: nessuna entità di dominio persistita. Le «entità» sono gli artefatti e il loro stato.

## Artefatti e stato di tracking

| Artefatto | Ruolo | Tracking git (post-feature) |
|---|---|---|
| `.sertor/pyproject.toml` | spec **stabile** del runtime (dep `sertor-core` da `git=<repo>`, no rev pin) | **tracciato** (invariato) |
| `.sertor/uv.lock` | lock **volatile** — registra il commit risolto (`…Sertor.git#<SHA>`) | **gitignorato + untracked** (era tracciato in F1) |
| `.sertor/.venv/` | runtime installato | gitignorato (già) |
| `scripts/dev/relock-runtime.ps1` | passo di re-lock check-then-act | **tracciato** (nuovo) |
| `tests/unit/test_relock_runtime_dogfood.py` | guardia di regressione | **tracciato** (nuovo) |

## Stato del runtime (rispetto a `origin/master`)

Derivato, non persistito — calcolato dallo script ad ogni invocazione:

- **`current`**: SHA lockato (`.sertor/uv.lock`) == `git rev-parse origin/master` → azione = **no-op**.
- **`behind`**: SHA lockato != HEAD, oppure lock/venv assente → azione = **re-lock** (`uv lock --upgrade-package
  sertor-core --project .sertor` + `uv sync --project .sertor`).
- **`error`**: `uv`/progetto `.sertor/` assenti o rete/risoluzione falliti → azione = **exit non-zero
  azionabile** (fail-loud), nessuna mutazione parziale spacciata per ok.

## Transizioni

```
[behind] --relock--> [current]      (successo)
[current] --relock--> [current]     (no-op)
[behind|current] --relock--> [error --> exit≠0]   (uv/git/rete falliti; runtime resta all'ultimo lock valido)
```
