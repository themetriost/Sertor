---
title: A-09 / E2-FEAT-010 — Portabilità POSIX degli hook (8 hook Python portabili)
type: experiment
tags: [feature, portabilità, hook, principio-x, principio-xii, sertor-cli, python, uv]
created: 2026-07-09
updated: 2026-07-09
sources: ["specs/095-portable-hooks-09/", "requirements/sertor-cli/epic.md", ".claude/hooks/", "packages/sertor/sertor_installer/assets/"]
---

# A-09 / E2-FEAT-010 — Portabilità POSIX degli hook

**Feature:** Riscrittura di tutti gli 8 hook host-facing da PowerShell `.ps1` a **Python portabile** invocato via `uv run --no-project python`, eliminando la dipendenza da PowerShell Core e abilitando l'installazione su qualunque OS (Windows · macOS · Linux).

**Stato:** ✅ Implementata (2026-07-09, branch `095-portable-hooks-09`).

> **✅ Supersede di [[feat-018-portabilita-os-hook]]** — FEAT-018 *rilevava e segnalava* il gap (hook `.ps1` inerti su non-Windows senza `pwsh`) senza risolverlo, accettando la "limitazione tecnica" che cambiare `powershell`→`pwsh` avrebbe rotto Windows. **A-09 ha rimosso la causa alla radice**: gli 8 hook sono stati riscritti in **Python portabile**, senza alcuna dipendenza da PowerShell su nessun OS (fix il causa, non mitigazione — Principio XII). La guardia `pwsh` di FEAT-018 è stata rimossa (`host_env.py` eliminato) e il gap si estingue per costruzione.

**Driver costituzionale:** [[principle-xii|Principio XII «Fail Loud, Fix the Cause»]] + [[principle-x|Principio X host-agnostico]].

## Problema e soluzione

### Problema
Gli **8 hook distribuiti** erano tutti in **PowerShell `.ps1`**:
- su Claude: wirati come `"shell": "powershell"` (non supportato su mac/Linux).
- su Copilot CLI: invocati via `pwsh -File` (richiede PowerShell Core, non disponibile di default su mac/Linux).
- Risultato: **inerzia totale su non-Windows senza `pwsh`** — gli hook non venivano mai eseguiti.

La causale radicale: **portabilità OS violata** (Principio X). FEAT-018 aveva *segnalato* il gap senza risolverlo; la convenzione «solo PowerShell» del repo lo accettava come limitazione tecnica.

### Soluzione: Python portabile
**Tutti gli 8 hook riscritti in Python**, invocati via:
```
uv run --no-project python <hook>.py [--assistant claude|copilot] [--mode ...]
```

Vantaggi:
- **`uv` garantito** — è una dipendenza d'installazione già presente (requisito di `sertor install`).
- **`--no-project` isola** dal `pyproject.toml` dell'host → non dipende da `.sertor/.venv`.
- **Python 3.11+** è disponibile ovunque (Windows · macOS · Linux).
- **Nessun PowerShell** richiesto, nessun wiring `"shell":"powershell"`.
- **Comportamento OS-indipendente** (subprocess detached cross-OS via `DETACHED_PROCESS`/`start_new_session`).

## Consegne (tre commit)

### US1: Wiring e trasporto (commit `2a343e1`)
**8 hook Python portabili + helper shared `_hooklib.py`:**

1. **`wiki-session-start.py`** — carica indice + log a inizio sessione (sovrascritto [[sessionstart-hook]]).
2. **`rag-freshness.py`** — re-index incrementale e smoke-test RAG post-sessione.
3. **`memory-capture.py`** — cattura trascrizioni a fine sessione.
4. **`fail-loudness.py`** — breadcrumb fallback su errore hook.
5. **`version-check.py`** — verifica disponibilità aggiornamenti.
6. **`installed-check.py`** — verifica completezza installazione.
7. **`lifecycle-hook.py`** — notifiche ciclo di vita (install/upgrade/uninstall).
8. **`config-init.py`** — inizializzazione config.

**Helper shared:**
- **`_hooklib.py`** — utilità stdlib (stdin-guard, segnalazione errore `hook.error/1` secret-free, `run()` fail-safe che esce sempre 0).

