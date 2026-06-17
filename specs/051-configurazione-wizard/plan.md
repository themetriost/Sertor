# Implementation Plan: Configurazione guidata (wizard) — `sertor configure`

**Branch**: `051-configurazione-wizard` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/051-configurazione-wizard/spec.md` (FEAT-003 epica
`sertor-cli`); requisiti `requirements/sertor-cli/configurazione/requirements.md` (Q1–Q4 chiuse).

## Summary

Nuovo sottocomando `sertor configure [rag]` nell'installer `sertor` che porta `.sertor/.env` da
«segreti vuoti» a «pronto» con un percorso guidato, **ibrido CI-safe** (Q1 a): prompt con TTY,
flag-driven senza TTY, **mai** bloccante. Comando **separato e ri-eseguibile** (Q2 a). I campi richiesti
derivano dalla **fonte unica** `Settings.validate_backend()` (NFR-04) per il **solo** insieme di
provider/store che il core onora (Q4 a: embedding Azure/Ollama; store Chroma/Azure Search). La scrittura
riusa il **merge additivo non distruttivo** del kit (`env_merge`, NFR-02), con overwrite solo su
conferma/`--overwrite` (FR-011). Validazione **statica di default**; **probe live opt-in** `--check` (Q3
a) eseguito **via il vehicle `sertor-rag`** in subprocess (Principio XI), mai importando la libreria di
embedding. Segreti **solo** in `.sertor/.env` (git-ignored), mascherati ovunque in output/log (FR-013).
Additivo: i comandi `install`/`upgrade`/`uninstall` restano invariati.

**Approccio tecnico (dal research):** `sertor` dipende già da `sertor-core` e `sertor-install-kit` →
la validazione statica importa `Settings`/`validate_backend` (lettura pura, non operazione tracciata,
non viola il Principio XI); la scrittura compone `merge_env` + `_replace_key_line` esistenti (DRY); il
mascheramento è una funzione pura unica (`mask_secret`); il report è un'entità pura con `render_human`/
`render_json` nello stile di `InstallReport`. Il probe live richiede un piccolo tassello di **core**
(`sertor-rag check`) da **promuovere a backlog** prima che `--check` conti come done (vedi sotto).

## Technical Context

**Language/Version**: Python ≥ 3.11 (workspace `uv`).

**Primary Dependencies**: stdlib (`argparse`, `getpass`, `sys`, `pathlib`); `sertor-core`
(`Settings`/`validate_backend`, lettura statica) + vehicle `sertor-rag` (probe via subprocess);
`sertor-install-kit` (`env_merge.merge_env`/`_replace_key_line`, `command_runner.SubprocessRunner`,
`report` pattern). **Nessuna nuova dipendenza** (Principio III).

**Storage**: file `.sertor/.env` dell'ospite (git-ignored). Nessun DB/indice toccato.

**Testing**: `pytest` nella suite di `packages/sertor` (unit + qualche integration), con `Settings`
risolto da env controllato e `CommandRunner` iniettabile per il probe; F.I.R.S.T., no rete, no cloud.

**Target Platform**: CLI cross-platform (Windows/Linux/macOS); host-agnostico (Principio X).

**Project Type**: estensione di un CLI esistente (single package `packages/sertor`).

**Performance Goals**: N/A (comando interattivo a bassa frequenza; senza `--check` zero rete).

**Constraints**: install≠run; non-distruttività/idempotenza; segreti solo in `.sertor/.env`, mai
versionati né a video/log; CI-safe (mai bloccante senza TTY); solo provider/store del core.

**Scale/Scope**: ~5 campi di configurazione (catalogo statico); 4 combinazioni profilo (2 backend × 2
store); 5 user story (3 P1, 2 P2 — di cui il probe è Should).

## Constitution Check

*GATE: superato PRIMA della Phase 0 e RI-VALUTATO dopo la Phase 1.* Gate da costituzione v1.2.0.

| # | Principio | Pre (Phase 0) | Post (Phase 1) | Note |
|---|-----------|:--:|:--:|------|
| I | Dipendenze verso l'interno (NN) | PASS | PASS | il comando vive in `sertor` (consumatore), non nel core; nessun SDK importato; usa `Settings`/`validate_backend` (astrazioni del core). Testabile con env controllato + runner mock. |
| II | Boundary & local-first | PASS | PASS | nessun tipo di terze parti nel comando; profilo locale completabile senza cloud (FR-006); store solo dove richiesto (FR-007). |
| III | YAGNI & unità piccole | PASS | PASS | zero nuove dipendenze; riuso di `merge_env`/`_replace_key_line`/report; catalogo campi minimo; funzioni piccole (resolve/prompt/write/report). |
| IV | Errori espliciti (NN) | PASS | PASS | campi mancanti senza TTY → `ConfigError` che li nomina, niente stato parziale (FR-005); probe fallito → errore azionabile (FR-023); niente `None` silenzioso. |
| V | Testabilità & misure | PASS | PASS | test F.I.R.S.T.; **test di copertura catalogo↔`validate_backend`** (no drift); test anti-leak segreti; runner iniettabile per il probe. (Misure hit@k/MRR: N/A — feature di config, non di retrieval.) |
| VI | Idempotenza & non-distruttività | PASS | PASS | merge additivo; overwrite solo su conferma/`--overwrite`; re-run → `.env` identico (FR-014); install≠run (FR-030). |
| VII | Leggibilità | PASS | PASS | naming di dominio (configure/resolve/validate/probe/mask); guard clause; funzioni piccole. |
| VIII | Configurabilità centralizzata | PASS | PASS | i campi e i loro default vengono da `Settings`/template, non hardcodati nel comando; il catalogo è solo presentazione. |
| IX | Osservabilità | PASS | PASS | evento `configure` (backend/store, conteggi, esito), **senza segreti**; probe osservato dal vehicle. |
| X | Host-agnostico (NN) | PASS | PASS | nessuna assunzione sull'ospite oltre `--target`; opera su qualunque repo. |
| XI | Consumo via vehicles | PASS | PASS | validazione statica = lettura `Settings` (non operazione runtime tracciata); **probe live via vehicle `sertor-rag` in subprocess**, MAI `build_embedder()` importato. Decisione esplicita nel research (Punto 3). |

**Esito: PASS 11/11 pre-design e post-design. Nessuna deroga.** (Sezione *Complexity Tracking* vuota.)

> **Nota Principio XI (chiarimento, non deroga):** importare `Settings`/`validate_backend` per la
> validazione *statica* non è «consumo di una capacità a runtime» (non è `index()`/`search()`, non c'è
> osservabilità da bypassare): è lettura di config pura, già fatta da `sertor-rag` stesso
> (`cli/__main__.py:183-189`). Il consumo runtime (chiamata di embedding del probe) passa rigorosamente
> per il vehicle. Confine onorato.

## Project Structure

### Documentation (this feature)

```text
specs/051-configurazione-wizard/
├── plan.md              # questo file
├── research.md          # Phase 0 — risoluzione dei 6 punti di "come"
├── data-model.md        # Phase 1 — entità (ConfigProfile/ConfigField/…/ConfigureReport)
├── quickstart.md        # Phase 1 — guida d'uso
├── contracts/
│   └── cli-commands.md  # Phase 1 — contratto del comando + report --json + exit code
├── checklists/          # (presente, dalla spec)
└── tasks.md             # Phase 2 — generato da /speckit-tasks (NON da /speckit-plan)
```

### Source Code (repository root)

```text
packages/sertor/src/sertor_installer/
├── __main__.py           # ESTESO: sub-parser `configure` + handler _cmd_configure + dispatch
├── configure.py          # NUOVO: orchestrazione (resolve campi → write → validate → [probe] → report)
├── config_fields.py      # NUOVO: catalogo ConfigField (presentazione) + mask_secret + copertura
├── configure_report.py   # NUOVO: ConfigureReport (render_human/render_json/exit_code)  [o in report.py]
└── env_merge.py          # (kit) riuso merge_env + _replace_key_line — NESSUNA modifica al percorso install

