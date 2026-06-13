# Feature Specification: Igiene e collocazione degli artefatti dell'installer sull'ospite

**Feature Branch**: `016-igiene-radice-host`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "Igiene e collocazione degli artefatti dell'installer Sertor sull'ospite (radice host pulita e prevedibile). Fonte: requirements/sertor-cli/igiene-radice-host/requirements.md (REQ-301..307, D1..D4 risolte, retrocompat ospiti esterni FUORI AMBITO). Asse: DOVE stanno i file (collocazione), ortogonale all'ownership (epica multiutente)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Radice host minima e prevedibile dopo l'install (Priority: P1)

Un maintainer installa una capacità Sertor (RAG e/o wiki) su un proprio repository. Al termine, la
radice del progetto ospite resta **ordinata e prevedibile**: contiene **solo** gli artefatti che
*devono* starci e la dotfolder di runtime, senza file di tooling sparsi che "sporcano" la root.

**Why this priority**: è il problema concreto che ha originato la feature (install su Kaelen,
2026-06-12): la radice disordinata è il sintomo che l'utente vuole eliminare. Senza questa garanzia
la feature non ha valore. È la fetta minima dimostrabile.

**Independent Test**: eseguire l'install su un repo ospite pulito e verificare l'elenco dei file
comparsi in radice: devono esserci solo i residenti inevitabili (`.claude/`, `CLAUDE.md`, `wiki/`,
`.gitignore`) più la dotfolder `.sertor/`; nessun altro file di tool a livello root.

**Acceptance Scenarios**:

1. **Given** un repository ospite senza installazione Sertor, **When** si esegue l'install di una
   capacità, **Then** la radice host contiene solo `.claude/`, `CLAUDE.md`, `wiki/`, `.gitignore` e
   `.sertor/`, e nessun altro artefatto di tooling a livello root.
2. **Given** un install RAG completato, **When** si ispeziona la radice host, **Then** l'intero
   runtime RAG (progetto, ambiente isolato, indice, configurazione di runtime) risiede sotto
   `.sertor/` e nessun file di runtime è in radice.
3. **Given** un install di capacità wiki, **When** si ispeziona la radice host, **Then** la
   configurazione del wiki **non** è in radice ma vive insieme al contenuto del wiki.

---

### User Story 2 - Wiki autocontenuto e invocazioni sempre funzionanti (Priority: P2)

La configurazione del wiki e il suo contenuto vivono nella **stessa cartella** (`wiki/`). Tutte le
superfici che invocano gli strumenti del wiki (skill, hook, agente, comando) trovano la
configurazione nella nuova sede **senza alcun intervento manuale**. Lo stesso vale per Sertor come
progetto che fa dogfooding: la sua configurazione interna è riallineata nello stesso passaggio.

**Why this priority**: spostare la configurazione senza riallineare *ogni* invocazione produrrebbe
uno strumento rotto (deriva di coerenza). È il rischio principale della feature e va garantito subito
dopo la radice pulita.

**Independent Test**: con la configurazione del wiki nella nuova sede, eseguire ciascuna operazione
del wiki esposta dagli asset installati e verificare che localizzi la configurazione e completi senza
che l'utente debba passare percorsi a mano; per Sertor stesso, eseguire la suite di test di
allineamento degli asset e verificarla verde.

**Acceptance Scenarios**:

1. **Given** un ospite con la configurazione del wiki nella nuova sede, **When** una qualunque
   invocazione installata degli strumenti del wiki viene eseguita, **Then** localizza la
   configurazione automaticamente e completa con successo.
2. **Given** la configurazione del wiki spostata, **When** si esamina l'insieme degli asset
   installati, **Then** nessuna invocazione punta ancora alla vecchia posizione.
3. **Given** Sertor stesso (progetto di dogfooding), **When** si riallinea la sua configurazione
   interna nello stesso cambiamento, **Then** tutte le sue invocazioni interne e i test di
   allineamento degli asset risultano coerenti e verdi, senza introdurre un meccanismo di migrazione
   riusabile.

