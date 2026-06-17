# Feature Specification: Hardening compatibilità GitHub Copilot dell'installer

**Feature Branch**: `049-compatibilita-copilot`

**Created**: 2026-06-17

**Status**: Draft

**Input**: Deriva da `requirements/sertor-cli/compatibilita-copilot/requirements.md` (FEAT-011, epica
`sertor-cli`). Correzione di FEAT-007 (PR #64) e FEAT-009 (PR #65) dopo un audit di dogfooding su un
ospite reale (Copilot CLI 1.0.63) che ha dimostrato che la "parità funzionale piena" Copilot dichiarata
è falsa su più superfici. **Principio guida vincolante** (decisione utente 2026-06-17): supporto NATIVO
per ogni tool, niente hack di compatibilità. Sei domande di scope (Q1–Q6) risolte in elicitazione.

---

> **Principio guida (VINCOLANTE, riflesso ovunque in questa spec — non riaprire):** ogni superficie va
> resa nel **formato/contratto nativo del tool target** (Claude · Copilot VS Code · Copilot CLI). Sono
> **vietati** gli hack di compatibilità: niente JSON con campi-di-entrambi (es. `systemMessage` +
> `additionalContext` insieme), niente formato Claude "tollerato" su Copilot, niente veicolo sbagliato
> (prompt-file su Copilot CLI). Il **riuso** riguarda il **CONTENUTO** (corpo istruzionale, fonte unica
> byte-for-byte); il **CONTENITORE/contratto** va **tradotto nativamente**. L'invariante FEAT-007
> «script `.ps1` identici» (FR-014) è **rilassato** a: *corpo dello script condiviso, ma invocazione e
> contratto di output **nativi** per assistente* (parametro d'invocazione `-Assistant`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gli hook installati per Copilot partono davvero (Priority: P1)

Un owner installa le capacità Sertor (wiki, rag-usage) su un ospite Copilot — VS Code o CLI — e si
aspetta che gli hook configurati vengano caricati ed eseguiti. Oggi il file hook è in formato Claude
(manca il campo di versione di schema, struttura annidata incompatibile, campi non riconosciuti):
l'interprete Copilot lo scarta e **nessun hook viene eseguito**, in silenzio. Con questa storia il file
hook risultante è conforme allo schema Copilot, viene caricato e gli hook si eseguono.

**Why this priority**: È il bug più critico e silenzioso dell'audit: senza il campo di versione di schema
l'intero file hook viene scartato e l'utente crede installata una capacità che non esiste. Senza questa
storia tutte le altre correzioni di output hook (Story 2/3) sono irraggiungibili.

**Independent Test**: Generare gli artefatti hook per i target Copilot e verificare, su un controllo di
sola ispezione (offline), che ogni file porti il campo di versione di schema, la forma piatta delle voci
e nessun campo Claude-only; confermare su un ospite reale che l'interprete Copilot li carica.

**Acceptance Scenarios**:

1. **Given** un'installazione con target Copilot (VS Code o CLI), **When** si ispeziona il file hook
   prodotto, **Then** esso porta il campo di versione di schema richiesto da Copilot, la lista degli hook
   è annidata direttamente sotto la chiave dell'evento dentro l'oggetto hook di primo livello, e ogni voce
   usa la forma piatta nativa (tipo, comando, timeout in secondi, opzionale selettore).
2. **Given** un file hook per target Copilot, **When** lo si ispeziona, **Then** non contiene alcun campo
   estraneo allo schema Copilot (in particolare i campi Claude-only di shell e di messaggio di stato).
3. **Given** un file hook per target Copilot, **When** lo si ispeziona, **Then** il valore di timeout usa
   il nome di campo documentato da Copilot (in secondi), non il nome di campo Claude.
4. **Given** un nome di evento espresso in forma maiuscola/cammello, **When** si produce il file hook per
   Copilot, **Then** è accettato in coerenza con il contratto di compatibilità Copilot CLI (alias).

---

### User Story 2 - Gli script hook emettono il contratto nativo dell'evento Copilot (Priority: P1)

Quando un hook scatta su Copilot, lo script associato deve emettere l'output esatto che Copilot attende
**per quell'evento**, senza falsificare campi di un altro tool. Oggi lo script condiviso emette un campo
Claude-only per gli eventi di stop e di fine-sessione; Copilot non lo riconosce e l'output va perso. Per
l'evento pre-tool, su Copilot il comportamento è fail-closed: un hook malformato o in errore **nega la
chiamata allo strumento**. Con questa storia ogni evento ottiene il contratto nativo: stop non-bloccante
con campo di decisione e motivazione, pre-tool fail-open (uscita pulita senza output spurio), fine-sessione
che non si appoggia a un output che Copilot non consuma.

**Why this priority**: È la metà funzionale del problema: un hook che parte ma emette il contratto
sbagliato è inutile (output perso) o pericoloso (negazione accidentale di tool call sul pre-tool). Il
fail-closed involontario del pre-tool è il rischio più grave dell'intera feature.

**Independent Test**: Per ogni evento hook installato su un target Copilot, invocare lo script in modalità
Copilot e verificare che l'output prodotto sia conforme al contratto Copilot di quell'evento e che, per gli
eventi dichiarati non-bloccanti, non produca mai un output bloccante.

**Acceptance Scenarios**:

1. **Given** l'evento di stop su Copilot (equivalente allo Stop di Claude) con lavoro wiki pendente,
   **When** lo script hook è invocato in modalità Copilot, **Then** emette un output non-bloccante nella
   forma nativa con campo di decisione "consenti" e una motivazione che porta il messaggio, **non** il
   campo di messaggio di sistema Claude-only.
2. **Given** l'evento pre-tool su Copilot senza alcuna violazione rilevata, **When** lo script hook è
   invocato, **Then** termina con esito di successo e senza output (o con solo output conforme a Copilot),
   così che il comportamento fail-closed del pre-tool non blocchi la chiamata allo strumento.
3. **Given** l'evento di fine-sessione su Copilot, **When** lo script hook è invocato, **Then** non si
   appoggia su un output consumato da Copilot (questo evento non produce output consumato su Copilot);
   qualunque messaggio per il terminale va sul canale di errore standard.
4. **Given** un qualunque evento hook su un target Copilot, **When** lo script produce output, **Then** non
   usa come unico canale di comunicazione un campo che appartiene esclusivamente allo schema Claude.

---

### User Story 3 - L'avvio sessione su Copilot inietta davvero il contesto (Priority: P1)

All'avvio di una sessione su un ospite Copilot, l'agente deve ricevere il contesto di progetto (roadmap,
indice wiki, coda del log). Oggi il comando hook di avvio-sessione emette stringhe semplici non-JSON:
Copilot tenta il parsing e, fallendo, **non inietta alcun contesto**. Con questa storia l'avvio-sessione
usa il **meccanismo nativo del target** per iniettare contesto, senza stringhe semplici né campo
"tollerato".

**Why this priority**: Senza contesto all'avvio l'agente ospite parte "a freddo" — esattamente l'essenza
che il sistema vuole impedire. È P1 perché è una capacità dichiarata installata ma silenziosamente nulla.

**Independent Test**: Generare la superficie di avvio-sessione per ciascun target Copilot e verificare che
il wiring/output sia nella forma nativa che quel target riconosce come contesto aggiuntivo (zero
stringhe-semplici senza wrapper); confermare su un ospite reale che il contesto viene iniettato.

**Acceptance Scenarios**:

1. **Given** la superficie di avvio-sessione installata per Copilot CLI, **When** la sessione si avvia,
   **Then** è usato il meccanismo nativo della CLI per iniettare contesto (voce di hook avvio-sessione di
   tipo "prompt"), **non** una stringa semplice né un campo extra solo tollerato.
2. **Given** la superficie di avvio-sessione installata per Copilot VS Code, **When** la sessione si avvia,
   **Then** è usato il meccanismo di contesto-sessione nativo di VS Code (la forma esatta è un **nodo di
   design** da fissare in fase di plan con verifica empirica — vedi *Nodi di design*).
3. **Given** un target Copilot, **When** l'hook di avvio-sessione produce output, **Then** è parsabile da
   Copilot come contesto aggiuntivo (nessuna stringa non-JSON che faccia fallire il parsing).

---

### User Story 4 - Un solo script condiviso, output nativo per assistente (Priority: P1)

Il corpo logico degli script hook (es. il controllo del wiki pendente) deve restare **una sola fonte**
condivisa tra Claude e Copilot — non una seconda copia da mantenere — ma ciascuna invocazione deve emettere
il contratto **nativo** dell'assistente che la chiama, selezionato da un parametro esplicito passato dal
wiring per-assistente. Non si emette un unico JSON che porta sia i campi Claude sia quelli Copilot
(dual-field hack vietato).

**Why this priority**: È il prerequisito strutturale delle Story 2 e 3 (come gli script producono il
contratto nativo) e materializza il principio guida sul confine contenuto-vs-contenitore. Senza, le
correzioni di output non hanno una casa coerente e si rischia il dual-field.

**Independent Test**: Verificare che esista un'unica fonte per il corpo di ciascuno script condiviso e che,
invocata con il parametro Claude vs Copilot, produca due output **diversi e ciascuno nativo**; verificare
che nessun output porti contemporaneamente i campi dei due tool.

**Acceptance Scenarios**:

1. **Given** uno script hook condiviso, **When** lo si invoca con il parametro di assistente Claude,
   **Then** emette il contratto di output nativo Claude; **When** lo si invoca con il parametro Copilot,
   **Then** emette il contratto di output nativo Copilot.
2. **Given** uno script hook condiviso, **When** lo si invoca per un qualunque assistente, **Then** l'output
   non contiene mai sia i campi Claude sia i campi Copilot nello stesso documento.
3. **Given** un caso in cui un singolo script parametrizzato non riesca a emettere in modo pulito il
   contratto nativo per un assistente, **When** si materializza la superficie, **Then** si usa una variante
   di script per-assistente anziché un output non-nativo o dual-field.

---

### User Story 5 - I comandi wiki/governance sono invocabili da Copilot CLI (Priority: P1)

Un utente su Copilot CLI vuole invocare i comandi wiki (equivalenti di `/wiki`, `wiki-author`) e la
gestione requisiti. Oggi questi sono depositati come prompt-file, che **non esistono su Copilot CLI**: i
comandi semplicemente non sono raggiungibili. Con questa storia, per il target CLI i comandi sono installati
in una forma invocabile dalla riga di comando (custom-agent), mentre su VS Code restano disponibili anche
come prompt-file (che VS Code supporta).

**Why this priority**: Su Copilot CLI è una capacità completamente assente, non degradata: i comandi non
esistono. Il piano comandi va reso per-target (VS Code prompt-file nativo + CLI custom-agent nativo).

**Independent Test**: Generare il piano comandi per il target CLI e verificare che le superfici comandi
(wiki e gestione requisiti) siano installate in una forma non esclusivamente basata su prompt-file;
verificare che il target VS Code mantenga i prompt-file.

**Acceptance Scenarios**:

1. **Given** l'installazione della capacità wiki con target Copilot CLI, **When** si ispeziona il piano,
   **Then** le superfici comandi wiki sono installate in una forma invocabile dalla CLI (es. file
   custom-agent), non solo da VS Code.
2. **Given** l'installazione della governance (skill gestione requisiti) con target Copilot CLI tramite il
   pacchetto di governance, **When** si ispeziona il piano, **Then** la skill è installata in una forma
   invocabile dalla CLI.
3. **Given** il target Copilot VS Code, **When** si ispeziona il piano, **Then** i prompt-file restano
   forniti per le superfici comandi (supportati da VS Code/Visual Studio).

---

### User Story 6 - Frontmatter di prompt-file e custom-agent conforme a Copilot (Priority: P1)

Le superfici comando e agente tradotte per Copilot devono avere un frontmatter nativo: i prompt-file
usano la chiave di modalità documentata da Copilot (non la chiave Claude-specifica), e i custom-agent non
portano un campo di modello con un valore Claude (nome di modello Claude non valido per Copilot). I campi
di persona (nome, descrizione, strumenti) sono preservati; il corpo istruzionale resta identico alla fonte
canonica Claude.

**Why this priority**: Frontmatter errato → comportamento non documentato (chiave di modalità sbagliata) o
valore di modello non valido (modello Claude su Copilot). È correzione mirata e a basso rischio, ma fa parte
della conformità nativa.

**Independent Test**: Generare prompt-file e custom-agent per i target Copilot e verificare che il
frontmatter usi le chiavi documentate da Copilot, che nessun custom-agent porti un campo di modello con
valore Claude e che il corpo coincida byte-per-byte con la fonte canonica.

**Acceptance Scenarios**:

1. **Given** un prompt-file generato per Copilot, **When** se ne ispeziona il frontmatter, **Then** usa la
   chiave di modalità documentata da Copilot, non la chiave Claude-specifica attuale.
2. **Given** un asset agente di origine che porta un campo di modello con un valore non valido per Copilot,
   **When** lo si traduce in custom-agent Copilot, **Then** il campo di modello è **omesso** dal frontmatter
   generato (default Copilot).
3. **Given** la traduzione di un asset agente Claude in custom-agent Copilot, **When** se ne ispeziona il
   frontmatter, **Then** i campi di nome, descrizione e strumenti sono preservati.
4. **Given** un prompt-file o custom-agent reso per Copilot, **When** se ne confronta il corpo con la fonte
   canonica Claude, **Then** è identico byte-per-byte (invariante anti-drift).

---

### User Story 7 - I bug dell'audit verrebbero presi da test di validità-schema (Priority: P1)

L'owner vuole una rete che impedisca il ritorno di questi difetti: una suite di test che verifica la
**validità di schema** degli asset generati per i target Copilot (non solo la loro presenza). I difetti
descritti nell'audit (campo di versione mancante, campi Claude-only, frontmatter sbagliato, output non
conforme per evento, comandi solo-prompt-file su CLI) avrebbero fatto fallire questi test se fossero
esistiti. Ogni nuovo asset Copilot richiede un test di validità-schema prima di essere considerato pronto.

**Why this priority**: È il criterio CS-7 e l'unica garanzia che la correzione non degradi al prossimo
cambiamento. Trasforma "corretto oggi" in "verificato a ogni modifica".

**Independent Test**: Reintrodurre artificialmente ciascun difetto dell'audit (campo di versione mancante,
campo Claude-only, frontmatter sbagliato, modello Claude in custom-agent, comando solo-prompt-file su CLI)
e verificare che la suite di test corrispondente fallisca.

