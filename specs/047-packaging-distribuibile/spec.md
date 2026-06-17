# Feature Specification: Packaging distribuibile (distribuzione interim `git+url`)

**Feature Branch**: `047-packaging-distribuibile`

**Created**: 2026-06-17

**Status**: Draft

**Input**: Deriva da `requirements/sertor-cli/packaging-distribuibile/requirements.md` (FEAT-001, epica
`sertor-cli` — parte packaging/distribuzione, Must). Decisioni utente D1 (licenza MIT + file LICENSE) e
D2 (ambito = formalizzare la distribuzione interim `git+url`, NON PyPI) prese in elicitazione; 4 domande
di scope risolte (DA-P1..P4). Ground truth di build verificata a monte dal flusso principale (vedi
*Assumptions*).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Installare il prodotto su un ambiente vergine con un solo comando (Priority: P1)

Un installatore (l'owner o un membro del team interno) parte da un ambiente pulito e vuole portare Sertor
su un repository ospite. Con **un singolo comando** ottiene il prodotto dalla sorgente di distribuzione
interim e si ritrova i punti d'ingresso pronti all'uso, senza passi manuali aggiuntivi e senza dover
attingere a un indice pubblico di pacchetti.

**Why this priority**: È il valore terminale della feature e il criterio con cui l'epica considera "fatto"
il packaging: una capacità non è consegnata finché un ospite non può ottenerla e usarla attraverso il
percorso d'installazione. Senza questa storia il packaging resta un prototipo che funziona "per prova".

**Independent Test**: Su un venv/ambiente effimero e pulito, eseguire il comando d'installazione dalla
sorgente interim e verificare che il punto d'ingresso del prodotto risponda a un'invocazione di
aiuto/versione restituendo successo.

**Acceptance Scenarios**:

1. **Given** un ambiente vergine, **When** l'installatore esegue il singolo comando d'installazione del
   prodotto installer, **Then** il relativo punto d'ingresso è disponibile e invocabile senza passi
   manuali ulteriori.
2. **Given** un ambiente vergine, **When** l'installatore esegue il singolo comando d'installazione del
   prodotto di governance, **Then** il relativo punto d'ingresso è disponibile e invocabile.
3. **Given** un'installazione dalla sorgente interim, **When** il prodotto viene risolto, **Then** le sue
   dipendenze interne sono soddisfatte dalla stessa sorgente, senza richiedere un indice pubblico di
   pacchetti.

---

### User Story 2 - Avere un prodotto distribuibile coerente sul piano legale e dei metadati (Priority: P1)

Un consumatore del prodotto distribuito (o un revisore) apre l'artefatto e trova **coerenza**: la licenza
dichiarata è accompagnata dal testo della licenza, e i metadati riportano i riferimenti essenziali (nome,
versione, autori, licenza, indirizzo del repository, descrizione). Non c'è promessa di licenza senza testo
né campo essenziale mancante.

**Why this priority**: La distribuzione di un artefatto che dichiara una licenza senza spedirne il testo è
un'incoerenza legale; metadati incompleti privano il consumatore dei riferimenti minimi. È parte
integrante del "distribuibile", non un abbellimento.

**Independent Test**: Per ogni prodotto distribuibile, ispezionare l'artefatto prodotto e verificare la
presenza del testo della licenza e dei campi di metadati essenziali; per i prodotti user-facing,
verificare anche i campi di riferimento aggiuntivi.

**Acceptance Scenarios**:

1. **Given** un prodotto distribuibile, **When** se ne ispeziona l'artefatto, **Then** esso contiene il
   testo della licenza MIT, coerente con la licenza dichiarata nei suoi metadati.
2. **Given** un prodotto user-facing, **When** se ne ispezionano i metadati, **Then** sono presenti nome,
   versione, descrizione, autori, licenza e indirizzo del repository.
3. **Given** i quattro prodotti del workspace, **When** se ne confrontano le versioni, **Then** riportano
   un'unica versione di prodotto allineata.

---

### User Story 3 - Verificare in modo ripetibile che il packaging regga (Priority: P1)

L'owner vuole una **prova ripetibile** — eseguibile nella CI locale, senza credenziali cloud né accesso a
indici pubblici di pacchetti — che ogni prodotto distribuibile si costruisca correttamente, che gli
artefatti contengano ciò che devono (incluso il testo della licenza e gli asset richiesti
dall'installazione) e che l'install pulito a un comando funzioni. Quando qualcosa non torna, la verifica
fallisce indicando il prodotto e il percorso problematico.

**Why this priority**: Senza una verifica ripetibile, la coerenza appena raggiunta degrada silenziosamente
alla prossima modifica. La prova trasforma "funziona oggi per fortuna" in "verificato a ogni cambiamento".

**Independent Test**: Eseguire la verifica di build/install su un ambiente isolato e confermare che produce
gli artefatti attesi e segnala in modo non ambiguo eventuali fallimenti (prodotto + percorso).

**Acceptance Scenarios**:

1. **Given** i prodotti distribuibili, **When** si esegue la verifica di build, **Then** per ciascuno sono
   prodotti gli artefatti di distribuzione attesi senza errori e con i contenuti richiesti.
2. **Given** un prodotto che dichiara una licenza senza spedirne il testo, **When** si esegue la verifica,
   **Then** la verifica fallisce.
3. **Given** un campo di metadati essenziale mancante in un prodotto distribuibile, **When** si esegue la
   verifica, **Then** la verifica fallisce.
4. **Given** un fallimento di build/install, **When** si esegue la verifica, **Then** essa identifica il
   prodotto e il gestore d'installazione coinvolti e termina con esito di errore.

---

### User Story 4 - Trovare nella documentazione come installare (Priority: P2)

Un installatore consulta la guida d'installazione e trova il comando esatto per la distribuzione interim
per **entrambi** i gestori supportati, i prerequisiti, quali sono i prodotti che si installano
direttamente e quali sono dipendenze interne, e la dichiarazione esplicita che la pubblicazione pubblica
è fuori ambito.

**Why this priority**: La capacità è davvero consegnata solo se è raggiungibile da chi non l'ha costruita;
la guida è il ponte. È P2 perché segue (ma completa) la capacità tecnica delle storie P1.

**Independent Test**: Leggere la guida e seguire alla lettera il comando documentato per ciascun gestore su
un ambiente pulito, verificando che porti a un'installazione funzionante.

**Acceptance Scenarios**:

1. **Given** la guida d'installazione, **When** la si consulta, **Then** essa riporta il comando esatto
   della distribuzione interim per entrambi i gestori supportati, con i prerequisiti.
2. **Given** la guida d'installazione, **When** la si consulta, **Then** essa dichiara che i prodotti a
   install diretto sono l'installer e quello di governance, mentre la libreria e il motore d'installazione
   sono dipendenze interne risolte dalla sorgente.
3. **Given** la guida d'installazione, **When** la si consulta, **Then** essa dichiara esplicitamente che
   la pubblicazione pubblica è fuori ambito e che la distribuzione interim è il canale corrente.

---

### Edge Cases

- **Licenza dichiarata senza testo** → la verifica di build deve fallire, non passare in silenzio
  (incoerenza legale resa visibile).
- **Asset d'installazione esclusi dall'artefatto** dell'installer → install rotto a valle; la verifica deve
  rilevarne l'assenza nell'artefatto, non scoprirla solo all'uso.
- **Versioni disallineate** tra i quattro prodotti → install incoerenti; il disallineamento va prevenuto da
  un'unica fonte di verità per la versione.
- **Gestore secondario che non risolve le dipendenze interne** come il primario → il limite va documentato
  e non blocca il "done"; il percorso primario resta il gate.
- **Cambio di layout del monorepo** che rompe la scoperta della sorgente dal checkout → colto dalla
  verifica su ambiente vergine.
- **Tentazione di pubblicazione pubblica** (upload, token, hardening supply-chain) → fuori ambito; non va
  introdotta da questa feature.
- **Installazione che avvia inavvertitamente l'indicizzazione** → l'installazione non deve avviare alcuna
  ingestione/creazione indice (install ≠ run).

## Requirements *(mandatory)*

> **Due insiemi di prodotti (definizione, da DA-P3/P4):**
> - **Build-validati (tutti e quattro):** la libreria, l'installer, il motore d'installazione e quello di
>   governance — devono costruirsi correttamente e portare il testo della licenza coerente. Sono il
>   bersaglio dei requisiti di licenza (gruppo A) e di build (gruppo C).
> - **User-facing (install diretto):** l'installer e quello di governance — sono il bersaglio della
>   checklist di metadati completi (gruppo B). La libreria e il motore d'installazione sono **dipendenze
>   interne** risolte dalla sorgente: build-validate ma esonerate dalla checklist user-facing.
>
> Dove un requisito dice "prodotto distribuibile" senza ulteriore specifica, si applica all'insieme
> build-validato; i requisiti di metadati user-facing (FR-010, FR-013) si applicano all'insieme
> user-facing.

### Functional Requirements

**Gruppo A — Licenza e coerenza legale**

- **FR-001**: Il sistema MUST includere un file di licenza con il testo MIT in ogni prodotto distribuibile
  e nella radice del repository.
- **FR-002**: I metadati di distribuzione di ogni prodotto MUST dichiarare la licenza MIT in modo coerente
  con il testo della licenza spedito.
- **FR-003**: Quando un prodotto distribuibile viene costruito, il sistema MUST includere il suo file di
  licenza all'interno dell'artefatto prodotto.
- **FR-004**: Se un prodotto dichiara una licenza nei metadati senza spedire il testo corrispondente, la
  verifica di build MUST fallire.

**Gruppo B — Versioning e metadati di distribuzione**

- **FR-010**: Ogni prodotto **user-facing** MUST esporre, nei metadati di distribuzione, nome, versione,
  descrizione, autori, licenza e indirizzo del repository.
- **FR-011**: Il sistema MUST applicare un'**unica versione di prodotto allineata** a tutti e quattro i
  prodotti del workspace, bumpata insieme e documentata in un'unica fonte di verità.
- **FR-012**: Ogni prodotto distribuibile MUST dichiarare un vincolo di versione del linguaggio coerente
  con la baseline del progetto (linguaggio ≥ versione minima dichiarata).
- **FR-013**: Dove il formato dei metadati lo supporta, ogni prodotto user-facing SHOULD dichiarare
  classificatori e parole chiave che descrivono licenza, versioni supportate e uso previsto.
- **FR-014**: Se un campo di metadati di distribuzione richiesto (per FR-010) manca da un prodotto
  user-facing, la verifica di build MUST fallire.

**Gruppo C — Validazione di build dell'artefatto**

- **FR-020**: Quando si esegue la build di un prodotto distribuibile, il sistema MUST produrre sia una
  distribuzione sorgente sia un artefatto installabile, senza errori.
- **FR-021**: Quando si costruisce l'installer, l'artefatto prodotto MUST includere gli asset non eseguibili
  necessari all'installazione (dati di pacchetto).
- **FR-022**: Il sistema MUST fornire una verifica di build ripetibile, eseguibile nella CI locale senza
  credenziali cloud e senza accesso di rete a indici pubblici di pacchetti.
- **FR-023**: Quando la verifica di build è eseguita, il sistema MUST verificare che ogni artefatto prodotto
  dichiari i punti d'ingresso attesi per il proprio prodotto.
- **FR-024**: Se la build di un qualunque prodotto distribuibile fallisce, la verifica MUST riportare il
  prodotto coinvolto e terminare con esito di errore.

**Gruppo D — Install pulito "a un comando" (verifica)**

- **FR-030**: Quando un installatore installa l'installer dalla sorgente interim in un ambiente pulito con
  un singolo comando, il sistema MUST rendere disponibile il punto d'ingresso dell'installer senza passi
  manuali aggiuntivi.
- **FR-031**: Quando un installatore installa il prodotto di governance dalla sorgente interim in un
  ambiente pulito con un singolo comando, il sistema MUST rendere disponibile il relativo punto d'ingresso.
- **FR-032**: Quando l'installer (o la libreria) è installato dalla sorgente interim, il sistema MUST
  risolvere le sue dipendenze interne dalla stessa sorgente, senza richiedere un indice pubblico di
  pacchetti.
- **FR-033**: Il sistema MUST verificare l'install pulito a un comando per **almeno due** gestori
  d'installazione: il percorso primario e un secondo percorso.
- **FR-034**: Quando l'install pulito si completa, il sistema MUST verificare che ogni punto d'ingresso
  installato sia invocabile (es. risponde a un'invocazione di aiuto/versione) restituendo successo.
- **FR-035**: Se l'install pulito a un comando **tramite il percorso primario** non rende disponibile un
  punto d'ingresso dichiarato, la verifica MUST fallire identificando il prodotto e il gestore. Il
  percorso secondario è verificato; se non risolve le dipendenze interne come il primario, il limite è
  **documentato** e l'ergonomia piena del percorso secondario è rinviata (FEAT-010) — non blocca il "done".

**Gruppo E — Documentazione del percorso d'installazione**

- **FR-040**: La guida d'installazione MUST documentare il comando esatto della distribuzione interim per
  entrambi i gestori supportati, inclusi i prerequisiti.
- **FR-041**: La guida d'installazione MUST dichiarare che i punti d'ingresso a install diretto sono
  l'installer e il prodotto di governance, e che la libreria e il motore d'installazione sono dipendenze
  interne risolte dalla sorgente — non pubblicizzati come install diretto dell'utente.
- **FR-042**: La documentazione MUST dichiarare esplicitamente che la pubblicazione pubblica è fuori ambito
  (rinviata a FEAT-006) e che la distribuzione interim è il canale corrente.

**Gruppo F — Invarianti preservati**

- **FR-050**: Se un prodotto è installato, il sistema MUST non avviare ingestione RAG o creazione indice
  (install ≠ run).
- **FR-051**: Il packaging e la sua verifica MUST non richiedere, incorporare o persistere alcun segreto
  (es. chiavi API) in file versionati o negli artefatti prodotti.
- **FR-052**: Quando la verifica di build/install gira contro un repository ospite, il sistema SHOULD non
  sovrascrivere file modificati dall'utente.
- **FR-053**: Il packaging MUST restare host-agnostico: costruire/installare non deve assumere uno specifico
  repository ospite, distribuzione del linguaggio o sistema operativo oltre i prerequisiti dichiarati.

### Key Entities

- **Prodotto distribuibile**: un'unità del workspace che viene costruita in un artefatto distribuibile.
  Si distingue in *build-validato* (tutti) e *user-facing* (a install diretto). Porta una licenza coerente
  e, se user-facing, metadati di riferimento completi.
- **Artefatto di distribuzione**: l'output costruito da un prodotto (distribuzione sorgente + artefatto
  installabile). Deve contenere il testo della licenza, i metadati dichiarati, i punti d'ingresso e — per
  l'installer — gli asset richiesti all'installazione.
- **Versione di prodotto**: l'unica versione allineata applicata a tutti i prodotti, governata da un'unica
  fonte di verità e bumpata insieme.
- **Sorgente di distribuzione interim**: il canale corrente da cui un ambiente pulito ottiene il prodotto e
  ne risolve le dipendenze interne, senza un indice pubblico di pacchetti.
- **Punto d'ingresso**: il comando reso disponibile dall'installazione; deve risultare invocabile dopo
  l'install pulito.
- **Verifica di build/install**: il controllo ripetibile che attesta licenza, metadati, build e install
  pulito; segnala in modo non ambiguo prodotto e percorso quando fallisce.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (licenza coerente)**: **0** prodotti distribuibili dichiarano una licenza nei metadati senza che
  il testo della licenza sia presente nel sorgente **e** nell'artefatto prodotto.
- **SC-002 (metadati completi)**: ogni prodotto user-facing espone, nei metadati dell'artefatto, almeno
  nome, versione, licenza, autori, indirizzo del repository e descrizione; **0** campi obbligatori mancanti.
- **SC-003 (build valida)**: per ogni prodotto distribuibile la build produce gli artefatti attesi
  (distribuzione sorgente + installabile) senza errori, con i contenuti richiesti; **0** build fallite.
- **SC-004 (install pulito a un comando)**: su un ambiente vergine, un singolo comando installa l'installer
  (e separatamente il prodotto di governance) dalla sorgente interim e ne rende disponibili i punti
  d'ingresso; verificato per **≥ 2** percorsi d'installazione.
- **SC-005 (entry-point invocabili)**: **100%** dei punti d'ingresso installati dal percorso primario
  rispondono con successo a un'invocazione di aiuto/versione dopo l'install pulito.
- **SC-006 (documentazione)**: la guida d'installazione documenta il percorso della distribuzione interim
  per **entrambi** i gestori, con comando esatto e prerequisiti, e dichiara il confine sulla pubblicazione
  pubblica.
- **SC-007 (versione allineata)**: i quattro prodotti del workspace riportano **un'unica** versione di
  prodotto identica; **0** disallineamenti.
- **SC-008 (confine pubblicazione)**: **0** artefatti o azioni di pubblicazione pubblica (upload, token,
  hardening supply-chain) introdotti da questa feature.
- **SC-009 (nessun segreto)**: **0** segreti presenti in file versionati o in artefatti prodotti dalla
  feature o dalla sua verifica.

## Assumptions

- **Ground truth di build già verificata a monte (sessione 2026-06-16, flusso principale; non rifatta in
  questa fase):** i quattro prodotti si costruiscono correttamente (distribuzione sorgente + artefatto
  installabile); l'artefatto dell'installer include gli asset; i metadati dichiarano MIT ma **manca** il
  riferimento al repository / ai classificatori e il testo della licenza non è incluso; **nessun** file di
  licenza è presente nel repository. Queste lacune sono precisamente ciò che la feature chiude.
- **Licenza = MIT** (decisione utente D1), coerente con la licenza già adottata dal componente di
  governance.
- **Distribuzione interim = sorgente dal checkout** (DA-4); la pubblicazione pubblica è fuori ambito
  (FEAT-006). Il design non deve precluderla.
- **Versione unica allineata** sui quattro prodotti (DA-P1), bumpata insieme da un'unica fonte di verità;
  un meccanismo automatico legato ai tag è *design*, fuori ambito.
- **Percorso primario + secondario** (DA-P2): il percorso primario è il gate del Must; il secondario è
  verificato ma, se non risolve le dipendenze interne come il primario, il limite è documentato e
  l'ergonomia piena è rinviata a FEAT-010 — non blocca il "done".
- **Insiemi di prodotti** (DA-P3/P4): l'installer e il prodotto di governance sono user-facing; la libreria
  e il motore d'installazione sono dipendenze interne (build-validate, metadati user-facing esonerati). I
  console-script della libreria sono raggiungibili **dopo** l'installazione, non promossi come install
  diretto. Esporli come install diretto sarà un'aggiunta futura non-breaking, fuori da questo ambito.
- **Verifica deterministica e isolata** (NFR): ripetibile in CI locale, senza rete verso indici pubblici di
  pacchetti per la build e senza credenziali cloud; l'install pulito avviene in un ambiente effimero.
- **Non-regressione**: l'introduzione di licenza/metadati non altera il comportamento runtime dei prodotti
  già consegnati (punti d'ingresso, import, suite di test esistente verde).
- **Fuori ambito (capacità future con casa durevole):** pubblicazione pubblica e hardening supply-chain
  (FEAT-006); ergonomia avanzata dell'installer e percorso secondario pieno (FEAT-010); lifecycle
  upgrade/uninstall (FEAT-008); wizard di configurazione provider (FEAT-003); meccanismo automatico di
  versioning legato ai tag (design); ri-specifica di entry-point/comandi/install≠run (già consegnati).
- **Domande di design ancora aperte (→ `/speckit-plan`)**: forma e sede della fonte di verità della
  versione e del meccanismo di bump; forma concreta della verifica ripetibile e sua collocazione nella CI
  locale; comportamento esatto del percorso secondario rispetto alle dipendenze interne. Non sono
  ambiguità di *cosa/perché*, quindi non bloccano la spec.
