# Research — Fail-loud breadcrumb negli hook + fallback «asset mancante → STOP» negli agent (E10-FEAT-019)

**Branch**: `077-fail-loud-hook-agent` · **Data**: 2026-06-29 · **Fonte**: `spec.md` +
`requirements/debito-tecnico/fail-loud-hook-agent/requirements.md`

Le forche di *prodotto* sono già RISOLTE in spec (DA-1 scope hook, DA-2 fallback uniforme, DA-3
meccanismo breadcrumb = `.sertor/.last-hook-error`). Restano i due *come* di plan: **DA-D-r1** (punti
esatti di scrittura + convenzione/helper condiviso) e **DA-D-r2** (forma della guardia
anti-regressione + sync dogfood). Più una **scoperta** sul sync dei dogfood rag.

## Metodo di ancoraggio (dogfooding MCP-first)

Orientamento via MCP `sertor-rag` (`search_code` su `rag-health.json`/`RUNTIME_IGNORES`, nessun errore
tool — dogfooding sano), poi `Read` sui file indicati. File reali esaminati interi:
`assets/rag/hooks/{memory-capture,rag-freshness,version-check}.ps1`,
`assets/claude/hooks/wiki-pending-check.ps1`, `assets/{rag/agents/concierge.md, claude/agents/wiki-curator.md}`,
`sertor-flow/.../agents/requirements-analyst.md`, `gitignore_append.py` (RUNTIME_IGNORES),
`tests/unit/test_assets_sync.py`, `tests/test_assets_hook_cli_invocation.py`,
`tests/test_assets_copilot_parity.py`, `sync.py`.

---

## D-1 — Pattern di riferimento (dato di partenza)

Il file di stato `.sertor/.rag-health.json` (FEAT-011) e `.sertor/.version-check.json` (E2-FEAT-013)
fissano il pattern: JSON con campo `schema` versionato, scritto **inline** dentro l'hook (nessun
modulo condiviso), collocato sotto la radice runtime `.sertor/`, registrato come **una riga** in
`RUNTIME_IGNORES` (kit) e rimosso dall'uninstall che cancella `.sertor/`. Il breadcrumb è il **gemello
esatto**: stesso trattamento, schema `hook.error/1`.

**Decisione:** il breadcrumb è scritto da una funzione PowerShell **inline byte-identica** nei 4 hook
(`Write-HookBreadcrumb`), non da un file `.ps1` condiviso dot-sourced. Motivo: i 4 hook sono asset
**installati indipendentemente** (3 in `assets/rag/hooks/`, 1 in `assets/claude/hooks/`, capacità
diverse `rag`/`wiki`); un dot-source introdurrebbe una dipendenza cross-file/cross-capacità e un nuovo
artefatto da installare/sincronizzare. La «convenzione condivisa» di REQ-009 è realizzata dalla
**funzione identica + lo schema del file**, esattamente come ogni hook oggi inlina la propria scrittura
di stato. La guardia (D-4) verifica che la funzione sia presente e invocata nei 4 hook.

---

## D-2 (DA-D-r1) — Punti esatti di scrittura del breadcrumb + no-op gated, per hook

**Convenzione comune.** Ogni hook in scope: (a) definisce inline `Write-HookBreadcrumb -Root -Hook
-Reason` (best-effort, `try{…}catch{}` interno → mai fatale, REQ-005); (b) usa un accumulatore
`$reason = $null` impostato sui rami degradati con **stringa hook-local secret-free** (mai
interpolazione di `$_`/output del vehicle non scrubbato → REQ-008/A-003); (c) prima di `exit 0` chiama
`Write-HookBreadcrumb` **solo se** `$reason` è valorizzato. `$root` è già risolto **prima** del blocco
`try` in tutti e 4 (verificato: memory-capture :50-56, rag-freshness foreground :195-197 / worker via
`-Root`, wiki-pending-check :39-44, version-check :85-87) → disponibile in ogni catch.

