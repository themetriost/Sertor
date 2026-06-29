# Data Model — Fail-loud breadcrumb negli hook + fallback agent (E10-FEAT-019)

Feature **host-facing, ZERO codice di core**: non introduce entità di `sertor_core` (nessun dominio,
porta, adapter, servizio). Le «entità» sono **artefatti distribuiti** (un file di stato runtime +
convenzioni testuali negli asset). Nessuna entità Python nuova.

## 1. Breadcrumb di errore hook — `.sertor/.last-hook-error` (file di stato runtime)

File **singolo, persistente, sovrascritto** (semantica «ultimo errore»), gemello di
`.sertor/.rag-health.json`. JSON, schema `hook.error/1`.

| Campo | Tipo | Obbligo | Descrizione |
|---|---|---|---|
| `schema` | string | sì | `"hook.error/1"` (versionamento additivo, gemello `rag.health/1`) |
| `hook` | string | sì | nome dell'hook che ha prodotto la traccia (`memory-capture` / `rag-freshness` / `wiki-pending-check` / `version-check`) |
| `ts` | string | sì | timestamp UTC `yyyy-MM-ddTHH:mm:ssZ` |
| `reason` | string | sì | motivo breve, leggibile, **secret-free** (stringa hook-local o output già scrubbato dal vehicle) |

**Invarianti**
- INV-1 — **sovrascritto** a ogni nuovo errore (`Set-Content`, non append): un solo file, l'ultimo
  fallimento vince (DA-3).
- INV-2 — scritto **solo** su un path degradato reale; un **no-op gated** (gate di feature spento) non
  lo crea né lo sovrascrive (REQ-004).
- INV-3 — scrittura **best-effort**: se fallisce (path non scrivibile, `.sertor/` non creabile) l'hook
  esce comunque 0; nessun nuovo percorso fatale (REQ-005/FR-005).
- INV-4 — **secret-free**: nessun segreto né contenuto `.env`; `reason` è hook-local o ereditato
  scrubbato (REQ-008/NFR-3).
- INV-5 — **runtime, non versionato**: in `RUNTIME_IGNORES`, rimosso dall'uninstall di `.sertor/`
  (REQ-016) — gemello `.rag-health.json`.

**Collocazione**: sotto la radice runtime `.sertor/` (igiene radice, feature 016).

## 2. Convenzione `Write-HookBreadcrumb` (funzione PowerShell inline)

Funzione **byte-identica** inlinata nei 4 hook in scope (non un file condiviso — research D-1).
Firma logica:

```
Write-HookBreadcrumb -Root <string> -Hook <string> -Reason <string>
```
- crea `.sertor/` se assente, scrive `.last-hook-error` (schema sopra), emette la nota stderr;
- **tutto** in `try{…}catch{}` interno → mai solleva, mai fatale (INV-3);
- è l'**unico** `catch` silenzioso sanzionato (il sink best-effort) riconosciuto dalla guardia A.

## 3. Convenzione fallback agent (testo host-agnostico nei body)

«Entità» testuale aggiunta ai 3 body, **byte-identica Claude↔Copilot** (REQ-013): regola uniforme
«se l'asset di cui sono guscio non è risolvibile/leggibile → **STOP** e segnala l'asset mancante».

| Agent | Asset di cui è guscio | Token stabili attesi dalla guardia B |
|---|---|---|
| `concierge` | skill `guided-setup` | `STOP` + `guided-setup` + «cannot be resolved or read» |
| `wiki-curator` | `wiki-playbook.md` / modulo `ops/` | `STOP` + `wiki-playbook` + «cannot be resolved or read» |
| `requirements-analyst` | skill `requirements` | `STOP` + `requirements` + «cannot be resolved or read» |

> Nota lingua: i body `concierge`/`wiki-curator` sono in EN; `requirements-analyst` è in IT con
> notazione EARS EN. La frase di fallback usa i token EN stabili (`STOP`, asset name, «cannot be
> resolved or read») per uniformità della guardia, restando host-agnostica.

## 4. Classificazione hook (riferimento, non entità Python)

| Hook | Capacità / asset dir | In scope | Punto/i breadcrumb |
|---|---|---|---|
| `memory-capture.ps1` | rag (`assets/rag/hooks/`) | sì | invocazione `memory archive` fallita (catch + `$LASTEXITCODE`) |
| `rag-freshness.ps1` | rag | sì (solo catastrofici) | spawn worker fallito · re-index fallito · worker crash |
| `wiki-pending-check.ps1` | wiki (`assets/claude/hooks/`) | sì | `scan` non risolvibile/in errore |
| `version-check.ps1` | rag | sì | catch interno catastrofico (incl. lettura cieca stato proprio) |
| `rag-freshness-start.ps1` / `version-check-start.ps1` / `wiki-session-start.ps1` / `sertor-rag-usage-check.ps1` | rag/wiki | no | read-only con fallback definito; non modificati (DA-1, R-1) |

## 5. Lifecycle (additivo, nessuna entità nuova del kit)
- `RUNTIME_IGNORES` += `".sertor/.last-hook-error"` (una riga, kit).
- uninstall: già coperto dalla rimozione di `.sertor/` runtime + righe `.gitignore`.
- nessun nuovo `ArtifactKind` / `WriteStrategy` / `Surface`.
