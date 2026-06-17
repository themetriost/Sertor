# Feature Specification: Configurazione guidata (wizard) dell'ospite — `sertor configure`

**Feature Branch**: `051-configurazione-wizard`

**Created**: 2026-06-17

**Status**: Draft

**Input**: Deriva da `requirements/sertor-cli/configurazione/requirements.md` (FEAT-003, epica
`sertor-cli`). Decomposizione **chiusa**: domande di scope Q1–Q4 già risolte con l'utente
(2026-06-17) — **(Q1 a)** modalità ibrida CI-safe; **(Q2 a)** comando separato `sertor configure`,
ri-eseguibile; **(Q3 a)** validazione statica di default + probe live opzionale dietro flag; **(Q4 a)**
solo i provider/store realmente supportati dal core (embedding Azure OpenAI / Ollama locale; store
Chroma locale / Azure AI Search). Queste decisioni NON si riaprono: eventuali ambiguità di *come*
vanno a `/speckit-plan`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Portare la configurazione da "segreti vuoti" a "pronta" con un comando guidato (Priority: P1)

Un maintainer ha appena eseguito l'installazione del RAG sul proprio progetto ospite e si ritrova un
file di configurazione con i segreti **vuoti**. Senza conoscere quali manopole servono, esegue **un
solo comando guidato** che gli fa scegliere il provider di embedding e lo store fra le opzioni
realmente disponibili, gli chiede uno per uno i valori richiesti (descrivendo cosa significano) e
scrive il risultato nel file di configurazione locale. Al termine sa di poter indicizzare, senza aver
mai aperto un editor.

**Why this priority**: È il valore terminale della feature e la causa-radice che chiude: oggi senza
configurazione il RAG non parte (il file resta con i segreti vuoti dopo l'installazione). Senza questa
storia l'utente resta bloccato o scopre l'errore solo al primo uso. Rende `install ≠ run` percorribile
da un utente reale.

**Independent Test**: Su un ambiente con file di configurazione a segreti vuoti, eseguire il comando
guidato fornendo i valori richiesti, quindi verificare che il file risultante sia dichiarato completo
per il backend/store scelti e che la validazione statica non riporti campi mancanti.

**Acceptance Scenarios**:

1. **Given** un file di configurazione con i segreti vuoti, **When** l'utente esegue il comando guidato
   e fornisce i valori richiesti, **Then** il file risultante contiene tutti i campi necessari al
   backend/store scelti e il comando dichiara la configurazione completa.
2. **Given** un terminale interattivo e un campo richiesto senza valore, **When** il comando raccoglie
   la configurazione, **Then** richiede quel campo mostrandone il nome, una breve descrizione e
   l'eventuale valore corrente.
3. **Given** la sola scelta del provider di embedding e dello store, **When** il comando determina i
   campi da raccogliere, **Then** l'insieme dei campi richiesti coincide con quello che il runtime
   esige per quella combinazione (nessuna lista divergente).

---

### User Story 2 - Configurare in modo non interattivo, sicuro per la CI (Priority: P1)

Un'automazione (o un utente che predilige l'esecuzione scriptata) configura il RAG fornendo **tutti i
valori tramite opzioni/ambiente**, senza alcun prompt. Il comando non si blocca mai in attesa di input
quando non c'è un terminale interattivo: o completa, o fallisce in modo esplicito nominando i campi
mancanti, senza scrivere una configurazione parziale.

**Why this priority**: La modalità CI-safe è parte integrante della decisione Q1 e della coerenza con
l'installer; senza di essa il comando sarebbe inadatto all'automazione e rischierebbe di bloccare le
pipeline. È P1 perché è un invariante, non un'opzione.

**Independent Test**: Eseguire il comando in un ambiente senza terminale interattivo, una volta con
tutti i valori forniti (deve completare senza prompt) e una volta con un valore richiesto mancante
(deve fallire nominandolo, senza scrivere configurazione parziale).

**Acceptance Scenarios**:

1. **Given** nessun terminale interattivo e tutti i valori richiesti forniti, **When** si esegue il
   comando, **Then** completa senza chiedere input e scrive la configurazione.
2. **Given** nessun terminale interattivo e un campo richiesto privo di valore (fornito o preesistente),
   **When** si esegue il comando, **Then** termina con esito di errore nominando il/i campo/i mancante/i
   e non scrive una configurazione parziale.
