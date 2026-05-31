# Requisiti — Skill: creare/indicizzare l'LLM Wiki
<!-- Deriva da: FEAT-003 -->

## 1. Contesto e problema (perché)

Un progetto software accumula, nel tempo, conoscenza che non risiede nel codice: decisioni
architetturali, il *perché* di una scelta, esperimenti condotti, fonti studiate, concetti
consolidati, log di sessione. Questa conoscenza è dispersa nelle conversazioni con l'agente
LLM, nelle note informali, nei messaggi di commit — e si perde o si ri-costruisce ogni volta
da zero.

Il **prototipo** ha già dimostrato in pratica due cose (fonte: `prototype/shared/loaders.py:59`,
funzione `load_docs`):
1. Un wiki in Markdown, strutturato con indice (`wiki/index.md`), log append-only
   (`wiki/log.md`), frontmatter YAML, backlink `[[...]]` e cartelle tematiche, può essere
   **ingerito nel corpus del RAG** come parte documentale — verificato nel dogfooding: le query
   `search_docs` restituiscono pagine del wiki (`wiki/syntheses/`, `wiki/log.md`, ecc.).
2. L'agente wiki-keeper (`.claude/agents/wiki-keeper.md`) mostra le **operazioni di
   manutenzione** (record, ingest, aggiornamento indice/log) che un attore automatico può
   compiere su questa struttura.

Il problema è che queste capacità non esistono come **componente production-grade
repo-agnostico**: sono cresciute organicamente su un singolo workspace. Quando un nuovo
progetto parte, non dispone di strumenti per:
- **Creare** la struttura wiki standardizzata da zero (directory, file fondamentali, convenzioni);
- **Documentare in continuo** (operazioni record/ingest) in modo programmatico e riproducibile;
- **Archiviare/distillare** conversazioni o sessioni nel wiki;
- **Indicizzare** il wiki risultante nel sistema RAG del progetto così che diventi parte del
  corpus documentale e sia interrogabile.

Senza questa skill, la conoscenza distillata (*il "perché"*, cfr. `wiki/syntheses/ruolo-wiki-da-w1.md`)
rimane separata dal RAG e non contribuisce alla qualità del retrieval.

---

## 2. Obiettivi e criteri di successo

Collegati direttamente a **CS-3** dell'epica (`requirements/sertor-core/epic.md §3`):
> *Il sistema può **creare/indicizzare** un LLM Wiki da un progetto e **mantenerlo** (rigenerazione
> indice + validazione link) in modo **idempotente** (re-run senza divergenze).*

I sotto-criteri misurabili per questa feature:

| ID | Criterio | Come si verifica |
|----|----------|-----------------|
| SC-3a | Dato un repository privo di wiki, la skill produce la struttura completa (`index.md`, `log.md`, cartelle tematiche) in un'unica invocazione. | Verifica automatica: presenza e conformità formale dei file generati. |
| SC-3b | Una seconda invocazione su un progetto già dotato di wiki non sovrascrive il contenuto esistente, non produce duplicati e lascia i file identici (idempotenza). | Hash dei file invariato tra la prima e la seconda esecuzione su input invariato. |
| SC-3c | Dopo l'operazione record/ingest su un wiki esistente, l'indice riflette le nuove pagine e il log contiene la nuova voce. | Controllo strutturale automatico su `index.md` e `log.md`. |
| SC-3d | Dato un wiki esistente e un indice RAG configurato, la skill (ri)indicizza il wiki e le pagine del wiki compaiono nei risultati di una query documentale pertinente. | Test di retrieval su query nota con corpus di verifica. |
| SC-3e | La skill funziona senza modifiche su almeno due repository diversi (portabilità repo-agnostica). | Esecuzione su il prototipo stesso + un secondo repo campione. |
| SC-3f | Dati un testo di conversazione/sessione e un wiki esistente, la skill produce una pagina di distillazione conforme alle convenzioni (frontmatter, sezione, backlink) e la appende al log. | Controllo strutturale automatico sulla pagina generata. |

---

## 3. Stakeholder e attori