**Acceptance Scenarios**:

1. **Given** la suite di test, **When** si rimuove il campo di versione di schema da un file hook Copilot,
   **Then** un test fallisce; idem reintroducendo un campo Claude-only o il nome di campo di timeout
   sbagliato.
2. **Given** la suite di test, **When** un prompt-file Copilot usa la chiave di frontmatter Claude-specifica,
   **Then** un test fallisce.
3. **Given** la suite di test, **When** un custom-agent Copilot porta un campo di modello con valore Claude,
   **Then** un test fallisce.
4. **Given** la suite di test, **When** lo script di un evento installato su Copilot produce output non
   conforme al contratto di quell'evento (o un output bloccante su un evento non-bloccante), **Then** un
   test fallisce.
5. **Given** la suite di test, **When** per il target CLI una superficie comando è installata in forma
   esclusivamente prompt-file, **Then** un test fallisce.
6. **Given** la suite di test, **When** la si esegue, **Then** gira interamente offline (senza dipendere da
   un client Copilot reale).

---

### User Story 8 - Onestà sui gap: nessun claim di parità non verificata (Priority: P2)

Un consumatore della documentazione delle superfici deve sapere la verità: dove la parità funzionale piena
non è stata validata contro lo schema Copilot e confermata empiricamente, **non** deve esserci un claim di
parità. Un gap noto o un comportamento non verificato va dichiarato esplicitamente nell'output
d'installazione e nella documentazione di mappatura delle superfici, non elencato come funzionalmente
equivalente. Questa storia include la verifica empirica documentata del target MCP nativo della CLI.

