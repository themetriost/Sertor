# Requisiti — Installer di governance/SDLC (`sertor-flow`)
<!-- Deriva da: FEAT-005 (epica sertor-cli) — riconcepita come pacchetto separato -->

## 1. Contesto e problema (perché)

Le capacità di **metodo di sviluppo (SDLC)** di Sertor — il flusso SpecKit
(`specify → clarify → plan → tasks → analyze → implement`), la gestione dei requisiti a due livelli
(epica/feature), la delega delle operazioni git, la **costituzione** che fa da gate di qualità, e il
**rituale di step / Definition of Done** — oggi vivono **solo** nel `.claude/` e `.specify/` di Sertor.
Non sono replicabili su un altro repository: un ospite che volesse lavorare con lo stesso metodo deve
ricostruirlo a mano.

L'epica `sertor-cli` (FEAT-005) prevedeva un sotto-comando `sertor install governance`. In sede di
discussione (2026-06-15) si è deciso di **riconcepirlo come pacchetto installabile separato**,
chiamato **`sertor-flow`**, per tre motivi:

1. **Dominio ortogonale al RAG.** `install wiki`/`install rag` veicolano capacità del **retrieval
   core** (scaffold `.env`/`.mcp.json`, bootstrap dipendenze di `sertor-core`). La governance è
   *metodo di lavoro*: non tocca embeddings, vector store, corpus. Sta sotto lo stesso ombrello solo
   per inerzia.
2. **Pulizia delle dipendenze.** Un ospite che vuole solo il flusso SDLC non deve tirarsi dietro
   `sertor-core` (con i suoi extra di retrieval). Oggi il pacchetto `sertor` **dipende** da
   `sertor-core` (`packages/sertor/pyproject.toml:9`); `sertor-flow` non deve.
3. **Backlog pregresso.** Esiste già la nota di voler riesportare il rituale/governance in un
   artefatto **portabile** (memoria di progetto: «riesportare in plugin portabile … ridecidere il
   nome»). `sertor-flow` realizza quella intenzione.

> **Confine netto col wiki.** Il sistema-wiki (skill `wiki-author`, agente `wiki-curator`, comando
> `/wiki`, playbook, hook wiki) è già coperto da `sertor install wiki` e **resta fuori** da
> `sertor-flow`. Vedi §4 e DA-b (coordinamento del blocco `CLAUDE.md`).

## 2. Obiettivi e criteri di successo

Obiettivo: portare l'apparato SDLC di Sertor su **qualunque repository ospite** con un comando, in
modo **non distruttivo**, **idempotente**, **install ≠ run** e **host-agnostico** (Principio X),
**senza** dipendere dal retrieval core.

Criteri di successo (misurabili, tech-agnostici):
- **CS-1 (installabilità separata):** un utente installa `sertor-flow` con un singolo comando
  `uv`/`pip` e ottiene un console-script dedicato, **senza** che `sertor-core` o il pacchetto `sertor`
  siano presenti.
- **CS-2 (install ≠ run):** in **0** casi l'installazione avvia una fase SDLC o un'operazione git;
  serve sempre un'invocazione esplicita successiva.
- **CS-3 (completezza del bundle):** dopo l'install, sul repo ospite sono presenti e invocabili **tutte**
  le superfici dichiarate in §4 (skill SpecKit + git, skill requisiti, agente requirements-analyst,
  agente configuration-manager, template `.specify/`, artefatto costituzione, blocco rituale in CLAUDE.md).
- **CS-4 (non distruttività & idempotenza):** lo stesso comando completa sia su **repo nuovo** sia su
  **repo esistente** (≥2 scenari) senza sovrascrivere file dell'utente; una **seconda** esecuzione non
  produce modifiche sugli artefatti già presenti.
- **CS-5 (indipendenza dal core):** in un ambiente in cui `sertor-core` **non è installato**,
  l'install di `sertor-flow` riesce comunque (verificabile: nessun import/risoluzione di `sertor-core`).
- **CS-6 (host-agnostico):** l'install completa su ≥2 ospiti diversi senza modifiche al corpo; gli
  asset host-facing sono in **inglese**, coerenti con l'installer esistente.

