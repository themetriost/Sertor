# Feature Specification: Ricerca semantica opzionale sull'archivio (FEAT-004)

**Feature Branch**: `072-ricerca-semantica-memoria` · **Created**: 2026-06-22 · **Status**: Draft

<!-- Deriva da: FEAT-004 (epica memoria-conversazioni) — requirements/memoria-conversazioni/ricerca-semantica/requirements.md -->

**Input**: FEAT-004 dell'epica `memoria-conversazioni` (Should). L'MVP della memoria conversazioni è
completo: FEAT-001 cattura e archivia le conversazioni in `memory.sqlite` (contenuto già **scrubbed**),
FEAT-002 le rende interrogabili **full-text** (FTS5/BM25, parola/frase esatta), feature 035 espone la CLI
+ hook `SessionEnd`, FEAT-009 la distribuisce via installer. La full-text trova solo ciò che **combacia
per parola**: «com'era finita la discussione sull'astensione del retrieval quando il punteggio è basso?»
non trova nulla se in quella sessione si diceva «confidence», «soglia», «min-score». Questa feature colma
quella lacuna con la **ricerca per significato** (semantica) sull'archivio episodico, come **percorso
opt-in distinto** dalla full-text (che resta il default).

---

> **Allineamento alla missione (gate Constitution).** La ricerca semantica della memoria serve la
> **qualità del contesto reso all'agente nel tempo**: ritrovare per *concetto* (non per stringa) cosa è
> già stato deciso/discusso. È la stessa stella polare (auto-conoscenza interrogabile, portabile,
> on-machine col provider locale di default). **Riusa il motore di retrieval del core** — non ne
> costruisce un secondo — quindi rafforza la pipeline esistente invece di derivare su un concern
> periferico.

> **Natura del cambiamento: ADDITIVO, a leva spenta = nessun costo.** Con la semantica **non** opt-in
> (default), comportamento e costo sono identici a oggi: nessun embedding, nessun indice nuovo, nessun
> import del percorso semantico — coerente col gate `build_*` esistente che ritorna `None` a memoria
> spenta. La full-text di FEAT-002 **resta il default** e non viene né disabilitata né modificata.

> **Decisioni di scope GIÀ fissate (non si riaprono).**
> - **Dove vive l'indice (DA-SS-1) → Opzione B: store vettoriale dedicato.** Si riusano **solo le
>   primitive di retrieval** del core (embedder via `build_embedder`, vector store via `build_store`,
>   namespacing via `collection_name`); **non** l'orchestratore file-oriented `IndexingService.index()`
>   né il manifest file-keyed di FEAT-009 (pensato per file mutabili — l'archivio memoria è
>   **append-only**). «No nuovo motore» (REQ-016) resta rispettato: il motore di retrieval è riusato.
> - **Incrementalità (DA-SS-4) → marker a watermark, append-only-aware.** L'indicizzazione embedda
>   **solo le unità nuove**, mai l'intero archivio; un marker durevole traccia «già embeddato». L'unico
>   rebuild totale è il cambio provider/dimensione vettore (REQ-032). La *forma esatta* del marker
>   (colonna in `memory.sqlite` vs manifest separato vs derivato dallo store) resta dettaglio di plan.
> - **Trigger di indicizzazione = automatico a fine sessione.** L'embedding di una sessione avviene
>   contestualmente alla sua archiviazione (percorso `memory archive` / hook `SessionEnd`), gated
>   dall'opt-in semantico; nessun passo manuale per la freschezza.
> - **Modo separato opt-in.** La semantica è un percorso distinto attivato esplicitamente (es. opzione
>   `--semantic` sulla ricerca, forma esatta = design); **nessun fallback silenzioso** alla full-text.
> - **Privacy.** Opt-in **ulteriore e distinto** da `SERTOR_MEMORY` (manopola proposta
>   `SERTOR_MEMORY_SEMANTIC`, default off); on-machine col provider locale di default (FEAT-011,
>   `glove`/`hash`).

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Archivio = `MemoryArchive`
> (`src/sertor_core/adapters/memory/archive.py`, sessioni+turni scrubbati, append-only `INSERT OR
> IGNORE`); full-text = `EpisodicSearch` (`src/sertor_core/services/episodic_search.py`); factory gated
> su `memory_enabled` in `src/sertor_core/composition.py` (`build_episodic_search`/`build_memory_archiver`
> ritornano `None` a memoria spenta); collezioni namespaced per `(corpus, provider)` via
> `collection_name`. I riferimenti a file ancorano i requisiti, **non** prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ritrovare una conversazione per significato, non per parola (P1, Must)
L'agente (o l'utente) interroga la memoria con una domanda in linguaggio naturale che usa **parole
diverse ma di significato affine** a quelle realmente dette nella sessione passata. La ricerca semantica
restituisce quella sessione tra i primi risultati, là dove la full-text non la troverebbe.

