# Implementation Plan: Self-hosting / dogfooding di SpecLift su Sertor (speclift FEAT-001)

**Branch**: `084-speclift-self-host` | **Date**: 2026-07-01 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification da `specs/084-speclift-self-host/spec.md` +
`requirements/speclift/self-host/requirements.md` + recon `wiki/sources/input-other-agents/speclift-recon.md`.

> **Rigenerato dopo il cambio di decisione del proprietario:** il self-host **non** dipende dalla CLI
> `sertor-rag`; il retrieval passa dal **server MCP** (tool `search_code`) orchestrato dall'agente dentro
> una **skill**. Il vecchio piano (vehicle CLI) è **SUPERATO**.

## Summary

Vendorare **SpecLift** (handoff Sinthari, `master @ be4da28`, MVP ~106 test) nel repo Sertor come nuovo
membro del workspace `uv` **`packages/speclift`**, per usarlo in **dogfooding** — generare requisiti EARS
ancorati e riverificati dai changeset reali di Sertor, alimentando il *lint semantico* del rituale di step
con evidenza ancorata. La feature è **additiva / vendoring**: **`sertor_core` resta byte-identico**
(Principio XI), e SpecLift consuma il retrieval di Sertor **esclusivamente** via il vehicle **MCP** (tool
`search_code`), orchestrato dall'agente nella skill — **mai** via la CLI `sertor-rag search`, **mai**
importando il core. La distribuzione su ospiti esterni è **FEAT-002**, fuori ambito.

**Approccio tecnico (dal research):**
- **Swap del solo locator (D-3):** rimuovi `adapters/rag_sertor.py` (adapter CLI), aggiungi
  `AgentEvidenceLocator` (file-reader) dietro la **stessa porta** `EvidenceLocator`; l'agente localizza via
  MCP `search_code` e consegna l'evidenza in un **artefatto JSON** (forma `Symbol`/`TestRef`, come il
  `FakeLocator`). Candidati out via `bundle --candidates-out`; evidenza in via `bundle --evidence`; nuovo
  `EvidenceInputError` (exit 6) fail-loud su evidenza malformata. Moat **invariato** (verifica sul
  filesystem). *(Contratto: `contracts/agent-evidence-interface.md`.)*
- copia one-shot pinnata a `be4da28` + `VENDORING.md` (D-1); `jsonschema` → dev, runtime `[]` (D-2);
  `requires-python` a `>=3.11` con verifica empirica, piano B se irriducibile (D-4); ruff di root **esclude**
  `packages/speclift`, speclift tiene il proprio `[tool.ruff]` (D-5); test per-pacchetto + step CI, marker
  nel pyproject di speclift (D-6); `LICENSE` MIT + provenienza che registra l'assenza upstream (stessa-org,
  D-7); versione statica `0.1.0`, escluso dal packaging distribuibile (D-8); skill dogfood **estesa** a
  orchestrare il retrieval via MCP (D-9).

## Technical Context

**Language/Version**: Python `>=3.11` (riconciliato da `>=3.12`, D-4). CI su 3.12 (`ci.yml:33-37`).

**Primary Dependencies**: runtime **nessuna** (stdlib-only + subprocess `git`); dev: `pytest>=8`,
`ruff>=0.6`, `jsonschema>=4` (test di contratto). **Nessuna** dipendenza da altri membri del workspace,
**nessun** SDK MCP importato (l'MCP è consumato dall'**agente** nella skill, non dal codice SpecLift).

**Storage**: N/A. SpecLift legge il filesystem (git diff, verifica àncore) e riceve l'evidenza da un
artefatto JSON prodotto dall'agente; non scrive stato persistente proprio. Non tocca il RAG.

**Testing**: `pytest` (~28 file; suite netta = upstream −`test_rag_sertor` +`test_agent_evidence`); marker
`contract`/`integration`; integration offline (git-fixture locale).

