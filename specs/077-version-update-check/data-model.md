# Data Model — auto-update version check (E2-FEAT-013)

**Branch**: `feat013-version-check-backlog` · **Fase**: Phase 1 (design)

> Entità di stato (file persistiti), script hook, voci di wiring e artefatti installer. Nessuna entità
> di dominio nuova in `sertor-core` (Principio I/XI invariato): la feature vive in asset PowerShell +
> orchestrazione installer + file JSON/testo locali.

## 1. Stato del check — `.sertor/.version-check.json` (schema `version.check/1`)

File JSON piatto persistito dallo script `version-check.ps1` al SessionEnd; letto dallo script/prompt
SessionStart e da un umano. Gitignored.

| Campo | Tipo | Obblig. | Descrizione |
|---|---|---|---|
| `schema` | string | sì | `"version.check/1"` — versione del contratto |
| `verdict` | string | sì | `behind` \| `up-to-date` \| `ahead` \| `unknown` (D-4) |
| `installed` | string | sì | versione installata letta dallo stamp `.sertor/.sertor-version` |
| `latest` | string | sì | ultima versione letta dal `/VERSION` remoto (vuota se GET fallita → `unknown`) |
| `checked_at` | string (ISO-8601 UTC) | sì | timestamp dell'ultima GET riuscita (gate della cache ~24h, D-5) |
| `dimensions` | object<string,string> | no (additivo) | versione installata per dimensione presente (`sertor`, `sertor-flow`) — FR-012/US6 |

**Invarianti**
- **INV-1 (no oscillazione)**: `up-to-date`/`ahead` sono scritti come stato canonico (file non
  cancellato) → il SessionStart legge un verdetto non-`behind` e **no-op** (NFR-6 gemella).
- **INV-2 (mai falso «behind»)**: parse del remoto/stamp fallito → `verdict: "unknown"`, `latest: ""`;
  il SessionStart non avvisa (FR-010).
- **INV-3 (privacy)**: nessun segreto; `installed`/`latest` sono numeri di versione pubblici (FR-015).
- **INV-4 (cache)**: a `checked_at` entro ~24h lo script **riusa** l'esito senza GET, ma riconferma il
  verdetto rispetto allo stamp corrente (un upgrade a metà giornata aggiorna il verdetto senza rete —
  R-5/FR-017).

## 2. Stamp installato — `.sertor/.sertor-version` (+ `.sertor/.sertor-flow-version`)

File di **testo** a singola riga, scritto dall'installer a install/upgrade-time (D-3). È la fonte
locale dell'«installato», confrontabile dallo script **senza Python**.

| File | Scritto da | Contenuto |
|---|---|---|
| `.sertor/.sertor-version` | `sertor install`/`upgrade` | versione del pacchetto `sertor` (dal proprio `/VERSION`, via `importlib.metadata.version("sertor")` in-process all'install — **non** nel path caldo dell'hook) |
| `.sertor/.sertor-flow-version` | `sertor-flow install`/`upgrade` | versione del pacchetto `sertor-flow` (copertura per-dimensione US6/FR-012, Could) |

**Invarianti**
- **INV-5 (loop chiusa)**: a `upgrade` lo stamp è **riscritto** con la nuova versione → il prossimo
  SessionEnd confronta lo stamp aggiornato col remoto e il verdetto torna `up-to-date` (FR-013/US7).
- **INV-6 (indeterminato)**: stamp assente/non parsabile → check `unknown` → skip (FR-010).

## 3. Script hook (asset PowerShell, host-agnostici)

### (a) `version-check.ps1` — SessionEnd (entrambi gli assistenti)
Gemello di `rag-freshness.ps1` per disciplina (exit 0 sempre, `try/catch`, stdin tollerante, root da
`$env:CLAUDE_PROJECT_DIR` → `hook.cwd` → `'.'`). Logica:
1. legge `.sertor/.version-check.json`; se `checked_at` entro ~24h e `SERTOR_VERSION_CHECK_FORCE` non
   impostata → **riusa** (nessuna GET), riconferma il verdetto vs stamp corrente, riscrive lo stato.
2. altrimenti: **GET** `SERTOR_VERSION_CHECK_URL` (default raw `master`, timeout ~5 s) → `latest`.
3. legge gli stamp installati (`.sertor/.sertor-version`[, `.sertor/.sertor-flow-version`]) → `installed`.
4. **confronto semantico per segmenti** (D-4) → `verdict`.
5. scrive `.sertor/.version-check.json` (schema `version.check/1`, §1).
6. **exit 0 sempre**; offline/parse-fail → stato `unknown` o riuso, nessun errore (FR-009/010).
   Mai invoca un LLM né importa `sertor_core` (FR-014).

