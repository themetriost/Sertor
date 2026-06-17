# Implementation Plan: Ciclo di vita dell'installer (upgrade e uninstall)

**Branch**: `048-lifecycle-installer` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/048-lifecycle-installer/spec.md` +
`requirements/sertor-cli/lifecycle-installer/requirements.md` (FEAT-008, epica `sertor-cli`).

## Summary

Produttivizza i due verbi mancanti del ciclo di vita dell'installer — **`upgrade`** e **`uninstall`** —
oggi descritti solo come procedura manuale in `docs/install.md §10.1/§10.2`. L'installer copre il primo
install (creazione condizionale + merge additivi); mancano l'aggiornamento dei file già presenti, la
rimozione degli obsoleti e la rimozione inversa affidabile. Le 4 decisioni di prodotto sono chiuse:
**Q1 (a)** wiki protetto, flag `--purge-wiki` + `--yes`; **Q2 (a)** obsoleti via diff a posteriori
contro una lista statica di path Sertor-owned, **nessun manifest**; **Q3 (c)** `sertor uninstall`
tutto-in-uno **e** per-capacità; **Q4 (a)** `sertor-flow upgrade`/`uninstall` **in ambito** (simmetria
piena).

Approccio tecnico risolto in Phase 0 (research.md) sulle 4 ambiguità di *come*:
- **D1** — niente `ArtifactKind`/`WriteStrategy` inversi: un **verbo ortogonale** `LifecycleOp`
  {INSTALL/UPGRADE/UNINSTALL} + 2 nuovi `Outcome` {UPDATED/REMOVED} + **funzioni inverse pure nel kit**,
  duali 1:1 delle primitive additive esistenti.
- **D2** — i plan di upgrade/uninstall **riusano lo stesso plan-builder d'install** (UNICA fonte di
  verità): nessun secondo plan-builder; il dispatch `apply(artifact, op)` sceglie la funzione inversa.
- **D3** — la dichiarazione statica dei path Sertor-owned è una **funzione pura
  `sertor_owned_paths(capability, assistant)`** co-localizzata col plan-builder, con un **test di
  copertura** che la tiene allineata (sostituisce il manifest).
- **D4** — conferma `--purge-wiki` **deterministica e CI-safe**: senza TTY e senza `--yes` non si
  cancella (default sicuro, avviso azionabile); `--purge-wiki --dry-run` è usage error.

Le primitive di ciclo di vita vivono **una sola volta nel `sertor-install-kit`** (stdlib-only, FR-053):
`sertor` e `sertor-flow` le consumano, restando simmetrici e impossibilitati a divergere (SC-010).

## Technical Context

**Language/Version**: Python ≥ 3.11 (baseline). Kit stdlib-only (NFR-07: niente nuove dipendenze).

**Primary Dependencies**: nessuna nuova. Si estende il `sertor-install-kit` (artifacts/executor/
report + nuovi moduli di rimozione/diff), e si aggiungono sottocomandi ai vehicles `sertor` e
`sertor-flow`. `uv`/`claude` restano dietro il `CommandRunner` iniettabile (per DEPENDENCIES/MCP).

**Storage**: N/A persistente. **Nessun manifest** (Q2 (a)): lo stato installato è ri-derivato a ogni
run dal codice (plan-builder + `sertor_owned_paths`) + scansione del filesystem `--target`.

**Testing**: pytest nei pacchetti installer. Unit: funzioni inverse del kit su fixture con contenuto
misto (Sertor + utente), idempotenza, dry-run a 0 byte, parità `sertor`/`sertor-flow`. Comandi con core
mockato dove tocca (`build_*` / `CommandRunner`), come `test_cli_search`/`test_cli_install`.

**Target Platform**: cross-platform (Windows/POSIX); opera solo nella `--target` corrente (FR-033).

**Project Type**: monorepo `uv workspace`, 4 pacchetti. La feature tocca `sertor-install-kit` (sede
unica delle primitive), `sertor` (`sertor_installer`), `sertor-flow` (`sertor_flow`). **Nessuna modifica
a `sertor-core`** (porte/adapter/composition invariati — non è una feature di runtime RAG).

**Performance Goals**: uninstall su ospite tipico (< 100 artefatti) < 10 s su FS locale (NFR-04/SC-011);
operazione locale, non di rete.

**Constraints**: install ≠ run (FR-051, mai indicizza) · fail-fast no-rollback (coerente con
`execute_plan`) · non-distruttività (FR-050: solo porzioni Sertor nei file condivisi) · idempotenza
(FR-026/SC-005) · host-agnostico (FR-052) · `sertor-flow` non dipende da `sertor-core`/`sertor`
(FR-045/055) · segreti mai nel report (FR-053) · valori `.sertor/.env` mai sovrascritti in upgrade
(NFR-05).

**Scale/Scope**: 3 capacità (`wiki`/`rag`/`governance`-puntatore) × 3 assistenti; 2 verbi × 2 CLI.
~8 funzioni inverse nel kit + `LifecycleOp` + 2 `Outcome` + esecutore verbo-aware; `sertor_owned_paths`
×3 capacità; 4 sottocomandi CLI; aggiornamento `docs/install.md §10`.

## Constitution Check

*GATE: superato PRIMA di Phase 0 e RI-VERIFICATO dopo Phase 1.* Gate dalla costituzione v1.2.0
(`.specify/memory/constitution.md`).

> **Natura della feature.** Vive nei **pacchetti installer**, non nel core RAG: non introduce entità di
> dominio del retrieval, porte, adapter, motori, né tocca `composition.py`. I principi *load-bearing*
> sono **III** (YAGNI: una sola tassonomia, niente kind inversi, niente manifest), **IV** (errori
> espliciti: usage error su flag incompatibili, fail-fast MCP, avvisi su obsoleti fuori perimetro),
> **VI** (idempotenza/install≠run/non-distruttività — il cuore della feature), **IX** (osservabilità:
> `log_event` upgrade/uninstall), **X** (host-agnostico) e **XI** (no import di `sertor_core` nei
> comandi di lifecycle). I principi del runtime RAG (II vector store, V metriche hit@k/MRR) sono
> **N/A** (nessun retrieval introdotto).

### Pre-design (dopo lettura spec+requirements)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS — non si tocca il core; il kit resta
  stdlib-only e indipendente da `sertor-core`. La fase wiki che attraversa `sertor-core` è solo
  l'install (`_apply_structure`, già wrappato al boundary); la **rimozione** del wiki è pura
  `remove_path`, nessun import del core.
- [x] **II — Boundary & local-first:** PASS (N/A runtime RAG) — nessuna dipendenza esterna/vector store
  introdotta; `uv`/`claude` restano dietro `CommandRunner`. Tutto locale.
- [x] **III — YAGNI & unità piccole:** PASS — **un solo** verbo `LifecycleOp` + 2 `Outcome` + funzioni
  inverse duali 1:1; **scartati** i 5 `WriteStrategy`/`ArtifactKind` inversi (raddoppio tassonomia) e
  il **manifest** (Q2 (a)). Una sola fonte di verità (plan-builder d'install).
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS — `--purge-wiki --dry-run` → usage error (exit
  2); client MCP assente → `McpRegistrationError` con fallback manuale; obsoleto fuori perimetro →
  avviso + continua (no crash, no rimozione cieca); JSON malformato → `ConfigError` (file non toccato,
  come i merge). Niente `None` silenzioso.
- [x] **V — Testabilità & misure:** PASS — funzioni inverse pure F.I.R.S.T. su fixture miste; comandi
  con core/runner mockati. Metrica retrieval (hit@k/MRR) **N/A** (feature d'installer, non di qualità
  retrieval).
- [x] **VI — Idempotenza & non-distruttività (cuore):** PASS — uninstall su pulito = tutti `skipped`
  (FR-026); upgrade su allineato = `0 updated` (SC-005); install ≠ run preservato (FR-051); rimozione
  SOLO di porzioni Sertor nei file condivisi byte-per-byte (FR-050/021/022/023); wiki protetto di
  default (FR-027).
- [x] **VII — Leggibilità:** PASS — nomi d'intento di dominio installer (`remove_marker_block`,
  `update_file_if_changed`, `deregister_mcp_client`, `sertor_owned_paths`), guard clause / early
  return, funzioni piccole duali delle additive esistenti.
- [x] **VIII — Configurabilità centralizzata:** PASS (N/A core) — nessuna scelta operativa di runtime
  RAG; ciò che varia per ospite (assistente, target) sta nei flag/`AssistantProfile`, non hardcoded.
- [x] **IX — Osservabilità:** PASS — `log_event(operation="upgrade"|"uninstall", capability, counts)` a
  fine operazione (FR-007/REQ-040), report esteso con `updated`/`removed`, **nessun segreto** nei
  detail (FR-053).
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS — path/marker risolti via `AssistantProfile` +
  costanti, nessuna assunzione sull'ospite; opera solo nella `--target` (FR-033/052); funziona su
  qualsiasi repo (code+doc/solo-doc/solo-code). Il dogfooding non introduce deroghe.
- [x] **XI — Consumo via vehicles:** PASS — i comandi sono nei vehicles CLI (`sertor`/`sertor-flow`),
  non importano `sertor_core` a runtime; il conteggio pagine del wiki (`--purge-wiki`) usa il
  filesystem stdlib, non la libreria. Le primitive inverse vivono nel kit (consumato dai vehicles).

**Esito pre-design: PASS 11/11, nessuna deroga.**

### Post-design (dopo Phase 1 — research/data-model/contracts/quickstart)

Riconfermato dopo aver fissato il design: verbo `LifecycleOp` + 2 `Outcome` (III); funzioni inverse
pure nel kit stdlib-only, duali 1:1 (III/VII); `sertor_owned_paths` + test di copertura al posto del
manifest (III/VI); regole `--purge-wiki` deterministiche (IV/VI); report `install.report/1` esteso
senza secondo schema (IX); primitive una sola volta nel kit consumate da entrambi i CLI (SC-010,
FR-053); `sertor-flow` continua a non dipendere da `sertor-core`/`sertor` (I, FR-045/055). **Nessuna
nuova porta/adapter, nessuna modifica a `composition.py`/servizi del core** → I/II/VIII/V(metriche)
restano N/A-PASS. **Nessuna violazione introdotta dal design.**

**Esito post-design: PASS 11/11, nessuna deroga.** "Complexity Tracking" non compilato (nessuna
violazione da giustificare).

## Project Structure

### Documentation (this feature)

```text
specs/048-lifecycle-installer/
├── spec.md              # input (già presente)
├── plan.md              # questo file
├── research.md          # Phase 0 — 4 ambiguità di design risolte (D1–D4)
├── data-model.md        # Phase 1 — entità estese (LifecycleOp, Outcome, SertorOwnedPaths, report)
├── quickstart.md        # Phase 1 — upgrade/uninstall/purge-wiki/flow
├── contracts/
│   ├── install-report-extended.md   # schema install.report/1 esteso (updated/removed)
│   └── cli-lifecycle.md             # contratti dei comandi upgrade/uninstall + primitive inverse
└── checklists/          # (preesistente)
```

### Source Code / artifacts (repository root)

```text
Sertor/
├── packages/sertor-install-kit/src/sertor_install_kit/
│   ├── artifacts.py          # MOD — + enum LifecycleOp; + Outcome.UPDATED/REMOVED
│   ├── report.py             # MOD — + contatori updated/removed (human + JSON), schema invariato
│   ├── executor.py           # MOD — execute_plan verbo-aware (op=INSTALL default; apply(art, op))
│   ├── claude_md.py          # MOD — + remove_marker_block / update_marker_block (duali)
│   ├── settings_merge.py     # MOD — + remove_settings_entries (inverso, riusa _inner_commands)
│   ├── gitignore_append.py   # MOD — + remove_gitignore_lines (inverso)
│   ├── mcp_merge.py          # MOD — + remove_mcp_server (inverso, file via solo-server)
│   ├── lifecycle.py          # NUOVO — update_file_if_changed, remove_path, deregister_mcp_client,
│   │                         #          execute_lifecycle (orchestratore verbo + fase obsoleti)
│   └── __init__.py           # MOD — riesporta i nuovi simboli (install-kit/1 esteso)
├── packages/sertor/src/sertor_installer/
│   ├── install_rag.py        # MOD — + sertor_owned_paths("rag", assistant); apply esteso a op
│   ├── install_wiki.py       # MOD — + sertor_owned_paths("wiki", assistant); apply esteso a op
│   └── __main__.py           # MOD — + sottocomandi `upgrade`/`uninstall` (capacità 0..N, flags)
├── packages/sertor-flow/src/sertor_flow/
│   ├── install_governance.py # MOD — + sertor_owned_paths("governance", assistant); apply esteso
│   └── __main__.py           # MOD — + sottocomandi `upgrade`/`uninstall`
└── docs/
    └── install.md            # MOD — §10 punta ai comandi automatici (manuale → fallback)
