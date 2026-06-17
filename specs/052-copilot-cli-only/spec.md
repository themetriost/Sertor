# Feature Specification: Consolidamento della distribuzione Copilot su un solo target (CLI-only)

**Feature Branch**: `052-copilot-cli-only`

**Created**: 2026-06-17

**Status**: Draft

**Input**: Deriva da `requirements/sertor-cli/copilot-cli-only/requirements.md` (FEAT-012, epica
`sertor-cli`). La distribuzione Copilot è verificata funzionante end-to-end (Copilot CLI 1.0.63), ma
permangono tre incoerenze/footgun: due target Copilot paralleli e non-equivalenti (VS Code vs CLI),
naming divergente fra pacchetti (`sertor` espone `copilot|copilot-cli`, `sertor-flow` solo `copilot`),
e la skill `requirements` resa come prompt-file (non invocabile dalla CLI). La decomposizione è
**chiusa**: le domande di scope Q1–Q4 sono già risolte con l'utente (2026-06-17) — **(Q1 a)** rimozione
TOTALE del target VS Code (`AssistantId.COPILOT`) dal kit, niente codice morto; **(Q2)** mapping del
nostro `copilot-cli` sull'upstream `--ai copilot` in un solo punto documentato; **(Q3 a)** per ospiti
già installati VS Code solo nota di migrazione (cleanup manuale, niente rilevamento/migrazione
automatica); **(Q4 a)** in `sertor-flow` rinomina DIRETTA `copilot → copilot-cli` (breaking
dichiarato, niente alias di deprecazione). Queste decisioni NON si riaprono: eventuali ambiguità di
*come* vanno a `/speckit-plan`.

---

> **Confine vincolante (riflesso ovunque in questa spec — non riaprire):** un solo target Copilot
> esposto, **la CLI** (`copilot-cli`). Il valore `copilot` (VS Code) **non è più raggiungibile** da
> nessun flag `--assistant` di nessun pacchetto. Il refactor è confinato ai pacchetti installer
> (`sertor`, `sertor-flow`, `sertor-install-kit`); **`sertor-core` resta invariato** (porte, adapter,
> composition, `sertor-rag`). Le superfici Copilot CLI restano **derivate dalla sorgente canonica
> Claude** (anti-drift), nessuna copia mantenuta separatamente. Il target `claude` resta **invariato**
> (non-regressione, gate). `install ≠ run`: nessun artefatto di esecuzione, nessuna indicizzazione.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un solo valore Copilot, niente target VS Code fuorviante (Priority: P1)

Un maintainer installa Sertor su un ospite Copilot. Oggi può scrivere `--assistant copilot` credendo
di configurare la propria CLI e ottenere invece artefatti in formato VS Code (un file di
configurazione MCP che la CLI non legge), con la capacità silenziosamente non funzionante. Con questa
storia il solo valore Copilot esposto è `copilot-cli`: chi passa `copilot` riceve un errore esplicito
che nomina il valore corretto, e l'installazione non produce mai artefatti VS Code.

**Why this priority**: È la causa-radice del footgun e il valore terminale della feature: due target
paralleli e non-equivalenti dietro lo stesso flag generano una capacità che sembra installata ma non
funziona. Eliminare la biforcazione rimuove la classe di errore alla radice. Senza questa storia tutte
le altre (naming, skill, mapping) restano incoerenti con un target ambiguo.

**Independent Test**: Eseguire un comando d'installazione con il valore Copilot legacy (`copilot`) e
verificare che termini con errore esplicito nominando `copilot-cli`; eseguire l'installazione con
`copilot-cli` e ispezionare il piano/artefatti, verificando che non compaia alcun artefatto specifico
di VS Code (file di configurazione MCP VS Code, prompt-file come veicolo dei comandi).

**Acceptance Scenarios**:

1. **Given** un comando d'installazione di `sertor` o `sertor-flow`, **When** l'utente passa il valore
   Copilot legacy (`copilot`) al flag dell'assistente, **Then** il comando termina con esito di errore
   e un messaggio esplicito che nomina `copilot-cli` come il valore Copilot corretto.