| Attore | Ruolo rispetto a questa feature |
|--------|--------------------------------|
| **Owner/maintainer** | Invoca la skill per avviare e alimentare il wiki di un nuovo progetto; valida che il corpus RAG includa le pagine wiki. |
| **Agente LLM (es. Claude Code)** | Attore automatico principale: usa la skill per le operazioni record/ingest durante le sessioni di lavoro; interroga il RAG che include il wiki come corpus documentale. |
| **Agente wiki-keeper** | Attore automatico secondario: usa (in futuro) le primitive esposte dalla skill per operazioni di manutenzione puntuale (post-MVP, FEAT-007). |
| **Epica sertor-cli** | Consumatore a valle: chiama questa skill come capacità installabile/configurabile. |
| **Codebase target** | Il progetto su cui si crea il wiki; la skill deve essere indifferente alla sua struttura interna. |
| **Sistema RAG del progetto** | Consumatore del wiki come corpus: dopo l'indicizzazione, il wiki entra nel retrieval documentale (ruolo 3 di DA-W1, cfr. `wiki/syntheses/ruolo-wiki-da-w1.md`). |

---

## 4. Ambito

### In ambito

1. **Inizializzazione della struttura wiki**: creare le directory tematiche (`concepts/`, `tech/`,
   `experiments/`, `sources/`, `syntheses/`) e i file fondamentali (`index.md`, `log.md`) con
   contenuto iniziale conforme alle convenzioni del progetto.
2. **Convenzioni obbligatorie**: frontmatter YAML (campi `title`, `type`, `tags`, `created`,
   `updated`, `sources`) in ogni pagina nuova; wikilink `[[nome-pagina]]` per i backlink;
   naming kebab-case; struttura del log in voci `## [YYYY-MM-DD] <operazione> | <titolo>` con
   operazione ∈ {setup, ingest, record, query, lint}.
3. **Operazione record**: creare o aggiornare una pagina tematica a partire da un brief
   strutturato (attività/decisione), aggiornare `index.md` e appendere una voce a `log.md`.
4. **Operazione ingest**: incorporare una fonte esterna (riassunto) in una pagina `sources/`,
   propagare i riferimenti nelle pagine concetto/tech correlate, aggiornare `index.md` e `log.md`.
5. **Distillazione di conversazione/sessione**: dato un testo di conversazione (trascrizione o
   riassunto), produrre una pagina wiki conforme (tipicamente in `experiments/` o `syntheses/`)
   e registrarla nel log.
6. **Indicizzazione del wiki nel RAG**: dato un wiki esistente e un sistema RAG configurato,
   ingerire le pagine Markdown del wiki nel corpus documentale del RAG; supportare la
   reindicizzazione (update incremental o full rebuild) in modo idempotente.
7. **Idempotenza**: ogni operazione di creazione/reindicizzazione eseguita più volte sullo stesso
   input produce lo stesso risultato senza divergenze (niente duplicati di pagine, voci di log,
   o chunk nel vettore store).
8. **Repo-agnosticità**: la skill opera su qualunque repository target senza dipendere dalla
   struttura interna del progetto ospitante.
9. **Configurabilità**: il percorso radice del wiki e il sistema RAG di destinazione sono
   configurabili senza modificare il codice della skill.

### Fuori ambito

- **Superficie wiki-nativa** (ruoli 1 e 2 di DA-W1): query strutturata *"cosa abbiamo deciso
  su X"* con risposta a pagina intera + backlink; navigazione per indice/nome; lookup preciso
  non-semantico. Post-MVP (FEAT-007).
- **Meccanismo di iniezione del contesto** (hook SessionStart o equivalente): competenza
  dell'host (es. Claude Code), non di questa skill. La skill espone il wiki ben strutturato;
  l'host decide cosa iniettare (cfr. `wiki/tech/hook-sessionstart-wiki.md`).
- **Spider e lint automatici**: rilevazione orfani, validazione link, distillazione
  automatica di raw → concept. Post-MVP (FEAT-007).
- **Arricchimento bidirezionale Wiki ↔ RAG-sorgenti**: loop dove le pagine wiki generano nuove
  query sul RAG dei sorgenti e viceversa. Post-MVP (FEAT-008).
