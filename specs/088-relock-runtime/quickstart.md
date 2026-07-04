# Quickstart — re-lock del runtime `.sertor/` a HEAD (E15-FEAT-008)

## Cos'è

Il runtime del dogfood (`.sertor/`) installa `sertor-core` da `git=<repo>` **HEAD**, ma il lock fissa il
commit. Dopo un merge su `master` il runtime resta indietro. Questo passo lo riallinea, in modo meccanico.

## Uso (rituale post-merge)

Dopo aver mergiato una PR su `master` (e col merge pushato su `origin`):

```powershell
.\scripts\dev\relock-runtime.ps1
```

- Se il runtime è già a HEAD → **no-op** (stampa e basta).
- Se è indietro → **re-lock** (`uv lock --upgrade-package sertor-core --project .sertor` + `uv sync`) verso
  l'HEAD di `origin/master`, e lo riporta (`re-lock: <old> -> <new>`).
- Dry-run: `.\scripts\dev\relock-runtime.ps1 -WhatIf`.

Poi prosegui il rituale post-merge: **re-index** del corpus (hook SessionEnd o `uv run sertor-rag index .`) e
**smoke MCP**. Il re-lock va **prima**, così l'indice si ricostruisce sul runtime aggiornato.

## Ordine del rituale post-merge (aggiornato)

1. **Gate pre-merge:** suite completa (`uv run pytest`) + `uv run ruff check .` **verdi** prima del merge.
2. **Merge** su `master` (push già fatto).
3. **Re-lock** del runtime → `scripts/dev/relock-runtime.ps1`.
4. **Re-index** del corpus toccato + **smoke MCP**.
5. **Mostra l'executive summary** della roadmap.

## Clone fresco

Non serve un lock committato: `.sertor/uv.lock` è **gitignorato**. Il setup del runtime risolve HEAD:

```powershell
uv sync --project .sertor
```

## Confine (importante)

Questo meccanismo è **dogfood-only**: gli ospiti pinnano una versione e ricevono l'auto-updater
(E2-FEAT-013), NON tracciano HEAD. Lo script vive in `scripts/dev/` e **non** è distribuito dagli installer;
non tocca l'hook `rag-freshness.ps1`. Una guardia di test lo verifica.

## Verifica

```powershell
uv run pytest tests/unit/test_relock_runtime_dogfood.py -q   # guardia tracking + confine dogfood
git ls-files .sertor/                                        # deve mostrare pyproject.toml, NON uv.lock
```
