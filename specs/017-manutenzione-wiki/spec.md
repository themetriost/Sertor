# Feature Specification: Manutenzione wiki deterministica (`move` · `reconcile` · `collect`+status)

**Feature Branch**: `017-manutenzione-wiki`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: residuo di FEAT-007 (`requirements/sertor-core/manutenzione-wiki/requirements.md`, gruppi B/C/D). I gruppi E (seed) ed F (asset EN) sono già consegnati a parte (PR #27/#28/#29); il gruppo A (probe di freschezza) è Won't (D1).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Spostare/rinominare una pagina senza rompere i link (Priority: P1) 🎯 MVP

Chi cura il wiki riorganizza le pagine (sposta una pagina in un'altra area, o la rinomina). Oggi
deve spostare il file **e** correggere a mano ogni link entrante (`[[nome]]`/`[[nome|alias]]` e link
relativi Markdown): su un wiki con molti link è lento e lascia link rotti. Vuole un comando che faccia
lo spostamento in modo **sicuro e atomico**, con anteprima.

**Why this priority**: è la capacità che rende il riordino (reorg) praticabile senza danni; è la più
usata nella manutenzione quotidiana e la più rischiosa se fatta a mano. Da sola consegna valore.

**Independent Test**: su un wiki temporaneo con pagine che si linkano a vicenda, spostare una pagina
con il comando e verificare che (a) il file sia nella nuova sede, (b) tutti i link entranti puntino
alla nuova sede, (c) un lint successivo non riporti link rotti aggiuntivi; con anteprima, nessun file
cambiato.

**Acceptance Scenarios**:

1. **Given** una pagina linkata da altre pagine con `[[nome]]` e `[[nome|alias]]`, **When** la si
   sposta con il comando, **Then** il file è nella destinazione e ogni link entrante è riscritto verso
   la nuova posizione (gli alias preservati).
2. **Given** uno spostamento, **When** lo si esegue in modalità anteprima, **Then** il sistema riporta
   il piano completo (file da spostare, link da riscrivere, conteggi) **senza** modificare alcun file.
3. **Given** una destinazione che esiste già come file, **When** si tenta lo spostamento, **Then** il
   comando fallisce con un errore esplicito e **non** modifica nulla (nessuna sovrascrittura).
4. **Given** uno spostamento interrotto a metà (file spostato ma non tutti i link riscritti), **When**
   si riesegue lo stesso comando, **Then** il sistema rileva lo stato parziale e completa la
   riscrittura invece di fallire (idempotenza).

---

### User Story 2 - Vedere le pagine obsolete da riconciliare (Priority: P2)

Chi cura il wiki vuole una **lista** delle pagine marcate come superate (`status: superseded`) per
decidere cosa farne (aggiornare, fondere, archiviare). Il comando deve solo **mostrare**, mai
modificare: la decisione resta umana/agentica. Serve anche che l'inventario delle pagine esponga il
campo `status`, oggi non incluso.

**Why this priority**: dà visibilità sulle conoscenze stantie senza il rischio di azioni automatiche;
è un health-check ricorrente. Dipende dal piccolo prerequisito sull'inventario (campo `status`).

**Independent Test**: su un wiki con alcune pagine `status: superseded` e altre no, eseguire il comando
e verificare che elenchi **tutte e sole** quelle superate (con percorso, data, eventuale successore,
motivo) e che **nessun** file venga modificato; su un wiki senza pagine superate, lista vuota con
indicatore "pulito".

**Acceptance Scenarios**:

1. **Given** un wiki con pagine `status: superseded` e pagine normali, **When** si esegue il comando di
   riconciliazione, **Then** vengono elencate solo le pagine superate, con percorso, data `updated`,
   successore dichiarato (se presente) e un motivo; nessun file è modificato.
2. **Given** un wiki senza pagine `status: superseded`, **When** si esegue il comando, **Then** la
   lista è vuota e il risultato indica esplicitamente "pulito", senza errore.
3. **Given** l'inventario delle pagine, **When** lo si richiede, **Then** include il campo `status`
   (se presente nel frontmatter) per ogni pagina, in modo che un consumatore che non lo conosce
   continui comunque a leggere il risultato senza errori.
4. **Given** una pagina superata, **When** la si elenca, **Then** il suo contenuto su disco resta
   intatto: il comando non cancella né trasforma nulla.

---

### User Story 3 - Eseguire la riconciliazione periodicamente (Priority: P3 · Could)

Chi mantiene il wiki vuole, opzionalmente, ricevere un report periodico delle obsolescenze senza
lanciarlo a mano ogni volta.

**Why this priority**: comodità marginale; non introduce capacità nuove nel prodotto, solo
schedulazione — che appartiene all'ambiente ospite. È un Could, potenzialmente solo documentazione.

**Independent Test**: seguendo la documentazione, configurare uno scheduler dell'ambiente ospite per
invocare la riconciliazione e verificare che produca il report; il prodotto stesso non aggiunge uno
scheduler.

**Acceptance Scenarios**:

1. **Given** la guida d'uso, **When** si configura uno scheduler dell'ambiente ospite (cron / Task
   Scheduler / hook CI) per invocare la riconciliazione, **Then** il report viene prodotto su una
   destinazione configurata, senza che il prodotto modifichi alcun file.

---

### Edge Cases

- **Link con alias** `[[nome|alias]]`: dopo lo spostamento l'alias visualizzato resta invariato, cambia
  solo il bersaglio.
- **Link relativi Markdown** verso la pagina spostata: riscritti come i wikilink.
- **Sorgente inesistente** per lo spostamento: errore esplicito, nessuna modifica.
- **Successore dell'obsoleta** dichiarato nel campo frontmatter `superseded_by` (decisione di design
  D6: fonte deterministica, solo frontmatter — il parsing di un banner nel corpo è scartato perché
  euristico); assente → campo successore vuoto, non un errore.
- **Pagine senza campo `status`**: non compaiono nella riconciliazione e nell'inventario il campo è
  semplicemente assente.
- **Nessuna pagina superata**: risultato "pulito", non un errore.

## Requirements *(mandatory)*

### Functional Requirements

**Gruppo B — spostamento sicuro con riscrittura dei link**

- **FR-001** (REQ-010): Il sistema MUST spostare una pagina wiki dalla sorgente alla destinazione (entro
  la radice del wiki) e riscrivere ogni wikilink (`[[nome]]` e `[[nome|alias]]`) e link relativo che
  risolve alla pagina spostata, in ogni altra pagina, così che tutti i link restino validi.
- **FR-002** (REQ-011): Al completamento, il sistema MUST restituire un risultato conforme a un contratto
  versionato `wiki.move/1` con: sorgente, destinazione, elenco dei file riscritti e conteggio delle
  occorrenze sostituite in ciascuno.
- **FR-003** (REQ-012): In modalità anteprima (`--dry-run`), il sistema MUST calcolare e restituire il
  piano completo (file da spostare, link da riscrivere, conteggi) **senza** modificare alcun file.
- **FR-004** (REQ-013): Se la destinazione esiste già come file, il sistema MUST fallire con un errore
  esplicito (nessuna sovrascrittura silenziosa) lasciando tutti i file invariati.
- **FR-005** (REQ-014): A fronte di uno stato parziale (file spostato, link non ancora tutti riscritti),
  una nuova invocazione con gli stessi parametri MUST rilevarlo e completare la riscrittura invece di
  fallire (idempotenza/recovery).
- **FR-006** (REQ-015): Lo spostamento MUST operare senza rete, LLM o servizi esterni e MUST risolvere i
  wikilink con la **stessa logica di slug-matching** usata dal lint esistente, così che spostamento e
  lint formino una coppia coerente (dopo uno spostamento, il lint non riporta link rotti aggiuntivi).

**Gruppo C — riconciliazione delle obsolescenze (sola lettura) + inventario con `status`**

- **FR-007** (REQ-021): L'inventario delle pagine (`collect`) MUST includere il valore del campo
  frontmatter `status` (se presente) nei metadati per pagina del contratto `wiki.collect/1`, come campo
  aggiuntivo forward-compatible.
- **FR-008** (REQ-020): Il comando di riconciliazione MUST enumerare tutte le pagine con `status:
  superseded` e riportarle come candidate all'obsolescenza, con percorso e (dove presente) data `updated`.
- **FR-009** (REQ-022): Al completamento, il sistema MUST restituire un risultato conforme a un contratto
  versionato `wiki.reconcile/1` con, per ogni candidata: percorso, valore di `status`, data `updated`,
  pagina successore dichiarata (dove presente, nel frontmatter o nel banner di supersession) e un campo
  `reason`; il comando MUST NOT eseguire alcuna modifica.
- **FR-010** (REQ-023/027): Il comando di riconciliazione MUST NOT cancellare, sovrascrivere o modificare
  alcuna pagina in autonomia; il contenuto di una pagina superata MUST restare su disco finché un agente
  o l'utente non ne richiede esplicitamente la rimozione/trasformazione (la risoluzione è fuori dal
  comando).
