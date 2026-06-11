# Feature Specification: CLI di esecuzione RAG `sertor-rag`

**Feature Branch**: `011-cli-esecuzione-rag`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "CLI di esecuzione RAG `sertor-rag`: console-script del pacchetto `sertor-core` (accanto a `sertor-wiki-tools`) che rende eseguibili da riga di comando le capacità di retrieval del core senza scrivere codice. Sottocomandi: `index <path>` e `search <query>`. Lettura della configurazione dalla config centralizzata del core, con validazione statica dei parametri del backend scelto. Osservabilità a runtime (-v, --log-json, --log-config dictConfig) + log strutturato dei fallimenti ai boundary del core. Vincoli: CLI sottile, install≠run, repo-agnostica, exit code per scripting, errori leggibili, testabile con mock senza rete. Fonte: requirements/sertor-cli/esecuzione/requirements.md (rev. 2026-06-11), DA-8 in requirements/sertor-cli/epic.md §9."

> **Contesto di prodotto.** Oggi le capacità di retrieval del core sono usabili solo come libreria
> Python o via server MCP. Questa feature aggiunge la terza superficie: il terminale. Per la
> decisione DA-8 (epica `sertor-cli`), il comando `sertor` è riservato all'installer
> (`sertor install <capacità>`); l'esecuzione vive nei console-script del core — **`sertor-rag`**
> (questa feature) accanto a `sertor-wiki-tools` (già consegnato). Requisiti EARS a monte:
> `requirements/sertor-cli/esecuzione/requirements.md` (rev. 2026-06-11).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Indicizzare un repository dal terminale (Priority: P1)

Un maintainer (o un agente LLM che usa la CLI come strumento) vuole costruire l'indice vettoriale di
un repository qualunque con un solo comando — `sertor-rag index <path>` — senza scrivere codice
Python. Al termine ottiene un report sintetico: numero di documenti/chunk indicizzati e dimensione
degli embedding.

