# Feature Specification: Embedder locale (local-first per indicizzazione, eval e CI) (FEAT-011)

**Feature Branch**: `068-embedder-locale` · **Created**: 2026-06-21 · **Status**: Draft

<!-- Deriva da: FEAT-011 (epica sertor-core) -->

**Input**: Deriva da `requirements/sertor-core/embedder-locale/requirements.md` (FEAT-011, epica
`sertor-core`; 62 REQ EARS, gruppi A–G; RNF-1..6; rischi R-1..R-6; MoSCoW §9). Vedi anche
`requirements/sertor-core/epic.md` (FEAT-011 nel backlog) e l'epica a valle `debito-tecnico` FEAT-003 (la
CI che consuma il determinismo di questa feature). La feature dota Sertor di un **profilo davvero
local-first** (zero-modello, zero-credenziali) per indicizzare e cercare **da subito**, con un percorso di
upgrade pulito verso Ollama/Azure.

---

> **Perché serve (problema).** Per **indicizzare** un progetto Sertor serve **sempre** un provider di
> embeddings: la pipeline embedda i chunk per popolare il vector store. Oggi i due provider disponibili —
> **Ollama** (modello locale) e **Azure OpenAI** (cloud) — richiedono, in molti contesti **enterprise**,
> cicli di **autorizzazione, security/legal review, budget**: installare/eseguire un model server *oppure*
> ottenere credenziali e quota cloud. Finché quei cicli non si chiudono, **Sertor non si può nemmeno
> avviare** — senza embedder non c'è indice, senza indice non c'è retrieval. Manca un provider
> **deterministico, senza modello e senza credenziali** che permetta di partire subito.

> **Valore (esito per lo stakeholder).** Un operatore ospite in contesto vincolato **indicizza e cerca con
> un solo comando**, su una macchina senza Ollama e senza credenziali cloud, e fa l'**upgrade pulito** a
> Ollama/Azure quando le autorizzazioni arrivano — solo cambiando una manopola, senza toccare codice. Il
> legale/security dell'ospite approva gli artefatti senza review onerose (licenza e provenienza pulite).
> Beneficio collaterale: il **gate di non-regressione dell'eval** diventa eseguibile **senza rete**,
> prerequisito della CI dell'epica `debito-tecnico`.

> **Confine vincolante (D↔N).** I provider locali sono **deterministici**: nessuna chiamata a un LLM, nessun
> modello da eseguire, nessuna rete nel percorso di embedding (salvo l'acquisizione una-tantum del file di
> vettori statici, legata alla sola prima indicizzazione). Il **core resta deterministico** e non invoca mai
> un LLM (confine D↔N). L'accesso alle capacità avviene **solo via vehicle** (CLI/MCP/composizione),
> Principio XI.

> **Additività (Principi I/III, local-first).** La feature è **additiva**: si innesta nel solo composition
> root + nuovi adapter dietro la porta `EmbeddingProvider` esistente. I provider **esistenti (Ollama/Azure)
> restano invariati** quando non si seleziona un provider locale; porta, servizi ed engine **non cambiano**.

> **Ancoraggio all'esistente (dato di partenza, non dettaglio da progettare).** La porta `EmbeddingProvider`
> esiste già (`domain/ports.py`), così come `build_embedder`/`build_store` nel composition root e il
> namespacing degli indici per `(corpus, provider)` via `collection_name()`. Questa feature **aggiunge due
> adapter** dietro quella porta e una **manopola di selezione dedicata**. I riferimenti a file/simboli
> servono ad **ancorare** i requisiti all'esistente, non a prescrivere il *come* (nomi di classi, algoritmi,
> struttura della cache sono materia del plan).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Indicizzo e cerco senza alcun provider configurato (P1, Must)
Operatore ospite in contesto enterprise vincolato (niente Ollama installato, niente credenziali cloud,
nessuna configurazione di provider): vuole **valore immediato**. Installa Sertor, lancia l'indicizzazione e
la ricerca con un solo comando e ottiene un indice utile **subito**, senza modificare codice e senza
attendere cicli di autorizzazione.

**Independent Test**: su una macchina priva di Ollama, senza credenziali cloud e senza alcuna manopola di
provider impostata, indicizzare e cercare un piccolo corpus **riesce** con un solo comando; i risultati sono
non vuoti e pertinenti per query in linguaggio naturale (default a vettori statici).

