# Quickstart — verifiche manuali del version-check (E2-FEAT-013)

**Branch**: `feat013-version-check-backlog`

Verifiche eseguibili a mano (PowerShell, Windows) per validare i criteri di successo. La logica vive
negli script `.ps1` + nello stato `.sertor/.version-check.json` + nello stamp `.sertor/.sertor-version`.
Le verifiche **non** richiedono cloud; la sola GET reale (V1) richiede rete verso GitHub raw.

> Prerequisito: capacità RAG installata sull'ospite (`sertor install rag`) → gli script e le voci di
> wiki/wiring sono depositati; lo stamp `.sertor/.sertor-version` è stato scritto a install-time.

## V1 — GET cachata (~1/giorno) [CS-2, FR-006]
1. Elimina `.sertor/.version-check.json` (forza una GET pulita).
2. Esegui lo script SessionEnd: `.\.claude\hooks\version-check.ps1; $LASTEXITCODE` → **0**.
3. Verifica che `.sertor/.version-check.json` esista con `checked_at` recente.
4. Riesegui subito lo script → **nessuna nuova GET** (cache fresca): `checked_at` invariato (riuso).
**Atteso**: una sola GET entro ~24h; riusi successivi senza rete.

## V2 — Behind → avviso al SessionStart [CS-1, FR-003]
1. Forza un verdetto `behind`: scrivi a mano `.sertor/.sertor-version` con un valore vecchio (es.
   `0.0.1`) e rilancia `version-check.ps1` (oppure imposta `$env:SERTOR_VERSION_CHECK_FORCE=1`).
2. Esegui `.\.claude\hooks\version-check-start.ps1 -Assistant claude` → l'output nomina **installato**,
   **ultimo** e il **comando d'aggiornamento** (`sertor upgrade` / `uvx --refresh …`); `$LASTEXITCODE`
   → **0**.
**Atteso**: avviso presentato; nessun aggiornamento applicato (FR-005).

## V3 — Up-to-date / ahead → nessun avviso [CS-1, FR-004, DA-5]
1. Allinea `.sertor/.sertor-version` al `latest` (o impostalo più nuovo, es. `99.0.0`) e rilancia
   `version-check.ps1`.
2. Esegui `version-check-start.ps1` → **nessun output** (no-op), `$LASTEXITCODE` → **0**.
**Atteso**: `verdict` `up-to-date`/`ahead`; il SessionStart non avvisa (dev-locale coperto).

## V4 — Offline / GET fallita → skip silenzioso [CS-2, FR-009]
1. Imposta un URL irraggiungibile: `$env:SERTOR_VERSION_CHECK_URL='https://invalid.invalid/VERSION'`
   e `$env:SERTOR_VERSION_CHECK_FORCE=1`.
2. Esegui `version-check.ps1` → `$LASTEXITCODE` **0**, nessun errore; lo stato resta `unknown` (o il
   precedente esito cachato è preservato).
3. Esegui `version-check-start.ps1` → nessun avviso.
**Atteso**: la sessione parte normalmente; mai un falso «sei indietro» (FR-010).

## V5 — Indeterminato (stamp/`/VERSION` non parsabili) [FR-010]
1. Scrivi `.sertor/.sertor-version` con contenuto non-versione (es. `xyz`) e rilancia.
2. `verdict` → `unknown`; il SessionStart non avvisa.

## V6 — Loop chiusa dopo l'aggiornamento [US7, FR-013]
1. Parti da un verdetto `behind` (V2).
2. Simula l'upgrade: riscrivi `.sertor/.sertor-version` al `latest` (è ciò che fa `sertor upgrade`).
3. Rilancia `version-check.ps1` (cache invalidata dal cambio stamp) → `verdict` `up-to-date`.
4. `version-check-start.ps1` → nessun avviso.
**Atteso**: l'avviso non si ripresenta; nessun avviso a vuoto dopo l'upgrade a metà giornata (R-5).

## V7 — Distribuzione & parità Claude / Copilot [CS-5, FR-016]
- **Claude**: `sertor install rag --assistant claude` su un repo pulito → presenti
  `.claude/hooks/version-check.ps1`, `.claude/hooks/version-check-start.ps1`, le voci SessionEnd +
  SessionStart in `.claude/settings.json`, lo stamp `.sertor/.sertor-version`.
- **Copilot**: `sertor install rag --assistant copilot-cli` → presente
  `.github/hooks/version-check.ps1`; **NON** presente `version-check-start.ps1` (W5); le voci in
  `.github/hooks/sertor-hooks.json` sono nel **formato piatto** (`version:1`/`timeoutSec`, SessionStart
  = `type:"prompt"`), mai il formato Claude.
**Atteso**: deposito non-distruttivo e idempotente; parità rispettata.

## V8 — Lifecycle (install/upgrade/uninstall) [FR-017]
1. `install` due volte → seconda esecuzione idempotente (SKIPPED/MERGED, nessun duplicato).
2. `upgrade` → lo stamp è **riscritto** con la nuova versione; voci aggiornate se cambiate.
3. `uninstall` → script, voci di wiring, stamp e `.sertor/` rimossi; le voci utente in
   `settings.json`/`sertor-hooks.json` preservate; le righe `.sertor/.version-check.json`/stamp
   rimosse dal `.gitignore`.

## V9 — Guardia di sync bundlato↔dogfood [FR-016, D-0f]
Esegui la suite root/`packages/sertor` che include la guardia estesa: l'asset bundlato
`assets/rag/hooks/version-check*.ps1` deve essere **byte-identico** alla copia dogfood
`.claude/hooks/version-check*.ps1`. Drift → test rosso (ricopia l'asset).

## V10 — D↔N & privacy [CS-6, FR-014/015]
- `Select-String -Path .\.claude\hooks\version-check*.ps1 -Pattern 'sertor_core|import |python'` →
  **nessun** import di `sertor_core` né lancio di Python nel path caldo (lo stamp lo scrive
  l'installer, non l'hook).
- L'unico egress di rete è la GET del `/VERSION` pubblico; nessun contenuto/segreto trasmesso.
- Nessun LLM invocato dagli script.