### (b) `version-check-start.ps1` — SessionStart (Claude only)
Gemello di `rag-freshness-start.ps1`. Logica:
1. legge `.sertor/.version-check.json` (root da `$env:CLAUDE_PROJECT_DIR` → `'.'`).
2. file assente OR `verdict != "behind"` → **no-op** (exit 0, nessun output) — INV-1.
3. `verdict == "behind"` → emette su stdout l'**avviso** (installato, ultimo, comando d'aggiornamento
   `sertor upgrade` / `uvx --refresh …`; se `dimensions` presente, nomina la/le dimensione/i indietro).
4. **exit 0 sempre**; mai applica un aggiornamento (FR-005 — solo avviso).

> **Copilot CLI**: nessuno script SessionStart (Copilot non esegue script al SessionStart, A-005) →
> la voce è un **prompt nativo statico** che istruisce l'agente a leggere `.sertor/.version-check.json`
> e relayare l'avviso se `behind` (D-1, W5 del wiring).

## 4. Voci di wiring per-assistente

Fonte unica logica: `HookEntrySpec` del kit (`render_copilot_hooks`), gemella delle voci
freschezza/memory-capture. Dettaglio nel contratto
[`contracts/version-check-hook-wiring.md`](./contracts/version-check-hook-wiring.md).

- **Claude** (`.claude/settings.json`, formato annidato): voce `SessionEnd` → `version-check.ps1`;
  voce `SessionStart` → `version-check-start.ps1`. Merge-dedup accanto alle voci esistenti (wiki,
  memory, freschezza) — `merge_settings` preserva le altre.
- **Copilot CLI** (`.github/hooks/sertor-hooks.json`, formato piatto generato): voce `SessionEnd`
  (command → `version-check.ps1`); voce `SessionStart` (prompt statico — nessuno script).

## 5. Artefatti installer (plan `build_rag_plan`, ordine canonico)

| # | `ArtifactKind` | Source | Target (Claude / Copilot) | WriteStrategy |
|---|---|---|---|---|
| 1 | FILE | `rag/hooks/version-check.ps1` | `.claude/hooks/…` / `.github/hooks/…` | CREATE_IF_ABSENT |
| 2 | SETTINGS_MERGE | `rag/settings.version-check.json` / sentinel | `.claude/settings.json` / `.github/hooks/sertor-hooks.json` | MERGE_DEDUP |
| 3 | FILE (Claude only) | `rag/hooks/version-check-start.ps1` | `.claude/hooks/…` | CREATE_IF_ABSENT |
| 4 | SETTINGS_MERGE | `rag/settings.version-check-start.json` / sentinel | `.claude/settings.json` / `.github/hooks/sertor-hooks.json` | MERGE_DEDUP |
| 5 | FILE (generato) | stamp `.sertor/.sertor-version` | `.sertor/.sertor-version` | (scritto dal valore `importlib.metadata` all'apply) |

> Note: (a) `version-check-start.ps1` (riga 3) è depositato **solo** su Claude; su Copilot il
> SessionStart è il prompt statico (riga 4, sentinel). (b) Lo stamp (riga 5) è scritto **a
> install/upgrade-time** dal valore noto in-process, **non** dall'hook a runtime (D-3). (c) Nessun
> nuovo `ArtifactKind`/`Surface`/`WriteStrategy` (riuso, Principio III).

## 6. Lifecycle (FEAT-008, riuso art-aware)

| Op | Script (FILE) | Wiring (SETTINGS_MERGE) | Stamp | `.gitignore` |
|---|---|---|---|---|
| **install** | CREATE_IF_ABSENT | merge-dedup (additivo) | scritto col valore corrente | `RUNTIME_IGNORES` esteso |
| **upgrade** | update se cambiato | merge-dedup idempotente | **riscritto** (chiude la loop, INV-5) | invariato |
| **uninstall** | remove | `remove_settings_entries` (`delete_if_empty` per `sertor-hooks.json`) | rimosso (parte di `.sertor/`) | `remove_gitignore_lines` |

**`sertor_owned_paths`**: owned_files += `version-check.ps1` (entrambi), `version-check-start.ps1`
(Claude only), stamp `.sertor/.sertor-version`; lo stato `.sertor/.version-check.json` e l'intero
`.sertor/` sono già coperti (owned_dir `.sertor`). Test di copertura: i `target_rel` del plan ⊆
owned_paths.

## Invarianti trasversali
- **A feature non installata**: comportamento e costo **identici a oggi** (RNF-5).
- **Non-fatale ovunque**: ogni script esce 0; nessun errore propagato alla sessione (RNF-2/FR-009).
- **Zero rete al SessionStart**: la GET è solo al SessionEnd, cachata (RNF-1).
- **D↔N**: lo script **segnala**, l'utente **agisce**; mai auto-upgrade, mai LLM, mai `sertor_core`.
- **Parità**: Copilot riceve solo il formato nativo (piatto `version:1`/`timeoutSec`/prompt), mai il
  formato Claude (lezione FEAT-011/049).
