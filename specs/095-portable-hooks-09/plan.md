# Implementation Plan: Portabilità POSIX degli hook (hook portabili)

**Branch**: `095-portable-hooks-09` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: A-09 (assessment SWOT P1). Requisiti
`requirements/sertor-cli/portabilita-hook-python/requirements.md`. DA-1 lock = sostituzione single-impl
con parità-gate.

## Summary

Gli 8 hook host-facing sono PowerShell (`.ps1`), wirati `"shell": "powershell"` / `pwsh -File` → **inerti
su mac/Linux senza `pwsh`** (Principio X violato in pratica). Si riscrivono in **una** implementazione
**portabile** (Python) che gira sul Python fornito da **`uv`** (dipendenza d'install garantita), cablata in
modo **OS-indipendente**; a **parità provata** (gate pre-merge) i `.ps1` sono ritirati. Riscrittura
**iso-funzionale**: stessi effetti, stesso contratto di output per-assistente (Claude/Copilot), stessa
semantica fail-safe (exit 0, breadcrumb secret-free). `sertor-core` invariato (la logica hook vive negli
asset installer).

**Decisioni cardine (research):**
- **Invocazione portabile = `uv run --no-project python <hookpath>`** — `--no-project` **isola** dal
  `pyproject.toml` dell'host (senza cui `uv run python` userebbe l'env dell'host: sbagliato/lento) e **non**
  dipende da `.sertor/.venv`, quindi funziona anche per l'install **wiki-only** (DA-3). Gli hook che usano
  il RAG chiamano `uv run --project .sertor sertor-rag …` **internamente** (Principio XI), raggiunto solo
  sugli install RAG (runtime presente); altrimenti degradano fail-safe (FR-011).
- **Wiring OS-indipendente:** il comando dell'hook non usa più `"shell":"powershell"`; invoca `uv` (che è
  cross-OS). Il path dell'hook si risolve via `CLAUDE_PROJECT_DIR` / cwd = project dir.
- **Parità = gate pre-merge (DA-4):** test **offline** per hook (evento+input simulati su stdin → asserisce
  stdout per-assistente + effetti di stato) col comportamento dei `.ps1` come riferimento documentato; +
  **smoke CI su matrice** (ubuntu+windows) che esegue i Python-hook (non richiedono `pwsh`).

## Technical Context

**Language/Version**: Python ≥ 3.11 (hook portabili, stdlib only: `json`, `urllib`, `subprocess`, `sys`,
`os`, `pathlib`, `hashlib`). Interprete fornito da **`uv`** (già richiesto per installare Sertor).

**Primary Dependencies**: **zero nuove** — stdlib. `uv` (già presente). I `.ps1` vengono rimossi.

**Storage**: file di stato in `.sertor/` (`.rag-health.json`, `.version-check.json`, `.last-hook-error`) —
**invariati** (stessi path/schema).

**Testing**: `pytest` — test di **parità** offline (simulazione evento→output+stato) + guardie sync
dogfood↔bundle aggiornate; smoke CI su matrice ubuntu+windows.

