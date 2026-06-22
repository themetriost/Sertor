# Feature Specification: Cattura memoria su GitHub Copilot CLI (FEAT-008)

**Feature Branch**: `073-cattura-copilot-cli` · **Created**: 2026-06-22 · **Status**: Draft

<!-- Deriva da: FEAT-008 (epica memoria-conversazioni) — requirements/memoria-conversazioni/cattura-multi-assistente/requirements.md -->

**Input**: FEAT-008 dell'epica `memoria-conversazioni`. L'MVP della memoria conversazioni è completo e
host-agnostico in tutto il suo tier — FEAT-001 cattura e archivia (`memory.sqlite`, contenuto già
**scrubbed**), FEAT-002 cerca **full-text**, FEAT-004 cerca per **significato**, FEAT-003 distilla,
feature 035 espone CLI + hook `SessionEnd` — **tranne un punto**: la **cattura** dei transcript, che è
host-specifica e oggi ha **un solo** adapter, `claude-code`. La distribuzione multi-assistente (FEAT-009)
ha già **depositato l'hook `SessionEnd` su ospiti Copilot**, ma quell'hook è **inerte**: scatta a fine
sessione e invoca `sertor-rag memory archive`, che seleziona l'unico adapter `claude-code` — incapace di
leggere i transcript di Copilot. **Su Copilot la memoria non cattura nulla: il tubo è posato, manca la
sorgente.** Questa feature aggiunge l'**adapter di cattura per GitHub Copilot CLI** dietro la porta
esistente. Una volta presente, l'intero tier a valle diventa operativo su Copilot **senza modifiche**.

---

> **Allineamento alla missione (gate Constitution).** La memoria conversazioni serve la stella polare —
> **qualità del contesto reso all'agente nel tempo**: ritrovare cosa è già stato deciso/discusso. Oggi
> quel contesto esiste **solo** per chi guida il progetto con Claude. Questa feature lo estende al
> **secondo assistente ospite** (Copilot CLI) **senza** duplicare nulla: riusa per intero archivio,
> ricerca e distillazione. È host-agnosticità (Principio X) resa reale per la memoria — la stessa
> capacità, portabile su più ambienti, senza lock-in sull'assistente.

> **Natura del cambiamento: ADDITIVO, a leva spenta = nessun costo.** Con la memoria off (default,
> `SERTOR_MEMORY=false`) non si cattura/legge nulla: nessun file Copilot aperto, nessun adapter
> costruito (gate `memory_enabled` esistente → factory `None`). L'adapter `claude-code` **resta il
> default**; il percorso Copilot si attiva solo selezionando esplicitamente l'adapter Copilot. Nessun
> componente del tier a valle (archivio, full-text, semantica, distillazione) viene toccato.

