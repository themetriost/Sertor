# Implementation Plan: `sertor install rag` — installer della capacità RAG

**Branch**: lavorazione su `master` (bugfix/installer, autorizzato dall'utente; il branch
`015-sertor-install-rag` resta vestigiale) | **Date**: 2026-06-12 | **Spec**:
[spec.md](./spec.md)

**Input**: Feature specification da `specs/015-sertor-install-rag/spec.md` (26 FR) + requirements
`requirements/sertor-cli/install-rag/requirements.md`.

## Summary

Implementare il sottocomando `sertor install rag` (oggi stub) per portare la capacità RAG su un repo
ospite con un solo comando, **scope B**: scaffold di config (`.env`/`.mcp.json`/`.gitignore`) +
bootstrap delle dipendenze Python via `uv` in un **runtime isolato `<target>/.sertor/`** (i sorgenti
host non vengono "pythonizzati"). Più il **fix di distribuzione** del `pyproject` del pacchetto
installer che sblocca l'esecuzione standalone via `uvx`. Approccio: **riuso del backbone**
dell'installer sorella `install wiki` (`Artifact`/`Outcome`/`InstallReport`, `build_plan→execute_plan`
fail-fast no-rollback), esteso con 4 nuovi `ArtifactKind` e un **runner di comandi esterni
iniettabile** che isola `uv` dietro un confine mockabile (testabile senza rete). Le decisioni di
scope sono tutte chiuse (DA-1..DA-4); design dettagliato in research.md/data-model.md/contracts/.

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: nessuna nuova dipendenza runtime per l'installer (orchestrazione `uv` via
`subprocess`; `importlib.resources` per gli asset). Il pacchetto `sertor` resta thin su `sertor-core`.

**Storage**: filesystem dell'ospite (`.sertor/`, `.env`, `.mcp.json`, `.gitignore`). Nessun DB.

**Testing**: pytest; `FakeCommandRunner` per `uv` (no rete), tmp_path per i target; stile dei test
esistenti in `packages/sertor/tests/` (`test_install_wiki.py`, `test_settings_merge.py`,
`test_host_agnostic.py`, `test_cli.py`).

**Target Platform**: cross-platform (Windows/macOS/Linux); l'ospite può essere Python o non-Python.

**Project Type**: CLI installer (pacchetto `sertor` in `packages/sertor/`, uv workspace member).

**Performance Goals**: N/A (operazione one-shot; il costo è `uv add`, esterno).

**Constraints**: install ≠ run (nessuna indicizzazione); idempotenza/non-distruttività; segreti mai
persistiti con valore; host-agnostico; layer sottile; testabile senza rete né `uv` reale.

**Scale/Scope**: un sottocomando + 4 tipi di artefatto + 3 asset template + fix `pyproject` (1 riga).

## Constitution Check

