# Feature Specification: Query congiunta multi-collezione & `upsert-index` in CLI

**Feature Branch**: `010-query-congiunta-e-upsert-index`

**Created**: 2026-06-10

**Status**: Draft

**Input**: User description: "I due pezzi deterministici (D) residui della feature Wiki (FEAT-003), in un'unica feature SpecKit: (A) query congiunta sulle collezioni codice + wiki con fusione dei top-k; (B) esposizione della scrittura idempotente dell'indice del wiki (`upsert_index`) come sottocomando della CLI `sertor-wiki-tools`. Requisiti a monte: `requirements/sertor-core/query-congiunta-e-indice/requirements.md`."

> **Derivazione**: FEAT-003 (epica `sertor-core`) — pezzi **deterministici (D)** residui.
> Requisiti EARS a monte: [`requirements/sertor-core/query-congiunta-e-indice/requirements.md`](../../requirements/sertor-core/query-congiunta-e-indice/requirements.md) (gruppi A/B, DA-1..6).

## Clarifications

### Session 2026-06-10

- Q: Con provider di embeddings diversi tra le due collezioni (spazi vettoriali non confrontabili), cosa fa la ricerca combinata? → A: Errore esplicito (fail-fast): la fusione richiede lo stesso provider; con provider eterogenei la ricerca combinata fallisce con errore esplicito. Eccezione **deliberata** alla policy tollerante della facade: meglio nessuna risposta che una fusione fuorviante.
- Q: Come individua il sistema la seconda collezione (wiki) da interrogare? → A: Da configurazione centrale (Settings): una manopola dichiara i corpora aggiuntivi da interrogare; il punto d'ingresso di composizione cabla entrambe le collezioni. I consumatori non cambiano (thin-consumer pieno; «default solo in Settings»).
- Q: Sommario con newline interni (multilinea) passato a `upsert-index`: rifiutare o normalizzare? → A: Errore esplicito ed exit code non-zero, nessuna scrittura (il trim del whitespace iniziale/finale resta scontato). La CLI scrive sempre fedelmente il testo fornito, mai lo ripara silenziosamente.
- Q: Il fan-out su due collezioni vale solo per la ricerca combinata o anche per la ricerca sulla sola documentazione? → A: Solo per la ricerca combinata. `search_code` e `search_docs` restano invariati (una collezione, filtro per tipo di documento): zero cambi di semantica per i consumatori esistenti. L'eventuale estensione di `search_docs` al wiki è un'evoluzione futura esplicita, fuori da questa feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Interrogare codice e wiki in una sola ricerca (Priority: P1)

Un consumatore del retrieval (un agente via server MCP, un motore RAG, la futura CLI) pone **una**
domanda e riceve i risultati più pertinenti pescati **sia** dal corpus del codice **sia** dal corpus
del wiki, fusi in un'unica lista ordinata per pertinenza. Oggi deve scegliere un corpus alla volta:
la conoscenza è divisa in due silos e il "perché" (wiki) non emerge accanto al "come" (codice).

**Why this priority**: è il cuore della visione «una sola verità interrogabile»; senza, la
separazione in collezioni resta un limite invece che un'architettura. È il pezzo con vero contenuto
ingegneristico della feature.

**Independent Test**: con due collezioni popolate (una di codice, una di wiki), una singola
invocazione della ricerca combinata restituisce risultati provenienti da entrambe, ordinati per
pertinenza decrescente, in numero complessivo ≤ k. Testabile in isolamento con store e embeddings
finti (nessuna rete).

**Acceptance Scenarios**:

1. **Given** due collezioni popolate (codice e wiki), **When** un consumatore esegue una ricerca
   combinata con limite `k`, **Then** riceve al più `k` risultati totali, ordinati per pertinenza
   decrescente, con almeno un risultato da ciascuna collezione quando entrambe contengono materiale
   pertinente.
2. **Given** la collezione wiki assente o vuota, **When** il consumatore esegue la ricerca combinata,
   **Then** riceve i risultati della sola collezione codice, senza errore (degradazione morbida).
3. **Given** entrambe le collezioni assenti o vuote, **When** il consumatore esegue la ricerca
   combinata, **Then** riceve una lista vuota e il sistema segnala l'evento con un avviso (nessuna
   eccezione).