**Installer wiring:**
- **7 claudeAssets `settings.*.json`** — rimosso `"shell": "powershell"`; aggiunto `"shell": "uv run --no-project python"` generico.
- **Copilot `HookEntrySpec`** — aggiunto `--assistant copilot` al comando di invocazione.
- **`_hooklib.py` depositato** per entrambi gli assistenti (asset condiviso).
- **`__pycache__` ignorato** nella raccolta asset (CLI walk esclude le directory).

**Worker re-index detached:**
- Implementato con `subprocess.Popen` + `start_new_session` (macOS/Linux) / `DETACHED_PROCESS` (Windows) per staccare il processo genitore.

### US2: Parity gate + smoke (commit `39bdc8a`)
**Due test suite come gate pre-merge:**

1. **`test_portable_hooks_parity.py`** — verifica **offline** che l'output di ogni hook Python **coincida byte-a-byte** con il precedente `.ps1` (contratto per-assistente). Fixture per il wiring legacy vs portabile.

2. **`test_portable_hooks_smoke.py`** — **esecuzione reale** di ogni hook tramite il **vero vehicle** `uv run --no-project python` su matrice CI:
   - Windows (Python 3.11+).
   - Ubuntu (Python 3.11+).
   - Marker `hooks_smoke` per esecuzione deliberata (non nei gate veloci).
   - Contract C6: **ogni hook eseguibile e non-fatale**.

### US3: Single-impl + migration + docs (commit `97da7bc`)
**Ritiro del PowerShell, migrazione legacy, docs aggiornate:**

1. **Rimozione dei `.ps1`** — i 8 file PowerShell rimossi dal bundle (single-impl: Python è l'unica implementazione).
2. **`sertor upgrade` migrazione legacy** — nuova primitiva nel ciclo di vita installer:
   - Rilevamento di `.ps1` nel `.sertor/hooks/` dell'ospite.
   - Stripping dichiarato (`legacy-owned → obsolete` phase).
   - Rimozione entries wiring legacy dai file `.json` / `settings.json` via helper `remove_hook_entries_by_command_substring` (del kit).
3. **Supersession di E10-FEAT-018** — la guardia `pwsh_available` e il modulo `host_env.py` rimossi (il problema è risolto, non c'è gap da segnalare).
4. **Docs utente aggiornate:**
   - `docs/install.md` — rimosso prerequisito PowerShell Core.
   - `install-claude.md` — rimosso disclaimer pwsh.
   - `install-copilot.md` — rimosso disclaimer pwsh.

## Invarianti mantenuti

- **Principio XI (accesso solo via vehicle):** gli hook non importano `sertor_core` direttamente; invocati via uv + CLI è il vehicle.
- **Fail-safe/breadcrumb:** comportamento di FEAT-019 (`_hooklib.run()` exit 0 sempre; `.last-hook-error` secret-free).
- **Sertor-core untouched:** zero modifiche logica core retrieval (portabilità è distribuzione/asset).
- **Zero nuove dipendenze:** Python + `uv` + stdlib solo.

## Esiti

- **SpecKit completo** (specify → plan → tasks → implement su branch).
- **Constitution Check:** PASS 12/12 + missione PASS (portabilità = installabile ovunque).
- **Gate verde:** sertor 510 · kit 149 · root 1166 · flow 142 test verdi, ruff clean.
- **Parity verfica:** output per-assistente (Claude/Copilot) coincide coi `.ps1` precedenti.
- **Smoke CI matrice:** ubuntu + windows, Python 3.11+, ogni hook eseguibile.

**Prossimo:** merge su master + live dogfood migration (validazione T022 in `sertor upgrade`).

## Crosslink

- **[[feat-018-portabilita-os-hook]]** — superata; gap risotto per costruzione.
- **[[principle-xii]]** — Principio XII «Fix the Cause» — rimosso difetto alla radice.
- **[[principle-x]]** — Principio X host-agnostico — zero dipendenza PowerShell/OS.
- **[[sessionstart-hook]]** — riscritto in Python, portabile.
- **[[feat-019-fail-loud-hook-agent]]** — gemella; fail-loudness + fallback agent mantengono Principio XII.
- **[[assistant-targeting]]** — wiring OS-indipendente per Claude/Copilot.
- **[[sertor-install-kit]]** — helper `remove_hook_entries_by_command_substring` per migrazione legacy.
- **[[step-ritual]]** — regola standing MCP-first e smoke-test applicati.
- **[[dogfood-fidelity]]** — risoluzione empirica via dry-run + live install.
- **[[wiki-tools]]** — nessun hook wiki-specifico impattato (ortogonale).
