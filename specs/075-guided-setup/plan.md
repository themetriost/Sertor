# Implementation Plan — guided-setup (E12-FEAT-002)

**Branch**: `075-guided-setup` · **Spec**: [`spec.md`](spec.md) · **Data**: 2026-06-23 ·
**Costituzione**: v1.4.0

> **Nota di processo.** `setup-plan.ps1` / `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** nel repo
> → parametri ricavati per convenzione dal branch (forma da `074`). Nessun hook SpecKit eseguito (git
> delegato al `configuration-manager`). MCP `sertor-rag` interrogato per l'ancoraggio
> (`find_symbol build_governance_plan`/`AssistantProfile`, `search_code`) — **nessun errore tool**.
>
> **Revisione (decisione utente).** Il concierge è un **AGENTE vero** (con `model: sonnet` su Claude),
> NON uno stub-skill. La feature distribuisce **una skill `guided-setup`** (il «come») **E un agente
> `concierge`** (la persona/orchestratore) — il pattern `sertor-flow` (agenti + skill).

## Summary

Consegna la prima feature **agentica** dell'epica usabilità:
- la **skill `guided-setup`** che l'agente dell'ospite esegue per condurre l'utente da «repo non
  configurato» a «RAG verificato» (un `sertor-rag doctor` verde), orchestrando **solo** i vehicle
  deterministici (`sertor install`, `sertor configure --set`, `sertor-rag doctor`/`index`);
- l'**agente `concierge`** — dispatcher sottile a un solo ramo (instrada verso `guided-setup`), con un
  **model pin** (`model: sonnet` su Claude), che **anticipa FEAT-009**.

Entrambi distribuiti **dual-target** via `sertor install`: skill in `.claude/skills/`↔`.github/skills/`,
agente in `.claude/agents/`↔`.github/agents/`. Coperti dalla **guardia di parità** estesa.

**Natura: ADDITIVO + scope di distribuzione.** Nessun codice runtime del core, nessun motore/porta/
comando nuovo. La feature vive in: 2 asset (1 skill + 1 agente) + wiring in `install_rag.py` +
estensione della guardia/test. `sertor-core` e `sertor-install-kit` **invariati**.

**Tecnica cardine (riuso, non reinvenzione):** **(skill)** il pattern eval (065) — byte-copia
host-agnostica nei contenitori `skills/`. **(agente)** il pattern `sertor-flow`
(`install_governance.py`) — `Surface.AGENT`/`render_path`/`render_custom_agent` per depositare l'agente
dual-target (Claude byte-copy con `model:` preservato; Copilot `render_custom_agent` con `model:`
omesso). **Nessun nuovo seam nel kit**: `render_custom_agent` è già esportato e usato da `sertor-flow`;
l'unica novità è un helper di render **locale** a `install_rag.py` (come quelli di wiki/governance).

## Technical Context

- **Linguaggio**: Python ≥ 3.11 (plan-builder/test in `sertor`); gli asset sono markdown EN.
- **Pacchetti**: `sertor` (plan-builder + asset + test). **NON** `sertor-core`, **NON**
  `sertor-install-kit` (riuso del seam esistente).
- **Dipendenze esistenti**: `sertor-rag doctor` (FEAT-001, contratto 074), `sertor install rag` /
  `sertor configure --set` (E2), `sertor-rag index .`; il render agente del kit (`render_custom_agent`,
  `Surface.AGENT`, `render_path`) come in `sertor-flow`.
- **Test**: offline (`Fake*Runner`, niente rete/`uv`/ospite reale).
- **NEEDS CLARIFICATION**: nessuno. DA-G1/G2/G3 risolte (spec); DA-D-r1/D-r2 risolte in
  [`research.md`](research.md) (D-1..D-7), riviste per la decisione «agente vero».

## Constitution Check — PRE-design

| Principio | Esito | Note |
|-----------|-------|------|
| I — Core a dipendenze interne | **PASS** | nessuna modifica al core; skill+agente sono asset. |
| II — Provider intercambiabili; local-first | **PASS** | euristica raccomanda locale di default; cloud opt-in confermato. |
| III — YAGNI / unità piccole | **PASS** | riuso integrale: skill=pattern eval, agente=pattern `sertor-flow`; nessuna nuova `ArtifactKind`/`Surface`; helper render locale (non un seam). |
| IV — Errori espliciti | **PASS** | rimanda agli errori azionabili dei vehicle; fail-loud su `doctor` rosso. |
| V — Testabilità/misura | **PASS** | guardia di parità + test di deposito/frontmatter offline. |
| VI — Idempotenza/non-distruttività | **PASS** | `CREATE_IF_ABSENT`; rileva→verifica, non ri-scaffolda; mutazioni solo su conferma. |
| VII — Leggibilità | **PASS** | wiring chirurgico (`_skill_artifacts` generica, `_concierge_artifact`, `_render_rag_file` — gemelli di wiki/governance). |
| VIII — Config centralizzata | **PASS** | provider in `.env` via `configure` (fonte unica `Settings`); nessun default nuovo. |
| IX — Osservabilità | **PASS (N/A runtime)** | nessuna operazione runtime nuova. |
| X — Host-agnostico | **PASS** | body byte-identico, riferimento-per-nome; distribuzione dual-target di skill+agente è il cuore; `model:` pin gestito by-target (preservato Claude / omesso Copilot). |
| XI — Consumo via vehicles | **PASS** | la skill orchestra CLI/MCP, mai importa `sertor_core`; prescritto nel body (hard boundary). |
| XII — Fail Loud, Fix the Cause | **PASS** | verify fail-loud (US5): nessun «fatto» presunto. |
| **Allineamento alla missione** | **PASS** | usabilità periferica ma serve adozione/portabilità (Principio X): un agente che installa/configura/verifica Sertor da solo È host-agnosticità reale; ancorata a CS-1 dell'epica sopra `doctor`. |

**Esito PRE: PASS 12/12 + missione PASS, nessuna deroga.**

## Project Structure (artefatti di questa feature)

```
specs/075-guided-setup/
├─ spec.md
├─ research.md                     # D-1..D-7 (DA-D-r1/D-r2 risolte, revisione agente)
├─ data-model.md                   # inventario asset (skill+agente) + punti di wiring
├─ contracts/
│  ├─ skill-guided-setup.md
│  ├─ agent-concierge.md           # agente vero, model: sonnet, render dual-target
│  └─ distribution-parity.md
├─ quickstart.md
└─ plan.md