4. **Given** un consumatore esistente configurato su una **singola** collezione, **When** esegue la
   ricerca combinata, **Then** il comportamento è identico a quello odierno (nessuna regressione).
5. **Given** ogni invocazione di ricerca combinata, **When** la ricerca viene eseguita, **Then** il
   sistema registra un evento strutturato con le collezioni interrogate, il `k` richiesto e il numero
   di risultati fusi (osservabilità).

---

### User Story 2 - Scrivere la riga d'indice del wiki dalla CLI (Priority: P2)

Il flusso di curazione del wiki (LLM nel loop o agente curatore) ha autorato il sommario di una
pagina e deve inserire/aggiornare la riga corrispondente nell'indice del wiki. Oggi deve modificare
il file a mano: fuori dal nucleo deterministico, senza idempotenza né esito tracciabile. Con il nuovo
sottocomando passa pagina e sommario alla CLI, che esegue la scrittura idempotente e riporta l'esito.

**Why this priority**: piccolo ma chiude il confine D↔N sull'indice: il giudizio (il sommario) resta
all'LLM, il piazzamento meccanico diventa codice testato. Dipende da nulla della User Story 1.

**Independent Test**: su un wiki fittizio con indice esistente, invocare il sottocomando con pagina
e sommario produce la riga attesa; la seconda invocazione identica non scrive nulla e riporta un
esito "no-op". Testabile in isolamento (filesystem temporaneo, nessuna rete).

**Acceptance Scenarios**:

1. **Given** un indice wiki esistente senza riga per la pagina X, **When** la CLI viene invocata con
   pagina X e un sommario, **Then** l'indice contiene la nuova riga link+sommario e l'esito riporta
   l'avvenuto inserimento.
2. **Given** un indice con riga per la pagina X e sommario S1, **When** la CLI viene invocata con
   pagina X e sommario S2 ≠ S1, **Then** la riga è aggiornata in place (nessun duplicato) e l'esito
   riporta l'avvenuto aggiornamento.
3. **Given** un indice con riga per la pagina X e sommario S, **When** la CLI viene invocata di nuovo
   con pagina X e lo stesso sommario S, **Then** nessuna scrittura avviene e l'esito riporta "no-op"
   (idempotenza).
4. **Given** un wiki senza file di indice, **When** la CLI viene invocata, **Then** termina con un
   errore esplicito e codice di uscita non-zero, indicando di inizializzare la struttura.
5. **Given** un sommario contenente caratteri non-ASCII fornito via stdin, **When** la CLI viene
   invocata su una console con codifica non-UTF-8, **Then** il testo è scritto fedelmente, senza
   corruzione (mojibake).

---

### Edge Cases

- **Pertinenza concentrata in una sola collezione**: se i migliori `k` risultati provengono tutti
  dalla stessa collezione, la fusione li restituisce tutti — nessuna quota minima per collezione.
- **Parità di punteggio tra collezioni**: l'ordinamento a parità di score deve essere deterministico
  (output stabile a input costante).
- **Collezioni con spazi vettoriali non confrontabili** (provider di embeddings diversi tra i due
  corpora): la fusione richiede lo stesso provider; in caso contrario la ricerca combinata fallisce
  con **errore esplicito** (fail-fast, mai fusione silenziosa di punteggi incomparabili) — vedi
  Clarifications, sessione 2026-06-10.
- **`k` minore del totale disponibile / maggiore del disponibile**: la fusione restituisce
  rispettivamente i migliori `k` complessivi, oppure tutti i disponibili (≤ k), senza errore.