**Why this priority**: È la correzione del false-positive che ha originato la feature (CS-1/CS-6 di
FEAT-007 violati). È P2 perché segue le correzioni tecniche P1, ma le completa: un claim corretto è parte
del "done".

**Independent Test**: Confrontare la documentazione delle superfici e l'output d'installazione con l'esito
delle verifiche: ogni superficie non validata-e-confermata risulta dichiarata come gap, non come parità
piena; la prova empirica sul target MCP della CLI è documentata.

**Acceptance Scenarios**:

1. **Given** una superficie non validata contro lo schema Copilot e non confermata su un client reale,
   **When** se ne consulta la documentazione, **Then** non è dichiarata "parità funzionale piena".
2. **Given** una superficie con un gap noto o comportamento non verificato per un target Copilot, **When**
   si esegue l'installazione, **Then** il gap è dichiarato esplicitamente nell'output e nella documentazione
   di mappatura, non listato come funzionalmente equivalente.
3. **Given** il target Copilot CLI, **When** si consulta la documentazione, **Then** è riportata la prova
   empirica (o la sua assenza) sul fatto che la CLI legga la configurazione MCP a livello di repository con
   la chiave radice attesa, e la superficie MCP è corretta se la prova empirica smentisce l'assunto corrente.

---

### Edge Cases

