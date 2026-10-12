# Feature Specification: Pagine ASP.NET nel corpus, con il codice lato server che contengono

**Feature Branch**: `140-pagine-aspnet`

**Created**: 2026-10-12

**Status**: Draft

**Deriva da**: E7-FEAT-006 (epica `ingestione-estesa`) · **Requisiti**: [`requirements/ingestione-estesa/pagine-aspnet/requirements.md`](../../requirements/ingestione-estesa/pagine-aspnet/requirements.md)

**Input**: indicizzare le pagine ASP.NET — WebForms (`.aspx`, `.ascx`, `.master`, `.asmx`, `.ashx`) e
Razor (`.cshtml`, `.razor`) — estraendo il codice C# lato server scritto dentro le pagine, con numeri di
riga riferiti al file originale, così che i metodi inline diventino simboli navigabili e il markup resti
ricercabile; degradazione dichiarata per le pagine che non si possono analizzare.

---

## Perché questa feature esiste

La missione di Sertor è rendere all'agente un corpus in cui **codice e documentazione** stanno insieme.
In un progetto ASP.NET il codice stesso è diviso in due: il code-behind (`Pagina.aspx.cs`) e la pagina,
che contiene il markup dell'interfaccia e spesso anche **codice lato server scritto inline**.

Oggi Sertor indicizza il code-behind e **ignora la pagina**, senza dirlo. Un agente che chiede «dove è
definito `BindGrid`?» riceve «non esiste» se il metodo è scritto in un blocco della pagina; un agente che
chiede «chi usa questo metodo del code-behind?» non vede la pagina che lo invoca. La parte di progetto
visibile sembra completa, ed è per questo che l'errore non si nota. È il secondo caso, dopo Rust, di un
difetto più generale già tracciato: un'omissione non dichiarata diventa una risposta falsa.

## Clarifications

### Session 2026-10-12

- Q: Il codice estratto deve comparire anche nelle unità di testo del markup? → A: No. Nelle unità del
  markup i blocchi di codice sono sostituiti da righe vuote (le righe del file restano allineate); ogni
  riga di codice compare una sola volta, nell'unità del suo simbolo.
- Q: Che nome qualificato riceve un metodo scritto in una pagina senza una classe che lo racchiuda? →
  A: Nome del file senza estensioni + nome del metodo (`Default.aspx` → `Default.Page_Load`); vale per
  entrambe le famiglie.
- Q: Cosa producono le espressioni brevi lato server (`<%= %>`, `<%: %>`, `<%# %>`)? → A: Solo relazioni
  di chiamata; il loro testo resta nelle unità del markup, nessuna unità propria.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Le pagine entrano nel corpus e il loro testo si trova (Priority: P1)

Un ospite con un progetto ASP.NET indicizza il proprio repository. Le pagine di entrambe le famiglie
entrano nel corpus, e una ricerca su un testo che compare solo in una pagina — l'identificativo di un
controllo, un'etichetta, un binding — la restituisce.

**Why this priority**: senza questo la pagina non esiste per l'agente; ogni altra capacità ne dipende.

**Independent Test**: indicizzare un repository di prova con un file per ciascuna delle sette estensioni
e cercare un testo presente solo nel markup di una pagina.

**Acceptance Scenarios**:

1. **Given** un repository con un file per ciascuna delle sette estensioni, **When** viene indicizzato,
   **Then** tutti e sette compaiono nel corpus come codice, con il loro percorso relativo come identità.
2. **Given** una pagina con un controllo identificato da un nome che non compare altrove, **When** si
   cerca quel nome, **Then** la pagina è fra i risultati.
3. **Given** una pagina senza alcun codice lato server, **When** viene indicizzata, **Then** entra nel
   corpus senza errori.
4. **Given** un file di code-behind `Pagina.aspx.cs`, **When** il repository viene indicizzato, **Then**
   il file è indicizzato come prima della feature.

---

### User Story 2 - I metodi scritti nelle pagine si trovano, alla riga giusta (Priority: P1)

L'agente chiede dove è definito un metodo scritto in un blocco di codice lato server di una pagina
(WebForms o Razor). Riceve la pagina e la riga esatta in cui il metodo inizia nel file originale, e il
contenuto del metodo è recuperabile come unità.