**Target Platform**: Windows + Linux (matrice CI), offline-capable (nessuna rete richiesta dai test — il
retrieval MCP è nell'agente, non nel codice testato).

**Project Type**: pacchetto CLI vendorato = nuovo membro del monorepo `uv` (dominio puro ports&adapters,
hatchling). Non un servizio, non una libreria del core.

**Performance Goals**: N/A (strumento su richiesta, determinismo prioritario).

**Constraints**: `sertor_core` invariato (Principio XI); zero ciclo di dipendenze; retrieval **solo** via
MCP `search_code` (skill), **zero** CLI `sertor-rag`, **zero** import `sertor_core`; fail-loud su MCP/indice
(skill) e su evidenza malformata (exit 6); skill host-agnostica nella forma; suite verde nel workspace.

**Scale/Scope**: 1 nuovo membro workspace; ~25 file sorgente vendorati; **swap del locator** = 1 file
rimosso (`rag_sertor.py`) + 1 aggiunto (`agent_evidence.py`) + 5 file toccati (`pipeline.py`, `cli.py`,
`config.py`, `serialize.py`, `domain/errors.py`) + skill estesa + test (−`test_rag_sertor`, +`test_agent_evidence`);
~5 punti d'integrazione workspace (root `pyproject.toml` × 2, `ci.yml`, pyproject del pacchetto,
`.claude/skills/`). Divergenze vendorate tracciate in `VENDORING.md`.

## Constitution Check

*GATE — v1.4.0. PASS/FAIL per principio; ogni FAIL va risolto o giustificato in Complexity Tracking.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE): PASS.** `sertor_core` invariato; SpecLift ha il
  proprio dominio puro ports&adapters. Lo **swap del locator** è precisamente Dependency Rule + Plugin: si
  sostituisce un adapter concreto (`SertorRagLocator`→`AgentEvidenceLocator`) dietro la porta
  `EvidenceLocator`, senza toccare dominio/stadi (`locate_evidence.py` invariato). Zero SDK nel dominio.