2. **Given** un'installazione con il valore `copilot-cli`, **When** si ispezionano gli artefatti
   prodotti, **Then** non esiste alcun file di configurazione MCP in formato VS Code e nessun
   prompt-file usato come veicolo dei comandi.
3. **Given** il toolkit d'installazione condiviso dopo il refactor, **When** se ne ispeziona
   l'enumerazione degli assistenti, **Then** non contiene più alcun valore per il target Copilot VS
   Code né i suoi rami di resa specifici (file di configurazione MCP VS Code, chiave-radice VS Code,
   prompt-file come veicolo dei comandi).

---

### User Story 2 - Naming uniforme `claude|copilot-cli` fra tutti i pacchetti (Priority: P1)

Un utente che lavora con la CLI usa sia `sertor` (RAG/wiki) sia `sertor-flow` (governance). Oggi vede
due interfacce divergenti: `sertor` accetta `claude|copilot|copilot-cli`, `sertor-flow` solo
`claude|copilot`. Con questa storia entrambi i pacchetti (e tutti i loro verbi: install, upgrade,
uninstall) espongono esattamente lo stesso insieme `claude|copilot-cli`, senza che `copilot` sia un
valore valido in nessun punto.

**Why this priority**: La coerenza del naming fra pacchetti dello stesso ecosistema è ciò che rende
prevedibile l'esperienza CLI; un'interfaccia divergente è essa stessa un footgun (l'utente impara un
valore su un comando e lo riusa erroneamente sull'altro). È P1 perché è un invariante d'interfaccia,
non un raffinamento.

**Independent Test**: Consultare l'aiuto/usage del flag dell'assistente per i comandi di `sertor` e di
`sertor-flow` (install, upgrade, uninstall) e verificare che mostrino esattamente `claude|copilot-cli`
in tutti, senza `copilot`; verificare che passare `copilot` produca errore in ciascuno.

**Acceptance Scenarios**:

1. **Given** un qualunque comando di `sertor` che accetta l'assistente (install, upgrade, uninstall),
   **When** se ne consulta l'aiuto, **Then** i valori validi sono esattamente `claude` e
   `copilot-cli`, e nessun altro.
2. **Given** un qualunque comando di `sertor-flow` che accetta l'assistente (install, upgrade,
   uninstall), **When** se ne consulta l'aiuto, **Then** i valori validi sono esattamente `claude` e
   `copilot-cli`, e nessun altro.
3. **Given** uno qualunque di quei comandi, **When** l'utente passa un valore diverso da `claude` o
   `copilot-cli`, **Then** il comando termina con esito di errore esplicito.

---

### User Story 3 - La skill `requirements` è invocabile dalla Copilot CLI (Priority: P1)

Un utente su Copilot CLI installa la governance con `sertor-flow` e vuole invocare la skill
`requirements`. Oggi è depositata come prompt-file, che esiste solo in VS Code, quindi dalla CLI la
skill non è raggiungibile. Con questa storia, sul target `copilot-cli`, la skill `requirements` è
installata come custom-agent (come gli altri comandi wiki di `sertor` già risolti in FEAT-011) ed è
invocabile dalla riga di comando; nessun prompt-file `requirements` viene depositato per quel target.

**Why this priority**: Sul target CLI è una capacità completamente assente, non degradata: la skill non
esiste. È l'ultima superficie Sertor-authored rimasta indietro rispetto a FEAT-011, e completa la
parità della governance su CLI.

**Independent Test**: Eseguire l'installazione della governance con `copilot-cli` e ispezionare gli
artefatti: verificare che la skill `requirements` sia presente come file custom-agent (invocabile da
CLI) e che non sia presente come prompt-file.

**Acceptance Scenarios**:

