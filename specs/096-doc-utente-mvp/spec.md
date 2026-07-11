# Feature Specification: Documentazione utente MVP (getting-started unico + README di valore)

**Feature Branch**: `096-doc-utente-mvp`

**Created**: 2026-07-11

**Status**: Draft

**Input**: E13 `documentazione-marketing` Fase 1, item di audit **A-18**. Consegna i due Must
dell'epica — **FEAT-001** (getting-started unico e consolidato) + **FEAT-002** (README orientato al
valore) — come un'unica feature accoppiata (coppia MVP di Fase 1). Requisiti di dettaglio in
[`requirements/documentazione-marketing/doc-utente-mvp/requirements.md`](../../requirements/documentazione-marketing/doc-utente-mvp/requirements.md)
(REQ-001..015).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dal nulla al primo valore, un solo percorso (Priority: P1)

Un utente nuovo, su un repo qualunque (Claude Code o Copilot CLI), apre **un solo documento**
(`docs/getting-started.md`) e lo segue in linea retta: prerequisiti → `sertor install rag` → `index` →
**prima query**. Al termine ha un retrieval funzionante e ha **visto** cosa lo rende diverso — una
query che gli restituisce **codice e documento insieme**. Non ha dovuto scegliere l'assistente in
cima, né leggere `specs/` o gli internals, né ricomporre a mano pezzi da file diversi.

**Why this priority**: è il criterio di successo primario dell'epica (CS-1) e la ragione di A-18. Senza
un ingresso unico, «funziona se sai dove guardare» resta il difetto.

**Independent Test**: partendo da `docs/getting-started.md` da solo, un lettore raggiunge il primo
retrieval eseguendo solo i comandi mostrati (copiati dai vehicle reali), senza aprire altri file se non
i rimandi espliciti al dettaglio per-assistente. Consegna valore anche se US2 non esiste.

**Acceptance Scenarios**:

1. **Given** un repo non configurato e nessuna conoscenza pregressa di Sertor, **When** il lettore
   segue `docs/getting-started.md` dall'alto in basso, **Then** raggiunge un primo retrieval
   funzionante usando solo i comandi mostrati.
2. **Given** il lettore è arrivato in fondo al getting-started, **When** esegue l'esempio finale,
   **Then** vede un risultato che contiene **sia codice sia documentazione** (la superficie fusa
   `search_combined`), a dimostrazione del differenziatore.
3. **Given** il lettore usa un assistente specifico (Claude o Copilot), **When** il percorso diverge
   per assistente, **Then** il getting-started lo rimanda al doc per-assistente giusto invece di
   duplicarne il contenuto.

---

### User Story 2 - Il «perché» a colpo d'occhio, senza gergo (Priority: P1)

Uno stakeholder o un non-addetto apre il `README.md` e, **in pochi minuti e senza gergo**, capisce
**cos'è Sertor e perché conviene**: il differenziatore — la **fusione code+doc** in un unico corpus
(*il codice dice cosa fa, la documentazione dice perché*) — è la **prima cosa** che legge, mostrata con
**un esempio concreto**, non solo affermata. Da lì sa dove andare per iniziare (un solo link).

**Why this priority**: è il secondo criterio di successo (CS-2/CS-3) e la prima impressione del
prodotto. Un README che apre con l'elenco delle feature non comunica il valore.

**Independent Test**: un lettore non-tecnico, leggendo solo l'apertura del README, sa dire con parole
proprie cos'è Sertor e qual è il suo differenziatore, e trova un unico punto d'ingresso per iniziare.
Consegna valore anche se US1 non esiste.

**Acceptance Scenarios**:

1. **Given** un lettore che non conosce Sertor, **When** legge l'apertura del README, **Then** il primo
   messaggio è il differenziatore fusione code+doc, prima di ogni elenco di feature o status.
2. **Given** il README, **When** il lettore cerca la prova del differenziatore, **Then** trova almeno un
   **esempio concreto** di una query che restituisce codice + documento insieme.
3. **Given** un lettore convinto a provare, **When** cerca da dove iniziare, **Then** il README rimanda a
   `docs/getting-started.md` come **ingresso unico**.

---

### User Story 3 - Convergenza dei doc esistenti sull'ingresso unico (Priority: P2)