- **File hook senza il campo di versione di schema** → scartato in silenzio dall'interprete Copilot,
  nessun hook eseguito; deve essere colto da un test di schema, non scoperto a runtime.
- **Output dual-field** (campi Claude + Copilot insieme) → vietato dal principio guida: rischio che un
  campo di decisione venga interpretato in modo inatteso dall'altro tool; un test deve impedirlo.
- **Pre-tool che produce errore o output malformato su Copilot** → fail-closed: nega la chiamata allo
  strumento. L'hook deve uscire con esito di successo anche in caso di errore di parsing (fail-open
  esplicito).
- **Comando wiki invocato da Copilot CLI mentre è installato solo come prompt-file** → il comando non
  esiste sulla CLI; va installato come custom-agent.
- **Campo di modello con valore Claude in un custom-agent Copilot** → valore non valido per Copilot; va
  omesso.
- **Avvio-sessione che emette una stringa semplice** → il parsing fallisce, nessun contesto iniettato.
- **Regressione sul target Claude** dovuta a una modifica dello script condiviso → il comportamento Claude
  deve restare invariato (parametro di assistente di default Claude, test di non-regressione).
- **Schema Copilot in evoluzione (Preview)** → una versione successiva potrebbe cambiare il formato; le
  superfici restano isolate dietro il seam per assistente e i test di schema falliscono in modo esplicito.
