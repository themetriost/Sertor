# Implementation Plan: Qualità del retrieval fuso code+doc su query NL/architetturali (FEAT-003)

**Branch**: `069-qualita-fusione-code-doc` | **Date**: 2026-06-21 | **Spec**: [`spec.md`](spec.md)

**Input**: `specs/069-qualita-fusione-code-doc/spec.md` ·
`requirements/retrieval-qualita/qualita-search-code-nl/requirements.md` (REQ-001..043, gruppi A–E,
RNF1–5, DA-a..e) · `requirements/retrieval-qualita/epic.md` (FEAT-003, CS-1..5) · harness su `master`:
`specs/065-ground-truth-valutazione/` (IR) e `specs/066-valutazione-navigazione-grafo/` (graph, pattern).

> **Nota di processo.** `.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> **ASSENTI** nel repo → parametri per convenzione dal branch (modello di forma:
> `specs/066-valutazione-navigazione-grafo/plan.md`); nessun hook SpecKit eseguito. Git **delegato** al
> `configuration-manager` (mai eseguito qui). MCP `sertor-rag` interrogato per l'ancoraggio al codice
> reale (`search_code graph_case suite_io`, `search_code evaluate EvalReport per_query`) + `Read`
> mirati; **nessun errore tool** da riportare.

## Summary

Rendere **misurabile e migliorabile** il differenziatore di Sertor — la **fusione code+doc** — sulle
query NL/architetturali, **prima** di introdurre tecniche, così che ogni «miglioramento» sia ancorato a
un numero (Principio V, stella polare). **Approccio cardine:** estendere l'harness IR esistente
(FEAT-001) in modo **additivo** — `evaluate`/`EvalReport` **invariati** — con tre novità:
1. **Attesi intent-typed** — campo additivo `intent ∈ {code,doc,both}` su `[[case]]` (research DA-b): l'intento
   decide superficie misurata e tipi attesi; i casi `both` **sono** la categoria di fusione (REQ-002/003).
2. **Misura per-superficie** — `search_code`/`search_docs`/`search_combined` misurate via tre adattatori
   `QueryableEngine` sottili sul `RetrievalFacade`, riusando `evaluate` (REQ-010/013); il combined come
   **test d'integrazione**.
3. **Fusion coverage** — metrica **pura e additiva** (REQ-020/021/022): un caso `both` è «coperto» solo
   se il top-k contiene ≥1 risultato `DOC` pertinente **E** ≥1 `CODE` pertinente; i tipi si leggono da
   `RetrievalResult.doc_type` (esiste già), nessuna doppia etichettatura. Riportata **accanto** a hit@k/MRR.

Più **baseline per-superficie + gate** (riuso del meccanismo `Baseline`+tolleranza, esteso) e i **seam**
per la genesi assistita (skill `eval-suite-author` estesa) **senza** che il run dipenda da un LLM. Le
**leve** (query transformation/HyDE, filtro metadata, contextual retrieval) sono opt-in **spente di
default**: la feature le **valuta**, non le prescrive (research DA-a/DA-e). Tutto in `services/eval/`
(moduli additivi/nuovi) + estensione thin del gruppo CLI `eval` (Principio I/XI). 5 forche di design
decise (research): **DA-a** ordine di valutazione metadata→contextual→query-transform (deciso dai
numeri); **DA-b** `intent` additivo + tipi a runtime + ≥8/superficie; **DA-c** baseline per-superficie +
tolleranza 0.0 + lift +0.05 (criterio di adozione, non gate); **DA-d** FEAT-004 ortogonale, FEAT-005/006/007
= leve candidate; **DA-e** target single-shot misurabile.

> **Stella polare.** Questa feature **è** la verifica della mission: rende misurabile con un numero
> (fusion coverage) che una query requisito→implementazione restituisca **doc + codice insieme**. È la
> capacità-firma, non un concern periferico (gate «Allineamento alla missione» → PASS, vedi sotto).

## Technical Context

**Language/Version**: Python ≥ 3.11 (`tomllib` stdlib = floor del progetto).
**Primary Dependencies**: solo **stdlib** (`tomllib`-read, serializzatore TOML a mano già esistente).
L'embedder/lo store sono dietro le porte esistenti (riuso `build_facade`). **Nessuna nuova dipendenza.**
**Storage**: artefatti **versionati** `eval/suite.toml` (esteso con `intent` su `[[case]]`) +
`eval/baseline.toml` (esteso con sezione `[fused_baseline]`, preserve-both). Nessun nuovo file.
**Testing**: `pytest` (unit, `not cloud`, mock/Chroma locale — RNF-1). Funzioni pure (fusion coverage,
`compare_fused_to_baseline`, IO suite/baseline) testabili senza rete; adattatori-superficie con
`RetrievalFacade` mock (structural typing); CLI con runner mockato (stile `test_cli_eval`).
**Target Platform**: CLI host-agnostica (qualunque progetto ospite indicizzato, Principio X).
**Project Type**: libreria + CLI (single project — core `src/sertor_core`, installer `packages/sertor`).
**Performance Goals**: suite di poche decine di casi in tempi interattivi/CI; costo dominato dal
retrieval (embedder+store), non dall'harness; a leve spente costo identico a oggi (RNF-1).
**Constraints**: determinismo (REQ-041, SC-004); additività a leve spente (RNF-1); local-first **zero
LLM** nel run (RNF-3); confine D↔N (run nel core/CLI, genesi nella skill); privacy metrics-only (RNF-3).
**Scale/Scope**: ~2 moduli nuovi in `services/eval/` (`fusion.py`, `fused_runner.py`) + estensioni a
`models.py`/`suite_io.py`/`regression.py`/`baseline_io.py`; estensione thin del gruppo CLI `eval`
(`--fused`/`--intent`); ~2 manopole `Settings`; 1 factory `build_fused_eval_runner` (riusa
`build_facade`); 1 evento osservabilità `fused_eval`; 1 estensione skill (debito P2).

## Constitution Check (PRE-design)

*GATE prima di Phase 0. Gate derivati da `.specify/memory/constitution.md` v1.4.0. Marcare PASS/FAIL.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** la misura vive nel core (fusion coverage =
  funzione pura in `services/eval/fusion.py`; adattatori-superficie dipendono dal **facade** dietro le
  porte, non dall'adapter); il CLI è **thin**. Nessun import di SDK/adapter nei servizi; esercitabile con
  `RetrievalFacade` mock. `evaluate`/`EvalReport` invariati. **PASS**
- [x] **II — Boundary & local-first:** nessun nuovo boundary verso provider (suite/baseline = **dati**;
  il retrieval riusa il facade dietro le porte); misura in locale, zero rete (RNF-3). **PASS**
- [x] **III — YAGNI & unità piccole:** **nessuna nuova porta** (riuso `QueryableEngine`/facade/`CodeGraph`);
  **nessuna nuova dipendenza**; `evaluate` non toccato; `intent` distinto da `kind` solo perché servono
  semantiche diverse (no campo `category` ridondante: `intent="both"` *è* la categoria); tipi a runtime
  (no doppia etichettatura). Funzioni pure piccole. **PASS**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** `SuiteValidationError` nomina il caso con `intent`
  invalido; `SuiteWriteError` (round-trip writer); suite senza casi `intent` → messaggio azionabile +
  report vuoto onesto (non zero ingannevole sul gate); baseline di fusione assente → `no-baseline`
  gestito (gate passa). Nessun `None` silenzioso. **PASS**
- [x] **V — Testabilità & misure:** **è** la feature della misura — rende operativo il Principio V per la
  fusione (fusion coverage + per-superficie su ground-truth; «nessun migliore senza numero», REQ-014).
  Funzioni pure F.I.R.S.T.; facade mock; baseline = livello accettato del progetto. **PASS**
- [x] **VI — Idempotenza & non-distruttività:** `add_case --intent`/`amend_case` preservano i casi
  esistenti, i `[[graph_case]]` e i casi senza intent (DA-d), idempotenti su `query`, round-trip
  validato; `[fused_baseline]` scritta **solo** su `--record-baseline`, senza toccare il `[baseline]` IR.
  Determinismo del run (SC-004). **PASS**
- [x] **VII — Leggibilità:** vocabolario di dominio (search/fuse/coverage/baseline/regression/intent);
  funzioni piccole, guard clause; costante `INTENT_SURFACE` esplicita. **PASS**
- [x] **VIII — Configurabilità centralizzata:** `eval_tolerance` (riuso) + `eval_fusion_k` default **solo**
  in `Settings` (env `SERTOR_EVAL_TOLERANCE`/`SERTOR_EVAL_FUSION_K`), mai hardcodati. **PASS**
- [x] **IX — Osservabilità:** il run emette evento `fused_eval` (cases per intento, MRR/hit per
  superficie, fusion_coverage, hit_but_not_covered, regressed, tolerance) via `log_event`; **metrics-only,
  nessun query/path/nome/testo libero** (RNF-3, contract `event-fused-eval.md`), gemello di `eval`/
  `graph_eval`. **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** suite/baseline = dato dell'**ospite** in `eval/` (override
  config), niente assunzioni Sertor nel corpo; path relativi alla root indicizzata; tipi letti da
  `doc_type` (universale code/doc). Manopole nel template `.env` dell'installer; skill estesa via installer
  (debito P2 tracciato). **PASS**
- [x] **XI — Consumo via vehicles:** il run accede al retrieval **solo** via `build_fused_eval_runner`→
  `build_facade` (il CLI è il vehicle); la skill esterna invoca i **sottocomandi** (`eval add-case
  --intent`, `eval validate-path`), **mai** importa `sertor_core`; eccezione test invariata. **PASS**
- [x] **XII — Fail Loud, Fix the Cause:** suite/intent/baseline che falliscono → errore azionabile o
  warning visibile (mai silenzio); una leva senza lift **non** viene adottata ma la misura **lo segnala**
  (non si nasconde l'assenza di guadagno); REQ-022 rende **visibile** la lacuna (hit ma non covered) invece
  di mascherarla con hit@k. Nessuna capacità spenta per schivare un errore. **PASS**
- [x] **Allineamento alla missione (fusione code+doc, qualità del retrieval reso all'agente):** la
  feature **rafforza direttamente** la stella polare — rende **verificabile con un numero** che il
  retrieval fuso restituisca doc+codice insieme (caso requisito→implementazione) e impedisce che un tipo
  anneghi l'altro (fusion coverage, REQ-020/022). È la capacità-firma della mission, non deriva su concern
  periferici. **PASS**

**Esito PRE-design: 12/12 PASS, nessuna deroga.**

## Project Structure

### Documentation (this feature)
```text
specs/069-qualita-fusione-code-doc/
├── plan.md                  # questo file
├── research.md              # Phase 0: 5 forche (DA-a..DA-e) + cardine architetturale + mecc/giudizio
├── data-model.md            # Phase 1: entità additive a services/eval/models.py + servizi + factory
├── quickstart.md            # Phase 1: percorso utente end-to-end
├── contracts/
│   ├── cli-eval-fused.md    # `eval run --fused` + `eval add-case --intent`
│   ├── artifacts-toml.md    # campo `intent` su [[case]] + sezione [fused_baseline]
│   └── event-fused-eval.md  # evento osservabilità `fused_eval` (metrics-only)
└── tasks.md                 # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)
```text
src/sertor_core/
├── services/
│   └── eval/
│       ├── models.py          # ESTESO: EvalCase.intent; FusionCaseResult/FusionReport/
│       │                      #         SurfaceEvalReport/FusedEvalReport/SurfaceBaseline/
│       │                      #         FusedBaseline/FusedRegressionVerdict; helper su EvalSuite
│       ├── suite_io.py        # ESTESO: _parse_case/_serialize_suite gestiscono `intent`
│       │                      #         (preservando [[graph_case]]); add_case/amend_case + intent
│       ├── fusion.py          # NUOVO: fusion_coverage(...) puro + INTENT_SURFACE
│       ├── fused_runner.py    # NUOVO: run_fused_evaluation + _SurfaceEngine + emit_fused_eval_event
│       ├── regression.py      # ESTESO: compare_fused_to_baseline (puro)
│       └── baseline_io.py     # ESTESO: load/write sezione [fused_baseline] (preserve-both)
├── config/
│   └── settings.py            # + eval_fusion_k (default + env); eval_tolerance riusato
├── composition.py             # + build_fused_eval_runner (riusa build_facade)
└── cli/
    ├── __main__.py            # + --fused su `eval run`; + --intent su `eval add-case`/`amend-case`
    └── output.py              # + format_fused_eval_report / format_fused_regression

packages/sertor/src/sertor_installer/assets/rag/
├── env.local.tmpl             # + SERTOR_EVAL_FUSION_K (commentata)
├── env.azure.tmpl             # idem
└── skills/eval-suite-author/SKILL.md  # ESTESO (genesi `intent`/casi `both`) — debito P2

eval/                          # DOGFOOD (repo Sertor): + casi NL intent-typed di esempio
└── suite.toml                 # esteso (esempio, non spedito agli ospiti)

tests/
├── unit/                      # fusion (coverage + edge REQ-022), fused_runner (facade mock),
│                              # suite_io (intent round-trip + preserve graph_case), regression fused,
│                              # baseline_io fused, cli eval --fused/--intent, output
└── integration/               # gate fusione e2e su indice Chroma locale (not cloud)
```