**Independent Test**: data una sessione archiviata che discute un concetto con un certo lessico, una
query semantica con sinonimi/parafrasi (zero parole in comune) restituisce quella sessione nel top-k;
la stessa query in full-text non la restituisce.

**Acceptance**:
1. **Given** la semantica opt-in e una sessione indicizzata che parla di «confidence/soglia/min-score»,
   **When** interrogo per significato con «astensione quando il punteggio è basso», **Then** quella
   sessione compare tra i primi risultati ordinati per similarità.
2. **Given** un risultato semantico, **When** lo ispeziono, **Then** porta almeno: identificatore di
   sessione, riferimento all'unità (es. indice di turno), timestamp della sessione, snippet, punteggio
   di similarità.
3. **Given** un limite di risultati configurato, **When** interrogo, **Then** non viene restituito
   l'intero indice: i risultati sono limitati al massimo configurato.

### User Story 2 — Opt-in ulteriore e separato (privacy a strati) (P1, Must)
Con la sola cattura attiva (`SERTOR_MEMORY=true`) ma la semantica **non** opt-in, nessun contenuto viene
embeddato e nessun indice vettoriale viene creato; la ricerca semantica è disponibile **solo** dopo
l'opt-in dedicato.

**Independent Test**: con `SERTOR_MEMORY=true` e la manopola semantica off, dopo aver archiviato sessioni
non esiste alcun indice vettoriale della memoria e nessuna chiamata di embedding è stata eseguita.

**Acceptance**:
1. **Given** la cattura attiva e la semantica off, **When** archivio sessioni, **Then** nessun contenuto
   è embeddato e nessun indice semantico è creato.
2. **Given** la semantica opt-in ma la cattura (`SERTOR_MEMORY`) off, **When** abilito la semantica,
   **Then** il sistema la tratta come **inattiva** (no embedding, no indice) e segnala la dipendenza.
3. **Given** l'opt-in semantico, **When** ispeziono le manopole, **Then** è una manopola **distinta** da
   `SERTOR_MEMORY`, con default off: accendere la cattura non accende mai silenziosamente l'embedding.

### User Story 3 — Indicizzazione automatica, fresca e incrementale (P1, Must)
Quando una sessione è archiviata e la semantica è opt-in, il suo contenuto è embeddato e aggiunto
all'indice contestualmente — così è recuperabile per significato senza un passo manuale. Le indicizzazioni
successive embeddano **solo il nuovo**, mai l'intero archivio.

**Independent Test**: archivio una sessione con la semantica opt-in → è subito interrogabile per
significato; una seconda indicizzazione senza nuove sessioni **non** produce nuove chiamate di embedding.

**Acceptance**:
1. **Given** la semantica opt-in, **When** una sessione viene archiviata, **Then** il suo contenuto è
   embeddato e aggiunto all'indice, ed è recuperabile alla ricerca successiva.
