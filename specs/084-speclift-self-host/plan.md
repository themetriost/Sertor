# Implementation Plan: Self-hosting / dogfooding di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` | **Date**: 2026-07-01 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification da `specs/084-speclift-self-host/spec.md` +
`requirements/speclift/self-host/requirements.md` + recon `wiki/sources/input-other-agents/speclift-recon.md`.

## Summary

Vendorare **SpecLift** (handoff Sinthari, `master @ be4da28`, MVP 104 test) nel repo Sertor come nuovo
membro del workspace `uv` **`packages/speclift`**, così da poterlo usare in **dogfooding** — generare
requisiti EARS ancorati e riverificati dai changeset reali di Sertor, alimentando il *lint semantico*
del rituale di step con evidenza ancorata. La feature è **additiva / vendoring**: **`sertor_core`
resta byte-identico** (Principio XI), SpecLift consuma il RAG **esclusivamente** via il vehicle CLI
`sertor-rag search --type code --json` (subprocess), **mai** importando il core. La distribuzione su
ospiti esterni è **FEAT-002**, fuori ambito.

**Approccio tecnico (dal research):** copia one-shot pinnata a `be4da28` con nota di provenienza (D-1);
`jsonschema` → dev-deps, runtime stdlib-only (D-2); vehicle configurato alla root Sertor patchando la
costante `SERTOR_RAG_VEHICLE = ("uv","run","sertor-rag")` (D-3); `requires-python` abbassato a `>=3.11`
con verifica empirica su 3.11, piano B dichiarato se irriducibile (D-4); ruff di root **esclude**
`packages/speclift` (precedente `prototype`), speclift tiene il proprio `[tool.ruff]` (D-5); test
integrati col **modello per-pacchetto** + step CI dedicato, marker `contract`/`integration` nel suo
pyproject → nessun conflitto (D-6); `LICENSE` MIT + provenienza che registra l'assenza upstream
(stessa-org handoff, D-7); versione statica `0.1.0`, escluso dal test di packaging distribuibile (D-8);
skill dogfood copia fedele (già host-agnostica e onesta), onestà doc↔codice nei doc/wiki (D-9).

## Technical Context

**Language/Version**: Python `>=3.11` (riconciliato da `>=3.12`, D-4). CI su 3.12 (`ci.yml:33-37`).

**Primary Dependencies**: runtime **nessuna** (stdlib-only + subprocess `git`/`sertor-rag`); dev:
`pytest>=8`, `ruff>=0.6`, `jsonschema>=4` (test di contratto). Nessuna dipendenza da altri membri.

**Storage**: N/A. SpecLift legge il filesystem (git diff, verifica àncore) e consuma l'indice RAG di
Sertor via CLI; non scrive stato persistente proprio.

**Testing**: `pytest` (28 file, 104 test: contract/integration/unit); marker `contract`/`integration`;
integration offline (git-fixture locale).

**Target Platform**: Windows + Linux (matrice CI), offline-capable (nessuna rete richiesta dai test).

**Project Type**: pacchetto CLI vendorato = nuovo membro del monorepo `uv` (dominio puro
ports&adapters, hatchling). Non un servizio, non una libreria del core.

**Performance Goals**: N/A (strumento su richiesta, determinismo prioritario su throughput).

**Constraints**: `sertor_core` invariato (Principio XI); zero ciclo di dipendenze; vehicle-only;
fail-loud sul prerequisito RAG (exit 3); skill host-agnostica; suite verde nel workspace.

**Scale/Scope**: 1 nuovo membro workspace; ~25 file sorgente vendorati + 28 file test; ~5 punti di
integrazione (root `pyproject.toml` × 2, `ci.yml`, pyproject del pacchetto, `.claude/skills/`); 3
divergenze funzionali minime tracciate (vehicle, jsonschema, messaggio rimedio).

## Constitution Check

*GATE — v1.4.0. PASS/FAIL per principio; ogni FAIL va risolto o giustificato in Complexity Tracking.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE): PASS.** `sertor_core` invariato; SpecLift ha
  il proprio dominio puro ports&adapters (adapter concreti dietro le porte `EvidenceLocator`/
  `AnchorResolver`/`EarsAuthor`), zero SDK nel dominio. Non tocca la struttura di dipendenze del core.