- **Nuovo asset Copilot aggiunto senza test di schema** → debito silenzioso; ogni nuovo asset Copilot
  richiede un test di validità prima di essere considerato pronto.

## Requirements *(mandatory)*

> **Due famiglie di target Copilot:** `copilot` (Copilot in VS Code agent mode) e `copilot-cli` (Copilot
> CLI). Alcune correzioni valgono per entrambi (hook JSON, output script, frontmatter); altre divergono per
> design (veicolo comandi: prompt-file su VS Code, custom-agent su CLI; meccanismo avvio-sessione). Il
> target `claude` resta invariato (non-regressione).

### Functional Requirements

**Gruppo A — Hook JSON: conformità schema Copilot**

- **FR-001**: Il sistema MUST produrre file hook JSON per i target Copilot con il campo di versione di
  schema di primo livello richiesto dallo schema hook Copilot.
- **FR-002**: Il sistema MUST produrre file hook JSON per i target Copilot con la lista degli hook annidata
  direttamente sotto la chiave del nome-evento dentro l'oggetto hook di primo livello, con ogni voce nella
  forma piatta nativa Copilot (campi: tipo, comando, timeout-in-secondi, e opzionalmente selettore), senza
  campi Claude-specifici (shell, messaggio di stato).
- **FR-003**: Se un file hook per un target Copilot conterrebbe un campo estraneo allo schema hook Copilot
  (es. shell, messaggio di stato), allora il sistema MUST non includere quel campo nell'artefatto generato.
- **FR-004**: Il sistema MUST usare il nome di campo Copilot documentato per il timeout della voce hook
  (timeout in secondi), non il nome di campo Claude.
- **FR-005**: Il sistema MUST supportare sia i nomi-evento in forma cammello maiuscola sia i loro alias
  documentati nel produrre i file hook per i target Copilot, in coerenza col contratto di compatibilità
  Copilot CLI.

**Gruppo B — Contratto di output degli script hook per evento**

- **FR-006**: Quando la superficie di avvio-sessione è installata per un target Copilot, il sistema MUST
  usare il meccanismo nativo Copilot di quel target per iniettare contesto di sessione (su Copilot CLI una
  voce di hook avvio-sessione di tipo "prompt"; su Copilot VS Code il suo meccanismo nativo di
  contesto-sessione) e MUST non emettere stringhe semplici non-JSON né appoggiarsi a un campo extra solo
  tollerato. *(Q1 = b)*
- **FR-007**: Quando uno script hook è invocato per l'evento di stop Copilot (equivalente allo Stop di
  Claude), il sistema MUST produrre un output non-bloccante nella forma nativa con campo di decisione
  "consenti" e una motivazione, anziché un campo di messaggio di sistema che Copilot non riconosce.
  *(Q3 = b)*
- **FR-008**: Se uno script hook è invocato per l'evento pre-tool Copilot e non rileva alcuna violazione,
  allora il sistema MUST terminare con esito di successo e produrre nessun output (o solo output conforme a
  Copilot), così che il comportamento fail-closed del pre-tool non blocchi le chiamate agli strumenti.
- **FR-009**: Se uno script hook emette output per l'evento di fine-sessione su un target Copilot, allora il
  sistema MUST non appoggiarsi sul fatto che quell'output venga consumato da Copilot (l'evento non produce
  output consumato su Copilot); qualunque messaggio destinato al terminale MUST essere scritto sul canale di
  errore standard.
- **FR-010**: Se lo script hook per un target Copilot produce un campo di output che appartiene
  esclusivamente allo schema hook Claude (es. il campo di messaggio di sistema come campo isolato di primo
  livello), allora il sistema MUST non usarlo come unico canale di comunicazione per quell'evento.

**Gruppo C — Output nativo per assistente degli script condivisi (no dual-compat)**

- **FR-011**: Il sistema MUST condividere il CORPO degli script hook tra i target Claude e Copilot (fonte
  unica, nessuna copia divergente del contenuto), ma ciascuno script MUST emettere il contratto di output
  NATIVO dell'assistente che lo invoca, selezionato da un parametro d'invocazione esplicito passato dal
  wiring per-assistente. Lo script MUST non emettere un singolo JSON che porti sia i campi Claude sia i
  campi Copilot (nessun dual-field hack). *(Q4 = b; FR-014 di FEAT-007 rilassato)*
