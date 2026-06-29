# Contract — Guardia anti-regressione + sync dogfood (E10-FEAT-019)

Tre guardie statiche/offline (no rete, no `uv`), modellate su
`tests/test_assets_hook_cli_invocation.py` (strip `<#…#>` + righe `#`, `iter_asset_dir`, meta-test
positivi/negativi). Realizzano FR-015/CS-6 e FR-014/CS-5.

## Guardia A — lint breadcrumb sui 4 hook in scope
Input: body `.ps1` canonici di `memory-capture` · `rag-freshness` · `wiki-pending-check` ·
`version-check` (solo righe di codice).

- **A1 (presenza+uso):** ogni hook contiene la **definizione** di `Write-HookBreadcrumb` **e** ≥1
  **invocazione** in codice. FAIL se manca.
- **A2 (no silent-swallow):** nessun `catch` con corpo «vuoto» (solo whitespace/`exit 0`/`Pop-Location`)
  in un hook in scope, **eccetto** il `catch` interno della funzione `Write-HookBreadcrumb` (sink
  best-effort sanzionato, REQ-005). FAIL se ne ricompare uno.
- **Meta:** (pos) `catch { exit 0 }` reintrodotto è flaggato; (neg) `catch { Write-HookBreadcrumb … }`
  passa; sanity: i 4 hook sono scoperti (anti-vacuità).

## Guardia B — assert fallback sui 3 body agent
Input: body canonici `concierge.md` · `wiki-curator.md` · `requirements-analyst.md`. Ogni body deve
contenere i token stabili del fallback: `STOP` (maiuscolo) + il **nome dell'asset** (`guided-setup` /
`wiki-playbook` / `requirements`) + la frase `cannot be resolved or read`. FAIL se uno manca.
- **Meta:** rimuovendo la frase di fallback da un body, l'assert fallisce (anti-vacuità).

## Parità host-agnostica — RIUSO (nessun codice nuovo)
`test_assets_copilot_parity.py` rende i piani wiki/governance/rag per Copilot e verifica su ogni body
LLM-facing: (a) no `.claude/` (b) no slash-command (c) no nome Claude. I 3 agent in scope sono già nei
piani → la frase di fallback host-agnostica è coperta **gratis** (REQ-013/CS-5). Vincolo di redazione:
nessun `.claude/`, slash-command o nome-modello/prodotto Claude nella frase.

## Guardia C — sync dogfood dei 3 hook rag (scoperta D-5)
Input: i 3 hook **rag** in scope. Asserisce `.claude/hooks/<n>.ps1` **byte-identico** ad
`assets/rag/hooks/<n>.ps1` (`memory-capture`, `rag-freshness`, `version-check`). Chiude il buco: la root
`test_assets_sync.py` copre solo `assets/claude/**`, quindi i dogfood rag non avevano guardia.
- `wiki-pending-check` (assets/claude) resta coperto dalla root sync; `wiki-curator` idem;
  `requirements-analyst` dalla `sertor-flow` sync.

## Guardia D — RUNTIME_IGNORES (additiva, gemella version-check)
Asserisce `".sertor/.last-hook-error" in RUNTIME_IGNORES` (kit).
