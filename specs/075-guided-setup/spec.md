# Feature Specification: guided-setup — guida agentica a install → configure → verify (E12-FEAT-002)

**Feature Branch**: `075-guided-setup` · **Created**: 2026-06-23 · **Status**: Draft

<!-- Deriva da: FEAT-002 (epica usabilità E12) — requirements/usabilita/guided-setup/requirements.md -->

**Input**: FEAT-002 dell'epica `usabilita` (E12). Il primo contatto con Sertor è oggi il momento più
fragile: l'utente deve sapere quale comando lanciare (`uvx … sertor install rag` poi `sertor-rag index .`),
scegliere il provider di embeddings, riempire `.sertor/.env` **a mano**, gestire l'attesa del download
GloVe (~822 MB) e — soprattutto — capire da solo se *«ha funzionato»*. Gli errori si auto-spiegano, ma
**uno alla volta** e **dopo** averci sbattuto; nessun percorso li anticipa né conduce dall'inizio alla
fine. Questa feature consegna quel percorso: **`guided-setup`**, la prima feature **agentica** dell'epica
— una **skill** (più uno **stub dell'agente *concierge***) che l'**agente frontier dell'ospite** esegue
per condurre l'utente da «repo non configurato» a «**RAG verificato**» (un `sertor-rag doctor` tutto
verde), conversando, scegliendo il provider dal contesto e **orchestrando solo i vehicle deterministici**
(`sertor install`, `sertor configure --set`, `sertor-rag doctor`/`index`). Coerente col confine **D↔N**:
l'intelligenza vive nell'agente ospite, **il core non chiama mai un LLM**; la skill non reimplementa i
comandi, li **usa**.

---

