<!--
SYNC IMPACT REPORT — Costituzione di Sertor
============================================
Versione: 1.3.0 → 1.4.0
Tipo di bump: MINOR (nuova sezione «Missione & stella polare» + check di allineamento nel gate)

Modifiche di questo emendamento (2026-06-20):
  + Sezione «Missione & stella polare (North Star)» — inserita subito dopo l'intro e prima di
    «## Core Principles». Definisce il differenziatore di Sertor (fusione code+doc in un unico
    corpus interrogabile insieme) e la stella polare vincolante: ogni capacità, feature e decisione
    DEVE servire la missione e rafforzare la fusione code+doc; in caso di conflitto vince la missione
    (o va riconsiderata esplicitamente).
  + Check di allineamento alla missione nel Constitution Check (sezione Governance): gate
    «Allineamento alla missione (fusione code+doc, qualità del retrieval reso all'agente)».
  Template dipendenti: plan-template.md — aggiunto gate «Allineamento alla missione» + rif. versione → v1.4.0.
  Origine: decisione utente (2026-06-20) — ancorare mission/vision in costituzione perché ogni
    decisione di design vada nella direzione della fusione code+doc come punto di forza competitivo.

Modifiche dell'emendamento precedente (2026-06-20, v1.2.0 → v1.3.0, MINOR):
  + Principio XII — Fail Loud, Fix the Cause: segnala ed elimina la causa, non sopprimere.
    Una capacità che fallisce va riparata nella causa, non disattivata/silenziata. La degradazione
    graziosa è ammessa solo se il fallimento è segnalato (warning/finding); la soppressione silenziosa
    e il disabilitare per schivare un errore sono vietati. Generalizza a ogni capacità e veicolo la
    regola standing «errori MCP = segnale, non rumore» già presente in CLAUDE.md/dogfooding.
  Template dipendenti: plan-template.md — aggiunto gate "XII — Fail Loud, Fix the Cause".
  Origine: episodio OTel (2026-06-20) in cui la mossa corretta fu riparare il collector, non
    spegnere l'export + decisione utente (2026-06-20).

Modifiche dell'emendamento precedente (2026-06-15, v1.1.1 → v1.2.0, MINOR):
  + Principio XI — Consumo attraverso i vehicles (CLI/MCP), non la libreria a runtime; unica eccezione
    gli unit/integration test. Motivazione: l'accesso diretto alla libreria (es. `build_indexer().index()`)
    bypassa il wiring trasversale dei consumatori (osservabilità, config, errori) → operazioni non
    tracciate (gap rilevato: re-index via libreria non comparso in telemetria).
  Template dipendenti: plan-template.md — aggiunto gate "XI — Consumo via vehicles".
  Origine: gap osservabilità (re-index via `build_indexer().index()` non tracciato) + decisione utente (2026-06-15).

Modifiche dell'emendamento precedente (2026-06-14, v1.1.0 → v1.1.1, PATCH):
  ~ Principio VII — chiarito lo stile delle funzioni: piccole e a bassa profondità di annidamento,
    guard clause / early return preferiti alla nidificazione profonda; il single-exit dogmatico
    (SESE) NON è richiesto (il problema è il nesting, non i return multipli — Dijkstra bandiva il
    GOTO, non i return). Allinea la regola alla pratica già in uso nel codebase (Clean Code).
  Origine: refactor di `_resolve_config` (wiki_tools) + discussione utente su SESE/nesting (2026-06-14).

----- Storico -----
Versione: 1.0.0 → 1.1.0
Tipo di bump: MINOR (nuovo principio aggiunto)

Modifiche dell'emendamento precedente (2026-06-05):
  + Principio X — Capacità host-agnostiche (la portabilità è un vincolo, non un'aspirazione)
  ~ Intro: scope allargato dal "core + CLI" a "tutte le capacità + veicoli (CLI, MCP)"
  Motivazione: codifica la mission (Sertor installabile su QUALSIASI progetto: code+doc,
  solo-doc, solo-code) e generalizza il Principio I a tutte le capacità (skill e LLM Wiki incluse).

Principi (12):
  I.    Il core a dipendenze verso l'interno (la libreria è il prodotto)
  II.   Provider e backend intercambiabili dietro boundary; local-first
  III.  Semplicità giustificata (YAGNI) e unità piccole
  IV.   Gestione errori esplicita; niente null silenzioso
  V.    Testabilità e qualità provata da misure
  VI.   Idempotenza, determinismo e non-distruttività
  VII.  Leggibilità come comunicazione; lascia il codice più pulito
  VIII. Configurabilità centralizzata del core
  IX.   Osservabilità: ogni operazione a runtime è loggata
  X.    Capacità host-agnostiche
  XI.   Consumo attraverso i vehicles (CLI/MCP), non la libreria a runtime
  XII.  Fail Loud, Fix the Cause — segnala ed elimina la causa, non sopprimere

Sezioni (1):
  «Missione & stella polare» — cornice d'orientamento vincolante (NUOVA in v1.4.0)

Template dipendenti:
  ✅ .specify/templates/plan-template.md  — aggiunto gate «Allineamento alla missione» + rif. versione → v1.4.0
  ✅ .specify/templates/spec-template.md  — nessuna modifica necessaria
  ✅ .specify/templates/tasks-template.md — nessuna modifica necessaria

Artefatti correlati:
  ✅ README.md (radice) — Vision/Mission: fonte del Principio X e della sezione «Missione & stella polare»
Tracciabilità: ogni principio cita i requisiti/criteri Sertor che codifica (REQ-E*, CS, OBJ, SC, REQ-*).
Fonti d'ispirazione: wiki "Clean Code" e "Clean Architecture" (Transcriptio).
Follow-up TODO: refactor host-agnostico delle skill wiki / playbook / rituale (oggi Sertor-coupled),
  per conformità al Principio X — vedi backlog.
-->


# Costituzione di Sertor

Principi vincolanti per la costruzione delle **capacità** di Sertor (motori RAG, indicizzazione, skill
LLM Wiki) e dei loro veicoli (**CLI**, **MCP**). Sertor è un framework **installabile su qualsiasi
progetto** ospite: i principi valgono per ogni capacità, non solo per il core (vedi Principio X). Le
parole chiave **MUST / SHOULD / MUST NOT** sono usate in senso RFC-2119.

## Missione & stella polare (North Star)

Sertor è un **framework installabile** che dota **qualsiasi progetto** — *code+doc*, *solo-doc*, *solo-code* — di **auto-conoscenza interrogabile**, **portabile e senza lock-in** (fonte di verità: [`README.md`](../../README.md); sintesi: [[mission-vision]]). Il **differenziatore** è la **fusione di codice e documenti** (requisiti, spec, wiki) in **un unico corpus interrogabile insieme**: il codice dice *cosa fa*, la documentazione dice *perché* — e il valore è restituirli **fusi** all'agente. Generare e servire sono **delegati per design** (all'agente frontier e a MCP): il fronte competitivo NON è generate/serve, ma la **qualità di ciò che si restituisce all'agente** — precisione/recall, segnale di confidenza, freschezza.

**Stella polare (vincolante):** ogni capacità, feature e decisione di design DEVE **servire questa missione** e, dove tocca il retrieval, **rafforzare la fusione code+doc** invece di derivare su concern periferici. Questa cornice è il *fine* che i principi qui sotto servono; in caso di conflitto tra un design e la missione, vince la missione (o la missione va prima riconsiderata esplicitamente).

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

Le funzioni MUST essere **piccole e a bassa profondità di annidamento**: si **preferiscono i guard
clause / early return** alla nidificazione profonda di condizioni, e si estrae un helper nominato
quando un blocco cresce o si annida. Il **single-exit dogmatico (SESE) NON è richiesto**: il problema
da evitare è la **profondità del nesting**, **non** il numero di `return`. *(Chiarimento v1.1.1: la
*structured programming* di Dijkstra bandiva il **GOTO**, non i `return` multipli; `return` multipli
che *riducono* l'annidamento sono idiomatici e preferiti. Un'uscita unica è legittima quando rende il
flusso più chiaro, ma non va imposta a scapito della leggibilità o della coerenza col resto del
codice, che usa guard clause.)*

*Razionale:* Clean Code Ch.1/2/4 (small functions, low nesting, intention-revealing names). I domini
RAG si offuscano facilmente con naming vago e con condizioni annidate: chiarezza e poca profondità
sono la leva di qualità più economica.

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

### X. Capacità host-agnostiche (la portabilità è un vincolo, non un'aspirazione)

Ogni capacità di Sertor — nucleo di retrieval, motori RAG, indicizzazione, skill LLM Wiki e gli
strumenti che le orchestrano — MUST essere **disaccoppiata dal dominio e dalla struttura del progetto
ospite**. L'ospite è un **consumatore**: si **configura**, non si **presume**. Il corpo di una
capacità MUST NOT incorporare assunzioni specifiche di un progetto (percorsi fissi, nomi di dominio,
struttura di cartelle dell'ospite); ciò che varia fra ospiti MUST vivere nella
**configurazione/istanziazione**, non nel codice della capacità. Il **dogfooding** (Sertor applicato
a sé stesso) è strumentale e MUST NOT essere usato come licenza per violare questo confine.
**Test non-negoziabile:** una capacità MUST poter operare su un progetto-ospite diverso (code+doc,
solo-doc, solo-code) senza modifiche al suo corpo — solo cambiando configurazione.

*Razionale:* è la traduzione operativa della **mission** (Sertor installabile su qualsiasi progetto) e
**generalizza il Principio I** — finora scoped al solo core-libreria ("la libreria è il prodotto,
repo-agnostico") — a **tutte** le capacità, incluse skill e LLM Wiki. Senza questo principio il
dogfooding tenderebbe a far sedimentare assunzioni Sertor-specifiche dentro capacità che devono
restare portabili. Fonti: README (Vision/Mission), REQ-E1/CS-5.

### XI. Consumo attraverso i vehicles (CLI/MCP), non la libreria a runtime

I consumatori **a runtime** — l'agente LLM, gli script, qualunque ospite o automazione — MUST accedere
alle capacità di Sertor **solo** attraverso i suoi **vehicles**: la **CLI** (`sertor-rag`,
`sertor-wiki-tools`) o il **server MCP**. MUST NOT importare e invocare la libreria `sertor_core`
direttamente a runtime (es. `build_indexer().index(...)`). **Unica eccezione: gli unit/integration
test**, che esercitano libreria e funzioni direttamente — è il modo in cui i Principi I e V garantiscono
la testabilità in isolamento.

*Razionale:* i vehicles cablano in modo **uniforme** i comportamenti trasversali — osservabilità
(`enable_observability`), configurazione centralizzata (Principio VIII), avvolgimento errori al boundary
(Principio IV), redazione segreti. L'accesso diretto alla libreria li **bypassa silenziosamente**: caso
reale, un re-index via `build_indexer().index()` non viene tracciato in telemetria perché salta
`enable_observability` (cablato solo nei vehicles). Confinare il consumo ai vehicles rende ogni
operazione osservabile e configurata in modo coerente; i test sono l'eccezione perché verificano
proprio l'unità isolata. *Nota:* non contraddice il Principio I (la libreria resta il prodotto,
architetturalmente autonoma e importabile) — questo principio governa **chi consuma a runtime**, non la
struttura delle dipendenze.

### XII. Fail Loud, Fix the Cause — segnala ed elimina la causa, non sopprimere

Quando una capacità fallisce, si **rimuove la causa**; MUST NOT disattivare, azzittire o aggirare la
capacità solo per **far sparire l'errore**. Il **feedback precoce e visibile è un valore**, non rumore:
i fallimenti MUST **emergere presto** (early feedback). La degradazione graziosa è ammessa **solo se il
fallimento è segnalato** (warning/finding) — la **soppressione silenziosa è vietata**, così come
spegnere una funzione per evitare di affrontarne l'errore. Rimuovere o disabilitare una capacità è
legittimo **solo come decisione esplicita e tracciata**, mai come riflesso per schivare un errore.

*Razionale:* un errore visto presto costa meno; spegnere la funzione che erra **distrugge il segnale**
e sposta il difetto più a valle. Generalizza a ogni capacità e veicolo la regola standing «errori =
segnale, non rumore» (oggi specifica dell'MCP/dogfooding). Non contraddice il Principio IV (gestione
errori esplicita) né la *policy errori voluta* (core tollerante con warning ↔ motore baseline strict):
la degradazione che **segnala** è conforme; ciò che il principio vieta è il **silenzio** o il
**disattivare per non vedere**. Origine: episodio OTel (2026-06-20) — la mossa corretta fu riparare il
collector, non spegnere l'export.

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
  (in particolare I e IV) MUST essere rivisto, oppure il principio emendato. Il check include il gate
  di **Allineamento alla missione:** il design serve la missione (auto-conoscenza portabile; **fusione
  code+doc**; qualità del retrieval reso all'agente) e non deriva su concern periferici? Marca
  PASS / N/A con motivo.
- **Emendamenti:** via PR che documenta la modifica e il razionale; versionati con **semantic
  versioning** (MAJOR: rimozione/ridefinizione di un principio; MINOR: nuovo principio/sezione;
  PATCH: chiarimenti).
- **Conformità:** il RAG di dogfooding sul prototipo è il riferimento di "cosa è buono"; le nuove
  capacità sono riviste rispetto a questi principi.

**Version**: 1.4.0 | **Ratified**: 2026-05-31 | **Last Amended**: 2026-06-20
