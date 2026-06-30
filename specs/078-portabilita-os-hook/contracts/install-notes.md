# Contratto — Note d'install (`InstallReport.notes`) per E10-FEAT-018

**Schema:** `install.report/1` (INVARIATO — additivo, nessun nuovo schema). Le note vivono nel campo
**esistente** `InstallReport.notes: list[str]` (`sertor-install-kit/report.py:44`, metodo `.note()` a
`:74`). Questa feature è la **prima emissione reale** in produzione.

## Resa (già garantita dal contratto esistente)

- **Umana** (`render_human`): una riga `Note: <messaggio>` per ciascuna nota (`report.py:101-102`).
- **JSON** (`render_json`, `--json`): chiave `notes` con array di stringhe, **presente solo se non-vuoto**
  (`report.py:126-127`). A `notes == []` il JSON è byte-identico a oggi (non-regressione).

## Nota A — Indisponibilità `pwsh` (host non-Windows)

**Emessa quando:** host **non-Windows** ∧ `pwsh` **non** in PATH ∧ il piano deposita ≥1 hook `.ps1`.
**Substringhe stabili (la guardia di test le asserisce):**

| # | Garanzia di contenuto | Verificabile in test |
|---|---|---|
| A1 | menziona **`pwsh`** / **PowerShell Core** | `"pwsh"` presente nella nota |
| A2 | contiene l'**URL** di rimediazione | `"learn.microsoft.com/powershell"` presente |
| A3 | identifica i **surface hook** affetti (almeno un `target_rel` `.ps1` del piano) | un path `.ps1` del piano presente nella nota |
| A4 | dichiara «**installati ma non-operativi**» (o equivalente esplicito) | substringa di stato presente |

**Esempio (forma, non vincolante alla virgola):**
> `pwsh (PowerShell Core) was not found on this non-Windows host: the deposited hooks
> (.github/hooks/rag-freshness.ps1, …) are installed but non-operational until you install it —
> https://learn.microsoft.com/powershell/scripting/install/installing-powershell`

**NON emessa quando:** host Windows (FR-006); `pwsh` presente su non-Windows (FR-004); il piano non
deposita hook. **Scope narrow (D-3):** l'assenza di questa nota significa solo «`pwsh` è disponibile»,
**non** «hook pienamente operativi» (l'operatività completa per-target è nei doc utente).

## Nota B — Inertness `memory-capture` (install rag Copilot CLI)

**Emessa quando:** `sertor install rag --assistant copilot-cli` — **sempre**, indipendente da
`SERTOR_MEMORY` (decisione D-2). **Substringhe stabili:**

| # | Garanzia di contenuto | Verificabile in test |
|---|---|---|
| B1 | menziona **`memory-capture`** | `"memory-capture"` presente |
| B2 | menziona **`SERTOR_MEMORY`** (=true) e **`SERTOR_MEMORY_ADAPTER`** (valore Copilot) | entrambe le chiavi presenti |
| B3 | dichiara che col default l'hook **scatta ma non cattura** sessioni Copilot utili | substringa esplicita |
| B4 | **cross-ref** alla capacità pianificata (distribuzione adapter nel template `.env`, epica memorie) | riferimento esplicito |

**NON emessa quando:** `--assistant claude` (FR-009, `report.notes == []` su Claude/Windows); capability
`wiki` (la nota è rag-specifica).

## Invarianti del contratto

- **Idempotenza:** `.note()` deduplica messaggi identici (`report.py:76`) → ri-emissione = no-op.
- **Non-fatale:** l'emissione di una nota non altera `exit_code()` (resta 0 senza altri errori, FR-005).
- **Ordine:** le note seguono l'ordine d'emissione; nessun vincolo d'ordinamento richiesto dai test
  (asserzione per-substringa, non posizionale).