- **Sommario vuoto o solo whitespace** (CLI): errore esplicito di input non valido (nessuna riga
  vuota scritta nell'indice).
- **Sommario su più righe** (CLI via stdin): la riga d'indice è una riga singola — l'input con
  newline interni è **rifiutato con errore esplicito** (mai scritto crudo spezzando la struttura
  dell'indice, mai normalizzato silenziosamente) — vedi Clarifications, sessione 2026-06-10.
- **Pagina con caratteri speciali nel path**: l'identità della riga è il path relativo POSIX della
  pagina; path equivalenti in forme diverse non devono produrre righe duplicate.

## Requirements *(mandatory)*

### Functional Requirements

**Gruppo A — Query congiunta multi-collezione**

- **FR-001**: Il sistema MUST offrire una capacità di ricerca combinata che interroga **sia** la
  collezione del corpus codice **sia** la collezione del corpus wiki per una singola query.
- **FR-002**: Quando la ricerca combinata è invocata con limite `k`, il sistema MUST restituire al
  più `k` risultati complessivi, ordinati per pertinenza decrescente attraverso le collezioni.
- **FR-003**: Nella fusione dei risultati di più collezioni, il sistema MUST ordinarli per il
  punteggio di similarità già presente su ogni risultato; a parità di punteggio l'ordinamento MUST
  essere deterministico.
- **FR-004**: Se una delle collezioni bersaglio è assente o vuota, il sistema MUST restituire i
  risultati delle collezioni rimanenti senza sollevare eccezioni (degradazione morbida, coerente con
  la policy tollerante esistente).
- **FR-005**: Se **tutte** le collezioni bersaglio sono assenti o vuote, il sistema MUST restituire
  una lista vuota ed emettere un avviso (nessuna eccezione).
- **FR-006**: Quando è configurata/bersagliata una sola collezione, il sistema MUST comportarsi in
  modo identico alla ricerca combinata odierna (nessuna regressione per i consumatori esistenti).
- **FR-006bis**: Il fan-out multi-collezione si applica **solo** alla ricerca combinata: le ricerche
  sul solo codice e sulla sola documentazione MUST restare invariate (una collezione, filtro per
  tipo di documento), senza alcun cambio di semantica per i consumatori esistenti.
- **FR-007**: La capacità di ricerca combinata MUST essere raggiungibile dai consumatori attraverso
  il punto d'ingresso di composizione esistente, senza che il consumatore conosca i dettagli di
  store/embeddings né il naming delle collezioni (thin-consumer). I corpora da interrogare MUST
  essere dichiarati nella configurazione centrale (i default vivono solo lì): il consumatore invoca
  la ricerca combinata senza alcun parametro aggiuntivo rispetto a oggi.
- **FR-008**: Il sistema MUST emettere, per ogni ricerca combinata, un evento di log strutturato con
  le collezioni interrogate, il `k` richiesto e il numero di risultati fusi.
- **FR-009**: Se le collezioni bersaglio non sono state costruite con lo stesso provider di
  embeddings (spazi vettoriali non confrontabili), la ricerca combinata MUST fallire con un errore
  esplicito che indichi la causa (provider eterogenei), senza restituire risultati parziali o fusi.
  È un'eccezione deliberata alla policy tollerante della facade (che resta valida per
  indice/collezione assente, FR-004/FR-005).

**Gruppo B — `upsert-index` in CLI**

- **FR-010**: La CLI del nucleo wiki MUST offrire una nuova operazione che inserisce/aggiorna una
  singola riga link+sommario nell'indice del wiki, delegando alla capacità idempotente già esistente
  nel nucleo.
- **FR-011**: L'operazione MUST accettare in input l'identificatore della pagina e il testo del
  sommario; il sommario MUST poter essere fornito come argomento **oppure** via stdin (sul modello
  dell'operazione di registro esistente).
- **FR-012**: La scrittura MUST essere idempotente: una seconda invocazione con coppia
  (pagina, sommario) identica MUST non scrivere nulla e riportare un esito "no-op".
- **FR-013**: Quando il sommario di una pagina già indicizzata cambia, il sistema MUST aggiornare la
  riga esistente in place, senza creare duplicati.
- **FR-014**: L'operazione MUST scrivere esattamente il testo fornito, senza generarlo, inferirlo o
  riscriverlo (il contenuto resta autorato esternamente — confine deterministico↔giudizio).
- **FR-015**: Se il file di indice del wiki non esiste, l'operazione MUST terminare con un errore
  esplicito e codice di uscita non-zero, indicando di inizializzare la struttura.
- **FR-016**: L'operazione MUST riportare un esito strutturato (formato macchina su richiesta,
  sintesi umana altrimenti) che indichi se è avvenuta una scrittura e se si è trattato di un
  inserimento o di un aggiornamento, coerente con gli esiti delle altre operazioni della CLI.
- **FR-017**: La lettura del sommario da stdin MUST avvenire in UTF-8, coerente con il trattamento
  già adottato per il corpo curato del registro (nessuna corruzione su console non-UTF-8).
- **FR-018**: L'operazione MUST rifiutare con errore esplicito e codice di uscita non-zero un
  sommario vuoto/solo whitespace **o contenente newline interni** (la riga d'indice è una riga
  singola); il whitespace iniziale/finale è rimosso col trim. Nessuna scrittura e nessuna
  normalizzazione silenziosa dell'input.

### Key Entities

- **Risultato di retrieval**: l'unità restituita dalla ricerca (testo, provenienza, tipo di
  documento, punteggio di pertinenza); già definita nel nucleo, riusata senza nuovi attributi.
