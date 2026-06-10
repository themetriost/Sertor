# Requisiti — LLM Wiki (creazione + end-to-end) — consolidato FEAT-003 ⊕ FEAT-010

<!-- Deriva da: FEAT-003 (assorbito) + FEAT-010 (autorità e2e) -->

---

## Stato e nota di consolidamento

**Stato: in progress**

> **NOTA DI CONSOLIDAMENTO** — Questo documento consolida FEAT-010 (LLM Wiki end-to-end) dentro
> FEAT-003. In caso di conflitto prevale FEAT-010. FEAT-003 è assorbito come storico (D-10 di
> FEAT-010). Consolidato il 2026-06-05.
>
> FEAT-010 (`spec/005-llm-wiki:requirements/sertor-core/llm-wiki/requirements.md`) era in stato
> **READY — approvato per il design** (iterazione 13; tutti i temi T0–T7 risolti, 2026-06-04).

> ⛔ **RIMOZIONE PER DESIGN (2026-06-09)** — Le convenzioni a cartelle d'input **`manual_edited/`** e
> **`ingested_sources/`** sono **eliminate dallo scope** (semplificazione; allinea il piano alla realtà,
> dove il wiki ha già consolidato tutto in `sources/`). **Modello risultante:** le fonti esterne tornano
> a `sources/` (riassunti, semantica Karpathy originale); l'autoring umano avviene nelle pagine normali
> del wiki (nessuna cartella-input immutabile); il retrieval si semplifica (indicizzato = wiki generato +
> codice, nessuna cartella-input da escludere). **Autorità sul "perché"** = discussioni/SpecKit (non più
> `manual_edited`). Dettaglio normativo e impatto: **D-18** (§12). Voci marcate `⛔ DELETED BY DESIGN`
> sotto: D-1, D-6, D-11; semplificate: D-7, D-4, D-5, D-9; FR-007/015/016/020/021/030/031 eliminate,
> FR-001/009/012/013/017/022/023 riformulate; SC-002 obsoleto, SC-010 riformulato; R-06 decaduto.

---

## Tabella di tracciabilità (FEAT-003 → consolidato)

| Gruppo FEAT-003 | ID FEAT-003 | Esito nel consolidato |
|---|---|---|
| A — Inizializzazione struttura | REQ-001..006 | **Assorbito invariato** (FEAT-010 D-10) |
| B — Operazione record | REQ-010..013 | **Assorbito invariato** (FEAT-010 D-10) |
| C — Operazione ingest | REQ-020..023 | **Riattivato (2026-06-09, D-18)**: l'override FR-030/FR-031 è stato rimosso per design; torna operativa la semantica Karpathy (ingest scrive un riassunto in `sources/`) |
| D — Distillazione | REQ-030..033 | **Assorbito invariato** (FEAT-010 D-10) |
| E — Indicizzazione RAG | REQ-040..045 | **Superato** da FR-008..011, FR-023/024 (FEAT-010 D-3/D-7); il modello cambia: collezioni separate, query congiunta, scope retrieval = wiki generato + codice |
| F — Idempotenza trasversale | REQ-050..051 | **Assorbito invariato** (FEAT-010 D-10, SC-006) |
| *(net-new FEAT-010)* | FR-001..042 | **Aggiunto** integralmente (vedere §5) |

---

## 1. Visione (perché)

Portare capacità RAG su qualunque repository in modo riproducibile, con **una sola verità
interrogabile**: i sorgenti (il *come*) e la documentazione/wiki (il *perché*) coesistono nello
stesso corpus; la documentazione nuova vive **accanto ai sorgenti** tramite l'**LLM Wiki**. L'LLM
Wiki deve funzionare **end-to-end**: dalla produzione del contenuto (manuale e automatica) alla
manutenzione, all'indicizzazione, fino all'interrogazione. Il **codice è una fonte opzionale**: LLM
Wiki + RAG vale anche per **progetti senza codice** (D-9).

Il problema originale di FEAT-003, ancora valido: la conoscenza dispersa nelle conversazioni con
l'agente LLM, nelle note informali e nei messaggi di commit si perde o si ri-costruisce ogni volta
da zero. Le capacità wiki cresciute organicamente nel workspace non esistono come **componente
production-grade repo-agnostico**. Questo documento specifica il *cosa* e il *perché* per
costruirle end-to-end.

---

## 2. Modello di riferimento — l'LLM Wiki di Karpathy

> **Fonte primaria**: gist `karpathy/llm-wiki.md` (4 apr 2026,
> <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>). Il nostro wiki si ispira a
> questo pattern; lo riportiamo qui come **riferimento normativo** per il design e2e.

**Idea centrale (vs RAG classico).** Invece di ri-scoprire la conoscenza a ogni query (il RAG
recupera chunk grezzi ogni volta, senza accumulo), l'LLM **costruisce e mantiene un wiki
persistente** — un insieme strutturato e interconnesso di file `.md` che sta **tra l'utente e le
fonti grezze**. La conoscenza è **compilata una volta e tenuta aggiornata**, non riderivata a ogni
domanda: i cross-reference ci sono già, le contraddizioni sono già state segnalate.

**Tre livelli.**
1. **Fonti grezze (raw)** — documenti **immutabili** (articoli, paper, immagini). L'LLM le **legge
   ma non le modifica mai**: sono la *source of truth*.
2. **Il wiki** — directory di `.md` **interamente di proprietà dell'LLM** (le scrive e mantiene lui).
3. **Lo schema** — documento di configurazione (es. `CLAUDE.md`) che definisce struttura, convenzioni
   e workflow (ingest / query / maintenance). È volutamente astratto: l'agente lo **co-evolve** con
   l'utente.

**File chiave.**
- `index.md` — **catalogo** di tutto: ogni pagina con link + sommario di una riga (+ metadati).
  L'LLM lo legge **per primo** per trovare le pagine rilevanti. Aggiornato a ogni ingest.
- `log.md` — registro **append-only** cronologico (ingest/query/lint), formato
  `## [YYYY-MM-DD] ingest | Titolo` (parsabile).
- **Pagine** — `.md` con **wikilink** `[[...]]`, cross-reference, **frontmatter** (tag, date,
  conteggio fonti). Tipi: entità, concetti, fonti, confronti, sintesi.

**Operazioni / workflow.**
- **Ingest** — l'utente mette una fonte nel raw e chiede di processarla; l'LLM legge, discute i
  takeaway, scrive una pagina-sommario, **aggiorna l'indice**, aggiorna le pagine entità/concetti
  collegate, appende al log. *Una sola fonte può toccare 10–15 pagine.*
- **Query** — l'LLM cerca via indice, legge, sintetizza **con citazioni**. **Punto chiave:** le buone
  risposte vanno **rifilate nel wiki come nuove pagine** (non disperse nella chat).
- **Lint** — health-check periodico: contraddizioni tra pagine, claim superate, pagine orfane,
  concetti senza pagina, cross-reference mancanti, lacune di dati.

**Principi.**
- **Immutabilità delle fonti grezze** (source of truth, mai modificata).
- **Separazione dei ruoli**: l'umano fa *sourcing, esplorazione e domande giuste*; l'LLM fa
  **tutto il lavoro ingrato** (riassumere, cross-referenziare, archiviare, bookkeeping).
- **Manutenzione a costo ~zero**: il costo non è leggere/pensare ma il *bookkeeping*; l'LLM non si
  annoia, non dimentica un cross-reference, tocca 15 file in un colpo.
- **Pagine self-contained**: scritte perché un agente *single-shot* le riprenda senza contesto di
  chat.

**Mappatura su Sertor.**
- Le convenzioni di Sertor (`index.md` + `log.md`, frontmatter, wikilink, wiki come repo git) sono
  **allineate** al pattern Karpathy.
- Le primitive `create_wiki`/`record`/`ingest`/`distill`/`index_wiki` **esistono** (FEAT-003 storico)
  ma **non sono ancora orchestrate** da un loop agentico (manca il volante) — è il gap che **D-2**
  colma.
- Sertor punta a interrogare wiki **+ codice insieme** tramite **collezioni separate** interrogate
  congiuntamente (D-3): estensione del pattern.