- **FR-012**: Se un singolo script parametrizzato non riesce a emettere in modo pulito il contratto nativo
  per un dato assistente, allora il sistema MUST usare una variante di script per-assistente anziché emettere
  un output non-nativo o dual-field.

**Gruppo D — Veicolo comandi per Copilot CLI**

- **FR-013**: Quando si installa la capacità wiki con il target Copilot CLI, il sistema MUST installare le
  superfici comando wiki (equivalenti di `/wiki`, `wiki-author`) in una forma invocabile da Copilot CLI (non
  solo da VS Code), quali file custom-agent. *(Q2 = c)*
- **FR-014**: Quando si installa la governance (skill gestione requisiti) con il target Copilot CLI tramite
  il pacchetto di governance, il sistema MUST installare la skill in una forma invocabile da Copilot CLI.
- **FR-015**: Dove è selezionato il target Copilot VS Code, il sistema SHOULD continuare a fornire i
  prompt-file per le superfici comando, in quanto supportati in VS Code/Visual Studio.

**Gruppo E — Frontmatter prompt-file e custom-agent**

- **FR-016**: Il sistema MUST usare il campo di frontmatter Copilot documentato per la modalità del
  prompt-file quando genera prompt-file per i target Copilot, non un nome di campo Claude-specifico.
- **FR-017**: Se l'asset agente di origine Claude contiene un campo di modello con un valore non valido per
  Copilot, allora il sistema MUST omettere il campo di modello dal frontmatter del custom-agent Copilot
  generato. *(Q6 = a)*
- **FR-018**: Il sistema MUST preservare i campi di nome, descrizione e strumenti nel tradurre un asset
  agente Claude in un custom-agent Copilot, in quanto parte del frontmatter custom-agent Copilot documentato.
- **FR-019**: Il sistema MUST mantenere il corpo istruzionale dei prompt-file e dei custom-agent resi
  byte-per-byte identico alla fonte canonica Claude, come richiesto dall'invariante anti-drift di FEAT-007.

**Gruppo F — Conformità MCP (verifica)**

- **FR-020**: Il sistema MUST documentare la prova empirica (o la sua assenza) sul fatto che Copilot CLI
  legga la configurazione MCP a livello di repository con la chiave radice attesa, e MUST correggere la
  superficie di configurazione MCP per il target CLI se la prova empirica contraddice l'assunto corrente.
  *(Q5 = incluso)*

**Gruppo G — Test di validità-schema Copilot**

- **FR-021**: Il sistema MUST includere test automatici che verifichino la validità strutturale di ogni file
  hook JSON generato per i target Copilot, asserendo: presenza del campo di versione di schema, forma
  corretta dell'oggetto hook di primo livello, assenza di campi Claude-specifici e nome di campo di timeout
  corretto.
- **FR-022**: Il sistema MUST includere test automatici che verifichino che il frontmatter di ogni
  prompt-file generato per i target Copilot usi il nome di campo Copilot documentato (non un campo
  Claude-specifico).
- **FR-023**: Il sistema MUST includere test automatici che verifichino che nessun custom-agent generato per
  un target Copilot contenga un campo di modello con un valore Claude-specifico.
- **FR-024**: Il sistema MUST includere test automatici che verifichino, per ciascun evento hook installato
  su un target Copilot, che lo script associato produca output conforme al contratto Copilot di
  quell'evento e che non produca un output bloccante per gli eventi dichiarati non-bloccanti.
- **FR-025**: Il sistema MUST includere test automatici che verifichino, per il target Copilot CLI, che le
  superfici comando (comandi wiki, skill gestione requisiti) siano installate in una forma non
  esclusivamente basata su prompt-file.
- **FR-026**: Se un nuovo asset rivolto a Copilot è aggiunto all'installer, allora il sistema MUST
  richiedere un corrispondente test di validità di schema prima che l'asset sia considerato pronto.

**Gruppo H — Onestà sui gap e correzione claim**

- **FR-027**: Il sistema MUST non dichiarare parità funzionale piena tra i target Claude e Copilot per
  alcuna superficie che non sia stata validata contro lo schema Copilot e confermata empiricamente su un
  client Copilot reale.
- **FR-028**: Se una superficie installata per un target Copilot ha un gap noto o un comportamento non
  verificato, allora il sistema MUST dichiarare quel gap esplicitamente nell'output d'installazione e nella
  documentazione di mappatura delle superfici, anziché elencarlo come funzionalmente equivalente.