I documenti esistenti (`install-claude.md`, `install-copilot.md`, `retrieval.md`) e il reference
completo (`install.md`) **convergono** sul getting-started: chi entra da uno di essi trova il rimando al
percorso unico, e chi entra dal getting-started trova i rimandi al dettaglio/reference — **senza
contenuto duplicato** e **senza fatti in deriva** dai comandi reali.

**Why this priority**: garantisce che l'MVP non crei un settimo doc scollegato ma **riordini** ciò che
c'è (CS-1/CS-5) evitando duplicazione (R-1) e drift (R-2).

**Independent Test**: navigando dai doc esistenti si raggiunge il getting-started e viceversa; nessun
comando mostrato diverge dai vehicle reali; il link/lint check è verde.

**Acceptance Scenarios**:

1. **Given** i doc per-assistente e il reference, **When** un lettore ci entra, **Then** trova un
   rimando coerente al getting-started come punto d'ingresso.
2. **Given** l'intero insieme dei doc utente, **When** si esegue il link/lint check, **Then** non ci sono
   link interni rotti né riferimenti pendenti.

---

### Edge Cases

- **Contenuto duplicato tra getting-started e per-assistente:** il getting-started deve *delegare* il
  dettaglio divergente, non ricopiarlo (R-1) — se un blocco esiste identico in due file, è un difetto.
- **Comando mostrato che non esiste / è cambiato:** se un comando nel doc non corrisponde a un vehicle
  reale, non va incluso (REQ-014). Se durante l'authoring emerge un comando errato negli asset, è un
  **finding** da segnalare, non da «aggiustare nella doc» mascherando il problema.
- **README che perde un fatto accurato** riscrivendo in chiave valore: i fatti di capacità/status
  esistenti vanno **preservati** riordinati, non cancellati (R-3).
- **Esposizione di artefatti interni:** un rimando che porta il lettore dentro `wiki/` o `specs/` come se
  fossero doc utente viola la separazione (REQ-013) — vietato.

## Requirements *(mandatory)*

### Functional Requirements

<!-- Tracciano REQ-001..015 di requirements.md. -->

- **FR-001**: `docs/getting-started.md` MUST presentare un **percorso unico host-agnostico** da repo non
  configurato al primo retrieval, senza far scegliere l'assistente in cima (REQ-001).
- **FR-002**: Il getting-started MUST coprire, **in ordine**, quattro tappe — prerequisiti, install RAG,
  index, prima query — come un unico viaggio lineare (REQ-002).
- **FR-003**: Dove il percorso diverge per assistente (Claude vs Copilot), il getting-started MUST
  **delegare** il dettaglio a `install-claude.md`/`install-copilot.md` invece di duplicarlo (REQ-003).
- **FR-004**: Il getting-started MUST **terminare con un esempio concreto** di fusione code+doc: una
  query che restituisce codice e documentazione insieme (la superficie fusa `search_combined`) (REQ-004).
- **FR-005**: Il getting-started MUST rimandare a `docs/install.md` come reference completo di flag/manopole
  e a `docs/retrieval.md` per i concetti hybrid-vs-graph, **assorbendo e ordinando**, non ripetendo per
  intero (REQ-005).
- **FR-006**: `README.md` MUST **aprire** con la proposta di valore guidata dal differenziatore fusione
  code+doc, **prima** degli elenchi di feature e status (REQ-006).
- **FR-007**: Il README MUST rendere il «perché» comprensibile a un non-addetto in pochi minuti, **senza
  gergo** (REQ-007).
- **FR-008**: Il README MUST includere **almeno un esempio concreto** del differenziatore (una query che
  restituisce codice e documentazione insieme) (REQ-008).
- **FR-009**: Il README MUST puntare a `docs/getting-started.md` come **ingresso unico** per iniziare
  (REQ-009).
- **FR-010**: Il README MUST **preservare i fatti** accurati di capacità/status già presenti (nessuna
  regressione informativa), riordinati sotto la narrazione di valore (REQ-010).
- **FR-011**: Entrambi gli artefatti MUST essere **host-agnostici** (validi per Claude e Copilot); il
  contenuto specifico d'assistente MUST vivere solo nei doc di dettaglio per-assistente (REQ-011).