- Per Sertor la *source of truth* è **stratificata** (D-4): **codice/test** per il comportamento,
  **discussioni/SpecKit** per il perché. *(2026-06-09, D-18: rimosso `manual_edited`.)*

---

## 3. Glossario

- **Layer A — Governance (Claude Code)**: hook `SessionStart` (lettura stato), comando `/wiki`
  (manuale), agente `wiki-keeper` (su delega). Oggi **scrive i Markdown a mano**.
- **Layer B — Prodotto Sertor (FEAT-003 storico)**: libreria `sertor_core.wiki`
  (`create_wiki`/`record`/`ingest`/`distill`/`index_wiki`) + CLI `sertor wiki index`.
- **Layer agentico**: skill + hook che **orchestrano** il Layer B e ne colmano i gap; è il "volante"
  che unisce i due layer (D-2).
- **Wiki generato**: le cartelle `concepts/`, `tech/`, `experiments/`, `syntheses/` + `index.md`,
  `log.md` — scritti e mantenuti dall'automazione.
- ~~**manual_edited/**~~ · ~~**ingested_sources/**~~ — ⛔ **DELETED BY DESIGN (2026-06-09, D-18)**: le
  due cartelle-input sono eliminate. Le fonti esterne sono riassunte in **`sources/`** (ingest, pattern
  Karpathy); l'autoring umano avviene nelle pagine normali del wiki.
- **sources/**: pagine-riassunto delle fonti esterne ingerite (semantica Karpathy; output dell'ingest).
- **Verità stratificata**: codice+test = autorità sul comportamento; discussioni/SpecKit = autorità
  sul perché.

---

## 4. Stakeholder e attori

| Attore | Ruolo rispetto a questa feature |
|--------|--------------------------------|
| **Owner/maintainer** | Invoca la skill per avviare e alimentare il wiki di un nuovo progetto; valida che il corpus RAG includa le pagine wiki. |
| **Agente LLM (es. Claude Code)** | Attore automatico principale: usa la skill per le operazioni record/ingest durante le sessioni; interroga il RAG che include il wiki come corpus documentale. |
| **Agente wiki-keeper** | Attore automatico secondario: usa le primitive della skill per operazioni di manutenzione puntuale. |
| **configuration-manager** | Componente di versioning; per il wiki **fornisce il diff** dell'ultimo commit alla parte D. *(2026-06-09, D-19: non invoca più la generazione — trigger manuale `/wiki`.)* |
| **Epica sertor-cli** | Consumatore a valle: chiama questa skill come capacità installabile/configurabile. |
| **Codebase target** | Il progetto su cui si crea il wiki; la skill deve essere indifferente alla sua struttura interna. |
| **Sistema RAG del progetto** | Consumatore del wiki come corpus: dopo l'indicizzazione, il wiki entra nel retrieval documentale (DA-W1). |

---

## 5. Ambito

### In ambito

1. Generazione/manutenzione **agentica** del wiki (skill che riusa FEAT-003 come primitive), invocata
   via **`/wiki`** (incrementale sul changeset dell'ultimo commit, D-19), **on-demand** e **periodica**.
2. **Ingest** di documentazione esterna → **riassunto in `sources/`** (creazione/on-demand/update).
   *(2026-06-09, D-18: era "import in `ingested_sources/`".)*
3. **Inizializzazione della struttura wiki**: directory tematiche e file fondamentali con contenuto
   iniziale conforme alle convenzioni.
4. **Convenzioni obbligatorie**: frontmatter YAML, wikilink `[[nome-pagina]]`, naming kebab-case,
   struttura log in voci `## [YYYY-MM-DD] <operazione> | <titolo>`.
5. **Operazione record**: creare o aggiornare una pagina tematica a partire da un brief strutturato.
6. **Distillazione di conversazione/sessione**: dato un brief condensato, produrre una pagina wiki
   conforme e registrarla nel log.
7. **Manutenzione**: lint strutturale (link rotti, orfani, copertura/cross-ref) + verifica di
   freschezza.
8. ~~**Gate al commit** human-in-the-loop~~ — ⛔ **DELETED BY DESIGN (2026-06-09, D-20)**: lint/freschezza restano come report non bloccante di `/wiki`.
9. **Retrieval** via RAG su **collezioni separate** wiki/codice (query congiunta).
10. **Superfici**: skill (primaria) + CLI + MCP; comando di **setup** `sertor wiki init`.
11. ~~Convenzione **`manual_edited/`**~~ — ⛔ **DELETED BY DESIGN (2026-06-09, D-18)**.
12. Funzionamento anche su **progetti senza codice**.
13. **Idempotenza**: ogni operazione di creazione/reindicizzazione eseguita più volte sullo stesso
    input produce lo stesso risultato senza divergenze.
14. **Repo-agnosticità**: la skill opera su qualunque repository target senza dipendere dalla
    struttura interna del progetto ospitante.

### Fuori ambito

- **Superficie wiki-nativa dedicata**: query a pagina intera, navigazione UI; si usa RAG + Obsidian/
  editor (D-13).
- **Arricchimento bidirezionale Wiki↔RAG** (loop wiki→query→wiki): futura FEAT-008.
- **Re-index full del corpus** da zero: capacità del nucleo/CLI; qui si usa l'incrementale.
- **GUI/interfaccia web** del wiki.
- **Traduzione automatica** dei contenuti.
- **Chunking di trascrizioni grezze**: la distillazione riceve input già condensato (DA-W3 risolta).
- **Priorità/boost nel ranking RAG**: il wiki è paritario agli altri chunk nel ranking semantico
  (DA-W1).
- **Versionamento/storicizzazione interna** delle pagine wiki (responsabilità del VCS del progetto).
- **Meccanismo di iniezione del contesto** (hook SessionStart o equivalente): competenza dell'host,
  non di questa skill.

---

## 6. Requisiti funzionali (EARS)

### Gruppo A — Inizializzazione della struttura wiki
*(assorbito invariato da FEAT-003; FEAT-010 D-10)*

**REQ-001 (Event-driven)**
*When the wiki-creation skill is invoked on a repository that has no wiki, the system shall
create the required directory structure (`concepts/`, `tech/`, `experiments/`, `syntheses/`) and
the two foundational files (`index.md`, `log.md`) with minimal valid content.*
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
thematic subdirectory (`concepts/`, `tech/`, `experiments/`, `syntheses/`) according to the
content type.*

**REQ-006 (Ubiquitous)**
*The system shall accept the wiki root path as a configurable parameter and shall not
hard-code any repository-specific path.*

### Gruppo B — Operazione record
*(assorbito invariato da FEAT-003; FEAT-010 D-10)*

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
*(superato da FR-030/FR-031; la semantica è ridefinita da FEAT-010 D-11)*

> **NOTA (aggiornata 2026-06-09, D-18)**: L'override di FEAT-010 (FR-030/031, ingest→`ingested_sources/`)
> è stato **rimosso per design**. Torna quindi **operativa** la semantica originale del Gruppo C:
> **l'ingest scrive un riassunto in `sources/`** (pattern Karpathy). REQ-020..023 sono di nuovo
> normativi.

### Gruppo D — Distillazione di conversazione/sessione
*(assorbito invariato da FEAT-003; FEAT-010 D-10)*

**REQ-030 (Event-driven)**
*When a distillation operation is invoked with a condensed brief/summary of a conversation or
session (not a raw transcript), the system shall produce a wiki page that captures the key
decisions, concepts, and outcomes from that input, placed in the appropriate thematic
directory.*
> Nota: l'input è già pre-elaborato dall'agente chiamante; la suddivisione/chunking di trascrizioni
> grezze è fuori ambito MVP (DA-W3 risolta).

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
*(superato da FR-008..011, FR-023/024; vedi FEAT-010 D-3/D-7)*

> **NOTA**: Il Gruppo E di FEAT-003 (REQ-040..045) è **superato** dal modello FEAT-010 che
> introduce: (a) separazione tra momento di generazione e momento di indicizzazione/retrieval;
> (b) collezioni separate wiki/codice interrogate congiuntamente; (c) scope retrieval = solo wiki
> generato + codice (input non indicizzati). Vedi FR-008..011 e FR-023/024.

*(REQ-040..045 conservati solo come riferimento storico; non sono operativi nel consolidato.)*

### Gruppo F — Idempotenza trasversale
*(assorbito invariato da FEAT-003; FEAT-010 D-10, SC-006)*

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

### Gruppo 5.1 — Popolamento e manutenzione agentici
*(net-new FEAT-010 D-2; pattern Karpathy §2)*

**FR-001 (Ubiquitous)**
*The system shall populate and maintain the wiki via an agentic layer (skill + hook) that
performs the bookkeeping of the Karpathy pattern (pages, `index.md`, `log.md`,
cross-references), reducing manual editing to the exception.*
> *(Riformulata 2026-06-09, D-18: rimosso il confinamento a `manual_edited/`.)*

**FR-002 (Optional — riuso DRY)**
*The skills/hooks may build on top of the FEAT-003 operations (`create_wiki`/`record`/`ingest`/
`distill`/`index_wiki`); where they rely on an already-covered capability, they should reuse
it rather than re-implement it (DRY, Principio III).*

**FR-003 (Event-driven)**
*When a new source or a relevant activity/decision is signalled, the system shall perform
ingest/record following the Karpathy pattern: read the source, write/update the thematic page,
update related pages (potentially multiple pages), update `index.md`, append exactly one entry
to `log.md`.*

**FR-004 (Event-driven)**
*When the `/wiki` command is invoked, the system shall update the wiki by processing the changeset
of the last commit (`git diff HEAD~1`) and record it in the log; the deterministic part computes the
changeset, the judgment part decides which pages/content to change per page-craft, wiki-craft and the
playbook. No full rebuild.*
> *(Risolta 2026-06-09, D-19: trigger = comando manuale `/wiki`, non hook; ambito = ultimo commit;
> il "cosa modificare" è responsabilità della parte N.)*

**FR-005 (Event-driven)**
*When a query/exploration produces reusable knowledge, the system shall be able to archive it
in the wiki as a new page (no dispersal in chat), updating the index and the log.*

**FR-006 (Optional)**
*Where enabled, the system shall execute a lint of the wiki (contradictions, orphan pages,
stale claims, missing cross-references/coverage) and report the results.*
> Cadenza/trigger del lint: vedi FR-037/FR-038.

**FR-007** — ⛔ **DELETED BY DESIGN (2026-06-09, D-18)** — dipendeva da `manual_edited/`, rimossa.
> *~~If a page is in `manual_edited/`, then the agentic layer shall not modify it nor delete it,
> reading it only as a source (D-1).~~*

### Gruppo 5.2 — Generazione (a) e indicizzazione/retrieval (b)
*(net-new FEAT-010 D-3; override Gruppo E)*

**FR-008 (Ubiquitous)**
*The generation of the wiki shall produce content in natural language with linked concepts
(wiki format), updatable incrementally.*

**FR-009 (Ubiquitous)**
*The set of input-sources for generation shall be configurable and modifiable during the
project lifecycle; default set: discussion logs, sources (`sources/`), tests, SpecKit
(`specs/`).*
> *(Riformulata 2026-06-09, D-18: rimosso `manual_edited/` dal set di default.)*

**FR-010 (Ubiquitous)**
*The wiki shall be indexed in a separate collection from the sources and shall be queryable
together with them (join at query-time), with equal weight (no boost) in moment (b).*

**FR-011 (Ubiquitous)**
*Each collection (wiki, sources) shall be independently regenerable: rebuilding one shall not
affect the other.*

### Gruppo 5.3 — Verità, autorità e obsolescenza
*(net-new FEAT-010 D-4)*

**FR-012 (Ubiquitous)**
*The system shall treat code+tests as authority on behaviour and discussions/SpecKit as
authority on the why; no single source of truth exists.*
> *(Riformulata 2026-06-09, D-18: rimosso `manual_edited`.)*

**FR-013 (Ubiquitous)**
*In case of conflict, the system shall apply the default hierarchy (behaviour → code/tests;
why → registered decision).*

**FR-014 (Optional)**
*Where configured, the system should apply an explicit authority hierarchy in place of the
default.*

**FR-015** — ⛔ **DELETED BY DESIGN (2026-06-09, D-18)** — dipendeva da `manual_edited/`, rimossa.
> *~~When an inconsistency involving `manual_edited/` is detected, the system shall signal it and
> ask the user how to proceed, without autonomously modifying or discarding the source.~~*

**FR-016** — ⛔ **DELETED BY DESIGN (2026-06-09, D-18)** — dipendeva da `manual_edited/`, rimossa.
> *~~The content of `manual_edited/` shall be compiled into derived wiki pages (synthesis/
> integration) and optionally linked to the source; the source file in `manual_edited/` shall
> remain unmodified (D-1).~~*

**FR-017 (Ubiquitous)**
*A wiki page shall be considered stale if it contradicts the code/tests (behaviour) or a
registered decision (SpecKit).*
> *(Riformulata 2026-06-09, D-18: rimosso `manual_edited`.)*

### Gruppo 5.4 — Fonti-input, trigger e versionamento
*(net-new FEAT-010 D-5/D-6)*

**FR-018 (Event-driven)**
*When the `/wiki` command is invoked (manual trigger), the system shall process the changeset of the
last commit (`git diff HEAD~1`, versioned sources) and update only the impacted pages.*
> *(Aggiornata 2026-06-09, D-19: il trigger è il comando manuale `/wiki`, non un hook automatico al
> commit; l'ambito resta il changeset dell'ultimo commit.)*

**FR-019 (Ubiquitous)**
*The system shall require git as a prerequisite; the state "last processed commit" acts as the
watermark for incremental updates.*

**FR-020** — ⛔ **DELETED BY DESIGN (2026-06-09, D-18)** — `ingested_sources/` rimossa; le fonti
esterne sono riassunte in `sources/` via ingest (vedi FR-030 riformulato).
> *~~The `ingested_sources/` folder shall be the entry point for non-versionable sources, used by
> the wiki as input for generating/enriching concepts (it is not an output of summary pages).~~*

**FR-021** — ⛔ **DELETED BY DESIGN (2026-06-09, D-18)** — `ingested_sources/` rimossa.
> *~~When the user requests it (at creation or update), the system shall (re)process
> `ingested_sources/` as input.~~*

**FR-022 (Unwanted behaviour)**
*If a source file to be ingested is an unreadable binary, then the system shall not ingest it.*
> *(Riformulata 2026-06-09, D-18: rimossi i riferimenti a `manual_edited/`/`ingested_sources/`.)*

### Gruppo 5.5 — Perimetro del retrieval
*(net-new FEAT-010 D-7; override Gruppo E)*

**FR-023 (Ubiquitous)**
*The RAG (moment b) shall index only the generated wiki (including `sources/`) and the code
(separate collections, joint query).*
> *(Riformulata 2026-06-09, D-18: rimossa la clausola sulle cartelle-input, non più esistenti.)*

**FR-024 (Ubiquitous)**
*Generated wiki pages may contain references/links to input sources; such references shall not
be indexed nor inserted into the RAG.*

### Gruppo 5.6 — Esecuzione: skill, trigger, setup, no-code
*(net-new FEAT-010 D-8/D-9)*

**FR-025 (Ubiquitous)**
*The wiki generation/maintenance shall be a distinct skill separate from the versioning
component; it is invoked manually via `/wiki`.*
> *(Riformulata 2026-06-09, D-19: il versioning non invoca più la skill; trigger manuale.)*

**FR-026** — ⛔ **SUPERATA (2026-06-09, D-19)** — il modello "config-manager invoca la skill al commit"
è sostituito dal trigger manuale `/wiki`.
> *~~When the configuration-manager (or equivalent) is about to commit, the system shall invoke
> the generation skill and include its outputs in the same commit…~~*

**FR-027** — ⛔ **SUPERATA (2026-06-09, D-19)** — niente contratto di trigger "al commit": il trigger
è il comando manuale `/wiki`.
> *~~The trigger shall be defined by a client-agnostic contract ("at commit, with the changeset")…~~*

**FR-028** — ⛔ **SUPERATA (2026-06-09, D-19)** — nessun binding del trigger da installare (trigger manuale).
> *~~The product setup shall install the trigger binding…~~*

**FR-029 (Ubiquitous)**
*The system shall not assume the presence of source code: code is an optional input-source;
LLM Wiki + RAG shall operate also for code-free projects.*

### Gruppo 5.7 — Ingest: riassunto in `sources/`
*(2026-06-09 D-18: l'override del Gruppo C decade; tornano operativi REQ-020..023, ingest scrive un
riassunto in `sources/`, semantica Karpathy.)*

**FR-030** — ⛔ **DELETED BY DESIGN (2026-06-09, D-18)** — sostituita dal ritorno alla semantica
"ingest produce un riassunto in `sources/`" (REQ-020..023, Gruppo C riattivato).
> *~~When the ingest functionality is invoked … the system shall (re)populate `ingested_sources/`
> with the imported external documentation.~~*

**FR-031** — ⛔ **DELETED BY DESIGN (2026-06-09, D-18)** — cade la separazione *import ≠ compile*.
> *~~Ingest (import into `ingested_sources/`) shall be distinct from compilation into concept-pages
> (generation, moment a): ingest provides the input, generation compiles it.~~*

### Gruppo 5.8 — Superfici di invocazione
*(net-new FEAT-010 D-12)*

**FR-032 (Ubiquitous)**
*On-demand wiki operations (ingest, query, regeneration, maintenance, setup) shall be exposed
via the LLM client skill (primary), CLI and MCP.*

### Gruppo 5.9 — Interrogazione e navigazione
*(net-new FEAT-010 D-13)*

**FR-033 (Ubiquitous)**
*Wiki querying shall occur via the RAG (existing search); no dedicated native wiki query
surface is in scope.*

**FR-034 (Ubiquitous)**
*The wiki shall remain interconnected Markdown (wikilinks), navigable with external tools
(Obsidian/editor) without a dedicated UI.*

### Gruppo 5.10 — Manutenzione: lint + freschezza
*(net-new FEAT-010 D-14)*

**FR-035 (Ubiquitous)**
*The system shall provide structural lint of the wiki (broken links, orphan pages, missing
coverage/cross-references, contradictions).*

**FR-036 (Ubiquitous)**
*The system shall provide freshness verification of wiki pages (staleness, FR-017).*

**FR-037 (Event-driven)**
*When `/wiki` is invoked, the system shall run lint + freshness incrementally on the pages linked
to the entities in the last-commit changeset (together with generation).*
> *(Riformulata 2026-06-09, D-19: trigger = `/wiki`, non "al commit".)*

**FR-038 (Event-driven)**
*When requested on-demand or according to a periodic schedule, the system shall run lint +
freshness on the entire wiki.*

### Gruppo 5.11 — Distillazione artefatti e setup
*(net-new FEAT-010 D-15/D-16)*

**FR-039 (Ubiquitous)**
*The system shall not provide a separate "distill-from-artifact" operation: artefacts are
input-sources for generation (D-3), which compiles them; an on-demand targeted mode
(regenerate from a single artefact) is admissible.*

**FR-040 (Event-driven)**
*When the wiki is initialised on a repo (`sertor wiki init` or equivalent), the system shall
create the structure and optionally execute an initial ingest.*
> *(Riformulata 2026-06-09, D-19: rimossa l'installazione del binding del trigger — trigger manuale.)*

### Gruppo 5.12 — Gate al commit
*(net-new FEAT-010 D-17)*

**FR-041** — ⛔ **DELETED BY DESIGN (2026-06-09, D-20)** — niente gate che blocca il commit (trigger manuale).
> *~~When lint/freshness at commit detect problems above the configurable threshold, the system
> shall block the commit…~~*

**FR-042** — ⛔ **DELETED BY DESIGN (2026-06-09, D-20)** — non c'è gate, quindi nessun override da tracciare.
> *~~Where the user chooses "ignore and commit", the system shall proceed with the commit…~~*

---

## 7. Criteri di successo (misurabili)

| ID | Criterio | Collegamento |
|----|----------|-------------|
| SC-001 | Su un repo inizializzato, un commit che tocca N file produce un aggiornamento del wiki **limitato alle pagine collegate alle entità del changeset** (non un full rebuild). | D-5/FR-018/FR-037 |
| SC-002 | ⛔ **OBSOLETO (2026-06-09, D-18)** — riguardava cartelle-input (`manual_edited/`, `ingested_sources/`) ora eliminate. | ~~D-7/FR-023~~ |
| SC-003 | Una query di retrieval restituisce risultati dal **wiki generato** e dal **codice** (collezioni separate interrogate insieme). | D-3/D-7/FR-010 |
| SC-004 | ⛔ **OBSOLETO (2026-06-09, D-20)** — riguardava il gate-che-blocca-il-commit, eliminato. Lint/freschezza restano come report non bloccante di `/wiki` (SC-009/FR-035..037). | ~~D-17/FR-041/FR-042~~ |
| SC-005 | Il prodotto funziona su un progetto **senza codice**: generazione, retrieval e manutenzione operano con le sole fonti documentali. | D-9/FR-029 |
| SC-006 | Rieseguendo un'operazione strutturale su input invariato, l'esito è **identico** (idempotenza: nessun duplicato di pagina/voce log; id chunk = path relativo). | REQ-050/051 |
| SC-007 | La stessa operazione è invocabile e raggiungibile da **skill, CLI e MCP**. | D-12/FR-032 |
| SC-008 | Dopo `sertor wiki init`, lanciando **`/wiki`** la generazione elabora il changeset dell'ultimo commit e aggiorna solo le pagine impattate. *(2026-06-09, D-19: era "un commit innesca la generazione via binding".)* | D-19/FR-004/FR-018/FR-040 |
| SC-009 | Una pagina che afferma un comportamento **contraddetto dal codice/test**, o una **decisione** contraddetta, è segnalata come **obsoleta**. | D-4/FR-017/FR-036 |
| SC-010 | L'ingest, alla creazione/on-demand/update, produce un **riassunto in `sources/`** della fonte esterna (pattern Karpathy). *(2026-06-09, D-18: era "popola `ingested_sources/` senza riassunto".)* | REQ-020..023 |
| SC-3a | Dato un repository privo di wiki, la skill produce la struttura completa (`index.md`, `log.md`, cartelle tematiche) in un'unica invocazione. | REQ-001 |
| SC-3b | Una seconda invocazione su un progetto già dotato di wiki non sovrascrive il contenuto esistente (idempotenza strutturale). | REQ-002/REQ-013 |
| SC-3c | Dopo record/ingest su un wiki esistente, l'indice riflette le nuove pagine e il log contiene la nuova voce. | REQ-011/REQ-012 |
| SC-3d | Dato un wiki esistente e un indice RAG configurato, le pagine del wiki compaiono nei risultati di una query documentale pertinente. | FR-010/SC-003 |
| SC-3e | La skill funziona senza modifiche su almeno due repository diversi (portabilità repo-agnostica). | REQ-006/FR-029 |
| SC-3f | Dati un testo di conversazione/sessione e un wiki esistente, la skill produce una pagina di distillazione conforme alle convenzioni. | REQ-030..033 |

---

## 8. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| RNF-001 | **Portabilità** | La skill opera su qualunque repository target senza dipendere da un sistema operativo specifico o da percorsi hard-coded. |
| RNF-002 | **Testabilità** | Ogni operazione espone un'interfaccia verificabile automaticamente; è possibile eseguire i test su un wiki temporaneo senza effetti sul corpus di produzione. |
| RNF-003 | **Configurabilità** | Il percorso del wiki, il provider LLM e il sistema RAG di destinazione sono configurabili tramite parametri o file di configurazione centralizzato, senza modificare il codice. *(2026-06-09, D-20: rimossa la soglia del gate.)* |
| RNF-004 | **Osservabilità minima** | Ogni operazione emette log strutturati (almeno: operazione, file coinvolti, esito, changeset processato) che permettono di diagnosticare fallimenti senza accedere al codice sorgente. |
| RNF-005 | **Gestione esplicita degli errori** | Condizioni di errore prevedibili (RAG non configurato, wiki già esistente, file corrotto, LLM non disponibile, git non disponibile) producono messaggi d'errore leggibili e non lasciano il sistema in uno stato parziale. |
| RNF-006 | **Isolamento delle dipendenze** | Le dipendenze specifiche della skill non devono confliggere con quelle degli altri motori RAG del core, e devono poter essere installate in ambienti isolati. |
| RNF-007 | **Scalabilità lineare** | Il corpus wiki indicizzato non deve imporre limiti artificiali al numero di pagine (la skill scala linearmente con il numero di file Markdown). |
| RNF-008 | **Latenza incrementale** | La generazione incrementale via `/wiki` (FR-018, changeset dell'ultimo commit) deve essere proporzionale alla dimensione del changeset, non al wiki intero. |

---

## 9. Vincoli, assunzioni e dipendenze

### Vincoli

- **Vincolo DA-W1**: il wiki è trattato come **corpus paritario** nel RAG; nessun meccanismo di
  boost semantico è in scope (`requirements/sertor-core/epic.md §9`).
- **Segreti**: nessun segreto (chiavi API, credenziali) viene persistito in file versionati; la
  configurazione sensibile transita esclusivamente tramite variabili d'ambiente o file `.env`
  non committati (`REQ-E5` dell'epica).
- **LLM condizionale**: il provider LLM è necessario **solo** per le operazioni che richiedono
  generazione (distillazione REQ-031, generazione wiki FR-001..007, verifica freschezza FR-036);
  le operazioni strutturali (creazione, ingest-import, indicizzazione) non devono richiedere un LLM.
- **Git obbligatorio**: il meccanismo di refresh al commit (FR-018/FR-019) richiede git come
  prerequisito documentato (D-5).
- **Dipendenza dal nucleo condiviso (FEAT-001)**: l'indicizzazione del wiki nel RAG dipende dalla
  disponibilità del nucleo di retrieval condiviso. Le operazioni strutturali (Gruppi A–D, F) sono
  sviluppabili in isolamento.

### Assunzioni

- Il repository target dispone di un filesystem accessibile in lettura/scrittura.
- Le pagine wiki sono scritte in Markdown (`.md`); altri formati sono fuori ambito.
- L'input dell'operazione di distillazione è un **brief/riassunto già condensato** (non una
  trascrizione grezza; DA-W3 risolta).
- Le fonti da ingerire contengono **solo contenuti leggibili** (no binari, FR-022). *(2026-06-09, D-18: era riferito a `manual_edited/`.)*
- È presente un **client LLM** (Claude Code/Copilot/Codex) che espone il comando `/wiki`. *(2026-06-09, D-19: rimosso il binding del trigger.)*
- La struttura wiki di base (`concepts/`, `tech/`, `experiments/`, `syntheses/`, `index.md`,
  `log.md`) è fissa nell'MVP; la personalizzazione strutturale per progetto è post-MVP.
- Le fonti versionate vivono nel repo; le fonti esterne ingerite sono riassunte in `sources/`. *(2026-06-09, D-18: rimosso `ingested_sources/`.)*

### Dipendenze

| Dipendenza | Tipo | Note |
|------------|------|------|
| **FEAT-001** (nucleo retrieval condiviso) | Funzionale (parziale) | Richiesta per l'indicizzazione RAG (FR-010/FR-023); i Gruppi A–D, F sono sviluppabili in isolamento. |
| **FEAT-009** (refresh incrementale indice) | Funzionale (abilitante) | Abilitatore della generazione/manutenzione incrementale al commit; in assenza, fallback a rigenerazione più ampia. |
| **REQ-E3** (epica, LLM obbligatorio per generazione) | Architetturale | Solo per REQ-031 e le operazioni di generazione; le altre operazioni sono LLM-free. |
| **Provider LLM configurato** | Runtime condizionale | Obbligatorio per distillazione e generazione wiki; opzionale per il resto. |
| **Sistema RAG configurato** | Runtime condizionale | Obbligatorio per indicizzazione (FR-010/FR-023); non richiesto per operazioni strutturali. |
| **configuration-manager** (o equivalente del client) | Runtime | Fornisce il diff dell'ultimo commit alla parte D. *(2026-06-09, D-19: non è più il binding del trigger.)* |
| **git** | Runtime obbligatorio | Prerequisito per il meccanismo di refresh al commit (FR-019). |

---

## 10. Rischi

| ID | Rischio | Prob | Impatto | Mitigazione |
|----|---------|------|---------|-------------|
| R-01 | **Rumore del giudizio LLM nella verifica di freschezza** (falsi positivi) | Media | Medio | Report non bloccante di `/wiki` (l'utente decide) + verità stratificata (D-4). *(2026-06-09, D-20: era "gate human-in-the-loop".)* |
| R-02 | **Costo/latenza della generazione** via `/wiki` | Media | Medio | Incrementale sul solo changeset dell'ultimo commit (D-5/D-19); invocazione manuale → nessuna latenza imposta al commit |
| ~~R-03~~ | ⛔ **DECADUTO (2026-06-09, D-19)** — nessun binding del trigger (trigger manuale `/wiki`) | — | — | — |
| R-04 | **Generazione su progetti grandi** lenta | Bassa | Medio | Incrementale di default; full solo on-demand/periodico; scalabilità lineare (RNF-007/008) |
| R-05 | **Divergenza tra le tre superfici** (skill/CLI/MCP) | Bassa | Medio | Superfici = binding sullo stesso core/contratto (D-8/D-12) |
| ~~R-06~~ | ⛔ **DECADUTO (2026-06-09, D-18)** — `manual_edited` rimossa, il rischio non si applica più | — | — | — |
| R-W1 | **Drift struttura wiki** (nomi cartelle/convenzioni divergono dal workspace) | Media | Alto | Convenzioni specificate come requisiti espliciti (Gruppo A) e validate su `prototype/wiki/` |
| R-W3 | **Dimensione crescente dell'indice RAG** (wiki molto grande rallenta la reindicizzazione) | Bassa | Medio | RNF-007 (scalabilità lineare); incrementale di default; full rebuild solo on-demand |
| R-W4 | **Dipendenza da FEAT-001 non ancora disponibile** | Media | Medio | I Gruppi A–D, F sono sviluppabili e dimostrabili in isolamento; pianificare integrazione con FEAT-001 come task separato |
| R-W5 | **Contaminazione del wiki di produzione durante i test** | Media | Alto | RNF-002: i test operano su un wiki temporaneo/sandbox completamente isolato |

---

## 11. Prioritizzazione (MoSCoW)

| Gruppo di requisiti | ID | MoSCoW | Motivazione |
|---|---|---|---|
| A — Inizializzazione struttura | REQ-001..006 | **Must** | Prerequisito di tutto il resto; senza struttura non si può operare né indicizzare. |
| B — Operazione record | REQ-010..013 | **Must** | Flusso minimo del wiki-keeper; operazione fondamentale per documentare in continuo. |
| D — Distillazione | REQ-030..033 | **Should** | Capacità di alto valore, dipende dal LLM; implementabile subito dopo i Must. |
| F — Idempotenza trasversale | REQ-050..051 | **Must** | CS-3/SC-006 la citano esplicitamente; senza idempotenza il wiki diverge. |
| Generazione via `/wiki` (D-2/D-3/D-5/D-19) + collezioni separate + retrieval (D-7) + setup (D-16) | FR-001..011, FR-018..019, FR-023..025, FR-040 | **Must** | Cuore e2e: senza, non c'è LLM Wiki vivo né "una sola verità interrogabile". *(2026-06-09, D-19: FR-026..028 superate.)* |
| ~~Convenzione input (`manual_edited` D-1 / `ingested_sources` D-6) + ingest→ingested_sources (D-11)~~ | ~~FR-007, FR-020..021, FR-030..031~~ | ⛔ **DELETED BY DESIGN (2026-06-09, D-18)** | Eliminate; ingest torna a riassumere in `sources/` (REQ-020..023). |
| Superfici skill+CLI+MCP (D-12) | FR-032..034 | **Should** | La skill@commit basta per il flusso primario; CLI/MCP ampliano l'uso. |
| Manutenzione (lint + freschezza D-14) | FR-035..038 | **Should** | Alza la qualità; il valore base esiste anche senza. *(2026-06-09, D-20: rimosso il gate al commit, FR-041/042.)* |
| Verità stratificata + gerarchia + obsolescenza (D-4) | FR-012..017 | **Should** | Consolida la governance della fonte di verità. |
| Trigger **periodico** (D-14) | FR-038 (schedulazione) | **Could** | Utile ma non essenziale rispetto a commit + on-demand. |
| No-code-first (D-9) | FR-029 | **Could** | Generalizza il prodotto; non blocca il caso con codice. |
| Gerarchia di autorità **configurabile** (D-4/FR-014) | FR-014 | **Could** | Il default copre la maggior parte dei casi. |

> **Sequenza consigliata per l'MVP**: Gruppo A → Gruppo B → Gruppo F → generazione al commit +
> collezioni separate (subordinato a FEAT-001) → ingest (riassunto in `sources/`, REQ-020..023) →
> Gruppo D → superfici CLI/MCP → manutenzione/gate. *(2026-06-09, D-18.)*

---

## 12. Decisioni prese (D-1 .. D-21)

Le decisioni seguenti sono state stabilite nel corso delle iterazioni di elicitazione di FEAT-010
(2026-06-04). Sono normative per il design a valle.

### D-1 — Convenzione "manuale vs automatico" (cartella `manual_edited/`)
> ⛔ **DELETED BY DESIGN (2026-06-09, vedi D-18).** La cartella `manual_edited/` è eliminata: l'autoring
> umano avviene nelle pagine normali del wiki. Testo conservato sotto solo come riferimento storico.

I file Markdown scritti a mano dall'umano vivono in `wiki/manual_edited/` e sono trattati come
**documentazione esterna / fonte autorevole**. L'automazione **non modifica né cancella mai** i file
in `manual_edited/`: li può solo **leggere** (come contesto/fonte) e **indicizzare**. Il wiki
generato (`concepts/` `tech/` `experiments/` `syntheses/` + `index.md`, `log.md`) è automatico. La
cartella `manual_edited/` **non è indicizzata nel RAG** (D-7): è input, si interroga via i concetti
compilati; le pagine generate possono linkarla.

### D-2 — Il wiki è popolato/mantenuto da un layer AGENTICO (skill + hook) che riusa FEAT-003
Il popolamento e la manutenzione del wiki seguono il pattern Karpathy (§2): il bookkeeping è svolto
da un **layer agentico** fatto di skill e hook che **riusano le operazioni di FEAT-003** come
primitive di libreria (DRY, Principio III), aggiungendovi l'**orchestrazione agentica**. L'editing
manuale resta possibile ma **confinato a `manual_edited/`** (D-1).

### D-3 — Due momenti distinti: generazione (a) e indicizzazione/retrieval (b)
**(a) Generazione** — modello Karpathy: contenuto in linguaggio naturale a concetti linkati,
aggiornato **incrementalmente** da un insieme di fonti-input configurabile. **(b) Indicizzazione +
interrogazione** — il wiki generato è un corpus RAG **paritario** ai sorgenti: **peso paritario**
solo qui; **collezioni separate** (wiki ≠ codice) interrogate insieme (join a query-time). Ogni
collezione si rigenera indipendentemente (risolve il rebuild distruttivo). Il codice è un **input**
alla generazione, non solo un corpus del RAG.

### D-4 — Verità stratificata, gerarchia di autorità e obsolescenza
**Codice + test** = autorità sul **comportamento**; **discussioni / SpecKit** = autorità sul
**perché**. Gerarchia di default per conflitti: comportamento → codice/test; perché →
decisione registrata. Gerarchia **configurabile** (Should). Conflitti rilevati →
**human-in-the-loop**: segnala e chiede, non decide da solo. Definizione di **obsolescenza**: pagina
contraddice il codice/test **oppure** una decisione registrata. *(Aggiornata 2026-06-09, D-18: rimosso
`manual_edited` come fonte/oggetto di conflitto.)*

### D-5 — Refresh git-driven al commit (fonti versionate) + git come prerequisito
Le fonti-input versionate vivono in git; il wiki si aggiorna **al commit**, elaborando il changeset
dall'ultimo commit (**generazione incrementale guidata da git**, watermark = "ultimo commit
elaborato"). **Git è prerequisito documentato**. Le fonti accettano qualunque contenuto leggibile;
binari non leggibili esclusi. *(Aggiornata 2026-06-09: D-18 rimuove `manual_edited/`; D-19 — l'aggiornamento è innescato dal comando `/wiki`, non automaticamente al commit; l'ambito resta il changeset dell'ultimo commit.)*

### D-6 — `ingested_sources/` (ex `sources/`): input esterno NON versionabile, a trigger manuale
> ⛔ **DELETED BY DESIGN (2026-06-09, vedi D-18).** La rinomina `sources/`→`ingested_sources/` e il
> "modello a due classi" sono annullati: `sources/` resta `sources/` con la semantica Karpathy
> (riassunti generati dall'ingest). Testo conservato sotto solo come riferimento storico.

La cartella `sources/` è **rinominata `ingested_sources/`** e **cambia ruolo**: da output di
riassunti generati a **punto d'ingresso delle sorgenti non versionabili** (paper, contenuti web).
Popolamento a **trigger manuale**. Il wiki la usa come input per generare e arricchire i concetti.
**Modello a due classi**: input (l'LLM legge, non scrive): codice · test · SpecKit · log discussioni
· `manual_edited/` · `ingested_sources/`; wiki generato (l'LLM scrive): `concepts/` · `tech/` ·
`experiments/` · `syntheses/` · `index.md` · `log.md`.

### D-7 — Retrieval "puro Karpathy": indicizzato solo il wiki generato + il codice
> ♻️ **SEMPLIFICATA (2026-06-09, vedi D-18).** Non esistendo più cartelle-input (`manual_edited/`,
> `ingested_sources/`), cade la clausola di esclusione: indicizzato = **wiki generato (incluso
> `sources/`) + codice**.

Nel momento (b) il RAG contiene **solo**: il **wiki generato** (incluso `sources/`) + il **codice**
(collezioni separate, query congiunta). I riferimenti esterni nelle pagine generate non sono
indicizzati.

### D-8 — Skill client-agnostica invocata al commit; trigger contract portabile; setup rilascia il trigger
> ♻️ **RIVISTA (2026-06-09, vedi D-19).** Resta valido che la generazione è una **skill distinta** dal
> versioning (SRP). È **superata** la parte "invocata al commit dal configuration-manager + contratto
> di trigger + binding": il trigger è il comando manuale `/wiki`. Testo sotto = riferimento storico.

La generazione/manutenzione del wiki è una **skill distinta** dal componente di versioning (SRP,
Principio VII). È **invocata al commit** dal configuration-manager: il config-manager decide il
**quando**, la skill fa il **cosa** (riusa FEAT-003). Esecuzione **sincrona quando possibile**
(output nello stesso commit); fallback asincrono. **Contratto di trigger portabile** (client-agnostico);
il configuration-manager è il binding per Claude Code. **Setup rilascia il binding** del trigger:
altrimenti il trigger si perde.

### D-9 — LLM Wiki + RAG come asset anche per progetti SENZA codice
Il codice è una delle fonti-input (D-3), **non un prerequisito**. Per i progetti senza codice manca
la "verità sul comportamento" (codice/test) di D-4, ma restano log discussioni, fonti in `sources/`,
e il wiki compilato interrogabile. Il git-prerequisito di D-5 resta; il "codice come
fonte" è opzionale. *(Aggiornata 2026-06-09, D-18: rimossi `manual_edited/`/`ingested_sources/`.)*

### D-10 — Questo documento è l'autorità e2e (consolidante); FEAT-003 assorbito come storico
Questo requisito (in origine FEAT-010 `llm-wiki`, ora consolidato qui) è il **riferimento canonico**
dell'LLM Wiki e2e. Assorbe da FEAT-003 (invariati): struttura/convenzioni (REQ-001..006), record
(REQ-010..013), distill (REQ-030..033), idempotenza (REQ-050/051). Override su: ingest/`sources/`
(→ D-6/D-11) e indicizzazione (→ D-3/D-5/D-7). Espande lo scope: manutenzione, refresh incrementale,
orchestrazione agentica, no-code. FEAT-003 (`wiki-creazione` storico) → `llm-wiki` è la feature wiki
di riferimento.

### D-11 — Funzionalità di "ingest": importa documentazione esterna in `ingested_sources/`
> ⛔ **DELETED BY DESIGN (2026-06-09, vedi D-18).** Cade la separazione *import ≠ compile*: l'ingest
> torna a produrre un **riassunto in `sources/`** (FEAT-003 Gruppo C, REQ-020..023, di nuovo operativo).
> Testo conservato sotto solo come riferimento storico.

Esiste una funzionalità di **ingest** che **importa documentazione esterna** in `ingested_sources/`
alla **creazione del wiki**, **on-demand** e a seguito di **update** di doc esterni. **Import ≠
compile**: l'ingest popola l'**input** (`ingested_sources/`); la **compilazione** in pagine-concetto
avviene nella **generazione** (momento a, D-3). Override di FEAT-003 REQ-020.

### D-12 — Superfici di invocazione: skill (primaria) + CLI + MCP per le operazioni on-demand
Le operazioni non-automatiche (ingest on-demand, query, rigenerazione, manutenzione, setup) sono
esposte su: **skill** del client LLM (primaria); **CLI** (`sertor …`); **MCP** (uso cross-client).
La generazione è innescata dal comando `/wiki` (D-19).

### D-13 — Query via RAG; navigazione umana via Obsidian/editor; nessuna superficie nativa
L'interrogazione avviene tramite il **RAG esistente** (`sertor search` + MCP `search_*`). Il wiki,
essendo `.md` interconnessi, è consultabile con **Obsidian o altri editor** (navigazione umana).
**Nessuna superficie wiki-nativa dedicata** in scope (chiude T6).

### D-14 — Manutenzione in scope: lint strutturale + verifica di freschezza; trigger incrementale/on-demand/periodico
In scope due controlli: **lint strutturale** (link rotti, orfani, copertura/cross-ref, contraddizioni)
e **verifica di freschezza** (FR-017). Trigger: via `/wiki` **incrementale** (pagine collegate alle
entità del changeset dell'ultimo commit, D-19); on-demand **full**; periodico **full**. *(2026-06-09, D-20: nessun gate; lint/freschezza riportano, non bloccano.)*

### D-15 — distill-da-artifact = modalità mirata della generazione (no operazione separata)
Gli artefatti (spec SpecKit, plan, ADR, requirements, design doc) sono **già fonti-input** della
generazione (D-3): la generazione li compila in concetti. **Non** esiste un'operazione
"distill-da-artifact" separata; ammessa una **modalità mirata** on-demand.

### D-16 — Comando/skill di setup (`sertor wiki init`)
> ♻️ **RIVISTA (2026-06-09, D-18+D-19).** Cade il punto (2) "installa il binding del trigger" (trigger
> manuale `/wiki`, D-19); l'ingest iniziale del punto (3) produce un riassunto in `sources/` (D-18).

Esiste un comando/skill di **setup** (`sertor wiki init`), eseguito **una volta per repo**, che:
(1) crea la struttura wiki (`create_wiki`); (2) ~~installa il binding del trigger~~ (rimosso, D-19);
(3) esegue un **ingest iniziale opzionale** (riassunto in `sources/`, D-18) se fornito.

### D-17 — Gate al commit: blocca, avvisa, propone soluzioni (incl. "ignora e committa")
> ⛔ **DELETED BY DESIGN (2026-06-09, vedi D-20).** Il gate-che-blocca-il-commit è eliminato: incoerente
> col trigger manuale `/wiki` post-commit (D-19). Lint/freschezza restano come parte normale di `/wiki`,
> senza blocco. Testo sotto = riferimento storico.

Al commit, se lint/freschezza rilevano problemi **sopra soglia configurabile**, il gate **blocca** il
commit, **avvisa** l'utente con i problemi rilevati e **propone una o più soluzioni**; tra le opzioni
c'è sempre **"ignora e committa lo stesso"** (override esplicito, **tracciato**). È
**human-in-the-loop** (coerente con D-4): l'utente decide; **nessun auto-fix silenzioso** né blocco
senza via d'uscita.

### D-18 — RIMOZIONE PER DESIGN (2026-06-09): eliminati `manual_edited/` e `ingested_sources/`
**Decisione canonica** che ribalta D-1, D-6, D-11 e semplifica D-4, D-5, D-7, D-9. Le due convenzioni
a cartelle d'input sono **rimosse dallo scope** per semplificazione e per **allineare il piano alla
realtà**: il wiki di produzione ha già consolidato la tassonomia in `sources/`, abbandonando
`manual_edited/`/`ingested_sources/` (vedi `wiki/syntheses/sistema-wiki-fonte-unica.md`).

**Modello risultante (sostituisce il "modello a due classi" di D-6):**
- **Niente `manual_edited/`**: l'autoring umano avviene nelle **pagine normali** del wiki; non esiste
  più una cartella-input immutabile né la regola "l'LLM non la modifica". La gerarchia di verità sul
  **perché** poggia su **discussioni/SpecKit** (decisioni registrate).
- **Niente `ingested_sources/`**: le fonti esterne **non versionabili** si gestiscono via l'operazione
  **ingest** che produce un **riassunto in `sources/`** (semantica Karpathy originale, = FEAT-003
  Gruppo C REQ-020..023, che torna così operativo). Cade la separazione *import ≠ compile* di D-11.
- **Retrieval semplificato (override di D-7):** indicizzato = **wiki generato (incluso `sources/`) +
  codice** (collezioni separate, query congiunta). Sparisce la clausola "le cartelle-input non sono
  indicizzate" perché non esistono più cartelle-input escluse.

**Impatto puntuale:**
- **Decisioni:** D-1 ⛔ · D-6 ⛔ · D-11 ⛔ · D-7 semplificata · D-4/D-5/D-9 ripulite dai riferimenti.
- **FR eliminate:** FR-007, FR-015, FR-016 (manual_edited) · FR-020, FR-021 (ingested_sources) · FR-030,
  FR-031 (ingest→ingested_sources, import≠compile).
- **FR riformulate:** FR-001, FR-009, FR-012, FR-013, FR-017 (rimosso "manual_edited") · FR-022 (binari
  solo su `sources/`) · FR-023 (rimossa la clausola sulle cartelle-input).
- **Criteri:** SC-002 ⛔ obsoleto · SC-010 riformulato (ingest scrive il riassunto in `sources/`).
- **Rischi:** R-06 (conflitti su `manual_edited`) decaduto.
- **Glossario/Scope/MoSCoW/Assunzioni:** allineati.

Non si riscrivono changelog né log storici: registrano la decisione di allora. Questa D-18 è la verità
corrente.

### D-19 — Trigger del wiki: comando manuale `/wiki`, ambito = ultimo commit, "cosa modificare" alla parte N
**Decisione canonica** che chiude DA-FR004/FR-004 e rivede il modello di trigger di D-8.

- **Trigger = comando manuale `/wiki`** (non hook automatico, non binding al commit). L'utente lo lancia
  quando vuole aggiornare il wiki.
- **Ambito = changeset dell'ultimo commit** (`git diff HEAD~1`). La **parte D** calcola il changeset
  (delegato al configuration-manager, che resta solo un fornitore di diff, non un invocatore). Mai
  rebuild completo.
- **Cosa modificare = parte N (giudizio LLM):** quali pagine e quali contenuti aggiornare lo decide il
  giudizio in base a **page-craft**, **wiki-craft** e al **playbook**.

**Impatto — superato il modello "automatico al commit via binding":**
- **Decisioni:** D-8 (skill *invocata al commit* dal configuration-manager) → la parte "invocazione
  automatica" è superata; resta valido che la skill è distinta dal versioning (SRP). D-16 → cade
  l'installazione del *binding del trigger* (non serve con trigger manuale).
- **FR superate:** FR-026 (config-manager invoca la skill al commit), FR-027 (contratto di trigger
  "al commit"), FR-028 (setup installa il binding), e la parte "installa il binding" di FR-040.
- **FR riformulate:** FR-037 (lint+freschezza incrementale all'invocazione di `/wiki`, non "al commit").
- **Criteri:** SC-008 (era "dopo init, un commit innesca la generazione") → riformulato su `/wiki`.
- **Rischi:** R-03 (trigger perso se il binding non è installato) → decaduto (nessun binding).

Coerente con la "calibra al valore": il trigger manuale è più semplice del binding automatico e copre il
flusso primario. L'automazione non presidiata (`claude -p` headless) resta fuori scope.

### D-20 — Eliminazione del gate al commit (risolve DA-GATE)
**Decisione canonica.** Il "gate al commit" (D-17) **blocca il commit** se lint/freschezza superano una
soglia: presuppone una generazione *automatica al commit*. Con D-19 il wiki si aggiorna con `/wiki`
**dopo** il commit (su `git diff HEAD~1`): non c'è un commit da bloccare. Il gate è quindi **eliminato
dallo scope**.

- **Superati:** D-17, FR-041, FR-042, SC-004.
- **Cosa resta:** lint + verifica di freschezza (FR-035/036/037) restano, ma come **parte normale di
  `/wiki`** (eseguono e riportano i problemi); **nessun blocco**, nessuna soglia di gate. L'utente
  decide se intervenire (resta human-in-the-loop, senza auto-fix).
- **Allineati:** scope §5 item 8, RNF-003 (soglia gate), R-01 (mitigazione), MoSCoW, D-14.

### D-21 — Modello a corpus unico per il retrieval (2026-06-10; rivede l'uso di D-3/D-7)
**Decisione canonica (utente).** Il wiki **vive dentro il progetto ospite by design**: l'install della
futura CLI lo crea così (epica `sertor-cli`, DA-7). Di conseguenza il wiki è già **parte del corpus
primario** dell'ospite come documentazione (`doc_type=doc`): per il caso standard **non serve** una
collezione separata interrogata congiuntamente — la separazione duplicherebbe i contenuti
(quasi-duplicati osservati live sul dogfood) senza aggiungere informazione.

- **Cosa cambia:** il modello "collezioni separate + query congiunta" (D-3/D-7, FR-010, SC-003) non è
  più il **default**: il default è **corpus unico** (wiki dentro il corpus dell'ospite; `search_docs`
  vede il wiki per natura, `search_combined` vede tutto senza duplicati). Sul dogfood Sertor:
  `SERTOR_EXTRA_CORPORA` rimossa, la collezione `wiki__*` resta come capacità esercitabile (rag-sync),
  non come parte del retrieval.
- **Cosa resta:** la **capacità** di query congiunta multi-collezione (feature `specs/010`,
  implementata e testata) resta nel prodotto per ospiti con corpora **davvero disgiunti** (es. wiki o
  doc-repo esterni al repository indicizzato). SC-003 va letto così: soddisfatto **per costruzione** nel
  modello a corpus unico; via fan-out solo nei casi disgiunti.
- **Riferimenti:** epica `sertor-cli` DA-7 (install crea il wiki dentro l'ospite); CLAUDE.md rituale
  punto 5 (re-index del solo corpus primario).

---

## 13. Domande aperte

| ID | Domanda | Priorità | Stato |
|----|---------|---------|-------|
| DA-FR004 | **Trigger esatto per FR-004**: hook Stop/SessionEnd, comando /wiki, o entrambi? | Media | ✅ **RISOLTA (2026-06-09, D-19)**: comando manuale `/wiki`, ambito = ultimo commit |
| DA-GATE | **Coerenza del gate (D-17/FR-041/FR-042/SC-004) col trigger manuale** | Media | ✅ **RISOLTA (2026-06-09, D-20)**: gate **eliminato** (opzione a); lint/freschezza restano come report non bloccante di `/wiki` |

Le domande aperte di FEAT-003 sono tutte chiuse (DA-W2..W6, elicitazione 2026-05-31).
I temi T0..T7 di FEAT-010 sono tutti risolti (iterazione 13, 2026-06-04). DA-FR004 risolta (D-19).

---

## 14. Changelog

### FEAT-003 (origine, 2026-05-31)
Elicitazione iniziale: struttura wiki, record, ingest (semantica vecchia), distillazione,
indicizzazione RAG, idempotenza. Domande DA-W2..W6 chiuse.

### FEAT-010 `llm-wiki` (2026-06-04, iterazioni 0..13)
- **Iter 0**: scheletro; D-1 (convenzione `manual_edited`).
- **Iter 1**: D-2 (popolamento agentico, riuso FEAT-003); FR-001..007.
- **Iter 2**: D-3 (due momenti generazione/indicizzazione, collezioni separate); FR-008..011.
- **Iter 3**: D-4 (verità stratificata, gerarchia, obsolescenza); FR-012..017.
- **Iter 4**: D-5 (refresh git-driven, git prerequisito) + D-6 (rinomina `sources/`→`ingested_sources/`); FR-018..022.
- **Iter 5**: D-7 (retrieval puro Karpathy: solo wiki generato + codice); FR-023..024.
- **Iter 6**: D-8 (skill client-agnostica, trigger portabile, setup rilascia binding) + D-9 (no-code); FR-025..029.
- **Iter 7**: D-10 (consolidante, FEAT-003 storico) + D-11 (ingest ridefinita, import≠compile); FR-030..031.
- **Iter 8**: D-12 (superfici skill+CLI+MCP); FR-032.
- **Iter 9**: D-13 (query via RAG, navigazione Obsidian, nessuna superficie nativa); FR-033..034.
- **Iter 10**: D-14 (lint strutturale + freschezza, trigger incrementale/on-demand/periodico); FR-035..038.
- **Iter 11**: D-15 (distill-da-artifact sussunto) + D-16 (setup `sertor wiki init`); FR-039..040.
- **Iter 12**: D-17 (gate al commit, blocca/avvisa/propone, override tracciato); FR-041..042.
- **Iter 13**: formalizzazione EARS completa, SC-001..010, MoSCoW, rischi, assunzioni, dipendenze. Status READY.

### Consolidamento (2026-06-05)
FEAT-010 folded dentro `wiki-creazione/requirements.md` (questo file). Vince FEAT-010 su tutti i
conflitti. FEAT-003 assorbito come storico (D-10). Stato: **in progress**.

### Rimozione per design — D-18 (2026-06-09)
Eliminate dallo scope le convenzioni a cartelle-input **`manual_edited/`** e **`ingested_sources/`**
(semplificazione; allineamento alla realtà del wiki, già consolidato in `sources/`). Decisione canonica
**D-18**. Marcate `⛔ DELETED BY DESIGN`: D-1, D-6, D-11, FR-007, FR-015, FR-016, FR-020, FR-021, FR-030,
FR-031; **semplificate/riformulate**: D-4, D-5, D-7, D-9, FR-001, FR-009, FR-012, FR-017, FR-022, FR-023;
SC-002 obsoleto, SC-010 riformulato, R-06 decaduto; glossario/scope/MoSCoW/assunzioni allineati. L'ingest
torna alla semantica Karpathy (riassunto in `sources/`, REQ-020..023 di nuovo operativi).

### Trigger del wiki — D-19 (2026-06-09)
Chiusa DA-FR004. Il trigger di generazione/aggiornamento del wiki è il **comando manuale `/wiki`** (non
hook, non binding automatico al commit); ambito = **changeset dell'ultimo commit** (`git diff HEAD~1`,
calcolato dalla parte D, configuration-manager come fornitore di diff); **cosa modificare** lo decide la
parte N (page-craft/wiki-craft/playbook). Decisione canonica **D-19**. Superato il modello automatico:
`⛔` FR-026, FR-027, FR-028; **rivisti** D-8 (resta SRP, cade l'invocazione-al-commit), D-16 (cade il
binding), FR-040; **riformulati** FR-004, FR-018, FR-037, FR-025, SC-008; **decaduto** R-03; allineati
scope/assunzioni/dipendenze/MoSCoW/D-13/D-14.

### Gate eliminato — D-20 (2026-06-09)
Risolta DA-GATE (opzione a): il **gate al commit è eliminato** — incoerente col trigger manuale `/wiki`
post-commit (D-19). Decisione canonica **D-20**. `⛔` D-17, FR-041, FR-042, SC-004; allineati scope §5
item 8, RNF-003, R-01, MoSCoW, D-14. Lint + verifica di freschezza (FR-035/036/037) restano come parte
**non bloccante** di `/wiki`.