> **Nota nativo-PowerShell (cruciale).** Un comando nativo (`uv run …`) con exit non-zero **non**
> solleva un'eccezione terminante in PowerShell: il `catch` cattura solo il *mancato avvio* del
> comando. Per rendere fail-loud anche il «vehicle ha girato ma è fallito» si controlla
> `$LASTEXITCODE` dopo l'invocazione, oltre al `catch`.

### memory-capture.ps1
- **No-op gated (REQ-004) — by construction:** il privacy gate `if (-not $enabled) { exit 0 }` (:41) è
  **prima** di qualunque risoluzione di root o invocazione → il path no-op non raggiunge mai
  `Write-HookBreadcrumb`. Nessuna modifica al gate. Un breadcrumb reale preesistente non è toccato.
- **Punti breadcrumb (REQ-001):** l'invocazione delegata è `uv run --project … sertor-rag memory
  archive` (:68) con fallback al `sertor-rag` globale (:71) e, nel catch, all'eseguibile nel venv
  (:79-87). Oggi **tutti** i fallimenti sono inghiottiti (:88-90 `catch {}`). Rami → `$reason`:
  1. dopo l'invocazione primaria/globale: se `$LASTEXITCODE -ne 0` → `"sertor-rag memory archive exited
     <code>"`;
  2. nel `catch` esterno (`uv` assente): se il fallback venv non esiste o il suo `$LASTEXITCODE -ne 0`
     o lancia → `"uv and venv sertor-rag both unavailable"` / `"venv sertor-rag exited <code>"`.
  Un solo `Write-HookBreadcrumb -Hook 'memory-capture'` prima del `exit 0` finale.

### rag-freshness.ps1 (SOLO path catastrofici — DA-1)
- **Già fail-loud (NON breadcrumb, no doppio segnale):** la degradazione di `doctor` (:99-102) confluisce
  in `verdict='degraded'` → scrive `.rag-health.json` + nota stderr (:154-159). Questa è già una traccia
  ispezionabile; il breadcrumb la duplicherebbe. **Decisione:** i path che alimentano il verdetto
  restano governati da `.rag-health.json`; il breadcrumb copre solo i **path muti che bypassano** la
  scrittura del verdetto.
- **Punti breadcrumb:**
  1. **Foreground spawn fallito** (:209-212, `Start-Process pwsh … catch`): il worker non parte → nessun
     doctor, nessun verdetto, nessun re-index → **mute** → `Write-HookBreadcrumb -Hook 'rag-freshness'
     -Reason "failed to spawn freshness worker"` prima di `exit 0`.
  2. **Re-index fallito nel worker** (:164-168): dopo la scrittura del verdetto (anche `healthy`), un
     fallimento dell'`index` è oggi silenzioso ("skip this time") e nasconde un problema reale →
     breadcrumb (`$LASTEXITCODE -ne 0` post-index **o** catch) → `"re-index failed after health write"`.
  3. **Worker outer catch catastrofico** (:172-175): crash del worker con stato **non** scritto → mute →
     breadcrumb `"freshness worker crashed"` (stringa fissa, no `$_`).

### wiki-pending-check.ps1
- **No-op legittimi (NON breadcrumb):** assenza di `wiki.config.toml` (:50, niente da fare) e
  `pending <= 0` / schema invalido (:75): non sono fallimenti.
- **Punto breadcrumb:** il `catch` sulla scan (:70-73, `Pop-Location; exit 0  # silent`) — la CLI
  `sertor-wiki-tools scan` non risolvibile o in errore: oggi muto → `Write-HookBreadcrumb -Hook
  'wiki-pending-check' -Reason "sertor-wiki-tools scan unavailable or failed"` (stringa hook-local fissa,
  **no** `$_` → REQ-008) prima di `exit 0`.

### version-check.ps1
- **Inconclusivo legittimo (NON breadcrumb):** GET fallito → `$latest=''` → verdetto `unknown` (:139-141)
  è un esito **definito** (offline), non un problema nascosto.