- **Priorità/boost nel ranking RAG**: il wiki è paritario agli altri chunk nel ranking semantico
  (decisione DA-W1, `requirements/sertor-core/epic.md §9`). Non si modellano meccanismi di
  prioritizzazione del ranking.
- **GUI o interfaccia web** per il wiki.
- **Versionamento/storicizzazione** interna delle pagine wiki (è responsabilità del VCS del
  progetto ospitante).
- **Traduzione automatica** dei contenuti del wiki.

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Inizializzazione della struttura wiki

**REQ-001 (Event-driven)**
*When the wiki-creation skill is invoked on a repository that has no wiki, the system shall
create the required directory structure (`concepts/`, `tech/`, `experiments/`, `sources/`,
`syntheses/`) and the two foundational files (`index.md`, `log.md`) with minimal valid
content.*
> Ancora: struttura osservata in `prototype/wiki/` e codificata in `.claude/agents/wiki-keeper.md`.

**REQ-002 (Unwanted behaviour)**
*If the target repository already contains a wiki with an existing `index.md` or `log.md`,
then the system shall not overwrite or truncate those files, and shall leave the pre-existing
content intact.*

**REQ-003 (Ubiquitous)**
*The system shall produce each new wiki page with a YAML frontmatter block containing at
minimum the fields `title`, `type`, `tags`, `created`, `updated`, and `sources`.*

**REQ-004 (Ubiquitous)**
*The system shall use `[[page-name]]` wikilinks for all cross-references between wiki pages.*

**REQ-005 (Ubiquitous)**
*The system shall name wiki files in kebab-case and place each file in the appropriate
thematic subdirectory (`concepts/`, `tech/`, `experiments/`, `sources/`, `syntheses/`)
according to the content type.*

**REQ-006 (Ubiquitous)**
*The system shall accept the wiki root path as a configurable parameter and shall not
hard-code any repository-specific path.*

### Gruppo B — Operazione record

**REQ-010 (Event-driven)**
*When a record operation is invoked with a brief (activity, decision, or concept), the system
shall create a new wiki page or update the existing one for that topic, without creating
duplicate pages for the same topic.*

**REQ-011 (Event-driven)**
*When a record operation completes, the system shall update `index.md` to include a link and
one-line summary for any newly added page.*

**REQ-012 (Event-driven)**
*When a record operation completes, the system shall append exactly one entry to `log.md` in
the format `## [YYYY-MM-DD] record | <title>`, with no modification to prior log entries.*

**REQ-013 (Unwanted behaviour)**
*If a record operation is invoked twice with identical input on an unchanged wiki, then the
system shall produce an output identical to the first run (no duplicate pages, no duplicate
log entries, no modified timestamps on unchanged files).*

### Gruppo C — Operazione ingest

**REQ-020 (Event-driven)**
*When an ingest operation is invoked with an external source (text or structured summary), the
system shall create or update a page in `sources/` containing the source summary, with
frontmatter including the original source reference.*

**REQ-021 (Event-driven)**
*When an ingest operation creates or updates a source page, the system shall propagate a
reference to that source in all directly related thematic pages (`concepts/`, `tech/`) that
already exist in the wiki.*

**REQ-022 (Event-driven)**
*When an ingest operation completes, the system shall update `index.md` and append one entry
to `log.md` with operation type `ingest`.*

**REQ-023 (Unwanted behaviour)**
*If an ingest operation encounters a source that contradicts a pre-existing wiki page, then
the system shall explicitly mark the contradiction in the affected page before updating it.*

### Gruppo D — Distillazione di conversazione/sessione

**REQ-030 (Event-driven)**
*When a distillation operation is invoked with a conversation or session text, the system shall
produce a wiki page that captures the key decisions, concepts, and outcomes from that input,
placed in the appropriate thematic directory.*

**REQ-031 (Event-driven)**
*When a distillation operation produces a new page, the system shall require a configured LLM
to extract and summarise the content; the operation shall be blocked and report an explicit
error if no LLM is configured.*

**REQ-032 (Event-driven)**
*When a distillation operation completes, the system shall update `index.md` and append one
entry to `log.md` with operation type `record`.*