**Acceptance**:
1. **Given** una macchina senza Ollama, senza credenziali cloud e senza provider configurato, **When**
   indicizzo e cerco un corpus, **Then** entrambi riescono con un solo comando, senza modificare codice.
2. **Given** nessun provider esplicitamente configurato, **When** il sistema sceglie il provider, **Then**
   usa il provider a **vettori statici (GloVe)** come **default**.
3. **Given** un provider locale selezionato, **When** la validazione statica della configurazione gira,
   **Then** **non** riporta campi obbligatori mancanti (un provider locale non blocca mai su credenziali).
4. **Given** le autorizzazioni cloud/Ollama arrivate, **When** seleziono Ollama o Azure tramite la sola
   manopola, **Then** l'upgrade avviene **senza modificare codice** e i due provider esistenti si comportano
   esattamente come oggi.

### User Story 2 — Indicizzo e cerco airgapped/offline, senza download (P1, Must)
Operatore in ambiente **airgapped/offline** (nessuna rete): deve poter indicizzare e cercare con **almeno
un** provider che non richieda **alcun download** né credenziali.

**Independent Test**: senza rete, selezionando il provider lessicale, indicizzare e cercare un corpus
**riesce** senza scaricare nulla; gli stessi input producono gli stessi vettori anche su una macchina
diversa e con una versione di Python diversa.

**Acceptance**:
1. **Given** una macchina senza rete, **When** seleziono il provider **lessicale** e indicizzo/cerco,
   **Then** funziona **senza alcun download** e senza credenziali.
2. **Given** il provider lessicale attivo, **When** indicizzo un corpus con identificatori di codice non
   presenti in alcun vocabolario, **Then** quei token **contribuiscono comunque segnale** (il vettore non è
   nullo per termini fuori vocabolario).
3. **Given** lo stesso testo, **When** lo embeddo in run diverse, su macchine diverse e con versioni di
   Python diverse, **Then** ottengo **vettori identici** (determinismo stabile, non legato a hashing
   salted/per-processo).
4. **Given** il provider lessicale come provider attivo, **When** uso il sistema, **Then** ricevo un
   **avviso** che la ricerca in linguaggio naturale è limitata e che GloVe/Ollama/Azure offrono semantica
   migliore.

### User Story 3 — Semantica NL locale di default con acquisizione on-demand (P1, Must)
Operatore di un host **doc-heavy** o profilo **doc-only**: vuole una semantica NL ragionevole **senza
cloud**. Alla **prima indicizzazione**, il sistema acquisisce on-demand il file di vettori statici
(scaricato una sola volta per macchina e condiviso fra tutti i progetti), poi indicizza e cerca con segnale
semantico; in airgapped fornisce il file da un percorso locale.

**Independent Test**: alla prima indicizzazione col default GloVe, in assenza del file in cache, il sistema
**scarica** il file ufficiale (con un avviso una-tantum sulla dimensione), poi indicizza; alla seconda
indicizzazione **riusa la cache senza ri-scaricare**; fornendo un percorso esplicito al file, **non** tenta
alcun download.

**Acceptance**:
1. **Given** il provider GloVe attivo e il file di vettori **assente dalla cache**, **When** indicizzo per la
   prima volta, **Then** il sistema **scarica** il file ufficiale **prima** di produrre i vettori, con un
   **avviso una-tantum** che è in corso il download di un file di grandi dimensioni (~822 MB).
2. **Given** il file scaricato, **When** indicizzo o cerco di nuovo (anche da un altro progetto sulla stessa
   macchina), **Then** il sistema **riusa la cache utente condivisa** senza ri-scaricare.
3. **Given** un **percorso esplicito** a un file di vettori locale (airgapped), **When** indicizzo, **Then**
   il sistema usa quel file e **non tenta alcun download**.
4. **Given** un token senza vettore GloVe (fuori vocabolario), **When** embeddo il testo, **Then** il
   sistema lo gestisce in modo **deterministico** senza far fallire la chiamata di embedding.
5. **Given** il file presente (in cache o fornito), **When** **installo** o **cerco** (cache già presente),
   **Then** il sistema **non scarica** nulla: l'acquisizione è legata alla sola indicizzazione.