3. **Given** gli stessi input forniti due volte, **When** si esegue il comando ripetutamente, **Then**
   il contenuto del file di configurazione risultante è identico (idempotenza).

---

### User Story 3 - Configurare il profilo locale senza alcun valore cloud (Priority: P1)

Un utente che lavora local-first sceglie il profilo locale (embedding Ollama + store Chroma) e completa
la configurazione **senza dover fornire alcun valore di servizio cloud**: nessun endpoint, nessuna
chiave. Il comando non gli chiede e non pretende campi che il profilo locale non usa.

**Why this priority**: Il local-first è un pilastro del prodotto e un criterio di successo dedicato
(local-only senza cloud). Un wizard che pretendesse comunque valori cloud romperebbe l'esperienza
locale ed escluderebbe l'uso senza credenziali.

**Independent Test**: Selezionare il profilo locale ed eseguire il comando; verificare che si completi
e venga dichiarato valido senza che sia stato richiesto o impostato alcun campo di servizio cloud.

**Acceptance Scenarios**:

1. **Given** il profilo locale (Ollama + Chroma), **When** si esegue il comando, **Then** la
   configurazione si completa senza richiedere alcun valore di servizio cloud.
2. **Given** il profilo locale, **When** si esegue la validazione statica al termine, **Then** la
   configurazione è dichiarata valida senza campi mancanti.

---

### User Story 4 - Riconfigurare in sicurezza senza distruggere valori esistenti (Priority: P2)

Un utente vuole cambiare provider o aggiornare una chiave su un file di configurazione che contiene già
valori validi. Esegue di nuovo il comando: i valori già presenti non vengono sovrascritti senza una
conferma esplicita (richiesta interattiva oppure opzione di forzatura), e le righe/commenti non
gestiti dal comando restano intatti.

**Why this priority**: La ri-eseguibilità è una conseguenza diretta della scelta del comando separato
(Q2) e della non distruttività; senza queste garanzie, riconfigurare rischierebbe di cancellare lavoro
esistente. È P2 perché completa l'esperienza ma non è il primo valore consegnato.

**Independent Test**: Su un file con un valore già impostato, eseguire il comando con un nuovo valore
per quel campo senza forzatura (deve preservare l'esistente o chiedere conferma) e con forzatura (deve
sovrascrivere), verificando in entrambi i casi che le righe non gestite restino intatte.

**Acceptance Scenarios**:

1. **Given** un campo già valorizzato, **When** si esegue il comando con un valore diverso senza
   conferma né forzatura, **Then** il valore esistente è preservato (o se ne chiede conferma in
   modalità interattiva), non sovrascritto silenziosamente.
2. **Given** un campo già valorizzato, **When** si esegue il comando con forzatura esplicita, **Then**
   il valore viene aggiornato.
3. **Given** un file con righe e commenti non gestiti dal comando, **When** il comando scrive, **Then**
   quelle righe e quei commenti restano invariati.

---

### User Story 5 - Verificare che la configurazione sia completa, con probe live opzionale (Priority: P2)

Al termine della raccolta, l'utente vuole sapere se la configurazione è davvero pronta. Il comando
esegue di default una **verifica statica** (offline) e dichiara la configurazione completa o ne nomina
i campi mancanti. Su richiesta esplicita, l'utente può chiedere anche un **controllo live** che tenta
un'operazione reale verso il provider e ne riporta l'esito, separatamente dalla verifica statica; senza
quella richiesta, non viene effettuata alcuna chiamata di rete.

**Why this priority**: La validazione pre-uso evita che l'errore si scopra solo al primo
indicizzazione/ricerca (causa-radice del crash osservato quando le chiavi mancano). Il probe live è
opt-in per rispettare lo spirito install ≠ run e non costare rete di default; per questo è P2 e il
probe è uno *Should*.

**Independent Test**: Configurare con un campo mancante e verificare che il comando lo nomini ed esca
non-zero; configurare completamente e verificare l'esito valido; richiedere il controllo live e
verificare che riporti successo/fallimento separatamente, mentre senza la richiesta non avviene alcuna
chiamata di rete.

**Acceptance Scenarios**:

1. **Given** una configurazione completa per il backend/store scelti, **When** si esegue la verifica
   statica, **Then** il comando la dichiara completa ed esce con esito di successo.
