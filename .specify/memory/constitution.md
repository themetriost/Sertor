<!--
SYNC IMPACT REPORT — Costituzione di Sertor
============================================
Versione: (template non versionato) → 1.0.0   [ratifica iniziale]
Tipo di bump: iniziale (MAJOR 1.0.0)

Principi (9, tutti aggiunti in questa ratifica):
  I.    Il core a dipendenze verso l'interno (la libreria è il prodotto)
  II.   Provider e backend intercambiabili dietro boundary; local-first
  III.  Semplicità giustificata (YAGNI) e unità piccole
  IV.   Gestione errori esplicita; niente null silenzioso
  V.    Testabilità e qualità provata da misure
  VI.   Idempotenza, determinismo e non-distruttività
  VII.  Leggibilità come comunicazione; lascia il codice più pulito
  VIII. Configurabilità centralizzata del core
  IX.   Osservabilità: ogni operazione a runtime è loggata

Sezioni aggiunte:
  - Sicurezza, segreti e provenienza
  - Governance

Template dipendenti:
  ✅ .specify/templates/plan-template.md  — sezione "Constitution Check" allineata ai 9 principi
  ✅ .specify/templates/spec-template.md  — nessuna modifica necessaria (resta agnostico)
  ✅ .specify/templates/tasks-template.md — nessuna modifica necessaria (resta agnostico)

Tracciabilità: ogni principio cita i requisiti/criteri Sertor che codifica
  (REQ-E*, CS, OBJ, SC, REQ-*).
Fonti d'ispirazione: wiki "Clean Code" e "Clean Architecture" (Transcriptio).
Follow-up TODO: nessuno.
-->

# Costituzione di Sertor

Principi vincolanti per la costruzione del **core** (motori RAG + skill LLM Wiki) e del suo veicolo
**CLI**. Le parole chiave **MUST / SHOULD / MUST NOT** sono usate in senso RFC-2119.

## Core Principles

### I. Il core a dipendenze verso l'interno (la libreria è il prodotto)

Il **core** Sertor — nucleo di retrieval, motori RAG (vettoriale/ibrido/grafo/agentico) e skill
LLM-Wiki — è **policy** e MUST essere usabile e testabile come **libreria autonoma**, senza dipendere
dalla CLI, da una UI o da alcun servizio esterno attivo. Le dipendenze a livello di codice sorgente
MUST puntare **verso l'interno**: il core MUST NOT importare alcun SDK concreto di provider (LLM,
embeddings, vector store) né il pacchetto CLI; gli adapter concreti e la CLI dipendono dalle
**astrazioni** del core, mai il contrario. Il wiring delle implementazioni concrete vive solo in un
componente **main/configurazione** dedicato.

*Razionale:* Dependency Rule + Plugin/Screaming Architecture (Clean Architecture). È l'espressione
letterale di REQ-E1 e CS-5 (riusabile come libreria, repo-agnostico): se il core conoscesse `click`
o `chromadb`, il prodotto sarebbe la CLI, non la capacità. **Test non-negoziabile:** ogni use case è
esercitabile con provider mock, senza CLI e senza cloud.

### II. Provider e backend intercambiabili dietro boundary; local-first

Ogni dipendenza esterna (LLM, provider di embeddings, vector store, graph store) MUST stare dietro
un'**astrazione di proprietà di Sertor** (un Adapter al boundary); i tipi di terze parti MUST NOT
trapelare nel core. La scelta fra implementazioni (locale ↔ cloud, un vendor ↔ un altro) MUST essere
**guidata da configurazione**, senza modifiche al codice. Ogni capacità MUST poter girare
**interamente in locale** (nessun cloud); il cloud (incl. Azure) è un **default configurabile**, non
un requisito. Un vector store è richiesto **solo** per le modalità che usano embeddings; la modalità
puramente strutturale (grafo) opera senza.