## 3. Stakeholder e attori

- **Owner/maintainer (tu):** porta il metodo SDLC su altri repository.
- **Team interno (futuro):** adotta lo stesso flusso di lavoro su più progetti.
- **Assistente LLM ospite (Claude Code & altri):** consumatore delle superfici agentiche installate
  (skill, agenti, blocco rituale).
- **Repository target:** progetto nuovo o esistente su cui `sertor-flow` opera.
- **Epica `sertor-cli` (a monte):** definisce i vincoli trasversali dell'installer (REQ-E1..E7).
- **Pacchetto `sertor` (parente):** ombrello wiki/rag; relazione di alias da decidere (DA-f).

## 4. Ambito

### In ambito — cosa il bundle distribuisce
- **Skill SpecKit di fase:** `speckit-specify`, `speckit-clarify`, `speckit-plan`, `speckit-tasks`,
  `speckit-analyze`, `speckit-checklist`, `speckit-implement`, `speckit-constitution`,
  `speckit-taskstoissues`.
- **Skill SpecKit git:** `speckit-git-feature`, `speckit-git-validate`, `speckit-git-remote`,
  `speckit-git-initialize`, `speckit-git-commit`.
- **Agenti SpecKit** corrispondenti alle fasi (specify/clarify/plan/tasks/analyze/checklist/implement/
  constitution/taskstoissues).
- **Skill `requirements`** (gestione requisiti a due livelli epica/feature) + agente
  **`requirements-analyst`**.
- **Agente `configuration-manager`** (delega delle operazioni git).
- **Template SpecKit** sotto l'area `.specify/templates/` dell'ospite.
- **Artefatto costituzione** sotto `.specify/memory/` (forma da decidere — DA-a).
- **Blocco «step ritual / Definition of Done»** nel `CLAUDE.md` dell'ospite (porzione SDLC del
  `claude-md-block`, in inglese; coordinamento con la porzione wiki = DA-b).
- **Report dell'installazione** (per-artefatto: created/skipped/merged/block/error), con opzione JSON.

### Fuori ambito
- **Sistema-wiki** (wiki-author/wiki-curator/`/wiki`/playbook/hook wiki): coperto da
  `sertor install wiki`.
- **Capacità RAG** (motori, `sertor-rag`, MCP): coperte da `sertor install rag` / `sertor-core`.
- **Reviewer «clean code» attivo** (agente/skill che applica il Principio VII oltre al Constitution
  Check): **non esiste ancora** → capacità futura tracciata (vedi §10 / roadmap), non in questo taglio.