**REQ-033 (Ubiquitous)**
*The system shall produce distilled pages that conform to the same structural conventions as
all other wiki pages (frontmatter, wikilinks, kebab-case filename, thematic placement).*

### Gruppo E — Indicizzazione nel RAG

**REQ-040 (Event-driven)**
*When the indexing operation is invoked, the system shall ingest all Markdown files found
under the configured wiki root path into the configured RAG corpus, associating each file with
metadata that identifies it as a wiki document (at minimum: `path`, `source: "doc"`,
`kind: "markdown"`).*
> Ancora: pattern già attivo nel corpus sertor — `prototype/shared/loaders.py:59-79`,
> `load_docs()`, dove `paths += sorted((root / "wiki").rglob("*.md"))`.

**REQ-041 (Event-driven)**
*When the indexing operation is invoked on a corpus that already contains wiki chunks, the
system shall update or replace those chunks without creating duplicate entries for the same
source file.*

**REQ-042 (State-driven)**
*While the RAG system is configured and reachable, the system shall complete the indexing
operation and confirm the number of wiki documents successfully ingested.*

**REQ-043 (Unwanted behaviour)**
*If the configured RAG system is unreachable or not configured, then the system shall abort
the indexing operation with an explicit, human-readable error message and shall not corrupt
any existing index state.*

**REQ-044 (Ubiquitous)**
*The system shall assign the same ranking weight to wiki chunks as to any other document
chunk in the RAG corpus (no semantic boost for wiki content).*
> Conforme alla decisione di autorità paritaria di DA-W1 (`requirements/sertor-core/epic.md §9`).

**REQ-045 (Unwanted behaviour)**
*If the wiki root path is empty or contains no Markdown files, then the system shall report a
warning and exit without modifying the RAG index.*

### Gruppo F — Idempotenza trasversale

**REQ-050 (Complex: event-driven + unwanted)**
*When any wiki operation (creation, record, ingest, distillation, indexing) is executed more
than once on an unchanged input, then the system shall produce an output identical to the
first execution, with no new files created, no log entries duplicated, and no index state
changed.*

**REQ-051 (Ubiquitous)**
*The system shall use the relative file path within the wiki as the stable identifier for each
wiki document across indexing runs, so that a re-index of an unchanged file does not generate
a new chunk identity.*
> Ancora: uso di `rel = p.relative_to(root).as_posix()` come `id` stabile in
> `prototype/shared/loaders.py:12-13` (`Doc.id`).

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| RNF-001 | **Portabilità** | La skill opera su qualunque repository target senza dipendere da un sistema operativo specifico o da percorsi hard-coded. |
| RNF-002 | **Testabilità** | Ogni operazione (creazione struttura, record, ingest, distillazione, indicizzazione) espone un'interfaccia verificabile automaticamente; è possibile eseguire i test su un wiki temporaneo senza effetti sul corpus di produzione. |
| RNF-003 | **Configurabilità** | Il percorso del wiki, il provider LLM (per le operazioni che lo richiedono) e il sistema RAG di destinazione sono configurabili tramite parametri o file di configurazione centralizzato, senza modificare il codice. |
| RNF-004 | **Osservabilità minima** | Ogni operazione emette log strutturati (almeno: operazione, file coinvolti, esito) che permettono di diagnosticare fallimenti senza accedere al codice sorgente. |
| RNF-005 | **Gestione esplicita degli errori** | Condizioni di errore prevedibili (RAG non configurato, wiki già esistente, file corrotto, LLM non disponibile) producono messaggi d'errore leggibili e non lasciano il sistema in uno stato parziale o inconsistente. |
| RNF-006 | **Isolamento delle dipendenze** | Le dipendenze specifiche della skill (es. librerie per la generazione LLM o per il vector store) non devono confliggere con quelle degli altri motori RAG del core, e devono poter essere installate in ambienti isolati. |
| RNF-007 | **Dimensione del payload** | Il corpus di pagine wiki indicizzato non deve imporre limiti artificiali al numero di pagine (la skill scala linealmente con il numero di file Markdown trovati sotto la radice wiki). |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli

- **Vincolo DA-W1**: il wiki è trattato come **corpus paritario** nel RAG; nessun meccanismo di
  boost semantico è in scope per questa feature (`requirements/sertor-core/epic.md §9`).
