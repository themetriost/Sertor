# Feature Specification: Motore RAG a grafo (code-graph strutturale)

**Feature Branch**: `014-motore-grafo`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "Motore RAG a grafo — code-graph strutturale (FEAT-005 dell'epica sertor-core). Fonte EARS completa: requirements/sertor-core/motore-grafo/requirements.md (31 REQ funzionali + 10 NFR + 8 LSC, domande DA-1..DA-5 tutte risolte — vedi §10). Punti chiave: navigazione strutturale deterministica del codice (find_symbol, who_calls, related_docs, get_context — i 4 tool storici che tornano nel server MCP), code-graph AST senza LLM; porta CodeGraph nel domain; grafo ORTOGONALE a SERTOR_ENGINE; build INTEGRATO in index(); tutti i 10 linguaggi del chunker con copertura archi dichiarata; ground-truth strutturale ≥5 simboli senza rete."

> **Fonte a monte:** `requirements/sertor-core/motore-grafo/requirements.md` (EARS, rev. 2026-06-12,
> DA-1..DA-5 risolte). I requisiti funzionali qui sotto mappano 1:1 sui REQ EARS (riferimento
> `REQ-NNN` accanto a ogni FR). Il GraphRAG "alla Microsoft" (knowledge graph LLM) è fuori ambito.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Il grafo del codice, costruito insieme all'indice (Priority: P1)

L'owner/maintainer indicizza il repository (`index()`): nello **stesso passaggio**, oltre agli
indici vettoriale e lessicale, il sistema costruisce il **grafo strutturale del codice** — nodi
per moduli, classi, funzioni, metodi e documenti; archi per contenimento, chiamate, import,
ereditarietà e menzioni doc→simbolo — e lo persiste su disco accanto agli altri indici, così
sopravvive ai riavvii e non è mai stantio rispetto al corpus. Da quel momento la domanda
fondamentale «**dove è definito il simbolo X?**» (`find_symbol`) riceve risposta esatta — path,
riga, tipo, nome qualificato — con un lookup deterministico, senza embeddings né cloud.

I nodi e gli archi di contenimento coprono **tutti i 10 linguaggi** del chunking sintattico
(derivano dai metadati già estratti); gli archi relazionali (chiamate, import, ereditarietà)
sono per-linguaggio, con la copertura effettiva **dichiarata** — mai assenza silenziosa.

**Why this priority**: senza grafo non esiste nulla del resto; `find_symbol` è il lookup
fondante (LSC-1) e da solo costituisce un MVP: indicizza → chiedi dove è definito un simbolo →
risposta esatta. La costruzione integrata (DA-2) è ciò che garantisce il grafo sempre vero.

**Independent Test**: su un corpus fixture con simboli noti, eseguire `index()` e verificare che
il grafo persista su disco (artefatto namespaced) e che `find_symbol` restituisca path e riga
corretti; ri-eseguire `index()` sullo stesso corpus → stesso grafo (idempotenza). Senza rete.

**Acceptance Scenarios**:

1. **Given** un repository con sorgenti e documentazione, **When** l'utente esegue
   l'indicizzazione, **Then** il grafo viene costruito nello stesso passaggio (nodi module/
   class/function/method/doc; archi contains/calls/imports/inherits/mentions) e persistito
   nella directory indici namespaced.
2. **Given** un grafo costruito, **When** si chiede `find_symbol` di un simbolo presente,
   **Then** tornano tutte le sue definizioni con path relativo, numero di riga, tipo e nome
   qualificato — in un solo lookup, senza chiamate a provider.
3. **Given** lo stesso corpus invariato, **When** si ricostruisce il grafo, **Then** nodi e
   archi sono identici (stessi id, stessa connettività).
4. **Given** un file in un linguaggio di cui gli archi di chiamata non sono supportati,
   **When** il grafo viene costruito, **Then** i suoi nodi e il contenimento ci sono comunque,
   e la copertura per-linguaggio dichiarata documenta il limite (niente assenza silenziosa).

---

### User Story 2 - Navigare le relazioni: chiamanti, documenti, contesto (Priority: P2)

