# Implementation Plan: Rimozione stub `assets/copilot/` (E10-FEAT-023)

**Branch**: `081-stub-copilot` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/081-stub-copilot/spec.md` · Requirements:
`requirements/debito-tecnico/stub-copilot/requirements.md` (epica debito-tecnico E10, audit ISSUE-09).

## Summary

Feature **sottrattiva / igiene host-facing**: rimuove il tree stub
`packages/sertor/src/sertor_installer/assets/copilot/**` — 4 file `.gitkeep` + 4 directory vuote
(`agents/`, `hooks/`, `instructions/`, `prompts/`) + `copilot/` stessa. Le dir furono create in
FEAT-044 ipotizzando asset Copilot statici; in FEAT-049 i JSON allora presenti furono rimossi e
sostituiti dalla **generazione a runtime nativa** (`render_copilot_hooks`/`render_custom_agent`/
`render_prompt_file`), lasciando il tree vuoto e **fuorviante** (suggerisce asset statici che non
esistono). Lo stato reale: i payload Copilot sono generati **interamente** da `assets/claude/**` e
`assets/rag/**`; **zero consumatori** leggono `assets/copilot/` (verificato).

**Approccio (design):** rimozione dei 4 `.gitkeep` (le dir vuote scompaiono — git non traccia dir
vuote), **nessun file di rimpiazzo** (Opzione A fissata), + una **guardia anti-ricomparsa leggera**
(estensione di `test_assets_copilot_guard.py`, asserisce l'assenza della dir via `asset_path`). **ZERO
modifiche a `sertor_core`** e **zero modifiche al codice di `install_rag.py`/`surfaces.py`**: la
generazione Copilot resta byte-identica. Due forche di *come* risolte: **DA-D-1** → estensione del guard
esistente (non file nuovo); **DA-D-2** → **nessun** commento in `install_rag.py` (viola l'out-of-scope
«install_rag.py invariato»; l'intento vive nella docstring del test, enforced).

Dettaglio in [research.md](./research.md), [data-model.md](./data-model.md),
[contracts/guard-anti-reappearance.md](./contracts/guard-anti-reappearance.md),
[quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: Python ≥ 3.11 (package `sertor`, `sertor_installer`).

**Primary Dependencies**: nessuna nuova. Riuso dell'API asset esistente
`sertor_installer.resources.asset_path` per la guardia; build via hatchling (glob ricorsivo).

**Storage**: N/A — la feature rimuove file statici nel package; nessun dato a runtime.

**Testing**: pytest (suite `sertor` + root); `test_assets_copilot_guard.py` (esteso),
`test_assets_copilot_parity.py`, `test_install_rag_copilot_cli.py`, `tests/integration/test_packaging.py`.

**Target Platform**: tooling di sviluppo/installer host-agnostico; nessun runtime del core coinvolto.

**Project Type**: pacchetto installer (`sertor`) — refactor sottrattivo di asset statici.

**Performance Goals**: N/A.

**Constraints**: zero codice di `sertor_core` (Principio XI); generazione Copilot byte-identica
(NFR-2); nessuna modifica a `pyproject.toml` (hatchling glob ricorsivo); offline/deterministico per i
test.

**Scale/Scope**: 4 file `.gitkeep` rimossi + 1 test additivo; nessuna modifica al codice Python di
runtime, ai test esistenti, agli altri asset.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gate derivati dalla costituzione (`.specify/memory/constitution.md`, v1.4.0).

### PRE-design (prima di Phase 0)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** **N/A** — nessun codice del core toccato;
  nessun import di SDK. PASS.
- [x] **II — Boundary & local-first:** **N/A** — nessuna dipendenza esterna introdotta. PASS.
- [x] **III — YAGNI & unità piccole:** **PASS** — rimuove artefatto superfluo; aggiunge solo una guardia
  minimale (singola asserzione), nessuna astrazione nuova.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** **N/A** — nessun percorso di errore nuovo. PASS.
- [x] **V — Testabilità & misure:** **PASS** — guardia anti-ricomparsa additiva (F.I.R.S.T., offline);
  non-regressione dell'intera suite verificata.
- [x] **VI — Idempotenza & non-distruttività:** **PASS** — rimozione idempotente; tocca **file del
  nostro package**, mai file dell'ospite; install≠run preservato.
- [x] **VII — Leggibilità:** **PASS** — lascia il repo più pulito (Boy Scout): elimina struttura
  ingannevole; l'intento è documentato nella docstring del test.
- [x] **VIII — Configurabilità centralizzata:** **N/A** — nessuna scelta operativa/config. PASS.
- [x] **IX — Osservabilità:** **N/A** — nessuna operazione a runtime. PASS.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** **PASS** — la generazione Copilot resta derivata da
  sorgenti neutre; nessuna assunzione d'ospite introdotta/rimossa.
- [x] **XI — Consumo via vehicles:** **PASS** — zero `sertor_core`; la pipeline Copilot
  (`build_rag_plan`/`surfaces`) resta invariata; nessun import di libreria.
- [x] **XII — Fail Loud, Fix the Cause:** **PASS** — rimuove la *causa* (stub fuorviante) invece di
  documentarla con un README che può divergere; la guardia **fallisce loud** se lo stub riappare.
- [x] **Allineamento alla missione:** **PASS** — la stella polare è la **realtà del contesto reso** a
  chi legge il repo (agente e manutentore); un tree di dir vuote comunica un'architettura inesistente.
  Rimuoverlo fa sì che lo stato del repo rifletta la realtà — coerente col principio che il contesto non
  deve disinformare. Igiene sul confine D↔N, nessun core, nessun LLM.

**Esito PRE: PASS 12/12 + missione PASS.** Nessuna deroga. Complexity Tracking **vuoto**.

### POST-design (dopo Phase 1)

Il design conferma la natura sottrattiva: rimozione di 4 `.gitkeep` + 1 test additivo, **zero** modifiche
a `sertor_core`, `install_rag.py`, `surfaces.py`, `pyproject.toml`, agli asset `claude/**`/`rag/**` e ai
test esistenti. Le due forche risolte non introducono codice di runtime (DA-D-1 = test additivo nel guard
esistente; DA-D-2 = nessun commento → `install_rag.py` invariato).

- I N/A · II N/A · III PASS · IV N/A · V PASS · VI PASS · VII PASS · VIII N/A · IX N/A · X PASS ·
  XI PASS · XII PASS · **Missione PASS**.

**Esito POST: PASS 12/12 + missione PASS.** Nessuna deroga; Complexity Tracking **vuoto**.

## Project Structure

### Documentation (this feature)

```text
specs/081-stub-copilot/
├── plan.md              # questo file
├── research.md          # Phase 0 (R-0..R-4: zero-consumatori, DA-D-1, DA-D-2, packaging, debiti)
├── data-model.md        # Phase 1 (entità: tree rimosso, pipeline invariata, guardie, guardia nuova)
├── quickstart.md        # Phase 1 (sequenza operativa + verifiche)
├── contracts/
│   └── guard-anti-reappearance.md   # contratto della guardia anti-ricomparsa
└── checklists/          # (pre-esistente)
```

### Source Code (repository root)

```text
packages/sertor/
├── src/sertor_installer/
│   ├── assets/
│   │   ├── claude/**          # INVARIATO — sorgente reale dei payload (anche Copilot)
│   │   ├── rag/**             # INVARIATO — sorgente reale dei payload (anche Copilot)
│   │   └── copilot/           # >>> RIMOSSO <<< (4 .gitkeep + 4 dir vuote + copilot/)
│   ├── install_rag.py         # INVARIATO (DA-D-2: nessun commento aggiunto)
│   ├── surfaces.py            # INVARIATO (render_* riesportate dal kit)
│   └── resources.py           # INVARIATO (asset_path riusato dalla guardia)
├── tests/
│   ├── test_assets_copilot_guard.py     # ESTESO: + test_no_copilot_asset_directory
│   ├── test_assets_copilot_parity.py    # INVARIATO (resta verde)
│   └── test_install_rag_copilot_cli.py  # INVARIATO (resta verde)
└── pyproject.toml             # INVARIATO (hatchling glob ricorsivo)

tests/integration/test_packaging.py      # INVARIATO (resta verde)
```

**Structure Decision**: refactor **sottrattivo** confinato al package `sertor` (`sertor_installer`).
L'unico file modificato è `tests/test_assets_copilot_guard.py` (estensione additiva); gli unici file
rimossi sono i 4 `.gitkeep`. Nessun altro pacchetto (`sertor-core`, `sertor-install-kit`, `sertor-flow`)
toccato.

## Phasing & verifica (dal quickstart)

1. **Riconferma zero-consumatori** (FR-005): grep `read_asset_text/iter_asset_dir/asset_path("copilot`)
   → atteso zero. Se emergesse un consumatore, **correggerlo prima** della rimozione.
2. **Rimozione** dei 4 `.gitkeep` (FR-001/002); nessun file di rimpiazzo (FR-003).
3. **Guardia anti-ricomparsa** (FR-008): `test_no_copilot_asset_directory` nel guard esistente.
4. **Non-regressione**: guard + parity + install-copilot + `uv build -p sertor` + packaging test + suite
   completa + `ruff` → zero nuovi fallimenti (CS-2/CS-3/CS-4).

## Complexity Tracking

*Nessuna violazione del Constitution Check → tabella vuota.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Note di processo

- `.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** nel
  repo → parametri ricavati per convenzione dal branch (`FEATURE_SPEC=specs/081-stub-copilot/spec.md`,
  `IMPL_PLAN=specs/081-stub-copilot/plan.md`, `SPECS_DIR=specs/081-stub-copilot`,
  `BRANCH=081-stub-copilot`); nessun hook SpecKit eseguito.
- **MCP `sertor-rag`**: non interrogato in questa sessione — il lavoro è su asset/codice locale con
  posizioni note (grep mirate + `Read`), nell'eccezione «fatto puntuale a posizione nota» della regola
  MCP-first. Nessun tool MCP invocato → **nessun errore MCP da segnalare**.
- Git **non eseguito** (delega al `configuration-manager`); brief di commit nel report finale.
