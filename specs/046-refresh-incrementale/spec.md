# Feature Specification: Refresh incrementale dell'indice RAG

**Feature Branch**: `046-refresh-incrementale`

**Created**: 2026-06-16

**Status**: Draft

**Input**: Deriva da `requirements/sertor-core/refresh-incrementale/requirements.md` (FEAT-009, epica `sertor-core`) + `corollario-costo.md`. Decisioni di scope F1/F2 prese con l'utente; prior art CocoIndex/LlamaIndex/LangChain.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ri-indicizzare solo ciò che è cambiato (Priority: P1)

L'operatore di un progetto grande modifica pochi file e rilancia l'indicizzazione. Il sistema riconosce
quali file sono cambiati e **riprocessa solo quelli** — lasciando intatto tutto il resto — così la
ricerca riflette le modifiche in un tempo proporzionale al cambiamento, non al corpus intero. Tutte le
modalità di ricerca (per significato, per parole chiave, per struttura del codice) restano allineate.

**Why this priority**: È il cuore della feature e l'unico motivo per cui esiste. Su ospiti grandi il
re-index completo a ogni modifica costa minuti e scoraggia il tenere l'indice fresco — in contrasto con
l'essenza «contesto dell'agente sempre reale». Senza questa storia non c'è feature.

**Independent Test**: Su un corpus indicizzato, modificare un solo file e rilanciare; verificare che solo
quel file è stato riprocessato e che una query restituisce il contenuto aggiornato, in un tempo molto
inferiore al re-index completo.

**Acceptance Scenarios**:

1. **Given** un corpus già indicizzato, **When** si modifica un file e si rilancia l'indicizzazione,
   **Then** solo quel file viene riprocessato (gli altri sono saltati) e i suoi nuovi contenuti compaiono
   nei risultati di ricerca.
2. **Given** un corpus già indicizzato, **When** si rilancia senza alcuna modifica, **Then** il sistema
   non apporta cambiamenti all'indice (idempotenza).
3. **Given** un file il cui timestamp è cambiato ma il contenuto è identico, **When** si rilancia,
   **Then** il file è trattato come invariato e non viene riprocessato.

---

### User Story 2 - Rimuovere ciò che è stato cancellato (Priority: P1)

L'operatore elimina (o rinomina) un file dalla sorgente e rilancia l'indicizzazione. Il sistema **rimuove
dall'indice** tutte le tracce di quel file, così la ricerca non restituisce più contenuti che non
esistono più.

**Why this priority**: Un indice che non rimuove i file spariti serve **contesto stantio/contraddittorio
con piena confidenza** — il fallimento più pericoloso per Sertor. La gestione delle cancellazioni è parte
integrante dell'incrementale, non un extra.

**Independent Test**: Eliminare un file indicizzato e rilanciare; verificare che nessuna query restituisce
più contenuti di quel file, in tutte le modalità di ricerca.

**Acceptance Scenarios**:

1. **Given** un file presente nell'indice, **When** lo si elimina dalla sorgente e si rilancia,
   **Then** nessun risultato di ricerca proviene più da quel file.
2. **Given** un file rinominato/spostato, **When** si rilancia, **Then** l'indice riflette la nuova
   collocazione e non conserva la vecchia.

---

### User Story 3 - Default incrementale con full rebuild come rete di sicurezza (Priority: P1)

Di default il sistema indicizza in modo incrementale quando esiste uno stato precedente valido. L'operatore
può sempre forzare un **rebuild completo da zero** (reset sicuro); inoltre, se lo stato precedente manca o
è incompatibile, il sistema **esegue automaticamente un full rebuild** invece di produrre un indice
parziale.

**Why this priority**: È il modello di attivazione scelto (incrementale di default). Il full su richiesta e
come fallback è la difesa contro la deriva silenziosa, indispensabile perché il default-incrementale alza
il rischio di disallineamento dalla realtà.

**Independent Test**: (a) Eliminare lo stato persistito e rilanciare → verificare che parte un full rebuild
e l'indice è completo; (b) forzare il full su un corpus già incrementale → verificare l'indice ricostruito
da zero.

**Acceptance Scenarios**:

1. **Given** uno stato precedente valido, **When** si rilancia senza opzioni, **Then** il sistema indicizza
   in modo incrementale.
2. **Given** assenza/incompatibilità dello stato precedente, **When** si rilancia, **Then** il sistema
   esegue un full rebuild completo (e rigenera lo stato), mai un indice parziale.
3. **Given** un corpus indicizzato, **When** l'operatore richiede esplicitamente il full rebuild,
   **Then** l'intero indice è ricostruito da zero e lo stato riscritto.

---