> **Decisioni di scope GIÀ fissate (ricognizione empirica su sessioni Copilot reali, Copilot CLI 1.0.63,
> 2026-06-22; non si riaprono).** Sono confini di scope, **non** il *come* di dettaglio (quello è plan).
> - **Sorgente = `~/.copilot/session-state/<uuid>/events.jsonl`.** Stream JSONL di eventi di sessione,
>   **unica fonte necessaria**: niente `session.db`, niente `workspace.yaml`, niente cloud. (Chiude
>   DA-CM-3: `events.jsonl` è la fonte di verità.)
> - **Solo dialogo nei turni.** Evento `user.message` → ruolo user (testo = `data.content`);
>   `assistant.message` → ruolo assistant (testo = `data.content`). **Tutto il resto si scarta**
>   (`system.message`, `tool.*`, `hook.*`, `session.*`, `permission.*`, `subagent.*`); i `toolRequests`
>   dentro `assistant.message` **non** sono turni. (Chiude DA-CM-1 e REQ-008.)
> - **Associazione progetto = filtro per cwd/gitRoot dell'evento `session.start`.** L'evento
>   `session.start` porta `data.context.cwd` e `data.context.gitRoot` (path assoluti puliti, JSON
>   stdlib): una sessione appartiene al progetto corrente se cwd/gitRoot combaciano. (Le cartelle sono
>   UUID, non path-encoded.) `vscode.metadata.json.origin` vale `"other"` → **inutile, scartato**.
>   (Chiude DA-CM-2.)
> - **Nome valore adapter = `copilot-cli`** (coerente con `--assistant copilot-cli` dell'installer).
>   (Chiude DA-CM-5.)
> - **Sede legacy `~/.copilot/history-session-state/` IGNORATA** (Could, fuori MVP). (Chiude DA-CM-4.)
> - **Cloud-sync di Copilot = sola documentazione** (REQ-015): Sertor legge solo il locale, **nessun
>   avviso a runtime**. (Chiude DA-CM-6.)

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Porta di cattura
> `TranscriptCaptureAdapter` (8ª porta, `domain/ports.py`); adapter Claude di riferimento
> `src/sertor_core/adapters/capture/claude_code.py` (`list_sessions`/`read_session`, best-effort
> non-fatale, stdlib-only, `kind="claude-code"`); selezione in
> `src/sertor_core/composition.py::build_capture_adapter` (oggi `_VALID_MEMORY_ADAPTERS = ("claude-code",)`,
> valore ignoto → `ConfigError` azionabile); manopole in `config/settings.py`
> (`memory_adapter` da `SERTOR_MEMORY_ADAPTER`, default `claude-code`; `claude_projects_dir` come
> override di sorgente). Entità prodotta invariata: `SessionRef`/`TranscriptContent`/`TranscriptTurn`
> (`domain/memory.py`). I riferimenti a file ancorano i requisiti, **non** prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Memoria su Copilot, alla pari di Claude (P1, Must)
L'owner guida un progetto con GitHub Copilot CLI e ha attivato la memoria di Sertor selezionando
l'adapter Copilot. Dopo alcune sessioni, le conversazioni Copilot sono **recuperabili** dall'archivio
locale esattamente come quelle catturate da Claude — full-text, per significato e disponibili alla
distillazione, senza alcuna differenza di funzionalità.

**Independent Test**: con la memoria attiva e l'adapter Copilot selezionato, dopo N sessioni Copilot del
progetto, il numero di sessioni Copilot archiviate è uguale al numero di sessioni catturate; ciascuna è
interrogabile via full-text e (se opt-in) semantica.

**Acceptance**:
1. **Given** la memoria attiva e l'adapter Copilot selezionato, **When** archivio dopo N sessioni
   Copilot del progetto, **Then** le N conversazioni sono presenti e recuperabili dall'archivio locale.
2. **Given** una conversazione catturata da Copilot, **When** la interrogo via full-text e via semantica
   (opt-in), **Then** è restituita alla pari di una catturata da Claude, senza modifiche a
   archivio/ricerca/distillazione.
3. **Given** sessioni catturate da Claude e da Copilot nello stesso archivio, **When** interrogo,
   **Then** entrambe le provenienze sono trattate uniformemente (nessuna è privilegiata o esclusa).

### User Story 2 — Selezione dell'adapter Copilot (P1, Must)
L'utente sceglie quale assistente catturare tramite la manopola di selezione adapter. Il valore
`copilot-cli` attiva la cattura Copilot, accanto a `claude-code`; un valore non riconosciuto produce un
errore di configurazione azionabile che nomina i valori ammessi.

**Independent Test**: con `SERTOR_MEMORY_ADAPTER=copilot-cli` la cattura usa la sorgente Copilot; con un
valore ignoto l'avvio fallisce con un errore che elenca i valori ammessi (`claude-code`, `copilot-cli`).

**Acceptance**:
1. **Given** la manopola di selezione impostata su `copilot-cli`, **When** eseguo la cattura, **Then** la
   sorgente è il session-store locale di Copilot, alla pari della selezione `claude-code`.
2. **Given** un valore di adapter non riconosciuto, **When** avvio la cattura, **Then** ricevo un errore
   di configurazione azionabile che **nomina** i valori ammessi (comportamento odierno, preservato).
3. **Given** nessuna selezione esplicita, **When** eseguo la cattura, **Then** l'adapter resta il default
   `claude-code` (non-regressione: gli ospiti Claude esistenti non cambiano comportamento).

### User Story 3 — Estrazione dei turni: solo dialogo, best-effort (P1, Must)
L'adapter legge lo stream di eventi di una sessione Copilot e ne ricava i **turni di conversazione**
ordinati (prompt utente e risposte assistente). Gli eventi non-dialogo (chiamate/risultati di tool, diff
di file, eventi di sistema/hook/permessi) **non** diventano turni. Una riga o un evento illeggibile è
saltato con un warning, mai fatale.

**Independent Test**: data una sessione di fixture con un mix di eventi (user/assistant + tool/system/
hook/permission), i turni estratti contengono **solo** il dialogo user/assistant in ordine; una riga
malformata in mezzo è saltata e il resto è comunque estratto.

**Acceptance**:
1. **Given** una sessione con eventi `user.message`/`assistant.message` intervallati da eventi
   non-dialogo, **When** la leggo, **Then** ottengo turni ordinati per i soli messaggi user/assistant,
   con il ruolo corretto, e gli eventi non-dialogo sono ignorati.
2. **Given** una sessione in cui un `assistant.message` contiene richieste di tool, **When** la leggo,
   **Then** quelle richieste **non** sono trattate come turni di conversazione.
3. **Given** una riga/evento strutturalmente non valido nello stream, **When** lo parso, **Then** è
   saltato, è loggato un warning, e il parsing del resto prosegue senza far fallire la cattura.

### User Story 4 — Associazione sessione↔progetto (cartelle UUID) (P1, Must)
Le cartelle di sessione Copilot sono UUID opachi, non path di progetto. L'adapter associa ogni sessione
al progetto leggendo la metadata **interna** della sessione (cwd/gitRoot registrati all'avvio della
sessione) e cattura per il progetto corrente solo le sessioni che vi corrispondono — senza mai
attribuirne una al progetto sbagliato in silenzio.

**Independent Test**: date più sessioni Copilot di progetti diversi nel session-store, la cattura per il
progetto corrente raccoglie solo le sessioni la cui metadata interna corrisponde a quel progetto; le
altre sono escluse; nessuna è misattribuita.

**Acceptance**:
1. **Given** sessioni di progetti diversi nel session-store, **When** catturo per il progetto corrente,
   **Then** sono incluse solo le sessioni la cui cwd/gitRoot interna corrisponde al progetto corrente.
2. **Given** una sessione la cui associazione al progetto non è determinabile, **When** la elaboro,
   **Then** non è attribuita silenziosamente a un progetto sbagliato (è esclusa, oppure marcata in modo
   esplicito; politica precisa = design).
3. **Given** il nome cartella UUID, **When** ricavo l'associazione, **Then** la derivo dalla metadata
   interna della sessione, **non** dal nome della cartella.

### User Story 5 — Privacy, local-first, sorgente assente (P1, Must)
Con la memoria disattivata non si cattura né si legge nulla. Attiva, l'adapter legge **solo** i file
locali di Copilot e il contenuto passa per lo scrub esistente prima dell'archiviazione; Sertor non
contatta il cloud-sync di Copilot né richiede rete. Se il session-store Copilot è assente (Copilot non
installato, nessuna sessione), la cattura restituisce un risultato vuoto con warning, non un errore.

**Independent Test**: con la memoria off non viene aperto alcun file Copilot; con la memoria on e un
provider locale, la cattura non genera traffico di rete e il testo archiviato è scrubbed; con il
session-store assente, la cattura torna vuota + warning (non eccezione).

**Acceptance**:
1. **Given** la memoria off, **When** scatta l'hook/comando di cattura, **Then** nessun file Copilot è
   letto e nulla è persistito.
2. **Given** la memoria on e la cattura Copilot, **When** archivio, **Then** l'adapter legge solo i file
   locali, il contenuto passa per lo scrub esistente, e non c'è traffico di rete verso il cloud-sync.
3. **Given** il session-store Copilot assente (Copilot non installato o nessuna sessione), **When**
   catturo, **Then** ottengo un risultato vuoto con warning, non un errore.

### User Story 6 — Idempotenza e robustezza al cambio formato (P2, Should)
Archiviare due volte la stessa sessione Copilot non crea duplicati (idempotenza ereditata dal tier). Se
un aggiornamento di Copilot CLI cambia il formato degli eventi in modo inatteso, l'adapter degrada a una
cattura best-effort/vuota con warning — mai un crash — e la limitazione è documentata.

**Independent Test**: catturare due volte la stessa sessione non aumenta i record d'archivio; una
sessione in un formato inatteso produce zero/parziali turni con warning, mai un'eccezione non gestita.

**Acceptance**:
1. **Given** una sessione Copilot già archiviata, **When** la stessa sessione viene ricatturata, **Then**
   non si creano duplicati nell'archivio (idempotenza, ereditata).
2. **Given** un evento/sessione in un formato non atteso dall'adapter, **When** lo elaboro, **Then**
   degrado a cattura best-effort/vuota con warning, senza crash.
3. **Given** la natura non contrattuale del formato `events.jsonl`, **When** documento la feature,
   **Then** la documentazione dichiara la versione di Copilot CLI verificata e che aggiornamenti possono
   richiedere adeguamenti.

### User Story 7 — Hook reso vivo su Copilot (P2, Should)
Su un ospite Copilot con la memoria configurata e l'adapter Copilot selezionato, l'hook `SessionEnd` già
depositato da FEAT-009 cattura effettivamente le sessioni — smette di essere inerte. Nessun nuovo
artefatto host viene introdotto da questa feature: l'hook esistente diventa funzionante perché ora ha una
sorgente da leggere.

**Independent Test**: su un ambiente Copilot con la memoria attiva e l'adapter Copilot, l'invocazione
dell'hook `SessionEnd` esistente produce sessioni archiviate (laddove prima produceva zero).

**Acceptance**:
1. **Given** un ospite Copilot con memoria attiva e adapter Copilot, **When** scatta l'hook `SessionEnd`
   già depositato, **Then** le sessioni Copilot sono catturate e archiviate (l'hook non è più inerte).
2. **Given** la memoria off su un ospite Copilot, **When** scatta l'hook, **Then** è un no-op (nessuna
   cattura), come per Claude.

## Edge Cases
- **Memoria off + adapter Copilot selezionato**: nessuna cattura/lettura (gate `memory_enabled` →
  factory `None`); il valore adapter è inerte finché la memoria non è attiva.
- **Valore adapter non riconosciuto**: errore di configurazione azionabile che nomina i valori ammessi
  (`claude-code`, `copilot-cli`) — comportamento odierno preservato.
- **Session-store Copilot assente** (Copilot non installato / nessuna sessione): risultato vuoto +
  warning, mai errore.
- **Sessione di un altro progetto** nel session-store condiviso: esclusa dal filtro cwd/gitRoot, non
  misattribuita.
- **Associazione al progetto indeterminabile** (manca `session.start` o cwd/gitRoot): non misattribuita
  in silenzio; esclusa o marcata esplicitamente (politica = design).
- **Riga/evento JSONL malformato**: saltato con warning, parsing del resto prosegue.
- **Evento non-dialogo** (`tool.*`/`system.*`/`hook.*`/`session.*`/`permission.*`/`subagent.*`): mai un
  turno; `toolRequests` dentro `assistant.message` non sono turni.
- **Cambio di formato `events.jsonl`** dopo un aggiornamento di Copilot CLI: degrado best-effort/vuoto
  con warning, mai crash; limitazione documentata.
- **Cloud-sync di Copilot attivo**: il grezzo può già essere sul cloud GitHub per scelta di Copilot;
  Sertor legge solo il locale e non interagisce col sync; il fatto è dichiarato in documentazione.
- **Ricattura della stessa sessione**: nessun duplicato (idempotenza ereditata dal tier).
- **Sede legacy `history-session-state/`**: ignorata (Could, fuori MVP).

## Requirements *(mandatory)*

### Requisiti funzionali

**Selezione dell'adapter**
- **FR-001 (selezione Copilot).** Quando la manopola di selezione adapter indica Copilot CLI, il sistema
  usa l'adapter Copilot come sorgente di cattura, alla pari della selezione `claude-code`. *(REQ-001)*
- **FR-002 (errore azionabile).** Se il valore di adapter configurato non è riconosciuto, il sistema
  solleva un errore di configurazione azionabile che nomina i valori ammessi (comportamento odierno,
  preservato). *(REQ-002)*
- **FR-003 (default invariato).** In assenza di selezione esplicita, l'adapter resta `claude-code`
  (non-regressione per gli ospiti Claude esistenti). *(deriva da REQ-001/016, vincolo di additività)*

**Discovery delle sessioni**
- **FR-004 (discovery dal session-store locale).** L'adapter Copilot scopre le sessioni catturate dal
  session-store locale per-sessione di Copilot CLI (le directory di sessione sotto la location
  session-state dell'utente). *(REQ-003)*
- **FR-005 (override del percorso sorgente).** Quando l'utente sovrascrive via configurazione la location
  del session-state di Copilot, l'adapter legge dal percorso sovrascritto (host-agnostico e testabile,
  in parità con l'override del projects-dir di Claude). *(REQ-004)*
- **FR-006 (identità stabile di sessione).** L'adapter identifica ogni sessione Copilot con un
  identificatore di sessione stabile (il suo id di sessione), così l'archiviazione è idempotente.
  *(REQ-005)*

**Estrazione dei turni (best-effort, non-fatale)**
- **FR-007 (turni ordinati con ruolo).** L'adapter legge lo stream di eventi di una sessione e produce
  turni di conversazione ordinati (prompt utente e risposte assistente) con i rispettivi ruoli, adatti
  all'archivio. *(REQ-006)*
- **FR-008 (best-effort non-fatale).** Se un evento o una riga è illeggibile o strutturalmente non
  valido, l'adapter lo salta, logga un warning e prosegue il parsing del resto, senza mai far fallire il
  run di cattura (parità con l'adapter Claude). *(REQ-007)*
- **FR-009 (solo dialogo).** L'adapter include nei turni catturati il **solo** dialogo user/assistant e
  **non** tratta i payload di eventi non-dialogo (chiamate/risultati di tool, diff di file, eventi di
  sistema/hook/permessi/subagent) come turni di conversazione; le richieste di tool dentro un messaggio
  assistente non sono turni. *(REQ-008)*

**Associazione sessione↔progetto**
- **FR-010 (associazione dalla metadata interna).** L'adapter associa ogni sessione catturata a un
  progetto, derivandolo dalla metadata registrata **dentro** la sessione (il nome della directory
  Copilot è un id opaco, non un path di progetto). *(REQ-009)*
- **FR-011 (nessuna misattribuzione silenziosa).** Se l'associazione al progetto di una sessione non è
  determinabile, l'adapter non la attribuisce silenziosamente a un progetto sbagliato: o la salta, o la
  archivia sotto un marcatore esplicito di progetto-sconosciuto (politica precisa = design). *(REQ-010)*

**Idempotenza e scrub (ereditati)**
- **FR-012 (idempotenza ereditata).** Quando la stessa sessione Copilot è catturata più di una volta, il
  sistema non la duplica nell'archivio (archiviazione idempotente, ereditata dal tier). *(REQ-011)*
- **FR-013 (scrub ereditato, non bypassabile).** Il contenuto catturato da Copilot passa per lo scrub dei
  segreti esistente prima dell'archiviazione; l'adapter Copilot non lo aggira né lo indebolisce.
  *(REQ-012)*

**Privacy e local-first**
- **FR-014 (privacy-by-default).** Se la cattura conversazioni non è attiva, l'adapter Copilot non cattura
  né persiste nulla. *(REQ-013)*
- **FR-015 (solo locale, no rete).** L'adapter legge solo i file locali di sessione di Copilot; non
  contatta il cloud session-sync di GitHub né richiede accesso di rete. *(REQ-014)*
- **FR-016 (trasparenza del cloud-sync).** La documentazione utente rende esplicito che Copilot CLI può
  sincronizzare di default i dati di sessione sul cloud GitHub — comportamento a monte e indipendente
  dall'archivio locale di Sertor, fuori dal controllo di Sertor; nessun avviso a runtime. *(REQ-015)*

**Host-specificità confinata**
- **FR-017 (host-specificità nell'adapter).** Tutta la conoscenza host-specifica di Copilot (percorsi,
  formato eventi, associazione al progetto) vive **solo** nell'adapter Copilot dietro la porta di cattura
  esistente; archivio, full-text, semantica e distillazione non richiedono alcuna modifica (Principio X).
  *(REQ-016)*

**Riuso del tier**
- **FR-018 (parità di tier).** Le sessioni catturate da Copilot sono archiviate, interrogabili full-text
  (FEAT-002), interrogabili per significato quando opt-in (FEAT-004) e disponibili alla distillazione
  (FEAT-003) alla pari delle sessioni catturate da Claude, senza modifiche a quei componenti. *(REQ-017)*

**Degradazione non-fatale della sorgente**
- **FR-019 (sorgente assente).** Se il session-store Copilot è assente (Copilot non installato, o nessuna
  sessione), la cattura produce un risultato vuoto con warning, non un errore. *(REQ-018)*
- **FR-020 (formato inatteso).** Se il formato eventi di una sessione non è quello atteso dall'adapter
  (es. dopo un aggiornamento di Copilot CLI che lo cambia), l'adapter degrada a una cattura
  best-effort/vuota con warning, mai un crash, e la limitazione è documentata. *(REQ-019)*

**Attivazione dell'hook distribuito**
- **FR-021 (hook reso vivo).** Mentre la cattura della memoria è attiva e l'adapter Copilot è selezionato
  su un ospite Copilot, l'hook `SessionEnd` già depositato (FEAT-009) cattura le sessioni Copilot — cessa
  di essere inerte. *(REQ-020)*

### Requisiti non funzionali
- **RNF-1 (resilienza al formato):** il parsing è best-effort; nessuna eccezione non gestita su formato
  inatteso/parziale; il guasto è warning, mai crash (parità con l'adapter Claude). *(NFR-001)*
- **RNF-2 (local-first / offline):** la cattura non produce traffico di rete; le sue dipendenze sono
  soddisfatte interamente in locale. *(NFR-002)*
- **RNF-3 (additività a leva spenta):** con la memoria off (default), comportamento e costo sono identici
  a oggi; nessun file Copilot letto, nessun adapter Copilot costruito (gate `memory_enabled`). *(NFR-003)*
- **RNF-4 (testabilità offline):** l'adapter è testabile con una directory di sessione Copilot di fixture
  (`events.jsonl` + metadata di esempio), senza Copilot CLI installato né rete — pattern dei test
  dell'adapter Claude. *(NFR-004)*
- **RNF-5 (tier invariato):** nessuna modifica ad archivio/ricerca/distillazione; verificabile (le loro
  suite restano verdi senza tocchi). *(NFR-005)*
- **RNF-6 (formato non contrattuale dichiarato):** il formato `events.jsonl` è un dettaglio **interno** di
  Copilot CLI (non un contratto pubblico stabile); la documentazione dichiara la/le versione/i di Copilot
  CLI verificate e che aggiornamenti possono richiedere adeguamenti (mitigato da RNF-1). *(NFR-006)*
- **RNF-7 (stdlib-only):** l'adapter, come quello Claude, non introduce nuove dipendenze di terze parti
  (parsing JSONL via stdlib). *(deriva dal vincolo «stdlib-only come l'adapter Claude»)*
- **RNF-8 (accesso via vehicle):** la cattura è esercitata via CLI/hook (`sertor-rag memory archive`),
  non importando il core (eccezione: i test) — Principio XI. *(vincolo ereditato dall'epica)*

### Key Entities
- **Adapter di cattura Copilot CLI** — il nuovo componente host-specifico dietro la porta
  `TranscriptCaptureAdapter` (`kind="copilot-cli"`); l'unico che conosce percorsi, formato eventi e
  associazione al progetto di Copilot.
- **Sorgente di sessione Copilot** — la directory di sessione locale (`<session-uuid>/`) sotto la
  location session-state dell'utente, contenente lo stream di eventi `events.jsonl`; percorso
  sovrascrivibile via configurazione.
- **Evento di sessione** — una riga dello stream JSONL; solo gli eventi `user.message`/`assistant.message`
  diventano turni; gli altri sono scartati.
- **Turno di conversazione** — l'unità prodotta per l'archivio (ruolo user/assistant + testo + indice +
  timestamp), identica all'entità del tier (`TranscriptTurn`); il transcript della sessione è
  `TranscriptContent` con `SessionRef`.
- **Selettore di adapter** — la manopola che sceglie la sorgente di cattura (`claude-code` default,
  `copilot-cli`); valore ignoto → errore azionabile.
- **Associazione progetto** — derivata dalla metadata interna della sessione (cwd/gitRoot dell'evento di
  avvio), non dal nome cartella UUID.

## Success Criteria *(mandatory)*
- **SC-001 (cattura su Copilot):** con la memoria attiva e l'adapter Copilot, dopo N sessioni Copilot del
  progetto il numero di sessioni archiviate è uguale a N (parità con Claude). *(FR-001/004/007, US1; CM-CS-1)*
- **SC-002 (parità di tier):** una conversazione catturata da Copilot è interrogabile full-text **e**
  semantica e disponibile alla distillazione alla pari di una catturata da Claude, **senza** modifiche ad
  archivio/ricerca/distillazione. *(FR-017/018, RNF-5, US1; CM-CS-2)*
- **SC-003 (host-specificità confinata):** l'unico componente che conosce Copilot è il nuovo adapter
  dietro la porta; il resto del nucleo resta invariato (le suite del tier restano verdi senza tocchi).
  *(FR-017, RNF-5, US1; CM-CS-3)*
- **SC-004 (privacy & local-first):** con la cattura off non viene catturato nulla; attiva con provider
  locale, la cattura non genera traffico di rete (monitor a zero), legge solo file locali e il contenuto
  passa per lo scrub esistente. *(FR-013/014/015, RNF-2, US5; CM-CS-4)*
- **SC-005 (idempotenza):** archiviare due volte la stessa sessione Copilot non crea duplicati
  (#record invariato). *(FR-012, US6; CM-CS-5)*
- **SC-006 (robustezza non-fatale):** sorgente assente → vuoto+warning; evento malformato → saltato+warning;
  formato inatteso → cattura best-effort/vuota+warning; **nessun** errore fatale. *(FR-008/019/020, RNF-1,
  US3/US5/US6; CM-CS-6)*
- **SC-007 (hook reso vivo):** su un ospite Copilot con memoria configurata e adapter Copilot, l'hook
  `SessionEnd` già depositato cattura effettivamente le sessioni (zero → N). *(FR-021, US7; CM-CS-7)*
- **SC-008 (solo dialogo):** i turni catturati contengono solo messaggi user/assistant; eventi
  tool/system/hook/permission/subagent e i `toolRequests` non compaiono come turni. *(FR-009, US3)*
- **SC-009 (associazione corretta):** date sessioni di progetti diversi nel session-store, la cattura per
  il progetto corrente raccoglie solo quelle la cui metadata interna corrisponde; nessuna misattribuzione
  silenziosa. *(FR-010/011, US4)*
- **SC-010 (default invariato):** senza selezione esplicita l'adapter resta `claude-code`; gli ospiti
  Claude esistenti non cambiano comportamento. *(FR-003, US2)*
- **SC-011 (additività a leva spenta):** con la memoria off, comportamento e costo identici a oggi;
  `sertor-core` non regredisce; suite verde, lint pulito; nessuna nuova dipendenza. *(RNF-3/7)*
- **SC-012 (testabilità offline):** l'adapter è coperto da test con una sessione Copilot di fixture, senza
  Copilot CLI installato né rete. *(RNF-4, US3)*

## Assumptions
- **A-001 — Sorgente locale Copilot accertata:** sessioni in `~/.copilot/session-state/<uuid>/` con
  `events.jsonl` (stream JSONL di eventi) come transcript; verificato empiricamente su Copilot CLI 1.0.63
  (2026-06-22). È l'unica fonte necessaria: `session.db`, `workspace.yaml`, cloud non sono letti.
- **A-002 — Mapping turni accertato:** `user.message` → ruolo user (testo `data.content`),
  `assistant.message` → ruolo assistant (testo `data.content`); ogni altro tipo di evento è scartato; i
  `toolRequests` nel messaggio assistente non sono turni.
- **A-003 — Associazione al progetto via cwd/gitRoot:** l'evento `session.start` porta
  `data.context.cwd` e `data.context.gitRoot`; una sessione appartiene al progetto corrente se questi
  combaciano con la cwd del progetto. `vscode.metadata.json.origin = "other"` è inutile e scartato.
- **A-004 — Nome valore adapter:** `copilot-cli`, coerente col naming `--assistant copilot-cli`
  dell'installer.
- **A-005 — Sede legacy ignorata:** `~/.copilot/history-session-state/` non è letta (Could, fuori MVP).
- **A-006 — Cloud-sync solo documentato:** Copilot può sincronizzare le sessioni sul cloud GitHub di
  default; Sertor legge solo il locale e non interagisce col sync; nessun avviso a runtime (sola
  documentazione).
- **A-007 — Porta e tier esistenti:** si riusa `TranscriptCaptureAdapter` (8ª porta) e tutto il tier a
  valle senza modifiche; l'entità prodotta è la stessa (`TranscriptContent`/`TranscriptTurn`/`SessionRef`).
- **A-008 — Gate privacy come gli altri `build_*`:** la factory dell'adapter è gated su `memory_enabled`;
  con la memoria off ritorna `None` (no-op), come oggi per `claude-code`.
- **A-009 — FEAT-009 ha già depositato l'hook:** l'hook `SessionEnd` e le manopole memoria sono già su
  ospiti Copilot; questa feature li rende effettivi, non li ridistribuisce.
- **A-010 — Testo già scrubbed dal tier:** lo scrub dei segreti è applicato dal percorso d'archiviazione
  esistente (FEAT-001); questa feature non aggiunge né bypassa scrub.

### Fuori ambito (dichiarato)
- **Cattura e archiviazione** del tier (FEAT-001 — dipendenza a monte, assunta come fornita).
- **Ricerca full-text / semantica / distillazione** (FEAT-002/004/003 — alimentate, non modificate).
- **Modifiche al tier a valle**: questa feature lo **alimenta** con una nuova sorgente; non lo tocca.
- **Distribuzione del valore `SERTOR_MEMORY_ADAPTER=copilot-cli` nel template `.env` dell'installer su
  host Copilot** (oggi default `claude-code`): **debito di completamento**, cross-ref **FEAT-009** (owner
  di `sertor install`), già nel backlog d'epica — **non** risolto qui. La feature non è *done* finché un
  ospite Copilot non riceve il valore adapter per il percorso di installazione.
- **Altri assistenti** (Codex, ecc.): fuori da questa feature (estendibile col medesimo pattern).
- **Sede legacy `history-session-state/`** (Could) e **fonte alternativa `session.db`**: non letti.
- **Interazione col cloud-sync di Copilot**: Sertor legge solo il locale; il sync è di Copilot.
- **Il *come* di dettaglio** (schema esatto evento→turno e ricomposizione del testo; politica precisa per
  progetto indeterminabile; nome esatto della manopola di override del percorso): fase di **design/plan**.

> **Tracciamento dello scope.** FEAT-009 (installer) è già nel backlog d'epica
> (`requirements/memoria-conversazioni/epic.md`): il debito di **distribuzione del valore adapter** via
> template `.env` è ancorato lì, nessun rinvio reale vive solo dentro `specs/`. La gestione della sede
> legacy `history-session-state/` resta **Could** nei requisiti d'epica.

### Forche di design (per `/speckit-plan`)
- **DA-CM-1 (residuo) — Ricomposizione del testo del turno:** `data.content` è già testo completo o vi
  sono delta/streaming da ricomporre? Verificato su eventi reali in design (il principio «solo dialogo» è
  fissato in FR-009). *Design.*
- **DA-CM-2 (residuo) — Politica per progetto indeterminabile:** skip vs marcatore esplicito di
  progetto-sconosciuto quando manca `session.start`/cwd/gitRoot (FR-011). *Design.*
- **DA-CM-3 — Nome della manopola di override del percorso sorgente Copilot:** in parità con
  `claude_projects_dir`/`SERTOR_..._PROJECTS_DIR`; nome esatto = design (FR-005). *Design.*
- **DA-CM-4 — Forma del filtro cwd/gitRoot:** match esatto vs path-containment (sottocartelle del
  progetto); decide quali sessioni del progetto sono incluse. *Design.*
