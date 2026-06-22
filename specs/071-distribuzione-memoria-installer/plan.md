# Implementation Plan: Distribuzione della memoria via installer (FEAT-009)

**Branch**: `071-distribuzione-memoria-installer` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: `specs/071-distribuzione-memoria-installer/spec.md` (deriva da FEAT-009, epica
`memoria-conversazioni`; requirements `requirements/memoria-conversazioni/distribuzione-installer/`).

## Summary

Rendere installabile su un ospite, via `sertor install rag`, la capacità di memoria conversazioni oggi
accesa solo sul dogfood. Cambiamento **ADDITIVO** confinato ai pacchetti installer
(`sertor`/`sertor-install-kit`) e agli asset: (1) manopole memoria nei due template `.env`; (2) script
di cattura come asset + wiring `SessionEnd` per-assistente (Claude `.claude/settings.json`, Copilot
nativo `.github/hooks/sertor-hooks.json`); (3) cenno ai comandi `sertor-rag memory` nel blocco
istruzioni `SERTOR:RAG-USAGE`; (4) copertura lifecycle (upgrade/uninstall) + `sertor_owned_paths`.
`sertor-core` **invariato**. Riusa **identicamente** il pattern dell'hook rag-usage (FILE +
SETTINGS_MERGE + routing per-assistente + lifecycle inverso) già in `install_rag.py`.

## Technical Context