*GATE iniziale (pre-Phase 0). Re-check post-design in fondo.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** l'installer **orchestra**, non duplica
  logica del core; il `CommandRunner` (porta dell'installer, non del core) isola `subprocess`; nessun
  SDK provider importato. Il core non viene toccato (l'esclusione `.sertor` è config, non codice).
- [x] **II — Boundary & local-first:** `uv` (unico tool esterno) dietro `CommandRunner`; backend
  local↔azure guidato da `--backend` → template `.env`. Il vector store non è richiesto qui (install).
- [x] **III — YAGNI & unità piccole:** riuso massimo del backbone wiki; nuovi `kind` additivi;
  funzioni pure (`compose_extras`, generatori di template); nessuna astrazione speculativa.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** `uv` assente / `uv add` fallito / config
  malformata → eccezioni di dominio + `ERROR` nel report con `failed_step`; niente `None` silenzioso
  né stato corrotto (fail-fast no-rollback; il re-run completa i buchi).
- [x] **V — Testabilità & misure:** `FakeCommandRunner` rende US1/US2 testabili senza rete; piano e
  merge testabili in tmp_path. (Le "misure di retrieval" non si applicano: feature di setup.)
- [x] **VI — Idempotenza & non-distruttività:** merge additivi (`.env`/`.mcp.json`/`.gitignore`),
  `uv add` idempotente, `uv init` saltato se pyproject presente; **install ≠ run** esplicito.
- [x] **VII — Leggibilità:** naming di dominio (`build_rag_plan`, `RagHostProfile`, `compose_extras`,
  `BOOTSTRAP_DEPS`); commenti solo sull'intenzione, come nei moduli esistenti.
- [x] **VIII — Configurabilità centralizzata:** le variabili `.env` derivano da `Settings` del core
  (fonte di verità); i default dei template stanno negli **asset** (package-data), non hardcoded nel
  codice (pattern `config_gen.py`).
- [x] **IX — Osservabilità:** il report è l'unica superficie d'osservabilità; ogni comando `uv`
  eseguito è riflesso nel `detail` dell'outcome; nessun segreto loggato.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** nessun percorso/dominio Sertor negli artefatti
  generati; ciò che varia (backend, corpus, source_dirs, url di distribuzione) è parametrico; gira su
  ospite Python o non-Python senza modifiche al corpo. La `git+url` di distribuzione è una costante
  di *progetto Sertor* (il prodotto distribuito), non un'assunzione sull'*ospite*.

**Esito GATE iniziale: PASS** (con una cautela tracciata sotto, non una violazione).

## Project Structure

### Documentation (this feature)
```text
specs/015-sertor-install-rag/
├── plan.md            # questo file
├── research.md        # R1..R6 (fix uv, topologia .sertor, runner mockabile, nuovi artifact, extra, sicurezza)
├── data-model.md      # entità (RagInstallOptions, RagHostProfile, CommandRunner, nuovi kind)
├── contracts/
│   └── cli-install-rag.md   # contratto del sottocomando + artefatti + exit code
├── quickstart.md      # flusso utente (uvx un comando)
└── tasks.md           # (/speckit-tasks — non creato qui)
```

### Source Code (repository root)
```text
packages/sertor/
├── pyproject.toml                         # + [tool.uv.sources] sertor-core = { git = … }  (R1)
└── src/sertor_installer/
    ├── __main__.py                        # + sub-parser flags rag; dispatch rag → handler (no stub)
    ├── artifacts.py                       # + ArtifactKind/WriteStrategy (DEPENDENCIES/ENV_MERGE/MCP_MERGE/GITIGNORE_APPEND)
    ├── install_rag.py        (NUOVO)      # build_rag_plan + execute_rag_plan (analogo install_wiki.py)
    ├── rag_profile.py        (NUOVO)      # RagInstallOptions, RagHostProfile, compose_extras
    ├── command_runner.py     (NUOVO)      # CommandRunner Protocol + SubprocessRunner (R3)
    ├── env_merge.py          (NUOVO)      # merge additivo .env (chiavi mancanti, segreti vuoti)
    ├── mcp_merge.py          (NUOVO)      # merge additivo .mcp.json (pattern settings_merge.py)
    ├── gitignore_append.py   (NUOVO)      # append dedup di righe
    ├── report.py / resources.py / config_gen.py   # INVARIATI (riuso)
    └── assets/rag/           (NUOVO)
        ├── env.azure.tmpl
        ├── env.local.tmpl
        └── mcp.server.json.tmpl
packages/sertor/tests/
    ├── test_install_rag.py   (NUOVO)      # piano+esecuzione con FakeCommandRunner, idempotenza
    ├── test_env_merge.py / test_mcp_merge.py / test_gitignore_append.py (NUOVI)
    ├── test_rag_profile.py   (NUOVO)      # compose_extras, default corpus, validazioni
    └── test_cli.py           (ESTESO)     # dispatch rag, exit code, --json
```

**Structure Decision**: estensione in-place del pacchetto installer `packages/sertor/`, rispecchiando
il modulo-per-responsabilità di `install wiki`. Nessun nuovo pacchetto, nessuna modifica al core.

## Complexity Tracking

> Nessuna **violazione** costituzionale. Una sola **cautela** dichiarata, coerente con la sorella
> `install wiki` e la 013:

| Punto | Perché accettato | Alternativa più semplice scartata |
|---|---|---|
| L'installer **esegue un processo esterno** (`uv`) — un side-effect non puro nel layer di setup | È l'essenza dello scope B ("un comando, niente internals"); isolato dietro `CommandRunner` (mockabile), riflesso nel report (Principio IX), e ammesso da install ≠ run (add ≠ index). Non viola il Principio I: orchestrazione, non logica di dominio del core. | "Solo scaffold + istruzioni" (opzione C, scartata dall'utente): non realizza la promessa. |
| Il template `.env` **ri-elenca i default-excludes** del core + `.sertor` | Il core *sostituisce* i default quando `SERTOR_EXCLUDE_PATTERNS` è presente; ri-elencarli evita di perderli senza toccare il core | Modificare i default del core per additività: tocca il core per un dettaglio dell'installer (peggio per Principio I/III) |

## Rischi di validazione (→ task espliciti, non bloccanti il design)
- **R1 (uvx end-to-end):** verifica `uvx --from "git+url#subdirectory=packages/sertor" sertor --help`
  → richiede il fix **pushato** sul remoto; task di validazione post-merge su ambiente pulito.
  Locale e subito: `uv lock`/`uv run pytest` dalla root restano verdi (dev non rotto).
- **R2 (esclusione `.sertor`):** verifica su un re-index reale che `.sertor/` sia escluso dal corpus.

## Constitution Check — RE-CHECK post-design (Phase 1)

Rivalutati i gate dopo research/data-model/contratti: **PASS 10/10**, invariato rispetto al GATE
iniziale. Il design non introduce import SDK nel core (I), tiene `uv` dietro una porta mockabile
(V), mantiene merge additivi e install ≠ run (VI), e nessun artefatto generato incorpora assunzioni
dell'ospite (X). La cautela "processo esterno" resta tracciata sopra, non promossa a violazione
(orchestrazione trasparente e isolata).

## Prossimo passo
`/speckit-tasks` — generare `tasks.md` ordinato per dipendenze. MVP = US1 (un-comando-RAG-pronto):
nuovi `kind` + `install_rag.py` + `command_runner.py` + asset + dispatch. US3 (fix `pyproject` +
validazione uvx) parallelizzabile e a basso accoppiamento.
