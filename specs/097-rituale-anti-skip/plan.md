# Implementation Plan: Rituale wiki resistente allo skip silenzioso (scoperta deterministica + dichiarazione forzata)

**Branch**: `097-rituale-anti-skip` | **Date**: 2026-07-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/097-rituale-anti-skip/spec.md` (E10-FEAT-026, MVP parte 1+3).

## Summary

Aggiungere un **nuovo sottocomando deterministico** `ritual-check` a `sertor-wiki-tools` (in
`src/sertor_core/wiki_tools/`) che, dato lo scope dello step (**git diff vs base**, con fallback
graceful), **elenca**: (a) **candidati a distillazione** (gruppi di pagine cambiate insieme che
condividono nuovi backlink incrociati e nessuna nuova pagina `concepts/`/`tech/`) e (b) **candidati a
drift** (pagine con segnali strutturali di possibile scollegamento dalla realtà), + **emette lo scaffold
di dichiarazione** `Rituale: record · distill · lint` coi candidati pre-popolati. Output JSON + summary
umano (pattern degli altri sottocomandi). **Il tool trova (deterministico, zero-LLM); l'agente giudica**
(D↔N). Parte 3: il contratto host-facing (blocco `SERTOR:WIKI-RITUAL` + `wiki-playbook`) richiede la
**dichiarazione forzata** a fine step; entrambi distribuiti via installer + guardia sync bundle.

## Technical Context

**Language/Version**: Python ≥ 3.11 (stdlib-only per il tool wiki; `subprocess` per git). Coerente con
`sertor_core.wiki_tools` (zero LLM, offline).

**Primary Dependencies**: nessuna nuova. Riusa `wiki_tools`: `profile.WikiProfile` (config da
`wiki.config.toml`: root, `source_dirs`, `taxonomy`, `exclude`, `strings`), `frontmatter` (parse
`title`/`updated`), il **backlink-graph** già costruito in `lint.py` (link/orphans), `contracts`
(dataclass di risultato + `--json`), `log_event` (osservabilità). Git via `subprocess` (stdlib).

**Storage**: N/A — **sola lettura** del wiki + `git diff`; il tool non scrive pagine (emette candidati +
scaffold su stdout).

**Testing**: `pytest` unit F.I.R.S.T. con **wiki-fixture + repo git temporaneo** (offline, no LLM):
euristica distill (positivo/negativo), segnali drift, fail-loud su scope indeterminabile, contratto JSON,
parità output; + guardia sync bundle (`test_assets_sync`) sugli asset host-facing.

**Target Platform**: qualunque ospite con git (Claude Code + Copilot); config da `wiki.config.toml`
(Principio X). **Fallback host-agnostico:** se non è un repo git (o manca la base), il tool **fallisce
loud** con messaggio azionabile oppure accetta pagine/range **espliciti** — mai un insieme vuoto
silenzioso (REQ-006).

**Project Type**: estensione del **vehicle** `sertor-wiki-tools` (libreria `sertor-core`) — installabile
per costruzione; + asset host-facing (blocco rituale/playbook) cablati nell'installer.

**Performance Goals**: N/A (una manciata di pagine per step). **Constraints**: zero-LLM/offline (D↔N),
deterministico/idempotente (sola lettura), host-agnostico. **Scale/Scope**: 1 nuovo sottocomando + 1
contract + registrazione CLI + asset host-facing + sync.

## Constitution Check

*GATE: prima della Phase 0 e dopo il design.* Costituzione v1.4.0.

- [x] **I — Dipendenze verso l'interno:** **PASS** — `ritual_check` vive in `sertor_core.wiki_tools`,
  **nessun SDK di provider**; usa solo stdlib (`subprocess` per git) + moduli `wiki_tools`. Il core resta
  importabile/testabile senza cloud/CLI.
- [x] **II — Boundary & local-first:** **N/A** — nessun provider esterno; git è locale.
- [x] **III — YAGNI & unità piccole:** **PASS** — un sottocomando + un'euristica piccola; MVP (parte 1+3),
  parti 2/4 fuori scope; niente astrazioni speculative.
- [x] **IV — Errori espliciti:** **PASS** — scope indeterminabile → `ConfigError` esplicito (REQ-006),
  come gli altri moduli (`_target_log`/`upsert_index`); niente `None` silenzioso.
- [x] **V — Testabilità & misure:** **PASS** — unit F.I.R.S.T. con fixture wiki+git; deterministico,
  offline, no LLM.
- [x] **VI — Idempotenza & non-distruttività:** **PASS** — **sola lettura** del wiki (emette candidati +
  scaffold); nessuna scrittura di pagine, nessun effetto collaterale.
- [x] **VII — Leggibilità:** **PASS** — naming di dominio (`ritual`, `distill_candidate`, `drift_candidate`).
- [x] **VIII — Configurabilità centralizzata:** **PASS** — soglie/glob (es. finestra candidati, eventuale
  segnale capability↔exec) da `wiki.config.toml` via `WikiProfile`, nessun default hardcoded nei componenti.
- [x] **IX — Osservabilità:** **PASS** — `log_event("ritual_check", …)` con conteggi/scope, come gli altri.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** **PASS** — config da `wiki.config.toml`; **nessun** path/
  struttura d'ospite hardcodato (il segnale capability↔exec, se incluso, è **config-driven**, non fisso);
  git-diff con **fallback graceful** (fail-loud o pagine esplicite) su host senza git. Gira su un ospite
  diverso senza modifiche al corpo.
- [x] **XI — Consumo via vehicles:** **PASS** — è un sottocomando del **vehicle** `sertor-wiki-tools`;
  l'agente lo consuma via CLI, non importa `sertor_core`.
- [x] **XII — Fail Loud, Fix the Cause:** **PASS (centrale)** — è la ragione della feature: lo skip
  silenzioso diventa segnale; scope indeterminabile → errore esplicito (mai vuoto-silenzioso).
- [x] **Allineamento alla missione:** **PASS (con motivo)** — il rituale mantiene il **wiki** (auto-conoscenza
  del progetto, parte del corpus reso all'agente) **senza drift silenzioso** proprio nell'EXEC che l'agente
  legge a ogni sessione: serve la **freschezza/realtà del contesto reso all'agente** (essenza della
  missione). È governance/meta, ma non deriva: ancora la qualità del contesto, non un concern periferico.

**Esito gate: PASS 12/12 + missione.** Nessuna violazione → nessun *Complexity Tracking*.

## Project Structure

### Documentation (this feature)

```text
specs/097-rituale-anti-skip/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/ritual-check.md   # schema del contratto JSON + CLI
├── spec.md · checklists/requirements.md
└── tasks.md                    # /speckit-tasks (non qui)
```

### Source Code (repository root)

```text
src/sertor_core/wiki_tools/
├── ritual_check.py       # NUOVO — euristica distill + segnali drift + scaffold (sola lettura)
├── contracts.py          # + RitualCheckResult (dataclass, `wiki.ritual_check/1`)
├── __main__.py           # + registrazione sottocomando `ritual-check` (+ opzioni --base/--pages/--json)
├── lint.py               # RIUSO del backlink-graph (link fra pagine); estrarre un helper se serve
├── frontmatter.py        # RIUSO parse `updated:`/`title:`
└── profile.py            # RIUSO WikiProfile (config); eventuale `[ritual]` opzionale (soglie/glob)

tests/unit/
└── test_ritual_check.py  # euristica ±, drift, fail-loud, JSON, host-agnostico

# Asset host-facing (parte 3, distribuiti via installer + bundle):
#  - blocco `SERTOR:WIKI-RITUAL` (claude-md-block) + `wiki-playbook.md`: contratto di dichiarazione forzata
#  - bundle in packages/sertor/.../assets/** + guardia `test_assets_sync`
```

**Structure Decision**: nuovo modulo `ritual_check.py` nel package `wiki_tools` (stesso pattern di
`scan`/`lint`: funzione pura che prende `WikiProfile`, ritorna una dataclass di `contracts`, logga via
`log_event`); registrato come sottocomando `ritual-check` in `__main__.py`. Parte 3 = modifica prosa al
blocco rituale host-facing + playbook, bundlata e sincronizzata (guardia sync). `sertor-core` engine di
retrieval **invariato**.

## Complexity Tracking

> Nessuna violazione del Constitution Check → sezione vuota.
