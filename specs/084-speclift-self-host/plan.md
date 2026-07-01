# Implementation Plan: Self-hosting / dogfooding di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` | **Date**: 2026-07-01 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification da `specs/084-speclift-self-host/spec.md` +
`requirements/speclift/self-host/requirements.md` + recon
`wiki/sources/input-other-agents/speclift-recon-pluggable.md` (flow reale) +
`wiki/sources/input-other-agents/speclift-recon.md` (packaging).

> **Rigenerato dopo che Sinthari ha recepito il nostro feedback.** Upstream ha mergiato su `master`
> (**`5ee6fc1`**, PR #7) una versione **PLUGGABLE** dell'`EvidenceLocator` (`ProvidedEvidenceLocator`,
> Adapter B: agente + tool MCP), **senza rimuovere** l'adapter CLI. → **Adottiamo il loro codice reale**:
> la feature diventa **vendoring PURO** (zero fork). Il precedente piano (swap del locator inventato:
> `AgentEvidenceLocator`, `--candidates-out`/`--evidence`, `EvidenceInputError` exit 6) è **SUPERATO**.

## Summary

Vendorare **SpecLift** (Sinthari `master @ 5ee6fc1`, MVP pluggable ~122 test) nel repo Sertor come nuovo
membro del workspace `uv` **`packages/speclift`**, per usarlo in **dogfooding** — generare requisiti EARS
ancorati e riverificati dai changeset reali di Sertor, alimentando il *lint semantico* del rituale di
step con evidenza ancorata. La feature è **additiva / vendoring PURO**: **`sertor_core` resta
byte-identico** (Principio XI), e il **codice `src/**` di speclift è copiato verbatim** (nessun fork). Il
self-host usa l'**Adapter B** pluggable upstream: il retrieval passa dal vehicle **MCP** (tool
`search_code`), orchestrato dall'agente nella skill — **mai** via la CLI `sertor-rag search`, **mai**
importando il core. La distribuzione su ospiti esterni è **FEAT-002**, fuori ambito.

**Approccio tecnico (dal research):**
- **Adozione dell'Adapter B pluggable (D-3):** vendora **entrambi** gli adapter (`SertorRagLocator` +
  `ProvidedEvidenceLocator`) dietro la porta `EvidenceLocator`; il dogfood usa il **three-gear flow reale**
  — `speclift changeset <ref> --out` (candidati) → l'agente localizza coi tool MCP e scrive `located.json`
  → `speclift bundle --changeset … --located …` → `assemble`. `rag_sertor.py` **resta** (dormiente); moat,
  exit-code (malformato→5, flag-misuse→2) e interfaccia (`located.json` chiavato `file::query`,
  `query_keys` G6) sono **quelli upstream**. *(Contratto: `contracts/evidence-locator-port.md` che
  **riferisce** quello upstream, non lo reinventa.)*
- copia one-shot pinnata a **`5ee6fc1`** + `VENDORING.md` (D-1); `jsonschema` → dev, runtime `[]` (D-2);
  `requires-python` a `>=3.11` con verifica empirica, piano B se irriducibile (D-4); ruff di root
  **esclude** `packages/speclift`, speclift tiene il proprio `[tool.ruff]` (D-5); test per-pacchetto +
  step CI, marker nel pyproject di speclift, **suite completa** (D-6); `LICENSE` MIT + provenienza che
  registra l'assenza upstream (stessa-org, D-7); versione statica `0.1.0`, escluso dal packaging
  distribuibile (D-8); skill dogfood = **copia verbatim** (upstream ha già Procedura A/B, D-9).

## Technical Context

**Language/Version**: Python `>=3.11` (riconciliato da `>=3.12`, D-4). CI su 3.12 (`ci.yml:33-37`).

**Primary Dependencies**: runtime **nessuna** (stdlib-only + subprocess `git`); dev: `pytest>=8`,
`ruff>=0.6`, `jsonschema>=4` (test di contratto). **Nessuna** dipendenza da altri membri del workspace,
**nessun** SDK MCP importato (l'MCP è consumato dall'**agente** nella skill, non dal codice SpecLift).