**Gruppo I — Invarianti preservati**

- **FR-040**: Le correzioni MUST non alterare il comportamento dell'installer per il target Claude
  (non-regressione); l'install per Copilot resta non distruttivo e idempotente.
- **FR-041**: Qualunque script hook che gestisce l'evento pre-tool MUST terminare sempre con esito di
  successo su Copilot, anche in caso di errore di parsing o condizione imprevista (nessuna negazione
  accidentale di chiamata a strumento — fail-open).
- **FR-042**: Le stesse correzioni MUST propagarsi al pacchetto di governance (superfici Copilot degli
  agenti e della skill Sertor-authored) senza introdurre una dipendenza del pacchetto di governance dal
  pacchetto del nucleo.
- **FR-043**: Le differenze per-assistente MUST passare per il seam di profilo-assistente nel toolkit
  d'installazione condiviso; nessuna superficie Copilot va falsificata con campi solo tollerati al di fuori
  di questo seam.

### Key Entities

- **Target Copilot**: l'assistente ospite di destinazione, in due famiglie — Copilot VS Code e Copilot CLI —
  che condividono molte correzioni ma divergono su veicolo comandi e meccanismo di avvio-sessione.
- **File hook (wiring)**: l'artefatto JSON che mappa evento → script secondo lo schema nativo del target;
  per Copilot deve portare il campo di versione di schema, forma piatta delle voci e nessun campo Claude-only.
- **Script hook condiviso**: il corpo logico unico, riusato tra Claude e Copilot, che emette il contratto di
  output nativo dell'assistente selezionato da un parametro d'invocazione (mai dual-field).
- **Superficie comando**: la capacità invocabile (comandi wiki, skill gestione requisiti) tradotta nel
  veicolo nativo del target: prompt-file su VS Code, custom-agent su CLI.
- **Custom-agent / prompt-file**: gli artefatti per-file con frontmatter tradotto nativamente (chiave di
  modalità Copilot; campo di modello Claude omesso; persona preservata) e corpo identico alla fonte canonica.
- **Contratto di output per evento**: la forma che Copilot attende per ciascun evento hook (avvio-sessione,
  stop non-bloccante, pre-tool fail-open, fine-sessione non consumato).
- **Seam di profilo-assistente**: l'unico punto che conosce le convenzioni per-assistente; risolve dove e
  come ogni superficie si materializza per ciascun target.
- **Suite di test di validità-schema**: la rete che attesta la conformità strutturale degli asset Copilot
  (non solo la presenza) e che avrebbe preso i difetti dell'audit; gira offline.
- **Documentazione di mappatura delle superfici / output d'installazione**: la sede dei claim di parità e
  delle dichiarazioni di gap; non deve affermare parità non verificata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (hook conformi)**: dopo l'installazione con target Copilot (VS Code o CLI), **100%** dei file
  hook risultanti sono validi secondo lo schema Copilot (campo di versione presente, struttura piatta, nomi
  di campo corretti) e vengono caricati dall'interprete Copilot; **0** file scartati per schema invalido.
- **SC-002 (output script conformi)**: per ogni evento hook installato su un target Copilot, lo script
  associato emette l'output nella forma attesa da Copilot per quell'evento; in **0** casi un hook
  non-bloccante genera un comportamento bloccante involontario.
- **SC-003 (avvio-sessione inietta contesto)**: l'hook di avvio-sessione su target Copilot produce **zero**
  stringhe semplici senza wrapper; l'output è parsabile da Copilot come contesto aggiuntivo.
- **SC-004 (comandi raggiungibili su CLI)**: per il target Copilot CLI, i comandi equivalenti di `/wiki`,
  `wiki-author` e la skill gestione requisiti sono installati in una forma invocabile dalla CLI (non solo da
  VS Code); **0** comandi solo-prompt-file sul piano CLI.
- **SC-005 (frontmatter agente senza campi Claude-only)**: **0** custom-agent generati per target Copilot
  contengono un campo di modello con valore Claude.
- **SC-006 (frontmatter prompt-file corretto)**: **100%** dei prompt-file generati per target Copilot usano
  la chiave di frontmatter documentata da Copilot; **0** usano la chiave Claude-specifica.
- **SC-007 (validazione a test, dei bug dell'audit)**: esiste una suite di test di validità-schema per gli
  asset Copilot; reintroducendo artificialmente ciascuno dei difetti dell'audit (campo di versione mancante,
  campo Claude-only, nome di timeout sbagliato, frontmatter sbagliato, modello Claude, comando
  solo-prompt-file su CLI, output non conforme per evento) **almeno un** test fallisce per ciascun difetto;
  la suite gira **interamente offline**.