L'agente (o l'owner) naviga il grafo oltre la definizione: «**chi chiama Y?**» (`who_calls`),
«**quali documenti parlano di Z?**» (`related_docs`) e «**dammi tutto il contesto del simbolo**»
(`get_context`: definizioni + chiamanti + chiamate uscenti + classi base + doc collegati, con
limiti configurabili per sezione). Le risposte sono deterministiche, citabili (formato
compatibile `path#chunk`) e distinguono i due casi di assenza: simbolo non trovato → risultato
vuoto esplicito; grafo mai costruito → errore esplicito e azionabile.

**Why this priority**: è il valore differenziante rispetto al retrieval per similarità — domande
strutturali che baseline e ibrido non possono soddisfare. Dipende dal grafo di US1.

**Independent Test**: su corpus fixture con relazioni note, verificare che `who_calls` includa i
chiamanti attesi, `related_docs` le pagine attese, `get_context` il bundle multi-hop con i limiti
per sezione rispettati; simbolo inesistente → vuoto; grafo assente → errore esplicito.

**Acceptance Scenarios**:

1. **Given** un grafo costruito, **When** si chiede `who_calls` di un simbolo, **Then** tornano
   i chiamanti diretti con path, riga, tipo e nome qualificato.
2. **Given** documentazione che menziona un simbolo per nome, **When** si chiede
   `related_docs`, **Then** tornano i documenti che lo menzionano.
3. **Given** un simbolo di classe, **When** si chiede `get_context`, **Then** il bundle include
   definizioni, chiamanti, chiamate uscenti, classi base e doc collegati, ciascuna sezione
   limitata al massimo configurato.
4. **Given** un nome non presente nel grafo, **When** si naviga, **Then** il risultato è vuoto
   ed esplicito (nessuna eccezione) — distinguibile dal caso «grafo non costruito», che invece
   produce un errore esplicito con l'azione da compiere.

---

### User Story 3 - I quattro tool tornano nel server MCP (Priority: P3)

L'agente LLM connesso al server MCP ritrova i **4 tool storici** — `find_symbol`, `who_calls`,
`related_docs`, `get_context` — accanto ai 3 di ricerca esistenti (che restano invariati).
Ogni tool delega al servizio di grafo del core (superficie sottile); se il grafo non è stato
costruito risponde con un errore strutturato e azionabile; se la dipendenza opzionale del grafo
non è installata, l'errore dice quale extra installare — mai fallimento muto.

**Why this priority**: è la promessa esplicita dell'epica («riporta find_symbol/who_calls nel
MCP») e il canale con cui il valore arriva all'agente; dipende da US1+US2 ma è una superficie,
non logica nuova.

**Independent Test**: avviare il server MCP e verificare che i 7 tool siano registrati; invocare
i 4 tool di grafo su corpus indicizzato e ottenere risposte citabili; senza grafo → errore
strutturato; senza extra → errore con istruzione d'installazione.

**Acceptance Scenarios**:

1. **Given** il server MCP avviato su un corpus con grafo, **When** il client elenca i tool,
   **Then** i 4 tool di grafo sono registrati accanto ai 3 di ricerca, invariati.
2. **Given** una chiamata `get_context` via MCP, **When** il simbolo esiste, **Then** la
   risposta è il bundle citabile (formato coerente con `path#chunk`).
3. **Given** un corpus senza grafo costruito, **When** un tool di grafo viene invocato,
   **Then** la risposta è un errore strutturato che indica di costruire il grafo (il server
   non va in crash).
4. **Given** l'extra del grafo non installato, **When** un tool di grafo viene invocato,
   **Then** l'errore è esplicito e azionabile (nomina l'extra da installare).

---

### User Story 4 - Qualità misurata: ground-truth strutturale (Priority: P4)

L'owner/maintainer dispone di un **ground-truth strutturale** versionato (≥5 simboli del corpus
sertor con definizioni, chiamanti e doc attesi) e di test che verificano — **senza rete** —
precisione dei chiamanti (≥80%), recall delle menzioni doc (≥80%) ed esattezza delle
definizioni. La copertura degli archi per-linguaggio è dichiarata e verificata almeno su un
caso per linguaggio dichiarato supportato.

**Why this priority**: «una feature senza misura non è fatta» (Principio V); chiude il cerchio
sulle promesse di US1/US2 e rende onesta la scelta multi-linguaggio (DA-3).

**Independent Test**: eseguire la suite del ground-truth (`pytest -m "not cloud"`) e verificare
le soglie LSC-2/LSC-3; la tabella di copertura per-linguaggio esiste ed è verificata.