**Why this priority**: è la scelta esplicita dell'utente (estrarre il C# inline) ed è ciò che distingue
questa feature da un'indicizzazione del solo testo. Una riga sbagliata renderebbe falsa ogni citazione.

**Independent Test**: una pagina di prova per famiglia, con metodi in posizioni note; interrogare la
definizione di ciascun metodo e confrontare percorso e riga con il file.

**Acceptance Scenarios**:

1. **Given** una pagina WebForms con un metodo dentro un blocco di script lato server, **When** l'agente
   cerca la definizione del metodo, **Then** riceve il percorso della pagina e la riga reale di inizio.
2. **Given** un componente Razor con un metodo in un blocco di codice, **When** l'agente cerca la
   definizione, **Then** riceve il percorso del componente e la riga reale di inizio.
3. **Given** una pagina con più blocchi di codice separati da markup, **When** viene indicizzata,
   **Then** le righe di ogni simbolo restano corrette anche per i blocchi successivi al primo.

---

### User Story 3 - Chi chiama cosa, fra pagine e code-behind (Priority: P2)

L'agente chiede chi invoca un metodo del code-behind. Fra le risposte c'è la pagina che lo chiama da un
blocco di codice o da un'espressione lato server.

**Why this priority**: completa la navigazione, ma la ricerca della definizione (US2) ha già valore da sola.

**Independent Test**: una pagina che invoca un metodo definito nel proprio code-behind; interrogare i
chiamanti del metodo.

**Acceptance Scenarios**:

1. **Given** una pagina che invoca un metodo del code-behind da un blocco di codice, **When** l'agente
   chiede chi chiama quel metodo, **Then** la pagina è fra i chiamanti.
2. **Given** un nome di metodo definito in così tanti punti da superare la soglia di ambiguità del
   sistema, **When** l'agente chiede chi lo chiama, **Then** il sistema applica la stessa regola già in
   uso per gli altri linguaggi, senza produrre archi dubbi.

---

### User Story 4 - Ciò che non si può analizzare si dichiara (Priority: P1)

Una pagina scritta in VB.NET, o con codice lato server che non si riesce ad analizzare, entra comunque
nel corpus come testo; la telemetria registra un evento che nomina il file e il motivo, così nessuno
scambia l'assenza di simboli per assenza di codice.

**Why this priority**: è la regola del progetto (*fail loud*) e il motivo stesso per cui la feature
nasce; una degradazione silenziosa ripeterebbe il difetto che si vuole chiudere.

**Independent Test**: una pagina VB.NET e una con un blocco C# malformato; verificare che entrambe siano
nel corpus e che per ciascuna sia stato emesso un evento con file e motivo.

**Acceptance Scenarios**:

1. **Given** una pagina che dichiara VB come linguaggio, **When** viene indicizzata, **Then** è nel
   corpus come testo e viene emesso un evento con il file e il linguaggio dichiarato.
2. **Given** una pagina con un blocco di codice lato server malformato, **When** viene indicizzata,
   **Then** è nel corpus e viene emesso un evento con il file e il motivo.

---

### User Story 5 - La copertura è dichiarata (Priority: P2)

Chi interroga il sistema sulla propria copertura vede quali relazioni sono supportate per le due nuove
famiglie, come per gli altri linguaggi.

**Why this priority**: rende onesta l'assenza di relazioni che la feature non produce.

**Independent Test**: leggere la dichiarazione di copertura dopo la feature e verificare le due voci.

**Acceptance Scenarios**:

1. **Given** la feature consegnata, **When** si consulta la dichiarazione di copertura del grafo,
   **Then** compaiono le famiglie WebForms e Razor con le relazioni effettivamente supportate.

---

### Edge Cases

- **File con BOM UTF-8**: il primo simbolo e i numeri di riga non devono spostarsi.
- **Espressioni brevi** (`<%= Titolo %>`) che non sono unità sintattiche complete: vanno analizzate
  senza produrre errori né simboli fittizi.
- **`@` come testo in Razor** (indirizzi email, `@@`): non deve essere scambiato per l'inizio di un blocco.
- **Blocchi annidati o parentesi graffe dentro stringhe** nei blocchi Razor: il blocco deve chiudersi
  alla graffa giusta.