- **SC-008 (no dual-field)**: **0** output di script hook per target Copilot contengono contemporaneamente i
  campi Claude e i campi Copilot.
- **SC-009 (correzione del claim)**: nella documentazione delle superfici, **0** superfici non
  validate-e-confermate sono dichiarate "parità funzionale piena"; ogni gap noto è dichiarato esplicitamente
  nell'output d'installazione e nella documentazione di mappatura.
- **SC-010 (non-regressione Claude)**: il comportamento dell'installer e degli hook per il target Claude
  resta invariato; la suite di test esistente per il target Claude resta verde.
- **SC-011 (parità governance senza dipendenza dal core)**: le stesse correzioni valgono per le superfici
  Copilot del pacchetto di governance, **senza** introdurre una dipendenza del pacchetto di governance dal
  pacchetto del nucleo.

## Assumptions

- **Ground truth dell'audit (sessione 2026-06-17, ospite Copilot CLI 1.0.63):** i file hook Copilot sono in
  formato Claude (manca il campo di versione di schema, struttura annidata incompatibile, presenti i campi
  shell/messaggio-di-stato/timeout-Claude); lo script condiviso del controllo wiki emette il campo di
  messaggio di sistema Claude-only per stop e fine-sessione; l'avvio-sessione emette stringhe semplici; i
  comandi wiki/governance su CLI sono solo prompt-file (non invocabili); i custom-agent portano un campo di
  modello con valore Claude; i prompt-file usano la chiave di frontmatter Claude. Queste lacune sono
  precisamente ciò che la feature chiude.
- **Principio guida = supporto nativo, niente hack** (decisione utente 2026-06-17): riuso del CONTENUTO,
  traduzione nativa del CONTENITORE; FR-014 di FEAT-007 («script identici») rilassato a «corpo condiviso,
  output nativo per assistente via parametro d'invocazione».
- **Q1–Q6 risolte e non riaperte:** Q1=(b) avvio-sessione nativo per target; Q2=(c) piano comandi per-target
  (VS Code prompt-file + CLI custom-agent); Q3=(b) stop non-bloccante (decisione "consenti" + motivazione);
  Q4=(b) script condiviso con output nativo per assistente via parametro, no dual-field; Q5=incluso la
  verifica empirica del target MCP della CLI; Q6=(a) omettere il campo di modello Claude nei custom-agent.
- **[ASSUNTO] A-1:** client target = GitHub Copilot in VS Code agent mode e Copilot CLI 1.0.x; il Copilot
  coding agent cloud è fuori scope (come in FEAT-007).
- **[ASSUNTO] A-2:** lo schema Copilot con campo di versione e struttura hook descritta nell'audit è quello
  della versione CLI 1.0.63; versioni future potrebbero richiedere aggiornamenti (assorbiti dal seam per
  assistente).
- **[ASSUNTO] A-3:** l'evento di stop Copilot è l'equivalente dell'evento Stop di Claude; i nomi in forma
  cammello sono accettati come alias.
- **[ASSUNTO] A-4 (coerente col codice):** il seam di profilo-assistente già mappa la configurazione MCP del
  target CLI sul file a livello di repository con la chiave radice standard; FR-020 chiede di documentare la
  prova empirica e correggere solo se smentita — non si assume nuova rete di test runtime.
- **Verifica empirica runtime (smoke-test su ospite reale)**: necessaria ma **fuori ambito** come requisito
  di prodotto — è validazione operativa; la suite di test di prodotto è strutturale e gira offline.
- **Fuori ambito (capacità future / asse diverso):** nuove superfici o capacità non presenti in
  FEAT-007/009; provider/store backend del nucleo (invariato); funzionamento interno di spec-kit (upstream);
  supporto Codex (era Could in FEAT-007); Copilot come provider LLM (asse diverso); pubblicazione pubblica.
- **Nodi di DESIGN aperti (→ `/speckit-plan`, NON ambiguità di cosa/perché, NON riaprono Q1–Q6):** (1) il
  meccanismo nativo esatto di iniezione contesto all'avvio-sessione su Copilot VS Code (il tipo "prompt" è
  solo-CLI) richiede verifica empirica in fase di design; (2) l'eventuale **revisione del seam di
  profilo-assistente / superficie** se non produce artefatti nativi per ogni superficie (revisione
  architetturale autorizzata dall'utente) — oggi il seam rende prompt-file per **entrambi** i target Copilot
  e copia il campo di modello, quindi va esteso/rivisto per il piano comandi per-target e l'omissione del
  modello.