- **Punto breadcrumb (anche REQ-006):** l'outer `catch { } # Catastrophic internal error: silent`
  (:166-168) — copre sia un errore interno catastrofico sia una **lettura cieca** dello stato runtime
  proprio (`.version-check.json`/stamp corrotto) che nascondesse un problema → `Write-HookBreadcrumb
  -Hook 'version-check' -Reason "version-check internal error"` prima di `exit 0`.

### REQ-006 e gli hook `*-start` (fuori scope, motivato)
Gli hook read-only di avvio (`rag-freshness-start`, `version-check-start`, `wiki-session-start`)
leggono stato runtime con fallback **definito** (`healthy`/`unknown`/nessuna azione): non nascondono un
problema → **non modificati** (DA-1, R-1 anti-over-scoping). REQ-006 è coperto dentro i 4 hook in scope
dove la lettura cieca confluisce nel catch catastrofico (version-check).

---

## D-3 (DA-D-r1) — Forma del breadcrumb scritto

`Write-HookBreadcrumb` scrive `.sertor/.last-hook-error` (JSON compatto, sovrascritto) + nota stderr:
- crea `.sertor/` se assente (mirror di rag-freshness `New-Item -Force`), tutto dentro `try{}catch{}` →
  se la scrittura fallisce (path non scrivibile) la funzione **ritorna in silenzio**, l'hook prosegue a
  `exit 0` (REQ-005/FR-005);
- campi: `schema=hook.error/1`, `hook`, `ts` (UTC `yyyy-MM-ddTHH:mm:ssZ`, gemello di rag-health), `reason`;
- nota stderr minima: `"[sertor] hook '<hook>' degraded: <reason> (see .sertor/.last-hook-error)"`;
- **semantica «ultimo errore»**: `Set-Content` sovrascrive (non append) → vince l'ultimo fallimento.

Contratto in `contracts/last-hook-error-state.md`.

---

## D-4 (DA-D-r2) — Forma della guardia anti-regressione

Modello = `tests/test_assets_hook_cli_invocation.py` (itera gli asset canonici via `iter_asset_dir`,
strippa `<#…#>` e righe `#`, ha meta-test positivi/negativi). Due nuove guardie + estensione parità:

### Guardia A — lint breadcrumb sui 4 hook in scope (nuova, root o `packages/sertor/tests/`)
Sui body `.ps1` canonici (solo codice):
- **A1 (presenza+uso):** ciascuno dei 4 hook in scope contiene la **definizione** di
  `Write-HookBreadcrumb` **e** almeno una **invocazione** in codice.
- **A2 (no silent-swallow):** nessun `catch { }` / `catch {}` / `catch { exit 0 }` (corpo vuoto o solo
  `exit 0`/`Pop-Location`) in un hook in scope, **eccetto** il `catch` interno della funzione
  `Write-HookBreadcrumb` stessa (l'unico catch silenzioso sanzionato = il sink best-effort REQ-005,
  annotato). Implementazione: regex sui code-line per `catch\s*\{…\}` con corpo «vuoto»; flag se fuori
  dal corpo di `Write-HookBreadcrumb`.
- **Meta-test:** una fixture con `catch { exit 0 }` reintrodotto è flaggata; la forma robusta (`catch {
  Write-HookBreadcrumb … }`) passa; sanity di discovery dei 4 hook (anti-vacuità).

### Guardia B — assert fallback sui 3 body agent (nuova)
Sui body canonici `concierge.md` / `wiki-curator.md` / `requirements-analyst.md`: ciascuno contiene
l'istruzione di fallback inequivocabile. Per evitare matching fragile di prosa si **standardizza** una
frase canonica con i token stabili: il token **`STOP`** (maiuscolo) co-locato con `cannot be resolved
or read` (fraseggio EN di REQ-010..012) e il **nome dell'asset** (`guided-setup` / `wiki-playbook` /
`requirements`). La guardia asserisce la presenza di questi token per ciascun body. Meta-test:
rimuovendo la frase, l'assert fallisce.