**Acceptance Scenarios**:

1. **Given** il ground-truth versionato, **When** i test girano, **Then** per ogni simbolo:
   `find_symbol` dà il path e l'intervallo di righe attesi; `who_calls` include i chiamanti
   attesi (precisione ≥80% sul set); `related_docs` include i doc attesi (recall ≥80%).
2. **Given** la scelta multi-linguaggio, **When** la copertura è dichiarata, **Then** per ogni
   linguaggio dichiarato con archi supportati esiste almeno un caso di ground-truth che lo
   verifica.
3. **Given** una riorganizzazione del repository, **When** il ground-truth viene riletto,
   **Then** resta esprimibile (path relativi, nessuna assunzione strutturale).

---

### Edge Cases

- **Simbolo assente dal grafo**: risultato vuoto esplicito (non eccezione), distinguibile da
  «grafo non costruito» (errore esplicito azionabile) — due assenze, due semantiche.
- **Grafo mai costruito + query**: errore esplicito che dice di costruirlo (mai vuoto muto).
- **Simbolo con nome ambiguo** (più candidati oltre la soglia configurabile): gli archi `calls`
  verso di esso vengono **omessi** invece di generare connessioni spurie.
- **Nomi duplicati legittimi** (stesso nome definito in più file): `find_symbol` restituisce
  TUTTE le definizioni.
- **Corpus solo-doc** (nessun sorgente): il grafo contiene solo nodi doc; le navigazioni sui
  simboli tornano vuote esplicite — nessun errore (host-agnostico).
- **Linguaggio senza estrazione archi**: nodi e `contains` presenti comunque; copertura
  dichiarata, mai silenzio.
- **Re-index del corpus**: il grafo si ricostruisce nello stesso passaggio — mai stantio
  rispetto agli indici di retrieval.
- **Extra del grafo non installato**: errore esplicito con l'istruzione d'installazione
  (mai tool che spariscono silenziosamente o risposte degradate).
- **Riavvio del server MCP**: il grafo persistito si ricarica da disco, nessuna ricostruzione
  implicita (install ≠ run).

## Requirements *(mandatory)*

### Functional Requirements

#### Costruzione del grafo (Gruppo A)

- **FR-001** (REQ-001): alla costruzione del grafo il sistema DEVE estrarre almeno i nodi
  `module`, `class`, `function`, `method`, `doc` e gli archi `contains`, `calls`, `imports`,
  `inherits`, `mentions` (doc→simbolo per corrispondenza di nomi distintivi).
- **FR-002** (REQ-002): la costruzione DEVE riusare i metadati sintattici già prodotti dal
  chunking (nome qualificato, simbolo, tipo di nodo, righe) per popolare i nodi, evitando un
  secondo parsing completo dei sorgenti.
- **FR-003** (REQ-003): il grafo DEVE coprire TUTTI i 10 linguaggi del chunking sintattico:
  nodi e `contains` language-agnostic; archi relazionali per-linguaggio best-effort con
  copertura effettiva DICHIARATA per linguaggio, mai assente in silenzio. *(DA-3, decisione
  utente.)*
- **FR-004** (REQ-004): la risoluzione di `calls`/`imports` È intra-corpus best-effort per
  nome; sopra una soglia configurabile di candidati ambigui l'arco viene omesso, non inventato.