### User Story 4 - Correttezza quando cambia la logica di elaborazione (Priority: P2)

Quando cambia la **logica** con cui i file vengono spezzati o analizzati (non i file in sé), il sistema
riprocessa i file interessati, così nessun contenuto prodotto da logica vecchia sopravvive nell'indice.

**Why this priority**: Senza questa garanzia, dopo un aggiornamento del prodotto l'indice incrementale
servirebbe risultati prodotti da logica obsoleta — un drift invisibile. È un pilastro della correttezza,
ma scatta meno spesso delle modifiche ai file.

**Independent Test**: Simulare un cambio della versione della logica di elaborazione e rilanciare;
verificare che i file interessati sono riprocessati e che non restano unità prodotte dalla versione
precedente.

**Acceptance Scenarios**:

1. **Given** un indice costruito con una certa versione della logica, **When** la versione cambia e si
   rilancia, **Then** i file interessati sono riprocessati e l'indice non contiene più unità della vecchia
   versione.

---

### User Story 5 - Vedere cosa è cambiato a ogni run (Priority: P3)

A ogni run incrementale il sistema riporta **quanti file** erano invariati / nuovi / modificati /
cancellati e **quante unità** sono state aggiunte o rimosse, così una deriva è visibile invece che
silenziosa.

**Why this priority**: Rende osservabile la salute dell'aggiornamento (mitigante chiave del rischio di
drift), ma è di supporto: la correttezza non dipende dal report.

**Independent Test**: Eseguire un run incrementale dopo modifiche note e verificare che i conteggi riportati
corrispondono ai cambiamenti effettuati.

**Acceptance Scenarios**:

1. **Given** un set noto di modifiche, **When** si esegue il run incrementale, **Then** il report dei
   conteggi (invariati/nuovi/modificati/cancellati, unità +/−) corrisponde alle modifiche.

---

### Edge Cases

- **Stato persistito corrotto o di formato incompatibile** → il sistema ripiega su un full rebuild (mai
  un indice parziale).
- **File modificato durante il run** → il run non deve lasciare quel file in uno stato parziale e
  incoerente; l'incoerenza va segnalata.
- **Timestamp cambiato ma contenuto identico** → trattato come invariato (nessun riprocessamento).
- **Cambio di provider/dimensioni di embedding** → lo stato è separato per `(corpus, provider)` così non
  si mescolano indici incompatibili.
- **Run interrotto a metà** (errore I/O / parsing) → niente indice silenziosamente parziale per il file
  coinvolto; il fallimento è esplicito.
- **Corpus piccolo** → l'incrementale non deve essere più lento di un full (per pochi file il full è già
  rapido).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST mantenere uno **stato persistito dell'indice** che registra, per ogni file
  sorgente, l'ultima modifica osservata, un'impronta del contenuto, le unità (chunk) da esso derivate e la
  versione della logica di elaborazione che le ha prodotte.
- **FR-002**: All'avvio di un run incrementale, il sistema MUST classificare ciascun file corrente come
  invariato, nuovo, modificato o cancellato confrontando timestamp (pre-filtro rapido) e impronta del
  contenuto (conferma) con lo stato persistito.
- **FR-003**: Se il timestamp differisce ma l'impronta del contenuto è identica, il sistema MUST trattare
  il file come invariato e non riprocessarlo.
- **FR-004**: Per un file nuovo o modificato, il sistema MUST riprocessare **solo** quel file e aggiornare
  in modo **mirato** le sue unità nell'indice di ricerca per significato.
- **FR-005**: Per un file modificato o cancellato, il sistema MUST rimuovere in modo **mirato** le unità
  precedentemente derivate da quel file, senza azzerare e ricostruire l'intero indice.
- **FR-006**: Per un file invariato, il sistema MUST saltarne lettura, elaborazione e scrittura.
- **FR-007**: Il sistema MUST conservare nello stato persistito le unità (o il necessario per ricostruirle)
  così che l'indice per **parole chiave** e la **mappa strutturale del codice** possano essere rigenerati
  **senza** rileggere o rielaborare i file invariati.
- **FR-008**: Quando l'insieme delle unità cambia, il sistema MUST rigenerare l'indice per parole chiave e
  la mappa strutturale del codice in modo che entrambi riflettano lo stato aggiornato.
- **FR-009**: In presenza di uno stato persistito valido, il sistema MUST indicizzare in modo
  **incrementale di default**.
- **FR-010**: Quando l'operatore richiede esplicitamente un rebuild completo, il sistema MUST ricostruire
  l'intero indice da zero e riscrivere lo stato.
- **FR-011**: Se lo stato persistito è assente, incompatibile o corrotto, il sistema MUST ripiegare su un
  full rebuild (rigenerando lo stato) invece di produrre un indice parziale.