- **Ciclo di vita dell'installer** (`upgrade`/`uninstall`): è FEAT-008 dell'epica `sertor-cli`.
- **Esecuzione** delle fasi SDLC (è ciò che le skill/agenti fanno *dopo* l'install) e **wizard di
  configurazione interattivo** (FEAT-003).
- **Pubblicazione su PyPI** (FEAT-006, Won't per ora): la distribuzione interim è `git+url`.
- **Definizione del *come*** (estrazione del toolkit condiviso, struttura del codice, formato asset):
  materia della fase di **design**. Qui si pone il *vincolo* (REQ-019/020), non la soluzione.

## 5. Requisiti funzionali (EARS)

### Packaging e punto d'ingresso
- **REQ-001 (Ubiquitous):** *The system shall be distributable as a standalone installable package
  named `sertor-flow`, separate from the `sertor` (wiki/rag) package.*
- **REQ-002 (Ubiquitous):** *The system shall expose its own dedicated console-script entry point,
  rather than being a subcommand of `sertor`.*
- **REQ-003 (Unwanted):** *If `sertor-core` is not installed in the environment, then the system shall
  still complete a governance install without error.*

### Install ≠ run e selezione del target
- **REQ-004 (Event-driven):** *When the user runs the install command against a target repository, the
  system shall deploy the governance asset bundle without executing any SDLC phase, git operation, or
  indexing.*
- **REQ-005 (Optional):** *Where the user does not specify a target, the system shall operate on the
  current working directory as the target repository.*
- **REQ-006 (Event-driven):** *When the install command runs, the system shall derive the set of
  artifacts from the bundle composition (not from a hard-coded count), so that adding or removing a
  bundled asset changes the plan automatically.*

### Composizione del bundle
- **REQ-007 (Ubiquitous):** *The system shall deploy the SpecKit phase skills and their corresponding
  agents (specify, clarify, plan, tasks, analyze, checklist, implement, constitution, taskstoissues).*
- **REQ-008 (Ubiquitous):** *The system shall deploy the SpecKit git skills (feature, validate, remote,
  initialize, commit).*
- **REQ-009 (Ubiquitous):** *The system shall deploy the requirements-management skill and the
  requirements-analyst agent.*
- **REQ-010 (Ubiquitous):** *The system shall deploy the configuration-manager agent.*
- **REQ-011 (Ubiquitous):** *The system shall deploy the SpecKit templates into the host's `.specify/`
  area.*
- **REQ-012 (Ubiquitous):** *The system shall provide a neutral, host-agnostic starter-constitution
  artifact under the host's `.specify/memory/` area, containing only the general engineering principles
  (not Sertor's RAG-specific ones), which the host then personalises via the `speckit-constitution`
  skill.* (DA-a risolta — composizione dello starter sotto.)
- **REQ-013 (Event-driven):** *When the install runs, the system shall add a marker-delimited
  step-ritual / Definition-of-Done block to the host `CLAUDE.md`.*

### Non distruttività, merge additivo, idempotenza
- **REQ-014 (Unwanted):** *If a target file already exists, then the system shall not overwrite it; it
  shall report the artifact as skipped.*
- **REQ-015 (Event-driven):** *When the host `CLAUDE.md` already contains the governance marker block,
  the system shall not duplicate it.*
- **REQ-016 (Unwanted):** *If a structured file is merged (e.g. JSON settings fragments), then the
  system shall merge additively and shall not remove or overwrite the user's existing entries.*
- **REQ-017 (Event-driven):** *When the install command is re-run against the same target, the system
  shall report no changes for artifacts already present (idempotency).*

### Reporting ed errori
- **REQ-018 (Ubiquitous):** *The system shall produce an install report listing each artifact and its
  per-artifact outcome (created, skipped, merged, block, or error).*
- **REQ-019 (Unwanted):** *If an artifact step fails, then the system shall stop fail-fast, leave
  already-written artifacts in place, and identify the failed step.*
- **REQ-020 (Optional):** *Where the user requests machine-readable output, the system shall emit the
  install report as JSON.*

### Vincoli trasversali (eredita epica `sertor-cli`)
- **REQ-021 (Unwanted):** *If a configuration value were a secret, then the system shall not persist it
  in a version-controlled file* (allineamento a REQ-E5; la governance di norma non ha segreti).
- **REQ-022 (Ubiquitous):** *The host-facing assets shall be authored in English (host-agnostic),
  consistent with the existing installer assets.*

### Alias dall'ombrello (opzionale)
- **REQ-023 (Event-driven):** *When the user runs `sertor install governance` on the umbrella package,
  the system shall report that governance is now provided by the separate `sertor-flow` package and how
  to install it, without the `sertor` package depending on `sertor-flow` (pointer, not delegation —
  DA-f).*

### Attribuzione di terze parti (vendoring)
- **REQ-025 (Ubiquitous):** *The system shall bundle the third-party SpecKit assets at a pinned version
  and shall include their MIT license text and copyright notice in the distributed package and on the
  host.*

### Selettività del bundle (opzionale, Could)
- **REQ-024 (Optional):** *Where the user requests a subset of the governance bundle (e.g. SpecKit
  only, requirements only, git-agent only), the system shall install only the selected subset.*
  (Default: bundle completo — DA-d.)

## 6. Requisiti non funzionali

- **NFR-1 (Isolamento dipendenze):** `sertor-flow` non deve richiedere `sertor-core` né alcun SDK di
  retrieval (embeddings, vector store) per installarsi o funzionare.
- **NFR-2 (Riuso del motore, no duplicazione):** la logica di installazione non distruttiva
  (enumerazione artefatti, strategie di scrittura, esecuzione fail-fast, report) **non deve essere
  duplicata** rispetto a quella già esistente in `sertor_installer`: va condivisa via un toolkit comune
  (il *come* è design — vedi DA-e/§7).
- **NFR-3 (Offline):** l'install non deve richiedere rete (gli asset viaggiano col pacchetto).
- **NFR-4 (Cross-platform):** l'install deve funzionare su Windows e su POSIX (coerente con l'attuale
  installer); eventuali asset eseguibili (hook) devono dichiarare la loro dipendenza dalla shell ospite.
- **NFR-5 (Canonicità asset & anti-drift):** gli asset impacchettati sono la **fonte canonica**; la
  copia in sviluppo (`.claude/` + `.specify/` di Sertor) è derivata e va mantenuta allineata con una
  guardia che fallisce in caso di deriva (come `tests/unit/test_assets_sync.py` per il wiki).
- **NFR-6 (Osservabilità leggera):** l'install deve poter emettere un resoconto leggibile e una forma
  JSON (REQ-020) per scripting; nessuna telemetria di rete.

## 7. Vincoli, assunzioni e dipendenze

**Vincoli**
- Python ≥ 3.11; distribuzione interim **`git+url`** (PyPI rinviato, FEAT-006).
- Install ≠ run (REQ-E2 dell'epica); non distruttività su repo esistente (REQ-E6); segreti mai
  versionati (REQ-E5).
- Host-agnostico (Principio X): nessuna assunzione su percorsi/strumenti dell'ospite nel corpo; le
  parti host-specifiche (es. quale assistente legge le skill) restano dietro asset/config.

**Assunzioni**
- Il motore di installazione esistente (`Artifact`/`ArtifactKind`/`WriteStrategy`/`Outcome`,
  `execute_plan` fail-fast, merge additivi `settings_merge`/`env_merge`/`mcp_merge`, blocco a marker in
  `claude_md`, `InstallReport`, sync con guard test) è **estraibile** in un toolkit condiviso senza
  dipendenza da `sertor-core` (oggi importa solo `ConfigError`/`SertorError`/`log_event`, sostituibili
  o spostabili).
- Le skill/agenti SpecKit e la skill `requirements` sono **asset di testo** (markdown/template),
  deployabili con la strategia `CREATE_IF_ABSENT` già usata per gli asset wiki.

**Dipendenze**
- Epica `sertor-cli` (vincoli trasversali, DA-8 split installer/esecuzione).
- Costituzione e template SpecKit attualmente in `.specify/` di Sertor (da promuovere ad asset
  canonici — DA-c/DA-e).
- Coordinamento col `claude-md-block` di `sertor install wiki` (DA-b).

## 8. Rischi

- **R-1 — Blocco `CLAUDE.md` condiviso col wiki:** oggi `claude-md-block.md` è un asset **del wiki** e
  contiene il rituale **accoppiato a wiki/RAG** (record, distill, re-index, dogfooding). Se `sertor-flow`
  scrive un blocco rituale e poi si installa anche il wiki (o viceversa), si rischia **doppio blocco o
  conflitto**. Mitigazione: scomporre il rituale in una parte SDLC-pura e una parte wiki, oppure un
  unico blocco con sezioni componibili (decisione: DA-b).
- **R-2 — Costituzione Sertor-specifica:** la costituzione di Sertor codifica principi *suoi* (thin
  consumer, host-agnostico, ecc.) non necessariamente validi per un ospite arbitrario. Imporla
  verbatim sarebbe errato. Mitigazione: starter neutro o innesco del flusso `speckit-constitution`
  (DA-a).
- **R-3 — Provenienza degli asset SpecKit:** parte delle skill/agenti `speckit-*` e dei contenuti
  `.specify/` potrebbe derivare dal framework di terze parti **spec-kit** (la git status li mostra come
  *untracked*). Redistribuirli ha implicazioni di **licenza/manutenzione**. Mitigazione: chiarire cosa è
  Sertor-authored vs vendored (DA-c) prima di impacchettare.
- **R-4 — Sottoinsieme canonico di `.specify/`:** `.specify/` contiene anche `scripts/`, `workflows/`,
  `extensions/`, `integrations/` che la policy di versionamento del workspace considera **scaffolding
  locale** (memoria: «versionare solo costituzione + artefatti prodotti»). Impacchettare tutto sarebbe
  errato. Mitigazione: definire il **sottoinsieme distribuibile** (DA-e).
- **R-5 — Disallineamento col repo Sertor (drift):** se gli asset canonici e il `.claude/`/`.specify/`
  di Sertor divergono, l'ospite riceve una versione diversa da quella in uso. Mitigazione: NFR-5 (guard
  test anti-drift), come per il wiki.
- **R-6 — Frammentazione pacchetti:** più pacchetti (`sertor`, `sertor-flow`, toolkit) aumentano la
  superficie di manutenzione e confondono la storia d'installazione. Mitigazione: alias REQ-023 e
  documentazione chiara.

## 9. Prioritizzazione (MoSCoW)

**Must**
- REQ-001, REQ-002, REQ-003 (pacchetto separato, entry-point proprio, indipendenza da core).
- REQ-004 (install ≠ run), REQ-005, REQ-006 (piano derivato dal bundle).
- REQ-007..REQ-013 (composizione del bundle).
- REQ-014..REQ-019 (non distruttività, idempotenza, fail-fast, report).
- REQ-022 (asset in inglese); NFR-1, NFR-2, NFR-5.

**Should**
- REQ-020 (output JSON), REQ-023 (alias dall'ombrello); NFR-3, NFR-4, NFR-6; REQ-021.

**Could**
- REQ-024 (install selettivo di sotto-bundle).
- Reviewer «clean code» attivo (fuori da questo taglio → capacità futura).

**Won't (per ora)**
- PyPI; upgrade/uninstall (FEAT-008); wizard di configurazione interattivo (FEAT-003).

## 10. Domande aperte

> **Tutte risolte (2026-06-15).** Le 7 domande DA-a..g sono state chiuse in sessione con l'utente; le
> decisioni sono riflesse nei requisiti funzionali e nei vincoli. La feature è pronta per `/speckit-specify`.

- **DA-a — Forma della costituzione installata: ✅ RISOLTA (2026-06-15).** Si deploya uno **starter
  neutro host-agnostico** + l'ospite lo personalizza con `speckit-constitution`. **Composizione dello
  starter** (classificazione della costituzione di Sertor v1.1.1 per generalità):
  - **Inclusi pienamente** (generali, de-Sertorizzati togliendo gli esempi RAG): **III** (YAGNI/SRP/DRY/
    unità piccole), **IV** (errori espliciti, no null silenzioso), **VI** (idempotenza/determinismo/
    non-distruttività/install≠run), **VII** (leggibilità Clean Code), sezione **Sicurezza/segreti**,
    sezione **Governance** (branch+PR, **Constitution Check gate**, emendamenti semver — cruciale: si
    aggancia al flusso SpecKit distribuito).
  - **Inclusi come kernel** (tenuto il principio generale, tolta la coda RAG-specifica): **I**
    (dipendi-verso-le-astrazioni; rimosso «la libreria è il prodotto»), **V** (test F.I.R.S.T./
    mockabilità; rimosso hit@k/MRR/baseline-prototipo), **VIII** (config centralizzata, no default
    hardcoded; rimossa la lista parametri RAG), **IX** (log strutturati, mai segreti; rimossi i campi
    embedding/chunk).
  - **Esclusi** (puramente Sertor): **II** (provider/backend RAG, local-first, vector store) e **X**
    (host-agnosticità = mission di Sertor).
- **DA-b — Coordinamento del blocco `CLAUDE.md` con il wiki: ✅ RISOLTA (2026-06-15).** **Due blocchi
  a marker distinti** (uno SDLC di proprietà di `sertor-flow`, uno Definition-of-Done di proprietà del
  wiki), con idempotenza indipendente e installabili separatamente. Grounding: l'attuale
  `claude-md-block.md` è **interamente wiki** (non contiene flusso SDLC) → i due blocchi sono quasi
  disgiunti. Le poche righe condivise (delega git al `configuration-manager`, commit-per-step): il
  **blocco SDLC è l'owner** della disciplina git/commit, il blocco wiki vi **rimanda**. I marker DEVONO
  essere distinti tra i due installer (no collisione idempotenza).
- **DA-c — Provenienza/licenza degli asset SpecKit: ✅ RISOLTA (2026-06-15).** Accertato: gli
  `speckit-*` (skill/agenti) e i template `.specify/` sono **di GitHub spec-kit** (frontmatter
  `author: github-spec-kit`, installati via spec-kit **v0.8.18**), licenza **MIT** → ridistribuibili
  con inclusione della nota di copyright + testo MIT. Sono **Sertor-authored**: skill `requirements` +
  agente `requirements-analyst`, agente `configuration-manager`, costituzione (starter), blocco
  rituale. **Decisione: VENDOR CON ATTRIBUZIONE** — `sertor-flow` impacchetta gli asset spec-kit a
  **versione pinnata (0.8.18)** come asset propri, includendo `LICENSE`/`NOTICE` MIT; la versione
  pinnata è un pregio (riproducibilità del metodo). Onere accettato: aggiornamento manuale di spec-kit.
  Vedi REQ-025.
- **DA-d — Granularità dell'install: ✅ RISOLTA (2026-06-15).** **Bundle completo (all-or-nothing) per
  l'MVP**: il metodo SDLC è un tutto coerente e i pezzi sono accoppiati (plan↔costituzione,
  requirements↔specify, configuration-manager↔fasi git) → i sotto-install parziali producono un metodo
  monco. La **selettività interna resta Could** (REQ-024), da aprire solo su domanda reale. La
  selettività *tra capacità* (wiki/rag/governance) è già soddisfatta dall'essere `sertor-flow` un
  pacchetto a sé.
- **DA-e — Sottoinsieme canonico di `.specify/`: ✅ RISOLTA (2026-06-15).** Tre categorie:
  - **Vendor (pinned, distribuiti verbatim)** — macchinario del metodo: `templates/`
    (spec/plan/tasks/checklist/constitution-template), `scripts/`, `extensions/git/`, `workflows/`.
  - **Generati per-host** (come `wiki.config.toml`, non copiati da Sertor): `init-options.json`,
    `integration.json`, `integrations/*.manifest.json` (riflettono le scelte dell'ospite: assistente,
    tipo di script).
  - **Esclusi** (stato runtime, gitignored): `.specify/feature.json` (puntatore alla feature corrente).
  - **Cross-platform (NFR-4):** si spediscono **entrambe** le varianti di script (`bash` + `powershell`,
    già fornite da spec-kit) e l'init generato dichiara quale usare (`script: ps|bash`); nessuna logica
    di detection OS. Coerente con la policy del workspace («versionare costituzione + artefatti,
    scaffolding resta locale») e con la generazione di config già fatta da `install wiki`.
- **DA-f — Nome e relazione coi pacchetti: ✅ RISOLTA (2026-06-15).** Nome confermato: **`sertor-flow`**.
  Relazione: **indipendenti + puntatore** — `sertor-flow` è autonomo; `sertor install governance`
  **rimanda** a `sertor-flow` (messaggio + come installarlo) **senza** che `sertor` dipenda da
  `sertor-flow` (no accoppiamento; chi installa solo wiki/rag non riceve gli asset SDLC). Vedi REQ-023.
- **DA-g — Hook di governance: ✅ RISOLTA (2026-06-15).** **Nessun hook di harness per l'MVP**:
  `sertor-flow` **non tocca `.claude/settings.json`**. Grounding: su Sertor stesso il metodo SDLC gira
  con **zero hook di harness** (gli unici in `settings.json` sono wiki+memoria, fuori scope); il flusso
  SpecKit usa skill on-demand + hook interni di SpecKit (`extensions.yml`, parte del macchinario
  `.specify/` vendored, **non** hook di harness) + Constitution Check dentro `plan`/`implement`. Il
  blocco rituale `CLAUDE.md` copre il promemoria del metodo; `speckit-git-validate` copre il
  branch-naming on-demand. Hook di harness = **Could** futuro se emerge un bisogno in background.
