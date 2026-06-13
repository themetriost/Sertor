# Implementation Plan: Igiene e collocazione degli artefatti sull'ospite

**Branch**: `016-igiene-radice-host` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/016-igiene-radice-host/spec.md`

## Summary

Rendere la **radice del repo ospite pulita e prevedibile** dopo l'install: (1) `wiki.config.toml`
vive in `wiki/` (non più in radice) e ogni invocazione degli strumenti del wiki la localizza — via
convenzione esplicita `--config wiki/wiki.config.toml --root .` **e** via auto-discovery del CLI;
(2) `.sertor/` confermata e testata come unica sede del runtime RAG; (3) nuovo meccanismo
`--mcp-scope project|local` su `install rag` (project = `.mcp.json` in radice; local = registrazione
nel client via `claude` CLI, nessun file nel repo, fail-fast se `claude` manca); (4) documentazione
dei residenti inevitabili a root. Il fix per **Sertor stesso** (spostamento + riallineamento asset
`.claude/` e test di sync) è **one-shot**, contestuale; **nessuna** migrazione per ospiti esterni
(decisione D4). Approccio: estensione sottile dell'installer (`packages/sertor/`) e una piccola
auto-discovery host-agnostica nel CLI `sertor-wiki-tools` (`src/sertor_core/wiki_tools/__main__.py`).

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: stdlib (argparse, json, tomllib, pathlib, shutil/subprocess); nessun nuovo
pacchetto. Il client `claude` è un tool esterno opzionale dietro `CommandRunner` (solo scope local).

**Storage**: file system dell'ospite (`wiki/`, `.sertor/`, `.mcp.json`, `.gitignore`, `~/.claude.json`
via client per lo scope local).

**Testing**: pytest; `FakeCommandRunner` per `claude`/`uv` (nessuna rete, nessun tool reale); guardie
di sync degli asset (`test_host_agnostic`).

**Target Platform**: cross-platform (Windows/macOS/Linux); il hook è PowerShell (`.ps1`).

**Project Type**: CLI/installer + libreria core (pacchetti `sertor` e `sertor-core`).

**Performance Goals**: N/A (operazioni di scaffolding locali, sub-secondo).

**Constraints**: install ≠ run; non-distruttività; idempotenza; host-agnostico (Principio X);
`.mcp.json` project-scope vincolato alla radice (client).

**Scale/Scope**: modifiche a ~6 moduli installer + 1 modulo CLI core + asset (`assets/claude/**`,
`claude-md-block.md`, hook) + fix one-shot del repo Sertor (`.claude/**`, `wiki.config.toml`,
`CLAUDE.md`) + `docs/install.md`.

## Constitution Check

*GATE iniziale (pre-Phase 0).* Costituzione v1.1.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** l'installer resta un layer sottile sopra
  `sertor_core`; `claude` è dietro il `CommandRunner` (porta dell'installer, non del core), come `uv`.
  Nessun SDK nel core; l'auto-discovery usa `load_profile` (astrazione esistente).
- [x] **II — Boundary & local-first:** il client `claude` è un dettaglio dietro `CommandRunner`; scope
  local è opzionale, project (file locale) resta il default → nessuna dipendenza da servizi.
- [x] **III — YAGNI & unità piccole:** l'auto-discovery e `MCP_REGISTER` rispondono a bisogni presenti
  (SC-2/R-1 ed REQ-304); nessuna astrazione speculativa. Funzioni piccole, riuso dei pattern 015.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** scope local non realizzabile → `McpRegistrationError`
  esplicito + comando manuale, **nessun** `.mcp.json` silenzioso; config non trovata → `ConfigError`;
  `--mcp-scope` invalido → `ConfigError`.
- [x] **V — Testabilità & misure:** tutto testabile senza rete (`FakeCommandRunner`, fixtures host);
  auto-discovery testata su config-in-root vs config-in-wiki; guardia di sync degli asset. (Le misure
  di retrieval non si applicano: feature di collocazione, non di qualità del retrieval.)
- [x] **VI — Idempotenza & non-distruttività:** re-run → config `skipped`, mcp `skipped` (project) o
  skip-if-present (local), structure idempotente; install ≠ run preservato; lo spostamento per
  Sertor è one-shot e per gli ospiti esterni non si tocca nulla.
- [x] **VII — Leggibilità:** naming di dominio (`mcp_scope`, `MCP_REGISTER`, `register`); commenti
  d'intenzione.
- [x] **VIII — Configurabilità centralizzata:** la specificità dell'ospite resta in
  `wiki.config.toml`; la **collocazione** è una convenzione generica (ordine di ricerca, `--root .`),
  non un default hardcoded nel corpo di una capacità.
- [x] **IX — Osservabilità:** `load_profile` già logga; la registrazione MCP local emette un evento
  (operazione, scope, esito); nessun segreto nei log.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** la convenzione di collocazione (`wiki/`, `.sertor/`,
  ordine di auto-discovery) si applica **uniformemente a qualunque ospite**, senza assunzioni di
  dominio; il fix one-shot di Sertor è dogfood e non introduce path Sertor-specifici nel corpo.

**Esito gate iniziale: PASS (10/10), nessuna deroga.**

## Project Structure

### Documentation (this feature)

```text
specs/016-igiene-radice-host/
├── plan.md              # questo file
├── research.md          # D1..D5 risolte
├── data-model.md        # delta enum/opzioni/errore + regola di collocazione
├── quickstart.md        # verifica SC-001..006
├── contracts/
│   └── cli-commands.md  # --mcp-scope + auto-discovery --config
├── checklists/
│   └── requirements.md  # checklist qualità spec (verde)
└── tasks.md             # generato da /speckit-tasks (non da questo comando)
```

### Source Code (repository root)

```text
packages/sertor/src/sertor_installer/
├── artifacts.py          # + ArtifactKind.MCP_REGISTER, WriteStrategy.REGISTER_CLI
├── rag_profile.py        # + RagInstallOptions.mcp_scope (validato)
├── install_rag.py        # build_rag_plan(mcp_scope); _apply_mcp_register; McpRegistrationError
├── install_wiki.py       # _CONFIG_TARGET → wiki/wiki.config.toml; mkdir; root_override in structure
├── __main__.py           # arg --mcp-scope su `install rag`
└── assets/
    ├── wiki.config.toml.tmpl              # (root="wiki" invariato; commenti)
    ├── claude-md-block.md                 # prosa/esempi alla nuova sede
    └── claude/
        ├── hooks/wiki-pending-check.ps1   # $config → wiki/wiki.config.toml
        ├── commands/wiki.md               # esempi invocazione
        ├── agents/wiki-curator.md         # prosa "config in wiki/"
        └── skills/wiki-author/**          # SKILL/playbook/ops/* esempi invocazione

src/sertor_core/wiki_tools/
└── __main__.py           # auto-discovery del --config (root → wiki/ → ConfigError)

packages/sertor/tests/
├── test_install_rag.py   # scope project/local, fail-fast, idempotenza
├── test_mcp_register.py  # (nuovo) registrazione via FakeCommandRunner
├── test_install_wiki.py  # config in wiki/, structure con root_override
└── test_host_agnostic.py # guardia sync asset ↔ .claude/

src/.../tests (wiki_tools)
└── test_cli auto-discovery (config in root vs wiki/ vs assente)

# Fix one-shot del repo Sertor (dogfood, contestuale):
wiki/wiki.config.toml      # git mv da ./wiki.config.toml
.claude/**                 # ri-sync dagli asset
CLAUDE.md                  # esempi append-log + blocco rituale
docs/install.md            # sezione "residenti a root" (mossa #4)
```

**Structure Decision**: nessun nuovo pacchetto/modulo strutturale. Si estendono i moduli installer
esistenti (pattern 015) e si aggiunge una funzione di auto-discovery nel `__main__` del CLI core. Il
fix di Sertor è una modifica di repo contestuale, non un meccanismo riusabile.

## Constitution Check (post-design re-check)

Dopo il design (research + data-model + contracts): nessuna nuova dipendenza pesante, nessun SDK nel
core, errori espliciti su tutti i percorsi di fallimento, idempotenza preservata, convenzione di
collocazione generica e host-agnostica. **PASS (10/10), Complexity Tracking vuoto.**

## Complexity Tracking

> Nessuna violazione costituzionale: tabella non necessaria.