- **Collezione**: il namespace fisico di un corpus indicizzato, identificato da (corpus, provider);
  la feature ne interroga **due** (codice e wiki) nella stessa ricerca.
- **Riga d'indice del wiki**: la voce link+sommario di una pagina nell'indice; identità = path
  relativo POSIX della pagina; il sommario è contenuto autorato esternamente.
- **Esito dell'operazione CLI**: il contratto strutturato che riporta scrittura/no-op e
  inserimento/aggiornamento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una singola invocazione di ricerca combinata su due collezioni popolate restituisce
  risultati da entrambe, ordinati per pertinenza, in numero complessivo ≤ k (verificabile con corpora
  di prova).
- **SC-002**: Con una collezione assente, la ricerca combinata restituisce il 100% dei risultati
  dell'altra senza alcun errore; con entrambe assenti restituisce lista vuota + avviso.
- **SC-003**: Per i consumatori a singola collezione, l'output della ricerca combinata è
  byte-per-byte identico a quello pre-feature sugli stessi input (zero regressioni).
- **SC-004**: La scrittura della riga d'indice è idempotente: su 100 invocazioni ripetute con lo
  stesso input, esattamente 1 scrittura e 99 esiti "no-op".
- **SC-005**: Il sommario scritto nell'indice è identico carattere-per-carattere a quello fornito
  (nessuna generazione/riscrittura, nessuna corruzione di encoding).
- **SC-006**: Entrambe le capacità funzionano su un progetto-ospite qualunque senza alcun riferimento
  al progetto Sertor (host-agnosticità dimostrabile con fixture neutre).
- **SC-007**: L'intera feature è coperta da test deterministici senza rete; la suite esistente resta
  verde e il lint pulito.

## Assumptions

- Il punteggio di pertinenza è già presente su ogni risultato di retrieval: la fusione non richiede
  nuovi attributi nel modello dati.
- Nel setup di dogfooding reale, i corpora codice e wiki sono indicizzati con lo **stesso** provider
  di embeddings, quindi con punteggi confrontabili; il caso a provider eterogenei è l'eccezione da
  governare con policy esplicita (DA-1).
- La nomenclatura del sottocomando e dei suoi argomenti segue il modello dell'operazione di registro
  esistente (`append-log`): nome `upsert-index`, pagina e sommario come argomenti dedicati, sommario
  in alternativa da stdin (DA-5, default ragionevole — confermabile in clarify senza impatto di
  scope).
- L'esito strutturato dell'operazione CLI segue lo stesso stile dei contratti già esposti dalle altre
  operazioni (DA-6: la forma esatta del contratto è decisione di piano, non di scope).
- La topologia fisica delle collezioni (stessa area di persistenza o aree distinte) è un accertamento
  tecnico da fare in fase di piano (DA-2); non cambia il comportamento richiesto, solo il design.
- Dove vive la fusione (nella porta dello store o orchestrata nel servizio di retrieval) è decisione
  di design in fase di piano (DA-3); il requisito vincola solo il comportamento osservabile.
- La forma esatta della manopola di configurazione che dichiara i corpora aggiuntivi (nome, formato)
  è decisione di piano; il requisito vincola solo che i default vivano nella configurazione centrale
  (FR-007).
- Restano fuori ambito: reranking/fusione lessicale (FEAT-004), generazione di sommari lato codice,
  nuovi tool MCP, CLI top-level `sertor` (epica `sertor-cli`).