### User Story 4 — Fallimento rumoroso e azionabile, mai degrado silenzioso (P1, Must)
Operatore con GloVe richiesto ma file assente dalla cache, nessun percorso fornito e rete non disponibile:
deve ricevere un **errore chiaro e azionabile** che nomina le vie d'uscita, **non** un fallimento silenzioso
né un degrado nascosto a un altro provider.

**Independent Test**: con GloVe richiesto, file assente, nessun percorso e nessuna rete, l'indicizzazione
**fallisce con un errore** che nomina sia l'override di percorso sia il fallback al provider lessicale; il
sistema **non** ripiega in silenzio su un altro provider; un valore di manopola non riconosciuto produce un
errore che nomina la manopola e i valori ammessi.

**Acceptance**:
1. **Given** GloVe richiesto, file assente dalla cache, nessun percorso impostato e nessuna rete, **When**
   indicizzo, **Then** il sistema **fallisce** con un errore azionabile che **nomina entrambe** le vie
   d'uscita (impostare il percorso GloVe esplicito, oppure selezionare il provider lessicale).
2. **Given** l'acquisizione o il caricamento del file GloVe che fallisce, **When** indicizzo, **Then** il
   sistema **espone l'errore esplicitamente** e **non** ripiega in silenzio su un altro provider.
3. **Given** un valore della manopola di selezione **non riconosciuto**, **When** il sistema configura il
   provider, **Then** solleva un **errore di configurazione azionabile** che nomina la manopola e i valori
   ammessi.
4. **Given** una selezione o un'acquisizione di provider, **When** avviene, **Then** l'esito è registrato
   come **evento di osservabilità strutturato metrics-only** (nessun segreto, coerente con gli eventi
   esistenti).

### User Story 5 — La capacità è installabile su un ospite (P1, Must / corollario installabile)
Su un **progetto terzo** (non Sertor), dopo `sertor install`, l'operatore trova nel template `.env` le nuove
manopole (selezione del provider e override del percorso GloVe), la documentazione che descrive i quattro
provider e il nuovo default, e una **nota di migrazione** sul cambio di default.

**Independent Test**: su un host pulito, dopo `sertor install`, il template `.env` depositato contiene la
manopola di selezione del provider e l'override di percorso; la documentazione utente descrive i quattro
provider, il nuovo default e l'override airgapped, con una nota di migrazione esplicita.

**Acceptance**:
1. **Given** un host pulito dopo `sertor install`, **When** ispeziono il template `.env` depositato, **Then**
   contiene la **manopola di selezione del provider** di embeddings e l'**override del percorso GloVe**.
2. **Given** la documentazione utente, **When** la consulto, **Then** descrive i **quattro provider**, il
   **nuovo default**, l'**override di percorso** per airgapped e una **nota di migrazione** che dichiara che
   il default è cambiato (prima il local-first implicava Ollama; ora è il provider a vettori statici;
   Ollama/Azure vanno selezionati esplicitamente).
3. **Given** un provider locale non selezionato, **When** uso Ollama/Azure come oggi, **Then** comportamento
   e **costo** restano **identici a oggi** (additività, Principi I/III).

### Edge Cases
- **Nessun provider configurato** — il sistema usa il **default GloVe** e indicizza/cerca con un solo
  comando (non un errore «manca un provider»). *(REQ-002, CS-1)*
- **Airgapped totale** — esiste **almeno un** provider (il lessicale) che funziona **senza alcun download**.
  *(REQ-010, CS-2)*
- **Token fuori vocabolario (GloVe)** — gestito in modo deterministico, **senza far fallire** l'embedding.
  *(REQ-023)*
- **Identificatori di codice (lessicale)** — i char-n-gram fanno sì che i token OOV **contribuiscano
  comunque segnale**. *(REQ-011)*
- **GloVe richiesto ma assente, nessun percorso, nessuna rete** — **fallimento azionabile** che nomina
  override-path e fallback lessicale; **mai** degrado silenzioso. *(REQ-040, CS-5)*
- **Errore di download/caricamento GloVe** — esposto esplicitamente, **nessun** ripiego silenzioso ad altro
  provider. *(REQ-041)*
- **Valore di manopola non riconosciuto** — errore di configurazione che **nomina** manopola e valori
  ammessi. *(REQ-003)*