**Target Platform**: ospiti Windows, macOS, Linux (l'obiettivo è la portabilità). `pwsh` non più richiesto.

**Project Type**: asset dell'installer (`packages/sertor/src/sertor_installer/assets/`); `sertor-core`
invariato.

**Performance Goals**: overhead per-hook comparabile a oggi (startup `uv run --no-project` ~ startup
powershell). Il `PreToolUse` (per-tool-use) resta non-bloccante e leggero (NFR-3).

**Constraints**: host-agnostico (X), fail-safe/exit 0 (IV/XII), install≠run (VI), zero dip nuove,
`sertor-core` invariato, no regressione Windows, parità provata prima del ritiro `.ps1`.

**Scale/Scope**: 8 hook riscritti + wiring (Claude `settings.json` + Copilot) + parità-test + guardie sync
+ ritiro `.ps1` + aggiornamento nota `pwsh` (E10-FEAT-018).

## Constitution Check

*GATE: pass prima di Phase 0, re-check dopo Phase 1.* Costituzione v1.4.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS. Gli hook sono **asset dell'installer**,
  non `sertor-core` (invariato). Chiamano il RAG solo via **vehicle** (CLI), non importano il core.
- [x] **II — Boundary & local-first:** N/A. Nessun provider/store toccato.
- [x] **III — YAGNI & unità piccole:** PASS. **Rimuove** la doppia implementazione (`.ps1`+eventuale `sh`)
  a favore di **una** sola; nessuna astrazione nuova; stdlib only.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS. Fail-safe con **breadcrumb** ispezionabile
  (degradazione che **segnala**), mai stato parziale/None silenzioso.
- [x] **V — Testabilità & misure:** PASS. **Verifica di parità** (offline + CI matrice) = gate pre-merge;
  ogni hook testato per output+stato con input simulati.
- [x] **VI — Idempotenza & install≠run:** PASS. Comportamento idempotente invariato; il deposito/wiring non
  avvia ingestioni (solo l'evento a runtime).
- [x] **VII — Leggibilità:** PASS. Un corpo per hook, nomi di dominio; niente doppio-binario da tenere in
  sync.
- [x] **VIII — Configurabilità centralizzata:** N/A (gli hook usano le env esistenti; nessun default di core
  nuovo).
- [x] **IX — Osservabilità:** PASS. Breadcrumb `.last-hook-error` (schema `hook.error/1`) preservato,
  secret-free.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS — **è il cuore della feature**. Elimina la dipendenza
  da una shell Windows-only; una implementazione operativa su ogni OS senza `pwsh`. Ripara la violazione
  pratica del Principio X (capacità inerte su un OS-family).
- [x] **XI — Consumo via vehicles:** PASS. Gli hook che toccano il RAG usano `uv run --project .sertor
  sertor-rag …` (CLI vehicle), mai `import sertor_core`.
- [x] **XII — Fail Loud, Fix the Cause:** PASS. Fail-safe **che segnala** (breadcrumb), non soppressione
  silenziosa; rimuove la causa (dipendenza pwsh) invece di aggirarla con una nota.
- [x] **Allineamento alla missione:** PASS. Portabilità = **installabile ovunque** (la missione): un ospite
  POSIX riceve capacità **funzionanti**, non inerti. Non deriva su concern periferici.

**Esito: 12/12 + missione PASS.** Nessuna violazione → nessun *Complexity Tracking*.

## Project Structure

### Documentation (this feature)

```text
specs/095-portable-hooks-09/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/hook-contract.md   # contratto per-assistente + fail-safe + parità
├── checklists/requirements.md   # (presente)
└── tasks.md                     # /speckit-tasks (dopo)
```

### Source Code (repository root)

```text
packages/sertor/src/sertor_installer/assets/
├── rag/hooks/                   # 6 hook RAG: .ps1 → .py portabili (memory-capture, rag-freshness(+start),
│                                #   sertor-rag-usage-check, version-check(+start))
├── claude/hooks/                # 2 hook wiki: wiki-pending-check, wiki-session-start → .py
├── rag/settings.*.json          # wiring Claude: "shell":"powershell" → invocazione uv run --no-project python
└── (Copilot) surfaces.py render_copilot_hooks   # wiring Copilot → stesso comando portabile

packages/sertor/src/sertor_installer/  # eventuale helper condiviso per il wiring portabile
packages/sertor-install-kit/…          # HookEntrySpec / render se il comando cambia forma

tests/…  packages/sertor/tests/…       # NUOVI: parità per-hook (offline) + guardie sync aggiornate
.claude/hooks/**                        # dogfood: i .py sincronizzati (sostituiscono i .ps1)
docs/install.md                         # aggiornare la nota pwsh (E10-FEAT-018) + operatività per OS
```

**Structure Decision.** La feature vive **interamente negli asset dell'installer** + il loro wiring +
i test di parità; `sertor-core` **invariato**. Un solo corpo per hook (Python), un solo comando di
invocazione portabile. DA-2/3/4 risolte in `research.md`.

## Complexity Tracking

> Nessuna violazione costituzionale → sezione vuota.