**Why this priority**: è il prerequisito di ogni altra operazione (senza indice non c'è ricerca) ed
è il pezzo che oggi obbliga a scrivere codice (`build_indexer().index(...)`). Da solo abilita il
dogfooding via CLI del repo Sertor.

**Independent Test**: su un repository di prova con provider/store mock, lanciare
`sertor-rag index <path>` e verificare exit code 0, report con conteggi corretti, e che i file
sorgente del repository non siano stati modificati.

**Acceptance Scenarios**:

1. **Given** un repository leggibile e una configurazione valida, **When** l'utente esegue
   `sertor-rag index <path>`, **Then** la CLI costruisce l'indice via core (full rebuild) e stampa
   il numero di chunk indicizzati e la dimensione embedding, uscendo con codice 0.
2. **Given** un `<path>` inesistente o non leggibile, **When** l'utente esegue `sertor-rag index`,
   **Then** la CLI stampa un errore leggibile ed esce con codice non-zero senza creare alcun indice.
3. **Given** un provider di embeddings indisponibile a metà operazione, **When** l'indicizzazione
   fallisce, **Then** la CLI interrompe, presenta l'errore del core in forma leggibile e non lascia
   un indice parziale o corrotto (l'indice preesistente resta valido).
4. **Given** un corpus selezionato (`--corpus` o configurazione), **When** si indicizza e si
   interroga, **Then** le operazioni avvengono nella collezione namespaced corrispondente, senza
   mescolare corpora distinti.

---

### User Story 2 - Interrogare l'indice dal terminale (Priority: P2)

Un maintainer (o un agente) vuole interrogare l'indice — `sertor-rag search <query>` — e ottenere i
top-k risultati più rilevanti con metadati citabili: path del file, tipo (code/doc), id del chunk,
punteggio, anteprima troncata. Può regolare `k`, filtrare per tipo (`code|doc|both`), chiedere
l'output JSON per consumo programmatico e il testo completo del chunk on-demand (`--full`).

**Why this priority**: è il valore d'uso della CLI (LSC-2), ma dipende dall'esistenza di un indice
(US1); testabile indipendentemente con un indice precostruito.

**Independent Test**: con un indice mock precostruito, lanciare `sertor-rag search "query"` e
verificare formato dei risultati (campi minimi presenti, anteprime troncate), rispetto di `-k` e
`--type`, equivalenza informativa tra output umano e `--json`.

**Acceptance Scenarios**:

1. **Given** un indice esistente, **When** l'utente esegue `sertor-rag search <query>`, **Then** la
   CLI restituisce i top-k risultati, ciascuno con almeno path, tipo documento, id chunk, punteggio
   e anteprima troncata (non il testo integrale).
2. **Given** opzioni esplicite `-k`/`--type`, **When** la ricerca viene eseguita, **Then** la CLI le
   rispetta; in assenza, usa i default della configurazione centralizzata (`default_k`, modalità `both`).
3. **Given** l'indice non esiste, **When** si richiede una ricerca, **Then** la CLI stampa un errore
   leggibile che indica di costruire prima l'indice ed esce non-zero (nessun risultato vuoto silenzioso).
4. **Given** `--json`, **When** la ricerca viene eseguita, **Then** l'output è un array JSON
   strutturato adatto al consumo da agente/script; le anteprime restano troncate salvo `--full`.

---

### User Story 3 - Rendere osservabili le operazioni (Priority: P3)

Un operatore vuole vedere cosa fa la CLI e collegare i log a sistemi esterni senza toccare il
codice: `-v/--verbose` rende visibili gli eventi INFO strutturati del core, `--log-json` li emette
come record JSON, `--log-config <file>` carica una configurazione di logging esterna (dictConfig
YAML/JSON) per agganciare appender arbitrari (file, syslog, Splunk/ELK). I fallimenti ai boundary
del core (embeddings, store, indexing) producono un evento di log strutturato prima della
propagazione dell'errore; nessun segreto compare mai nei log.

**Why this priority**: completa il Principio IX (osservabilità) e l'uso operativo/automazione, ma la
CLI è già utile senza (US1+US2).

**Independent Test**: eseguire index/search con mock e le opzioni di logging attive; verificare
l'emissione dei record (formato, campi), il caricamento del dictConfig e l'assenza di segreti nei
log; provocare un fallimento al boundary e verificare l'evento strutturato.

**Acceptance Scenarios**:

1. **Given** `-v`, **When** un'operazione viene eseguita, **Then** gli eventi INFO strutturati del
   core sono visibili sulla console.
2. **Given** `--log-json`, **When** un'operazione emette log, **Then** ogni evento è un record JSON
   strutturato adatto all'ingestione esterna.
3. **Given** `--log-config <file>` valido (dictConfig YAML/JSON), **When** la CLI parte, **Then** la
   configurazione è caricata e gli appender definiti ricevono gli eventi, senza modifiche al codice.
4. **Given** un fallimento a un boundary del core (embeddings/store/indexing), **When** l'errore si
   verifica, **Then** un evento di log strutturato (operazione, provider/backend, ragione) è emesso
   prima che l'errore sia propagato.

---

### Edge Cases

- `<path>` esiste ma è un file, non una directory → errore leggibile, exit non-zero, nessun indice.
- Configurazione backend incompleta (es. `azure` senza endpoint/chiave/deployment) → blocco
  **prima** di contattare qualunque servizio, con errore esplicito che nomina i parametri mancanti;
  il default `local` è completo per costruzione e non viene mai bloccato staticamente.
- Provider formalmente configurato ma irraggiungibile (es. Ollama spento) → errore a runtime
  presentato in forma leggibile (non stack trace), exit non-zero.
- Query vuota o solo spazi in `search` → errore d'uso leggibile, exit non-zero.
- Sottocomando ignoto o argomento obbligatorio mancante → messaggio d'uso + exit non-zero, nessuna
  operazione parziale.
- `--log-config` con file inesistente o malformato → errore leggibile, exit non-zero, nessuna
  operazione eseguita.
- Repository molto piccolo o vuoto → l'indicizzazione completa con report a zero/n bassi, senza errori.
- Import del pacchetto o installazione → nessuna operazione RAG avviata (install ≠ run).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La CLI MUST esporre un unico entry-point a riga di comando `sertor-rag` (console-script
  del pacchetto core) che smista ai sottocomandi `index` e `search`. *(REQ-001 rev. DA-8)*
- **FR-002**: La CLI MUST fornire testo di help per l'entry-point e per ogni sottocomando. *(REQ-002)*
- **FR-003**: In caso di sottocomando ignoto o argomento obbligatorio mancante, la CLI MUST stampare
  un errore leggibile e uscire non-zero, senza operazioni parziali. *(REQ-003)*
- **FR-004**: La CLI MUST restituire exit code 0 in successo e non-zero in errore. *(REQ-004)*
- **FR-005**: `index <path>` MUST costruire l'indice vettoriale del repository via core (full
  rebuild) e riportare numero di chunk e dimensione embedding. *(REQ-010)*
- **FR-006**: Se `<path>` non esiste o non è leggibile, `index` MUST fallire con errore leggibile
  senza creare alcun indice. *(REQ-011)*
- **FR-007**: Se provider/store è indisponibile durante l'indicizzazione, la CLI MUST interrompere,
  presentare l'errore del core in forma leggibile e non lasciare un indice parziale/corrotto. *(REQ-012)*
- **FR-008**: `index` MUST essere non distruttivo sul repository target (scrive solo nello store
  dell'indice). *(REQ-013)*
- **FR-009**: Dove l'utente seleziona un corpus (`--corpus` o configurazione), la CLI MUST
  indicizzare e interrogare la collezione namespaced corrispondente; il flag esplicito prevale sulla
  configurazione. *(REQ-014)*
- **FR-010**: `search <query>` MUST restituire i top-k risultati con almeno path, tipo documento
  (code/doc), id chunk, punteggio e anteprima troncata; `--full` restituisce il testo completo
  on-demand. *(REQ-020)*
- **FR-011**: `search` MUST onorare `-k` e `--type code|doc|both` se specificati, altrimenti usare i
  default della configurazione centralizzata (`default_k`; modalità `both`). *(REQ-021)*
- **FR-012**: Se l'indice non esiste, `search` MUST stampare un errore leggibile che indichi di
  costruire prima l'indice e uscire non-zero (nessun risultato vuoto silenzioso). *(REQ-022)*
- **FR-013**: Con `--json`, `search` MUST stampare i risultati come array JSON strutturato; le
  anteprime restano troncate in entrambi i formati salvo `--full`. *(REQ-023)*
- **FR-014**: La CLI MUST leggere tutte le scelte operative dalla configurazione centralizzata del
  core (env e/o `.env`), senza richiedere modifiche al codice. *(REQ-040)*
- **FR-015**: Se i parametri richiesti dal backend selezionato sono assenti o incompleti, la CLI
  MUST bloccare l'operazione con errore esplicito e leggibile **prima** di contattare qualunque
  servizio (validazione statica; la raggiungibilità resta errore a runtime, FR-007). *(REQ-041 rev.)*
- **FR-016**: La CLI MUST NOT scrivere valori segreti su file versionati. *(REQ-042)*
- **FR-017**: Con `-v/--verbose`, la CLI MUST abilitare l'emissione degli eventi di log INFO
  strutturati del core. *(REQ-050)*
- **FR-018**: Con `--log-json`, la CLI MUST emettere gli eventi di log come record JSON strutturati
  (uno per evento). *(REQ-051)*
- **FR-019**: Con `--log-config <file>` in forma dictConfig (YAML o JSON), la CLI MUST caricare la
  configurazione così che appender arbitrari si possano agganciare senza modificare il codice. *(REQ-052)*
- **FR-020**: Se un'operazione fallisce a un boundary del core (embeddings, vector store, indexing),
  il sistema MUST emettere un evento di log strutturato (operazione, provider/backend, ragione)
  prima della propagazione dell'errore. Estensione additiva del core. *(REQ-053)*
- **FR-021**: Il sistema MUST documentare l'insieme dei campi di log strutturati emessi per
  operazione. *(REQ-054)*
- **FR-022**: CLI e core MUST NOT includere segreti nei record di log (redazione prima
  dell'emissione). *(REQ-055)*
- **FR-023**: Installazione, aggiunta o semplice import della CLI MUST NOT avviare alcuna operazione
  di indicizzazione o RAG; ogni operazione richiede un comando esplicito. *(REQ-060)*
- **FR-024**: La CLI MUST operare su qualunque repository fornito come path, senza assunzioni
  hardcoded su struttura interna, linguaggi o dimensione. *(REQ-061)*

### Key Entities

- **Report di indicizzazione**: esito di `index` — numero di documenti/chunk indicizzati, dimensione
  embedding, corpus/collezione di destinazione.
- **Risultato di ricerca (vista CLI)**: proiezione del risultato del core — path, tipo documento,
  id chunk, punteggio, anteprima troncata (testo completo solo con `--full`).
- **Evento di log strutturato**: record con operazione, provider/backend, esito/ragione; mai segreti.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un utente indicizza un repository qualunque con **un solo comando** e ottiene il
  report (chunk + dimensione embedding) senza scrivere alcuna riga di codice. *(LSC-1)*
- **SC-002**: Un utente ottiene i top-k risultati con tutti i metadati citabili da **un solo
  comando**, in formato umano e JSON. *(LSC-2)*
- **SC-003**: In **0** casi l'installazione/import avvia operazioni RAG: ogni operazione parte solo
  da invocazione esplicita. *(LSC-4)*
- **SC-004**: Con configurazione backend incompleta, il **100%** delle operazioni RAG si blocca con
  errore esplicito prima di qualunque chiamata a servizi. *(LSC-5)*
- **SC-005**: Le stesse operazioni completano su **≥2 repository diversi** senza modifiche e senza
  alterare i file dei repository. *(LSC-6)*
- **SC-006**: I log strutturati sono visibili a richiesta e collegabili ad appender esterni
  (file/syslog/Splunk) **senza modificare il codice**. *(LSC-7)*
- **SC-007**: L'intera superficie CLI è verificabile in automatico con provider/store mock, senza
  rete né servizi cloud. *(NFR-02)*
- **SC-008 (dogfood)**: Il repo Sertor stesso è indicizzato e interrogato via `sertor-rag` con
  risultati coerenti con quelli della facade/server MCP a parità di configurazione.

## Assumptions

- Il console-script `sertor-rag` vive nel pacchetto `sertor-core` esistente (accanto a
  `sertor-wiki-tools`); la distribuzione pubblica (PyPI/git+url) resta fuori ambito. *(A-1 rev.)*
- La configurazione è definita altrove (env/`.env`, default del core): la CLI la legge, non la
  scrive; il wizard interattivo è un'altra feature. *(A-2)*
- Il provider reale (Ollama/Azure) è un prerequisito d'esecuzione, non di costruzione: i test usano
  mock; il dogfooding reale richiede un provider configurato. *(A-3)*
- Fuori ambito (DA-8 e revisione 2026-06-11): il comando installer `sertor install <capacità>`;
  l'indicizzazione del wiki in corpus dedicato (già coperta da `sertor-wiki-tools index`); il wizard
  di configurazione; la pubblicazione del pacchetto.
- Policy d'errore del core rispettata: la facade è tollerante, il motore baseline è strict — per
  FR-012 la CLI imbocca la via strict; la scelta puntuale è di design, non di questa spec.