1. **Given** l'installazione della governance con il target Copilot CLI, **When** si ispezionano gli
   artefatti, **Then** la skill `requirements` è depositata come file custom-agent invocabile dalla
   CLI.
2. **Given** la stessa installazione, **When** si ispezionano gli artefatti, **Then** non esiste alcun
   prompt-file per la skill `requirements`.
3. **Given** il custom-agent `requirements` generato per `copilot-cli`, **When** se ne confronta il
   corpo con la fonte canonica Claude, **Then** deriva dalla stessa sorgente unica (anti-drift),
   senza una copia mantenuta separatamente.

---

### User Story 4 - Lanciare la governance upstream con il nome che spec-kit riconosce (Priority: P1)

Quando `sertor-flow` installa la governance per il target `copilot-cli`, deve lanciare l'inizializzatore
upstream (spec-kit) con il valore di assistente che quest'ultimo riconosce — `copilot`, perché spec-kit
0.8.18 non conosce `copilot-cli`. Con questa storia il nostro `copilot-cli` è tradotto nell'argomento
upstream corretto in un unico punto documentato, e la verifica del layout atteso dopo l'inizializzazione
controlla i marker effettivamente prodotti da spec-kit per l'assistente Copilot (così l'idempotenza non
si rompe rilanciando ogni volta).

**Why this priority**: Senza la traduzione corretta il lancio upstream fallisce (valore non
riconosciuto) e la governance non si installa; senza l'allineamento della verifica del layout
l'idempotenza si rompe (layout mai trovato → rilancio a ogni esecuzione). È P1 perché abilita
l'installazione stessa della governance su CLI.

**Independent Test**: Verificare, con un esecutore di comando simulato (offline), che il comando di
inizializzazione costruito per `copilot-cli` contenga il valore upstream `copilot`; verificare che la
verifica del layout atteso dopo l'inizializzazione controlli i marker coerenti con l'assistente Copilot
(non una chiave specifica `copilot-cli` che spec-kit non produce).

**Acceptance Scenarios**:

1. **Given** `sertor-flow` che installa la governance per `copilot-cli`, **When** costruisce il comando
   di inizializzazione upstream, **Then** il comando passa il valore di assistente upstream `copilot`.
2. **Given** la traduzione `copilot-cli` → valore upstream, **When** se ne cerca la definizione nel
   sorgente, **Then** risiede in un unico punto, esplicitamente documentato.
3. **Given** un'installazione della governance per `copilot-cli` eseguita due volte sullo stesso ospite,
   **When** si verifica il layout atteso dopo l'inizializzazione, **Then** i marker controllati
   coincidono con quelli effettivamente prodotti da spec-kit per l'assistente Copilot, così la seconda
   esecuzione è riconosciuta come già inizializzata (idempotenza preservata).

---

### User Story 5 - Il target Claude resta intatto (Priority: P1)

Un utente che usa Claude non deve subire alcun effetto da questo consolidamento. Tutte le superfici
installate con `--assistant claude`, sia per `sertor` sia per `sertor-flow`, restano identiche a prima
del refactor.

**Why this priority**: La non-regressione di Claude è un gate duro del prodotto: il target principale
non può degradare per un refactor che riguarda Copilot. È P1 perché è un invariante assoluto.

**Independent Test**: Eseguire l'installazione con `claude` prima e dopo il refactor e confrontare gli
artefatti prodotti, verificandone l'identità; verificare che la suite di test esistente per Claude
resti verde senza modifiche alla sua logica.

**Acceptance Scenarios**:

1. **Given** un'installazione con il target Claude, **When** si confrontano gli artefatti prodotti
   prima e dopo il refactor, **Then** sono identici per `sertor` e per `sertor-flow`.
2. **Given** la suite di test esistente che copre il target Claude, **When** la si esegue dopo il
   refactor, **Then** resta verde senza che la sua logica di test debba essere modificata.

---

### User Story 6 - Migrazione onesta per chi aveva installato il target VS Code (Priority: P2)