**Storage**: N/A. SpecLift legge il filesystem (git diff, verifica àncore) e, nel flow B, riceve
l'evidenza da `located.json` prodotto dall'agente; non scrive stato persistente proprio. Non tocca il RAG.

**Testing**: `pytest` (**suite completa upstream**, ~122 test; nessuna rimozione — vendoring puro);
marker `contract`/`integration`; integration offline (git-fixture locale; `test_rag_sertor` con runner
mockato).

**Target Platform**: Windows + Linux (matrice CI), offline-capable (nessuna rete richiesta dai test — il
retrieval MCP è nell'agente, non nel codice testato).

**Project Type**: pacchetto CLI vendorato = nuovo membro del monorepo `uv` (dominio puro ports&adapters,
hatchling). Non un servizio, non una libreria del core.

**Performance Goals**: N/A (strumento su richiesta, determinismo prioritario).

**Constraints**: `sertor_core` invariato (Principio XI); codice `src/**` di speclift **verbatim**; zero
ciclo di dipendenze; retrieval del dogfood **solo** via MCP `search_code` (Adapter B), **zero** CLI
`sertor-rag`, **zero** import `sertor_core`; fail-loud su MCP/indice (skill) e su evidenza malformata
(exit 5 upstream); skill host-agnostica nella forma; suite verde nel workspace.

**Scale/Scope**: 1 nuovo membro workspace; ~25 file sorgente **vendorati verbatim** (2 adapter, il seam
pluggable, `query_keys`, la skill Procedura A/B); **zero file di codice modificati** (vs 5+ del design
«swap» superato); ~5 punti d'integrazione workspace (root `pyproject.toml` × 2, `ci.yml`, pyproject del
pacchetto, `.claude/skills/`) + 2 file nostri (`LICENSE`, `VENDORING.md`). Divergenze **solo di
packaging** tracciate in `VENDORING.md`.

## Constitution Check

*GATE — v1.4.0. PASS/FAIL per principio; ogni FAIL va risolto o giustificato in Complexity Tracking.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE): PASS.** `sertor_core` invariato; SpecLift ha il
  proprio dominio puro ports&adapters, vendorato verbatim. La porta `EvidenceLocator` ha **due** adapter
  pluggable (upstream) — Dependency Rule + Plugin allo stato dell'arte: il dominio/stadi non conoscono
  l'adapter concreto. Zero SDK nel dominio.