- [x] **II — Boundary & local-first: PASS.** SpecLift resta interamente locale (git + filesystem + lettura
  di un file di evidenza). Il retrieval MCP vive **fuori** dal codice SpecLift (nell'agente). N/A per vector
  store proprio.
- [x] **III — YAGNI & unità piccole: PASS.** Lo swap è la modifica **minima** che realizza «retrieval via
  MCP nella skill»: si rimpiazza il **solo** adapter di localizzazione. Il flag `--candidates-out` +
  l'`AgentEvidenceLocator` + `EvidenceInputError` sono ciascuno **necessari** al design (candidati out,
  evidenza in, fail-loud). Le generalizzazioni (env-var vehicle, sync, distribuzione, config-all'install)
  sono rinviate a FEAT-002. *(Nota onesta: il design MCP tocca più file vendorati del vecchio design CLI —
  che patchava una costante — ma è il prezzo della decisione del proprietario, non complessità speculativa.)*
- [x] **IV — Errori espliciti (NON-NEGOZIABILE): PASS.** Nuovo `EvidenceInputError` (exit 6) su evidenza
  assente/malformata: niente `None` silenzioso, niente evidenza vuota/di default, niente àncora fabbricata.
  Il fail-loud MCP/indice vive nella skill (l'agente si ferma). Fedele alla policy errori upstream.
- [x] **V — Testabilità & misure: PASS.** Suite F.I.R.S.T. integrata e verde nel workspace (CS-4); il nuovo
  `AgentEvidenceLocator` è testato in isolamento (fed da file valido/assente/malformato) e riusa i test di
  `locate_evidence` (stessa forma del `FakeLocator`). hit@k/MRR **N/A** (SpecLift non è un motore di
  retrieval — la misura pertinente è la suite verde + il moat deterministico).
- [x] **VI — Idempotenza & non-distruttività: PASS.** Stadi deterministici invariati; il vendoring non avvia
  indicizzazione (install≠run); nessuna sovrascrittura di file utente; `assemble` rilegge input e riverifica
  sul filesystem. *(Deviazione dal sandwich: l'agente tocca 2 stadi — vedi nota sotto, non è una deroga.)*
- [x] **VII — Leggibilità: PASS.** Vocabolario di dominio preservato (ingest/parse/locate/lift/verify/render);
  il nuovo adapter e il flag hanno nomi rivelatori (`AgentEvidenceLocator`, `--candidates-out`, `--evidence`).
- [x] **VIII — Configurabilità centralizzata: PASS.** Nessun default hardcodato nel corpo: rimosso il vehicle
  morto da `config.py`; il percorso dell'evidenza è un argomento CLI esplicito, non una costante sparsa.
- [x] **IX — Osservabilità: PASS (N/A per il core).** SpecLift ha la sua `observability.py` (stage_event);
  la feature non introduce operazioni nel core Sertor da loggare. Nessun segreto nei log.
- [x] **X — Host-agnostico (NON-NEGOZIABILE): PASS (con confine dichiarato).** La skill resta host-agnostica
  nella **forma** (no path-assistente, no slash-command, no nome-modello). I nuovi passi nominano il tool MCP
  **`search_code`**: è un vehicle **di Sertor** (il framework consumato), **non** un dettaglio del progetto
  *ospite* — Principio X vieta di presumere l'ospite, non di nominare i vehicle di Sertor. Il corpo è dunque
  host-agnostico nella forma e **Sertor-targeted nel contenuto del retrieval** (inevitabile: la capacità
  *localizza l'evidenza tramite il retrieval di Sertor*). Il dogfooding non è usato come licenza per accoppiare
  la forma. Generalizzazione host-facing (installer/IT→EN) = FEAT-002/E12. *(Tensione dichiarata con onestà,
  research D-9.)*
- [x] **XI — Consumo via vehicles: PASS (allineato/rafforzato).** Retrieval **solo** via il vehicle **MCP**
  `search_code` (l'interfaccia d'integrazione per gli agenti); **zero** CLI `sertor-rag`, **zero**
  `import sertor_core` (l'adapter CLI `rag_sertor.py` è **rimosso**; grep negativo sul core verificato). È
  l'applicazione letterale della regola «i consumatori esterni si integrano via MCP» (REQ-E1). Nessuna nuova
  via d'accesso diretto introdotta.
- [x] **XII — Fail Loud, Fix the Cause: PASS.** Due punti fail-loud: (a) MCP/indice giù → l'agente si ferma e
  segnala (skill, con rimedio); (b) evidenza malformata → `EvidenceInputError` exit 6, mai degrado silenzioso.
  Il finding «Sinthari senza LICENSE» è **segnalato** (D-7), non sepolto. La divergenza dal codice vendorato è
  **dichiarata** e rimandata a Sinthari (FR-016/017), non nascosta.
- [x] **Allineamento alla missione: PASS (indiretto, dichiarato con onestà).** SpecLift **non** tocca il
  differenziatore diretto (fusione code+doc / motori / hit-rate): è **periferico**. Il contributo è
  **indiretto ma reale**: produce requisiti ancorati e riverificati che tengono `requirements/`/wiki/
  `CLAUDE.md` **onesti rispetto al codice reale**, rafforzando **veridicità e freschezza** del contesto che il
  RAG poi serve. In più, il self-host **consuma il contratto d'integrazione che Sertor pubblica per gli agenti
  — l'MCP** — rispettando la regola per cui i consumatori esterni non dipendono dalla CLI. Non gonfiato: la
  spec stessa lo dichiara periferico.

> **Nota di design (NON una deroga costituzionale): deviazione dal «sandwich a un solo stadio intelligente».**
> Spostando la localizzazione dall'adapter deterministico all'agente (che la ottiene via MCP `search_code`),
> l'agente ora tocca **due** stadi di giudizio — localizza **E** scrive le frasi EARS — anziché uno solo. È
> una scelta **consapevole e dichiarata**, comunicata a Sinthari come feedback (FR-017). Il **moat** (verifica
> delle àncore sul **filesystem**, `anchor_fs.py`, mai via RAG) resta l'ultima rete: un'evidenza
> mal-localizzata che non regge è **esclusa**, mai accettata in silenzio — la garanzia forte è preservata.

**Esito pre-design: PASS 12/12 + missione PASS.** Nessuna deroga. **Complexity Tracking vuoto.**

## Project Structure

### Documentation (this feature)

```text
specs/084-speclift-self-host/
├── plan.md                          # questo file
├── research.md                      # Fase 0 — 9 decisioni (D-1..D-9), D-3 = swap del locator/MCP
├── data-model.md                    # Fase 1 — entità di integrazione E1..E8
├── quickstart.md                    # Fase 1 — ciclo candidati→localizza(MCP)→bundle→autoring→assemble
├── contracts/
│   ├── agent-evidence-interface.md  # NUOVO — candidati out + evidenza in (agente↔SpecLift)
│   └── workspace-integration.md     # membri/uv.lock/no-ciclo/lint/pytest/CI
└── tasks.md                         # Fase 2 (/speckit-tasks — NON creato qui)
```
*(Rimosso `contracts/rag-vehicle-contract.md` — il vehicle CLI non esiste più nel self-host.)*

### Source Code (repository root)

```text
packages/speclift/                         # NUOVO membro del workspace (vendorato, D-1)
├── pyproject.toml                          # requires-python >=3.11; deps runtime []; [tool.ruff]/[pytest] propri
├── LICENSE                                 # MIT (convenzione workspace, D-7)
├── VENDORING.md                            # nota di provenienza + divergenze (E2)
├── src/speclift/
│   ├── config.py                           # DIVERGENZA: rimosso SERTOR_RAG_VEHICLE/sertor_rag_vehicle (morto)
│   ├── cli.py                              # DIVERGENZA: bundle += --candidates-out / --evidence (D-3)
│   ├── pipeline.py                         # DIVERGENZA: default_components → AgentEvidenceLocator; + emit_candidates()
│   ├── serialize.py                        # DIVERGENZA: + changeset_to_candidates_dict / agent_evidence_from_dict
│   ├── observability.py
│   ├── domain/{models,ports,errors}.py     # errors.py DIVERGENZA: + EvidenceInputError (exit 6); models/ports invariati
│   ├── adapters/{git_diff,anchor_fs,authored,ears_requirements}.py   # rag_sertor.py RIMOSSO (D-3)
│   │   └── agent_evidence.py               # NUOVO — AgentEvidenceLocator (file-reader, alimentato)
│   ├── stages/{ingest,parse_diff,filter_sources,locate_evidence,bundle,lift,verify,render}.py  # INVARIATI
│   └── skills/speclift/SKILL.md            # sorgente vendorato, ESTESO (orchestrazione MCP, D-9)
└── tests/{contract,integration,unit}/      # −test_rag_sertor.py, +test_agent_evidence.py; marker contract/integration

.claude/skills/speclift/SKILL.md            # copia dogfood (deposito + estensione MCP, D-9)

pyproject.toml (root)                       # members += packages/speclift; ruff extend-exclude += packages/speclift
.github/workflows/ci.yml                    # step "Tests — speclift" (+ opz. "Lint — speclift")
uv.lock                                     # rigenerato

# INVARIATI: src/sertor_core/**, src/sertor_mcp/**, packages/{sertor,sertor-install-kit,sertor-flow}/**
```

**Structure Decision.** `packages/speclift` è un membro del workspace **senza dipendenze da altri membri**:
grafo aciclico garantito (`speclift → ∅`). La modifica sostanziale è lo **swap del locator** (adapter dietro
la porta `EvidenceLocator`), che tocca solo il composition root (`default_components`) e la superficie CLI,
lasciando dominio e stadi invariati. Il core e gli altri membri restano byte-identici.

## Fasi di lavoro (per /speckit-tasks)

1. **Vendoring (D-1).** Copia `src/speclift/**`, `tests/**`, `skills/speclift/SKILL.md` da Sinthari
   `be4da28` in `packages/speclift/`. Crea `LICENSE` (MIT) e `VENDORING.md` (E2).
2. **pyproject del pacchetto (D-2/D-4/D-5/D-6/D-8).** `requires-python >=3.11`; `dependencies = []`,
   `dev += jsonschema`; versione statica `0.1.0`; `[tool.ruff]` (110/`SIM`/`py311`);
   `[tool.pytest.ini_options]` (marker `contract`/`integration`).
3. **Swap del locator (D-3) — il cuore.**
   a. **Rimuovi** `adapters/rag_sertor.py` e `tests/unit/test_rag_sertor.py`; togli
      `SERTOR_RAG_VEHICLE`/`sertor_rag_vehicle` da `config.py`.
   b. **Aggiungi** `adapters/agent_evidence.py::AgentEvidenceLocator` (legge l'artefatto JSON, forma
      `Symbol`/`TestRef`, contratto `agent-evidence-interface.md`; valida all'ingresso → `EvidenceInputError`).
   c. **`domain/errors.py`**: `EvidenceInputError(SpecLiftError)`, `exit_code = 6`.
   d. **`pipeline.py`**: `default_components` costruisce `AgentEvidenceLocator` (non `SertorRagLocator`);
      aggiungi `emit_candidates(options, diff_source, config)` (ingest→parse→filter, no locator).
   e. **`serialize.py`**: `changeset_to_candidates_dict(changeset, excluded)` (localization request) +
      `agent_evidence_from_dict(payload)` (riusa `_symbol_from`/`_test_from`).
   f. **`cli.py`**: `speclift bundle` += `--candidates-out` (emette candidati, no locator) e `--evidence`
      (inietta `AgentEvidenceLocator`); `bundle` senza flag → fail-loud usage; mappa `EvidenceInputError`→6.
   g. **Test nuovo** `tests/unit/test_agent_evidence.py` (fed da file valido/assente/malformato; contratto
      con `locate_evidence`). Verifica che `test_locate_evidence.py` (8 test) resti verde con l'adapter reale.
4. **Skill dogfood estesa (D-9).** Estendi `skills/speclift/SKILL.md`: passi «candidati → localizza via MCP
   `search_code` → scrivi evidenza → `bundle --evidence`» **prima** dei passi autoring→assemble; fail-loud su
   MCP/indice; resta host-agnostica nella forma. Deposita la copia in `.claude/skills/speclift/SKILL.md`.
5. **Integrazione workspace.** Root `pyproject.toml`: `members += packages/speclift`,
   `ruff extend-exclude += packages/speclift`. `uv sync --all-packages` → `uv.lock`.
6. **Verifica empirica.** `uv run pytest packages/speclift/tests -m "not cloud"` verde;
   `uv run --python 3.11 pytest …` verde (accettazione FR-019; se rosso per costrutto 3.12-only → piano B
   FR-020, dichiarazione). `uv run ruff check .` verde (speclift escluso).
7. **CI (D-6).** Step `Tests — speclift` nel job `test`. (Opz. `Lint — speclift`.)
8. **Non-regressione.** `git diff -- src/sertor_core pyproject.toml` sul core = solo le 2 righe di
   workspace/ruff attese; grep `import sertor_core` su `packages/speclift/src` = 0; grep `sertor-rag`/
   `rag_sertor` sul path di localizzazione = 0; suite altri membri verdi.
9. **Verifica di dogfooding e2e.** `candidati → (agente: search_code) → bundle --evidence → autoring →
   assemble` su un commit reale con indice fresco; report riverificato; fail-loud su evidenza malformata
   (exit 6) e su MCP/indice giù (agente si ferma).
10. **Feedback a Sinthari (FR-017).** Voce in `wiki/sources/input-other-agents/` che dichiara la divergenza
    CLI→MCP + il gap residuo (non è navigazione code-graph).

## Constitution Check (post-design)

Dopo la definizione degli artefatti (research/data-model/contracts/quickstart), **nessun principio è violato
e nessuna nuova complessità è introdotta**:

- I/IV/X/XI (non-negoziabili) restano **PASS**: core invariato; swap dell'adapter dietro la porta (I);
  `EvidenceInputError` esplicito (IV); skill host-agnostica nella forma con confine dichiarato (X); retrieval
  solo via MCP, zero import/CLI (XI, rafforzato).
- III **PASS**: swap minimale; le generalizzazioni rinviate a FEAT-002 — nessuna astrazione speculativa.
- VI/XII **PASS**: stadi deterministici + moat sul filesystem + doppio fail-loud (MCP nella skill, evidenza
  nel codice). La **deviazione dal sandwich** è una nota di design dichiarata, non una deroga.
- Missione **PASS** (indiretto, non gonfiato; consuma l'MCP come contratto d'integrazione).

**Esito post-design: PASS 12/12 + missione PASS.** Nessuna deroga. **Complexity Tracking vuoto.**

## Tracciamento dello scope (rinvii promossi, non sepolti)

- **Distribuzione su ospiti esterni** (installer/packaging, config del vehicle/retrieval per un ospite,
  sync bundlato↔dogfood, guardia di sync skill, IT→EN, generalizzazione host-agnostica) → **FEAT-002**
  (backlog epica `speclift`).
- **Traduzione IT→EN** degli asset SpecLift → tema **E12**.
- **SpecAudit / Debrief / Guida al test** → **FEAT-003/004/005** (stesso backlog).
- **Convergenza upstream verso il retrieval MCP** → **feedback registrato a Sinthari**
  (`wiki/sources/input-other-agents/`, FR-017), non un debito interno.
- **Gap navigazione code-graph** (`find_symbol`/`who_calls`): il self-host usa `search_code` (semantico);
  il gap si **dichiara** (FR-016), non si chiude qui.
- **Finding LICENSE upstream assente** → segnalato in `VENDORING.md` (D-7); conferma col proprietario
  upstream raccomandata (stessa-org, proseguibile).
- **Step CI `Lint — speclift`** → opzionale, aggiungibile in tasks; non necessario per la verde del gate di
  root.

## Complexity Tracking

*Nessuna violazione da giustificare — vuoto.*

## Nota di processo

`.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** →
parametri per convenzione dal branch `084-speclift-self-host` (forma dai plan `074`–`083`). Nessun hook
SpecKit eseguito. **Git non eseguito** (delega a `configuration-manager`). MCP `sertor-rag` interrogato
(`search_code` sull'output/shape degli hit): **nessun errore tool**. Il codice SpecLift è ancorato al clone
Sinthari `be4da28` (`Read`/`Glob`/`Grep`); il codice Sertor via MCP + `Read`.

## Brief di commit (per `configuration-manager`)

- **Messaggio:** `docs(plan): rigenera piano FEAT-001 speclift al design MCP-skill (branch 084)`
- **Corpo (perché):** allinea gli artefatti di design (plan/research/data-model/contracts/quickstart) al
  cambio di decisione: retrieval via il server MCP (tool `search_code`) dentro una skill, **non** via la CLI
  `sertor-rag`; swap del solo locator (`rag_sertor.py` rimosso, `AgentEvidenceLocator` aggiunto);
  `sertor_core` invariato. Sostituito `contracts/rag-vehicle-contract.md` con
  `contracts/agent-evidence-interface.md`. Constitution PASS 12/12 + missione PASS, nessuna deroga (deviazione
  dal sandwich dichiarata come nota di design).
- **File da includere:**
  - `specs/084-speclift-self-host/plan.md`
  - `specs/084-speclift-self-host/research.md`
  - `specs/084-speclift-self-host/data-model.md`
  - `specs/084-speclift-self-host/contracts/agent-evidence-interface.md`
  - `specs/084-speclift-self-host/contracts/workspace-integration.md`
  - `specs/084-speclift-self-host/quickstart.md`
  - `CLAUDE.md` (aggiornamento riferimento al piano tra i marker SpecKit)
- **File da rimuovere (git rm):** `specs/084-speclift-self-host/contracts/rag-vehicle-contract.md`
- **NON includere:** nessun codice vendorato (è fase implement); nessun `.env`/segreto.
- **Hook SpecKit:** non eseguire `EXECUTE_COMMAND`/hook git.
