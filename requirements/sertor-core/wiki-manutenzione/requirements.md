# Requisiti — Skill: mantenere il wiki vivo (lint strutturale + semantico / indice / distillazione)
<!-- Deriva da: FEAT-007 -->
<!-- Esteso (2026-06-03): aggiunto il lint SEMANTICO (Gruppo H) dopo che il dogfood del lint
     strutturale ha mostrato un "verde ingannevole". -->

## 1. Contesto e problema (perché)

La skill di **creazione** del wiki (FEAT-003, in `master`) crea la struttura, documenta in continuo
(record/ingest/distill) e indicizza le pagine nel RAG. Ma un wiki **vive e si degrada**: i wikilink
si rompono quando una pagina cambia nome, nascono pagine **orfane** non più collegate, l'**indice**
(`index.md`) diverge dalle pagine reali, e possono accumularsi **contraddizioni**. Senza una
manutenzione disciplinata e **idempotente**, il wiki perde coerenza e degrada la qualità del RAG
documentale (rischio R-2 dell'epica).

FEAT-007 è la **controparte di manutenzione** di FEAT-003: non crea contenuti nuovi a mano, ma
**verifica e rigenera** ciò che esiste (lint dei link, rilevazione orfani, rigenerazione
dell'indice, segnalazione contraddizioni) e — dove serve un LLM — **distilla** sorgenti grezze in
pagine concept. Riusa le convenzioni e la struttura già definite nel core
(`src/sertor_core/wiki/conventions.py`, `structure.py`): frontmatter YAML, wikilink `[[...]]`,
naming kebab-case, cartelle tematiche, `index.md`/`log.md`.

**Cadenza — manutenzione frequente, non una-tantum.** Il lint (e in generale la manutenzione) è
pensato per girare **di continuo / a intervalli molto frequenti**, tipicamente **al termine di ogni
feature** (o prima del merge): deve quindi essere **veloce, idempotente e non distruttivo**, e
**automatizzabile come gate ricorrente** del flusso di lavoro, con un esito **pass/fail**
consumabile (così la documentazione non diverge mai a lungo dal codice).

**Ruolo prioritario — il wiki è la documentazione UFFICIALE del progetto.** Deve racchiudere,
descrivere, collegare e dettagliare **tutti i concetti alla base del progetto**: le **entità di
business**, le **funzionalità ad alto/medio livello**, le **motivazioni dietro le scelte** e
l'**architettura** — cioè la descrizione documentale di ciò che è realizzato nel codice. Le
**sorgenti "raw"** da cui questa documentazione è distillata non sono solo le **discussioni**, ma
anche **tutti gli artifact di SpecKit e dei requisiti** (epic, requirements, spec, plan, tasks,
costituzione): il wiki li **sintetizza in forma narrativa** e vi **rimanda con link** per il
dettaglio, **senza duplicarli** (coerente con DA-W1: il wiki *rimanda* agli artefatti, non li
specchia, così non diverge). FEAT-007 mantiene questa documentazione **coerente, completa e
collegata** nel tempo.

**Lezione dal dogfood — perché serve un lint SEMANTICO.** Il lint **strutturale** (Gruppi A–G,
già realizzato) verifica solo la *forma*: link risolti, niente orfani, indice sincronizzato coi
file, coperture per *path atteso*. Eseguito sul wiki di produzione ha restituito **"verde"** mentre
il wiki era, nel merito, **sconclusionato**: l'indice e le pagine descrivevano **funzionalità
obsolete**, con riferimenti tutti formalmente validi. Un indice perfettamente sincronizzato può
documentare il falso. La forma sana **non garantisce** la verità del contenuto. Serve quindi una
verifica della **sostanza**: un lint **semantico** assistito da LLM che giudichi se ciò che il wiki
*afferma* è ancora **vero, coerente e completo** rispetto al **codice reale**. Il riferimento di
verità è duplice — **coerenza interna** (wiki↔wiki) **e** confronto col **codice indicizzato** nel
corpus di dogfooding (il progetto usa il proprio retrieval per validare la propria documentazione,
chiudendo il loop). Dove i problemi riguardano pagine **generate dallo strumento**, la correzione
può essere **assistita** (proposta + applicazione su diff revisionabile); le pagine **curate a mano**
ricevono **solo** una proposta, mai una riscrittura automatica.

---

## 2. Obiettivi e criteri di successo

| ID | Criterio (misurabile) | Collegamento |
|----|------------------------|--------------|
| LSC-1 | `lint` produce un **report strutturato** che elenca link rotti e pagine orfane di un wiki, **senza modificare alcun file**. | CS-3 (mantenere), Principio IV/VI |
| LSC-2 | `index-rebuild` rigenera il catalogo di `index.md` **in modo idempotente** (re-run su wiki invariato → file identico) e **senza distruggere** il contenuto curato a mano. | CS-3, Principio VI |
| LSC-3 | Su un wiki invariato, qualunque operazione rieseguita produce un **esito identico** (nessun file/voce/timestamp nuovi). | Principio VI |
| LSC-4 | Le contraddizioni **marcate** (dall'ingest di FEAT-003) sono elencate nel report; con LLM configurato, è possibile segnalare contraddizioni semantiche. | CS-3 |
| LSC-5 | La skill opera su **≥2 wiki diversi** senza modifiche (path da configurazione). | CS-5 (repo-agnostico) |
| LSC-6 | Ogni operazione emette **log strutturati** (operazione, file coinvolti, conteggi, esito). | Principio IX |
| LSC-7 | Il wiki copre, come **documentazione ufficiale**, le aree fondamentali del progetto: **entità di business, funzionalità (alto/medio livello), motivazioni delle scelte, architettura**; il lint **segnala le aree mancanti**. | FEAT-007 (ruolo prioritario) |
| LSC-8 | Ogni pagina di documentazione distillata da artifact **rimanda con link** alle fonti (spec/plan/tasks/requirements/epic/costituzione) per il dettaglio, **senza duplicarne** il contenuto. | DA-W1, Principio III |
| LSC-9 | Con LLM configurato, il **lint semantico** rileva almeno: (a) una pagina/sommario che descrive una **funzionalità non più presente** nel codice (obsolescenza), (b) una **contraddizione semantica** tra pagine, (c) una **lacuna di copertura** (entità/feature/decisione/architettura presente nel codice ma non documentata), (d) un **sommario di indice/pagina viva stantio**; ciascun problema con **severità**. | FEAT-007 (lint semantico) |
| LSC-10 | L'**auto-fix assistito** applica correzioni (riscrittura o **cancellazione** di pagine obsolete) **solo** su pagine **generate dalla tooling**, presentandole come **diff revisionabile**; sulle pagine **curate a mano** (o prive di marcatore) produce **solo una proposta** e **non le cancella mai**. Un intervento manuale su una pagina generata la rende **curata**. | Principio VI, LSC-9 |
| LSC-11 | Senza LLM, il lint semantico è **saltato senza errore** e il lint strutturale resta pienamente operativo con il suo esito pass/fail (degrado controllato). | NFR-04, Principio IV |

---

## 3. Stakeholder e attori

| Attore | Ruolo |
|--------|-------|
| **Owner/maintainer** | Esegue lint/index-rebuild periodici; legge il report e decide le correzioni. |
| **Agente LLM (es. Claude Code)** | Attore automatico: invoca le operazioni; per la distillazione/contraddizioni semantiche usa l'LLM. |
| **Skill di creazione (FEAT-003)** | Fornisce convenzioni, struttura e i marcatori di contraddizione che il lint legge. |
| **CI / automazione (futuro)** | Consuma il report strutturato di `lint` come gate di qualità del wiki. |
| **Wiki target** | Qualunque radice wiki conforme alle convenzioni. |

---

## 4. Ambito

### In ambito
- **Documentazione ufficiale del progetto** (prioritario): mantenere nel wiki le pagine che descrivono **entità di business**, **funzionalità (alto/medio livello)**, **motivazioni/decisioni** e **architettura**; ogni pagina **rimanda con link** alle fonti di dettaglio (artifact SpecKit/requisiti) senza duplicarle.
- **Distillazione di artifact e discussioni → documentazione** (con LLM): dato un artifact (epic/requirements/spec/plan/tasks/costituzione) o un brief di discussione, produrre/aggiornare la pagina di documentazione conforme, con backlink alla fonte.
- **Lint**: validazione dei wikilink (link rotti verso pagine inesistenti), rilevazione **pagine orfane**, segnalazione di pagine presenti su disco ma assenti dall'indice, e **segnalazione delle aree di documentazione mancanti** (entità/feature/decisioni/architettura); **report strutturato, non distruttivo**.
- **Rigenerazione dell'indice**: ricostruzione/aggiornamento del catalogo di `index.md` (link + sommario per pagina), **idempotente** e **non distruttiva** del contenuto curato a mano.
- **Contraddizioni**: elenco delle pagine con marcatori di contraddizione; (opzionale, con LLM) segnalazione di contraddizioni semantiche.
- **Lint semantico (con LLM)** — verifica della *sostanza*, con riferimento di verità **duplice** (coerenza interna wiki↔wiki **e** confronto col **codice indicizzato** del corpus di dogfooding):
  - **(a) obsolescenza vs codice**: pagine/sommari che descrivono funzionalità non più presenti o cambiate nel codice;
  - **(b) contraddizioni semantiche** tra pagine (oltre i marcatori espliciti);
  - **(c) lacune di copertura semantiche**: entità di business / feature / decisioni / architettura presenti nel codice ma non documentate;
  - **(d) accuratezza di indice/sommari e pagine vive** (es. roadmap): descrizioni non più aderenti allo stato reale.
- **Provenienza delle pagine**: marcatura della provenienza (**generata dallo strumento** vs **curata a mano**) come prerequisito per governare l'auto-fix.
- **Auto-fix assistito** dei problemi semantici: **solo** su pagine generate dallo strumento, come **diff revisionabile** prima del consolidamento; sulle pagine curate a mano solo **proposta**.
- **Idempotenza** trasversale; **repo-agnosticità** e **configurabilità** (path del wiki); **osservabilità** (log strutturati).

> **Sorgenti "raw" (definizione estesa).** Non solo i file in `raw/` (discussioni, note), ma anche
> **gli artifact del progetto**: `requirements/**` (epic + requisiti EARS), `specs/**`
> (spec/plan/tasks/contracts/research/quickstart) e `.specify/memory/constitution.md`. Il wiki li
> **distilla** in documentazione narrativa e vi **rimanda** per il dettaglio.

### Fuori ambito
- **Creazione struttura, record, ingest** (è FEAT-003).
- **Indicizzazione del wiki nel RAG** (FEAT-003, Gruppo E).
- **Arricchimento bidirezionale Wiki↔RAG** (FEAT-008).
- **Auto-correzione dei link rotti** (richiede giudizio: il lint **segnala**, non ripara).
- **Riscrittura semantica delle pagine CURATE a mano** (su quelle l'auto-fix produce solo proposte; la riscrittura assistita è ammessa **solo** sulle pagine generate dallo strumento).
- **Generazione ex-novo** di intere pagine mancanti come parte del lint (le lacune si **segnalano**; la creazione resta la distillazione esplicita, Gruppo D/G).
- **Re-indicizzazione FULL del corpus di codice** da zero (il lint semantico fa solo un **re-index incrementale del change set** prima del confronto, vedi REQ-096/DA-13; il full re-index resta di FEAT-003/CLI).
- **Generazione di risposte** / UX-CLI (epica `sertor-cli`).

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Lint (verifica non distruttiva)

**REQ-001 (Event-driven)** *When a lint operation is invoked on a wiki root, the system shall scan
all Markdown pages and produce a structured report of issues, without modifying any file.*

**REQ-002 (Event-driven)** *When linting, the system shall report every wikilink `[[name]]` whose
target page does not exist (broken link), indicating the source page.*

**REQ-003 (Event-driven)** *When linting, the system shall report **orphan** pages — pages not
referenced by any wikilink in another page nor listed in `index.md` — escludendo per definizione
`index.md` e `log.md`.*

**REQ-004 (Event-driven)** *When linting, the system shall report pages present on disk but **missing
from the `index.md` catalog** (indice disallineato).*

**REQ-005 (Unwanted behaviour)** *If a lint operation runs without an explicit fix flag, then the
system shall NOT modify, create or delete any wiki file (sola lettura di default).*

**REQ-006 (Optional feature)** *Where an explicit fix flag (`--fix`) is given, the system shall apply
only **safe, idempotent** fixes (es. rigenerazione dell'indice) e **mai** auto-fix dei link rotti
(che richiedono giudizio).*

### Gruppo B — Rigenerazione dell'indice

**REQ-010 (Event-driven)** *When an index-rebuild operation is invoked, the system shall regenerate
the page catalog of `index.md` (link + one-line summary per page) reflecting the pages currently on
disk.*

**REQ-011 (Unwanted behaviour)** *If `index.md` contains manually-curated content outside the managed
catalog region, then the system shall preserve it (rigenerazione non distruttiva).*

**REQ-012 (Event-driven)** *When index-rebuild runs twice on an unchanged wiki, then the resulting
`index.md` shall be identical to the first run (idempotenza, nessun diff).*

**REQ-013 (Ubiquitous)** *The system shall derive each catalog entry's one-line summary from the page
itself (es. titolo del frontmatter o primo heading).*

### Gruppo C — Contraddizioni

**REQ-020 (Event-driven)** *When linting, the system shall report every page containing an explicit
contradiction marker (prodotto dall'ingest di FEAT-003).*

**REQ-021 (Optional feature)** *Where an LLM provider is configured, the system shall be able to flag
**semantic** contradictions between pages as report items (segnalazione, non modifica).*
> Le contraddizioni semantiche sono **dettagliate ed estese** nel **Gruppo H** (lint semantico,
> REQ-072), che le inquadra insieme a obsolescenza, lacune e accuratezza dei sommari.

**REQ-022 (Unwanted behaviour)** *If no LLM is configured, then semantic contradiction detection shall
be skipped (solo marcatori espliciti), senza errore.*

### Gruppo D — Distillazione raw→concept

**REQ-030 (Event-driven)** *When a distill-raw operation is invoked on a source file under `raw/`, the
system shall produce or update a conforming concept page (frontmatter, kebab-case, cartella tematica,
wikilink) che ne sintetizza il contenuto.*

**REQ-031 (Unwanted behaviour)** *If no LLM provider is configured, then a distill-raw operation shall
be blocked with an explicit, readable error.*

**REQ-032 (Event-driven)** *When distill-raw produces a new or updated page, the system shall update
`index.md` and append one entry to `log.md`.*

**REQ-033 (Unwanted behaviour)** *If distill-raw is re-run on an unchanged input, then the system
shall not create duplicate pages or log entries (idempotenza **strutturale**; il contenuto generato
dall'LLM può variare solo se la pagina non esiste ancora).*

### Gruppo E — Idempotenza trasversale

**REQ-040 (Complex: event-driven + unwanted)** *When any maintenance operation (lint, index-rebuild,
distill-raw) is executed more than once on an unchanged wiki, then the system shall produce an output
identical to the first execution, with no new files, no duplicate log entries, and no modified
timestamps on unchanged files.*

**REQ-041 (Ubiquitous)** *The system shall use the relative path of a page as its stable identifier
(coerente con FEAT-003), così che la manutenzione non generi nuove identità.*

### Gruppo F — Configurazione, osservabilità, repo-agnosticità

**REQ-050 (Ubiquitous)** *The system shall accept the wiki root path as a configurable parameter and
shall not hard-code any repository-specific path.*

**REQ-051 (Ubiquitous)** *The system shall emit structured log events for each operation (operazione,
file/pagine coinvolte, conteggi, esito) senza segreti.*

**REQ-052 (Ubiquitous)** *The system shall return the lint outcome as a **structured report**
(elenco di problemi tipizzati) consumabile a programma (es. da una CI), oltre a una resa leggibile.*

**REQ-053 (Ubiquitous)** *The maintenance operations (lint, index-rebuild, coverage report) shall be
designed to run **frequentemente e ripetutamente** — es. al termine di ogni feature / prima del
merge — restando veloci, idempotenti e non distruttive, e shall produce a **pass/fail outcome**
consumabile come **gate** di automazione (CI / hook di fase / comando ricorrente).*

### Gruppo G — Il wiki come documentazione ufficiale (prioritario)

**REQ-060 (Ubiquitous)** *The wiki shall act as the project's **official documentation**, covering at
minimum: **business entities**, **high/medium-level features**, **rationale behind decisions**, and
**architecture** — la descrizione documentale di ciò che è realizzato nel codice.*

**REQ-061 (Ubiquitous)** *The system shall treat as distillation **sources** both project discussions
and the **project artifacts**: `requirements/**` (epic + EARS), `specs/**`
(spec/plan/tasks/contracts/research/quickstart) and `.specify/memory/constitution.md`.*

**REQ-062 (Event-driven)** *When the system distills an artifact (or a discussion) into a
documentation page, it shall **link** to the source artifact(s) for detail and **shall not duplicate**
their content (il wiki sintetizza e rimanda, non specchia).*

**REQ-063 (Event-driven)** *When a documentation-distillation operation is invoked on an artifact (or
brief), the system shall produce or update a conforming wiki page (frontmatter, kebab-case, cartella
tematica, wikilink) che descrive l'entità/funzionalità/decisione/architettura pertinente, con backlink
alla fonte.*

**REQ-064 (Event-driven)** *When linting, the system shall report **missing documentation coverage**:
quali aree fondamentali (entità di business, funzionalità, decisioni, architettura) non risultano
documentate nel wiki.*

**REQ-065 (Unwanted behaviour)** *If a documentation-distillation operation needs generation and no LLM
provider is configured, then the operation shall be blocked with an explicit, readable error (le sole
operazioni LLM-free sono lint, rigenerazione indice e segnalazione coperture/contraddizioni marcate).*

### Gruppo H — Lint semantico (LLM-assistito) e auto-fix assistito

**REQ-070 (Optional feature)** *Where an LLM provider is configured, the system shall perform a
**semantic lint** that produces typed issues alongside the structural ones, judging the **substance**
of the wiki (verità, coerenza, completezza del contenuto) e non solo la forma.*

**REQ-071 (Event-driven — obsolescenza vs codice)** *When the semantic lint runs and a wiki page or
index summary asserts a functionality/behaviour that the **indexed code corpus** (dogfooding) does
not support or contradicts, the system shall report an **obsolescence** issue identifying the page and
the divergent claim.*

**REQ-072 (Event-driven — contraddizioni semantiche)** *When the semantic lint runs, the system shall
report **semantic contradictions between pages** (affermazioni in conflitto nel merito), oltre ai
marcatori espliciti del Gruppo C.*

**REQ-073 (Event-driven — lacune di copertura)** *When the semantic lint runs, the system shall report
**semantic coverage gaps**: business entities, features, decisions or architecture present in the code
corpus but **not documented** in the wiki (la variante semantica di REQ-064, che è per path atteso).*

**REQ-074 (Event-driven — accuratezza sommari/pagine vive)** *When the semantic lint runs, the system
shall report **stale summaries**: voci dell'indice e pagine "vive" (es. roadmap) la cui descrizione
non riflette più lo stato corrente della pagina/codice corrispondente.*

**REQ-075 (Ubiquitous — riferimento di verità duplice)** *The semantic lint shall judge using BOTH
**internal coherence** (wiki↔wiki) AND **comparison against the code** through the project's retrieval
over the indexed corpus (dogfooding).*

**REQ-076 (Ubiquitous — provenienza)** *The system shall record and read the **provenance** of each
wiki page. Una pagina è **generata** se prodotta dalla tooling/dagli agenti del progetto
(`wiki-keeper`, `record`/`distill`, `distill_artifact`); è **curata a mano** se mantenuta
dall'utente (es. le pagine "vive" come la roadmap). La provenienza governa cosa l'auto-fix può
modificare o cancellare.*

**REQ-077 (Event-driven — auto-marcatura)** *When the tooling produces or updates a page through its
own pipeline (es. `distill_artifact`/`record`), the system shall mark that page as **generated**, così
che l'auto-fix possa manutenerla.*

**REQ-077b (Unwanted behaviour — salvaguardia dell'intervento manuale)** *If a human edits a page
marked **generated**, then the system shall reclassify it as **curated** (l'intervento manuale ha
precedenza: l'auto-fix non sovrascrive una pagina su cui l'utente ha messo mano).*

**REQ-077c (Unwanted behaviour — default sicuro)** *If a page has no provenance marker (es. pagine
preesistenti), then the system shall treat it as **curated** by default; una classificazione iniziale
esplicita può marcare come **generated** le pagine prodotte dalla tooling (vedi DA-9).*

**REQ-078 (Optional feature — proposta)** *Where assisted auto-fix is enabled and an LLM is configured,
the system shall, for each fixable semantic issue, **generate a proposed correction** (testo + pagina
bersaglio + motivazione).*

**REQ-079 (Event-driven — applicazione assistita)** *When an assisted auto-fix is applied, the system
shall write **only** on **tool-generated pages**, nella working tree/index, così che la modifica entri
nel **commit imminente**; la modifica resta **revisionabile come diff** (commit/PR) prima del merge
(mai scrittura cieca; l'umano resta nel loop e approva la PR).*

**REQ-080 (Unwanted behaviour — pagine curate)** *If the target of an auto-fix is a hand-curated page
(o priva di marcatore), then the system shall **only emit a proposal** in the report and shall NOT
modify the page.*

**REQ-081 (Unwanted behaviour — degrado senza LLM)** *If no LLM provider is configured, then the
semantic lint and its auto-fix shall be **skipped without error**, and the structural lint shall still
run and produce its pass/fail outcome.*

**REQ-082 (Ubiquitous — severità e gate)** *The system shall assign a **severity** to each semantic
issue and shall feed it into the lint **pass/fail** outcome, with a **configurable threshold** che
determina quali severità bloccano il gate.*

**REQ-083 (Ubiquitous — limiti di costo)** *The semantic lint shall **bound** its LLM usage (es. limite
di chiamate/pagine per esecuzione o campionamento) and shall report **what was not covered** (nessun
troncamento silenzioso).*

**REQ-084 (Complex — idempotenza della rilevazione)** *When the semantic lint runs twice on an
unchanged wiki and corpus, then the system shall produce an **equivalent set of issues** (stessa
rilevazione e severità), pur riconoscendo che il **testo** delle proposte/riscritture può variare per
non determinismo dell'LLM (l'idempotenza è garantita sulla *rilevazione*, non sul testo generato).*

**REQ-085 (Optional feature — cancellazione assistita di pagine generate obsolete)** *Where assisted
auto-fix is enabled, when a **generated** page is found obsolete and **not meaningfully updatable**,
the system shall propose its **deletion** as a reviewable change; il consolidamento avviene solo dopo
revisione. Le pagine **curate a mano non sono mai cancellate** dall'auto-fix.*

**REQ-086 (Event-driven — classificazione iniziale della provenienza)** *When provenance is first
introduced on an existing wiki, the system shall support a **one-time classification** that marks
tool/agent-produced pages as **generated** and explicitly hand-maintained living pages (es. roadmap)
as **curated**, con default sicuro = **curated** in caso di incertezza.*

**REQ-087 (Event-driven — baseline completo alla prima esecuzione)** *When the semantic lint runs with
no prior state (nessun watermark), the system shall verify **all** pages against the code corpus (full
baseline), nei limiti di costo (REQ-083).*

**REQ-088 (Event-driven — incrementale guidato da git)** *When a prior watermark exists, the system
shall determine the code **entities/files changed** in the relevant **change set** — gli elementi
**staged/working** per un'esecuzione **pre-commit**, oppure i **commit dal watermark** per
un'esecuzione pre-push/periodica (via git/GitHub) — and shall re-verify **only the wiki pages
associated** with those changed entities (manutenzione incrementale, non "tutto contro tutto").*

**REQ-089 (Ubiquitous — watermark git)** *The system shall persist the **git reference** (commit) of
the last completed semantic lint, così da delimitare l'ambito della successiva esecuzione incrementale.*

**REQ-090 (Ubiquitous — mappa entità↔pagine)** *The system shall maintain or derive an association
between **code entities/files** and the **wiki pages** that document them, so that a change to an entity
selects the pages to re-verify (riusa backlink/copertura ove possibile).*

**REQ-091 (Unwanted behaviour — fallback se git non disponibile)** *If git history is unavailable or
the watermark is missing/invalid, then the system shall fall back to a **full baseline** rather than
skipping verification, segnalandolo nel report.*

**REQ-092 (Event-driven — trigger pre-commit/pre-push, a monte di git)** *When a commit, a push or a PR
creation is about to occur, the system shall run the (incremental) semantic lint **and** assisted
auto-fix **before** the version-control operation, so that any fix to generated pages is included in
the **same** commit; il commit/push effettivo è poi eseguito dal `configuration-manager` (il lint è il
**trigger a monte**, non lo esegue git stesso).*

**REQ-093 (Unwanted behaviour — niente cambiamenti rilevanti)** *If the pending change set touches no
entity associated with any wiki page, then the pre-commit semantic run shall be a **fast no-op** (non
rallenta i commit che non impattano la documentazione).*

**REQ-094 (Unwanted behaviour — blocco sopra soglia)** *If, after auto-fix, open semantic issues remain
at or above the **configured severity threshold**, then the pre-commit/pre-push gate shall **block** the
version-control operation and report the blocking issues; issues **below** threshold shall pass with a
**warning** (non bloccano).*

**REQ-095 (Optional feature — override esplicito e tracciato)** *Where an explicit override is provided,
the system shall allow the commit/push to proceed despite blocking issues, **recording** the override
in modo tracciabile (escape hatch dichiarato, non un bypass silenzioso degli hook).*

**REQ-096 (Event-driven — re-index incrementale prima del confronto)** *Before performing the semantic
verification, the system shall **incrementally re-index** the code files in the change set (git-driven),
so the comparison uses the **current** code (entità modificate e relativo contesto). Realizza la
sinergia con FEAT-009 (indicizzazione incrementale).*

**REQ-097 (Unwanted behaviour — fallback se l'incrementale non è disponibile)** *If incremental
re-indexing is not available, then the system shall degrade gracefully — leggendo direttamente i file
del change set dalla working tree e **segnalando** che il contesto dell'indice può essere stantio —
rather than comparing against stale code silently.*

**REQ-098 (Ubiquitous — granularità per affermazione)** *The semantic lint shall judge obsolescence and
contradictions at the granularity of **individual verifiable claims/paragraphs** (non l'intera pagina),
so that issues identify the **specific claim** and the assisted auto-fix can be **surgical** (diff
minimi e revisionabili).*

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| NFR-01 | **Non distruttività** | Lint è sola lettura; index-rebuild preserva il contenuto curato a mano; distill non sovrascrive pagine invariate (Principio IV/VI). |
| NFR-02 | **Idempotenza** | Re-run su wiki invariato → esito identico (hash file invariati). |
| NFR-03 | **Testabilità** | Ogni operazione testabile su un **wiki sandbox temporaneo** (mai sul wiki di produzione); distillazione/contraddizioni semantiche con LLM **mock**. |
| NFR-04 | **Isolamento dell'LLM** | Distillazione **e lint semantico** (incl. contraddizioni semantiche, obsolescenza, lacune, accuratezza sommari) richiedono un LLM; lint strutturale, orfani e index-rebuild sono **LLM-free** e restano operativi senza LLM. |
| NFR-05 | **Portabilità** | Funziona su Linux e Windows senza modifiche. |
| NFR-06 | **Osservabilità** | Log strutturati per ogni operazione (Principio IX); il lint semantico registra anche conteggio chiamate LLM e copertura. |
| NFR-07 | **Performance** | Lint **strutturale** deterministico in pochi secondi (gira a ogni feature). Lint **semantico** gira **pre-commit/pre-push** ma resta pratico perché **incrementale** (solo le entità del change set, REQ-088) e **no-op** quando il change set non tocca pagine (REQ-093); costo limitato (NFR-09). |
| NFR-08 | **Automazione/cadenza** | Le operazioni sono **idempotenti e non interattive**, integrabili come **trigger pre-commit/pre-push** (a monte del configuration-manager, REQ-092) o gate CI, con esito pass/fail; il gate semantico **blocca** sopra una soglia di severità configurabile, con override esplicito (REQ-082/094/095). |
| NFR-09 | **Costo / budget LLM** | Il lint semantico **limita** chiamate/token per esecuzione (campionamento o tetto), espone quanto coperto/non coperto, e non degrada in costi incontrollati su wiki/corpus grandi (REQ-083). |
| NFR-10 | **Local-first** | Il lint semantico deve poter girare con un **LLM locale** (es. Ollama), non solo cloud (Azure): nessuna dipendenza obbligatoria da servizi a pagamento (coerente con local-first del progetto). |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli
- **V-1**: Riusa le convenzioni/struttura di FEAT-003; non le ridefinisce (DRY, Principio III).
- **V-2**: Il lint **non modifica** il wiki (Principio IV/VI); le uniche scritture sono operazioni esplicite (index-rebuild, distill).
- **V-3**: Nessun segreto su file versionati; `raw/` resta non versionato (lettura consentita, scrittura no).
- **V-4**: Python ≥ 3.11.

### Assunzioni
- **A-1**: Il wiki target è conforme alle convenzioni di FEAT-003 (frontmatter, wikilink, cartelle).
- **A-2**: L'attore automatico (agente LLM) fornisce l'LLM quando serve (distill/contraddizioni semantiche).
- **A-3**: La distillazione riceve **sorgenti già leggibili** in formato testo: i file in `raw/`
  (discussioni/note) **e** gli artifact del progetto (`requirements/**`, `specs/**`,
  `.specify/memory/constitution.md`); non gestisce crawling esterno né formati binari.
- **A-4**: La documentazione ufficiale **rimanda** agli artifact per il dettaglio (link), non li
  duplica: gli artifact restano la fonte di verità formale, il wiki è la sintesi narrativa.
- **A-5**: Il lint semantico assume un **corpus di codice indicizzato e ragionevolmente aggiornato**
  (corpus `production` del dogfooding) come riferimento di verità "codice"; un corpus stantio degrada
  la qualità della rilevazione (vedi R-M8, DA-13).
- **A-6**: La provenienza delle pagine è **dichiarabile**: le pagine generate dallo strumento sono
  marcabili; quelle esistenti prive di marcatore sono trattate come curate a mano (default sicuro).

### Dipendenze
- **D-1**: **FEAT-003** (convenzioni e struttura del wiki, marcatori di contraddizione) — in `master`.
- **D-2**: Porta **`LLMProvider`** del core — per la distillazione documentale (ruolo prioritario), le contraddizioni semantiche **e l'intero lint semantico** (Gruppo H).
- **D-3**: Gli **artifact** `requirements/**`, `specs/**`, `.specify/memory/constitution.md` come sorgenti della documentazione (in repo, versionati).
- **D-4**: Il **retrieval del core** sul **corpus `production`** (codice indicizzato, dogfooding) come fonte di verità "codice" per l'obsolescenza e le lacune (Gruppo H). Riusa la capacità RAG già esistente.
- **D-5**: Il lint **strutturale** (Gruppi A–G, già realizzato in `spec/005-wiki-manutenzione`) che il lint semantico **estende** affiancandone i problemi e l'esito pass/fail.
- **D-6**: **Git/GitHub** (storia dei commit) come sorgente del "cosa è cambiato" per la verifica incrementale (REQ-088/089). **Sinergia con FEAT-009** (refresh incrementale dell'indice RAG, anch'esso git-driven): condividono il segnale di diff sui sorgenti.
- **D-7**: **Capacità di re-index incrementale** (FEAT-009) come **prerequisito** per aggiornare il corpus sul change set prima del confronto (REQ-096); con fallback se assente (REQ-097).

---

## 8. Rischi

| ID | Rischio | Prob. | Impatto | Mitigazione |
|----|---------|-------|---------|-------------|
| R-M1 | **Rigenerazione indice distruttiva**: sovrascrive contenuto curato a mano. | Media | Alto | REQ-011 + DA-1 (sezione gestita tra marcatori); test su sandbox. |
| R-M2 | **Falsi positivi orfani** (es. pagine linkate solo da link Markdown, o index/log). | Media | Medio | DA-5 (definizione precisa di "referenziato"); index.md/log.md esenti (REQ-003). |
| R-M3 | **Non determinismo LLM** in distill/contraddizioni semantiche. | Alta | Medio | Idempotenza **strutturale** (REQ-033); contraddizioni semantiche come Could/opzionali. |
| R-M4 | **Qualità contraddizioni semantiche** bassa (rumore). | Media | Medio | MVP solo marcatori espliciti; semantico opt-in con LLM (DA-2). |
| R-M5 | **Contaminazione del wiki di produzione** durante i test. | Media | Alto | NFR-03: test su wiki temporaneo isolato. |
| R-M6 | **Allucinazione "correttiva"**: l'LLM segnala come obsoleto/contraddittorio un contenuto in realtà corretto, o propone una riscrittura che introduce errori. | Alta | Alto | Auto-fix **solo** su pagine generate + **diff revisionabile** con umano nel loop (REQ-079/080); severità + soglia gate (REQ-082); proposta motivata e tracciabile. |
| R-M7 | **Costo/token incontrollato** del lint semantico su wiki/corpus grandi. | Media | Medio | Limiti/campionamento + report di copertura (REQ-083/NFR-09); cadenza on-demand, non a ogni feature (NFR-07). |
| R-M8 | **Corpus stantio**: il codice indicizzato non riflette lo stato attuale → falsi "obsoleti" o lacune errate. | Media | Alto | **Re-index incrementale del change set prima del confronto** (REQ-096); fallback lettura working tree + segnalazione (REQ-097). |
| R-M9 | **Provenienza errata**: una pagina curata trattata come generata → auto-fix la sovrascrive/cancella. | Bassa | Alto | Default sicuro = curata (REQ-077c); intervento manuale riclassifica a curata (REQ-077b); cancellazione solo su generate e revisionata (REQ-085). |
| R-M10 | **Rename/spostamento di entità** non rilevato dal diff git → pagina collegata non ri-verificata (falso "tutto ok") nell'incrementale. | Media | Medio | Rilevazione rename di git; baseline completo periodico/forzabile; fallback completo se watermark invalido (REQ-091). |
| R-M11 | **Watermark stantio o mappa entità↔pagine incompleta** → l'incrementale salta pagine da verificare. | Media | Medio | Baseline completo forzabile; il report segnala l'ambito coperto vs saltato (REQ-083); mappa derivata e aggiornata al baseline (REQ-090). |

---

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivazione |
|----------|-----------|-------------|
| **Must** | REQ-001..005 (lint+report), REQ-040/041 (idempotenza), REQ-050..053 (config/osservabilità/report + **cadenza/gate ricorrente**), **REQ-060/061/062 (wiki = documentazione ufficiale: ruolo, sorgenti incl. artifact, link-non-duplica)**, REQ-064 (report coperture mancanti, LLM-free) | Valore centrale: il wiki **è** la documentazione ufficiale, mantenuta coerente e diagnosticabile in modo non distruttivo, **verificabile a ogni feature**. |
| **Should** | REQ-010..013 (rigenera indice), REQ-020 (contraddizioni marcate), **REQ-030..033 + REQ-063/065 (distillazione documentale da artifact/discussioni, con LLM)**, **REQ-070..077 + REQ-081..084 (lint SEMANTICO: i 4 controlli, verità duplice, provenienza, degrado, severità/gate, limiti di costo, idempotenza della rilevazione)** | Mantiene l'indice allineato, alimenta la documentazione ufficiale e — priorità richiesta dall'utente — verifica la **sostanza** del wiki contro il codice. Il lint semantico è il prossimo incremento (lo strutturale è già fatto). |
| **Could** | REQ-078..080 + **REQ-085** (**auto-fix assistito**: proposta + applicazione su diff per le sole pagine generate, incl. **cancellazione** di pagine generate obsolete) | Alto valore ma più rischioso (allucinazioni): dopo che la **rilevazione** semantica ha dimostrato valore; richiede prima il marcatore di provenienza (REQ-076/077/086). |
| **Won't (ora)** | Auto-fix dei link rotti; riscrittura automatica di pagine curate; generazione ex-novo di pagine mancanti nel lint; crawling esterno; arricchimento Wiki↔RAG (FEAT-008) | Fuori ambito / altre feature. |

> **Nota sull'auto-fix.** L'utente ha richiesto l'auto-fix **assistito**. È classificato **Could** non
> per de-prioritizzarlo ma per **sequenza**: prima la **rilevazione** semantica (Should) e il
> **marcatore di provenienza** (REQ-076, prerequisito), poi l'applicazione assistita su diff. Resta
> nel perimetro di FEAT-007 e va realizzato subito dopo la rilevazione.

---

## 10. Domande aperte

### Risolte (lint strutturale + ruolo documentazione)

Chiuse in elicitazione (2026-06-03) e codificate nei requisiti.

- **DA-1 — Rigenerazione di `index.md`.** *Risolta:* **sezione gestita tra marcatori**
  (`<!-- sertor:catalog -->` … `<!-- /sertor:catalog -->`); tutto il resto resta intatto (REQ-010/011).
- **DA-2 — Contraddizioni.** *Risolta:* **solo marcatori espliciti** nell'MVP (REQ-020);
  contraddizioni **semantiche** con LLM restano **Could** (REQ-021/022).
- **DA-3 — Distillazione documentale.** *Risolta:* **in ambito, Should**, e **assistita /
  non distruttiva** — l'LLM genera la pagina quando manca e **non sovrascrive** il contenuto curato a
  mano (idempotenza strutturale); l'agente resta nel loop (REQ-030..033, REQ-063/065).
- **DA-4 — Lint: report vs fix.** *Risolta:* **report di default + `--fix` opt-in** per i soli fix
  **sicuri/idempotenti** (rigenerazione indice); **mai** auto-fix dei link rotti (REQ-005/006).
- **DA-5 — "Referenziato" (orfani).** *Risolta:* referenziato = compare in `index.md` **o** in un
  **wikilink** `[[...]]` di un'altra pagina; `index.md`/`log.md` esenti (REQ-003).
- **DA-6 — Invocazione.** *Risolta:* **operazioni come libreria nel core** in questa feature;
  l'esposizione via sottocomandi CLI (`sertor wiki lint/reindex/distill`) arriva in una feature CLI
  successiva.
- **DA-7 — Modello di contenuto.** *Risolta:* **cartelle tematiche dedicate** (entità di business →
  `concepts/`; architettura + decisioni → `syntheses/`; una pagina per feature) + **copertura
  verificata su un set atteso configurabile** (REQ-060/064).
- **DA-8 — Trigger del gate.** *Risolta:* la feature espone un'**operazione non-interattiva con esito
  pass/fail** (REQ-053); come **default** la si **aggancia a un hook di fase** (es. dopo `implement`),
  lasciando CI e invocazione manuale possibili. Il meccanismo preciso è design.
- **DA-9 — Provenienza delle pagine (chi può toccare l'auto-fix).** *Risolta (2026-06-04):* le pagine
  prodotte dalla **tooling/agenti** (`wiki-keeper`, `record`/`distill`, `distill_artifact`) sono
  **generate** → l'auto-fix le può **aggiornare** e, se obsolete e non aggiornabili, **cancellare**
  (assistito, su diff revisionabile). Le pagine **curate a mano** (es. roadmap) sono **proposta-only**
  e **mai cancellate**. **Salvaguardia:** un intervento manuale su una pagina generata la **riclassifica
  come curata**. Pagine preesistenti prive di marcatore: **default curate**, con classificazione
  iniziale che marca come generate quelle prodotte dalla tooling (REQ-076/077/077b/077c/085/086).
  *(Resta come dettaglio di design l'euristica di classificazione iniziale — vedi DA-9-bis sotto.)*
- **DA-9-bis — Euristica di classificazione iniziale (design).** Con quale segnale si marcano le ~17
  pagine esistenti come generate vs curate (es. tracce in `log.md` di `record`/`distill`, o lista
  esplicita)? Default sicuro = curata; la roadmap è sempre curata.

### Risolte (lint semantico — Gruppo H)

Chiuse in elicitazione (2026-06-04) e codificate nei requisiti. Resta aperto solo il dettaglio di
**design** DA-9-bis (euristica di classificazione iniziale della provenienza).

- **DA-10 — Ampiezza del confronto col codice.** *Risolta (2026-06-04):* **baseline completo alla
  prima esecuzione**, poi **incrementale guidato da git** — si ri-verificano solo le pagine collegate
  alle **entità cambiate** nei commit intercorsi dall'ultimo lint (watermark git). Richiede watermark,
  mappa entità↔pagine e fallback completo se git/watermark mancano (REQ-087..091); sinergia con FEAT-009
  (D-6). *(Resta design: la granularità della mappa entità↔pagine e la gestione dei rename — R-M10.)*
- **DA-11 — Flusso/innesco dell'auto-fix.** *Risolta (2026-06-04):* l'auto-fix (e il lint semantico
  incrementale) è un **trigger pre-commit/pre-push** (e pre-PR) che scatta **a monte del
  `configuration-manager`**. Applica i fix alle pagine **generate** nella working tree, così entrano
  nello **stesso commit**; il commit/push lo fa poi il configuration-manager e tu rivedi nel **diff/PR**.
  È **veloce** perché incrementale (solo le entità nel change set) e **no-op** se il change set non
  tocca pagine; **saltato senza LLM** (REQ-079/088/092/093). *(Resta a DA-12 se un esito negativo
  **blocca** il commit/push o solo avvisa.)*
- **DA-12 — Gate semantico: blocca o avvisa?** *Risolta (2026-06-04):* **blocca sopra soglia** — il
  commit/push si interrompe se restano problemi aperti di severità ≥ soglia **configurabile**; quelli
  sotto soglia passano con **warning**. Esiste un **override esplicito e tracciato** per i casi limite.
  Cadenza = pre-commit/pre-push (DA-11), resa pratica dall'incrementalità (REQ-082/094/095).
- **DA-13 — Freschezza del corpus.** *Risolta (2026-06-04):* **re-index incrementale del change set
  prima** del confronto (git-driven, sinergia FEAT-009), così il codice di riferimento è corrente
  (entità + contesto). Fallback alla lettura della working tree con segnalazione se l'incrementale non
  è disponibile (REQ-096/097, D-7). Il **full re-index** resta fuori ambito.
- **DA-14 — Granularità della rilevazione "obsoleto".** *Risolta (2026-06-04):* **per affermazione/
  paragrafo** (claim) — l'issue identifica la frase specifica e l'auto-fix è chirurgico (diff minimi);
  costo sostenibile grazie all'incrementalità (REQ-098).