- **Vincolo DA-2**: l'MVP del wiki si limita a creazione e indicizzazione; la manutenzione
  automatica (spider/lint) è esclusa da questo documento (`epic.md §9`, FEAT-007).
- **Segreti**: nessun segreto (chiavi API, credenziali) viene persistito in file versionati;
  la configurazione sensibile transita esclusivamente tramite variabili d'ambiente o file `.env`
  non committati (`REQ-E5` dell'epica).
- **LLM condizionale**: il provider LLM è necessario **solo** per le operazioni che richiedono
  generazione (distillazione, REQ-031); le operazioni strutturali (creazione, record manuale,
  indicizzazione) non devono richiedere un LLM configurato.
- **Dipendenza dal nucleo condiviso (FEAT-001)**: l'indicizzazione del wiki nel RAG
  (Gruppo E) dipende dalla disponibilità del nucleo di retrieval condiviso (ingestione,
  chunking, embeddings, vector store). Questa feature può essere sviluppata e testata in
  isolamento per le operazioni strutturali (Gruppi A–D), ma l'integrazione completa richiede
  FEAT-001.

### Assunzioni

- Il repository target dispone di un filesystem accessibile in lettura/scrittura nella
  directory radice dove viene creato il wiki.
- Le pagine wiki sono scritte in Markdown (`.md`); altri formati sono fuori ambito.
- Il testo di conversazione/sessione fornito all'operazione di distillazione è in lingua
  comprensibile dal LLM configurato (nessun requisito di traduzione in scope).
- La struttura wiki (`concepts/`, `tech/`, `experiments/`, `sources/`, `syntheses/`,
  `index.md`, `log.md`) è quella definita nel CLAUDE.md del workspace e mostrata nel
  prototipo (`prototype/wiki/`); non si prevede personalizzazione strutturale nell'MVP.

### Dipendenze

| Dipendenza | Tipo | Note |
|------------|------|------|
| **FEAT-001** (nucleo retrieval condiviso) | Funzionale (parziale) | Richiesta per il Gruppo E (indicizzazione RAG); i Gruppi A–D sono sviluppabili in isolamento. |
| **REQ-E3** (epica, LLM obbligatorio per generazione) | Architetturale | Solo per REQ-031 (distillazione); le altre operazioni sono LLM-free. |
| **Provider LLM configurato** | Runtime condizionale | Obbligatorio per distillazione; opzionale per il resto. |
| **Sistema RAG configurato** | Runtime condizionale | Obbligatorio per Gruppo E; non richiesto per Gruppi A–D. |

---

## 8. Rischi

| ID | Rischio | Probabilità | Impatto | Mitigazione |
|----|---------|-------------|---------|-------------|
| R-W1 | **Drift struttura wiki**: la struttura attesa dalla skill (nomi cartelle, convenzioni frontmatter) diverge da quella usata organicamente nel workspace corrente, causando incompatibilità. | Media | Alto | Specificare le convenzioni come requisiti espliciti (§5 Gruppo A) e validarle su un wiki di test ricavato da `prototype/wiki/`. |
| R-W2 | **Idempotenza non garantita per la distillazione**: la generazione LLM produce output non deterministici, rendendo difficile garantire che una seconda distillazione sullo stesso input non produca una pagina diversa. | Alta | Medio | Modellare l'idempotenza come proprietà della *struttura* (nessun duplicato di pagina/log) piuttosto che del *contenuto* generato; accettare che contenuti distillati possano variare tra run se il file non esiste ancora. |
| R-W3 | **Dimensione crescente dell'indice RAG**: un wiki molto grande (centinaia di pagine) può rallentare la reindicizzazione o saturare il vector store in configurazione locale. | Bassa | Medio | Richiedere (RNF-007) che la skill scala linearmente; limitare la scope dell'MVP a wiki di dimensioni ragionevoli (< 500 pagine); rimandare ottimizzazioni (batch, incremental) a iterazioni successive. |
| R-W4 | **Dipendenza da FEAT-001 non ancora disponibile**: se il nucleo retrieval condiviso non è pronto, il Gruppo E (indicizzazione) è bloccato, ritardando il criterio CS-3d. | Media | Medio | I Gruppi A–D (struttura, record, ingest, distillazione) sono sviluppabili e dimostrabili in isolamento; pianificare l'integrazione con FEAT-001 come task separato. |
| R-W5 | **Contaminazione del wiki di produzione durante i test**: eseguire test di idempotenza sul wiki reale del workspace può alterarne i contenuti. | Media | Alto | Richiedere (RNF-002) che i test operino su un wiki temporaneo/sandbox completamente isolato dal corpus di produzione. |

---

## 9. Prioritizzazione (MoSCoW)

| Gruppo | Requisiti | MoSCoW | Motivazione |
|--------|-----------|---------|-------------|
| A — Inizializzazione struttura | REQ-001…REQ-006 | **Must** | Prerequisito di tutto il resto; senza struttura non si può operare né indicizzare. |
| B — Operazione record | REQ-010…REQ-013 | **Must** | Operazione fondamentale per documentare in continuo; costituisce il flusso minimo del wiki-keeper. |
| C — Operazione ingest | REQ-020…REQ-023 | **Should** | Aggiunge valore significativo ma l'MVP può funzionare con il solo record; l'ingest di fonti esterne è un caso d'uso meno frequente. |
| D — Distillazione conversazione | REQ-030…REQ-033 | **Should** | Capacità di alto valore (archiviare sessioni), ma dipende dal LLM ed è più complessa da rendere idempotente; implementabile subito dopo i Must. |
| E — Indicizzazione RAG | REQ-040…REQ-045 | **Must** | È il requisito core di FEAT-003 secondo DA-W1: *creare + indicizzare nel RAG* è la definizione stessa del confine MVP. Dipende da FEAT-001. |
| F — Idempotenza trasversale | REQ-050…REQ-051 | **Must** | CS-3 la cita esplicitamente; senza idempotenza il wiki diverge e degrada la qualità del RAG (R-2 epica). |

> **Sequenza consigliata per l'MVP**: Gruppo A → Gruppo B → Gruppo F → Gruppo E (subordinato a
> FEAT-001) → Gruppi C e D in parallelo come secondo incremento.