**Structure Decision**: single project. Il **core** ospita la misura (moduli `services/eval/fusion.py`+
`fused_runner.py` + estensione additiva di `models.py`/`suite_io.py`/`regression.py`/`baseline_io.py`); il
**CLI** estende thin il gruppo `eval`; l'**installer** cabla la manopola. Il retrieval riusa `build_facade`.
La skill estesa segue (P2 — gruppo E). **`evaluate`/`EvalReport` INVARIATI**.

## Phase 0 — Research
Vedi [`research.md`](research.md). **Cardine:** estensione additiva dell'harness IR (NON un secondo
oracolo come FEAT-011 — la misura è rank-based; la fusion coverage è un passaggio puro sui `doc_type`).
Forche: **DA-a** ordine di valutazione leve metadata→contextual→query-transform, deciso dai numeri (finding:
query-transform rischia RNF-3 se introduce LLM nel run); **DA-b** campo `intent` additivo, tipi a runtime,
≥8/superficie (≥6 fusione), genesi via skill (P2); **DA-c** baseline per-superficie + tolleranza 0.0 +
lift +0.05 (adozione, non gate; target assoluto fusion coverage = Could); **DA-d** FEAT-004 ortogonale,
FEAT-005/006/007 = leve candidate (le loro feature = il «come»); **DA-e** target single-shot misurabile.