- **Stesso nome di metodo in molte pagine** (`Page_Load`): ogni pagina ha il suo simbolo, distinto dal
  nome qualificato (`Default.Page_Load`, `Ordini.Page_Load`); la navigazione per nome segue la soglia di
  ambiguità esistente.
- **Pagine con lo stesso nome in cartelle diverse** (`Admin/Default.aspx`, `Default.aspx`): il nome
  qualificato coincide, ma i simboli restano distinti perché la loro identità include il percorso.
- **Pagina molto grande**: il contenuto viene comunque spezzato in unità di dimensione gestibile.
- **Indicizzazione incrementale**: modificare solo una pagina aggiorna solo quella pagina.
- **Code-behind VB** (`.aspx.vb`): resta fuori dal corpus, come oggi (estensione non supportata).

## Requirements *(mandatory)*

### Functional Requirements

**Ingestione**
- **FR-001**: Il sistema MUST includere nel corpus, come documenti di codice, i file con estensione
  `.aspx`, `.ascx`, `.master`, `.asmx`, `.ashx`, `.cshtml`, `.razor`, con il percorso relativo come
  identità stabile. *(REQ-001)*
- **FR-002**: Il sistema MUST registrare per ciascuno di questi documenti un'identità di linguaggio che
  distingua la famiglia WebForms dalla famiglia Razor. *(REQ-002)*
- **FR-003**: Il sistema MUST continuare a indicizzare i file di code-behind C# esattamente come prima.
  *(REQ-003)*

**Estrazione del codice lato server**
- **FR-004**: Per le pagine WebForms, il sistema MUST estrarre il C# contenuto nei blocchi di script lato
  server, nei blocchi di codice e nelle espressioni lato server (di output, di output codificato e di
  data-binding). Per gli handler e i web service (`.ashx`, `.asmx`), dove tutto ciò che segue la direttiva
  iniziale è codice, il sistema MUST trattare come C# l'intero contenuto dopo la direttiva. *(REQ-004)*
- **FR-005**: Per le pagine Razor, il sistema MUST estrarre il C# contenuto nei blocchi `@code`,
  `@functions` e `@{ }`. *(REQ-005)*
- **FR-006**: Il sistema MUST riferire ogni simbolo e ogni unità di testo derivata dal codice estratto
  alle righe del file originale della pagina. *(REQ-006)*
- **FR-006a**: I blocchi di codice (script lato server, blocchi di codice, blocchi Razor) MUST produrre
  unità di testo per simbolo; le espressioni brevi lato server MUST NOT produrre unità di testo proprie e
  contribuiscono solo alle relazioni di chiamata (FR-008).

**Simboli e navigazione**
- **FR-007**: Il sistema MUST esporre classi, metodi e funzioni definiti nel codice estratto come simboli
  del grafo il cui percorso è la pagina. *(REQ-007)*
- **FR-007a**: Un simbolo definito fuori da qualunque classe dichiarata nel blocco MUST ricevere come nome
  qualificato il nome del file senza estensioni seguito dal nome del simbolo (`Default.aspx` →
  `Default.Page_Load`; `Counter.razor` → `Counter.IncrementCount`). Un simbolo dentro una classe dichiarata
  nel codice della pagina (es. la classe di un handler `.ashx`) segue la regola già in uso per il C#, senza
  prefisso: la stessa classe ha lo stesso nome qualificato ovunque sia scritta.
- **FR-008**: Il sistema MUST derivare le relazioni di chiamata dal codice estratto — blocchi ed
  espressioni brevi — verso i simboli del corpus, applicando la soglia di ambiguità dei nomi già in uso.
  *(REQ-008)*
- **FR-009**: Il sistema MUST dichiarare, insieme alla copertura degli altri linguaggi, le relazioni
  supportate per le famiglie WebForms e Razor. *(REQ-009)*

**Markup e degradazione dichiarata**
- **FR-010**: Il sistema MUST rendere ricercabile il markup di ogni pagina, così che un testo presente
  solo fuori dai blocchi di codice sia recuperabile. Le unità di testo del markup MUST NOT contenere il
  codice dei blocchi estratti (sostituito da righe vuote, così le righe del file restano allineate); il
  testo delle espressioni brevi resta nel markup. *(REQ-010)*
- **FR-011**: Se una pagina dichiara un linguaggio lato server diverso da C#, il sistema MUST
  indicizzarla come solo testo ed emettere un evento osservabile che nomina il file e il linguaggio.
  *(REQ-011)*