```

**Structure Decision**: feature **a livello di pacchetti installer**, non di `src/sertor_core/**`. Le
primitive inverse e l'orchestratore verbo-aware stanno **una sola volta** nel `sertor-install-kit`
(FR-053/SC-010); i consumer (`sertor`, `sertor-flow`) aggiungono solo `sertor_owned_paths` per capacità,
il dispatch `apply(artifact, op)` esteso ai verbi e i sottocomandi CLI. Nessuna primitiva di rimozione
nei consumer. Nuovo modulo `lifecycle.py` nel kit per le funzioni non-attaccabili a un file additivo
esistente (`update_file_if_changed`, `remove_path`, `deregister_mcp_client`) e per `execute_lifecycle`;
le altre inverse stanno **accanto** alla loro additiva (anti-drift di lettura).

## Implementation Notes (non-binding, per `/speckit-tasks`)

Ordine suggerito, dal fondante al consumer:
1. **Tassonomia kit** — `LifecycleOp` (INSTALL default), `Outcome.UPDATED/REMOVED`, contatori nel
   `InstallReport` (human + JSON), `execute_plan` verbo-aware retrocompatibile. Test: report esteso,
   default INSTALL invariato (non-regressione).
2. **Funzioni inverse del kit** — `remove_marker_block`/`update_marker_block` (claude_md),
   `remove_settings_entries` (settings_merge), `remove_gitignore_lines` (gitignore_append),
   `remove_mcp_server` (mcp_merge), e in `lifecycle.py`: `update_file_if_changed`, `remove_path`,
   `deregister_mcp_client`. Test su fixture miste (Sertor + utente), idempotenza, byte-per-byte.
3. **`execute_lifecycle`** — orchestratore: percorre il plan col verbo, dispatch a `apply(art, op)`,
   poi fase obsoleti (diff `sertor_owned_paths` ∩ disco − plan); `--dry-run` proietta senza scrivere.
4. **`sertor_owned_paths` per capacità** — funzioni pure in `install_rag.py`/`install_wiki.py`/
   `install_governance.py` derivate dalle costanti+`AssistantProfile`; **test di copertura**
   (`plan ⊆ owned`).
5. **CLI `sertor`** — sottocomandi `upgrade`/`uninstall` (capacità 0..N → aggregato; `--assistant`/
   `--dry-run`/`--json`; `--purge-wiki`/`--yes` con regole D4); `governance` = puntatore.
6. **CLI `sertor-flow`** — `upgrade`/`uninstall` simmetrici, runner iniettabile; invariante no-dep.
7. **Osservabilità** — `log_event(operation="upgrade"|"uninstall", ...)` a fine comando.
8. **Documentazione** — `docs/install.md §10`: i comandi automatici come via primaria, lo script
   manuale come fallback/storico.
9. **Non-regressione** — suite dei tre pacchetti + `ruff check .` verdi.

## Out-of-Scope tracking (promozione, NON sepoltura)

Voci rinviate da questa feature, già con casa durevole (nessuna nuova casa da creare):
- **Rollback automatico a versione precedente + gestione versioni** → **FEAT-006** (epica `sertor-cli`,
  distribuzione/PyPI). Citato, non duplicato.
- **Distribuzione dei comandi `upgrade`/`uninstall` sugli ospiti già installati** (bootstrap del
  bootstrap) → dipende dal canale di distribuzione (**FEAT-006**); l'ospite aggiorna il pacchetto.
- **Ergonomia avanzata installer / multi-target** → **FEAT-010** (Could).
- **Upgrade del runtime Python isolato oltre il merge idempotente delle dipendenze** → gestito
  dall'`uv add` idempotente odierno; un upgrade dedicato del venv non è richiesto qui.
- **Uninstall cross-utente/di sistema · GUI/wizard · upgrade su evento/CI** → fuori ambito (§4 spec),
  non capacità future tracciate (nessuna promozione necessaria).

> Nessun rinvio reale vive solo dentro `specs/048-…/`: i rinvii reali mappano su FEAT-006/FEAT-010
> esistenti dell'epica `sertor-cli`. Nessuna riga nuova da aggiungere al backlog o alla roadmap per
> questa feature.
```