- **FR-011** (REQ-025): Se non esiste alcuna pagina con `status: superseded`, il comando MUST restituire
  una lista vuota e un indicatore esplicito di stato "pulito", senza errore.
- **FR-012** (REQ-026): Il comando di riconciliazione MUST operare in modo deterministico e offline (no
  rete, no LLM), sicuro come health-check senza effetti collaterali.

**Gruppo D — riconciliazione periodica (Could)**

- **FR-013** (REQ-028, Could): Il sistema SHOULD documentare come invocare la riconciliazione (sola
  detection) su pianificazione dell'**ambiente ospite** (es. cron, Task Scheduler, hook CI) verso una
  destinazione configurata; il prodotto MUST NOT incorporare un proprio scheduler.

**Trasversali**

- **FR-014**: I nuovi contratti (`wiki.move/1`, `wiki.reconcile/1`) e l'estensione di `wiki.collect/1`
  MUST essere forward-compatible: un consumatore che conosce solo il campo `schema` MUST continuare a
  deserializzare senza errori.
- **FR-015**: Tutti i comandi MUST restare host-agnostici: ciò che varia tra ospiti deriva dalla config
  del wiki, nessun percorso/nome/lingua è cablato nel corpo dei comandi.

### Key Entities *(include if feature involves data)*