- **Hashing salted di default di Python** — il lessicale **non** vi si appoggia: determinismo
  cross-macchina/cross-Python garantito. *(REQ-013, R-4)*
- **Mescolanza di vettori di provider diversi** — impedita dal namespacing `(corpus, provider)`: dimensioni
  e semantiche diverse non si mischiano nella stessa collezione. *(REQ-051, R-6)*
- **Cambio di default sorprende un ospite esistente** — mitigato da nota di migrazione e avviso esplicito.
  *(REQ-061, R-2)*
- **Costo del provider locale** — nessun costo monetario; il download GloVe è una-tantum per-macchina.
  *(RNF-6)*

## Requirements *(mandatory)*
Fonte autorevole: `requirements/sertor-core/embedder-locale/requirements.md` (REQ-001..062, gruppi A–G;
RNF-1..6; rischi R-1..6). In sintesi (mappatura per gruppo):

- **A — Selezione del provider (Must):** una **manopola di selezione dedicata** fra almeno **quattro** valori
  — i due nuovi locali (lessicale, vettori statici) e i due esistenti (Ollama, Azure) (REQ-001); **default**
  ai vettori statici (GloVe) quando nulla è configurato (REQ-002); valore non riconosciuto → **errore di
  configurazione azionabile** che nomina manopola e valori ammessi (REQ-003); la manopola è l'**unica**
  superficie di scelta del provider — **`RAG_BACKEND` è rimosso** e non più consultato (REQ-004); lo store ha
  la **sua** manopola con default sul local store (REQ-006); se `RAG_BACKEND` è ancora presente nell'ambiente,
  **avviso** che non è più onorato + nomi delle manopole sostitutive (REQ-007); con un provider locale
  selezionato, la validazione statica **non riporta campi obbligatori mancanti** (REQ-005).
- **B — Provider lessicale, pavimento zero-download (Must):** vettori prodotti con la **sola libreria
  standard**, senza modello, credenziali o rete (REQ-010); ogni vettore deriva da **char-n-gram** del testo,
  così i token fuori vocabolario (identificatori di codice) **contribuiscono segnale** (REQ-011); dimensione
  vettore **fissa e stabile**, nome provider stabile che la codifica (REQ-012); **determinismo** cross-run,
  cross-macchina, cross-Python (hashing stabile, non salted) (REQ-013); con il lessicale attivo, **avviso**
  che la ricerca NL è limitata e che GloVe/Ollama/Azure offrono semantica (REQ-014).
- **C — Provider a vettori statici GloVe, default (Must):** ogni embedding prodotto da **vettori GloVe
  pre-addestrati** (GloVe 6B, dimensione 300) **senza eseguire alcun modello** (REQ-020); vettore di testo
  composto **deterministicamente** dai vettori dei token (aggregazione), output stabile e dimensione fissa
  (REQ-021); nome provider stabile che codifica la dimensione, distinto dagli altri (REQ-022); token fuori
  vocabolario gestito **deterministicamente senza far fallire** la chiamata (REQ-023); dipendenza dal **solo
  file GloVe** e da dipendenze **importate lazily**, così selezionare un altro provider non scarica il file
  né importa quelle dipendenze (REQ-024).
- **D — Acquisizione e cache dei vettori statici (Must):** alla **prima indicizzazione** col file assente, il
  sistema **scarica** il file ufficiale prima di produrre vettori (REQ-030); conservato in una **cache utente
  condivisa per-macchina** (stile XDG), riusata fra progetti/corpora (REQ-031); con **percorso esplicito**
  fornito, il sistema usa quel file e **non scarica** (airgapped) (REQ-032); all'avvio del download, **avviso
  una-tantum** sulla dimensione (~822 MB) (REQ-033); **niente download né requisito del file all'install o in
  query** quando la cache esiste — l'acquisizione è legata all'indicizzazione (REQ-034); file in cache o
  fornito **riusato senza ri-scaricare** (REQ-035).
- **E — Diagnostica fail-loud, Principio XII (Must):** GloVe richiesto ma assente + nessun percorso + nessuna
  rete → **errore azionabile** che nomina **entrambe** le vie d'uscita (REQ-040); acquisizione/caricamento
  GloVe fallito → errore **esplicito**, **nessun** fallback silenzioso (REQ-041); selezione e acquisizione
  registrate come **eventi di osservabilità strutturati** coerenti con gli esistenti (metrics-only, no
  segreti) (REQ-042).