packages/sertor/tests/
├── test_cli_configure.py     # NUOVO: modalità interattiva/flag-driven, exit code, usage
├── test_configure_write.py   # NUOVO: scaffold/merge/overwrite/idempotenza/no-secret-in-vcs
├── test_config_fields.py     # NUOVO: copertura catalogo↔validate_backend, mask_secret
└── test_configure_check.py   # NUOVO: probe via runner mock (ok/fail/non-disponibile), zero rete senza --check
```

**Structure Decision**: estensione del pacchetto `packages/sertor` (l'installer). Il comando è un
**consumatore sottile**: parsing argparse → `configure.py` (orchestrazione) → riuso di
`Settings`/`validate_backend` (core, lettura) e `merge_env`/`_replace_key_line`/`SubprocessRunner` (kit).
Nessuna nuova porta del core; nessuna modifica al runtime del core (porte/adapter/composition invariati).

## Phase 0 — Research (completata)

`research.md` risolve i 6 punti di *come*:
1. **TTY/CI-safe** — risoluzione per campo (flag→env/esistente→prompt-se-TTY); `isatty()` su stdin+stdout;
   `--non-interactive`; mancante senza TTY → errore che li nomina, exit 1, niente parziale.
2. **Prompt & segreti** — un prompt per campo da `ConfigField`; `getpass` per i segreti; `mask_secret`
   come unico punto di mascheramento.
3. **Probe live** — opt-in `--check` via vehicle `sertor-rag` (subprocess, Principio XI); embed di una
   stringa; degrado onesto se il sottocomando-probe non esiste; **dipendenza di core promossa a backlog**.
4. **Nomi/flag/exit** — `sertor configure [rag] [--target] [--backend] [--store] [--set] [--overwrite]
   [--non-interactive] [--check] [--json]`; exit 0/1/2 come l'installer.
5. **Scrittura** — riuso `merge_env` (additivo) + `_replace_key_line` (overwrite controllato); scaffold
   dal template se `.env` assente; idempotenza by construction.
6. **Report** — `ConfigureReport` puro, umano + `--json`, segreti solo mascherati; test anti-leak.

## Phase 1 — Design (completata)

- **data-model.md**: `ConfigProfile`, `ConfigField` (+invariante di copertura), `FieldResolution`,
  `ValidationOutcome`, `LiveCheckOutcome`, `ConfigureReport` (+ `mask_secret`).
- **contracts/cli-commands.md**: sintassi, modalità, scrittura, validazione, probe, report `--json`,
  exit code, osservabilità, invarianti.
- **quickstart.md**: 5 scenari (interattivo Azure, CI non-interattivo, locale, riconfigura,
  `--check`) + confini + exit code.
- **CLAUDE.md**: aggiornato il riferimento al piano corrente tra i marker SpecKit.

## Capacità da promuovere (regola «Out of Scope si promuovono»)

| Capacità rinviata | Casa durevole | Priorità | Azione |
|-------------------|---------------|:--:|--------|
| **Probe di connettività del vehicle** (`sertor-rag check` / embed di prova osservato) — prerequisito di `--check` | **Nuova FEAT nel backlog `requirements/sertor-core/`** (gemella del self-test MCP) | Should | da creare **prima** che US5/`--check` conti come done |
| Wizard manopole opzionali (cache/obs/engine/graph) | spec §Assumptions + epica `sertor-cli` | Could | già tracciato |
| Estensione provider/store | epica `backend-store-scala` | Won't (qui) | già tracciato |

## Prontezza per /speckit-tasks

Tutti gli artefatti Phase 0/1 prodotti; Constitution Check PASS 11/11 (pre/post) senza deroghe; nessun
`NEEDS CLARIFICATION` residuo sulle scelte critiche (Q1–Q4 chiuse a monte; i 6 punti di *come* risolti).
**Un solo follow-up tracciato (non bloccante per il P1):** creare la FEAT di core per il probe del
vehicle prima di completare US5/`--check` (il P1 — US1/2/3 — è interamente realizzabile con la sola
validazione statica). Pronto per `/speckit-tasks`.

## Complexity Tracking

*(Vuoto — nessuna violazione del Constitution Check da giustificare.)*