**Language/Version**: Python ≥ 3.11.
**Primary Dependencies**: `sertor-install-kit` (stdlib-only); nessuna nuova dipendenza (RNF-1).
**Storage**: N/A (deposita file/template; l'archivio `memory.sqlite` resta sotto `.sertor/`).
**Testing**: pytest (offline, `Fake*Runner`), suite `packages/sertor/tests/**`.
**Target Platform**: host-agnostico (Principio X); trigger di cattura assistant-specifico.
**Project Type**: pacchetti installer (`sertor` consumer del kit).
**Constraints**: additivo, idempotente, non-distruttivo, privacy-by-default, offline-verificabile.
**Scale/Scope**: ~6 file toccati (2 template, 2 nuovi asset, 1 blocco md, `install_rag.py`) + test.

## Constitution Check

Gate derivati dalla costituzione (v1.4.0). Tutti PASS.

- [x] **I — Dipendenze verso l'interno:** nessuna modifica al core; gli installer non importano SDK; il
  kit è stdlib-only. **PASS.**
- [x] **II — Boundary & local-first:** nessuna dipendenza esterna nuova; cattura locale; nessun cloud.
  **PASS.**
- [x] **III — YAGNI & unità piccole:** riuso dei tipi artefatto esistenti, **nessun nuovo `ArtifactKind`**
  (DA-c); cenno in blocco esistente (no nuovo marker, DA-a); script invariato (DA-b). **PASS.**
- [x] **IV — Errori espliciti:** percorsi d'installazione fail-fast del kit invariati; l'hook è
  non-fatale by design (privacy-gate → exit 0). **PASS.**
- [x] **V — Testabilità & misure:** install/upgrade/uninstall verificabili offline coi runner mock;
  guardia `plan ⊆ owned` estesa. **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** FILE create-if-absent, SETTINGS_MERGE dedup, ENV merge
  additivo; re-run stabile; nessun overwrite. **PASS.**
- [x] **VII — Leggibilità:** naming coerente coi gemelli (`_MEMORY_HOOK_*`, `_copilot_memory_hook_specs`).
  **PASS.**
- [x] **VIII — Configurabilità centralizzata:** le manopole restano in `Settings` (fonte unica); i
  template le **riflettono**, non ne introducono di nuove. **PASS.**
- [x] **IX — Osservabilità:** percorso d'installazione invariato (già osservato dal kit). **PASS.**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** manopole/archivio agnostici; trigger per-assistente via
  `AssistantProfile`; gap Copilot dichiarato (cattura = FEAT-008). **PASS.**
- [x] **XI — Consumo via vehicles:** l'hook invoca la **CLI** `sertor-rag memory archive` (vehicle), mai
  la libreria; il cenno indirizza l'agente ai comandi CLI/MCP. **PASS.**
- [x] **XII — Fail Loud, Fix the Cause:** la causa («memoria non distribuita») è rimossa cablandola
  nell'installer; il gap di cattura su Copilot è **dichiarato** (non silenziato) → FEAT-008. **PASS.**
- [x] **Allineamento alla missione:** distribuire la memoria estende l'auto-conoscenza **portabile** oltre
  il dogfood (freschezza/qualità del contesto reso nel tempo). **PASS.**

Nessuna deviazione → Complexity Tracking vuoto.

## Decisioni di design (forche risolte)

- **DA-a — Cenno istruzioni:** **poche righe nel blocco `SERTOR:RAG-USAGE` esistente**
  (`rag/claude-md-block-rag-usage.md`), non un nuovo marker. Meno superficie, nessun nuovo
  `shared_edit`/lifecycle; il cenno viaggia col blocco già instradato per-assistente.
- **DA-b — `-Assistant` sullo script:** **non serve.** L'hook `memory-capture.ps1` è già silenzioso ed
  esce 0 (SessionEnd non-bloccante); il corpo è **identico** su Claude e Copilot (FR-015). Varia solo il
  wiring (path container + formato nativo Copilot generato).
- **DA-c — Riuso vs nuovo `ArtifactKind`:** **riuso** `ArtifactKind.FILE` (CREATE_IF_ABSENT, byte-copy)
  per lo script e `ArtifactKind.SETTINGS_MERGE` (MERGE_DEDUP) per il wiring `SessionEnd`. Nessun tipo
  nuovo (RNF-1, gemello esatto dell'hook rag-usage).

## Change-list concreta (il *come*)

**Asset nuovi:**
- `assets/rag/hooks/memory-capture.ps1` — **byte-copy** dell'attuale `.claude/hooks/memory-capture.ps1`
  (canonico d'ora in poi); corpo invariato.
- `assets/rag/settings.memory-capture.json` — frammento wiring Claude `SessionEnd` che invoca
  `.claude/hooks/memory-capture.ps1` (shape gemella di `settings.hooks.json`/`settings.rag-usage.json`).

**Asset modificati:**
- `assets/rag/env.local.tmpl` **e** `assets/rag/env.azure.tmpl` — sezione «Conversation memory» con le 8
  manopole di `Settings`, `SERTOR_MEMORY` **commentata/off**, ognuna con commento d'uso/privacy.
- `assets/rag/claude-md-block-rag-usage.md` — sezione «Conversation memory (optional)» coi comandi
  `sertor-rag memory search/list/show/archive` e la condizione `SERTOR_MEMORY=true`.

**`install_rag.py`:**
- Costanti: `_MEMORY_HOOK_ASSET`, `_MEMORY_HOOK_TARGET` (`.claude/hooks/memory-capture.ps1`),
  `_MEMORY_HOOK_TARGET_COPILOT` (`.github/hooks/memory-capture.ps1`), `_MEMORY_CAPTURE_SETTINGS`
  (`rag/settings.memory-capture.json`), `_COPILOT_MEMORY_WIRING_SENTINEL`.
- `_copilot_memory_hook_specs()` → `[HookEntrySpec("SessionEnd","command", f"{_PWSH}
  {_MEMORY_HOOK_TARGET_COPILOT}", 15)]` (nessun matcher; render nativo `sessionEnd`).
- `build_rag_plan`: appende, dopo le eval-skill, `FILE`(memory hook) + `SETTINGS_MERGE`(wiring
  memory) instradati per-assistente (sentinel su Copilot, asset Claude).
- `_rag_hook_fragment(art)`: aggiungi il ramo `_COPILOT_MEMORY_WIRING_SENTINEL → render_copilot_hooks(
  _copilot_memory_hook_specs())`; il ramo Claude legge `art.source` (già generico → gestisce sia
  rag-usage sia memory).
- Uninstall: il branch SETTINGS_MERGE usa `_rag_hook_fragment(art)` (art-aware) al posto del vecchio
  `_rag_settings_fragment(art, is_copilot)` che ignorava `art.source` (rischio di rimuovere il frammento
  sbagliato); `_rag_settings_fragment` rimosso. `delete_if_empty` su `sertor-hooks.json` invariato.
- `sertor_owned_paths`: aggiungi il memory hook target a `owned_files` (il target settings è già coperto
  dal `shared_edit` esistente → coverage `plan ⊆ owned` soddisfatta).

**Test:**
- `tests/test_install_rag_usage.py`: aggiorna `test_plan_contains_rag_usage_artifacts` (ora ≥1
  SETTINGS_MERGE, non `== 1`; assert presenza rag-usage).
- Nuovo `tests/test_install_rag_memory.py`: plan contiene FILE+SETTINGS memory (Claude+Copilot); hook
  depositato; `SessionEnd` cablato e dedup (preserva hook utente + coesiste con rag-usage/wiki);
  idempotenza; uninstall rimuove memory preservando altri; copilot wiring generato nativo; blocco md
  contiene il cenno memoria; gating privacy (env `SERTOR_MEMORY` off).
- Nuovo `tests/unit/test_env_template_memory.py` (anti-drift R-4): i due template contengono le 8 chiavi
  di `Settings` con `SERTOR_MEMORY` off.

## Project Structure

```text
specs/071-distribuzione-memoria-installer/
├── plan.md        # questo file
├── spec.md        # /speckit-specify
├── research.md    # decisioni di design (forche DA-a/b/c) — sintetizzate qui
├── data-model.md  # entità d'installazione coinvolte
└── tasks.md       # /speckit-tasks
```

**Source (repo):** `packages/sertor/src/sertor_installer/install_rag.py` +
`packages/sertor/src/sertor_installer/assets/rag/**` + `packages/sertor/tests/**`.

**Structure Decision**: nessuna nuova struttura; estensione mirata del plan-builder rag e degli asset,
riuso del `sertor-install-kit`.

## Complexity Tracking

*Nessuna violazione del Constitution Check → tabella vuota.*