2. **Given** una configurazione con campi mancanti, **When** si esegue la verifica statica, **Then** il
   comando elenca i campi mancanti ed esce con esito di errore, lasciando il file (parziale) marcato
   come incompleto.
3. **Given** la richiesta esplicita di controllo live, **When** la si esegue su una configurazione
   completa, **Then** il comando tenta un'operazione reale verso il provider e ne riporta l'esito,
   distinto dalla verifica statica.
4. **Given** nessuna richiesta di controllo live, **When** si esegue il comando, **Then** non viene
   effettuata alcuna chiamata di rete verso i provider.

---

### Edge Cases

- **File di configurazione assente** all'avvio del comando → il comando lo crea dal template di backend
  appropriato prima di applicare i valori (funziona anche se l'installazione del RAG non è stata
  eseguita prima), senza avviare alcuna operazione RAG.
- **Provider non supportato richiesto** (es. uno di quelli elencati nel brief d'epica ma privo di
  adapter, o privo di API di embedding) → non deve essere offerto come opzione: il comando propone solo
  ciò che il core onora.
- **Segreto digitato/fornito** → non deve mai comparire in chiaro a video, nei log o nei report: è
  sempre mascherato prima di qualunque emissione.
- **Esecuzione senza terminale interattivo e campo richiesto mancante** → fallimento esplicito che
  nomina il campo, senza configurazione parziale (non un blocco silenzioso in attesa di input).
- **Controllo live richiesto che fallisce** → esito di errore con messaggio azionabile, senza scartare
  la configurazione già scritta.
- **Modalità RAG che non richiede uno store** → il comando consente di completare senza store
  configurato; altrimenti lo store è richiesto.
- **Tentazione di indicizzare** al termine della configurazione → fuori ambito: il comando non avvia mai
  ingestione o creazione di indice (install ≠ run).
- **Tentazione di configurare le manopole opzionali** (cache, osservabilità, motore, code-graph,
  limiti) → fuori ambito in questa feature: restano commentate nel template (estensione futura).

## Requirements *(mandatory)*

> **Insieme delle opzioni offerte (vincolo di realtà, da Q4):** il comando propone esclusivamente i
> provider di embedding e gli store che il core supporta oggi — embedding **Azure OpenAI** e **Ollama
> locale**; store **Chroma locale** e **Azure AI Search**. I provider del brief d'epica privi di
> adapter, o privi di un'API di embedding, **non** vengono offerti: estenderli è lavoro di core (epica
> `backend-store-scala`), fuori da questa feature.
>
> **Fonte unica dei campi richiesti:** l'insieme dei campi necessari per la combinazione scelta deriva
> dalla **stessa fonte di verità usata a runtime** per la validazione del backend, non da una lista
> duplicata nel comando (nessun rischio di divergenza).

### Functional Requirements

**Gruppo A — Selezione e raccolta**

- **FR-001**: Quando l'utente avvia il comando di configurazione, il sistema MUST presentare solo i
  provider di embedding realmente supportati dal core (Azure OpenAI; Ollama locale) e nessun altro.
- **FR-002**: Quando l'utente seleziona una combinazione provider/store, il sistema MUST determinare
  l'insieme esatto dei campi di configurazione richiesti per quella combinazione dalla stessa fonte di
  verità usata a runtime.
- **FR-003**: Dove è disponibile un terminale interattivo e un valore non è stato fornito, il sistema
  MUST richiedere ciascun campo necessario, mostrandone nome, breve descrizione ed eventuale valore
  corrente.
- **FR-004**: Dove il comando è eseguito con tutti i valori richiesti forniti (o senza terminale
  interattivo), il sistema MUST completare senza prompt e MUST non bloccarsi in attesa di input
  (CI-safe).
- **FR-005**: Se un campo richiesto non ha né un valore fornito né un valore esistente e non c'è un
  terminale interattivo per richiederlo, il sistema MUST terminare con esito di errore nominando il/i
  campo/i mancante/i, senza scrivere una configurazione parziale.
- **FR-006**: Dove l'utente seleziona il profilo locale (Ollama + Chroma), il sistema MUST completare la
  configurazione senza richiedere alcun valore di servizio cloud.
- **FR-007**: Dove la modalità RAG scelta non richiede uno store vettoriale, il sistema MUST consentire
  il completamento senza uno store configurato; altrimenti MUST richiedere uno store.