# Asset sorgente CREATI (bundle `sertor`):
packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md
packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md           # NUOVO albero agents/

# Wiring MODIFICATO:
packages/sertor/src/sertor_installer/install_rag.py            # W1-W7 (research D-4)

# Guardia/test MODIFICATI (offline):
packages/sertor/tests/test_assets_copilot_parity.py           # _render_rag render-aware + closure (G1-G3)
packages/sertor/tests/test_install_rag.py                     # deposito + frontmatter + lifecycle

# Tracciamento scope:
requirements/usabilita/epic.md                                # FEAT-002 in progress, FEAT-009 stub agente
```

## Phase 0 — Research

Completata in [`research.md`](research.md). Sintesi:
- **D-0** pattern accertato: skill RAG byte-copia in `skills/`; **agenti dual-target via `sertor-flow`**
  (`_SERTOR_AUTHORED`/`Surface.AGENT`/`render_custom_agent`, `model:` preservato Claude / omesso
  Copilot); kit espone già tutto (nessun nuovo seam).
- **D-1** concierge = **agente vero** `concierge` (`agents/`, `model: sonnet`) + skill `guided-setup`
  (`skills/`); stub-skill rimosso.
- **D-2** body `guided-setup`: single-file EN, 10 sezioni; riferimento-per-nome.
- **D-3** euristica = 3 segnali via vehicle/file → proposta+conferma.
- **D-4** wiring = skill (`_skill_artifacts`) + agente (`_concierge_artifact` con `render_path` +
  helper render-aware locale `_render_rag_file`); owned_dirs (skill) + owned_files (agente); upgrade
  render-aware.
- **D-5** parità: `_render_rag` allineato al render reale (traduce `.agent.md` → il `model:` Claude non
  sfugge); closure mirata; `test_no_wiki_artifacts_created` ristretto a «no agente wiki».
- **D-6** test di deposito offline. **D-7** tracciamento FEAT-009 (stub agente).

## Phase 1 — Design & Contracts

- **Data model** ([`data-model.md`](data-model.md)): inventario asset (skill+agente) + 7 punti di
  wiring + file toccati/creati enumerati.
- **Contracts** ([`contracts/`](contracts/)): skill, **agente** (model pin + render dual-target),
  distribuzione/parità (incl. il punto critico `_render_rag` render-aware).
- **Quickstart** ([`quickstart.md`](quickstart.md)).

### Decisioni di design risolte (DA-D-r1/D-r2)

| ID | Decisione | Razionale |
|----|-----------|-----------|
| DA-D-r1 (asset) | skill `guided-setup` single-file EN; **agente `concierge`** (dispatcher 1 ramo, `model: sonnet` su Claude); euristica a 3 segnali via vehicle/file; body host-agnostico, riferimento-per-nome | pattern `sertor-flow` (skill «come» + agente «persona» con modello fissato); lezione FEAT-001/056 (no leak nel body) + FEAT-011/049 (`model:` omesso su Copilot) |
| DA-D-r2 (wiring) | skill via `_skill_artifacts`/byte-copy; agente via `Surface.AGENT`/`render_path`/`render_custom_agent` (helper `_render_rag_file` locale, NO seam kit); owned_dirs+owned_files; upgrade render-aware; guardia: `_render_rag` allineato + closure mirata | riuso del kit (già usato da `sertor-flow`); il punto critico è far rendere alla guardia ciò che il plan deposita davvero |

## Constitution Check — POST-design

- **III/X**: skill=pattern eval, agente=pattern `sertor-flow`, helper render **locale** (non un seam) →
  riuso massimo, parità by construction (frontmatter tradotto). **PASS.**
- **XI/D↔N**: il contratto skill prescrive l'hard boundary (mai `sertor_core`/`build_*`); l'agente è
  instradamento + orchestrazione via la skill, non importa il core. **PASS.**
- **X (model pin)**: `model: sonnet` preservato su Claude, **omesso** su Copilot dal renderer esistente
  — verificato come `sertor-flow` con `requirements-analyst`/`configuration-manager`. La guardia
  (`_render_rag` render-aware) garantisce che il `model:` Claude non sfugga su Copilot. **PASS.**
- **VI**: `CREATE_IF_ABSENT`; lifecycle skill=owned_dir, agente=owned_file. **PASS.**
- **Additività (RNF-7)**: `sertor-core`/`sertor-install-kit` invariati; install RAG invariato salvo +1
  skill +1 agente; `doctor`/`configure`/`index` invariati. **PASS.**

**Esito POST: PASS 12/12 + missione PASS, nessuna deroga.**

## Tracciamento dello scope (durevole)

- **FEAT-009** (`requirements/usabilita/epic.md:180`) → **«parzialmente avviata (stub agente
  `concierge` a un ramo)»**: gli altri rami (config-recommender FEAT-004 / search-diagnose FEAT-007) +
  i check proattivi restano FEAT-009. NON duplicata, NON done.
- **FEAT-002** (`:172`) → **in progress** (spec/plan 075).
- **FEAT-003 / FEAT-004**: consumo opzionale citato «quando disponibili»; voci esistenti, nessuna
  orfana in `specs/`.
- **«Feature completa»**: done **solo** quando Claude **E** Copilot ricevono **skill E agente** via
  `sertor install` (FR-010/011 — in ambito). Prova LIVE su ospite reale = follow-up.

## Rischi / aperti per `/speckit-tasks`

- **R-1 (guardia render-aware — CRITICO)**: `_render_rag` nel test di parità deve essere allineato al
  render reale del plan (tradurre `.agent.md`), altrimenti il `model: sonnet` del frontmatter Claude
  potrebbe sfuggire ai check di leak su Copilot. È il primo task della guardia (D-5/G1).
- **R-2 (closure per nome-asset)**: l'agente cita `guided-setup` per nome → closure mirata «ogni asset
  citato è depositato» (la file-based non lo cattura).
- **R-3 (`test_no_wiki_artifacts_created`)**: va **ristretto** da «no agente» a «no agente wiki» (il rag
  plan ora deposita l'agente `concierge` in `agents/`). Senza questa modifica il test esistente
  fallisce.
- **R-4 (prova LIVE)**: done automatico offline; prova su Claude/Copilot reale = follow-up
  non-bloccante.
- **Nessun NEEDS CLARIFICATION residuo.**

## Brief di commit (per il `configuration-manager`)

- **Tipo/scope**: `docs(plan): piano E12-FEAT-002 guided-setup (075) — skill + agente concierge`.
- **File da includere** (solo artefatti di design):
  - `specs/075-guided-setup/research.md`
  - `specs/075-guided-setup/data-model.md`
  - `specs/075-guided-setup/contracts/skill-guided-setup.md`
  - `specs/075-guided-setup/contracts/agent-concierge.md`
  - `specs/075-guided-setup/contracts/distribution-parity.md`  *(eliminato `contracts/stub-concierge.md`)*
  - `specs/075-guided-setup/quickstart.md`
  - `specs/075-guided-setup/plan.md`
  - `CLAUDE.md` (blocco-piano aggiornato a 075 corrente / 074 storico)
- **Corpo (perché)**: design della prima feature agentica usabilità — skill `guided-setup` (il «come»)
  + **agente vero `concierge`** (persona/orchestratore, `model: sonnet` su Claude) — revisione su
  decisione utente (NON skill-only). Riuso dei pattern di distribuzione esistenti: skill=eval (065),
  agente=`sertor-flow` (`Surface.AGENT`/`render_custom_agent`). Nessuna nuova `ArtifactKind`/`Surface`,
  nessun seam nel kit, `sertor-core`/`sertor-install-kit` invariati. Constitution PASS 12/12 + missione.
- **NON includere**: `requirements/usabilita/epic.md` (tracciamento FEAT-009) → in implementazione o in
  commit separato `docs(usabilita): …`. Ricordare la **eliminazione** di
  `specs/075-guided-setup/contracts/stub-concierge.md` (file rimosso, va in `git rm`/staging della
  delezione). Branch `075-guided-setup`.
- **NON eseguire** hook SpecKit né git distruttivo.