- **F — Determinismo, isolamento, non-regressione (Must):** entrambi i nuovi provider dietro la porta
  `EmbeddingProvider` **senza cambiare** porta, servizi o engine (REQ-050); vettori namespaced per
  `(corpus, provider)` così provider diversi (dimensioni/semantiche diverse) **non si mischiano** (REQ-051);
  comportamento di Ollama/Azure **invariato** quando un provider locale non è selezionato (REQ-052);
  lessicale **importabile e usabile senza alcun extra opzionale**, dipendenze dei vettori statici importate
  lazily (REQ-053).
- **G — Host / installabile (Must per 062; Should per 060/061):** l'installer include la manopola di
  selezione del provider e l'override del percorso GloVe nel template `.env` (REQ-060, Should); la
  documentazione utente descrive i quattro provider, il nuovo default, l'override airgapped e la **nota di
  migrazione** (REQ-061, Should); il percorso eval/CI ottiene il provider **via la composizione**
  (`build_embedder`), mai importando adapter fuori dai test — Principio XI (REQ-062, Must).

### Requisiti non funzionali (sintesi)
- **RNF-1 (determinismo):** output ripetibile a parità di input; lessicale deterministico anche
  cross-macchina/cross-Python (hashing stabile, non salted).
- **RNF-2 (isolamento dipendenze):** lessicale = sola stdlib; vettori statici = dipendenze **lazy**; il core
  resta importabile **senza** scaricare GloVe.
- **RNF-3 (local-first / privacy):** nessuna chiamata cloud e nessuna credenziale per i provider locali;
  nessun segreto negli eventi.
- **RNF-4 (non-regressione):** zero impatto su costo/comportamento dei provider esistenti quando non
  selezionati; nessuna modifica fuori da composition + nuovi adapter + Settings + (eventuale) superficie di
  validazione/errori.
- **RNF-5 (memoria):** footprint runtime del provider GloVe 300d nell'ordine atteso (≈ centinaia di MB),
  documentato; il lessicale ha footprint trascurabile.
- **RNF-6 (costo):** nessun costo monetario per i provider locali; il download GloVe è una-tantum
  per-macchina.

### Key Entities
- **Provider lessicale** *(adapter dietro `EmbeddingProvider`)* — produce vettori da char-n-gram del testo
  con la sola stdlib; zero-modello, zero-credenziali, zero-download; deterministico cross-macchina; dimensione
  fissa e nome stabile che la codifica. È il **pavimento** airgapped/offline/CI.
- **Provider a vettori statici (GloVe)** *(adapter dietro `EmbeddingProvider`, default)* — produce vettori da
  vettori GloVe pre-addestrati (6B, 300d, licenza PDDL/pubblico dominio) aggregando i vettori dei token, senza
  eseguire un modello; dipende dal solo file dati e da dipendenze importate lazily.
- **Manopola di selezione del provider** — configurazione **dedicata** e **unica** che sceglie fra i quattro
  provider (lessicale, vettori statici, Ollama, Azure); `RAG_BACKEND` **rimosso**; lo store ha la propria
  manopola (default local); default embedder = vettori statici.
- **File di vettori statici** *(artefatto dati, non versionato)* — il file GloVe ufficiale; conservato in una
  **cache utente condivisa per-macchina**, riusato fra progetti; fornibile da un **percorso esplicito** in
  airgapped.
- **Override del percorso GloVe** — configurazione che indica un file di vettori locale; quando presente,
  nessun download è tentato.
- **Esito di selezione/acquisizione** *(evento di osservabilità)* — registrazione metrics-only di quale
  provider è stato scelto e dell'esito dell'acquisizione, coerente con gli eventi esistenti; nessun segreto.
- **Errore azionabile (fail-loud)** — diagnostica che, quando un provider non può operare, **nomina le vie
  d'uscita** (override-path, fallback lessicale) e **mai** degrada in silenzio (Principio XII).

## Success Criteria *(mandatory)*
- **SC-001 (parte da subito, zero-config):** su una macchina senza Ollama, senza credenziali cloud e senza
  alcuna configurazione di provider, un ospite **indicizza e cerca** un corpus con un solo comando, senza
  modificare codice; il default è il provider a vettori statici. *(REQ-001/002/005; CS-1)*