*Razionale:* "Details Are Replaceable" (Clean Architecture) + "Boundaries" (Clean Code);
REQ-E2/E4/E7, CS-7. Il ricambio di provider (OpenAI→Anthropic, Chroma→pgvector) è inevitabile e MUST
costare una modifica di configurazione, non una ri-architettura.

### III. Semplicità giustificata (YAGNI) e unità piccole

Nessuna astrazione, dipendenza o layer viene aggiunto senza **evidenza presente** di necessità (un
caso d'uso reale oggi). Funzioni e moduli MUST essere piccoli e a **singola responsabilità** (SRP),
mantenuti a un solo livello di astrazione; la logica MUST NOT essere duplicata (DRY) — la logica
condivisa di retrieval/chunking/embeddings vive nel nucleo, non copiata fra i motori. Le dipendenze
pesanti o in conflitto (es. il motore a grafo) MUST essere **isolabili** per evitare conflitti
d'ambiente.

*Razionale:* Clean Code (small functions, SRP, DRY, smell G5) + regola "niente over-engineering";
visione modulare/selettiva, REQ-E2/E7.

### IV. Gestione errori esplicita; niente null silenzioso

La gestione degli errori MUST essere **basata su eccezioni** con eccezioni **ricche di contesto** e
di dominio; gli errori di terze parti MUST essere **avvolti** nei tipi di eccezione di Sertor al
boundary. Le operazioni MUST NOT restituire o propagare `null`/`None` per segnalare un'assenza in
modo silenzioso, né lasciare stato parziale/corrotto: un indice mancante, un provider non
disponibile, un RAG irraggiungibile o un wiki vuoto MUST fallire **in modo esplicito**, con un
messaggio chiaro e azionabile e **senza** effetti collaterali sullo stato esistente.

*Razionale:* Clean Code Ch.7 (exceptions over return codes, provide context, don't return/pass null);
FEAT-002 REQ-004 (abort, niente indice parziale), FEAT-003 REQ-043.

### V. Testabilità e qualità provata da misure

Ogni capacità MUST avere test automatici **F.I.R.S.T.** (Fast, Independent, Repeatable,
Self-validating, Timely); il core MUST essere testabile con **provider mock**, senza cloud attivo.
La qualità del retrieval MUST essere **misurata** su un corpus campione con ground-truth (hit@k,
MRR), con il **prototipo come baseline** e le soglie di accettazione fissate in fase di design — una
feature senza misura **non è "fatta"**, è un prototipo. Il **TDD** (le tre leggi) è SHOULD
(raccomandato come pratica), non imposto.

*Razionale:* Clean Code Ch.9 (F.I.R.S.T., i test come rete di sicurezza) + decisione "misurare prima"
(baseline = prototipo); CS-1/CS-4, OBJ-2/OBJ-6.

### VI. Idempotenza, determinismo e non-distruttività

Rieseguire un'operazione (indicizzazione, wiki record/ingest/index) sullo **stesso input** MUST
produrre un risultato **stabile**: nessun chunk/pagina/voce di log duplicati, identificatori stabili
derivati dai path relativi. **Installazione ≠ esecuzione**: installare o aggiungere una capacità
MUST NOT avviare da sola un'ingestione costosa. Operare su un repository esistente MUST essere
**non distruttivo** (nessuna sovrascrittura silenziosa di file dell'utente). Il **costo/latenza**
delle chiamate LLM MUST essere considerato prima di invocarle (preferire i percorsi deterministici
più economici dove adeguati).

*Razionale:* REQ-E6 (idempotenza), CLI CS-2/REQ-E2 (install≠run), CS-4 (non-distruttività),
FEAT-001 REQ-004/010, FEAT-003 SC-3b.

### VII. Leggibilità come comunicazione; lascia il codice più pulito

Il codice è scritto **per chi lo legge**. I nomi MUST essere rivelatori d'intenzione e usare il
**vocabolario di dominio** del retrieval (retrieve, rank, fuse, rerank, synthesize, index) invece di
verbi generici (process, execute, handle). I commenti sono riservati all'intenzione che il codice non
può esprimere; codice commentato e commenti ridondanti vengono rimossi. Ogni modifica lascia il
codice toccato **almeno pulito quanto l'ha trovato** (Boy Scout Rule).

*Razionale:* Clean Code Ch.1/2/4. I domini RAG si offuscano facilmente con naming vago: la chiarezza
è la leva di qualità più economica.

### VIII. Configurabilità centralizzata del core

Tutte le scelte operative del core — provider LLM/embeddings, backend di retrieval/vector store,
percorsi, parametri di chunking (dimensione, overlap, set di linguaggi), `k` di retrieval, batch
size, pattern di esclusione — MUST essere governate da un'**unica configurazione centralizzata**,
leggibile da file e/o variabili d'ambiente, **senza modificare il codice** e **senza default
hardcoded** nei singoli componenti. Cambiare ambiente (locale ↔ cloud), provider o parametri MUST
essere un atto di **configurazione**, non di codifica.

*Razionale:* Clean Architecture (la config è un "detail" confinato nel Main Component; la policy è
indipendente dai dettagli) + REQ-030 (FEAT-001) e CS-4 (configurabile senza toccare il codice).
Rende reali i Principi I e II: senza configurazione centralizzata, l'intercambiabilità è teorica.

### IX. Osservabilità: ogni operazione a runtime è loggata

Ogni operazione a runtime MUST emettere **log strutturati** sufficienti a diagnosticare un fallimento
senza leggere il codice sorgente. In particolare, **sia la creazione di embeddings/indicizzazione sia
il retrieval (interrogazione)** MUST registrare almeno: operazione, provider/backend usato, numero di
documenti/chunk processati, dimensione dell'embedding, tempi di esecuzione ed eventuali errori. I log
MUST NOT contenere segreti. L'osservabilità fa parte della definizione di "production-grade", non è un
extra.

*Razionale:* Clean Code (error handling con contesto) + Clean Architecture (Humble Object: logica
osservabile separata dal glue); FEAT-001 REQ-031, FEAT-002 NFR-007, FEAT-003 RNF-004.

## Sicurezza, segreti e provenienza

I segreti (chiavi API, credenziali) MUST NOT essere scritti in file versionati; transitano solo via
variabili d'ambiente o `.env` non committato. Gli artefatti rigenerabili (indici, vector store,
cache, log, virtualenv, corpora vendored) MUST essere git-ignored. L'ingestione MUST mantenere il
corpus pulito (esclusione configurabile di binari/artefatti/segreti).

*Razionale:* REQ-E5 + disciplina `.gitignore` del workspace.

## Governance

Questa costituzione **prevale** sulle decisioni ad-hoc; in caso di conflitto tra un design/piano e un
principio, vince il principio (o il principio viene prima emendato).

- **Workflow di produzione:** dopo la ratifica si lavora a **branch + PR** — niente push diretti su
  `main`/`master` (l'eccezione della fase prototipo termina con la ratifica).
- **Constitution Check:** ogni `plan.md` MUST superare un gate di Constitution Check **prima** della
  ricerca (Phase 0) e **dopo** il design (Phase 1); un design che viola un principio non-negoziabile
  (in particolare I e IV) MUST essere rivisto, oppure il principio emendato.
- **Emendamenti:** via PR che documenta la modifica e il razionale; versionati con **semantic
  versioning** (MAJOR: rimozione/ridefinizione di un principio; MINOR: nuovo principio/sezione;
  PATCH: chiarimenti).
- **Conformità:** il RAG di dogfooding sul prototipo è il riferimento di "cosa è buono"; le nuove
  capacità sono riviste rispetto a questi principi.

**Version**: 1.0.0 | **Ratified**: 2026-05-31 | **Last Amended**: 2026-05-31