## Phasing implementativo (MECCANICO prima, GIUDIZIO dopo)
**MUST — infrastruttura di misura (tutto meccanico, deterministico):**
1. schema: `EvalCase.intent` + `suite_io` (parse/serialize/add/amend, preserve-both).
2. metrica: `fusion.py` (fusion coverage puro) + adattatori-superficie + `fused_runner`.
3. baseline per-superficie + `compare_fused_to_baseline` + `baseline_io` (sezione `[fused_baseline]`).
4. vehicle: `build_fused_eval_runner` + CLI `eval run --fused`/`add-case --intent` + output + evento.
5. dogfood: casi NL intent-typed in `eval/suite.toml`; **registrare le baseline reali**.

**SOLO DOPO — empirico (Should, giudizio + misura):**
6. valutare ≥1 leva opt-in (ordine DA-a) → confronto vs baseline; adottarla **solo** con lift misurato,
   spenta di default; la sua feature dedicata (FEAT-005/006/007) diventa il «come».
7. genesi assistita: estendere la skill `eval-suite-author` (debito di completamento P2).

## Phase 1 — Design
[`data-model.md`](data-model.md) (entità additive + servizi + factory) · [`contracts/`](contracts/)
(CLI / TOML / evento) · [`quickstart.md`](quickstart.md). `CLAUDE.md` aggiornato (riferimento al piano
corrente, marker SPECKIT).