- **FR-012**: Il sistema MUST garantire che un run incrementale produca un indice **equivalente** a un full
  rebuild sulla stessa sorgente (stesse unità, stesso indice per significato, stesso indice per parole
  chiave, stessa mappa strutturale).
- **FR-013**: Quando la versione della logica di elaborazione registrata differisce da quella corrente, il
  sistema MUST riprocessare i file interessati, così che nessuna unità prodotta da logica vecchia
  sopravviva.
- **FR-014**: Se un run incrementale fallisce a metà per un file (errore di lettura/parsing/scrittura), il
  sistema MUST segnalare il fallimento e NON lasciare quel file in uno stato parziale e incoerente.
- **FR-015**: Al termine di un run incrementale, il sistema MUST riportare i conteggi di file
  invariati/nuovi/modificati/cancellati e di unità aggiunte/rimosse.
- **FR-016**: Il sistema MUST emettere il run incrementale come evento osservabile, coerentemente con i run
  di indicizzazione completi.
- **FR-017**: Indicizzando più volte la stessa sorgente in modo incrementale, il sistema MUST non apportare
  ulteriori modifiche (idempotenza).
- **FR-018**: La capacità incrementale MUST essere raggiungibile attraverso i vehicles (CLI/MCP), senza un
  percorso d'accesso separato di sola libreria.

### Key Entities

- **Stato persistito dell'indice (manifest)**: la memoria di «cosa è già indicizzato». Per ogni file:
  ultima modifica, impronta del contenuto, unità derivate, versione della logica. È un artefatto locale e
  rigenerabile, separato per `(corpus, provider)`. È la fonte per riconoscere i cambiamenti, rimuovere le
  tracce dei file spariti e rigenerare gli indici secondari a basso costo.
- **File sorgente**: l'unità di cambiamento; assume uno stato (invariato / nuovo / modificato /
  cancellato) determinato dal confronto con il manifest.
- **Unità derivata (chunk)**: il pezzo in cui un file è spezzato; ha un identificatore stabile e una
  versione della logica che l'ha prodotta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Modificando un solo file su un corpus grande, il tempo di re-index è **proporzionale al
  delta** e sostanzialmente inferiore al full rebuild dello stesso corpus (es. ordini di grandezza più
  rapido quando cambia una frazione minima dei file).
- **SC-002**: Dopo un run incrementale, una qualunque query restituisce gli **stessi risultati** che si
  otterrebbero da un full rebuild sulla stessa sorgente, in tutte le modalità (significato, parole chiave,
  struttura).
- **SC-003**: Un file cancellato non compare in **0** query dopo il run incrementale.
- **SC-004**: Al cambio della versione della logica di elaborazione, **100%** dei file interessati sono
  riprocessati e **0** unità della versione precedente sopravvivono.
- **SC-005**: Con stato persistito assente o incompatibile, **100%** dei run producono un indice completo
  (full automatico) e **0** indici parziali.
- **SC-006**: Un secondo run incrementale su sorgente invariata produce **0** modifiche all'indice.
- **SC-007**: **100%** dei run incrementali riportano i conteggi del delta (file e unità).

## Assumptions

- **Granularità a file**: l'unità di cambiamento è il file (un file modificato è rielaborato per intero);
  il risparmio sul costo di vettorializzazione a livello di singola unità è già coperto dalla cache
  esistente (FEAT-019). Il rilevamento a grana più fine è fuori MVP.
- **Manifest locale e non versionato**: lo stato persistito è un artefatto rigenerabile, locale,
  gitignored, separato per `(corpus, provider)`; non contiene segreti.
- **Accesso via vehicles** (CLI/MCP), coerente col Principio XI; nessun percorso di sola libreria.
- **Dipendenza FEAT-019** (cache di vettorializzazione per impronta del contenuto): riusata, non
  ridefinita.
- **Fuori ambito (capacità future)**: modalità live/watch del filesystem; notifiche di cambiamento push da
  sorgenti remote; indici per parole chiave e mappa strutturale **veramente** incrementali (qui sono
  rigenerati dallo stato, non aggiornati in modo mirato); parallelizzazione dell'elaborazione;
  riconoscimento dei rinomini come tali (nel primo taglio = cancellazione + nuovo); accesso concorrente
  multi-processo allo stesso indice.
- **Domande di design rinviate a `/speckit-clarify` e `/speckit-plan`** (non bloccano la spec): sede/forma
  del manifest; eventuale full periodico di riconciliazione anti-drift; riconoscimento dei rinomini;
  locking per più processi concorrenti; soglia oltre la quale l'incrementale conviene rispetto al full.
