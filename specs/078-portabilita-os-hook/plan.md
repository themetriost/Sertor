# Implementation Plan — Portabilità OS degli hook (guardia `pwsh` + gap dichiarato) + onestà surface inerti

**Branch**: `078-portabilita-os-hook` · **Spec**: [`spec.md`](./spec.md) · **Data**: 2026-06-30
**Epica**: debito-tecnico (E10) · **FEAT**: 018 · **Input**:
`requirements/debito-tecnico/portabilita-os-hook/requirements.md`

> **Nota di processo.** `.specify/scripts/powershell/setup-plan.ps1` e
> `.claude/skills/speckit-plan/SKILL.md` **assenti** (come 074–077) → parametri per convenzione dal
> branch; nessun hook eseguito. **MCP `sertor-rag` interrogato** (`search_code` su `InstallReport.notes`
> e sul wiring hook per-assistente) — **nessun errore tool**.

## Summary

Rende **onesti** due claim impliciti dell'installer, senza toccare `sertor_core` (Principio XI). (1)
**Guardia `pwsh` install-time**: su host non-Windows in cui `pwsh` (PowerShell Core) non è in PATH, un
`sertor install rag`/`wiki` che deposita hook `.ps1` non li dichiara operativi — aggiunge una **nota
azionabile** (surface affetti + URL d'installazione) a `InstallReport.notes`, visibile in resa umana e
JSON; non-fatale (exit 0); nessuna nota su Windows o con `pwsh` presente. (2) **Onestà su Copilot CLI**:
ogni `install rag --assistant copilot-cli` emette una nota che dichiara che `memory-capture` richiede
`SERTOR_MEMORY=true` + `SERTOR_MEMORY_ADAPTER=copilot-cli` e cross-referenzia la capacità pianificata
(FEAT-009 memorie). (3) **Documentazione utente** (`docs/install.md`, `docs/install-copilot.md`,
tabella capability `packages/sertor/docs/install.md`) che dichiara il prerequisito `pwsh` e l'operatività
per-target. (4) **Guard tests** deterministici (OS mocking) + sync dogfood↔bundle verde.

**Strategia FISSATA (non riaperta):** guardia + gap dichiarato, hook **PowerShell-only** (nessun gemello
`.sh`). Onestà via il meccanismo **esistente** `InstallReport.notes` (prima emissione reale in produzione).

## Technical Context

- **Linguaggio:** Python ≥ 3.11. **Pacchetti toccati:** `sertor-install-kit` (nuovo modulo puro
  `host_env.py`), `sertor` (`install_rag.py`, `install_wiki.py`), `docs/`. **`sertor-core` INVARIATO.**
- **Dipendenze:** solo **stdlib** (`os`, `shutil`). Nessuna nuova dipendenza, nessun extra.
- **Storage/stato:** nessuno (no file di stato; la nota vive nel report in-memory, schema
  `install.report/1` invariato).
- **Test:** `uv run pytest` (offline, OS mocking via `monkeypatch.setattr(host_env, …)`), `ruff`.
- **Confine D↔N:** rilevamento `pwsh` ed emissione note = **meccanici** (codice installer, nessun LLM);
  l'azione sui gap resta all'agente/utente.
- **NEEDS CLARIFICATION:** nessuno. Le 2 forche residue (DA-D-r1/r2) e il quesito sul wiring (D-3) sono
  risolti in `research.md`.

## Constitution Check (PRE-design) — costituzione v1.4.0 (12 principi + missione)

| Gate | Esito | Motivo |
|---|---|---|
| **Allineamento alla missione** | **PASS** | Hook/installer esistono per tenere **reale** il contesto reso all'agente (freschezza RAG, cattura memoria). Un installer che dichiara operativi hook che su mac/Linux non partono mai è il modo in cui l'apparato si scopre rotto settimane dopo. Rendere la portabilità **onesta** *protegge* la stella polare. |
| I. Core dipendenze verso l'interno | **PASS** | `sertor_core` invariato; modifica confinata a installer + doc. |
| II. Provider/backend dietro boundary | **N/A** | Nessun provider/store toccato. |
| III. Semplicità (YAGNI), unità piccole | **PASS** | Un modulo puro + 4 funzioni piccole; riuso del contratto `notes` esistente; nota memory in `install_rag` (single consumer, no porta). |
| IV. Errori espliciti, niente null silenzioso | **PASS** | La guardia **segnala** (nota), non sopprime; non introduce ritorni `None`. |
| V. Testabilità e misura | **PASS** | Guard tests deterministici (OS mocking, F.I.R.S.T.); builder/gating puri. |
| VI. Idempotenza/non-distruttività | **PASS** | `.note()` deduplica; nessun asset/file utente toccato; install≠run. |
| VII. Leggibilità | **PASS** | Nomi rivelatori (`pwsh_unavailability_note`, `maybe_note_pwsh`); guard clause. |
| VIII. Config centralizzata core | **N/A** | Nessuna config core; nessun nuovo env. |
| IX. Osservabilità | **PASS** | La nota **è** osservabilità d'install (Principio IX del report). |
| X. Host-agnostico | **PASS** | Check binario su qualunque host non-Windows, nessun hardcoding di distro; rende la portabilità **reale**. |
| XI. Consumo via vehicles | **PASS** | Codice installer Python; **zero** import di `sertor_core`, nessun LLM. |
| XII. Fail Loud, Fix the Cause | **PASS** | È **l'essenza** della feature: il fallimento silenzioso (exit 0 senza hook) diventa segnale visibile e azionabile. |

**Esito PRE: PASS 12/12 + missione PASS.** Nessuna deroga. Complexity Tracking **vuoto**.

## Project Structure (artefatti del design)

```
specs/078-portabilita-os-hook/
├─ spec.md            # input
├─ plan.md            # questo file
├─ research.md        # forche risolte (D-1/D-2/D-3) + ancoraggio
├─ data-model.md      # host_env + le 2 note + derivazione hook surfaces
├─ contracts/
│  ├─ install-notes.md  # contenuto/substringhe stabili delle 2 note (schema install.report/1)
│  └─ pwsh-guard.md     # tabella di verità + invarianti della guardia
└─ quickstart.md      # verifiche offline (OS mocking)
```

## Phase 0 — Research (sintesi; dettaglio in `research.md`)

- **D-1 (DA-D-r1):** logica `pwsh` in **helper condiviso del kit** (`host_env.py`) — DRY (rag+wiki
  oggi, `sertor-flow` domani), seam di mock unico, Principio XI/X. La nota `memory-capture` resta in
  `install_rag.py` (rag-specifica).
- **D-2 (DA-D-r2):** nota `memory-capture` **sempre** su install rag Copilot CLI (anticipatoria,
  default-state visibility, install-time non conosce il `SERTOR_MEMORY` runtime); **sì** aggiornare la
  tabella capability `packages/sertor/docs/install.md` (sezione testo + nota in tabella).
- **D-3 (finding wiring):** guardia **rileva+segnala**, **non** riscrive il wiring (cambiare
  `shell:powershell`→`pwsh` romperebbe Windows 5.1 → NFR-5). Limite tecnico aperto (semantica `shell`
  Claude su non-Windows) **dichiarato** nei doc + **promosso a candidata follow-up**, non inventato; la
  nota resta **narrow** su «`pwsh` non trovato».

## Phase 1 — Design & contracts

**Modifiche (enumerate):**

1. **`sertor-install-kit/src/sertor_install_kit/host_env.py` (NUOVO):** `is_windows`,
   `pwsh_available`, `pwsh_unavailability_note(hook_surfaces)`, `maybe_note_pwsh(report, hook_surfaces)`,
   `PWSH_INSTALL_URL`. Puro stdlib, mockabile.
2. **`install_rag.py::execute_rag_plan`:** dopo `_kit_execute_plan` → derivare
   `hook_surfaces = [a.target_rel for a in plan if a.target_rel.endswith(".ps1")]`; chiamare
   `maybe_note_pwsh(report, hook_surfaces)`; se `assistant is COPILOT_CLI` → `report.note(<memory note>)`.
   Nuova costante modulo per il testo `memory-capture` (con `SERTOR_MEMORY`/`SERTOR_MEMORY_ADAPTER` +
   cross-ref FEAT-009). Aggiornare il commento stale a `:146-148` («INERT until adapter exists» →
   l'adapter esiste; manca la distribuzione del valore, FEAT-009).
3. **`install_wiki.py::execute_plan`:** dopo `_kit_execute_plan` → `maybe_note_pwsh(report, hook_surfaces)`.
4. **Doc utente:** `docs/install.md` (§5/§6/§10.1: prerequisito `pwsh` su mac/Linux con URL + elenco
   surface + frase «installati ma non-operativi»; **nuova** sezione/tabella operatività-per-target);
   `docs/install-copilot.md` (§1: hook richiedono `pwsh` su mac/Linux + `memory-capture` richiede
   `SERTOR_MEMORY`/`SERTOR_MEMORY_ADAPTER`); `packages/sertor/docs/install.md` (tabella capability +
   nota operatività per target).
5. **Test (guard):** `sertor-install-kit/tests/unit/test_host_env.py` (builder/gating puri);
   `packages/sertor/tests/…` — nota pwsh (assente/presente/Windows → `[]`) su rag e wiki; nota
   `memory-capture` su rag Copilot, assente su Claude; estensione/preservazione di
   `test_claude_report_has_no_gap_note`. OS mocking via `monkeypatch.setattr(host_env, …)` (R-6).
6. **Sync:** nessun asset toccato → `tests/unit/test_assets_sync.py` verde per costruzione (FR-015).

**Contratti:** vedi `contracts/install-notes.md` (substringhe stabili delle 2 note, schema invariato) e
`contracts/pwsh-guard.md` (tabella di verità + invarianti). **CLAUDE.md** aggiornato (riferimento piano).

## Constitution Check (POST-design)

Il design non introduce: nuove porte/`ArtifactKind`/`Surface`/`WriteStrategy`/seam del kit; nuove
dipendenze; nuovi schemi; nuovi env; codice in `sertor_core`; alcun LLM. È **additivo** (a comportamento
sano `report.notes == []`, JSON byte-identico). Tutti i gate **PRE** restano validi. **Esito POST: PASS
12/12 + missione PASS.** Nessuna deroga; Complexity Tracking **vuoto**.

## Tracciamento scope (Out-of-Scope promossi)

- Distribuzione `SERTOR_MEMORY_ADAPTER=copilot-cli` nel template `.env` → **FEAT-009 epica
  memoria-conversazioni** (qui solo la nota). · Visibilità SessionStart Copilot → **E10-FEAT-008**. ·
  Wiring hook Claude portabile su non-Windows → **candidata follow-up** (roadmap → *Nuove funzionalità
  da discutere*; verificare semantica `shell` Claude Code). · Nota su percorso `upgrade` → estensione
  triviale futura (non FEAT). · Pulizia stile body hook/`CLAUDE.md` → **FEAT-021/022**. · Gemello `.sh` +
  guardia `pwsh` runtime → **Won't** (decisione utente). Nessun rinvio reale resta sepolto in `specs/`.

## Progress

- [x] Phase 0 — research.md (forche risolte, ancoraggio MCP)
- [x] Phase 1 — data-model.md · contracts/ · quickstart.md · CLAUDE.md aggiornato
- [x] Constitution Check PRE: **PASS 12/12 + missione**
- [x] Constitution Check POST: **PASS 12/12 + missione**
- [ ] Phase 2 — `/speckit-tasks` (fuori da questo plan)