---

## 10. Domande aperte

**[DA CHIARIRE: DA-W2]** Le operazioni record e ingest (Gruppi B e C) devono essere invocabili
solo da un agente LLM (che costruisce il brief), o anche direttamente da un umano tramite
interfaccia testuale/CLI? Questo influenza se il formato del brief è strutturato (es. JSON/YAML)
o in linguaggio naturale.

**[DA CHIARIRE: DA-W3]** L'operazione di distillazione (Gruppo D) deve operare su **trascrizioni
intere di conversazione** (potenzialmente molto lunghe) o su **riassunti già prodotti**
dall'agente chiamante? La risposta determina se la skill deve gestire la suddivisione/chunking
del testo in ingresso prima di passarlo al LLM, o se può assumere che l'input sia già
pre-elaborato a dimensioni gestibili.

**[DA CHIARIRE: DA-W4]** La reindicizzazione RAG del wiki (Gruppo E, REQ-041) deve essere
**incrementale** (reindicizza solo i file modificati dall'ultimo run) o **full rebuild** (ogni
run reindicizza tutto)? L'incrementale è preferibile per wiki grandi ma richiede un meccanismo
di tracciamento delle modifiche (es. hash o timestamp); il full rebuild è più semplice e
naturalmente idempotente. La scelta impatta FEAT-001.

**[DA CHIARIRE: DA-W5]** Il campo `sources` del frontmatter YAML (REQ-003) deve contenere
**riferimenti formali** (es. URI, path file) o **etichette libere** in linguaggio naturale?
La risposta determina se l'ingest (REQ-020) può popolare automaticamente questo campo in modo
verificabile.

**[DA CHIARIRE: DA-W6]** La struttura delle cartelle tematiche (`concepts/`, `tech/`,
`experiments/`, `sources/`, `syntheses/`) deve essere **fissa** (come nel prototipo e in
`CLAUDE.md`) o **configurabile per progetto**? Nell'MVP si assume fissa (§7 Assunzioni), ma
un progetto diverso potrebbe avere esigenze diverse.