**Gruppo B — Scrittura non distruttiva e segreti**

- **FR-010**: Quando la configurazione è confermata, il sistema MUST scrivere i valori nel file di
  configurazione locale con una fusione additiva e non distruttiva che preserva righe e commenti non
  gestiti.
- **FR-011**: Se un campo ha già un valore non vuoto nel file di configurazione, il sistema MUST non
  sovrascriverlo senza conferma esplicita (richiesta interattiva o opzione di forzatura esplicita).
- **FR-012**: Il sistema MUST scrivere i valori segreti solo nel file di configurazione locale (che è
  escluso dal versionamento) e MUST non scrivere mai un segreto in alcun file versionato.
- **FR-013**: Il sistema MUST mascherare i valori segreti in ogni output del terminale e in ogni report
  strutturato (nessun segreto è mai riecheggiato o registrato).
- **FR-014**: Ri-eseguire il comando con gli stessi input MUST produrre lo stesso contenuto del file di
  configurazione (idempotenza).
- **FR-015**: Se il file di configurazione non esiste quando il comando viene eseguito, il sistema MUST
  crearlo dal template di backend appropriato prima di applicare i valori (così il comando funziona
  anche se l'installazione del RAG non è stata eseguita prima), senza avviare alcuna operazione RAG.

**Gruppo C — Validazione**

- **FR-020**: Quando la configurazione termina, il sistema MUST eseguire la validazione statica e
  riportare se la configurazione è completa per il backend/store scelti.
- **FR-021**: Se la validazione statica riporta campi mancanti, il sistema MUST elencarli e terminare
  con esito di errore, lasciando il file (parziale) come scritto ma chiaramente marcato come incompleto.
- **FR-022**: Dove l'utente richiede un controllo live (opzione dedicata), il sistema MUST eseguire un
  probe minimo del provider (un'operazione reale) e riportarne l'esito separatamente dalla validazione
  statica; senza la richiesta, MUST non effettuare alcuna chiamata di rete.
- **FR-023**: Se un controllo live richiesto fallisce, il sistema MUST riportare il fallimento con un
  messaggio azionabile e un esito di errore, senza scartare la configurazione scritta.

**Gruppo D — Osservabilità, interazione e invarianti**

- **FR-030**: Il sistema MUST non avviare mai ingestione RAG o creazione di indice come parte della
  configurazione (install ≠ run).
- **FR-031**: Quando la configurazione si completa, il sistema MUST emettere un riepilogo leggibile
  (provider/store scelti, campi impostati, esito della validazione) e, su richiesta di output
  strutturato, un report machine-readable — nessuno dei due contenente valori segreti.
- **FR-032**: Il sistema MUST terminare con esito di successo su configurazione completa e valida, con
  esito di errore su configurazione incompleta/invalida o su controllo live fallito, e con esito di uso
  errato su invocazione malformata.
- **FR-033**: Il comando MUST restare host-agnostico e assistant-agnostico: non presuppone uno specifico
  repository ospite né uno specifico assistente, oltre ai prerequisiti già richiesti dal prodotto.

### Key Entities

- **Profilo di configurazione**: la combinazione provider-di-embedding × store che l'utente sceglie fra
  le opzioni supportate (es. profilo locale Ollama + Chroma; profilo Azure). Determina quali campi sono
  richiesti.
- **Campo di configurazione richiesto**: una manopola necessaria al profilo scelto (es. endpoint,
  chiave, deployment di embedding), con nome, descrizione e natura (segreto o no). L'insieme dei campi
  richiesti è derivato dalla fonte di verità di runtime, non duplicato.
- **File di configurazione locale**: il file dell'ambiente runtime dell'ospite (escluso dal
  versionamento) in cui i valori, inclusi i segreti, vengono scritti in modo additivo e non distruttivo.
- **Segreto**: un valore sensibile (es. chiave d'accesso) che vive solo nel file di configurazione
  locale, mai versionato, sempre mascherato in output e log.
- **Validazione statica**: il controllo offline che stabilisce se la configurazione è completa per il
  backend/store scelti, elencando i campi mancanti; è la sola fonte dei campi richiesti.
- **Controllo live (probe)**: la verifica opt-in che tenta un'operazione reale verso il provider per
  confermare che la configurazione funzioni davvero, distinta dalla validazione statica.
- **Esito della configurazione**: il risultato riportato all'utente (provider/store scelti, campi
  impostati, validazione, eventuale probe), in forma leggibile e machine-readable, privo di segreti.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (configurazione completa senza editor)**: un utente porta il file di configurazione da
  "segreti vuoti" a "pronto per l'indicizzazione" eseguendo **un solo** comando guidato, senza aprire
  manualmente il file.
- **SC-002 (validazione pre-uso)**: al termine, il comando dichiara la configurazione **valida** se e
  solo se la validazione statica non riporta campi mancanti per il backend/store scelti; altrimenti
  nomina i campi mancanti ed esce con esito di errore.
- **SC-003 (segreti mai versionati)**: in **0** esecuzioni un segreto finisce in un file tracciato dal
  versionamento; i segreti vivono solo nel file di configurazione locale.
- **SC-004 (solo opzioni reali)**: il comando propone esclusivamente i provider di embedding e gli store
  supportati dal core; in **0** casi offre un'opzione che il RAG non può poi onorare.
- **SC-005 (non distruttività & idempotenza)**: ri-eseguire la configurazione preserva i valori già
  presenti salvo conferma di sovrascrittura; **due** esecuzioni con gli stessi input producono **lo
  stesso** file di configurazione.
- **SC-006 (CI-safe)**: il comando è eseguibile in modo **non interattivo** (tutti i valori via
  opzioni/ambiente) e in **0** casi si blocca in attesa di input quando non c'è un terminale
  interattivo.
- **SC-007 (local-only senza cloud)**: scegliendo il profilo locale (Ollama + Chroma) la configurazione
  si completa **senza** richiedere alcun valore di servizio cloud.
- **SC-008 (nessun segreto a video/log)**: in **0** output del terminale, log o report compare un valore
  segreto in chiaro.
- **SC-009 (install ≠ run)**: in **0** esecuzioni la configurazione avvia ingestione o creazione di
  indice.

## Assumptions

- **Le decisioni di scope Q1–Q4 sono risolte a monte** (requirements, 2026-06-17) e codificate qui:
  modalità ibrida CI-safe (Q1 a); comando separato `sertor configure`, ri-eseguibile (Q2 a); validazione
  statica di default + controllo live opzionale (Q3 a); solo provider/store supportati dal core (Q4 a).
  Non vengono riaperte: eventuali ambiguità di *come* sono di pertinenza di `/speckit-plan`.
- **Confine "minimo vitale"**: il comando configura solo ciò che serve a far girare il RAG (provider di
  embedding, store, relativi segreti). Il wizard delle manopole **opzionali** (cache, osservabilità,
  motore, code-graph, limiti) è un'estensione *Could*, fuori ambito: quelle restano commentate nel
  template. **[ASSUNTO]**
- **Fuori ambito (capacità future con casa durevole):** aggiungere nuovi provider/store (OpenAI
  pubblico, Anthropic, Copilot-embeddings, PGVector, MongoDB) è lavoro di core → epica
  `backend-store-scala`; configurazione di capacità non-RAG (wiki/governance non hanno provider da
  configurare); gestione segreti esterna (key vault, secret manager); indicizzazione/esecuzione del RAG
  (resta ai comandi di esecuzione, install ≠ run); distribuzione del comando su altri assistenti (il
  comando è assistant-agnostico per costruzione).
- **Riuso, non duplicazione**: l'insieme dei campi richiesti deriva dalla validazione di backend di
  runtime (fonte unica, niente drift) e la scrittura riusa la fusione additiva del file di
  configurazione già usata dall'installazione del RAG. Le forme concrete di questi riusi sono *come* di
  design.
- **Probe live = Should** (opt-in): il controllo live è una storia P2 e un requisito *Should*; il valore
  P1 è completo con la sola validazione statica.
- **Non-regressione**: il nuovo comando è additivo e non altera il comportamento runtime delle capacità
  già consegnate (lettura della configurazione, installazione del RAG, esecuzione).
- **Domande di design ancora aperte (→ `/speckit-plan`, non bloccano la spec)**: forma concreta della
  presentazione delle opzioni e dei prompt; meccanismo di rilevamento del terminale interattivo; forma
  del probe live e del provider su cui agisce; nomi esatti di comando/opzioni e mappatura sugli exit
  code; sede e forma del report strutturato. Sono ambiguità di *come*, non di *cosa/perché*.