- **SC-002 (airgapped):** in ambiente offline, **almeno un** provider (il lessicale) indicizza e cerca
  **senza alcun download** e senza credenziali. *(REQ-010; CS-2)*
- **SC-003 (determinismo):** a parità di input (testo, provider, dimensione, file di vettori) gli embeddings
  sono **deterministici e ripetibili**; per il lessicale anche **cross-macchina e cross-versione Python**.
  *(REQ-013/021; RNF-1; CS-3)*
- **SC-004 (selezione solo via config, esistenti invariati):** la scelta del provider avviene **solo via
  configurazione**; il comportamento e il **costo** di Ollama/Azure restano **invariati** quando non si
  seleziona un provider locale nuovo. *(REQ-001/004/052; RNF-4; CS-4)*
- **SC-005 (fail-loud):** quando un provider non può operare (es. GloVe richiesto, assente e senza rete), il
  sistema **fallisce in modo rumoroso e azionabile** nominando le vie d'uscita, **mai** in silenzio e **mai**
  degradando di nascosto a un altro provider; un valore di manopola non riconosciuto produce un errore che
  nomina manopola e valori ammessi. *(REQ-003/040/041; CS-5)*
- **SC-006 (acquisizione e cache):** alla prima indicizzazione GloVe il file è scaricato (con avviso
  una-tantum sulla dimensione); successivamente è **riusato dalla cache** condivisa senza ri-scaricare; con
  un percorso esplicito **nessun download** è tentato; install e query non scaricano il file. *(REQ-030..035)*
- **SC-007 (installabile):** su un host pulito, dopo `sertor install`, le manopole introdotte compaiono nel
  template `.env`, la documentazione utente descrive i quattro provider e il nuovo default, con **nota di
  migrazione** sul cambio di default. *(REQ-060/061; CS-6)*
- **SC-008 (via vehicle, niente LLM nel core):** il percorso eval/CI ottiene il provider **via la
  composizione** (`build_embedder`), mai importando adapter fuori dai test; il core resta deterministico e
  **non invoca mai un LLM**. *(REQ-062; Principio XI; confine D↔N)*
- **SC-009 (isolamento dipendenze):** il lessicale è usabile **senza alcun extra opzionale**; selezionare un
  provider diverso da GloVe **non** scarica il file GloVe né importa le sue dipendenze; il core è importabile
  senza scaricare nulla. *(REQ-024/053; RNF-2)*
- **SC-010 (segnale semantico/lessicale adeguato al ruolo):** il provider a vettori statici offre semantica
  NL locale utile per host doc-heavy/doc-only; il provider lessicale, attivo, **avvisa** che la ricerca NL è
  limitata e i token OOV (identificatori di codice) contribuiscono comunque segnale. *(REQ-011/014/020)*

## Assumptions
- **GloVe redistribuibile e raggiungibile.** Si assume che la distribuzione ufficiale GloVe 6B
  (`glove.6B.zip`, ~822 MB, contiene 50/100/200/300d) sia raggiungibile dalla sorgente PDDL e
  redistribuibile; in airgapped si usa l'override di percorso. *(Requisiti §7.)*
- **Default = GloVe 300d.** Il nuovo default è il provider a vettori statici GloVe 6B 300d (licenza
  PDDL/pubblico dominio), scelto per semantica NL pulita sul piano licenza/provenienza. *(Decisione utente,
  Requisiti §10.)*
- **Manopola dedicata e unica.** La selezione del provider usa una manopola **dedicata**
  (`SERTOR_EMBED_PROVIDER`, valori `glove|hash|ollama|azure`) come **unica** superficie; **`RAG_BACKEND` è
  rimosso** e lo store si sceglie con la propria manopola (default local). *(REQ-001/004/006/007; decisione
  utente "una sola configurazione"; il wiring di dettaglio è del plan.)*
- **«LLM» = agente dell'utente.** Coerente con la terminologia del workspace: nel core/CLI non esiste alcuna
  chiamata a un LLM; i provider locali sono puramente deterministici.