---

### User Story 3 - Scelta dello scope di registrazione MCP (Priority: P3)

Durante l'install, il maintainer può scegliere **dove** registrare il server MCP: nella radice del
repository (scope *project*) oppure fuori dal repository, nella configurazione personale del client
(scope *local*), così da poter avere una radice senza il file di registrazione MCP.

**Why this priority**: offre il controllo per eliminare anche l'ultimo residente "scomodo" della
radice quando lo si desidera, ma non è la fetta minima: la radice è già prevedibile senza questa
scelta (il file MCP è un residente legittimo e documentato in scope *project*).

**Independent Test**: eseguire l'install scegliendo lo scope *local* e verificare che in radice non
compaia il file di registrazione MCP e che il server resti raggiungibile dal client; ripetere con
*project* e verificare il merge non distruttivo del file in radice.

**Acceptance Scenarios**:

1. **Given** un install con scope MCP *local*, **When** l'install completa, **Then** non esiste un
   file di registrazione MCP nella radice del repository e il server resta raggiungibile dal client.
2. **Given** un install con scope MCP *project*, **When** esiste già un file di registrazione MCP in
   radice, **Then** l'install lo aggiorna in modo non distruttivo preservando le voci preesistenti.
3. **Given** una richiesta di scope *local* non realizzabile (strumento del client non disponibile),
   **When** l'install la elabora, **Then** fallisce con un messaggio leggibile (ed eventualmente il
   comando manuale equivalente) e **non** scrive silenziosamente un file di registrazione in radice.

---

### Edge Cases

- **Scope *local* non realizzabile**: lo strumento del client necessario manca → fail-fast con
  messaggio azionabile; mai un fallback silenzioso che scrive il file in radice (copre il rischio
  R-3 dei requisiti).
- **Ospite già installato con la configurazione del wiki in radice**: la migrazione automatica è
  **fuori ambito** (decisione D4). Un nuovo install scrive la configurazione nella sede nuova; un
  eventuale file legacy in radice **non** viene rimosso dall'installer (limite noto e dichiarato).
- **File di registrazione MCP già presente in radice** (scope *project*): aggiornamento non
  distruttivo, nessuna perdita di voci esistenti.