## Constitution Check (POST-design)

*Re-check dopo Phase 1.*

- [x] **I** — Design confermato: fusion coverage pura nel core, adattatori-superficie sul **facade** dietro
  le porte, CLI thin, mock-testabile; `evaluate`/`EvalReport` invariati. **PASS**
- [x] **II** — Nessun nuovo boundary provider; retrieval riusa il facade; local-first preservato. **PASS**
- [x] **III** — Zero porte nuove, zero dipendenze nuove; entità additive con default neutri; `evaluate`
  intatto; baseline di fusione nello stesso `baseline.toml` (no file separato superfluo). **PASS**
- [x] **IV** — Errori di dominio espliciti + assenze gestite (no casi intent → messaggio+report vuoto;
  baseline assente → `no-baseline`; intent invalido → `SuiteValidationError` che nomina il caso). **PASS**
- [x] **V** — Funzioni pure F.I.R.S.T.; la feature realizza la misura della fusione (Principio V), criterio
  «nessun migliore senza numero» nel gate/adozione. **PASS**
- [x] **VI** — Writer non-distruttivo/idempotente che preserva `[[case]]` (con/senza intent) e
  `[[graph_case]]` (DA-d, round-trip validato); `[fused_baseline]` solo su flag; determinismo. **PASS**
