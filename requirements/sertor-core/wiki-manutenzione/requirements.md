# Requisiti — Skill: mantenere il wiki vivo (lint / indice / distillazione)
<!-- Deriva da: FEAT-007 -->

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
- **Idempotenza** trasversale; **repo-agnosticità** e **configurabilità** (path del wiki); **osservabilità** (log strutturati).

> **Sorgenti "raw" (definizione estesa).** Non solo i file in `raw/` (discussioni, note), ma anche
> **gli artifact del progetto**: `requirements/**` (epic + requisiti EARS), `specs/**`
> (spec/plan/tasks/contracts/research/quickstart) e `.specify/memory/constitution.md`. Il wiki li
> **distilla** in documentazione narrativa e vi **rimanda** per il dettaglio.

### Fuori ambito
- **Creazione struttura, record, ingest** (è FEAT-003).
- **Indicizzazione del wiki nel RAG** (FEAT-003, Gruppo E).
- **Arricchimento bidirezionale Wiki↔RAG** (FEAT-008).
- **Auto-correzione dei link rotti** o riscrittura semantica delle pagine (il lint **segnala**, non ripara, salvo la rigenerazione dell'indice che è un'operazione esplicita e sicura).
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

**REQ-005 (Unwanted behaviour)** *If a lint operation runs, then the system shall NOT modify, create
or delete any wiki file (sola lettura); le correzioni sono operazioni separate ed esplicite.*

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

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| NFR-01 | **Non distruttività** | Lint è sola lettura; index-rebuild preserva il contenuto curato a mano; distill non sovrascrive pagine invariate (Principio IV/VI). |
| NFR-02 | **Idempotenza** | Re-run su wiki invariato → esito identico (hash file invariati). |
| NFR-03 | **Testabilità** | Ogni operazione testabile su un **wiki sandbox temporaneo** (mai sul wiki di produzione); distillazione/contraddizioni semantiche con LLM **mock**. |
| NFR-04 | **Isolamento dell'LLM** | Solo distillazione e contraddizioni semantiche richiedono un LLM; lint, orfani e index-rebuild sono **LLM-free**. |
| NFR-05 | **Portabilità** | Funziona su Linux e Windows senza modifiche. |
| NFR-06 | **Osservabilità** | Log strutturati per ogni operazione (Principio IX). |
| NFR-07 | **Performance** | Scala linearmente col numero di pagine; nessun limite artificiale. |

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

### Dipendenze
- **D-1**: **FEAT-003** (convenzioni e struttura del wiki, marcatori di contraddizione) — in `master`.
- **D-2**: Porta **`LLMProvider`** del core — per la distillazione documentale (ruolo prioritario) e le contraddizioni semantiche.
- **D-3**: Gli **artifact** `requirements/**`, `specs/**`, `.specify/memory/constitution.md` come sorgenti della documentazione (in repo, versionati).

---

## 8. Rischi

| ID | Rischio | Prob. | Impatto | Mitigazione |
|----|---------|-------|---------|-------------|
| R-M1 | **Rigenerazione indice distruttiva**: sovrascrive contenuto curato a mano. | Media | Alto | REQ-011 + DA-1 (sezione gestita tra marcatori); test su sandbox. |
| R-M2 | **Falsi positivi orfani** (es. pagine linkate solo da link Markdown, o index/log). | Media | Medio | DA-5 (definizione precisa di "referenziato"); index.md/log.md esenti (REQ-003). |
| R-M3 | **Non determinismo LLM** in distill/contraddizioni semantiche. | Alta | Medio | Idempotenza **strutturale** (REQ-033); contraddizioni semantiche come Could/opzionali. |
| R-M4 | **Qualità contraddizioni semantiche** bassa (rumore). | Media | Medio | MVP solo marcatori espliciti; semantico opt-in con LLM (DA-2). |
| R-M5 | **Contaminazione del wiki di produzione** durante i test. | Media | Alto | NFR-03: test su wiki temporaneo isolato. |

---

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivazione |
|----------|-----------|-------------|
| **Must** | REQ-001..005 (lint+report), REQ-040/041 (idempotenza), REQ-050..052 (config/osservabilità/report), **REQ-060/061/062 (wiki = documentazione ufficiale: ruolo, sorgenti incl. artifact, link-non-duplica)**, REQ-064 (report coperture mancanti, LLM-free) | Valore centrale: il wiki **è** la documentazione ufficiale, mantenuta coerente e diagnosticabile in modo non distruttivo. |
| **Should** | REQ-010..013 (rigenera indice), REQ-020 (contraddizioni marcate), **REQ-030..033 + REQ-063/065 (distillazione documentale da artifact/discussioni, con LLM)** | Mantiene l'indice allineato e **alimenta la documentazione ufficiale** (prioritaria) distillando gli artifact; richiede LLM. |
| **Could** | REQ-021/022 (contraddizioni **semantiche** con LLM) | Alto valore ma LLM-dipendente e rumoroso; dopo il resto. |
| **Won't (ora)** | Auto-fix dei link rotti; crawling esterno; arricchimento Wiki↔RAG (FEAT-008) | Fuori ambito / altre feature. |

---

## 10. Domande aperte

- **DA-1 — Strategia di rigenerazione di `index.md`.** Sezione **gestita tra marcatori**
  (es. `<!-- sertor:catalog -->` … `<!-- /sertor:catalog -->`, si rigenera solo quel blocco) **vs**
  ricostruzione dell'intero blocco "## Pagine". *Direzione proposta:* **marcatori** (preserva il
  curato, non distruttivo, idempotente). Da confermare in design.
- **DA-2 — Contraddizioni: euristiche vs LLM.** *Direzione:* MVP = solo **marcatori espliciti**
  (deterministico); contraddizioni **semantiche** opt-in con LLM (Could). Da confermare.
- **DA-3 — Distillazione documentale: portata.** *Aggiornata (ruolo prioritario):* la distillazione
  che alimenta la **documentazione ufficiale** (da artifact + discussioni) è **in ambito e Should**
  (non più post-MVP); richiede LLM (REQ-065). Resta da confermare **quanto** è automatica vs assistita.
- **DA-7 — Modello di contenuto della documentazione ufficiale.** Quale tassonomia/granularità per
  entità di business, funzionalità, decisioni, architettura (es. una pagina per entità? una per
  feature? una pagina-architettura unica?) e **come** il lint verifica la "copertura" (euristica su
  cartelle/tag attesi vs check esplicito). *Direzione proposta:* cartelle tematiche dedicate
  (es. `concepts/` per entità, `syntheses/` per architettura/decisioni) + copertura verificata su un
  set atteso configurabile. Da confermare in design.
- **DA-4 — Lint: solo-report vs auto-fix.** *Direzione:* **solo report**; l'unica scrittura "fix" è
  la **rigenerazione dell'indice** (operazione separata, esplicita, sicura, idempotente). Niente
  auto-fix dei link. Da confermare.
- **DA-5 — Definizione di "referenziato" per gli orfani.** Solo wikilink `[[...]]`? anche link
  Markdown `[..](..)`? l'indice conta? *Direzione:* referenziato = compare in `index.md` **o** in un
  wikilink di un'altra pagina; `index.md`/`log.md` esenti. Da confermare.
- **DA-6 — Superficie d'invocazione.** Operazioni come funzioni di libreria e/o sottocomandi della
  CLL (`sertor wiki lint` / `wiki reindex` / `wiki distill`)? *Direzione:* libreria nel core +
  (eventuale) esposizione CLI in una feature CLI successiva. Da confermare in design.