- **Distinzione da `FakeEmbedder`.** Il provider lessicale di **prodotto** (con segnale lessicale) è distinto
  dal mock di test `FakeEmbedder` (hash d'identità), che resta per i test.
- **Estensione, non reinvenzione.** La feature **estende** il composition root con due adapter dietro la
  porta esistente; porta, servizi ed engine restano invariati; il namespacing `(corpus, provider)` esistente
  separa i vettori.
- **Dipendenza installer.** La distribuzione su ospite riusa il percorso `sertor install` /
  `sertor-install-kit` (manopole nel template `.env`, documentazione, nota di migrazione).
- **Dipendenza a valle.** La CI col gate eval (epica `debito-tecnico` FEAT-003) consuma questa feature ma è
  **fuori ambito** qui.

### Fuori ambito (dichiarato)
- La **CI vera** (workflow `.github/workflows`) — appartiene all'epica `debito-tecnico` (FEAT-003); qui si
  consegnano provider + manopole + test + template installabili che la abilitano.
- **Altre fonti di vettori statici** oltre GloVe (word2vec, fastText, Model2Vec): scartate per
  licenza/provenienza (CC BY-SA, file non licenziati, web scraping) che reintrodurrebbero la frizione legale
  che la feature vuole eliminare — GloVe/PDDL è la scelta pulita.
- Qualsiasi **modello neurale locale** (sentence-transformers/torch): contraddice il vincolo zero-dipendenze.
- **Reranking, motori, code-graph**: non toccati (ortogonali).
- **Modifiche alla porta `EmbeddingProvider`, ai servizi o agli engine**: la feature è additiva e si innesta
  nel solo composition root + nuovi adapter.
- Il **come** (nomi esatti delle manopole, dimensione del vettore lessicale, algoritmo di aggregazione
  token→vettore, struttura della cache, verifica d'integrità del download): fase di **design/plan**.

> **Tracciamento dello scope (regola «gli Out-of-Scope si promuovono»).** Le voci **Could** dei requisiti —
> dimensione GloVe configurabile oltre il default 300d, verifica d'integrità (checksum) del file scaricato,
> helper CLI esplicito di pre-download — sono già registrate nella MoSCoW dei requisiti
> (`requirements/sertor-core/embedder-locale/requirements.md` §9) e nel backlog d'epica
> (`requirements/sertor-core/epic.md`). La CI vera è già FEAT-003 dell'epica `debito-tecnico`. Al `plan`, se
> una di queste cresce in capacità reale, resta tracciata lì; nessun rinvio reale vive solo dentro `specs/`.

### Forche di design (NON risolte qui — per `/speckit-plan`)
Sono questioni di **come**, fuori dal *cosa/perché* della spec; menzionate per non seppellirle. **Le forche
di scope sono già decise** (vedi riquadro sotto) e **non** sono qui.
- **Dimensione del vettore lessicale** e algoritmo di char-n-gram (quale n, quale tecnica di hashing stabile,
  quale dimensione fissa). *(Design.)*
- **Algoritmo di aggregazione token→vettore** per GloVe (media? somma normalizzata? pesatura?). *(Design.)*
- **Struttura della cache** e layout su disco (directory XDG, nome file, gestione concorrenza dei download).
  *(Design.)*
- **Forma esatta dell'evento di osservabilità** per selezione/acquisizione (campi metrics-only). *(Design.)*
- **Sorgente di download** concreta del file GloVe e gestione di proxy/rete vincolata. *(Design.)*

> **Decisioni di scope già risolte (utente) — riportate come vincoli, NON come domande.**
> **Scope:** due provider locali deterministici dietro la porta esistente. **Default:** `glove` (vettori
> statici GloVe 6B 300d). **Sorgente/licenza:** GloVe 6B 300d, PDDL/pubblico dominio. **Manopola:**
> dedicata `SERTOR_EMBED_PROVIDER` (`glove|hash|ollama|azure`), **unica** superficie; **`RAG_BACKEND`
> rimosso**, store via `SERTOR_STORE_BACKEND` (default local). **Distribuzione vettori:** download alla prima indicizzazione + cache utente condivisa
> per-macchina + override di percorso (airgapped). **Fail-loud:** errore azionabile che nomina override-path
> e fallback lessicale; mai degrado silenzioso (Principio XII). **Confine D↔N:** core deterministico, nessun
> LLM nel core; accesso via vehicle (Principio XI).