> **Allineamento alla missione (gate Constitution).** L'usabilità è *periferica* al differenziatore di
> Sertor (qualità del retrieval reso all'agente), ma **serve l'adozione e la portabilità**: *un agente che
> sa installare, configurare e verificare Sertor da solo su un ospite qualunque È host-agnosticità reale*
> (Principio X). `guided-setup` è il primo strato agentico che, sopra il substrato deterministico
> `sertor-rag doctor` (FEAT-001, già su `master`), realizza CS-1 dell'epica: «dal nulla a verificato»
> senza conoscere gli internals. Vincolo non negoziabile (**confine D↔N**): la skill è eseguita
> dall'agente dell'ospite, **il core non chiama mai un LLM**; l'intelligenza è nelle istruzioni della
> skill, non in una chiamata programmatica.

> **Natura del cambiamento: ADDITIVO + scope di distribuzione.** La feature **non** è codice di core: non
> aggiunge motori, porte o comandi runtime. Introduce **asset di istruzioni** (una skill `guided-setup` +
> uno **stub** dell'agente *concierge*), il **wiring di distribuzione dual-target** che li deposita via
> `sertor install`, e una **guardia di parità**. Niente percorso runtime del core cambia; a feature
> installata, il comportamento dei comandi deterministici è identico a oggi (la skill li orchestra, non li
> altera). È il corollario **«feature completa»**: non è *done* finché un ospite la riceve via
> `sertor install` su entrambi gli assistenti supportati.

> **Anticipa FEAT-009 (stub dichiarato).** Lo scope è deliberatamente esteso per includere un **agente
> *concierge* minimale** (un sottile dispatcher) accanto alla skill standalone — decisione presa con
> l'utente (DA-G1). Questo **anticipa FEAT-009** (l'agente *concierge* pieno dell'epica): qui il concierge
> è uno **stub** con **un solo ramo** (instrada verso `guided-setup`). I suoi compiti pieni — dispatch
> verso config-recommender (FEAT-004) e search-diagnose (FEAT-007), check proattivi all'avvio — **restano
> FEAT-009**. FEAT-009 va perciò tracciata come **parzialmente avviata (stub)**, non duplicata né
> consegnata.

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** I vehicle che la skill orchestra
> esistono già e sono accertati: `sertor install rag` (installer `sertor`, deposita asset + scaffolda
> `.sertor/.env`); `sertor configure`/`configure --set` (wizard CI-safe, catena flag→env→prompt, segreti
> via `getpass`, mascheramento in `mask_secret`); `sertor-rag doctor` (FEAT-001, su `master`: quadro
> quattro aree env/provider/indice/MCP con esito pass/warn/fail, `--json` a schema stabile, exit-code
> gate, offline-safe); `sertor-rag index .` (primo index, può innescare il download GloVe ~822 MB con
> avviso una-tantum esistente). Il **pattern di distribuzione dual-target** è collaudato (`wiki-author`,
> `eval-suite-author`, `eval-feedback`): corpo host-agnostico byte-identico con **riferimento-per-nome**
> agli asset, contenitore tradotto nativamente (Claude `.claude/skills/` ↔ Copilot `.github/skills/`;
> agente `.claude/agents/` ↔ `.github/agents/`), guardia di parità offline. I riferimenti **ancorano** i
> requisiti, non prescrivono il *come* (forma esatta del body della skill, dei prompt, dell'euristica =
> design).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Dal nulla a «RAG verificato» (P1, Must)
Un utente nuovo, su un repo non configurato, chiede all'agente dell'ospite di «mettere su Sertor».
L'agente esegue la skill `guided-setup`: rileva lo stato corrente (sola lettura), propone i passi
**install → configure → verify** conversando, sceglie il provider dal contesto motivandolo, riempie
`.env` per via sicura, e al termine lancia `sertor-rag doctor` riportando l'esito **verificato**.
L'utente arriva a «tutto verde» senza conoscere i nomi dei comandi né dei knob.

**Independent Test**: a partire da un repo non configurato, seguendo le sole istruzioni della skill,
l'agente conduce install → configure → verify usando esclusivamente i vehicle deterministici e termina
mostrando l'esito di `doctor`; la skill non reimplementa alcun comando.

**Acceptance**:
1. **Given** un repo senza configurazione Sertor, **When** l'utente chiede di configurare Sertor e
   l'agente esegue `guided-setup`, **Then** la skill conduce install → configure → verify orchestrando
   solo i vehicle deterministici (`sertor install`, `sertor configure --set`, `sertor-rag doctor`).
2. **Given** la skill in esecuzione, **When** completa i passi, **Then** lancia `sertor-rag doctor` e
   riporta l'esito verificato, senza dichiarare successo se `doctor` non è verde.
3. **Given** un utente che non conosce gli internals, **When** segue la guida, **Then** non gli è
   richiesto di conoscere i nomi dei comandi o dei knob per arrivare a «verificato».

### User Story 2 — Scelta del provider dal contesto, con conferma (P2, Should)
La skill osserva pochi segnali (credenziali cloud presenti? host airgapped/offline? serve semantica NL
sui documenti?) e **consiglia** un provider — locale (`glove`/`hash`) o cloud — **motivando** il
trade-off. La decisione finale resta all'utente: la skill propone, l'utente sceglie.

**Independent Test**: con credenziali cloud assenti (o host airgapped) la skill raccomanda un provider
locale spiegando il perché; con credenziali cloud presenti propone l'opzione cloud con la sua
motivazione; in entrambi i casi la scelta è confermata dall'utente, non imposta.

**Acceptance**:
1. **Given** assenza di credenziali cloud o host airgapped, **When** la skill consiglia il provider,
   **Then** raccomanda un provider locale (`glove`/`hash`) e spiega il trade-off, lasciando la scelta
   all'utente.
2. **Given** credenziali cloud presenti ed esigenza di semantica NL, **When** la skill consiglia,
   **Then** può proporre il provider cloud con motivazione, sempre come proposta da confermare.
3. **Given** qualunque raccomandazione, **When** è presentata, **Then** la decisione finale spetta
   all'utente; la skill non seleziona un provider senza conferma.

### User Story 3 — Segreti inseriti per via sicura, mai a schermo (P1, Must)
Quando serve un segreto di configurazione (es. una chiave API cloud), la skill lo fa fornire **solo**
attraverso i percorsi sicuri del wizard (`sertor configure --set` / prompt `getpass`), e **non stampa
mai** il valore del segreto — né a schermo né nei log della conversazione.

**Independent Test**: in un flusso che richiede un segreto, il valore è fornito via il percorso sicuro
del wizard e non compare mai nell'output della skill; la verifica vale per ogni segreto del flusso.

**Acceptance**:
1. **Given** un segreto necessario, **When** la skill lo raccoglie, **Then** lo fa via
   `sertor configure --set`/prompt sicuro e non stampa mai il valore.
2. **Given** un flusso completato, **When** se ne ispeziona l'output, **Then** nessun valore di segreto
   vi compare (mascherato/assente).
3. **Given** un segreto già presente in `.env`, **When** la skill verifica la config, **Then** non lo
   ri-richiede né lo espone.

### User Story 4 — Attesa del download GloVe annunciata (P2, Should)
Quando l'utente sceglie il provider `glove` e il modello non è in cache, la skill **annuncia** il
download una-tantum (~822 MB) prima di innescare il primo `index`, così l'attesa è attesa e non un
blocco silenzioso. Si appoggia al progress di FEAT-003 quando disponibile; finché non c'è, si limita
all'annuncio.

**Independent Test**: con `glove` scelto e cache assente, la skill informa del download una-tantum prima
del primo `index`; con cache presente non annuncia alcun download.

**Acceptance**:
1. **Given** `glove` scelto e modello non in cache, **When** la skill sta per innescare il primo
   `index`, **Then** informa l'utente del download una-tantum prima di procedere.
2. **Given** `glove` con modello già in cache, **When** procede all'index, **Then** non annuncia alcun
   download.
3. **Given** la disponibilità futura di un progress (FEAT-003), **When** esiste, **Then** la skill vi si
   appoggia; finché non c'è, l'annuncio testuale basta (degrado onesto).

### User Story 5 — Verify onesto e fail-loud (P1, Must)
Al termine dei passi, la skill lancia `sertor-rag doctor` e riporta lo stato **verificato**. Se `doctor`
**non** è tutto verde, la skill espone **area + rimedio** e **non dichiara** il setup riuscito (fail
loud, Principio XII): nessun «fatto» presunto.

**Independent Test**: con `doctor` tutto verde la skill dichiara il setup verificato; con `doctor` che
riporta un fail, la skill espone l'area che fallisce e il rimedio, e non dichiara successo.

**Acceptance**:
1. **Given** i passi completati, **When** la skill verifica, **Then** lancia `sertor-rag doctor` e riporta
   l'esito reale (non presunto).
2. **Given** `doctor` non tutto verde, **When** la skill riporta, **Then** espone l'area in errore e il
   rimedio e **non** dichiara il setup riuscito.
3. **Given** `doctor` tutto verde, **When** la skill riporta, **Then** dichiara il setup verificato con
   l'esito a supporto.

### User Story 6 — Consenso prima di ogni mutazione (P2, Should)
La skill esegue **liberamente** i check di **sola lettura** (lanciare `doctor`, rilevare config
esistente). Ogni passo che **muta l'ospite o scarica** (`sertor install`, `configure --set`, primo
`index`/download GloVe) viene **proposto** ed eseguito **solo dopo conferma esplicita** dell'utente.

**Independent Test**: i check di sola lettura sono eseguiti senza chiedere conferma; ogni azione che
modifica l'ospite o scarica è preceduta da una richiesta di conferma e non parte senza un «sì».

**Acceptance**:
1. **Given** un check di sola lettura (doctor, rilevazione config), **When** serve, **Then** la skill lo
   esegue senza richiedere conferma.
2. **Given** un passo che muta l'ospite o scarica (install/configure --set/index/download), **When** la
   skill sta per eseguirlo, **Then** lo propone e chiede conferma esplicita prima di procedere.
3. **Given** l'utente non conferma, **When** un passo mutante è proposto, **Then** la skill non lo esegue.

### User Story 7 — Ri-esecuzione idempotente su ospite già configurato (P2, Should)
Eseguita di nuovo su un ospite già configurato, la skill **rileva** lo stato esistente e **verifica**
(via `doctor`/rilevazione config), invece di ri-scaffoldare alla cieca. Non duplica install/config già
presenti; conduce solo i passi mancanti.

**Independent Test**: su un ospite già configurato e sano, la ri-esecuzione della skill rileva la config
esistente e riporta lo stato verificato senza ripetere install/configure; su un ospite con un passo
mancante, conduce solo quel passo.

**Acceptance**:
1. **Given** un ospite già configurato e sano, **When** la skill è ri-eseguita, **Then** rileva lo stato
   esistente, verifica via `doctor` e non ri-scaffolda alla cieca.
2. **Given** un ospite con configurazione parziale, **When** la skill è ri-eseguita, **Then** conduce
   solo i passi mancanti, non quelli già completi.
3. **Given** una ri-esecuzione, **When** procede, **Then** non duplica artefatti già presenti
   (idempotenza percepita dall'utente).

### User Story 8 — Installabile dual-target con parità (P1, Must)
La skill e lo stub del concierge sono **host-agnostici** e installabili su **entrambi** gli assistenti
supportati (Claude, Copilot) via `sertor install`, col pattern di distribuzione esistente: corpo
byte-identico con riferimento-per-nome agli asset, contenitore tradotto nativamente, coperti dalla
**guardia di parità**.

**Independent Test**: `sertor install` deposita la skill (e lo stub concierge) nei contenitori nativi di
ciascun assistente; il corpo è byte-identico tra i due target; la guardia di parità non segnala
divergenze e i riferimenti-per-nome risolvono ad asset effettivamente depositati.

**Acceptance**:
1. **Given** un ospite Claude e uno Copilot, **When** eseguo `sertor install`, **Then** la skill (e lo
   stub concierge) sono depositati nei contenitori nativi di ciascuno (`.claude/skills/`+`.claude/agents/`
   ↔ `.github/skills/`+`.github/agents/`).
2. **Given** gli asset depositati, **When** la guardia di parità li controlla, **Then** il corpo è
   byte-identico tra i target e ogni asset citato per nome dal body è effettivamente depositato
   (closure dei riferimenti).
3. **Given** un assistente non-Claude, **When** il body viene reso, **Then** non contiene leak di
   contenitore dell'altro target (no `.claude/` path/slash-command/nomi-prodotto Claude su Copilot).

### User Story 9 — Stub del concierge che instrada (P2, Should)
Un agente *concierge* **minimale** è distribuito accanto alla skill: instrada la richiesta di setup
verso `guided-setup`. È uno **stub** con un solo ramo; i compiti pieni del concierge (altri dispatch,
check proattivi) restano FEAT-009 e **non** sono in ambito qui.

**Independent Test**: invocato per un intento di setup, lo stub del concierge instrada verso la skill
`guided-setup`; non espone rami verso capacità non ancora esistenti (config-recommender/search-diagnose).

**Acceptance**:
1. **Given** una richiesta di setup, **When** lo stub del concierge la riceve, **Then** instrada verso la
   skill `guided-setup`.
2. **Given** lo stub, **When** se ne ispeziona il contenuto, **Then** ha un solo ramo (guided-setup) e
   **non** dispatcha verso capacità FEAT-004/FEAT-007 non esistenti.
3. **Given** il backlog d'epica, **When** si traccia lo stato, **Then** FEAT-009 risulta **parzialmente
   avviata (stub)**, non duplicata né completata.

## Edge Cases
- **Repo non configurato**: la skill conduce install → configure → verify dall'inizio (US1).
- **Credenziali cloud assenti / host airgapped**: la skill raccomanda provider locale (`glove`/`hash`)
  con motivazione, mai sceglie cloud al buio (US2).
- **Credenziali cloud presenti + esigenza semantica NL**: propone cloud, sempre da confermare (US2).
- **`glove` senza cache**: annuncia il download una-tantum prima del primo `index` (US4); con cache,
  nessun annuncio.
- **`doctor` rosso a fine flusso**: la skill espone area + rimedio e **non** dichiara successo (US5,
  fail-loud).
- **Segreto richiesto**: raccolto via percorso sicuro del wizard, mai stampato; se già in `.env`, non
  ri-richiesto (US3).
- **Passo mutante senza conferma**: la skill non lo esegue; chiede sempre prima di mutare/scaricare (US6).
- **Ri-esecuzione su ospite già configurato e sano**: rileva e verifica, non ri-scaffolda; conduce solo i
  passi mancanti su config parziale (US7, idempotenza).
- **Host privo di agente frontier**: il modello agentico presuppone l'agente dell'ospite; dove non c'è,
  restano i vehicle deterministici e la doc (la skill non si applica) — confine dichiarato, non un crash.
- **Distribuzione su un solo target**: la guardia di parità impedisce drift e leak di contenitore tra
  Claude e Copilot (US8).
- **Concierge oltre il singolo ramo**: lo stub non instrada verso capacità non esistenti (US9);
  l'estensione è FEAT-009.

## Requirements *(mandatory)*

### Requisiti funzionali

**Flusso guidato (orchestrazione dei vehicle)**
- **FR-001 (flusso install→configure→verify).** Quando l'utente chiede di configurare Sertor, la skill
  `guided-setup` conduce l'utente attraverso install → configure → verify usando **solo** i vehicle
  deterministici (`sertor install`, `sertor configure --set`, `sertor-rag doctor`), senza reimplementarli.
  *(REQ-001; CS-1)*
- **FR-002 (verify finale via doctor).** Quando i passi di setup sono completi, la skill lancia
  `sertor-rag doctor` e riporta lo stato **verificato**. *(REQ-005; CS-4)*
- **FR-003 (fail-loud).** Se `doctor` non è tutto verde, la skill espone l'area in errore e il rimedio e
  **non** dichiara il setup riuscito (Principio XII). *(REQ-006; CS-4)*

**Scelta del provider (euristica minima + conferma)**
- **FR-004 (raccomandazione locale dal contesto).** Dove le credenziali cloud sono assenti (o l'host è
  airgapped), la skill raccomanda un provider locale (`glove`/`hash`) e spiega il trade-off, lasciando la
  scelta all'utente. *(REQ-002; CS-2)*
- **FR-005 (decisione all'utente).** La skill **propone** il provider con motivazione; la decisione
  finale spetta sempre all'utente (nessuna selezione senza conferma). *(REQ-002; DA-G2)*

**Segreti sicuri**
- **FR-006 (segreti via percorso sicuro).** Quando serve un segreto di configurazione, la skill lo
  imposta via `sertor configure --set`/prompt sicuro e **non stampa mai** il valore del segreto. *(REQ-003;
  CS-3)*

**Download GloVe**
- **FR-007 (annuncio download).** Quando il provider `glove` è scelto e non in cache, la skill **informa**
  l'utente del download una-tantum prima di innescare il primo `index`. *(REQ-004)*

**Consenso e idempotenza**
- **FR-008 (consenso prima delle mutazioni).** Se un passo cambierebbe l'ospite o scaricherebbe
  (`install`, `configure --set`, primo `index`/download), la skill chiede conferma esplicita prima di
  eseguirlo; i check di sola lettura (`doctor`, rilevazione config) sono eseguiti liberamente. *(REQ-008)*
- **FR-009 (idempotenza su ri-esecuzione).** Mentre è ri-eseguita su un ospite già configurato, la skill
  rileva lo stato esistente e verifica (non ri-scaffolda alla cieca); conduce solo i passi mancanti.
  *(REQ-009)*

**Distribuzione e parità**
- **FR-010 (host-agnostico + dual-target).** La skill è host-agnostica e installabile su entrambi gli
  assistenti supportati via `sertor install`, con corpo byte-identico tra i target e riferimento-per-nome
  agli asset (contenitore tradotto nativamente). *(REQ-007; NFR-2)*
- **FR-011 (guardia di parità).** Il sistema di distribuzione è coperto da una guardia di parità offline
  che verifica corpo byte-identico tra target, closure dei riferimenti (ogni asset citato è depositato) e
  assenza di leak di contenitore (no path/comandi/nomi-prodotto dell'altro target). *(REQ-007; CS-5)*

**Stub del concierge (anticipa FEAT-009)**
- **FR-012 (stub concierge a un ramo).** È distribuito un agente *concierge* minimale che instrada la
  richiesta di setup verso `guided-setup`; è uno **stub** con un solo ramo e **non** dispatcha verso
  capacità non ancora esistenti (config-recommender/search-diagnose). *(DA-G1; anticipo FEAT-009)*

**Confine D↔N**
- **FR-013 (nessun LLM nel core).** L'intelligenza vive nella skill eseguita dall'agente dell'ospite; il
  **core non chiama mai un LLM** e la skill non reimplementa la logica dei comandi (li orchestra). *(REQ-E1
  d'epica; NFR-1)*

### Requisiti non funzionali
- **RNF-1 (D↔N, Principio XI):** la skill è eseguita dall'agente ospite e usa solo i vehicle; il core non
  chiama un LLM; nessun accesso a internals per scorciatoie. *(NFR-1)*
- **RNF-2 (host-agnostico, Principio X):** corpo della skill (e dello stub) byte-identico tra Claude e
  Copilot (riferimento-per-nome agli asset); contenitore tradotto nativamente. *(NFR-2)*
- **RNF-3 (privacy):** nessun segreto a schermo o nei log; i segreti passano per i percorsi sicuri del
  wizard. *(NFR-3)*
- **RNF-4 (onestà, Principio XII):** lo stato riportato è quello **verificato** da `doctor`, mai presunto.
  *(NFR-4)*
- **RNF-5 (consenso & non-distruttività):** nessuna mutazione/download dell'ospite senza conferma
  esplicita; ri-esecuzione idempotente. *(REQ-008/009)*
- **RNF-6 (calibrazione al valore):** la skill è un asset di **istruzioni** — prescrive il flusso e i
  vincoli, non sovra-specifica; orchestra i vehicle, non li reimplementa. *(epica §5 «calibra al valore»)*
- **RNF-7 (additività):** a feature installata, il comportamento dei comandi deterministici è identico a
  oggi; nessun percorso runtime del core è alterato. *(CS-6 d'epica)*

### Key Entities
- **Skill `guided-setup`** — l'asset di istruzioni host-agnostico che l'agente dell'ospite esegue;
  prescrive il flusso install → configure → verify, la scelta provider con conferma, i segreti sicuri, il
  verify fail-loud, il consenso e l'idempotenza. Body byte-identico tra target, riferimento-per-nome agli
  asset.
- **Stub dell'agente *concierge*** — agente minimale (un solo ramo) che instrada la richiesta di setup
  verso `guided-setup`; anticipa FEAT-009 senza implementarne i compiti pieni.
- **Vehicle orchestrati** — i comandi deterministici che la skill richiama (`sertor install`,
  `sertor configure --set`, `sertor-rag doctor`, `sertor-rag index`); non sono in ambito (sono FEAT-001/E2),
  la skill li usa.
- **Raccomandazione di provider** — l'esito dell'euristica minima (creds cloud? airgapped? semantica NL?)
  → provider consigliato (`glove`/`hash`/cloud) + motivazione; proposta da confermare, non decisione.
- **Esito di verifica** — il report di `sertor-rag doctor` (le quattro aree con pass/warn/fail) che la
  skill riporta onestamente; gate del «successo».
- **Artefatti di distribuzione dual-target** — i contenitori nativi per assistente in cui skill e stub
  sono depositati via `sertor install` (Claude `.claude/skills`+`.claude/agents` ↔ Copilot
  `.github/skills`+`.github/agents`); coperti dalla guardia di parità.

## Success Criteria *(mandatory)*
- **CS-1 (dal nulla a verificato):** seguendo la sola skill, un utente nuovo arriva da repo non
  configurato a `sertor-rag doctor` tutto verde, senza conoscere i nomi dei comandi/knob. *(FR-001/002,
  US1)*
- **CS-2 (scelta provider motivata):** la skill sceglie il provider dal contesto (airgapped? creds cloud?
  semantica NL?) e lo motiva, lasciando la decisione all'utente; verificato su almeno il caso «creds
  assenti → locale» e «creds presenti → cloud proposto». *(FR-004/005, US2)*
- **CS-3 (segreti mai esposti):** nessun valore di segreto compare nell'output della skill in alcun
  flusso; i segreti passano per `configure --set`/prompt sicuro. *(FR-006, US3)*
- **CS-4 (verify fail-loud):** con `doctor` verde la skill dichiara «verificato»; con `doctor` rosso
  espone area+rimedio e non dichiara successo. *(FR-002/003, US5)*
- **CS-5 (host-agnostico & installabile):** skill e stub sono installabili su Claude e Copilot via
  `sertor install`; corpo byte-identico, closure dei riferimenti, zero leak di contenitore — verificati
  dalla guardia di parità offline. *(FR-010/011, US8)*

## Assumptions
- **A-001 — `sertor-rag doctor` disponibile (FEAT-001, su `master`):** è il passo di *verify* della skill;
  senza, la skill resterebbe cieca sull'esito. Prerequisito soddisfatto (FEAT-001 consegnata).
- **A-002 — Vehicle E2 disponibili:** `sertor install` e `sertor configure`/`--set` (wizard CI-safe,
  segreti via `getpass`/`mask_secret`) sono i vehicle orchestrati; esistono nel pacchetto `sertor`.
- **A-003 — Pattern di distribuzione dual-target riusabile:** il render da fonte unica + contenitore
  nativo per assistente + guardia di parità è collaudato (`wiki-author`, `eval-suite-author`); questa
  feature lo riusa, non lo reinventa.
- **A-004 — Agente frontier presente sull'ospite:** è il presupposto del modello agentico di Sertor;
  dove non c'è, la skill non si applica (restano i vehicle deterministici).
- **A-005 — Euristica provider minima sufficiente per l'MVP:** pochi segnali (creds cloud / airgapped /
  esigenza NL) + conferma utente bastano; la profilazione ricca del repo è FEAT-004 (config-recommender).
- **A-006 — Sinergia con FEAT-003 (progress GloVe):** la skill si appoggia al progress quando esiste;
  finché non c'è, l'annuncio testuale del download una-tantum è sufficiente (degrado onesto).

### Fuori ambito (dichiarato)
- **I comandi deterministici in sé** (`install`/`configure`/`doctor`/`index`): esistono già (FEAT-001 /
  E2 `sertor-cli`) — la skill li **usa**, non li ricrea.
- **Profilazione ricca del repo per la scelta provider** (linguaggi/dimensione/struttura): è **FEAT-004**
  (config-recommender); qui solo euristica minima + conferma.
- **Compiti pieni del concierge** (dispatch verso config-recommender/search-diagnose, check proattivi
  all'avvio): sono **FEAT-009**; qui solo lo **stub** a un ramo (anticipo dichiarato).
- **Progress/ETA del download GloVe** (meccanismo deterministico): è **FEAT-003**; qui solo l'annuncio.
- **Auto-azione senza consenso:** la skill propone ed esegue **su conferma** ogni mutazione/download.
- **Il core che chiama un LLM** (confine D↔N): l'intelligenza è nell'agente dell'ospite.
- **Il *come* di dettaglio** (forma esatta del body della skill e dei prompt, struttura dello stub
  concierge, segnali esatti dell'euristica, wiring preciso nell'installer e nella guardia di parità):
  fase di **design/plan**.

> **Tracciamento dello scope.** Lo **stub del concierge** anticipa **FEAT-009** (epica `usabilita`): va
> tracciato nel backlog d'epica come **parzialmente avviato (stub)**, non come consegnato — i compiti
> pieni restano FEAT-009. La sinergia con **FEAT-003** (progress GloVe) e **FEAT-004**
> (config-recommender) è un consumo opzionale: le voci restano nel backlog d'epica, non rinviate solo
> dentro `specs/`. La feature non è *done* finché un ospite Claude **e** uno Copilot ricevono skill +
> stub via `sertor install` (corollario «feature completa»): è in ambito (FR-010/011), non un debito
> rinviato.

### Forche di design — RISOLTE con l'utente (per `/speckit-plan`)
- **DA-G1 — Skill autonoma vs ramo del concierge: RISOLTA.** Scope esteso a **entrambi**: skill
  `guided-setup` invocabile a sé (pattern `wiki-author`/`eval-suite-author`) **+** uno **stub** dell'agente
  *concierge* (un solo ramo: instrada verso guided-setup). Anticipa FEAT-009 (stub), tracciato come
  parzialmente avviato. *(decisione utente; FR-012.)*
- **DA-G2 — Profondità dell'euristica di scelta provider: RISOLTA.** **Euristica minima** (creds cloud
  presenti? host airgapped? serve semantica NL?) → consiglia locale/cloud con motivazione; **decide
  l'utente**. La profilazione ricca resta FEAT-004. *(decisione utente; FR-004/005.)*
- **DA-G3 — Confine d'esecuzione sull'ospite: RISOLTA.** «**Esegue su conferma**»: check di **sola
  lettura** liberi (`doctor`, rilevazione config); passi che **mutano l'ospite o scaricano**
  (`install`, `configure --set`, primo `index`/download GloVe) **proposti ed eseguiti solo dopo conferma
  esplicita** (REQ-008 consenso, REQ-009 idempotenza). Mai segreti a schermo (REQ-003). *(decisione utente;
  FR-006/008/009.)*
- **DA-D-r1 (residuo, design) — Forma esatta degli asset:** struttura del body della skill, dei prompt di
  conferma, dello stub concierge, segnali precisi dell'euristica provider — *Design.*
- **DA-D-r2 (residuo, design) — Wiring di distribuzione:** punti esatti nell'installer (Surface/contenitori
  per target) e nella guardia di parità (closure dei riferimenti, anti-leak) — *Design.*
