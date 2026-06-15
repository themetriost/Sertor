# Feature Specification: Distribuzione su GitHub Copilot (parità di assistente) — pacchetto `sertor`

**Feature Branch**: `044-distribuzione-copilot`

**Created**: 2026-06-15

**Status**: Draft

**Input**: FEAT-007 (epica sertor-cli) — requisiti in `requirements/sertor-cli/distribuzione-copilot/requirements.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - RAG (server MCP) raggiungibile da Copilot (Priority: P1)

Un team che lavora con **GitHub Copilot** installa la capacità RAG di Sertor su un repository
scegliendo il proprio assistente come target. Al termine, dal client Copilot vede e usa il server
`sertor-rag` (ricerca su codice e documentazione) **senza dover modificare a mano** la configurazione,
esattamente come oggi può fare un utente Claude.

**Why this priority**: è la fetta più sottile e di valore più alto. Le CLI di Sertor sono già
assistant-agnostic; il solo cablaggio del server MCP nel client Copilot rende immediatamente
utilizzabile la capacità centrale (retrieval) senza dipendere da un assistente specifico. È un MVP
end-to-end da sola.

**Independent Test**: su un repo pulito, eseguire l'installazione della capacità RAG indicando Copilot
come assistente target; verificare da un client Copilot che il server `sertor-rag` risulti collegato e
i suoi strumenti disponibili, senza editing manuale della parte non segreta della configurazione.

**Acceptance Scenarios**:

1. **Given** un repository senza configurazione di assistente, **When** l'utente installa la capacità
   RAG scegliendo Copilot come target, **Then** il server `sertor-rag` è registrato nella superficie di
   configurazione MCP usata dai client Copilot e risulta interrogabile.
2. **Given** l'installazione RAG per Copilot, **When** la configurazione MCP viene prodotta, **Then**
   nessun valore segreto è scritto in un file versionato.
3. **Given** l'installazione RAG per Copilot completata, **When** l'utente non lancia alcun comando di
   indicizzazione, **Then** nessuna ingestione o creazione di indice parte automaticamente.

---

### User Story 2 - Rituale e comandi del sistema-wiki su Copilot (Priority: P2)

L'utente Copilot riceve, oltre al RAG, il **sistema-wiki**: le istruzioni/rituale che oggi vivono nel
blocco `CLAUDE.md` e i comandi di autoraggio del wiki (es. la consolidazione `/wiki`), nelle forme
native consumabili dal suo assistente. Così un progetto guidato da Copilot mantiene il wiki vivo con
lo stesso metodo di un progetto guidato da Claude.

**Why this priority**: completa la parità delle superfici *interattive* (istruzioni + comandi), che è
il grosso del valore quotidiano del sistema-wiki, costruendo sulla scelta-assistente già introdotta in
US1.

**Independent Test**: installare la capacità wiki con target Copilot su un repo; verificare che il
blocco di istruzioni/rituale sia presente nella superficie di istruzioni di Copilot e che i comandi del
wiki siano invocabili da un client Copilot.

**Acceptance Scenarios**:

1. **Given** l'installazione wiki per Copilot, **When** l'utente apre il proprio assistente,
   **Then** il blocco istruzioni/rituale di Sertor è attivo nella superficie di istruzioni di Copilot.
2. **Given** l'installazione wiki per Copilot, **When** l'utente invoca il comando di consolidazione del
   wiki dal client Copilot, **Then** ottiene l'equivalente funzionale del comando disponibile sotto
   Claude.
3. **Given** un repo che già contiene un blocco istruzioni installato, **When** si ri-esegue
   l'installazione, **Then** il blocco è aggiornato in loco senza duplicazioni.

---

### User Story 3 - Automatismi (agente e hook) del wiki su Copilot (Priority: P3)

L'utente Copilot riceve anche gli **automatismi**: l'agente di bookkeeping del wiki (oggi
`wiki-curator`) come custom-agent Copilot, i promemoria di registrazione legati al ciclo di sessione e
il controllo anti-bypass del Principio XI, negli equivalenti hook di Copilot.

**Why this priority**: chiude la parità portando le superfici *automatiche*. È l'ultima fetta perché
poggia su US1/US2 e tocca le superfici più soggette a evoluzione upstream (hook in Preview).

**Independent Test**: installare wiki+rag con target Copilot; verificare che esista un custom-agent
Copilot equivalente all'agente di bookkeeping, che gli hook di ciclo-sessione siano configurati e che
il controllo d'uso del Principio XI emetta l'avviso non bloccante atteso.

**Acceptance Scenarios**:

1. **Given** l'installazione wiki per Copilot, **When** si ispezionano le superfici installate,
   **Then** esiste un custom-agent Copilot equivalente all'agente di bookkeeping del wiki.
2. **Given** l'installazione per Copilot, **When** una sessione dell'assistente inizia o termina,
   **Then** scatta il promemoria di registrazione equivalente a quello disponibile sotto Claude.
3. **Given** l'installazione RAG per Copilot, **When** l'agente tenta di usare direttamente la libreria
   `sertor_core` fuori dai vehicles, **Then** il controllo emette un avviso non bloccante (fail-open),
   preservando la semantica dell'hook Claude.

---

### Edge Cases

- **Coesistenza Claude + Copilot sullo stesso repo**: installando per Copilot dopo (o prima) di Claude,
  le due configurazioni devono coesistere senza conflitti e senza che gli automatismi si attivino due
  volte (Copilot può leggere nativamente alcune superfici in formato Claude).
- **Repo esistente con file utente**: l'installazione non deve sovrascrivere file modificati dall'utente
  senza conferma esplicita.
- **Superficie Copilot non disponibile/Preview**: se una superficie target (es. hook in Preview) non è
  supportata dal client dell'utente, il sistema lo dichiara esplicitamente invece di fallire in
  silenzio o fingere parità.
- **Gap di parità reale**: se una superficie Claude non ha equivalente funzionale, deve essere
  dichiarata, non omessa.
- **Segreti**: nessun segreto della configurazione (es. chiavi del provider) finisce in file versionati.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST consentire all'utente di scegliere l'assistente target
  dell'installazione tra almeno `claude` e `copilot`, installando solo gli artefatti di quell'assistente.
- **FR-002**: Il sistema MUST applicare un assistente target predefinito, documentato, quando l'utente
  non ne specifica alcuno.
- **FR-003**: Quando l'utente sceglie Copilot per una capacità in ambito, il sistema MUST installare un
  equivalente funzionale **per ogni** superficie che l'installazione Claude produce per la stessa
  capacità (parità piena).
- **FR-004**: Quando si installa la capacità RAG con target Copilot, il sistema MUST registrare il
  server `sertor-rag` nella superficie di configurazione MCP usata dai client Copilot del repository.
- **FR-005**: Il sistema MUST produrre la configurazione MCP per Copilot in modo che la sua parte non
  segreta non richieda editing manuale perché il server sia individuabile.
- **FR-006**: Il sistema MUST NOT persistere alcun valore segreto in un file versionato.
- **FR-007**: Il sistema MUST documentare come verificare, da un client Copilot, che il server
  `sertor-rag` sia collegato e i suoi strumenti disponibili.
- **FR-008**: Quando si installa per Copilot, il sistema MUST depositare il/i blocco/i di
  istruzioni-rituale di Sertor nella superficie di istruzioni repo-wide di Copilot.
- **FR-009**: Il sistema MUST delimitare ogni blocco di istruzioni installato con marcatori stabili, in
  modo che la ri-installazione aggiorni il blocco in loco senza duplicarlo.
- **FR-010**: Quando si installa la capacità wiki per Copilot, il sistema MUST fornire equivalenti
  Copilot dei comandi di autoraggio del wiki (es. la consolidazione `/wiki`) invocabili dal client.
- **FR-011**: Quando si installa la capacità wiki per Copilot, il sistema MUST fornire un custom-agent
  Copilot equivalente all'agente di bookkeeping del wiki.
- **FR-012**: Quando si installa la capacità wiki per Copilot, il sistema MUST fornire equivalenti
  Copilot degli hook di promemoria legati al ciclo di sessione (controlli di registrazione pendente a
  inizio/fine sessione).
- **FR-013**: Quando si installa la capacità RAG per Copilot, il sistema MUST fornire un equivalente
  Copilot del controllo d'uso del Principio XI (avviso sull'uso diretto di `sertor_core` fuori dai
  vehicles/test), preservandone il comportamento non bloccante e fail-open.
- **FR-014**: Il sistema MUST mantenere cross-platform gli script degli hook installati (PowerShell e
  shell POSIX), coerente con gli asset dell'installer esistenti.
- **FR-015**: Il sistema MUST esporre una mappatura documentata, superficie-per-superficie, tra gli
  artefatti Claude e i loro equivalenti Copilot per ogni capacità in ambito.
- **FR-016**: Se una superficie Claude in ambito non ha equivalente funzionale sull'assistente target,
  allora il sistema MUST dichiararlo esplicitamente all'utente invece di ometterlo in silenzio.
- **FR-017**: Quando il setup gira su un repository esistente, il sistema MUST NOT sovrascrivere file
  modificati dall'utente senza conferma esplicita.
- **FR-018**: Se una capacità è installata o aggiunta per il target Copilot, il sistema MUST NOT avviare
  automaticamente ingestione o creazione dell'indice (install ≠ run).
- **FR-019**: Il sistema MUST mantenere le CLI di esecuzione (`sertor-rag`, `sertor-wiki-tools`)
  assistant-agnostic, senza introdurre varianti per-assistente.
- **FR-020**: La ri-esecuzione dell'installazione per lo stesso assistente target MUST essere
  idempotente (nessuna duplicazione né corruzione di artefatti).
- **FR-021**: Quando lo stesso contenuto di superficie è installato per più di un assistente, il sistema
  SHOULD derivare gli artefatti di ciascun assistente da un'unica fonte di verità, per prevenire la
  deriva tra assistenti.

### Key Entities

- **Assistente target**: l'assistente ospite per cui si installa (almeno `claude`, `copilot`); ne
  determina l'insieme di artefatti prodotti.
- **Superficie**: una categoria di artefatto distribuibile (configurazione MCP, blocco istruzioni,
  comando/skill, agente, hook); ha una forma per ciascun assistente.
- **Mappatura di parità**: la corrispondenza documentata superficie-Claude → superficie-Copilot, con
  l'eventuale dichiarazione di gap.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un utente Copilot completa l'installazione di una capacità in ambito (RAG o wiki)
  scegliendo l'assistente e usa la capacità dal proprio client (server MCP collegato, oppure comando
  wiki invocabile) **senza editing manuale** della configurazione non segreta.
- **SC-002**: Per la capacità installata, il **100%** delle superfici disponibili sotto Claude ha sotto
  Copilot un equivalente funzionante **oppure** un gap dichiarato esplicitamente; **0** superfici omesse
  in silenzio.
- **SC-003**: In **0** casi l'installazione per Copilot avvia automaticamente ingestione o creazione
  dell'indice.
- **SC-004**: La ri-esecuzione dell'installazione per lo stesso assistente produce **0** duplicazioni e
  **0** file corrotti; su repo esistente, **0** sovrascritture silenziose di file utente.
- **SC-005**: Le CLI di esecuzione restano identiche tra assistenti: **0** varianti di comando
  per-assistente.
- **SC-006**: Su uno stesso repository configurato per **entrambi** gli assistenti, le due
  configurazioni coesistono senza conflitti e senza doppia attivazione degli automatismi.

## Assumptions

- **Client target = GitHub Copilot in VS Code (agent mode)**. Altri client Copilot (es. coding agent
  cloud) sono fuori dal primo taglio.
- **Meccanismo di selezione assistente**: si assume un selettore esplicito (es. opzione
  `--assistant claude|copilot`) con **default `claude`**; forma esatta e default definitivi sono
  decisione di design (fase plan), non di specifica.
- **Riuso vs traduzione (DA-2)**: poiché i client Copilot in VS Code leggono nativamente superfici in
  formato Claude (`.claude/settings.json`, `CLAUDE.md`/`AGENTS.md`), la scelta tra **riusare** gli
  asset Claude e **autorizzare** asset Copilot nativi è una leva di design da sciogliere in fase plan
  con uno spike; non cambia il *cosa* di questa specifica (parità funzionale + onestà sui gap).
- **Ambito ai soli asset del pacchetto `sertor`** (wiki + rag). La governance/SpecKit (`sertor-flow`) è
  la feature gemella FEAT-009 e resta fuori.
- **Codex** è fuori taglio (Could d'epica).
- Le capacità del core (server MCP, sistema-wiki) non cambiano: questa feature agisce solo a livello di
  **distribuzione**.