- **FR-012**: Se il codice estratto di una pagina non si può analizzare, il sistema MUST indicizzare la
  pagina come testo ed emettere un evento osservabile che nomina il file e il motivo. *(REQ-012)*
- **FR-013**: Se una pagina non contiene codice lato server, il sistema MUST indicizzarla come testo
  senza segnalare errori. *(REQ-013)*

**Proprietà della pipeline**
- **FR-014**: Il sistema MUST produrre unità di testo, identità e grafo identici per lo stesso contenuto
  di pagina in ricostruzioni successive, sia nell'indicizzazione completa sia in quella incrementale.
  *(REQ-015)*
- **FR-015**: Il sistema MUST lasciare invariata l'indicizzazione di tutti i file non ASP.NET.
- **FR-016**: La documentazione che descrive cosa entra nel corpus MUST elencare le nuove estensioni e
  correggere l'affermazione oggi falsa secondo cui qualunque altro linguaggio verrebbe indicizzato con
  il fallback.

### Key Entities

- **Pagina ASP.NET**: un file del corpus che mescola markup e codice lato server; ha un percorso, una
  famiglia (WebForms o Razor) e un linguaggio lato server dichiarato (C# per default).
- **Blocco di codice lato server**: un tratto della pagina che contiene C#, con la sua posizione nel file
  originale (righe di inizio e fine) e il suo tipo (script, blocco, espressione, blocco Razor).
- **Simbolo inline**: classe, metodo o funzione definita in un blocco; appartiene alla pagina e ha la
  riga di inizio nel file originale.
- **Evento di degradazione**: segnalazione osservabile che una pagina è stata indicizzata solo come
  testo, con file e motivo (linguaggio non C#, codice non analizzabile).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Su un repository di prova con un file per ciascuna delle 7 estensioni, **7 su 7** file sono
  nel corpus dopo l'indicizzazione.
- **SC-002**: Per ogni metodo definito inline nelle pagine di prova (almeno uno per famiglia, incluso un
  metodo in un blocco successivo al primo), la ricerca della definizione restituisce la pagina e una riga
  di inizio con **scarto 0** dalla riga reale.
- **SC-003**: La ricerca dei chiamanti di un metodo del code-behind invocato da una pagina di prova
  restituisce quella pagina.
- **SC-004**: Una ricerca su un testo presente solo nel markup di una pagina di prova restituisce la
  pagina fra i primi 5 risultati.
- **SC-005**: Per le pagine di prova non analizzabili (una VB.NET, una con C# malformato), **2 su 2** sono
  nel corpus e **2 su 2** hanno prodotto un evento con file e motivo: **0** degradazioni silenziose.
- **SC-006**: Tutti i test esistenti continuano a passare e, sul corpus del progetto stesso (che non
  contiene pagine ASP.NET), identità e unità di testo dei file già indicizzati non cambiano.

## Assumptions

- **Linguaggio delle pagine**: la grande maggioranza delle pagine reali è in C#; VB.NET resta fuori
  dall'estrazione (dichiarato, non silenzioso). Un supporto VB sarebbe una voce separata.
- **JavaScript lato client** nei blocchi di script non lato server resta testo del markup.
- **Espressioni Razor inline** (`@Model.Nome`) fuori dai blocchi elencati restano testo e non producono
  relazioni.
- **Relazioni fra file** (pagina ↔ code-behind, master page ↔ pagine, controlli registrati): fuori da
  questa specifica; la richiesta corrispondente (REQ-014, *Could*) resta nel backlog dell'epica.
- **Installabilità**: la capacità viaggia con il pacchetto del core e raggiunge gli ospiti con un
  rilascio; non introduce artefatti d'installazione nuovi (la logica d'installazione è congelata).
- **Nessuna dipendenza nuova obbligatoria**: l'analisi del C# riusa il supporto già presente per i file
  `.cs`.
- **Nessuna pagina ASP.NET nel corpus del progetto**: la verifica sul dogfood riguarda la non-regressione;
  la verifica della capacità avviene su fixture dedicate.
- **Degradazione e duplicati**: quando una pagina è indicizzata solo come testo (FR-011/FR-012), il codice
  resta nelle sue unità di testo — non esistendo unità sintattiche, non c'è nulla da duplicare.