- [x] **VII** — Naming di dominio, unità piccole, `INTENT_SURFACE` esplicita. **PASS**
- [x] **VIII** — `eval_fusion_k`/`eval_tolerance` solo in `Settings`. **PASS**
- [x] **IX** — Evento `fused_eval` metrics-only (contract `event-fused-eval.md`); dimensioni a cardinalità
  chiusa (`surface`/`intent`), nessun query/path/nome. **PASS**
- [x] **X** — Suite/baseline = dato ospite in `eval/` (config override); path relativi; tipi da `doc_type`
  universale; manopola nel template `.env`; skill estesa via installer (debito P2 tracciato). **PASS**
- [x] **XI** — Run via `build_fused_eval_runner`→`build_facade` (CLI = vehicle); skill esterna via
  sottocomandi, mai import di `sertor_core`; eccezione test invariata. **PASS**
- [x] **XII** — Fallimenti visibili (errori azionabili, warning su path mancanti); REQ-022 rende la lacuna
  visibile invece di mascherarla; una leva senza lift è segnalata, non nascosta; nessuna capacità spenta
  per schivare errori. **PASS**
- [x] **Allineamento alla missione** — Confermato POST-design: la fusion coverage e `hit_but_not_covered`
  rendono **verificabile e storicizzabile** che la feature rafforza la fusione code+doc; è la stella
  polare resa misurabile. **PASS**

**Esito POST-design: 12/12 PASS, nessuna deroga. Complexity Tracking vuoto.**

## Complexity Tracking
Nessuna violazione da giustificare.

## Tracciamento dello scope (Out-of-Scope → casa durevole)
- **Leve come feature a sé** (query transformation/HyDE = FEAT-005; filtro metadata esteso = FEAT-006;
  contextual retrieval = FEAT-007): già **promosse** nel backlog d'epica
  (`requirements/retrieval-qualita/epic.md`). Qui sono **leve candidate** da valutare per misura; la
  feature dedicata diventa il «come» se adottata (DA-d). Nessun rinvio reale vive solo dentro `specs/`.
- **Hold-out di validazione formale**: **Could** (R-1), già nei requisiti §9.
- **Target assoluto di fusion coverage** (es. ≥0.6 per «done»): **Could** — si fissa dopo la baseline
  reale (Principio V), non a priori.
- **Estensione della skill `eval-suite-author`** ai casi NL intent-typed: **debito di completamento P2**
  (gruppo E/Should), da chiudere prima che la capacità conti come *done* su un ospite.
- **Cambio del default** se una leva mostra lift forte: **Could** (richiede decisione esplicita, REQ-031).