- [x] **II — Boundary & local-first: PASS.** SpecLift è interamente locale (git + filesystem +
  subprocess CLI); nessun provider cloud. Il consumo RAG è dietro l'astrazione `SertorRagLocator`
  (vehicle). N/A per vector store (non ne ha uno proprio).
- [x] **III — YAGNI & unità piccole: PASS.** Copia one-shot (non sync, D-1); patch della costante (non
  env-var, D-3); esclusione ruff (non riformattazione, D-5). Ogni scelta è la minima che soddisfa il
  requisito; le generalizzazioni (env-var, sync, distribuzione) sono rinviate a FEAT-002.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE): PASS.** `RagUnavailableError` → exit 3, niente `None`
  silenzioso, niente stato parziale; upstream conforme e preservato (`rag_sertor.py:87-99`).
- [x] **V — Testabilità & misure: PASS.** 104 test F.I.R.S.T. integrati e verdi nel workspace (CS-4) +
  verifica empirica su 3.11 (FR-018). hit@k/MRR **N/A** (SpecLift non è un motore di retrieval — la
  misura pertinente è la suite verde e il moat deterministico).
- [x] **VI — Idempotenza & non-distruttività: PASS.** Sandwich deterministico (RNF-6); il vendoring
  non avvia indicizzazione (install≠run); nessuna sovrascrittura di file utente; `assemble` rilegge
  input e riverifica sul filesystem.
- [x] **VII — Leggibilità: PASS.** Codice vendorato fedele e leggibile (vocabolario di dominio:
  ingest/parse/locate/lift/verify/render); commenti solo d'intenzione.
- [x] **VIII — Configurabilità centralizzata: PASS.** Il vehicle vive in `config.py` (config
  centralizzata di SpecLift), non hardcodato sparso. La patch cambia un **default di configurazione**,
  nel locus deputato.
- [x] **IX — Osservabilità: PASS (N/A per il core).** SpecLift ha la sua `observability.py`; questa
  feature non introduce operazioni nel core Sertor da loggare. Nessun segreto nei log.
