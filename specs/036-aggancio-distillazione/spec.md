# Feature Specification: Aggancio della distillazione all'archivio episodico

**Feature Branch**: `036-aggancio-distillazione`

**Created**: 2026-06-14

**Status**: Draft

**Input**: FEAT-003 dell'epica `memoria-conversazioni`. Fonte requisiti:
`requirements/memoria-conversazioni/aggancio-distillazione/requirements.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recuperare una conversazione passata per distillarla (Priority: P1)

Mentre lavoro mi accorgo che una decisione presa in una sessione di settimane fa non è mai finita nel
wiki (il rituale era assente quel giorno). So che la conversazione è stata archiviata. Voglio
**recuperarne il transcript intero** dal terminale, portarlo in contesto, condensarlo e distillarlo
nelle pagine wiki — invece di dover ricostruire a memoria un brief.

**Why this priority**: è il cuore della feature e il motivo dell'epica. Senza il recupero della
conversazione intera, la modalità «from conversation» di `distill` resta una rete di sicurezza solo
teorica (oggi pretende un brief scritto a mano e vieta il transcript grezzo).

**Independent Test**: con la memoria attiva e almeno una sessione archiviata, eseguire il comando di
«show» con la chiave di quella sessione restituisce **tutti** i turni in ordine (ruolo, timestamp,
testo) — non snippet. Verificabile da solo, senza alcun altro pezzo della feature.

**Acceptance Scenarios**:

1. **Given** la memoria attiva e una sessione `S` archiviata con N turni, **When** chiedo di mostrare
   `S`, **Then** ottengo i N turni in ordine di indice, ciascuno con ruolo, timestamp e testo completo.
2. **Given** una chiave di sessione inesistente, **When** chiedo di mostrarla, **Then** ottengo un
   messaggio azionabile «sessione non trovata» e un codice di uscita non-zero (distinto dal caso di
   sessione esistente ma vuota).
3. **Given** l'output in forma JSON (`--json`), **When** mostro una sessione, **Then** ottengo una
   struttura parseable con metadati della sessione e l'elenco ordinato dei turni.

---

### User Story 2 - Scoprire quale conversazione recuperare (Priority: P2)

Non ricordo la chiave esatta della sessione che mi serve. Voglio **elencare le conversazioni
archiviate più recenti** (chiave, data, numero di turni) per individuare quella giusta e poi
recuperarla.

**Why this priority**: rende la User Story 1 comoda da usare nella pratica (senza elenco si deve
conoscere la chiave a memoria). Da sola non distilla nulla, ma è il complemento naturale; abbinata a
`memory search` (FEAT-002) copre sia la scoperta per recency sia quella per contenuto.

**Independent Test**: con più sessioni archiviate, eseguire il comando di «list» restituisce le più
recenti con chiave, data e #turni, ordinate dalla più recente, entro un limite.

**Acceptance Scenarios**:

1. **Given** 3 sessioni archiviate in tempi diversi, **When** elenco le sessioni, **Then** le vedo
   ordinate dalla più recente alla più vecchia, ciascuna con chiave, data e numero di turni.
2. **Given** un limite richiesto K inferiore al numero di sessioni, **When** elenco, **Then** ottengo
   al più K voci.
3. **Given** un archivio vuoto, **When** elenco, **Then** ottengo uno stato vuoto esplicito (nessun
   errore).

---

### User Story 3 - Distillazione disciplinata: backup, non automatismo (Priority: P1)

Come custode del progetto, voglio la garanzia che agganciare la distillazione all'archivio **non**
introduca alcuna distillazione automatica né alcun costo di token ricorrente: la distillazione da
archivio avviene **solo** quando la invoco esplicitamente, su una sessione **mirata**. L'archivio
resta memoria di backup (cold storage), non una sorgente che viene rielaborata a ogni turno.

**Why this priority**: è il vincolo che protegge il budget di token e l'integrità del flusso. È P1
perché un'implementazione che lo violasse sarebbe peggiore dello stato attuale (spreco silenzioso).

**Independent Test**: ispezione del comportamento del sistema — il rituale di step e l'hook
`SessionEnd` restano invariati; non esiste alcun nuovo trigger che invochi distillazione; con
`SERTOR_MEMORY` spento i nuovi comandi falliscono con errore azionabile e nient'altro cambia.

**Acceptance Scenarios**:

1. **Given** la feature consegnata, **When** termina una sessione o un turno, **Then** non viene
   avviata alcuna distillazione automatica (nessun consumo di token oltre la cattura economica già
   esistente).
2. **Given** `SERTOR_MEMORY` non configurato, **When** invoco «show» o «list», **Then** ottengo un
   errore azionabile che nomina la manopola e un'uscita non-zero, identico al gating di
   `memory search`/`memory archive`.
3. **Given** la procedura `distill` documentata, **When** la consulto, **Then** la modalità «from
   conversation» indica di **recuperare una sessione mirata** dall'archivio, condensarla nel flusso
   principale e poi distillare — mai di distillare l'intero archivio.

### Edge Cases

- **Sessione esistente ma vuota** (nessun turno): «show» distingue questo caso dalla sessione
  inesistente (stato vuoto esplicito, non errore «not found»).
- **Archivio assente / illeggibile / corrotto**: «show» e «list» degradano a stato vuoto esplicito +
  warning, mai crash (coerenza con la policy non-fatale di FEAT-001/002).
- **Transcript molto lungo**: la `show` restituisce comunque l'intera sessione (la scelta della
  sessione è già mirata; restringere prima è compito di `memory search`).
- **Chiave con caratteri host-specifici** (`session_key` opaca): trattata come dato opaco, nessun
  branch sull'identità dell'assistente.
- **Memoria spenta a metà** (manopola off): nessun file letto, errore azionabile immediato.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST restituire, su richiesta per chiave, il **transcript completo** di una
  sessione archiviata — tutti i turni in ordine di indice, con ruolo, timestamp e testo — non snippet.
- **FR-002**: Il sistema MUST poter restituire un **elenco delle sessioni archiviate più recenti**
  (per ciascuna: chiave, istante di cattura, numero di turni), ordinato dalla più recente ed entro un
  limite configurabile.
- **FR-003**: Se la chiave richiesta non è presente nell'archivio, il sistema MUST restituire un esito
  esplicito «non trovata», distinto sia da un errore sia da una sessione vuota.
- **FR-004**: Se l'archivio è assente, vuoto o illeggibile, il sistema MUST degradare a stato vuoto
  esplicito + warning, mai un crash.
- **FR-005**: Il recupero e l'elenco MUST essere esposti ai consumatori sottili tramite una factory di
  composition root, **senza** introdurre una nuova porta di dominio.
- **FR-006**: Gli utenti MUST poter eseguire un comando «mostra sessione» con una chiave, ottenendo il
  transcript intero in forma leggibile e, con un'opzione `--json`, in forma strutturata — coerente con
  lo stile di output di `memory search`/`memory archive`.
- **FR-007**: Gli utenti MUST poter eseguire un comando «elenca sessioni» recenti, con un'opzione di
  limite, in forma umana e `--json`.
- **FR-008**: Se la memoria conversazioni non è abilitata, i comandi MUST fallire con un errore
  azionabile che nomina la manopola e uscire con codice non-zero (gating identico alla feature 035).
- **FR-009**: Se la chiave richiesta non è trovata, il comando «mostra» MUST stampare un messaggio
  azionabile e uscire con codice non-zero (distinto dal caso successo-con-vuoto).
- **FR-010**: La procedura `distill` (in modalità «from conversation») MUST essere aggiornata per
  indirizzare il flusso principale a **recuperare la sessione mirata** dall'archivio, condensarla e poi
  distillare — sostituendo il precedente obbligo di un brief scritto a mano.
- **FR-011**: Dove la procedura di distillazione è distribuita agli ospiti come asset installabile, la
  stessa indicazione «attingi all'archivio» MUST essere riflessa nell'asset, mantenendolo coerente con
  la procedura in-repo (host-agnostico).
- **FR-012**: La feature MUST essere puramente additiva: comportamento di core, CLI e hook esistenti
  invariato; con la memoria spenta il sistema MUST comportarsi esattamente come prima.
- **FR-013** (vincolo cardine): Se la distillazione dall'archivio viene avviata, MUST avvenire
  **solo** per invocazione esplicita, iniziata da umano/agente, su una sessione **mirata**; il sistema
  MUST NON distillare automaticamente intere conversazioni, l'intero archivio, né su base
  per-turno/per-sessione.
- **FR-014**: Il percorso di recupero ed elenco MUST restare interamente locale — nessuna rete,
  nessun embedding, nessun LLM — preservando la privacy by design (contenuto già scrubbato a monte).

### Key Entities *(include if feature involves data)*

- **Sessione archiviata**: la conversazione conservata (chiave opaca, progetto, istante di cattura,
  tipo di adapter, elenco ordinato di turni post-scrub, numero di turni). Già modellata da FEAT-001
  (`ArchivedSession`); questa feature la **legge** e la **espone**, non la ridefinisce.
- **Voce di elenco sessione**: vista sintetica per la scoperta (chiave, data, numero di turni), senza
  il contenuto dei turni.
- **Turno**: unità conversazionale (indice, ruolo, timestamp, testo) — già modellata da FEAT-001.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Data una sessione archiviata di N turni, il comando «mostra» restituisce esattamente
  quei N turni in ordine, con testo completo (nessuna troncatura).
- **SC-002**: Con M sessioni archiviate, il comando «elenca» le presenta dalla più recente, entro il
  limite richiesto, con chiave/data/#turni corretti.
- **SC-003**: Una distillazione in modalità «from conversation» può attingere a una sessione
  archiviata senza che l'utente scriva un brief a mano (la procedura documentata lo prevede).
- **SC-004**: La consegna **non** aggiunge alcun trigger automatico di distillazione: rituale di step
  e hook `SessionEnd` restano invariati; zero token consumati per-turno/per-sessione dal nuovo aggancio.
- **SC-005**: Con la memoria spenta, il comportamento dell'intero sistema è identico a prima della
  feature, e i nuovi comandi falliscono con errore azionabile + uscita non-zero.
- **SC-006**: Recupero ed elenco non effettuano alcuna chiamata di rete (verificabile: nessun accesso
  esterno nel percorso query).
- **SC-007**: La feature non introduce nuove porte di dominio (verificabile: il numero di Protocol in
  `domain/ports.py` resta invariato).

## Assumptions

- **DA-1 risolta (a)**: il recupero porta i **turni grezzi** in contesto e il flusso principale (Opus)
  li **condensa e distilla**. Nessuno step di condensazione automatica (nessun codice di riassunto):
  coerente con «distill è giudizio».
- **DA-2 risolta**: il comando «elenca» (`list`) è **incluso** nell'MVP della feature (costo minimo,
  rende scopribile la chiave).
- **DA-3 risolta**: la granularità del recupero è la **sessione intera** (allineata alla granularità
  ibrida di FEAT-001); il recupero a livello di thread/finestra di turni è un raffinamento successivo.
- **DA-4 risolta**: eventuali tool MCP `show`/`list` sono **fuori ambito** (Could, rinviati); la
  superficie è solo CLI — copre il caso d'uso del flusso principale.
- Il recupero della sessione intera per chiave **esiste già** nel core (`MemoryArchive.get`): la
  feature aggiunge solo l'elenco (lettura) e la superficie CLI.
- La privacy è coperta a monte: il contenuto è scrubbato all'archiviazione (FEAT-001); il percorso di
  lettura è locale.
- La superficie CLI si innesta sul gruppo di sotto-comandi `memory` introdotto dalla feature 035.
