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
- **Lint**: validazione dei wikilink (link rotti verso pagine inesistenti), rilevazione **pagine orfane**, segnalazione di pagine presenti su disco ma assenti dall'indice; **report strutturato, non distruttivo**.
- **Rigenerazione dell'indice**: ricostruzione/aggiornamento del catalogo di `index.md` (link + sommario per pagina), **idempotente** e **non distruttiva** del contenuto curato a mano.
- **Contraddizioni**: elenco delle pagine con marcatori di contraddizione; (opzionale, con LLM) segnalazione di contraddizioni semantiche.
- **Distillazione raw→concept** (con LLM): da una sorgente in `raw/`, produrre/aggiornare una pagina concept conforme alle convenzioni.
- **Idempotenza** trasversale; **repo-agnosticità** e **configurabilità** (path del wiki); **osservabilità** (log strutturati).

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
- **A-3**: La distillazione riceve una **sorgente già leggibile** in `raw/`; non gestisce crawling esterno né formati binari (coerente con DA-W3 di FEAT-003).

### Dipendenze
- **D-1**: **FEAT-003** (convenzioni e struttura del wiki, marcatori di contraddizione) — in `master`.
- **D-2**: Porta **`LLMProvider`** del core — solo per distillazione e contraddizioni semantiche.

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
| **Must** | REQ-001..005 (lint+report), REQ-040/041 (idempotenza), REQ-050/051/052 (config/osservabilità/report) | Il valore centrale: verificare il wiki in modo non distruttivo e diagnosticabile. |
| **Should** | REQ-010..013 (rigenera indice), REQ-020 (contraddizioni marcate) | Mantiene l'indice allineato e segnala contraddizioni note; deterministico, LLM-free. |
| **Could** | REQ-030..033 (distillazione raw→concept), REQ-021/022 (contraddizioni semantiche) | Alto valore ma LLM-dipendenti e non deterministici; dopo i deterministici. |
| **Won't (ora)** | Auto-fix dei link rotti; crawling esterno; arricchimento Wiki↔RAG (FEAT-008) | Fuori ambito / altre feature. |

---

## 10. Domande aperte

- **DA-1 — Strategia di rigenerazione di `index.md`.** Sezione **gestita tra marcatori**
  (es. `<!-- sertor:catalog -->` … `<!-- /sertor:catalog -->`, si rigenera solo quel blocco) **vs**
  ricostruzione dell'intero blocco "## Pagine". *Direzione proposta:* **marcatori** (preserva il
  curato, non distruttivo, idempotente). Da confermare in design.
- **DA-2 — Contraddizioni: euristiche vs LLM.** *Direzione:* MVP = solo **marcatori espliciti**
  (deterministico); contraddizioni **semantiche** opt-in con LLM (Could). Da confermare.
- **DA-3 — Distillazione raw→concept: MVP o post-MVP?** *Direzione:* **post-MVP / Could** (dipende
  da LLM, non deterministica, e `raw/` è vendored): prima i deterministici (lint + indice). Da confermare.
- **DA-4 — Lint: solo-report vs auto-fix.** *Direzione:* **solo report**; l'unica scrittura "fix" è
  la **rigenerazione dell'indice** (operazione separata, esplicita, sicura, idempotente). Niente
  auto-fix dei link. Da confermare.
- **DA-5 — Definizione di "referenziato" per gli orfani.** Solo wikilink `[[...]]`? anche link
  Markdown `[..](..)`? l'indice conta? *Direzione:* referenziato = compare in `index.md` **o** in un
  wikilink di un'altra pagina; `index.md`/`log.md` esenti. Da confermare.
- **DA-6 — Superficie d'invocazione.** Operazioni come funzioni di libreria e/o sottocomandi della
  CLL (`sertor wiki lint` / `wiki reindex` / `wiki distill`)? *Direzione:* libreria nel core +
  (eventuale) esposizione CLI in una feature CLI successiva. Da confermare in design.