- [x] **X — Host-agnostico (NON-NEGOZIABILE): PASS.** La **skill** resta host-agnostica (no
  path-assistente/slash/nome-modello — verificata). Il vehicle Sertor-specifico vive in `config.py`
  (config), **non** nel corpo della capacità né nella skill; è ciò che «varia per ospite» → nel locus
  giusto. La piena host-configurabilità (env-var/config-all'install) è **FEAT-002**. Il dogfooding non
  è usato come licenza per accoppiare il corpo. *(Tensione III↔X esplicitata e risolta senza deroga,
  research D-3.)*
- [x] **XI — Consumo via vehicles: PASS.** Consumo RAG **solo** via CLI `sertor-rag` (subprocess);
  **zero** `import sertor_core` (grep negativo verificato, uniche occorrenze = commenti dichiarativi).
  Nessuna nuova via d'accesso diretto introdotta.
- [x] **XII — Fail Loud, Fix the Cause: PASS.** Il prerequisito RAG mancante **emerge** (exit 3 +
  messaggio, reso azionabile col rimedio `sertor-rag index .`); nessuna soppressione, nessun degrado
  silenzioso. Il finding «Sinthari senza LICENSE» è **segnalato** (research D-7), non sepolto.
- [x] **Allineamento alla missione: PASS (indiretto, dichiarato con onestà).** SpecLift **non** tocca
  il differenziatore diretto (fusione code+doc / motori / hit-rate): è **periferico**. Il contributo è
  **indiretto ma reale**: produce requisiti ancorati e riverificati che tengono `requirements/`/wiki/
  `CLAUDE.md` **onesti rispetto al codice reale**, rafforzando **veridicità e freschezza** del contesto
  che il RAG poi serve. Non gonfiato: la spec stessa lo dichiara periferico (§Allineamento alla missione).

**Esito pre-design: PASS 12/12 + missione PASS.** Nessuna deroga. **Complexity Tracking vuoto.**

## Project Structure

### Documentation (this feature)

```text
specs/084-speclift-self-host/
├── plan.md                       # questo file
├── research.md                   # Fase 0 — 9 decisioni (D-1..D-9)
├── data-model.md                 # Fase 1 — entità di integrazione E1..E6
├── quickstart.md                 # Fase 1 — ciclo bundle→autoring→assemble + verifiche
├── contracts/
│   ├── rag-vehicle-contract.md   # SpecLift → sertor-rag search --type code --json
│   └── workspace-integration.md  # membri/uv.lock/no-ciclo/lint/pytest/CI
└── tasks.md                      # Fase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)

```text
packages/speclift/                         # NUOVO membro del workspace (vendorato, D-1)
├── pyproject.toml                          # requires-python >=3.11; deps runtime []; [tool.ruff]/[pytest] propri
├── LICENSE                                 # MIT (convenzione workspace, D-7)
├── VENDORING.md                            # nota di provenienza + divergenze (E2)
├── src/speclift/
│   ├── config.py                           # DIVERGENZA: SERTOR_RAG_VEHICLE = ("uv","run","sertor-rag") (D-3)
│   ├── cli.py  pipeline.py  serialize.py  observability.py
│   ├── domain/{models,ports,errors}.py     # dominio puro (invariato)
│   ├── adapters/{git_diff,rag_sertor,anchor_fs,authored,ears_requirements}.py
│   │                                       # rag_sertor.py: messaggio RagUnavailableError con rimedio (D-3, Should)
│   ├── stages/{ingest,parse_diff,filter_sources,locate_evidence,bundle,lift,verify,render}.py
│   └── skills/speclift/SKILL.md            # sorgente vendorato (host-agnostico, fedele)
└── tests/{contract,integration,unit}/      # 104 test; marker contract/integration

.claude/skills/speclift/SKILL.md            # copia dogfood (deposito, D-9)

pyproject.toml (root)                       # members += packages/speclift; ruff extend-exclude += packages/speclift
.github/workflows/ci.yml                    # step "Tests — speclift" (+ opz. "Lint — speclift")
uv.lock                                     # rigenerato

# INVARIATI: src/sertor_core/**, src/sertor_mcp/**, packages/{sertor,sertor-install-kit,sertor-flow}/**
```

**Structure Decision.** `packages/speclift` è un membro del workspace **senza dipendenze da altri
membri** (come `sertor-install-kit` è senza dipendenze *in ingresso*): grafo aciclico garantito
(`speclift → ∅`). L'integrazione tocca **5 punti** (root pyproject × 2, CI, pyproject del pacchetto,
`.claude/skills/`) + 6 divergenze tracciate in `VENDORING.md`. Il core e gli altri membri sono
byte-identici.

## Fasi di lavoro (per /speckit-tasks)

1. **Vendoring (D-1).** Copia `src/speclift/**`, `tests/**`, `skills/speclift/SKILL.md` da Sinthari
   `be4da28` in `packages/speclift/`. Crea `LICENSE` (MIT) e `VENDORING.md` (E2).
2. **pyproject del pacchetto (D-2/D-4/D-5/D-6/D-8).** `requires-python >=3.11`; `dependencies = []`,
   `dev += jsonschema`; versione statica `0.1.0`; `[tool.ruff]` (110/`SIM`/`py311`);
   `[tool.pytest.ini_options]` (marker `contract`/`integration`).
3. **Divergenze funzionali (D-3).** Patch `config.py` (`SERTOR_RAG_VEHICLE`); messaggio azionabile in
   `rag_sertor.py` (Should). Ogni divergenza → riga in `VENDORING.md`.
4. **Integrazione workspace.** Root `pyproject.toml`: `members += packages/speclift`,
   `ruff extend-exclude += packages/speclift`. `uv sync --all-packages` → `uv.lock`.
5. **Verifica empirica.** `uv run pytest packages/speclift/tests -m "not cloud"` verde;
   `uv run --python 3.11 pytest …` verde (accettazione FR-018; se rosso per costrutto 3.12-only →
   piano B FR-019, dichiarazione). `uv run ruff check .` verde (speclift escluso).
6. **CI (D-6).** Step `Tests — speclift` nel job `test`. (Opz. `Lint — speclift`.)
7. **Skill dogfood (D-9).** Deposita `.claude/skills/speclift/SKILL.md` (copia fedele).
8. **Non-regressione.** `git diff -- src/sertor_core pyproject.toml` sul core = solo le 2 righe di
   workspace/ruff attese; grep `import sertor_core` su `packages/speclift/src` = 0; suite altri membri
   verdi.
9. **Verifica di dogfooding e2e.** `bundle → autoring → assemble` su un commit reale con indice fresco;
   report riverificato; fail-loud su indice assente (exit 3 + rimedio).

## Constitution Check (post-design)

Dopo la definizione degli artefatti (research/data-model/contracts/quickstart), **nessun principio è
violato e nessuna nuova complessità è introdotta**:

- I/IV/X/XI (non-negoziabili) restano **PASS**: core invariato, vehicle-only, skill host-agnostica,
  errori espliciti fail-loud. La tensione III↔X sul vehicle è risolta collocandolo in `config.py`
  (locus di configurazione), non nel corpo/skill.
- III **PASS**: gli artefatti confermano scelte minime (one-shot, patch-costante, esclusione-ruff) e
  rinviano le generalizzazioni a FEAT-002 — nessuna astrazione speculativa.
- V/VI/XII **PASS**: suite integrata + moat deterministico + fail-loud azionabile.
- Missione **PASS** (indiretto, non gonfiato).

**Esito post-design: PASS 12/12 + missione PASS.** Nessuna deroga. **Complexity Tracking vuoto.**

## Tracciamento dello scope (rinvii promossi, non sepolti)

- **Distribuzione su ospiti esterni** (installer/packaging, env-var vehicle, sync bundlato↔dogfood,
  guardia di sync skill, generalizzazione host-agnostica del vehicle) → **FEAT-002** (backlog epica
  `speclift`).
- **Traduzione IT→EN** degli asset SpecLift → tema **E12**.
- **SpecAudit / Debrief / Guida al test** → **FEAT-003/004/005** (stesso backlog).
- **Finding LICENSE upstream assente** → segnalato in `VENDORING.md` (D-7); conferma col proprietario
  upstream raccomandata (stessa-org, proseguibile).
- **Step CI `Lint — speclift`** → opzionale, aggiungibile in tasks; non necessario per la verde del
  gate di root.

## Complexity Tracking

*Nessuna violazione da giustificare — vuoto.*

## Nota di processo

`.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** →
parametri per convenzione dal branch `084-speclift-self-host` (forma dai plan `074`–`083`). Nessun hook
SpecKit eseguito. **Git non eseguito** (delega a `configuration-manager`). MCP `sertor-rag` interrogato
(`search_code` sull'output della CLI `search`, `search_docs` sul precedente vendoring SpecKit):
**nessun errore tool**. Il codice SpecLift è ancorato al clone Sinthari `be4da28`; il codice Sertor via
MCP + `Read`.

## Brief di commit (per `configuration-manager`)

- **Messaggio:** `docs(plan): piano FEAT-001 speclift — self-host/dogfooding di SpecLift (branch 084)`
- **Corpo (perché):** aggiunge gli artefatti di design (plan/research/data-model/contracts/quickstart)
  per vendorare SpecLift come `packages/speclift`, dogfooding-only, `sertor_core` invariato, vehicle-only.
  Constitution PASS 12/12 + missione PASS, nessuna deroga.
- **File da includere:**
  - `specs/084-speclift-self-host/plan.md`
  - `specs/084-speclift-self-host/research.md`
  - `specs/084-speclift-self-host/data-model.md`
  - `specs/084-speclift-self-host/contracts/rag-vehicle-contract.md`
  - `specs/084-speclift-self-host/contracts/workspace-integration.md`
  - `specs/084-speclift-self-host/quickstart.md`
  - `CLAUDE.md` (aggiornamento riferimento al piano tra i marker SpecKit)
- **NON includere:** nessun codice vendorato (è fase implement); nessun `.env`/segreto.
- **Hook SpecKit:** non eseguire `EXECUTE_COMMAND`/hook git.