- **Pagina wiki**: file Markdown con frontmatter; campi rilevanti qui: `status` (es. `superseded`),
  `updated`, eventuale successore; più i wikilink/link entranti da altre pagine.
- **Piano di spostamento** (`wiki.move/1`): sorgente, destinazione, file riscritti e conteggi.
- **Candidata all'obsolescenza** (`wiki.reconcile/1`): percorso, `status`, `updated`, successore, motivo.
- **Voce di inventario** (`wiki.collect/1`): metadati per pagina, ora inclusivi di `status`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dopo uno spostamento, il **100%** dei link entranti alla pagina punta alla nuova sede e un
  lint successivo riporta **zero** link rotti aggiuntivi.
- **SC-002**: In modalità anteprima, lo spostamento modifica **zero** file pur riportando il piano completo.
- **SC-003**: Con destinazione già esistente, lo spostamento fallisce e modifica **zero** file.
- **SC-004**: Uno spostamento interrotto, rieseguito, arriva a uno stato finale **identico** a quello di
  un'esecuzione non interrotta (idempotenza).
- **SC-005**: La riconciliazione elenca **esattamente** le pagine `status: superseded` (nessun falso
  positivo, nessuna omissione) e modifica **zero** file.
- **SC-006**: L'inventario include `status` quando presente; un consumatore che conosce solo `schema`
  continua a leggere il risultato senza errori (forward-compatibilità verificata).
- **SC-007**: Su wiki senza pagine superate, la riconciliazione restituisce lista vuota + "pulito" con
  esito di successo.
- **SC-008**: Tutti i comandi completano **senza rete e senza LLM** (eseguibili come health-check offline).

## Assumptions

- **Gruppi E ed F fuori ambito**: seed localizzati e asset in inglese sono **già consegnati** (PR
  #27/#28/#29, record retroattivo `requirements/sertor-cli/tema-lingua-runtime/`); questa feature non
  li ritocca. Il gruppo A (probe di freschezza) è **Won't** (D1).
- **Successore della pagina superata** (D6 risolta): letto **solo** dal campo frontmatter
  `superseded_by` (path/slug della pagina che sostituisce); deterministico. Il banner nel corpo è
  scartato (euristico). Se `superseded_by` è assente, il campo successore è vuoto (non un errore).
- **Slug-matching condiviso**: lo spostamento riusa la logica di risoluzione dei wikilink già usata dal
  lint, per garantire coerenza `move`↔`lint`.
- **`status` è già un campo opzionale** dichiarato nel template di config installato; le pagine possono
  averlo o meno.
- **Risoluzione delle obsolescenze esclusa**: fondere/aggiornare/potare le pagine superate è giudizio,
  fuori da questa feature; la riconciliazione si ferma alla detection.
- **Scheduling fuori prodotto**: il trigger periodico (D) è documentazione + delega all'ambiente ospite;
  nessuno scheduler incorporato (host-agnostico).
