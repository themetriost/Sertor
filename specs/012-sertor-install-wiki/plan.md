# Implementation Plan: Installer `sertor` + `sertor install wiki`

**Branch**: `012-sertor-install-wiki` | **Date**: 2026-06-11 | **Spec**: [`spec.md`](spec.md)

**Input**: Feature specification from `specs/012-sertor-install-wiki/spec.md`
**Requisiti EARS**: `requirements/sertor-cli/installer/requirements.md` (REQ-100..143, DI-1..DI-5 risolte)

## Summary

Backbone del comando `sertor` (console-script, sottocomandi estensibili, help, exit code 0/1/2) +
primo sottocomando `sertor install wiki`, che porta sull'ospite l'intero sistema-wiki (skill
wiki-author, comando `/wiki`, agente wiki-curator, hook di sessione con merge in `settings.json`,
sezione step-ritual nel `CLAUDE.md` via blocco a marker, `wiki.config.toml` con default inferiti,
struttura `wiki/`). Approccio (da `research.md`): **pacchetto `sertor` distinto** in uv workspace
(`packages/sertor/`, modulo `sertor_installer`) che dipende da `sertor-core` (D1); artefatti come
**package-data** in `sertor_installer/assets/`, letti con `importlib.resources`, con la **fonte negli
assets** e `.claude/` del repo Sertor come **derivato** mantenuto allineato da un **test di sync**
anti-drift (D2/D3). L'installer è un **layer sottile** su file system: riusa
`sertor_core.wiki_tools.init_structure`/`load_profile` (D-1) e le eccezioni di dominio del core; non
duplica logica, non avvia LLM/rete/indicizzazione (install ≠ run). Non-distruttività per artefatto
(file-per-file, merge dedup-per-command, marker idempotente), fail-fast senza rollback, report su
stdout + exit code.

## Technical Context

