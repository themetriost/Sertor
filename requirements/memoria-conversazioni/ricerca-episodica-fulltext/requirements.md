# Requisiti — Ricerca episodica full-text locale
<!-- Deriva da: FEAT-002 (epica: memoria-conversazioni) -->

## 1. Contesto e problema (perché)

L'epica «Memoria delle conversazioni» mira a colmare il tier mancante sotto il wiki: l'archivio
grezzo episodico delle conversazioni con l'agente. Avere un archivio senza poterlo interrogare lo
rende un silo inerte: la feature che lo trasforma in **memoria che risponde** è la ricerca episodica.

I **casi speciali** a cui questa feature risponde sono domande del tipo:
- «ne avevamo già parlato?»
- «com'è finita quella cosa di cui avevamo discusso?»
- «cosa avevamo deciso su X tre settimane fa, e perché?»

Questi casi si distinguono dalla ricerca semantica (FEAT-004, Should): qui si vuole trovare una
conversazione passata per parola chiave, frase o finestra temporale — il contenuto **non deve
lasciare la macchina** in nessun caso. Il full-text locale è la scelta che soddisfa
contemporaneamente utilità e privacy-by-default (CS-2 dell'epica).

La feature presuppone che FEAT-001 (cattura e archiviazione locale dei transcript) sia già
implementata e operativa: l'archivio locale di sessioni è la sorgente di dati di questa feature.

## 2. Obiettivi e criteri di successo

Criteri di successo propri di questa feature (ereditano e specializzano CS-2 dell'epica):

- **FS-CS-1 (completezza):** data una parola chiave o frase presente nel testo di una sessione
  archiviata, la ricerca restituisce quella sessione tra i risultati.
- **FS-CS-2 (pertinenza):** i risultati sono ordinati per pertinenza lessicale alla query e/o per
  recency; la sessione più recente tra quelle altrettanto pertinenti non viene retrocessa senza motivo.
- **FS-CS-3 (citazione):** ogni risultato riporta almeno: identificatore della sessione, data/ora,
  path del transcript (se applicabile) e uno snippet di testo che mostra il contesto del match.
- **FS-CS-4 (filtro temporale):** una query con vincolo di finestra temporale («tre settimane fa»)
  restringe i risultati alle sole sessioni il cui timestamp cade nell'intervallo; i risultati fuori
  finestra non appaiono.
- **FS-CS-5 (privacy locale):** la ricerca non produce traffico di rete; nessun frammento di
  transcript viene inviato a servizi esterni durante l'operazione di ricerca.
- **FS-CS-6 (archivio vuoto o nessun risultato):** la ricerca su un archivio vuoto o che non
  contiene match per la query restituisce uno stato vuoto esplicito senza errore.
- **FS-CS-7 (host-agnostico):** la ricerca funziona su almeno due ospiti/archivi diversi senza
  modifiche al corpo della feature (Principio X dell'epica, CS-5).

## 3. Stakeholder e attori

- **Agente LLM (attore primario):** interroga la ricerca nei casi speciali durante una sessione per
  recuperare contesto episodico da conversazioni passate; è sia produttore (le sessioni archiviate
  da FEAT-001 sono le sue conversazioni) sia consumatore della ricerca.
- **Owner/maintainer (utente):** beneficia della memoria episodica ritrovando decisioni e contesto
  che il wiki distillato non ha catturato; può invocare la ricerca manualmente.
- **Il sistema-wiki (consumatore indiretto):** le operazioni `distill`/`record` possono usare i
  risultati della ricerca per localizzare la sessione sorgente da cui attingere (FEAT-003, Should).

## 4. Ambito

### In ambito
- Ricerca full-text **lessicale** (per parola chiave/frase) sull'archivio locale di transcript
  prodotto da FEAT-001.
- Filtro opzionale su **intervallo temporale** della sessione.
- Restituzione di risultati con **citazione** della sessione (id, data/ora, path) e **snippet**
  di contesto.
- Ordinamento dei risultati per **pertinenza lessicale** e/o **recency** (configurabile o
  combinato).
- Comportamento **non-fatale** su archivio assente o vuoto: stato vuoto esplicito, nessuna
  eccezione.
- **Host-agnostico**: la logica di ricerca non fa assunzioni sull'assistente ospite; opera
  sull'archivio locale qualunque sia la sua provenienza (Principio X).
- Osservabilità minima: la ricerca emette un evento strutturato con i parametri usati e il numero
  di risultati restituiti (allineato al pattern `log_event` del core).

### Fuori ambito
- **Cattura e archiviazione dei transcript** (FEAT-001 — dipendenza a monte; questa feature la
  assume come fornita).
- **Ricerca semantica/embedding** (FEAT-004, Should, opt-in separato): nessun embedding, nessun
  vector store, nessun modello di linguaggio nel percorso critico di questa feature.
- **Aggancio diretto alla distillazione del wiki** (FEAT-003, Should): questa feature fornisce
  solo l'interfaccia di ricerca; il collegamento con `distill`/`record` è responsabilità di FEAT-003.
- **Scrub dei segreti nel contenuto**: il testo è già stato scrubbed da FEAT-001; questa feature
  riceve e presenta il testo già redatto.
- **Cancellazione/governance/retention**: è FEAT-006.
- **Roll-up cross-progetto**: è FEAT-007.
- **Cattura multi-assistente**: è FEAT-008.
- **Interfaccia grafica o TUI dedicata**: la ricerca è una capacità interrogabile; la sua
  eventuale superficie visiva appartiene alla CLI/TUI (epica `sertor-cli`).

## 5. Requisiti funzionali (EARS)

### 5.1 Capacità di ricerca di base

**REQ-001 (Ubiquitous):** *The episodic search shall accept a text query and return the list of
archived sessions whose transcript content contains a lexical match, ordered by relevance.*

**REQ-002 (State-driven):** *While the session archive is absent or empty, the episodic search
shall return an explicit empty result without raising an error.*

**REQ-003 (Event-driven):** *When a query is submitted, the episodic search shall return, for each
matching session, at least: the session identifier, the session timestamp, the transcript path (if
available), and a text snippet showing the matched context.*

**REQ-004 (Ubiquitous):** *The episodic search shall operate entirely on the local machine; it
shall not send any fragment of the transcript content to an external service or network endpoint.*

### 5.2 Filtro temporale

**REQ-005 (Optional feature):** *Where a time-window constraint is provided (start date, end date,
or both), the episodic search shall restrict results to sessions whose timestamp falls within the
specified interval.*

**REQ-006 (Unwanted behaviour):** *If the time-window start is later than the end, then the
episodic search shall reject the constraint and return an explicit error describing the invalid
interval.*

**REQ-007 (Optional feature):** *Where only a start date is provided, the episodic search shall
return sessions from that date onwards; where only an end date is provided, it shall return sessions
up to and including that date.*

### 5.3 Ordinamento e pertinenza

**REQ-008 (Ubiquitous):** *The episodic search shall rank results by lexical relevance to the
query; when relevance is equal, more recent sessions shall rank higher.*

**REQ-009 (Optional feature):** *Where a recency-first ordering is requested, the episodic search
shall rank results by session timestamp descending, ignoring relative lexical score differences.*

**REQ-010 (Ubiquitous):** *The episodic search shall limit the number of returned results to a
configurable maximum (default: a finite, documented value); it shall not return the full archive
unconditionally.*

### 5.4 Snippet e citazione

**REQ-011 (Ubiquitous):** *The episodic search shall include in each result a text snippet of
configurable length (default: a finite, documented window) extracted from the transcript at or
around the matched position.*

**REQ-012 (Ubiquitous):** *The episodic search shall include in each result the session identifier
and the session timestamp in a machine-readable format.*

**REQ-013 (Optional feature):** *Where the transcript path is recorded in the archive, the
episodic search shall include it in the result.*

### 5.5 Comportamento su archivio parziale o corrotto

**REQ-014 (Unwanted behaviour):** *If a transcript entry in the archive is unreadable or
structurally invalid, then the episodic search shall skip that entry, log a warning, and continue
searching the remaining entries without interrupting the operation.*

**REQ-015 (Unwanted behaviour):** *If the archive index is absent (not yet built or deleted), then
the episodic search shall return an explicit empty result with a warning, not an error.*

### 5.6 Host-agnostico e portabilità

**REQ-016 (Ubiquitous):** *The episodic search body shall not contain any assumption about the
assistant host that captured the transcripts; it shall operate on the local archive regardless of
its provenance.*

**REQ-017 (Ubiquitous):** *The episodic search shall be operable from at least two different host
environments (e.g. Claude Code and a second assistant) without modifications to its implementation.*

### 5.7 Osservabilità

**REQ-018 (Event-driven):** *When a search operation completes, the episodic search shall emit a
structured log event recording the query (or a hash thereof, if the content is sensitive), the
time-window filters applied, the number of results returned, and the latency of the operation.*

**REQ-019 (Unwanted behaviour):** *If logging the search event fails, then the search result shall
still be returned to the caller; the observability failure shall be non-fatal.*

### 5.8 Idempotenza e coerenza con FEAT-001

**REQ-020 (Ubiquitous):** *The episodic search shall reflect the current state of the archive as
produced by FEAT-001; it shall not introduce its own persistent write-side state beyond what is
needed to index the archive for search.*

[DA CHIARIRE: REQ-020 assume che la ricerca costruisca/legga un indice di ricerca locale
separato rispetto all'archivio grezzo di FEAT-001 — es. un indice FTS aggiornato
all'archiviazione. Se l'archivio grezzo è già direttamente scansionabile in full-text
(es. SQLite con FTS5 nativo) questa distinzione potrebbe collassare. La risposta impatta
il requisito di aggiornamento dell'indice al momento dell'archiviazione di una nuova sessione.]

**REQ-021 (Event-driven):** *When a new session is added to the archive (FEAT-001), the episodic
search index shall be updated to include that session before the next search invocation.*

## 6. Requisiti non funzionali

**NFR-001 (Latenza):** la ricerca su un archivio di dimensione tipica (fino a [DA CHIARIRE: N]
sessioni — dipende dalla granularità definita da DA-M-b) deve restituire risultati entro un tempo
percettivamente immediato in un contesto interattivo (indicativamente < 2 secondi su hardware
consumer standard). [DA CHIARIRE: definire la soglia quantitativa una volta nota la dimensione
attesa dell'archivio.]

**NFR-002 (Scalabilità):** la ricerca deve degradare in modo prevedibile e documentato al
crescere dell'archivio; la documentazione della feature deve indicare il punto oltre il quale il
comportamento è fuori specifica (es. N sessioni o M MB di testo indicizzato).

**NFR-003 (Privacy locale):** la ricerca non deve produrre traffico di rete di alcun tipo durante
l'operazione; questo è verificabile con un monitor di rete in ambiente di test.

**NFR-004 (Affidabilità non-fatale):** un guasto nell'indice di ricerca (es. file corrotto o
assente) non deve propagarsi come eccezione non gestita al chiamante; deve essere segnalato come
stato vuoto o warning.

**NFR-005 (Zero dipendenze cloud):** la feature non deve richiedere credenziali o connettività a
servizi cloud per funzionare; le sue dipendenze devono essere soddisfabili interamente in locale.

**NFR-006 (Dipendenze minimali):** coerente con il principio local-first del core: preferire
funzionalità della stdlib o dipendenze già presenti nel core piuttosto che aggiungere nuove
dipendenze di terze parti. [DA CHIARIRE: questa scelta impatta la decisione riuso BM25 vs FTS
dedicato — vedi §10.]

**NFR-007 (Testabilità senza terminale):** la logica di ricerca deve essere testabile come
funzione pura o come componente isolato, senza richiedere un terminale, un assistente attivo o
un corpus reale — pattern già stabilito dal core (es. `live_snapshot` in
`src/sertor_core/observability/live.py`)

**NFR-008 (Osservabilità strutturata):** gli eventi emessi dalla ricerca seguono il pattern
`log_event` già in uso nel core (`src/sertor_core/observability/logging.py`); nessuna dipendenza
aggiuntiva di logging.

## 7. Vincoli, assunzioni e dipendenze

### Vincoli (ereditati dall'epica)
- **Privacy-by-default (REQ-M-E1/E2):** la ricerca full-text locale è il default di privacy; la
  ricerca semantica (che embedda) è un opt-in separato e appartiene a FEAT-004.
- **Host-agnostico (REQ-M-E3):** il corpo non fa assunzioni sull'host; qualunque adattamento
  host-specifico (cattura, path dell'archivio) è responsabilità di FEAT-001 e della config.
- **Contenuto già scrubbed:** FEAT-001 ha applicato lo scrub dei segreti; questa feature riceve
  testo già redatto e non applica scrub aggiuntivo.

### Assunzioni documentate
- **A-001 — Archivio fornito da FEAT-001:** si assume che FEAT-001 sia implementata e produca un
  archivio locale di sessioni con almeno: id sessione, timestamp, contenuto testuale (già scrubbed),
  path del transcript (facoltativo). Se FEAT-001 non è operativa, la ricerca restituisce risultati
  vuoti (NFR-004).
- **A-002 — Granularità di unità: sessione (assunzione provvisoria):** in assenza di una risposta
  a DA-M-b, si assume che l'unità di archivio e di ricerca sia la **sessione** (non il singolo
  turno/messaggio). Lo snippet di contesto viene estratto da un punto del testo della sessione, non
  da un turno isolato. [DA CHIARIRE: se la granularità fosse il turno, la ricerca dovrebbe
  restituire il turno con riferimento alla sessione padre — impatto sui REQ-003/011/012/013.]
- **A-003 — Pattern SQLite locale:** coerentemente con i precedenti del core (cache embeddings in
  `src/sertor_core/adapters/embeddings/cache.py` — pattern `(model, content_hash) -> vector`
  su SQLite stdlib; store osservabilità in
  `src/sertor_core/observability/store.py` — pattern `query_events(operation, since, until)` con
  indici su `(operation, ts)` e `ts`), si assume che un archivio basato su SQLite locale sia il
  pattern di riferimento anche per FEAT-002. La scelta concreta tra FTS5 nativo di SQLite vs un
  indice BM25 separato è materia di design (vedi §10 e DA-M-b).
- **A-004 — Nessun cloud nel percorso critico:** nessuna chiamata a LLM, embedding provider o
  search index cloud nel percorso di una query di ricerca episodica.
- **A-005 — Porta di ricerca episodica come seam:** coerentemente con lo stile delle sei porte
  Protocol del core (`src/sertor_core/domain/ports.py` — `EmbeddingProvider`, `VectorStore`,
  `LexicalIndex`, `Reranker`, `CodeGraph`, `ObservabilityStore`), si assume che la ricerca
  episodica sarà esposta tramite una porta Protocol che definisce il contratto senza legarlo a
  un'implementazione specifica. Il nome e i metodi esatti della porta sono materia di design.
- **A-006 — Indice aggiornato al momento dell'archiviazione:** si assume che FEAT-001 (o la
  composizione tra FEAT-001 e FEAT-002) garantisca che l'indice di ricerca sia aggiornato
  contestualmente all'archiviazione di una nuova sessione (REQ-021). L'archivio grezzo e
  l'indice di ricerca non divergono.

### Dipendenze
- **FEAT-001 (Must, a monte):** cattura e archiviazione locale dei transcript — è la sorgente di
  dati; FEAT-002 senza FEAT-001 non ha nulla da cercare.
- **DA-M-b (irrisolta):** la granularità dell'unità di memoria (sessione / turno / thread) impatta
  struttura dei risultati, snippet e aggiornamento dell'indice. Documentata in A-002 con assunzione
  provvisoria «sessione».
- **Porta `ObservabilityStore` (già in `domain/ports.py`):** usata per l'osservabilità (REQ-018/019)
  se abilitata; non è una dipendenza hard (NFR-004 — non-fatale).

## 8. Rischi

- **R-002 (ereditato — ridotto):** il contenuto grezzo dei transcript ha alta sensibilità. Questo
  rischio è **ridotto per FEAT-002** rispetto all'epica: la ricerca è locale e il testo è già
  scrubbed da FEAT-001. Il rischio residuo è un bug che esponga il testo via log non redatti
  (mitigazione: seguire il pattern `log_event` con fields già redatti del core).
- **R-004 (ereditato — partecipa):** la crescita illimitata dell'archivio degrada le prestazioni di
  ricerca. Mitigazione in questa feature: NFR-001/NFR-002 impongono un limite documentato e una
  degradazione prevedibile; la governance della retention appartiene a FEAT-006.
- **R-FT-001 — Indice di ricerca e archivio grezzo divergenti:** se l'aggiornamento dell'indice
  (REQ-021) fallisce silenziosamente, le sessioni archiviate non vengono trovate. Mitigazione:
  REQ-021 impone aggiornamento prima della prossima ricerca; REQ-014/015 rendono il guasto
  osservabile (warning).
- **R-FT-002 — Falsi negativi per scrub aggressivo:** se FEAT-001 redige termini tecnici
  rilevanti (es. nomi di variabili, pattern di segreti vicini a token di codice), la ricerca non
  troverà quelle occorrenze. Questo rischio è ereditato dallo scrub di FEAT-001 e non mitigabile
  da FEAT-002; va documentato come comportamento atteso.
- **R-FT-003 — Dimensione archivio e prestazioni:** su archivi molto grandi (es. anni di sessioni
  dense) la ricerca full-text potrebbe superare la soglia NFR-001. Mitigazione: NFR-002 impone
  documentazione del limite; FEAT-006 (retention) riduce la dimensione operativa.
- **R-FT-004 — DA-M-b irrisolta impatta l'implementazione:** se la granularità dell'unità cambia
  da sessione a turno dopo che FEAT-002 è implementata, la struttura dei risultati e degli snippet
  deve essere rivista. Mitigazione: A-002 documenta l'assunzione come provvisoria; il design deve
  rendere la granularità un parametro, non un hardcode.

## 9. Prioritizzazione (MoSCoW) interna

| ID | Requisito / gruppo | Priorità |
|----|-------------------|----------|
| REQ-001..004 | Ricerca di base (query, risultati, privacy locale, archivio vuoto) | **Must** |
| REQ-005..007 | Filtro temporale | **Must** (CS-2 dell'epica parla esplicitamente di finestre «tre settimane fa») |
| REQ-008, REQ-010..013 | Ordinamento e citazione completa | **Must** |
| REQ-014..015 | Degradazione graceful su archivio parziale/assente | **Must** |
| REQ-016..017 | Host-agnostico (Principio X) | **Must** |
| REQ-018..019 | Osservabilità non-fatale | **Must** |
| REQ-020..021 | Coerenza indice/archivio | **Must** |
| REQ-009 | Ordinamento recency-first su richiesta | **Should** |
| NFR-001..005, NFR-007..008 | Latenza, scalabilità, privacy, affidabilità, testabilità | **Must** |
| NFR-002 (soglia quantitativa) | Definizione numerica del limite di scalabilità | **Should** (richiede DA-M-b e dimensionamento reale) |
| NFR-006 | Dipendenze minimali | **Should** |

## 10. Domande aperte

**DA-FT-001 — Riuso del lexical/BM25 del core vs FTS SQLite dedicato [priorità: ALTA]**

Il core dispone già di un adapter BM25 in `src/sertor_core/adapters/lexical/bm25.py`
(`Bm25LexicalIndex` con sidecar JSON, `LexicalIndex` port in `domain/ports.py`). Questo adapter
è progettato per indicizzare chunk di codice/documentazione del corpus RAG (tokenizzazione per
snake_case, sidecar JSON per collezione RAG).

La ricerca episodica ha un profilo diverso: opera su transcript di conversazioni (testo naturale,
non codice), su unità di ricerca sessione (non chunk RAG), e deve supportare filtri temporali.

Le opzioni di design (da valutare in fase di design, non qui):
- **Opzione A — FTS SQLite nativo (FTS5):** SQLite (già usato per `EmbeddingCache` e
  `SqliteObservabilityStore`) offre FTS5 integrato, stdlib, con supporto per `MATCH`, snippet,
  rank e filtri su colonne (es. timestamp). Nessuna dipendenza aggiuntiva; integrato nell'archivio.
- **Opzione B — Riuso `Bm25LexicalIndex`:** adattare l'adapter BM25 esistente per i transcript.
  Pro: riuso del codice; Contro: il sidecar JSON non è ottimale per archivi grandi, la
  tokenizzazione snake_case non è pensata per testo naturale, e i filtri temporali richiederebbero
  metadata aggiuntivi.
- **Opzione C — Porta nuova con implementazioni intercambiabili:** definire una porta
  `EpisodicSearchIndex` separata (dietro `Protocol`, stile `domain/ports.py`) con due adapter —
  uno FTS5 (default) e uno BM25 (riuso). Il composition root sceglie via config.

[DA CHIARIRE: quale opzione è preferita? La decisione impatta NFR-006 (dipendenze minimali) e la
struttura dell'archivio prodotto da FEAT-001. Segnalare al design.]

**DA-FT-002 — Granularità ereditata da DA-M-b [priorità: ALTA]**

DA-M-b dell'epica chiede: l'unità archiviata è la sessione intera, il turno o un thread?
FEAT-002 assume provvisoriamente «sessione» (A-002). Se la risposta fosse «turno»:
- REQ-003 deve restituire anche il turno specifico, non solo la sessione contenitrice.
- REQ-011 (snippet) diventa il testo del turno (più corto, meno bisogno di finestra).
- REQ-012 deve includere sia id sessione sia id/indice del turno.
- L'indice di ricerca ha cardinalità molto più alta (un turno per riga vs una sessione per riga).

[DA CHIARIRE: risolvere DA-M-b prima del design di FEAT-002. Segnalare che la scelta impatta
struttura dei risultati e dimensionamento dell'indice.]

**DA-FT-003 — Soglia quantitativa di scalabilità (NFR-001/002) [priorità: MEDIA]**

NFR-001 parla di «archivio di dimensione tipica» e «indicativamente < 2 secondi». La soglia
quantitativa richiede: (a) la risposta a DA-M-b per sapere la cardinalità dell'indice; (b) una
stima della dimensione tipica (N sessioni × M token medi per sessione). Da fissare in fase di
design dopo DA-M-b.

**DA-FT-004 — Redazione della query nell'evento di osservabilità (REQ-018) [priorità: BASSA]**

REQ-018 prescrive di loggare «la query o un suo hash se il contenuto è sensibile». La query
utente potrebbe contenere termini sensibili (es. nomi di credenziali o persone). Il pattern
del core usa `log_event` con fields già redatti (vedi `src/sertor_core/observability/logging.py`
e la strategia di redaction di FEAT-001). [DA CHIARIRE: si logga la query in chiaro, si usa un
hash, o si applica lo stesso scrub di FEAT-001? La coerenza con la strategia di FEAT-001 è
preferibile.]

**DA-FT-005 — Aggiornamento sincrono vs asincrono dell'indice (REQ-021) [priorità: MEDIA]**

REQ-021 richiede che l'indice sia aggiornato prima della prossima ricerca. La domanda di design è
se l'aggiornamento avvenga **in-transaction con l'archiviazione** (sincrono, forte coerenza) o
**al momento della prima ricerca successiva** (lazy, eventuale). L'opzione sincrona è più semplice
e coerente; l'opzione lazy riduce la latenza di archiviazione su archivi grandi. [DA CHIARIRE in
design, in coerenza con la scelta di FEAT-001 sull'atomicità dell'archiviazione.]