- **FR-005** (REQ-005): il grafo DEVE essere persistito nella directory indici namespaced
  (stessa dell'indice vettoriale) e sopravvivere al riavvio del server.
- **FR-006** (REQ-006): la costruzione del grafo È INTEGRATA nell'indicizzazione: `index()`
  produce anche il grafo nello stesso passaggio (mai stantio); un percorso di rebuild dedicato
  PUÒ esistere in aggiunta. *(DA-2.)*
- **FR-007** (REQ-007): se il grafo è assente quando arriva una query di grafo, il sistema
  DEVE sollevare un errore esplicito e azionabile («costruisci il grafo prima»), non un
  risultato vuoto silenzioso.
- **FR-008** (REQ-008): ricostruire il grafo sullo stesso corpus invariato DEVE produrre lo
  stesso insieme di nodi e archi (idempotenza).

#### Porta e architettura (Gruppo B)

- **FR-009** (REQ-010): il sistema DEVE esporre una porta `CodeGraph` (Protocol) nel dominio
  con almeno: build, find_symbol, who_calls, related_docs, get_context, exists. *(DA-1.)*
- **FR-010** (REQ-011): l'implementazione concreta vive in un adapter dedicato ed è cablata
  ESCLUSIVAMENTE nel composition root; nessun servizio/facade/motore la importa direttamente.
- **FR-011** (REQ-012): la dipendenza della libreria di grafi DEVE essere isolabile come extra
  installabile separatamente; il pacchetto base resta importabile senza.
- **FR-012** (REQ-013): il servizio di grafo È ORTOGONALE a `SERTOR_ENGINE`: non è un valore
  della manopola dei motori; è esposto come servizio distinto dal composition root.

#### Navigazione strutturale (Gruppo C)

- **FR-013** (REQ-020): `find_symbol(name)` DEVE restituire tutte le definizioni con match
  esatto del nome (kind class/function/method), ciascuna con path relativo, riga, kind e nome
  qualificato.
- **FR-014** (REQ-021): `who_calls(name)` DEVE restituire i nodi con arco `calls` uscente
  verso il simbolo, con path, riga, kind e nome qualificato.
- **FR-015** (REQ-022): `related_docs(name)` DEVE restituire i nodi doc con arco `mentions`
  verso il simbolo, con path e nome qualificato del simbolo.
- **FR-016** (REQ-023): `get_context(name)` DEVE restituire il bundle multi-hop (definizioni,
  chiamanti, chiamate uscenti, classi base, doc collegati), ogni sezione limitata a un massimo
  configurabile (default: 10 definizioni, 8 chiamanti/chiamate, 8 doc).
- **FR-017** (REQ-024): un simbolo assente dal grafo produce un risultato vuoto esplicito (non
  eccezione), distinguibile dal caso «grafo non costruito» (FR-007).
- **FR-018** (REQ-025): ogni nodo restituito include un riferimento citabile compatibile col
  formato del server MCP (`path#simbolo` o `path:riga`).

#### Integrazione nel server MCP (Gruppo D)

- **FR-019** (REQ-030): all'avvio del server MCP i 4 tool di grafo DEVONO essere registrati
  accanto ai 3 di ricerca esistenti, senza modificarne interfaccia o comportamento.
- **FR-020** (REQ-031): ogni tool di grafo DELEGA esclusivamente al servizio di grafo del
  core; nessuna logica di grafo reimplementata nel server.
- **FR-021** (REQ-032): grafo non costruito + tool invocato → risposta di errore strutturata
  (niente crash) che indica di costruire il grafo.
- **FR-022** (REQ-033): il servizio di grafo si costruisce nel composition root via una
  factory dedicata, con import pigro della dipendenza; extra assente e capacità richiesta →
  errore esplicito con l'istruzione d'installazione. *(DA-5.)*

#### Qualità misurata e ground-truth (Gruppo E)

- **FR-023** (REQ-040): ground-truth versionato con ≥5 simboli del corpus sertor (definizioni
  attese con path+righe, chiamanti attesi, doc attesi dove applicabile), come fixture nel repo.
- **FR-024** (REQ-041): i test del ground-truth verificano find_symbol/who_calls/related_docs
  per ogni simbolo, SENZA rete; le soglie LSC-2/LSC-3 (≥80%) si misurano su questo set.
- **FR-025** (REQ-042): il ground-truth usa path relativi e nessuna assunzione sulla struttura
  interna del progetto oltre il verificabile nel corpus.

#### Osservabilità (Gruppo F)

- **FR-026** (REQ-050): la costruzione del grafo emette un evento di log strutturato con
  almeno: corpus, path del grafo, conteggio nodi per kind, conteggio archi per tipo, tempo.
- **FR-027** (REQ-051): ogni navigazione emette un evento con: operazione, simbolo, numero
  risultati, tempo.
- **FR-028** (REQ-052): i log non contengono mai segreti (redazione esistente).

#### Retro-compatibilità (Gruppo G)

- **FR-029** (REQ-060): l'introduzione del grafo NON modifica le interfacce dei motori
  esistenti, della facade né di alcuna porta esistente: la porta `CodeGraph` è additiva.
- **FR-030** (REQ-061): il servizio di grafo è non distruttivo sul repository (nessuna
  modifica ai file utente); il grafo persistito vive nella directory indici namespaced.
- **FR-031** (REQ-062): `SERTOR_ENGINE=baseline|hybrid` produce comportamento identico a
  oggi per tutti i consumatori: il grafo è ortogonale alla selezione del motore.

### Key Entities

- **Nodo del grafo**: entità strutturale del corpus — `module` (file sorgente), `class`,
  `function`, `method`, `doc` (documento Markdown) — con path relativo, riga, kind e nome
  qualificato; citabile in formato compatibile `path#chunk`.
- **Arco del grafo**: relazione tipata tra nodi — `contains` (gerarchia sintattica), `calls`,
  `imports`, `inherits` (best-effort intra-corpus, ambigui omessi), `mentions` (doc→simbolo).
- **Grafo persistito**: artefatto JSON namespaced per corpus nella directory indici, costruito
  da `index()` nello stesso passaggio degli altri indici; idempotente, ricaricabile a riavvio.
- **Porta `CodeGraph`**: astrazione di dominio delle operazioni di costruzione e navigazione;
  l'adapter concreto (libreria di grafi) sta dietro l'extra dedicato.
- **Bundle di contesto** (`get_context`): risposta multi-hop composta per sezioni (definizioni,
  chiamanti, chiamate, basi, doc) con limiti configurabili per sezione.
- **Ground-truth strutturale**: fixture versionata di simboli noti con definizioni/chiamanti/
  doc attesi; misura precisione e recall senza rete; stratificata per linguaggio dichiarato.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (LSC-1): dato un simbolo presente nel corpus, la sua definizione (path + riga
  corretti) arriva in un solo lookup, senza alcuna iterazione di retrieval per similarità.
- **SC-002** (LSC-2): i chiamanti diretti restituiti raggiungono precisione ≥80% sul
  ground-truth (≥5 simboli), misurata senza rete su fixture versionata.
- **SC-003** (LSC-3): le pagine doc che menzionano un simbolo vengono trovate con recall ≥80%
  sullo stesso ground-truth.
- **SC-004** (LSC-4): i 4 tool storici sono registrati nel server MCP e invocabili dal client
  senza modifiche di configurazione; i 3 tool esistenti restano invariati.
- **SC-005** (LSC-5): costruzione e navigazione del grafo funzionano senza vector store, senza
  embeddings e senza alcun servizio cloud.
- **SC-006** (LSC-6): la costruzione è idempotente: stesso corpus → stesso grafo (stessi nodi,
  stessi archi).
- **SC-007** (LSC-7): il grafo funziona su qualunque corpus indicizzato col nucleo (verifica su
  un secondo corpus senza alcun adattamento).
- **SC-008** (LSC-8): l'intera suite di test del grafo passa senza rete su fixture versionata.

## Assumptions

- **Grafo in-memory + persistenza JSON (A-1/A-5, DA-4)**: il grafo caricato in memoria da un
  artefatto JSON namespaced è adeguato per corpus < 50.000 nodi; lo schema JSON di dettaglio è
  decisione di design; corpora più grandi sono fuori ambito MVP.
- **Libreria di riferimento networkx (A-2)**: leggera, usata nel prototipo; il vincolo
  architetturale (porta + extra isolato + import pigro) vale per qualunque libreria.
- **Risoluzione best-effort (A-3)**: gli archi `calls`/`imports` coprono solo il corpus
  (niente librerie esterne); gli ambigui sono omessi deliberatamente — la precisione prevale
  sulla completezza.
- **Nodi dai metadati del chunker (A-4, R-3)**: i nodi derivano dai metadati sintattici
  esistenti; per gli archi relazionali è ammesso un passaggio AST dedicato dove i metadati non
  bastano (scelta di design).
- **Interfaccia tool come il prototipo (A-6)**: i 4 tool MCP hanno parametro `name: str`;
  parametri opzionali aggiuntivi sono di design.
- **Copertura archi per-linguaggio (DA-3)**: la decisione utente «tutti i 10 linguaggi» è
  attuata con nodi/`contains` garantiti ovunque e archi relazionali stratificati: la copertura
  REALE per linguaggio è dichiarata in documentazione e verificata dal ground-truth almeno con
  un caso per linguaggio dichiarato; profondità ulteriore è rifinitura (Could).
- **Warm-up del server MCP (R-7)**: se l'inizializzazione del servizio di grafo è bloccante,
  va inclusa nel warm-up eager di `main()` (lezione della hotfix PR #23).