**Language/Version**: Python ≥ 3.11 (vincolo d'epica V-4; coerente con `pyproject.toml:6`).

**Primary Dependencies**: `sertor-core` (riuso `wiki_tools` + `domain.errors`); stdlib
`argparse`, `importlib.resources`, `json`, `tomllib`/`tomli_w` per generare il TOML, `pathlib`.
Nessuna dipendenza pesante (niente SDK provider, niente rete).

**Storage**: file system del repo ospite (nessun DB). Artefatti = package-data nel wheel.

**Testing**: `pytest` su repository temporanei (fixture `tmp_path`); marker `not cloud`; nessuna
rete/LLM (NFR-I-01, SC-006). Test di sync assets ⇄ `.claude/` (D2).

**Target Platform**: Linux + Windows (NFR-I-04). L'installer è Python puro e portabile; l'hook
bundlato è PowerShell (eseguito poi dall'harness, non dall'installer; D6).

**Project Type**: CLI installer (secondo pacchetto Python del monorepo, consumatore di `sertor-core`).

**Performance Goals**: N/A (operazione one-shot su pochi file; nessun obiettivo di throughput).

**Constraints**: offline-capable (by construction, package-data); idempotente e non-distruttivo
(Principio VI); host-agnostico (Principio X); install ≠ run (FR-007/022/REQ-140).

**Scale/Scope**: ~12 artefatti installati; backbone + 1 sottocomando + 2 stub. Nessun
NEEDS CLARIFICATION residuo (DI-* chiuse a monte; D1..D8 risolte in `research.md`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Valutazione PRE-design (prima di Phase 0)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS. L'installer è un consumatore di
  `sertor-core`; dipende dalle sue funzioni/eccezioni, mai il contrario. Pacchetto **distinto**
  (D1) rende la dipendenza fisica e mono-direzionale. Non importa SDK di provider.
- [x] **II — Boundary & local-first:** PASS (N/A pieno). L'installer non ha provider esterni:
  opera solo su file. Nessun vector store/LLM coinvolto.
- [x] **III — YAGNI & unità piccole:** PASS. Layer sottile; nessuna astrazione speculativa.
  `--json`/`--upgrade`/variante hook Linux esplicitamente differiti (Could/futuri).
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS. Eccezioni di dominio del core
  (`SertorError`/`ConfigError`/`IngestionError`); fail-fast su errore, nessuno stato corrotto;
  JSON malformato → errore esplicito, mai riscrittura silenziosa.
- [x] **V — Testabilità & misure:** PASS. Test F.I.R.S.T. su `tmp_path`, offline. La clausola
  "misura del retrieval (hit@k/MRR)" **non si applica** (questa feature non fa retrieval); la
  misura rilevante è SC-001..008 (verificabili su filesystem).
- [x] **VI — Idempotenza & non-distruttività:** PASS — è il cuore della feature. Re-run stabile
  (skip/merge dedup/marker), install ≠ run, nessuna sovrascrittura silenziosa.
- [x] **VII — Leggibilità:** PASS. Naming di dominio dell'installer (`Artifact`, `InstallPlan`,
  `InstallReport`, `HostProfile`; verbi `install`/`merge`/`generate`).
- [x] **VIII — Configurabilità centralizzata:** PASS. I default del `wiki.config.toml` generato
  stanno nel **template negli assets** (NFR-I-07), non hard-coded nel codice; il codice inietta solo
  `language`/`source_dirs`.
- [x] **IX — Osservabilità:** PASS (proporzionato). L'install è un'operazione su file: il
  **report** è la sua osservabilità (FR-025). Log strutturati via `observability` del core dove
  utile (es. `init_structure` già logga, `structure.py:64`). Nessun segreto nei log/file (FR-019).
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS **con azione**. Gli artefatti bundlati devono
  essere ripuliti dalle note "profilo Sertor" (D3): il comportamento è già host-agnostico (legge da
  `wiki.config.toml`), ma SC-004 chiede zero riferimenti *testuali* → riformulazione degli esempi
  negli assets, verificata da test di scansione. Nessuna deroga.

**Esito PRE-design: PASS (10/10).** Nessuna voce in Complexity Tracking. L'unica azione vincolante è
X (ripulitura assets), tracciata in D3 e nei tasks.

### Valutazione POST-design (dopo Phase 1)

Rivalutazione dopo `research.md`, `data-model.md`, `contracts/`, `quickstart.md`:

- **I** — PASS confermato. `data-model.md §6` fissa il confine: l'installer riusa
  `wiki_tools.init_structure`/`load_profile` e gli errori del core; non duplica logica. La direzione
  della dipendenza resta verso `sertor-core`.
- **IV** — PASS confermato. `contracts/cli-commands.md` (exit 0/1/2) e `install-report.md`
  (fail-fast + `failed_step`) codificano errori espliciti; edge case JSON malformato → fail-fast.
- **VI** — PASS confermato. Contratti di `claude-md-block.md` (skip-on-present) e `install-report.md`
  (re-run tutto skipped/merged-0) dimostrano l'idempotenza; `data-model §3` fissa install ≠ run.
- **VIII** — PASS confermato. D7 mette i default nel template degli assets; il codice non li
  hard-coda; invariante "config generata passa `load_profile`" verificata da test.
- **X** — PASS confermato. D3 + `contracts/claude-md-block.md` impongono contenuto host-agnostico;
  SC-004 ha un test di scansione con whitelist sui nomi-comando di prodotto. `language` default `en`
  (non l'italiano di Sertor); `exclude` senza `prototype/`; `source_dirs` euristica generica.
- **II/III/V/VII/IX** — invariati rispetto al pre-design (nessuna scelta di Phase 1 li tocca).

**Esito POST-design: PASS (10/10).** Nessuna nuova violazione introdotta dal design. Complexity
Tracking vuoto.

## Project Structure

### Documentation (this feature)

```text
specs/012-sertor-install-wiki/
├── plan.md              # questo file
├── research.md          # Phase 0 — decisioni D1..D8
├── data-model.md        # Phase 1 — Artifact/InstallPlan/InstallReport/HostProfile
├── quickstart.md        # Phase 1 — guida operativa
├── contracts/           # Phase 1 — CLI, report, blocco marker
│   ├── cli-commands.md
│   ├── install-report.md
│   └── claude-md-block.md
├── spec.md              # input
├── checklists/          # esistente (checklist verde)
└── tasks.md             # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)

```text
# Monorepo a due pacchetti. sertor-core invariato; nuovo pacchetto `sertor`.

pyproject.toml                          # root: sertor-core (invariato) + [tool.uv.workspace]
src/sertor_core/                        # invariato — riuso: wiki_tools/, domain/errors.py
src/sertor_mcp/                         # invariato

packages/sertor/                        # NUOVO pacchetto `sertor` (D1)
├── pyproject.toml                      # depends on sertor-core; [project.scripts] sertor = ...
├── src/sertor_installer/
│   ├── __init__.py
│   ├── __main__.py                     # backbone CLI argparse (pattern cli/__main__.py)
│   ├── install_wiki.py                 # InstallPlan: orchestrazione degli Artifact (sottile)
│   ├── artifacts.py                    # Artifact/WriteStrategy + scrittura per strategia
│   ├── settings_merge.py              # merge dedup-per-command (D5)
│   ├── claude_md.py                    # blocco a marker (D4)
│   ├── config_gen.py                   # HostProfile + euristica source_dirs + template (D7)
│   ├── report.py                       # InstallReport (umano + --json)
│   ├── resources.py                    # accesso assets via importlib.resources (D2)
│   ├── sync.py                         # sync assets → .claude/ in sviluppo (D2)
│   └── assets/                         # package-data (D2/D3)
│       ├── claude/{skills/wiki-author/*, commands/wiki.md, agents/wiki-curator.md, hooks/*.ps1}
│       ├── settings.hooks.json         # frammento delle 3 voci hook
│       ├── claude-md-block.md          # contenuto della sezione step-ritual (dentro i marker)
│       └── wiki.config.toml.tmpl       # template del profilo
└── tests/
    ├── test_install_wiki.py            # US1/US2: repo vuoto, re-run, pre-popolato
    ├── test_settings_merge.py          # D5: dedup, malformato → fail-fast
    ├── test_claude_md.py               # D4: marker idempotente, fuori-blocco intatto
    ├── test_config_gen.py              # D7: euristica + passa load_profile
    ├── test_cli.py                     # backbone: help, stub, exit code (SC-007)
    ├── test_host_agnostic.py           # SC-004: scansione zero «Sertor»
    └── test_assets_sync.py             # D2: assets ⇄ .claude/ allineati
```

**Structure Decision**: secondo pacchetto Python (`packages/sertor/`, modulo importabile
`sertor_installer`, console-script `sertor`) in uv workspace, dipendente da `sertor-core` (D1). Gli
artefatti non-Python sono package-data sotto `sertor_installer/assets/` (D2). Il `pyproject.toml` di
root resta invariato per `sertor-core`; si aggiunge solo `[tool.uv.workspace] members =
["packages/sertor"]`. Se in `tasks` il workspace risultasse problematico con la versione di `uv` del
repo, il fallback è il modulo dentro il wheel `sertor-core` (research D1 alt. (b)) — ma con deroga a
REQ-100 da registrare qui in Complexity Tracking.

## Complexity Tracking

> Nessuna violazione del Constitution Check da giustificare (PASS 10/10 pre e post-design).
> Tabella intenzionalmente vuota.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
