# Data Model — E10-FEAT-018 (portabilità OS hook + onestà surface inerti)

**Branch**: `078-portabilita-os-hook` · **Data**: 2026-06-30 · **Fase**: 1 (design)

La feature è **additiva** e **senza nuove entità di dominio del core**: non introduce `ArtifactKind`,
`Surface`, `WriteStrategy`, porte o seam del kit nuovi. Riusa il contratto **esistente**
`InstallReport.notes` (schema `install.report/1`, invariato). Le «entità» qui sono: il modulo di
rilevamento (`host_env`), le **due note** (stringhe in `report.notes`) e la derivazione delle hook
surfaces dal piano.

## 1. Modulo di rilevamento — `sertor_install_kit.host_env` (NUOVO, puro)

Funzioni stdlib (`os`, `shutil`), deterministiche, mockabili. **Zero** import di `sertor_core`, nessun LLM.

| Funzione | Firma | Comportamento |
|---|---|---|
| `is_windows` | `() -> bool` | `os.name == "nt"` |
| `pwsh_available` | `() -> bool` | `shutil.which("pwsh") is not None` (binario: trovato/non trovato; nessun test di versione, nessun hardcoding di distro — NFR-4) |
| `pwsh_unavailability_note` | `(hook_surfaces: Sequence[str]) -> str` | builder **puro**: produce la nota d'indisponibilità (elenco surface affetti + URL PowerShell Core + frase «installati ma non-operativi»). Nessun side-effect |
| `maybe_note_pwsh` | `(report: InstallReport, hook_surfaces: Sequence[str]) -> None` | gating: `(not is_windows()) and (not pwsh_available()) and hook_surfaces` → `report.note(pwsh_unavailability_note(hook_surfaces))`; altrimenti **no-op**. Idempotente (`.note()` deduplica) |

Costante modulo: `PWSH_INSTALL_URL = "https://learn.microsoft.com/powershell/scripting/install/installing-powershell"`.

> `maybe_note_pwsh` invoca `is_windows()`/`pwsh_available()` come **global del modulo** → i test patchano
> `host_env.is_windows`/`host_env.pwsh_available` (CI Windows simula il ramo non-Windows — R-6).

## 2. Derivazione delle hook surfaces (dichiarativa)

Nessuna lista hardcoded. I consumatori derivano i surface hook dal piano già costruito:

```
hook_surfaces = [a.target_rel for a in plan if a.target_rel.endswith(".ps1")]
```

- **rag/claude:** `.claude/hooks/sertor-rag-usage-check.ps1`, `memory-capture.ps1`, `rag-freshness.ps1`,
  `rag-freshness-start.ps1`, `version-check.ps1`, `version-check-start.ps1`.
- **rag/copilot-cli:** i corrispettivi `.github/hooks/*.ps1` (senza gli script SessionStart — prompt nativi).
- **wiki/claude:** `.claude/hooks/wiki-pending-check.ps1` (+ eventuali altri sotto `assets/claude/hooks`).
- **wiki/copilot-cli:** `.github/hooks/wiki-pending-check.ps1`.

Se un piano non deposita hook (`hook_surfaces == []`) la guardia è un no-op (la nota descrive solo hook
realmente depositati — coerenza CS-1).

## 3. Nota d'indisponibilità `pwsh` (voce di `report.notes`)

**Tipo:** `str` (free-text caveat, contratto `InstallReport.notes`). **Emessa quando:** host non-Windows
∧ `pwsh` assente ∧ il piano deposita hook. **Contenuto (contratto in `contracts/install-notes.md`):**
1. identifica i **surface hook** depositati ma non-operativi senza `pwsh`;
2. messaggio di **rimediazione azionabile** con **URL** PowerShell Core;
3. frase esplicita: senza `pwsh` quei surface sono **installati ma non-operativi**.

Resa: **umana** (riga `Note: …`) **e** JSON (`notes[]`), per costruzione del report (FR-003).

## 4. Nota d'inertness `memory-capture` Copilot (voce di `report.notes`)

**Tipo:** `str`. **Emessa quando:** `sertor install rag --assistant copilot-cli` (**sempre**, indipendente
da `SERTOR_MEMORY` — D-2). **Contenuto:**
1. `memory-capture` richiede **`SERTOR_MEMORY=true`** **e** un valore adapter Copilot esplicito per
   **`SERTOR_MEMORY_ADAPTER`** per catturare sessioni Copilot CLI;
2. col default l'hook **scatta ma non cattura nulla di utile**;
3. **cross-ref** alla capacità pianificata (distribuzione del valore adapter nel template `.env`,
   epica memoria-conversazioni / FEAT-009) → l'utente sa che un fix è pianificato e può optare manualmente.

**Vive in** `install_rag.py` (rag-specifica, single consumer). **Non** emessa su Claude/Windows (FR-009).

## 5. Punti di emissione (seam, invariato il resto)

| Funzione | File | Aggiunta |
|---|---|---|
| `execute_rag_plan` | `install_rag.py` | dopo `_kit_execute_plan` → `maybe_note_pwsh(report, hook_surfaces)`; se `assistant is COPILOT_CLI` → `report.note(<memory-capture note>)` |
| `execute_plan` (wiki) | `install_wiki.py` | dopo `_kit_execute_plan` → `maybe_note_pwsh(report, hook_surfaces)` |

La CLI (`_cmd_install_rag`/`_cmd_install_wiki`) resta **thin**: solo `render_json`/`render_human`. Il
percorso lifecycle (`upgrade`/`uninstall`) **non** è toccato (la nota è un advisory install-time —
research §Estensioni).

## 6. Invarianti

- **Non-fatale (FR-005/NFR-3):** la guardia non solleva mai; tutti i surface non-hook installati;
  `exit_code()` = 0 in assenza di altri errori. La guardia è solo `report.note(...)`.
- **Nessuna nota su Windows (FR-006) / con `pwsh` presente (FR-004):** garantito dal gating di
  `maybe_note_pwsh` (no-op).
- **Non-regressione Claude+Windows (FR-009/CS-3):** `report.notes == []` (né pwsh né Copilot) — il test
  `test_claude_report_has_no_gap_note` resta verde.
- **Schema invariato:** `install.report/1`; `notes[]` appare nel JSON **solo se non-vuoto** (già così).
- **Nessun asset cambia:** sync `assets/claude/**` ↔ `.claude/` verde per costruzione (FR-015).