- **FR-012**: Ogni comando mostrato MUST essere un'invocazione **reale e corrente** dei vehicle, copiata
  dagli asset/doc reali (`uvx --from … sertor install rag`, `uv run --project .sertor sertor-rag index .`,
  `… sertor-rag search …`), non inventata (REQ-012).
- **FR-013**: Se un rimando presentasse un artefatto **interno** (`wiki/`, `specs/`) come doc utente,
  allora NON deve farlo; i doc utente MUST essere autosufficienti senza gli internals (REQ-013).
- **FR-014**: Se un comando o un claim non è verificabile contro un vehicle/asset reale, allora NON va
  incluso (anti-drift, Principio XII) (REQ-014).
- **FR-015**: Entrambi gli artefatti MUST superare il **link/lint check** della documentazione del repo
  (nessun link interno rotto, nessun riferimento pendente) (REQ-015).

### Key Entities

- **`docs/getting-started.md`** (nuovo) — il documento d'ingresso unico host-agnostico; contiene il
  percorso a quattro tappe e l'esempio finale code+doc; delega il dettaglio ai per-assistente e al
  reference.
- **`README.md`** (riscritto) — il pitch di valore in radice; apre col differenziatore + esempio, poi
  capacità/status preservati, poi puntatore all'ingresso unico.
- **Doc esistenti** (`install-claude.md`, `install-copilot.md`, `retrieval.md`, `install.md`) — invariati
  nella sostanza ma **riallineati** con un rimando al getting-started (convergenza, no duplicazione).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un lettore raggiunge il **primo retrieval funzionante** seguendo **un solo documento**
  (`docs/getting-started.md`) ed eseguendo **solo** i comandi mostrati, senza aprire `specs/` né gli
  internals (CS-1).
- **SC-002**: Un lettore non-tecnico, dalla **sola apertura** del README, sa enunciare cos'è Sertor e il
  suo differenziatore; l'apertura non contiene gergo non spiegato (CS-2).
- **SC-003**: Il differenziatore fusione code+doc è dimostrato con **≥ 1 esempio concreto** (una query che
  restituisce codice + documento insieme) sia nel getting-started sia nel README (CS-3).
- **SC-004**: **100% dei comandi** mostrati nei due artefatti corrisponde a un vehicle/asset reale del
  repo; il link/lint check dei doc è **verde** (0 link interni rotti) (CS-4).
- **SC-005**: **Zero** riferimenti che espongono `wiki/` o `specs/` come doc utente; i due artefatti sono
  autosufficienti (CS-5).
- **SC-006**: **Zero** blocchi di contenuto duplicati verbatim tra `getting-started.md` e i doc
  per-assistente (il dettaglio divergente è delegato, non copiato).

## Assumptions

- **A-1**: Il differenziatore (fusione code+doc) è **già reale e misurabile** (epica `retrieval-qualita`);
  qui lo si **comunica**, non lo si dimostra da capo.
- **A-2**: La distribuzione resta **interim `git+url`** (repo privato, niente PyPI); gli esempi non
  assumono la pubblicità del repo.
- **A-3**: Esiste un **link/lint check** applicabile a `docs/` (da confermare in plan quale strumento
  copre `docs/` oltre al lint del wiki — DA-4/REQ-015).
- **A-4** *(confermata in clarify 2026-07-11, DA-1)*: gli esempi comando del getting-started mostrano
  **entrambe le varianti affiancate** — Claude (`--assistant` omesso) **e** Copilot
  (`--assistant copilot-cli`) — per essere esplicitamente host-agnostici, accettando i blocchi
  raddoppiati dove il comando diverge. Il dettaglio pieno resta delegato ai per-assistente (FR-003).
- **A-5** *(confermata in clarify 2026-07-11, DA-2)*: l'esempio concreto code+doc è **illustrativo
  generico e host-agnostico** (query sul repo dell'utente, con la forma dei due flussi `docs`/`code` di
  `search_combined`), non una query legata al corpus di Sertor (DA-2).
- **A-6**: Nessuna modifica a codice/vehicle/installer: è authoring di documentazione statica (D↔N,
  NFR-3). Un eventuale comando errato negli asset è un finding, non parte dello scope.