- **Ospite non-Python**: il runtime resta confinato in `.sertor/`; i sorgenti dell'ospite non
  vengono toccati (comportamento già introdotto dall'install RAG).
- **Re-run dell'install** sulla stessa sede: idempotente, nessun duplicato e nessun nuovo file di
  tooling sparso in radice.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (REQ-301): L'installer MUST mantenere l'intero runtime RAG sotto `.sertor/` nella radice
  ospite e MUST NOT collocare alcun file di runtime RAG direttamente in radice.
- **FR-002** (REQ-302): L'installer MUST collocare la configurazione del wiki dentro `wiki/` e MUST
  configurare ogni invocazione installata degli strumenti del wiki (skill, hook, agente, comando)
  affinché la localizzi senza intervento manuale.
- **FR-003** (REQ-303): Quando la posizione della configurazione del wiki cambia, gli asset
  installati e la configurazione interna di Sertor MUST restare coerenti — nessuna invocazione
  lasciata a puntare alla vecchia posizione.
- **FR-004** (REQ-304): L'install MUST offrire un meccanismo di scelta dello scope di registrazione
  MCP: *project* scrive/aggiorna il file di registrazione nella radice; *local* registra il server
  nella configurazione personale del client senza scrivere file nel repository.
- **FR-005** (REQ-305): Se lo scope *local* è richiesto ma non realizzabile, l'installer MUST fallire
  in modo esplicito e leggibile (ed eventualmente stampare il comando manuale) e MUST NOT scrivere
  silenziosamente un file di registrazione in radice.
- **FR-006** (REQ-306): L'installer MUST NOT collocare in radice artefatti diversi dagli inevitabili
  (`.claude/`, `CLAUDE.md`, `wiki/`, `.gitignore`) e dalla dotfolder `.sertor/`, e MUST documentare
  perché ciascun residente di radice deve trovarsi lì.
- **FR-007** (REQ-307): Gli artefatti generati MUST essere host-agnostici: nessun percorso assoluto
  di Sertor né riferimento al dominio Sertor cablato (Principio X).
- **FR-008** (eccezione D4): Per Sertor stesso (dogfooding), la configurazione interna del wiki MUST
  essere spostata nella nuova sede **one-shot**, come fix diretto contestuale, riallineando nello
  stesso cambiamento gli asset interni che la invocano e i relativi test di allineamento; l'installer
  MUST NOT includere un meccanismo/comando di migrazione per gli ospiti esterni già installati.

### Key Entities *(include if feature involves data)*

- **Radice host**: l'insieme dei file/cartelle a livello root del repository ospite; l'obiettivo è
  che contenga solo i residenti inevitabili più `.sertor/`.
- **Configurazione del wiki**: il file di profilo che governa percorsi e impostazioni degli strumenti
  del wiki; si sposta da radice a `wiki/`, accanto al contenuto.
- **Dotfolder di runtime `.sertor/`**: l'unica sede del runtime RAG sull'ospite (progetto isolato,
  ambiente, indice, configurazione di runtime).
- **Registrazione MCP**: il modo in cui il server MCP è reso noto al client; vive o in radice (scope
  *project*) o nella configurazione personale del client (scope *local*).
- **Asset dell'installer**: le superfici agentiche distribuite (skill, hook, agente, comando) che
  invocano gli strumenti del wiki e devono localizzare la configurazione nella sede corretta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dopo un install su un repo ospite pulito, la radice host contiene **solo** `.claude/`,
  `CLAUDE.md`, `wiki/`, `.gitignore` e `.sertor/` — **zero** altri file di tooling sparsi.
- **SC-002**: Con la configurazione del wiki nella nuova sede, il **100%** delle invocazioni degli
  strumenti del wiki negli asset installati completa con successo senza intervento manuale
  dell'utente.
- **SC-003**: Con scope MCP *local*, dopo l'install **non** esiste un file di registrazione MCP nella
  radice del repository e il server resta raggiungibile dal client.
- **SC-004**: Sertor stesso (dogfooding) opera con la configurazione del wiki nella nuova sede: tutte
  le sue invocazioni interne e i test di allineamento degli asset risultano verdi.
- **SC-005**: A fronte di uno scope *local* non realizzabile, l'install fallisce con messaggio
  leggibile e produce **zero** file di registrazione scritti silenziosamente in radice.
- **SC-006**: Un re-run dell'install non aggiunge alcun nuovo file di tooling in radice rispetto al
  primo run (idempotenza della collocazione).

## Assumptions

- **Retrocompatibilità ospiti esterni fuori ambito** (decisione utente D4, 2026-06-13): la base
  installata esterna è trascurabile e si riallinea con un nuovo install; non si costruisce alcun
  percorso/comando di migrazione. Un eventuale file di configurazione legacy in radice su un vecchio
  ospite non viene rimosso dall'installer.
- **Default dello scope MCP deciso altrove**: questa feature fornisce il **meccanismo** di scelta
  *project*/*local*; il valore di default (e la sua logica mono-utente vs team) è materia della
  feature `installer-multiutente`. Si assume che, in assenza di scelta esplicita, l'install conservi
  il comportamento corrente (registrazione in radice, scope *project*).
- **Vincoli di collocazione verificati**: il file di registrazione MCP project-scope deve risiedere
  in radice (vincolo del client, non spostabile in `.claude/`); `.claude/`, `CLAUDE.md` e `wiki/`
  sono residenti inevitabili a root (lettura del client / documentazione by-design).
- **`.sertor/` come unica sede del runtime** è già realtà (introdotta dall'install RAG); questa
  feature la conferma e la documenta, non la reintroduce.
- **Fix one-shot di Sertor**: lo spostamento della configurazione interna di Sertor e il
  riallineamento dei suoi asset/test avvengono nello stesso cambiamento, senza diventare un asset di
  migrazione riusabile.