- [x] **II — Boundary & local-first: PASS.** SpecLift resta interamente locale (git + filesystem +
  lettura di `located.json`). Il retrieval MCP vive **fuori** dal codice SpecLift (nell'agente). N/A per
  vector store proprio.
- [x] **III — YAGNI & unità piccole: PASS (rafforzato).** Il **vendoring puro** è la modifica **minima**:
  adottando il codice pluggable upstream, la nostra divergenza di codice runtime è **zero** (solo
  packaging). Convergere con l'upstream è il migliore risultato DRY/manutenzione — nessuna astrazione
  nostra da mantenere, re-vendoring economico. Le generalizzazioni (distribuzione, config-all'install)
  sono rinviate a FEAT-002.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE): PASS.** Gli exit-code upstream sono adottati tale-e-quali
  (malformato→5, flag-misuse→2, RAG giù dell'Adapter A→3): niente `None` silenzioso, niente evidenza
  vuota/di default, niente àncora fabbricata. Il fail-loud MCP/indice vive nella skill (l'agente si
  ferma). **Nessun** `EvidenceInputError`/exit 6 nostro (era superfluo — l'exit 5 upstream copre
  l'evidenza malformata).
- [x] **V — Testabilità & misure: PASS.** Suite F.I.R.S.T. **completa** integrata e verde nel workspace
  (CS-4), inclusi i test dell'Adapter B (`test_provided_locator`/`test_query_keys`/`test_three_gear_flow`)
  offline. hit@k/MRR **N/A** (SpecLift non è un motore di retrieval — la misura pertinente è la suite
  verde + il moat deterministico).
- [x] **VI — Idempotenza & non-distruttività: PASS.** Stadi deterministici verbatim; il vendoring non
  avvia indicizzazione (install≠run); nessuna sovrascrittura di file utente; `assemble` rilegge input e
  riverifica sul filesystem. *(Deviazione dal sandwich con l'Adapter B: l'agente tocca 2 stadi — è una
  scelta **upstream dichiarata**, vedi nota sotto, non una deroga.)*
- [x] **VII — Leggibilità: PASS.** Vocabolario di dominio preservato verbatim
  (ingest/parse/locate/lift/verify/render + changeset/located/bundle). Nessun nostro rename.
- [x] **VIII — Configurabilità centralizzata: PASS.** `config.py` è vendorato verbatim (incluso
  `SERTOR_RAG_VEHICLE`, usato solo dall'Adapter A dormiente); il percorso dell'evidenza è un argomento CLI
  esplicito upstream, non una costante sparsa.
- [x] **IX — Osservabilità: PASS (N/A per il core).** SpecLift ha la sua `observability.py`
  (`stage_event`); la feature non introduce operazioni nel core Sertor da loggare. Nessun segreto nei log.
- [x] **X — Host-agnostico (NON-NEGOZIABILE): PASS (con confine dichiarato).** La skill upstream è **già**
  host-agnostica nella **forma** (no path-assistente, no slash-command, no nome-modello — verificato); la
  scelta A vs B è essa stessa host-agnostica (sceglie in base a cosa l'host espone). I passi della
  Procedura B nominano i tool MCP **di Sertor** (`search_code`/…): sono vehicle **di Sertor** (il framework
  consumato), **non** un dettaglio del progetto *ospite* — Principio X vieta di presumere l'ospite, non di
  nominare i vehicle di Sertor. Host-agnostico nella forma e **Sertor-targeted nel contenuto** del
  retrieval (inevitabile: la capacità *localizza l'evidenza tramite il retrieval di Sertor*). Il
  dogfooding non è usato come licenza per accoppiare la forma. Generalizzazione host-facing = FEAT-002/E12.
- [x] **XI — Consumo via vehicles: PASS (allineato/rafforzato).** Nel flow B il retrieval passa **solo**
  dal vehicle **MCP** `search_code` (l'interfaccia d'integrazione per gli agenti); **zero** CLI
  `sertor-rag`, **zero** `import sertor_core`. L'adapter CLI `rag_sertor.py` **esiste** ma è **dormiente**
  nel nostro uso (garanzia strutturale: il flow B non invoca mai `SertorRagLocator.locate_*`; tripwire:
  nessun `.sertor/` in root → uso erroneo fallirebbe *loud*). È l'applicazione letterale della regola «i
  consumatori esterni si integrano via MCP» (REQ-E1). Nessuna nuova via d'accesso diretto introdotta.
- [x] **XII — Fail Loud, Fix the Cause: PASS.** Fail-loud a due punti: (a) MCP/indice giù → l'agente si
  ferma e segnala (skill, con rimedio); (b) evidenza malformata → exit **5** upstream, mai degrado
  silenzioso. Il finding «Sinthari senza LICENSE» (verificato a `5ee6fc1`) è **segnalato** (D-7), non
  sepolto. Il feedback CLI→MCP è **già stato recepito** da upstream (`5ee6fc1`) — Fix the Cause a monte.
- [x] **Allineamento alla missione: PASS (indiretto, dichiarato con onestà).** SpecLift **non** tocca il
  differenziatore diretto (fusione code+doc / motori / hit-rate): è **periferico**. Il contributo è
  **indiretto ma reale**: produce requisiti ancorati e riverificati che tengono `requirements/`/wiki/
  `CLAUDE.md` **onesti rispetto al codice reale**, rafforzando **veridicità e freschezza** del contesto che
  il RAG poi serve. In più, il self-host **consuma il contratto d'integrazione che Sertor pubblica per gli
  agenti — l'MCP** — rispettando la regola per cui i consumatori esterni non dipendono dalla CLI. Non
  gonfiato: la spec stessa lo dichiara periferico.

> **Nota di design (NON una deroga costituzionale): la deviazione dal «sandwich a un solo stadio
> intelligente» è ora una SCELTA UPSTREAM DICHIARATA.** Con l'Adapter B l'agente tocca **due** stadi di
> giudizio — localizza **E** scrive le frasi EARS — anziché uno solo. A differenza del piano precedente,
> **non è una nostra estensione**: è documentata apertamente da Sinthari in
> `contracts/evidence-locator-port.md:41-46` (vendorato). Il **moat** (verifica delle àncore sul
> **filesystem**, `anchor_fs.py`, mai via RAG) resta l'ultima rete: un'evidenza mal-localizzata che non
> regge è **esclusa**, mai accettata in silenzio — la garanzia forte è preservata per entrambi gli adapter.

**Esito pre-design: PASS 12/12 + missione PASS.** Nessuna deroga. **Complexity Tracking vuoto.**

## Project Structure

### Documentation (this feature)

```text
specs/084-speclift-self-host/
├── plan.md                          # questo file
├── research.md                      # Fase 0 — 9 decisioni (D-1..D-9), D-3 = adozione Adapter B pluggable
├── data-model.md                    # Fase 1 — entità di integrazione (E*) + entità upstream adottate (U*)
├── quickstart.md                    # Fase 1 — three-gear flow reale (changeset→located→bundle→assemble)
├── contracts/
│   ├── evidence-locator-port.md     # RIFERISCE il contratto upstream (non lo reinventa)
│   └── workspace-integration.md     # membri/uv.lock/no-ciclo/lint/pytest/CI
└── tasks.md                         # Fase 2 (/speckit-tasks — NON creato qui)
```
*(Rimosso `contracts/agent-evidence-interface.md` — l'interfaccia inventata è superata dall'adozione
dell'Adapter B upstream.)*

### Source Code (repository root)

```text
packages/speclift/                         # NUOVO membro del workspace (vendorato VERBATIM da 5ee6fc1, D-1)
├── pyproject.toml                          # DIVERGENZE DI PACKAGING: requires-python >=3.11; deps []; ruff/pytest propri
├── LICENSE                                 # MIT (convenzione workspace, D-7 — nostro)
├── VENDORING.md                            # nota di provenienza (5ee6fc1) + divergenze di packaging (E2 — nostro)
├── src/speclift/                           # VERBATIM upstream (nessun file modificato)
│   ├── config.py                           # verbatim (SERTOR_RAG_VEHICLE resta, usato solo dall'Adapter A)
│   ├── cli.py                              # verbatim (changeset / bundle --changeset/--located / assemble)
│   ├── pipeline.py                         # verbatim (build_changeset + build_bundle_from_changeset, seam pluggable)
│   ├── serialize.py                        # verbatim (changeset_to_dict / changeset_from_dict)
│   ├── observability.py                    # verbatim
│   ├── domain/{models,ports,errors,query_keys}.py  # verbatim (query_keys = G6 condivisa)
│   ├── adapters/{git_diff,rag_sertor,provided_locator,anchor_fs,authored,ears_requirements}.py  # verbatim (ENTRAMBI gli adapter)
│   ├── stages/{ingest,parse_diff,filter_sources,locate_evidence,bundle,lift,verify,render}.py    # verbatim
│   └── skills/speclift/SKILL.md            # verbatim (Procedura A/B host-agnostica; il dogfood usa B)
└── tests/{contract,integration,unit}/      # verbatim (suite completa: +provided_locator/query_keys/three_gear, +rag_sertor)

.claude/skills/speclift/SKILL.md            # copia dogfood (verbatim della skill upstream, D-9)

pyproject.toml (root)                       # members += packages/speclift; ruff extend-exclude += packages/speclift
.github/workflows/ci.yml                    # step "Tests — speclift" (+ opz. "Lint — speclift")
uv.lock                                     # rigenerato

# INVARIATI: src/sertor_core/**, src/sertor_mcp/**, packages/{sertor,sertor-install-kit,sertor-flow}/**
```

**Structure Decision.** `packages/speclift` è un membro del workspace **senza dipendenze da altri
membri**: grafo aciclico garantito (`speclift → ∅`). Il codice `src/**` è **verbatim upstream** (vendoring
puro): il dogfood usa l'**Adapter B** già presente, senza toccare dominio, stadi, config o l'Adapter A. Il
core e gli altri membri restano byte-identici.

## Fasi di lavoro (per /speckit-tasks)

1. **Vendoring verbatim (D-1).** Copia `src/speclift/**`, `tests/**`, `skills/speclift/SKILL.md` e i
   contratti (`specs/001-speclift-mvp/contracts/**`) da Sinthari **`5ee6fc1`** in `packages/speclift/`
   **senza modifiche di codice**. Crea `LICENSE` (MIT) e `VENDORING.md` (E2, commit `5ee6fc1`, divergenze
   di packaging).
2. **pyproject del pacchetto (D-2/D-4/D-5/D-6/D-8) — le UNICHE divergenze.** `requires-python >=3.11`;
   `dependencies = []`, `dev += jsonschema`; versione statica `0.1.0`; `[tool.ruff]` (110/`SIM`/`py311`);
   `[tool.pytest.ini_options]` (marker `contract`/`integration`).
3. **Integrazione workspace.** Root `pyproject.toml`: `members += packages/speclift`,
   `ruff extend-exclude += packages/speclift`. `uv sync --all-packages` → `uv.lock`.
4. **Skill dogfood (D-9).** Deposita la copia **verbatim** della skill upstream in
   `.claude/skills/speclift/SKILL.md`. Nessuna estensione (upstream ha già Procedura A/B). Verifica
   host-agnosticità (no path-assistente/slash/nome-modello) e presenza della Procedura B (tool MCP).
5. **Verifica empirica.** `uv run pytest packages/speclift/tests -m "not cloud"` verde (suite completa);
   `uv run --python 3.11 pytest …` verde (accettazione FR-019; se rosso per costrutto 3.12-only → piano B
   FR-020, dichiarazione in `VENDORING.md`). `uv run ruff check .` verde (speclift escluso).
6. **CI (D-6).** Step `Tests — speclift` nel job `test`. (Opz. `Lint — speclift`.)
7. **Non-regressione.** `git diff -- src/sertor_core pyproject.toml` sul core = solo le 2 righe di
   workspace/ruff attese; grep `import sertor_core` su `packages/speclift/src` = 0 (fuori dai commenti
   upstream); suite altri membri verdi.
8. **Verifica di dogfooding e2e (Adapter B).** `changeset → (agente: search_code) → bundle --changeset
   --located → autoring → assemble` su un commit reale con indice fresco; report riverificato; fail-loud
   su evidenza malformata (exit 5) e su MCP/indice giù (agente si ferma). Verifica che il flow non spawni
   alcun `sertor-rag`.
9. **Conferma a Sinthari (FR-017 — già chiuso).** Voce in `wiki/sources/input-other-agents/` che
   **ringrazia/conferma** l'adozione dell'Adapter B pluggable (il feedback CLI→MCP è **già** recepito da
   `5ee6fc1`) + registra il gap residuo (non è navigazione code-graph).

## Constitution Check (post-design)

Dopo la definizione degli artefatti (research/data-model/contracts/quickstart), **nessun principio è
violato e nessuna nuova complessità è introdotta**:

- I/IV/X/XI (non-negoziabili) restano **PASS**: core invariato; due adapter pluggable dietro la porta (I);
  exit-code upstream espliciti, no exit 6 nostro (IV); skill host-agnostica nella forma con confine
  dichiarato (X); retrieval del dogfood solo via MCP, zero import/CLI, Adapter A dormiente (XI,
  rafforzato).
- III **PASS (rafforzato)**: vendoring puro = zero divergenza di codice runtime; convergenza con upstream
  = ottimo per DRY/manutenzione.
- VI/XII **PASS**: stadi deterministici verbatim + moat sul filesystem + doppio fail-loud (MCP nella
  skill, evidenza malformata exit 5). La **deviazione dal sandwich** è una scelta **upstream** dichiarata,
  non una nostra deroga.
- Missione **PASS** (indiretto, non gonfiato; consuma l'MCP come contratto d'integrazione).

**Esito post-design: PASS 12/12 + missione PASS.** Nessuna deroga. **Complexity Tracking vuoto.**

## Tracciamento dello scope (rinvii promossi, non sepolti)

- **Distribuzione su ospiti esterni** (installer/packaging, config del vehicle/retrieval per un ospite,
  sync bundlato↔dogfood, guardia di sync skill, IT→EN, generalizzazione host-agnostica) → **FEAT-002**
  (backlog epica `speclift`).
- **Traduzione IT→EN** degli asset SpecLift → tema **E12**.
- **SpecAudit / Debrief / Guida al test** → **FEAT-003/004/005** (stesso backlog).
- **Convergenza upstream verso il retrieval MCP** → **già avvenuta** (`5ee6fc1`): resta una voce di
  **conferma/ringraziamento** a Sinthari (`wiki/sources/input-other-agents/`, FR-017), non un feedback di
  divergenza aperto.
- **Gap navigazione code-graph** (`find_symbol`/`who_calls`): il dogfood può usare `search_code`
  (semantico); il gap si **dichiara** (FR-016), non si chiude qui.
- **Finding LICENSE upstream assente** (a `5ee6fc1`) → segnalato in `VENDORING.md` (D-7); conferma col
  proprietario upstream raccomandata (stessa-org, proseguibile).
- **Step CI `Lint — speclift`** → opzionale, aggiungibile in tasks; non necessario per la verde del gate
  di root.

## Complexity Tracking

*Nessuna violazione da giustificare — vuoto.*

## Nota di processo

`.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** →
parametri per convenzione dal branch `084-speclift-self-host` (forma dai plan `074`–`083`). Nessun hook
SpecKit eseguito. **Git non eseguito** (delega a `configuration-manager`). MCP `sertor-rag` interrogato in
apertura (`search_code`): **nessun errore tool**. Il codice SpecLift è ancorato al clone Sinthari
**`5ee6fc1`** (`git rev-parse HEAD` verificato; `Read`/`Glob`/`Grep` sul flow reale, `cli.py`/`pipeline.py`/
`provided_locator.py`/`query_keys.py`/`evidence-locator-port.md`/`SKILL.md`/`test_three_gear_flow.py`); il
codice Sertor via MCP + `Read`.

## Brief di commit (per `configuration-manager`)

- **Messaggio:** `docs(plan): rigenera piano FEAT-001 speclift al vendoring-puro/pluggable (branch 084)`
- **Corpo (perché):** Sinthari ha recepito il feedback di dogfooding e mergiato su master (`5ee6fc1`) una
  versione **pluggable** dell'`EvidenceLocator` (Adapter B: agente + MCP). Gli artefatti di design
  (plan/research/data-model/contracts/quickstart) sono riallineati: **adozione** dell'Adapter B upstream
  (vendoring PURO, zero fork), il dogfood usa il **three-gear flow** (`changeset` → localizza via tool MCP
  → `bundle --changeset/--located` → `assemble`); `rag_sertor.py` **resta** (dormiente); interfaccia/exit
  code **upstream** (malformato→5, flag-misuse→2), **nessun** `EvidenceInputError`/exit 6 nostro;
  `sertor_core` invariato. Rimosso `contracts/agent-evidence-interface.md` (interfaccia inventata) →
  sostituito da `contracts/evidence-locator-port.md` che **riferisce** quello upstream. Constitution PASS
  12/12 + missione PASS, nessuna deroga (deviazione dal sandwich = scelta upstream dichiarata).
- **File da includere:**
  - `specs/084-speclift-self-host/plan.md`
  - `specs/084-speclift-self-host/research.md`
  - `specs/084-speclift-self-host/data-model.md`
  - `specs/084-speclift-self-host/contracts/evidence-locator-port.md`
  - `specs/084-speclift-self-host/contracts/workspace-integration.md`
  - `specs/084-speclift-self-host/quickstart.md`
  - `CLAUDE.md` (aggiornamento riferimento al piano tra i marker SpecKit)
- **File da rimuovere (git rm):** `specs/084-speclift-self-host/contracts/agent-evidence-interface.md`
  (già rimosso dal filesystem; da stage-are come cancellazione).
- **NON includere:** nessun codice vendorato (è fase implement); nessun `.env`/segreto.
- **Hook SpecKit:** non eseguire `EXECUTE_COMMAND`/hook git.