Un ospite che in passato ha eseguito l'installazione con il valore Copilot legacy (`copilot`, VS Code)
ha artefatti VS Code sul disco. Dopo il consolidamento, ri-eseguire con `copilot` fallisce (Story 1).
Con questa storia l'utente trova una nota di migrazione chiara nella documentazione: il target è stato
consolidato in `copilot-cli` e il percorso di aggiornamento è ri-eseguire l'installazione con
`--assistant copilot-cli` sullo stesso ospite (gli eventuali artefatti VS Code residui sono rimossi
manualmente — nessun rilevamento/migrazione automatica).

**Why this priority**: È la chiusura onesta della breaking change voluta. È P2 perché l'uso reale del
target VS Code è probabilmente nullo (mai validato su client reale), ma una breaking change senza
percorso di migrazione documentato lascerebbe un utente bloccato senza spiegazione.

**Independent Test**: Consultare la documentazione d'installazione e verificare che contenga una nota di
migrazione che spiega il consolidamento in `copilot-cli`, indica come percorso di aggiornamento la
ri-esecuzione con `--assistant copilot-cli`, e chiarisce che il cleanup degli artefatti VS Code residui
è manuale (nessuna logica automatica).

**Acceptance Scenarios**:

1. **Given** la documentazione d'installazione dopo il refactor, **When** la si consulta, **Then**
   contiene una nota di migrazione che spiega che il target Copilot è stato consolidato in `copilot-cli`.
2. **Given** la nota di migrazione, **When** la si legge, **Then** indica come percorso di aggiornamento
   la ri-esecuzione dell'installazione con `--assistant copilot-cli` sullo stesso ospite.
3. **Given** la nota di migrazione, **When** la si legge, **Then** chiarisce che la rimozione degli
   eventuali artefatti VS Code residui è un'operazione manuale, senza alcun rilevamento o migrazione
   automatica.

---

### User Story 7 - Documentazione allineata a un solo percorso Copilot (Priority: P2)

Un consumatore della documentazione d'installazione deve trovare un solo percorso Copilot, coerente con
il codice. Oggi la documentazione descrive entrambi i target e usa il valore legacy negli esempi. Con
questa storia la documentazione dedicata a Copilot e quella di riferimento descrivono un unico percorso
con `--assistant copilot-cli`, senza più una sezione/esempi per il target VS Code.

**Why this priority**: Una documentazione che continua a citare il target rimosso contraddice il codice
e ricrea il footgun a livello di istruzioni. È P2 perché segue le correzioni di codice P1, ma completa
il "done" (documentazione utente allineata alla realtà).

**Independent Test**: Ispezionare la documentazione dedicata a Copilot e quella di riferimento e
verificare che gli esempi usino `--assistant copilot-cli`, che non esista una sezione separata per il
target VS Code e che l'elenco dei valori validi sia esattamente `claude|copilot-cli`.

**Acceptance Scenarios**:

1. **Given** la documentazione d'installazione dedicata a Copilot, **When** la si consulta, **Then**
   descrive un singolo percorso d'installazione con `--assistant copilot-cli`, senza una sezione per il
   target VS Code né esempi con il valore legacy.
2. **Given** la documentazione di riferimento dell'installazione, **When** la si consulta, **Then**
   elenca esattamente `claude|copilot-cli` come insieme completo dei valori validi dell'assistente.

---

### Edge Cases

- **Valore Copilot legacy passato** (`copilot`) → il comando termina con esito di errore esplicito che
  nomina `copilot-cli`, mai un comportamento silenzioso o un fallback al target VS Code.
- **Valore di assistente sconosciuto** (diverso da `claude`/`copilot-cli`) → errore esplicito, exit di
  uso errato; la risoluzione del profilo solleva sul valore (ora sconosciuto) `copilot`.
- **Punto di formazione del valore upstream non unico** → se la stringa di assistente per l'upstream si
  formasse in più punti, la traduzione `copilot-cli` → `copilot` potrebbe restare incompleta; la spec
  richiede un unico punto documentato (Story 4).