### Parità host-agnostica — RIUSO della guardia esistente (nessun codice nuovo)
`test_assets_copilot_parity.py` rende già i 3 piani (wiki/governance/rag) per Copilot e verifica
(a) no `.claude/` (b) no slash-command (c) no nome Claude su **ogni body LLM-facing** — i 3 agent in
scope sono già coperti (concierge=rag, wiki-curator=wiki, requirements-analyst=governance). Aggiungendo
il fallback in **prosa host-agnostica** è coperto **gratis** (REQ-013/CS-5). Vincolo di redazione:
niente `.claude/`, niente slash-command, niente nome-modello/prodotto Claude nella frase di fallback.

---

## D-5 (DA-D-r2) — Scoperta: sync dogfood dei 3 hook rag NON coperto

`sertor_installer.sync` propaga **solo** `assets/claude/**` → `.claude/` (verificato in `sync.py`). La
root `test_assets_sync.py` itera `iter_asset_dir("claude")`. Ma i 3 hook **rag** dogfood
`.claude/hooks/{memory-capture,rag-freshness,version-check}.ps1` sono **git-tracked** (output di un
`sertor install rag --assistant claude` sul repo) e **byte-identici** al canonico — **senza alcuna
guardia di sync**. wiki-pending-check (assets/claude) è coperto dalla root sync; wiki-curator (claude)
idem; requirements-analyst dalla flow sync. I 3 hook rag sono il **buco**.

**Decisione:** nuova guardia dedicata `test_assets_rag_dogfood_sync.py` (root) che asserisce i 3 hook
rag in scope `.claude/hooks/<n>.ps1` **byte-identici** ad `assets/rag/hooks/<n>.ps1`. Chiude il buco e
realizza FR-014/CS-5 per gli hook rag (la modifica al canonico va ri-sincronizzata a mano nei dogfood +
guardia anti-drift). Additiva, scoped ai 3 hook (R-1).

> **Errore-MCP = finding:** nessun errore dai tool `mcp__sertor-rag__*` in questa sessione (server
> sano). La scoperta D-5 emerge da `Read`/`git ls-files`, non da un guasto MCP.

---

## D-6 — Installer / lifecycle (additivo)

Unica modifica al kit: **una riga** in `RUNTIME_IGNORES` (`gitignore_append.py`):
`".sertor/.last-hook-error"` (gemello di `.rag-health.json`). L'uninstall rimuove già `.sertor/` runtime
(test `test_uninstall_rag_removes_runtime_and_shared`) + la riga `.gitignore` (`remove_gitignore_lines`).
Nessun nuovo `ArtifactKind`/`WriteStrategy`/seam. Guardia additiva (gemella di
`test_version_check_runtime_ignores`): `.sertor/.last-hook-error in RUNTIME_IGNORES`.

---

## D-7 — Estensioni / Out-of-Scope (promossi a casa durevole, non sepolti)
- **Consumo attivo della traccia all'avvio** (oltre l'induzione `degraded` di FEAT-011) → follow-up
  **Could** epica debito-tecnico (già in §9 requirements).
- **Portabilità OS hook (gemello bash) + onestà surface Copilot inerti** → **FEAT-018** (backlog).
- **Pulizia stile/altitude body + blocchi CLAUDE.md** → **FEAT-021/FEAT-022** (backlog).

Nessun rinvio reale resta in `specs/`.

## Sintesi forche risolte
| Forca | Esito |
|---|---|
| DA-D-r1 punti scrittura | 1 punto memory-capture, 3 rag-freshness (spawn/index/worker-crash), 1 wiki-pending-check, 1 version-check; no-op gated by-construction |
| DA-D-r1 convenzione | funzione inline `Write-HookBreadcrumb` byte-identica + schema `hook.error/1` (no file condiviso) |
| DA-D-r2 guardia | A=lint breadcrumb (presenza+no-silent-catch), B=assert fallback agent, parità RIUSATA, +D-5 sync rag dogfood |
| D-5 (scoperta) | nuova guardia byte-identità dogfood per i 3 hook rag (buco non coperto) |