2. **Given** un'indicizzazione già eseguita, **When** ri-indicizzo senza sessioni nuove, **Then** non
   vengono prodotte nuove chiamate di embedding (incrementalità: O(nuovo)).
3. **Given** una sessione già indicizzata, **When** la stessa sessione viene ri-processata, **Then**
   l'indice non crea voci duplicate (idempotenza).
4. **Given** un marker durevole di «già indicizzato», **When** il processo riparte o si avvia una nuova
   esecuzione separata, **Then** l'incrementale salta le unità già embeddate tra riavvii ed esecuzioni.

### User Story 4 — Modo separato, nessun fallback silenzioso (P1, Must)
La full-text resta il default; la semantica è un percorso distinto attivato esplicitamente. Se l'utente
seleziona il modo semantico ma la semantica non è opt-in (o l'indice è assente), riceve un messaggio
esplicito e azionabile, **mai** un fallback silenzioso alla full-text.

**Independent Test**: la ricerca senza modo semantico passa per la full-text; con il modo semantico
selezionato ma la semantica non opt-in, l'esito è un messaggio che nomina l'opt-in richiesto (non
risultati full-text mascherati da semantici).

**Acceptance**:
1. **Given** nessun modo esplicito, **When** cerco nella memoria, **Then** la ricerca usa il percorso
   full-text di FEAT-002 (default invariato).
2. **Given** il modo semantico selezionato e la semantica opt-in, **When** cerco, **Then** la query è
   instradata alla ricerca semantica.
3. **Given** il modo semantico selezionato ma la semantica non opt-in (o indice assente), **When** cerco,
   **Then** ricevo un messaggio esplicito e azionabile che nomina l'opt-in/indice richiesto e **nessun**
   fallback silenzioso alla full-text.

### User Story 5 — On-machine col provider locale (P1, Must)
Con un provider di embeddings locale (default dopo FEAT-011), l'intero percorso — indicizzazione e query
— avviene **senza traffico di rete**: nessun frammento di transcript lascia la macchina. Con un provider
cloud, l'invio off-machine del contenuto (già scrubbed) è una conseguenza **esplicita** dell'opt-in.

**Independent Test**: con un provider locale configurato, indicizzazione + query non generano traffico di
rete (monitor di rete a zero); con un provider cloud, l'implicazione di invio off-machine è documentata/
segnalata, non silenziosa.

**Acceptance**:
1. **Given** un provider locale, **When** indicizzo e interrogo, **Then** non c'è traffico di rete e
   nessun frammento di transcript lascia la macchina.
2. **Given** un provider cloud configurato per la semantica, **When** abilito/uso la semantica, **Then**
   l'invio off-machine del contenuto è reso esplicito (documentato e/o segnalato), non silenzioso.
3. **Given** il selettore provider del core (`SERTOR_EMBED_PROVIDER`), **When** scelgo il provider della
   semantica, **Then** uso lo stesso selettore esistente (default locale), senza un selettore nuovo solo
   per la memoria.

### User Story 6 — Degradazione non-fatale e backfill (P2, Should)
Guasti (indice assente, provider giù, unità corrotta, embedding fallito a fine sessione) non si propagano
come eccezioni: sempre stato vuoto/warning/errore azionabile, mai crash. Le sessioni archiviate **prima**
dell'opt-in possono essere portate nell'indice (backfill) senza ri-archiviazione.

**Independent Test**: con indice assente la query semantica torna risultato vuoto + warning (non
eccezione); con sessioni pre-opt-in, il backfill le embedda senza ri-archiviarle ed è anch'esso
incrementale.

**Acceptance**:
1. **Given** un indice semantico assente, **When** interrogo per significato, **Then** ricevo un
   risultato vuoto esplicito con warning, non un errore.
2. **Given** il provider di embeddings non disponibile a query-time, **When** interrogo, **Then** ricevo
   uno stato vuoto/errore azionabile e il chiamante non va in crash.
3. **Given** una singola unità illeggibile o con embedding invalido, **When** interrogo, **Then** quella
   unità è saltata con warning e i restanti risultati sono serviti.
4. **Given** l'embedding di una sessione fallisce a fine archiviazione, **When** archivio, **Then** il
   grezzo della sessione resta intatto, viene loggato un warning e il run di cattura continua.
5. **Given** un archivio con sessioni catturate prima dell'opt-in, **When** eseguo il backfill, **Then**
   le sessioni di backlog sono embeddate (solo quelle non ancora indicizzate) senza ri-archiviarle.

## Edge Cases
- **Cattura off, semantica opt-in**: dipendenza segnalata; semantica inattiva (no embedding, no indice).
- **Cambio provider/dimensione vettore (REQ-032)**: unico caso che ri-embedda lo storico; rebuild totale
  **esplicito e osservabile** (il namespacing per `(corpus, provider)` di `collection_name` può rendere il
  rebuild *implicito* — la collezione cambia col provider; la conferma è dettaglio di plan).
- **Provider cloud + auto-indicizzazione a fine sessione**: ogni chiusura manderebbe contenuto (già
  scrubbed) fuori macchina — implicazione resa esplicita (REQ-020); default locale la evita.
- **Filtro temporale**: la semantica supporta una finestra temporale sul timestamp di sessione, in parità
  con la full-text di FEAT-002.
- **Indice semantico ↔ corpus codice/doc**: l'indice della memoria è **isolato** dal corpus del progetto;
  contenuto memoria e corpus non si mescolano mai negli stessi risultati.
- **Indice = artefatto derivato**: cancellarlo/ricostruirlo non altera il grezzo; il rebuild dal grezzo
  produce un indice equivalente.
- **Re-indicizzazione senza nuove sessioni**: nessuna nuova chiamata di embedding (incrementalità).

## Requirements *(mandatory)*

### Requisiti funzionali

**Opt-in di privacy a strati**
- **FR-001 (opt-in obbligatorio).** Senza opt-in semantico esplicito, il sistema **non** embedda alcun
  contenuto e **non** crea alcun indice vettoriale. *(REQ-001)*
- **FR-002 (dipendenza dalla cattura).** La semantica richiede che la cattura (`SERTOR_MEMORY`) sia
  attiva; con la cattura off, la semantica è trattata come inattiva e la dipendenza è segnalata.
  *(REQ-002)*
- **FR-003 (manopola distinta, default off).** L'opt-in semantico è una manopola **distinta** da
  `SERTOR_MEMORY`, default off; accendere la cattura non accende mai l'embedding. *(REQ-003)*

**Indicizzazione semantica (automatica, incrementale)**
- **FR-004 (auto-index a fine sessione).** Quando una sessione è archiviata e la semantica è opt-in, il
  suo contenuto è embeddato e aggiunto all'indice, rendendola recuperabile per significato. *(REQ-004)*
- **FR-005 (no-op se non opt-in).** Quando una sessione è archiviata e la semantica **non** è opt-in,
  viene archiviata (comportamento FEAT-001) senza embedding né tocco dell'indice. *(REQ-005)*
- **FR-006 (idempotenza).** Indicizzare una sessione già indicizzata non crea voci duplicate. *(REQ-006)*
- **FR-007 (incrementalità).** Ogni run di indicizzazione embedda **solo** le unità non già presenti
  nell'indice e **mai** l'intero archivio di default (sfrutta la natura append-only). *(REQ-030)*
- **FR-008 (marker durevole).** Il sistema registra in modo durevole quali unità sono già state
  embeddate (marker/watermark), così l'incrementale le salta tra riavvii ed esecuzioni separate.
  *(REQ-031)*
- **FR-009 (backfill).** Esiste un modo per embeddare le sessioni di backlog (catturate prima dell'opt-in)
  senza ri-archiviarle; il backfill è anch'esso incrementale (solo le unità non ancora indicizzate).
  *(REQ-007)*
- **FR-010 (embedding fallito non-fatale).** Se l'embedding di una sessione a fine archiviazione
  fallisce, il grezzo resta intatto, è loggato un warning e il run di cattura continua. *(REQ-008)*
- **FR-011 (rebuild totale solo eccezionale).** Un cambio di provider/dimensione vettore o di versione di
  logica che rende i vettori incompatibili causa un rebuild totale dall'archivio; è l'**unico** caso che
  ri-embedda contenuto già indicizzato, ed è **esplicito e osservabile**. *(REQ-032)*

**Ricerca semantica**
- **FR-012 (query NL → risultati ranked).** La ricerca semantica accetta una query in linguaggio naturale
  e restituisce unità di memoria ordinate per similarità semantica. *(REQ-009)*
- **FR-013 (citazione completa).** Ogni risultato porta almeno: id di sessione, riferimento all'unità
  (es. indice di turno), timestamp di sessione, snippet, punteggio di similarità. *(REQ-010)*
- **FR-014 (limite configurabile).** Il numero di risultati è limitato a un massimo configurabile (default
  finito e documentato); non restituisce incondizionatamente l'intero indice. *(REQ-011)*
- **FR-015 (filtro temporale).** Con un vincolo di finestra temporale, i risultati sono ristretti alle
  unità il cui timestamp di sessione cade nell'intervallo (parità con la full-text). *(REQ-012)*

**Modo separato dalla full-text**
- **FR-016 (full-text resta default).** La full-text di FEAT-002 resta il percorso di default; abilitare
  la semantica non la disabilita né la sostituisce. *(REQ-013)*
- **FR-017 (instradamento esplicito).** Con il modo semantico selezionato esplicitamente, la query è
  instradata alla semantica; altrimenti si usa la full-text. *(REQ-014)*
- **FR-018 (nessun fallback silenzioso).** Modo semantico selezionato ma non opt-in (o indice assente) →
  messaggio esplicito e azionabile che nomina l'opt-in/indice richiesto; **nessun** fallback silenzioso
  alla full-text. *(REQ-015)*

**Riuso del RAG, isolamento**
- **FR-019 (riuso, no nuovo motore).** Indicizzazione e query riusano le capacità di embedding/vector-store
  del core (le stesse del corpus codice/doc); nessun motore di retrieval separato è introdotto. *(REQ-016)*
- **FR-020 (indice isolato).** L'indice semantico della memoria è isolato dall'indice del corpus
  codice/doc del progetto; contenuto memoria e corpus non si mescolano mai negli stessi risultati.
  *(REQ-017)*

**Provider e on-machine**
- **FR-021 (selettore esistente).** Indicizzazione e query usano il provider scelto dal selettore esistente
  del core (`SERTOR_EMBED_PROVIDER`), default locale (FEAT-011); nessun selettore nuovo per la memoria.
  *(REQ-018)*
- **FR-022 (on-machine col locale).** Con un provider locale configurato, tutto il percorso (index + query)
  avviene senza traffico di rete; nessun frammento di transcript lascia la macchina. *(REQ-019)*
- **FR-023 (invio off-machine esplicito).** Con un provider cloud configurato, l'invio off-machine del
  contenuto (già scrubbed) è reso esplicito (documentato e/o segnalato), non silenzioso. *(REQ-020)*

**Degradazione non-fatale**
- **FR-024 (indice assente).** Indice semantico assente alla query → risultato vuoto esplicito + warning,
  non errore. *(REQ-021)*
- **FR-025 (provider giù a query-time).** Provider non disponibile/misconfigurato alla query → stato
  vuoto/errore azionabile; il chiamante non va in crash. *(REQ-022)*
- **FR-026 (unità corrotta).** Unità illeggibile o embedding invalido → saltata con warning; i restanti
  risultati sono serviti. *(REQ-023)*

**Host-agnostico**
- **FR-027 (no assunzioni sull'host).** Il corpo di indicizzazione e ricerca non assume l'assistente che
  ha catturato i transcript; opera sull'archivio locale indipendentemente dalla provenienza. *(REQ-024)*
- **FR-028 (operabile su ≥2 ospiti).** La ricerca semantica è operabile da ≥2 ambienti host diversi senza
  modifiche all'implementazione. *(REQ-025)*

**Osservabilità**
- **FR-029 (evento di indicizzazione).** A indicizzazione completata, è emesso un evento strutturato
  **metrics-only** con almeno: numero di unità embeddate, nome provider, latenza; **nessun** testo di
  transcript. *(REQ-026)*
- **FR-030 (evento di query).** A query completata, è emesso un evento strutturato **metrics-only** con
  almeno: numero di risultati, filtri di finestra temporale applicati, latenza; la query è registrata
  solo come hash o omessa, **mai** in chiaro (coerente con FEAT-002). *(REQ-027)*
- **FR-031 (osservabilità non-fatale).** Se l'emissione di un evento fallisce, il risultato di
  indicizzazione/ricerca è comunque prodotto; il guasto di osservabilità è non-fatale. *(REQ-028)*

**Coerenza con l'archivio**
- **FR-032 (artefatto derivato).** L'indice semantico è un artefatto derivato dell'archivio FEAT-001:
  cancellarlo/ricostruirlo non altera il grezzo, e ricostruirlo dall'archivio produce un indice
  equivalente. *(REQ-029)*

### Requisiti non funzionali
- **RNF-1 (privacy locale di default):** col provider locale di default, l'intero percorso (index + query)
  è offline; verificabile con un monitor di rete in test (zero traffico). *(NFR-001)*
- **RNF-2 (additività a leva spenta):** con la semantica non opt-in (default), comportamento e costo sono
  identici a oggi: nessun embedding, nessun file/indice nuovo, nessun import del percorso semantico
  (coerente col gate `build_*` esistente che ritorna `None`). *(NFR-005)*
- **RNF-3 (`sertor-core` riuso, dipendenze minimali):** riuso delle capacità di embedding/store già nel
  core; nessuna nuova dipendenza di terze parti se evitabile (local-first). *(NFR-006)*
- **RNF-4 (affidabilità non-fatale):** nessun guasto (indice assente/corrotto, provider giù) si propaga
  come eccezione non gestita; sempre stato vuoto/warning/errore azionabile. *(NFR-004)*
- **RNF-5 (testabilità offline):** indicizzazione e ricerca testabili come componente isolato con
  embedder/store mock (pattern delle fixture del core), senza rete né corpus reale. *(NFR-007)*
- **RNF-6 (costo a regime = O(nuovo)):** grazie all'incrementalità, il costo di embedding a regime è
  proporzionale alle sole unità nuove; una seconda indicizzazione senza nuove sessioni non produce nuove
  chiamate di embedding; il ri-embedding dello storico avviene solo nel caso eccezionale (FR-011).
  *(NFR-009)*
- **RNF-7 (costo dell'auto-index a fine sessione documentato):** il costo di embedding per-sessione è
  contenuto e non degrada percettibilmente la chiusura di sessione; con provider locale è solo CPU. La
  documentazione dichiara l'implicazione di costo (e, per provider cloud, di privacy). *(NFR-002)*
- **RNF-8 (osservabilità strutturata):** gli eventi seguono il pattern `log_event` del core, fields già
  redatti, metrics-only; nessuna nuova dipendenza di logging. *(NFR-008)*
- **RNF-9 (latenza di query):** una query semantica su un archivio di dimensione tipica restituisce in
  tempo percettivamente immediato in contesto interattivo (indicativamente < 2 s su hardware consumer);
  la soglia quantitativa precisa si fissa dopo la decisione di granularità. *(NFR-003)*

### Key Entities
- **Indice semantico della memoria** — collezione vettoriale dedicata e **isolata** dal corpus
  codice/doc, popolata dagli embedding delle unità dell'archivio; artefatto **derivato** e ricostruibile.
- **Unità di memoria indicizzata** — l'unità embeddata e restituita (turno/sessione/chunk = granularità
  di design); porta id sessione, riferimento all'unità, timestamp, snippet.
- **Risultato semantico** — un esito di ricerca: id sessione + riferimento unità + timestamp + snippet +
  punteggio di similarità.
- **Marker di «già indicizzato» (watermark)** — registro durevole append-only-aware delle unità già
  embeddate; abilita l'incrementalità tra riavvii/esecuzioni (forma esatta = design).
- **Opt-in semantico** — manopola booleana dedicata (proposta `SERTOR_MEMORY_SEMANTIC`), distinta da
  `SERTOR_MEMORY`, default off.
- **Modo di ricerca** — selettore esplicito full-text (default) vs semantico, senza fallback silenzioso.

## Success Criteria *(mandatory)*
- **SC-001 (recupero per significato):** data una sessione che discute un concetto, una query semantica con
  parole diverse ma affini la restituisce nel top-k, dove la full-text non la trova. *(FR-012/013, US1)*
- **SC-002 (opt-in ulteriore):** con `SERTOR_MEMORY=true` ma semantica off, dopo l'archiviazione **zero**
  unità embeddate e **nessun** indice vettoriale creato. *(FR-001/002/003, US2)*
- **SC-003 (on-machine col locale):** col provider locale, indicizzazione + query a **zero traffico di
  rete** (monitor a zero). *(FR-021/022, RNF-1, US5)*
- **SC-004 (full-text resta default):** abilitare la semantica non disabilita né sostituisce la full-text;
  senza modo esplicito la ricerca resta full-text. *(FR-016/017, US4)*
- **SC-005 (no fallback silenzioso):** modo semantico senza opt-in/indice → messaggio azionabile, mai
  risultati full-text mascherati. *(FR-018, US4)*
- **SC-006 (incrementalità O(nuovo)):** una seconda indicizzazione senza nuove sessioni produce **zero**
  nuove chiamate di embedding; idempotente sulla stessa sessione. *(FR-006/007/008, RNF-6, US3)*
- **SC-007 (auto-index fresco):** una sessione archiviata con la semantica opt-in è recuperabile per
  significato senza un passo manuale. *(FR-004, US3)*
- **SC-008 (riuso, no nuovo motore):** nessun nuovo engine di retrieval; indicizzazione e query passano per
  le primitive embedder/store/`collection_name` del core. *(FR-019, RNF-3)*
- **SC-009 (indice isolato):** contenuto memoria e corpus codice/doc non compaiono mai negli stessi
  risultati di ricerca. *(FR-020)*
- **SC-010 (degradazione non-fatale):** indice assente → vuoto+warning; provider giù → errore azionabile;
  unità corrotta → saltata; nessun crash del chiamante. *(FR-024/025/026, RNF-4, US6)*
- **SC-011 (additività a leva spenta):** con la semantica off, comportamento e costo identici a oggi;
  `sertor-core` non regredisce; suite verde, lint pulito. *(RNF-2/3)*
- **SC-012 (osservabilità metrics-only):** gli eventi index/query non contengono testo/transcript/query in
  chiaro; la query è hash o omessa. *(FR-029/030/031, RNF-8)*
- **SC-013 (host-agnostico):** indicizzazione e ricerca operano su ≥2 ospiti senza modifiche al corpo.
  *(FR-027/028)*

## Assumptions
- **A-001 — Archivio fornito da FEAT-001:** sessioni+turni scrubbati in `memory.sqlite`
  (`adapters/memory/archive.py`), con id sessione, timestamp, contenuto, indice di turno.
- **A-002 — Full-text fornita da FEAT-002:** `EpisodicSearch` resta il percorso di default; la semantica
  le si affianca.
- **A-003 — Gate privacy come gli altri `build_*`:** la factory del percorso semantico ritorna `None`
  (no-op) quando la semantica non è opt-in, come `build_episodic_search`/`build_memory_archiver` a
  `SERTOR_MEMORY` off.
- **A-004 — Manopola dedicata:** nuova booleana dedicata (proposta `SERTOR_MEMORY_SEMANTIC`, default off),
  accanto alle manopole memoria esistenti; nome esatto = design.
- **A-005 — Provider dal selettore esistente:** l'embedding usa `SERTOR_EMBED_PROVIDER` (default locale
  dopo FEAT-011); nessun selettore nuovo solo per la memoria.
- **A-006 — Indicizzazione contestuale all'archiviazione:** il percorso di archiviazione (FEAT-001/035,
  hook `SessionEnd`) è il punto in cui scatta anche l'embedding, quando opt-in; grezzo e indice non
  divergono (FR-032).
- **A-007 — Testo già scrubbed:** FEAT-001 ha applicato lo scrub; questa feature embedda testo già redatto
  e non applica scrub aggiuntivo.

### Fuori ambito (dichiarato)
- **Cattura e archiviazione** (FEAT-001 — dipendenza a monte, assunta come fornita).
- **Ricerca full-text** (FEAT-002 — affiancata, non modificata).
- **Parità MCP** dei comandi di memoria (search/show/list via server MCP): **FEAT-010**. Questa feature
  consegna via libreria/CLI; l'esposizione MCP è successiva.
- **Distribuzione via installer** delle nuove manopole/asset (template `.env`, hook, doc): debito di
  completamento da promuovere a FEAT-009/installer, **non** risolto qui (vedi *Tracciamento dello scope*).
- **Cancellazione/governance/retention** dell'indice semantico: **FEAT-006**; qui solo il gancio di
  coerenza/ricostruibilità con l'archivio.
- **Cattura multi-assistente** (FEAT-008) e **roll-up cross-progetto** (FEAT-007).
- **Scrub aggiuntivo dei segreti**: il testo è già scrubbed da FEAT-001.
- **Il *come* di dettaglio** (granularità turno/sessione/chunk; forma esatta del marker; nome esatto della
  manopola e del flag; superficie utente del modo semantico): fase di **design/plan**.

> **Tracciamento dello scope.** FEAT-010/009/006/008/007 sono già nel backlog d'epica
> (`requirements/memoria-conversazioni/epic.md`): nessun rinvio reale vive solo dentro `specs/`. Il debito
> di **distribuzione via installer** (DA-SS-6) è da chiudere prima che la capacità conti come *done* —
> cross-ref FEAT-009 (owner di `sertor install`).

### Forche di design (per `/speckit-plan`)
- **DA-SS-2 — Granularità dell'unità indicizzata/restituita:** turno (coerente con FEAT-002), sessione
  intera, o chunk (come il RAG)? Impatta NFR-009/RNF-9 (soglia di latenza). *Design.*
- **DA-SS-3 — Superficie utente del modo semantico:** opzione `--semantic` su `memory search` (un comando,
  due modi, raccomandata) vs sotto-comando dedicato `memory search-semantic`. *Design.*
- **DA-SS-4 (residuo) — Forma del marker di watermark:** colonna/flag in `memory.sqlite` vs manifest
  separato namespaced per `(corpus-memoria, provider)` vs derivato dallo stato del vector store; e se il
  rebuild di REQ-032 sia *implicito* via cambio collezione (`collection_name` namespaced). *Design.*
- **DA-SS-5 — Nome esatto della manopola:** proposta `SERTOR_MEMORY_SEMANTIC` (booleana, default off).
  *Design.*