- **Verifica del layout atteso non aggiornata** → se la verifica cercasse una chiave specifica
  `copilot-cli` che spec-kit non produce, il layout non sarebbe mai trovato e l'inizializzazione
  rilancerebbe a ogni esecuzione (rottura dell'idempotenza).
- **Test del vecchio target VS Code rimossi senza equivalente CLI** → una superficie resterebbe priva
  di copertura; la spec richiede copertura equivalente per `copilot-cli` al posto di ogni test VS Code
  rimosso.
- **Ospite con artefatti VS Code residui** → il refactor non li tocca automaticamente; la migrazione è
  documentale (Story 6), il cleanup è manuale.
- **Tentazione di mantenere il target VS Code "nascosto" nel codice** → escluso: la rimozione è totale
  (Q1 a), nessun codice morto né profilo non testato.
- **Tentazione di introdurre un alias di deprecazione per `copilot`** → escluso: in `sertor-flow` la
  rinomina è diretta, la breaking change è voluta e dichiarata (Q4 a).

## Requirements *(mandatory)*

> **Un solo target Copilot:** dopo questo refactor il solo valore Copilot valido è `copilot-cli`. Il
> valore `copilot` (VS Code) non è esposto né raggiungibile in alcun pacchetto; passarlo è un errore
> esplicito. Le superfici Copilot CLI restano derivate dalla sorgente canonica Claude (anti-drift); il
> target Claude è invariato; `sertor-core` non viene toccato.

### Functional Requirements

**Gruppo A — Rimozione del target VS Code**

- **FR-001**: Quando l'utente passa il valore Copilot legacy (`copilot`) a un qualunque comando di
  `sertor` o `sertor-flow`, il sistema MUST rifiutarlo con un messaggio di errore esplicito che nomina
  `copilot-cli` come il valore Copilot corretto.
- **FR-002**: Il sistema MUST non produrre alcun file di configurazione MCP in formato VS Code come
  artefatto d'installazione per nessun target.
- **FR-003**: Il sistema MUST non produrre alcun prompt-file come veicolo dei comandi per il target
  `copilot-cli`.
- **FR-004**: Il sistema MUST rimuovere totalmente il valore del target Copilot VS Code
  dall'enumerazione degli assistenti del toolkit condiviso, insieme al suo profilo e a tutti i rami di
  resa specifici di VS Code (file di configurazione MCP VS Code, chiave-radice VS Code, prompt-file come
  veicolo dei comandi); nessun codice morto né profilo non testato deve restare.

**Gruppo B — Naming uniforme `copilot-cli`**

- **FR-005**: Il comando d'installazione di `sertor` MUST accettare esattamente `claude` e
  `copilot-cli` come valori validi dell'assistente; ogni altro valore MUST produrre un errore esplicito.
- **FR-006**: I comandi di installazione, upgrade e disinstallazione di `sertor-flow` MUST accettare
  esattamente `claude` e `copilot-cli` come valori validi dell'assistente; ogni altro valore MUST
  produrre un errore esplicito.
- **FR-007**: I comandi di upgrade e disinstallazione di `sertor` MUST accettare esattamente `claude` e
  `copilot-cli` come valori validi dell'assistente; ogni altro valore MUST produrre un errore esplicito.
- **FR-008**: Dopo la rimozione del target VS Code, la risoluzione del profilo dell'assistente per
  `copilot-cli` MUST risolvere la superficie MCP sul file di configurazione MCP a livello di repository
  con la chiave-radice della CLI, e tutte le altre superfici sulle convenzioni native della CLI; la
  stessa risoluzione MUST sollevare un errore sul valore (ora sconosciuto) `copilot`.

**Gruppo C — Skill `requirements` come custom-agent su `copilot-cli`**

- **FR-009**: Quando si installa la governance di `sertor-flow` con il target `copilot-cli`, il sistema
  MUST depositare la skill `requirements` come file custom-agent invocabile da Copilot CLI.
- **FR-010**: Quando si installa la governance con il target `copilot-cli`, il sistema MUST non produrre
  alcun prompt-file per la skill `requirements`.
- **FR-011**: Il custom-agent della skill `requirements` per `copilot-cli` MUST essere derivato dalla
  stessa sorgente canonica Claude usata per tutte le altre superfici Sertor-authored (anti-drift), senza
  una copia mantenuta separatamente.
- **FR-012**: Il veicolo dei comandi per la superficie comando del profilo `copilot-cli` MUST essere il
  custom-agent.

**Gruppo D — Mapping upstream spec-kit**

- **FR-013**: Quando `sertor-flow` installa la governance per `copilot-cli` e lancia l'inizializzatore
  upstream, il sistema MUST passare il valore di assistente upstream `copilot` (il valore riconosciuto da
  spec-kit 0.8.18).
- **FR-014**: La verifica del layout atteso dopo l'inizializzazione upstream per il target `copilot-cli`
  MUST controllare i marker coerenti con il layout dell'assistente Copilot prodotto da spec-kit, non una
  chiave specifica `copilot-cli` che spec-kit non produce.
- **FR-015**: La traduzione dal valore di assistente `copilot-cli` all'argomento upstream MUST risiedere
  in un unico punto ed essere esplicitamente documentata.

**Gruppo E — Non-regressione Claude e copertura di test**

- **FR-016**: Il sistema MUST produrre artefatti identici per il target `claude` prima e dopo questo
  refactor; nessun test rivolto a Claude MUST richiedere modifiche alla propria logica.
- **FR-017**: La suite di test esistente per `copilot-cli` (RAG, wiki, hook) MUST continuare a passare
  senza modifiche alla logica di test rivolta a `copilot-cli`.
- **FR-018**: Quando i test per il precedente target VS Code (`copilot`) vengono aggiornati, il sistema
  MUST fornire una copertura equivalente per `copilot-cli` al loro posto, così che nessuna superficie
  resti priva di test.
- **FR-019**: I test di guardia sugli asset Copilot MUST verificare gli asset per `copilot-cli`
  soltanto; i riferimenti al profilo VS Code MUST essere rimossi dal loro ambito.

**Gruppo F — Documentazione e migrazione**

- **FR-020**: La documentazione d'installazione dedicata a Copilot MUST descrivere un singolo percorso
  d'installazione, usando `--assistant copilot-cli` ovunque, senza una sezione per il target VS Code né
  esempi con il valore legacy `copilot`.
- **FR-021**: La documentazione di riferimento dell'installazione MUST elencare `claude|copilot-cli`
  come insieme completo dei valori validi dell'assistente, rimuovendo il valore VS Code `copilot`.
- **FR-022**: Il sistema MUST includere una nota di migrazione (nella documentazione d'installazione)
  per gli utenti che in precedenza hanno eseguito l'installazione con il valore Copilot legacy
  (`copilot`), spiegando che il target è stato consolidato in `copilot-cli` e che il percorso di
  aggiornamento è ri-eseguire l'installazione con `--assistant copilot-cli` sullo stesso ospite, con
  cleanup manuale degli eventuali artefatti VS Code residui.

### Key Entities

- **Target Copilot (unico)**: l'assistente ospite Copilot di destinazione, ora un solo valore —
  `copilot-cli` — con il suo profilo nativo (file di configurazione MCP a livello di repository con
  chiave-radice della CLI; comandi come custom-agent; hook nativi).
- **Profilo di assistente (seam)**: l'unico punto che conosce le convenzioni per-assistente e risolve
  dove/come ogni superficie si materializza; dopo il refactor conosce solo `claude` e `copilot-cli`, e
  solleva sul valore `copilot`.
- **Enumerazione degli assistenti**: il tipo condiviso nel toolkit d'installazione; dopo la rimozione
  totale contiene solo i valori validi, senza traccia del target VS Code.
- **Superficie comando**: la capacità invocabile (comandi wiki, skill `requirements`) resa nel veicolo
  nativo del target CLI — custom-agent — non come prompt-file.
- **Skill `requirements` (Sertor-authored)**: la superficie comando della governance di `sertor-flow`,
  ora resa come custom-agent su `copilot-cli`, derivata dalla sorgente canonica Claude.
- **Mapping del valore upstream**: la traduzione, in un unico punto documentato, dal nostro
  `copilot-cli` all'argomento di assistente che spec-kit riconosce (`copilot`).
- **Verifica del layout atteso**: il controllo di idempotenza che, dopo l'inizializzazione upstream,
  riconosce un'installazione già presente; per `copilot-cli` controlla i marker coerenti con il layout
  Copilot prodotto da spec-kit.
- **Nota di migrazione**: la sede documentale che spiega la breaking change e il percorso di
  aggiornamento per gli ospiti già installati con il valore VS Code legacy.
- **Suite di test offline**: la copertura che attesta l'assenza di artefatti VS Code, la presenza degli
  artefatti `copilot-cli` (incluso il custom-agent `requirements`) e la non-regressione di Claude, senza
  dipendere da un client Copilot reale.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (target unico per la CLI Copilot)**: dopo il refactor, `copilot-cli` è il solo valore Copilot
  esposto dalla CLI di `sertor`, `sertor-flow` e dal toolkit condiviso; in **0** pacchetti il valore VS
  Code `copilot` è raggiungibile tramite il flag — passarlo restituisce un errore esplicito.
- **SC-002 (naming uniforme)**: `sertor` e `sertor-flow` espongono esattamente le stesse scelte
  `claude|copilot-cli` per tutti i verbi (install, upgrade, uninstall); in **0** pacchetti `copilot`
  figura come valore valido.
- **SC-003 (skill `requirements` su CLI)**: dopo l'installazione della governance con `copilot-cli`, la
  skill `requirements` è presente come file custom-agent invocabile da CLI e **0** prompt-file
  `requirements` sono prodotti.
- **SC-004 (nessun artefatto VS Code)**: dopo l'installazione con `copilot-cli`, in **0** casi vengono
  prodotti un file di configurazione MCP in formato VS Code o prompt-file come veicolo dei comandi.
- **SC-005 (non-regressione Claude)**: gli artefatti prodotti per il target `claude` sono identici prima
  e dopo il refactor, sia per `sertor` sia per `sertor-flow`, e la suite di test esistente per Claude
  resta verde senza modifiche alla sua logica.
- **SC-006 (mapping upstream corretto)**: quando `sertor-flow` lancia l'inizializzatore upstream per
  `copilot-cli`, la chiamata effettiva usa l'argomento upstream `copilot`; la traduzione è definita in un
  unico punto documentato.
- **SC-007 (idempotenza della governance preservata)**: l'installazione della governance con
  `copilot-cli` eseguita due volte sullo stesso ospite riconosce alla seconda esecuzione il layout già
  inizializzato (la verifica del layout atteso non rilancia l'inizializzazione upstream).
- **SC-008 (copertura equivalente, nessuna superficie scoperta)**: ogni test del precedente target VS
  Code rimosso ha un equivalente per `copilot-cli`; in **0** casi una superficie precedentemente coperta
  resta priva di test dopo il refactor.
- **SC-009 (documentazione allineata)**: la documentazione d'installazione dedicata a Copilot descrive un
  unico percorso con `copilot-cli`, non menziona il target VS Code come opzione, e l'insieme dei valori
  validi documentato è esattamente `claude|copilot-cli`; è presente una nota di migrazione per gli ex
  utenti del valore legacy.
- **SC-010 (anti-drift e core invariato)**: le superfici `copilot-cli` restano derivate dalla sorgente
  canonica Claude (nessuna copia separata) e in **0** punti il refactor modifica `sertor-core` (porte,
  adapter, composition, `sertor-rag`); il toolkit condiviso resta privo di dipendenze dal nucleo.

## Assumptions

- **Le decisioni di scope Q1–Q4 sono risolte a monte** (requirements, 2026-06-17) e codificate qui:
  rimozione TOTALE del target VS Code (Q1 a); mapping `copilot-cli → --ai copilot` in un solo punto
  documentato (Q2); per ospiti VS Code esistenti solo nota di migrazione, cleanup manuale (Q3 a);
  rinomina diretta `copilot → copilot-cli` in `sertor-flow`, breaking change senza alias (Q4 a). Non
  vengono riaperte: eventuali ambiguità di *come* sono di pertinenza di `/speckit-plan`.
- **[ASSUNTO] A-1 — copertura del target CLI**: il target `copilot-cli` copre il 100% degli utenti
  Copilot reali di Sertor; non esiste un caso d'uso validato dell'integrazione VS Code che giustifichi il
  mantenimento di `copilot` (VS Code). Se emergesse, sarebbe una nuova feature separata (riapertura del
  target VS Code), non un rollback di questo refactor.
- **[ASSUNTO] A-2 — upstream spec-kit**: spec-kit 0.8.18 accetta `--ai copilot`, non `--ai copilot-cli`;
  il mapping interno è responsabilità di Sertor e non richiede modifiche upstream. Se una versione pinned
  futura introducesse `--ai copilot-cli`, il mapping andrebbe aggiornato nell'unico punto documentato
  (Story 4 / FR-015); resta valido fino a revisione esplicita.
- **[ASSUNTO] A-3 — seam come tipo condiviso**: l'enumerazione degli assistenti vive nel toolkit
  d'installazione condiviso ed è importata sia da `sertor` sia da `sertor-flow`; la rimozione del target
  VS Code si propaga a entrambi i consumatori per costruzione (consistenza garantita dal tipo unico).
- **Confine del refactor**: confinato ai pacchetti installer (`sertor`, `sertor-flow`,
  `sertor-install-kit`). **`sertor-core` resta invariato** (porte, adapter, composition, `sertor-rag`);
  il toolkit condiviso resta stdlib-only e privo di dipendenze dal nucleo.
- **Anti-drift**: tutte le superfici `copilot-cli` restano derivate dalla sorgente canonica Claude
  tramite i renderer del toolkit (custom-agent, hook nativi); non si introducono asset mantenuti
  separatamente per `copilot-cli`.
- **`install ≠ run`**: il refactor non altera il principio; l'installer deposita artefatti e non avvia
  indicizzazione né esecuzione.
- **Non-distruttività per ospiti già `copilot-cli`**: il refactor non modifica i file depositati su
  ospiti già installati con `copilot-cli`; cambiano solo il codice Sertor e la documentazione.
- **Breaking change esplicita e voluta**: la rimozione del valore `copilot` è una breaking change
  intenzionale; deve produrre un errore esplicito e azionabile (exit di errore, messaggio che nomina
  `copilot-cli`), mai un comportamento silenzioso.
- **Fuori ambito (capacità future / asse diverso)**: supporto VS Code come target (non precluso, ma una
  nuova feature separata se mai servisse); nuovi assistenti oltre `claude` e `copilot-cli`; cloud-agent /
  Codex (già Won't in FEAT-007); rilevamento/migrazione automatica per ospiti VS Code esistenti (solo
  nota documentale); il comando `sertor-rag check` (follow-up FEAT-003); qualunque modifica al runtime di
  `sertor-core`.
- **Domande di design ancora aperte (→ `/speckit-plan`, non bloccano la spec)**: la forma esatta della
  rimozione nell'enumerazione e dei rami di resa da eliminare; il punto preciso e la forma del mapping del
  valore upstream; l'aggiornamento concreto della verifica del layout atteso per `copilot-cli`; la
  strategia di sostituzione dei test del vecchio target con equivalenti `copilot-cli`; la collocazione
  esatta della nota di migrazione. Sono ambiguità di *come*, non di *cosa/perché*.
