# Feature Specification: Qualità del retrieval fuso code+doc su query NL/architetturali (FEAT-003)

**Feature Branch**: `069-qualita-fusione-code-doc` · **Created**: 2026-06-21 · **Status**: Draft

<!-- Deriva da: FEAT-003 (epica retrieval-qualita) -->

**Input**: Deriva da `requirements/retrieval-qualita/qualita-search-code-nl/requirements.md` (FEAT-003,
epica `retrieval-qualita`, REQ-001..043, gruppi A–E, RNF1–5, DA-a..e). Vedi anche
`requirements/retrieval-qualita/epic.md`. La feature rende **misurabile e migliorabile** la qualità del
retrieval **fuso code+doc** — il differenziatore di Sertor — sulle query NL/architetturali, *prima* di
introdurre tecniche di miglioramento, così che ogni «miglioramento» sia ancorato a un numero.

---

> **Stella polare (gate «Allineamento alla missione», costituzione v1.4.0) — riportata nella spec.** Il
> differenziatore di Sertor è la **fusione di codice e documenti** in un unico corpus: *il codice dice
> cosa fa, la documentazione dice perché*. Questa feature **rafforza** direttamente quella fusione —
> rende verificabile con un numero che una query architetturale/«requisiti» restituisca **doc + codice
> insieme**, e impedisce che un tipo **anneghi** l'altro. È la capacità-firma della mission
> (requisito→implementazione), non un concern periferico.

> **Natura empirica / ordine di valore (vincolante).** Il cuore Must di questa feature è
> l'**infrastruttura di misura**, non un cambio di codice di retrieval: un set NL multi-superficie con
> attesi *intent-typed*, una **categoria dedicata** per i casi cross-artefatto, una **metrica di fusion
> coverage**, **baseline per-superficie** e il **gate di non-regressione**. «Migliorare» **non** è una
> tecnica prescritta a monte: è il ciclo **misura → confronto leve → adotta solo ciò che mostra un lift
> misurato**. Le leve (query transformation/HyDE, filtro metadata, contextual retrieval) si scelgono
> **dopo** aver visto le baseline e restano **spente di default** finché un cambio di default non è
> deciso esplicitamente.

> **Confine vincolante (D↔N).** Il **run di misura** (esecuzione del set, metriche per-superficie,
> fusion coverage, non-regressione) è **deterministico** e accede al retrieval **solo via vehicle**
> (`sertor-rag eval`, Principio XI): nessun import di engine fuori dai test, nessuna chiamata LLM nel run
> oltre l'**embedder** (unico modello). La **genesi del set NL** e il **giudizio sulle leve** (cosa è
> «pertinente», quale intento, quale «needs both») sono superfici di **giudizio** (skill
> `eval-suite-author` / utente), separate dal run.

> **Ancoraggio all'esistente (dato di partenza, non dettaglio da progettare).** L'harness di valutazione
> esiste già su `master` (FEAT-001/011): `evaluate()/EvalReport` in `src/sertor_core/engines/evaluation.py`,
> il servizio `src/sertor_core/services/eval/`, la suite-dato `eval/suite.toml`, il vehicle `sertor-rag
> eval`. Le superfici di ricerca esistono: `search_code` / `search_docs` / `search_combined` in
> `src/sertor_core/services/retrieval.py`, motore in `src/sertor_core/engines/hybrid.py`. La **fusion
> coverage** e la **categoria fusione** sono una metrica/categoria **nuova e additiva** sull'harness: lo
> **estendono**, non lo reinventano. I riferimenti a file servono ad **ancorare** i requisiti, non a
> prescrivere il *come*.

> **Additività (Principi I/III, local-first).** A leve spente, indice, comportamento di ricerca e
> **costo** restano identici a oggi. La misura gira in **locale** (mock/Chroma) senza richiedere il
> cloud; il confronto sul provider forte è **fuori ambito** (FEAT-002).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Misuro onestamente la fusione code+doc del mio progetto (P1, Must)
Owner/maintainer di un progetto indicizzato: vuole sapere, con un numero, se una query NL/architetturale
restituisce **insieme** la documentazione (il *perché*) e il sorgente (il *cosa*). Dispone di un set di
query NL versionato in cui ogni query ha un **risultato atteso coerente con il suo intento** — *«dove è
definito»* → sorgente, *«perché/come funziona»* → documentazione, *«quali requisiti e dove sono
implementati»* → **entrambi**. Esegue la misura e ottiene, **accanto** a hit-rate@k/MRR, una **fusion
coverage** che conta un caso come coperto **solo** quando il top-k contiene **almeno un documento
pertinente E almeno un sorgente pertinente**.

**Independent Test**: su un progetto indicizzato con un set NL curato (con casi doc-oriented,
code-oriented e cross-artefatto etichettati per intento), eseguendo la misura si ottengono hit-rate@k,
MRR **e** fusion coverage; un caso cross-artefatto il cui top-k contiene **solo** doc (o solo codice)
risulta **hit** su hit@k ma **miss** su fusion coverage — la lacuna è esplicitamente visibile.

**Acceptance**:
1. **Given** un set NL versionato con attesi *intent-typed* (source/doc/entrambi) e una categoria
   distinta per i casi cross-artefatto, **When** eseguo la misura, **Then** ottengo hit-rate@k, MRR **e**
   fusion coverage, con la fusion coverage **riportata accanto** alle altre metriche.
2. **Given** un caso di fusione il cui top-k soddisfa hit@k ma **manca** uno dei due tipi richiesti,
   **When** misuro, **Then** quel caso conta come **miss su fusion coverage** (hit@k da solo non nasconde
   la lacuna).
3. **Given** lo stesso set e lo stesso indice, **When** ri-eseguo la misura, **Then** i numeri sono
   **identici** (determinismo, nessun LLM nel run oltre l'embedder).
4. **Given** una query NL a cui non si può assegnare un atteso coerente con l'intento, **When** si
   costruisce il set, **Then** essa è **esclusa** anziché valutata contro un bersaglio arbitrario.

### User Story 2 — Registro baseline per-superficie e presidio la non-regressione (P1, Must)
Prima di toccare qualunque cosa, l'utente registra **baseline distinte** di `search_code`, `search_docs`
e `search_combined` sul set NL. Da quel momento, ogni esecuzione che scende sotto una di quelle baseline
(o sui casi/baseline esistenti di FEAT-001/011) oltre tolleranza **fallisce** (gate). La
`search_combined` è misurata come **test d'integrazione** dei guadagni per-superficie.

**Independent Test**: registrate le tre baseline per-superficie, una misura ripetuta a parità di
indice/set le rispetta (exit zero); degradando artificialmente una superficie il gate **segnala la
regressione ed esce non-zero**; i casi/baseline preesistenti restano validi e protetti.

**Acceptance**:
1. **Given** il set NL e l'indice, **When** registro le baseline, **Then** sono memorizzate **distinte
   per superficie** (`search_code`, `search_docs`, `search_combined`) come riferimento del progetto.
2. **Given** baseline registrate, **When** una misura scende sotto una baseline per-superficie (o sui
   casi/baseline esistenti) oltre tolleranza, **Then** il gate **esce non-zero**; entro tolleranza esce
   zero.
3. **Given** i guadagni per-superficie, **When** misuro `search_combined`, **Then** essa è valutata come
   **test d'integrazione** che verifica che la superficie fusa **integri** quei guadagni (non li perda).

### User Story 3 — Migliore solo con un numero: confronto leve guidato-da-misura (P2, Should)
Vista la baseline, l'utente valuta una o più **leve** opt-in (query transformation/HyDE, filtro metadata
esteso, contextual retrieval) attivandole **una alla volta** sul set, e confronta il risultato
per-superficie e di fusion coverage con la baseline. **Nessuna** leva viene dichiarata un miglioramento
senza un **lift misurato** sulla superficie rilevante; le leve adottate restano **spente di default**
finché un cambio di default non è deciso esplicitamente.

**Independent Test**: attivando una leva opt-in e ri-misurando, il report mostra il delta per-superficie e
di fusion coverage rispetto alla baseline; una leva senza lift misurato **non** è adottata; a leve spente
i numeri tornano identici alla baseline (additività).

**Acceptance**:
1. **Given** una leva di miglioramento NL abilitata, **When** misuro, **Then** essa è applicata e il
   confronto col baseline mostra il **delta per-superficie e di fusion coverage**.
2. **Given** una leva che **non** mostra lift sulla superficie rilevante, **When** valuto, **Then** essa
   **non** è dichiarata un miglioramento e **non** è adottata.
3. **Given** una leva disabilitata, **When** indicizzo e cerco, **Then** **comportamento e costo sono
   identici a oggi** (additivo).
4. **Given** una leva con lift, **When** la si adotta, **Then** resta **spenta di default** finché un
   cambio di default non è giustificato e deciso esplicitamente.

### User Story 4 — Miglioramento effettivo per-superficie (P2, Should)
Scelta la leva che mostra lift, la pertinenza NL di `search_docs` **e** di `search_code` migliora di un
margine **misurabile** rispetto alla rispettiva baseline (si attaccano le cause **isolate** per
superficie, P1.c), senza rompere la fusione misurata sul combined.

**Independent Test**: dopo l'adozione di una leva, la metrica per-superficie di `search_docs` e quella di
`search_code` sul set NL superano la baseline di un margine dichiarato; il combined non regredisce sulla
fusion coverage.

**Acceptance**:
1. **Given** una leva adottata, **When** ri-misuro per-superficie, **Then** `search_docs` **e**
   `search_code` migliorano di un margine **misurabile** rispetto alla baseline.
2. **Given** quel miglioramento, **When** misuro `search_combined`, **Then** la fusion coverage **non
   regredisce** (un guadagno per-superficie che rompe la fusione è respinto, R-3).

### User Story 5 — Genesi assistita del set NL (giudizio, separata dal run) (P2, Should)
L'utente, invece di scrivere a mano ogni query NL con attesi intent-typed, **delega all'agente** (via
skill `eval-suite-author` estesa) la proposta di candidati `query NL → atteso (intent-typed)` **dai
contenuti già indicizzati**, usando i tool di retrieval. L'agente **propone**; l'utente cura/approva;
**solo gli approvati** sono persistiti **via il vehicle**, e il run resta deterministico.

**Independent Test**: a corpus indicizzato, una sessione di authoring assistito produce candidati NL
intent-typed **proposti** (non imposti); solo gli approvati sono persistiti nel set; il run di misura
resta deterministico e non invoca alcun LLM oltre l'embedder.

**Acceptance**:
1. **Given** un corpus indicizzato, **When** l'utente delega la genesi del set NL all'agente, **Then**
   l'agente **propone** candidati `query NL → atteso (intent-typed, inclusi casi «needs both»)` e li
   presenta per revisione.
2. **Given** candidati proposti, **When** l'utente ne approva alcuni, **Then** **solo gli approvati**
   sono persistiti, **via il vehicle**; gli scartati sono ignorati.
3. **Given** la genesi assistita, **When** la si esercita, **Then** essa resta una **superficie di
   giudizio (skill)** separata dal run: né il core né il comando di misura invocano un LLM oltre
   l'embedder (confine D↔N).

### Edge Cases
- **Query NL senza atteso coerente con l'intento** — esclusa dal set, non valutata contro un bersaglio
  arbitrario. *(REQ-004)*
- **Caso di fusione che soddisfa hit@k ma manca un tipo** — conta come **miss su fusion coverage**;
  hit@k da solo non può nascondere la lacuna. *(REQ-022)*
- **Una leva migliora una superficie ma rompe la fusione** — respinta dal gate di non-regressione sul
  combined / fusion coverage. *(REQ-040, R-3)*
- **Leva che costa troppo** — il trade-off costo↔qualità è parte del giudizio di adozione; a leve spente
  il costo è identico a oggi. *(REQ-030, R-3)*
- **Overfitting al set** — set rappresentativo; un hold-out di validazione è una possibilità *Could*.
  *(R-1)*
- **Determinismo del run** — stesso indice + stesso set → stessi numeri, sempre; nessun LLM nel run oltre
  l'embedder. *(REQ-041, RNF-3)*
- **Casi/baseline esistenti** — restano validi e protetti dal gate; questa feature è **additiva**.
  *(REQ-040, RNF-5)*

## Requirements *(mandatory)*
Fonte autorevole: `requirements/retrieval-qualita/qualita-search-code-nl/requirements.md` (REQ-001..043,
gruppi A–E; RNF-1..5). In sintesi (mappatura per gruppo):

- **A — Set NL multi-superficie + categoria fusione (Must):** set NL/architetturale **versionato** con
  attesi che riflettono l'**intento** di ogni query, coprendo casi **doc-oriented**, **code-oriented** e
  **cross-artefatto (requisito→implementazione)** (REQ-001); i casi cross-artefatto/fusione marcati come
  **categoria distinta** misurabile a sé (REQ-002); attesi **intent-typed** — source per «where
  defined», doc per «why/how», **entrambi** per cross-artefatto (REQ-003); una query NL senza atteso
  coerente con l'intento è **esclusa** anziché valutata su un bersaglio arbitrario (REQ-004).
- **B — Misura e miglioramento per-superficie, combined come integrazione (Must B-core / Should
  B-lift):** baseline di pertinenza NL **distinte** per `search_code`, `search_docs`, `search_combined`
  *prima* di ogni intervento (REQ-010, Must); `search_combined` validata come **test d'integrazione** dei
  guadagni per-superficie (REQ-013, Must); nessuna tecnica dichiarata un miglioramento senza un **lift
  misurato** sulla superficie rilevante (REQ-014, Must); miglioramento **misurabile** di `search_docs`
  (REQ-011, Should) e di `search_code` su NL architetturali (REQ-012, Should).
- **C — Metrica di fusione (fusion coverage, Must):** per un caso di fusione/cross-artefatto, un caso
  conta **coperto** solo quando il top-k contiene **≥1 documento pertinente E ≥1 sorgente pertinente**
  (REQ-020); fusion coverage **riportata accanto** a hit-rate@k/MRR così che il fallimento «un tipo
  annega l'altro» sia esplicitamente visibile (REQ-021); un caso che soddisfa hit@k ma manca un tipo
  richiesto conta **miss su fusion coverage** (REQ-022).
- **D — Leve come opt-in additive, scelte per misura (Should):** una leva di miglioramento NL (query
  transformation, filtro metadata esteso, contextual retrieval, …), dove abilitata, è applicata
  lasciando **comportamento e costo invariati a leve spente** (REQ-030); la **scelta e adozione** delle
  leve è **guidata dal confronto misurato** per-superficie e di fusione, **non prescritta a monte**; una
  leva adottata resta **spenta di default** finché un cambio di default non è giustificato e deciso
  esplicitamente (REQ-031).
- **E — Non-regressione, local-first, vehicle, confine D↔N (Must E-core / Should REQ-043):** un
  miglioramento che fa regredire i casi esistenti o le baseline per-superficie/fusione oltre tolleranza è
  **respinto** (gate, REQ-040); la misura resta **local-first e deterministica**, nessun provider cloud
  richiesto (REQ-041); la misura passa per il **vehicle esistente** (`sertor-rag eval`), aggiungendo la
  fusion coverage come metrica **additiva** anziché sostituire hit-rate@k/MRR (REQ-042); dove il set NL è
  prodotto con assistenza dell'agente (`eval-suite-author`), i candidati sono persistiti **solo via il
  vehicle** e il run resta **deterministico** (confine D↔N, nessun LLM nel run oltre l'embedder)
  (REQ-043, Should).

### Requisiti non funzionali (sintesi)
- **RNF-1 (additività):** a leve spente, comportamento e costo identici a oggi; `sertor-core` invariato
  fuori dai punti nuovi (Principi I/III).
- **RNF-2 (misurabilità):** nessun «miglioramento» senza un numero sul ground-truth (Principio V).
- **RNF-3 (local-first/deterministico):** misura locale, ripetibile, senza rete; nessun LLM nel run —
  l'embedder è l'unico modello.
- **RNF-4 (mission-alignment):** la feature **rafforza la fusione code+doc** (stella polare); le metriche
  per-superficie + fusion coverage la rendono verificabile.
- **RNF-5 (no regressione):** casi e baseline esistenti (FEAT-001/011) restano validi.

### Key Entities
- **Set NL/architetturale** *(artefatto-dato del progetto, additivo alla suite esistente)* — insieme di
  casi NL versionati con attesi *intent-typed*; copre doc-oriented, code-oriented e cross-artefatto.
- **Caso NL intent-typed** — `query NL`, `atteso` tipizzato per intento (source / doc / entrambi),
  `intento/categoria`; unità di hit/miss e di fusion coverage.
- **Categoria di fusione (cross-artefatto)** — sottoinsieme distinto dei casi in cui la risposta giusta
  deve **spaziare** documentazione e sorgente; misurabile a sé.
- **Metrica di fusion coverage** — per i casi che richiedono entrambi i tipi: «coperto» solo se il top-k
  contiene ≥1 doc pertinente E ≥1 sorgente pertinente; riportata **accanto** a hit-rate@k/MRR.
- **Baseline per-superficie** *(artefatto-dato del progetto)* — riferimenti distinti di pertinenza NL per
  `search_code`, `search_docs`, `search_combined`; livello da non degradare.
- **Leva di miglioramento (opt-in)** — tecnica NL (query transformation/HyDE, filtro metadata,
  contextual retrieval) abilitabile a misura; spenta di default; valutata per lift.
- **Report di misura esteso** — esito del run: hit-rate@k, MRR, **fusion coverage**, dettaglio
  per-superficie e per-categoria, eventuale confronto baseline↔leva. (Estensione additiva di `EvalReport`.)
- **Esito di non-regressione** — confronto misura↔baseline (per-superficie e fusione) con tolleranza, e
  **stato d'uscita** utilizzabile come gate.

## Success Criteria *(mandatory)*
- **SC-001 (set NL onesto e multi-superficie):** esiste un set NL versionato con attesi **intent-typed**
  che copre query doc-oriented, code-oriented e cross-artefatto, con i casi di fusione in una **categoria
  distinta**. *(REQ-001/002/003; CS-1 epica)*
- **SC-002 (baseline per-superficie):** baseline distinte di `search_code`, `search_docs`,
  `search_combined` sono registrate **prima** di ogni intervento. *(REQ-010; CS-2 epica)*
- **SC-003 (fusion coverage visibile):** la misura riporta la **fusion coverage accanto** a
  hit-rate@k/MRR; un caso che soddisfa hit@k ma manca un tipo richiesto risulta **miss su fusion
  coverage**. *(REQ-020/021/022; CS-4 epica)*
- **SC-004 (determinismo, niente LLM nel run):** due esecuzioni a parità di indice/set danno numeri
  **identici**; il run non invoca alcun LLM oltre l'embedder. *(REQ-041/043, RNF-3)*
- **SC-005 (combined come integrazione):** `search_combined` è misurata come **test d'integrazione** che
  verifica l'integrazione dei guadagni per-superficie senza rompere la fusione. *(REQ-013; CS-4 epica)*
- **SC-006 (nessun «migliore» senza numero):** nessuna tecnica è dichiarata un miglioramento senza un
  **lift misurato** sulla superficie rilevante rispetto alla baseline. *(REQ-014, RNF-2; Principio V)*
- **SC-007 (gate di non-regressione):** un intervento che fa regredire casi/baseline esistenti o le
  baseline per-superficie/fusione oltre tolleranza **esce non-zero** ed è respinto. *(REQ-040; RNF-5)*
- **SC-008 (via vehicle, additiva):** la misura passa per `sertor-rag eval`; la fusion coverage è una
  metrica **additiva** all'harness, non sostituisce hit-rate@k/MRR. *(REQ-042; Principio XI)*
- **SC-009 (additività a leve spente):** con le leve di questa feature disabilitate, indice,
  comportamento di ricerca e **costo** sono **identici a oggi**. *(REQ-030, RNF-1; Principi I/III)*
- **SC-010 (miglioramento per-superficie, Should):** dopo l'adozione di una leva con lift, `search_docs`
  **e** `search_code` migliorano di un margine misurabile sul set NL, senza regressione di fusion
  coverage sul combined. *(REQ-011/012; CS-3 epica)*
- **SC-011 (mission-alignment verificabile):** le metriche per-superficie + fusion coverage rendono
  **verificabile** che la feature rafforza la fusione code+doc (un caso requisito→implementazione che
  restituisce doc+codice insieme è misurato come coperto). *(RNF-4; gate «Allineamento alla missione»)*

## Assumptions
- **Indice presente prima dell'uso.** Il progetto è **già indicizzato** (RAG) prima di costruire il set
  NL ed eseguire la misura; la genesi assistita richiede un indice popolato.
- **«LLM» = agente dell'utente via skill**, non un servizio LLM terzo nel codice. Il core e il comando di
  misura non chiamano mai un LLM; l'unico modello nel run è l'**embedder** del retrieval.
- **Riuso dell'esistente.** La feature **estende** l'harness FEAT-001/011 (`evaluate`/`EvalReport`,
  `services/eval/`, `eval/suite.toml`, `sertor-rag eval`) e le superfici `search_code/docs/combined`; la
  fusion coverage e la categoria fusione sono **additive**.
- **Fasatura empirica.** Il Must è l'**infrastruttura di misura** (set + categoria + fusion coverage +
  baseline + gate). Le **leve** (Should) si scelgono e adottano **dopo** aver visto le baseline; il loro
  *quale/come* è design, deciso dai numeri.
- **Dipendenza installer (corollario installabile).** Eventuali manopole host-facing introdotte dalle
  leve (es. nel template `.env`) vanno cablate in `sertor install`; il set NL e le baseline vivono come
  dati versionati del progetto ospite (come la suite di FEAT-001).

### Fuori ambito (dichiarato)
- Le **modalità** di retrieval in sé (vettoriale/ibrido/grafo/agentico): epica `sertor-core`.
- L'eval **su provider forte/cloud** (marker `cloud`): **FEAT-002** dell'epica — qui local-first.
- La **calibrazione delle soglie** `SERTOR_MIN_SCORE` (governa l'astensione): **FEAT-004**, ortogonale.
- Le tecniche avanzate **come feature a sé** — query transformation/HyDE, filtro metadata esteso,
  contextual retrieval: **FEAT-005/006/007**; qui sono **leve candidate**, non l'oggetto.
- Definizione del **come** (quale tecnica/leva, struttura del codice, schema dell'artefatto, nomi di
  comando/manopola, formula esatta delle soglie di «miglioramento»): fase di **design/plan**.

> **Tracciamento dello scope (regola «gli Out-of-Scope si promuovono»).** Le tecniche avanzate
> (query transformation/HyDE, filtro metadata esteso, contextual retrieval) sono già **promosse** a casa
> durevole nel backlog d'epica come **FEAT-005/006/007** (`requirements/retrieval-qualita/epic.md`); qui
> figurano solo come **leve candidate** da valutare per misura. L'hold-out di validazione formale è una
> capacità *Could* tracciata nei requisiti. Nessun rinvio reale vive solo dentro `specs/`.

### Forche di design (NON risolte qui — per `/speckit-clarify` o `/speckit-plan`)
Sono questioni di **come**, fuori dal *cosa/perché* della spec; menzionate per non seppellirle. **Nessuna
cambia lo scope** (lo scope è l'infrastruttura di misura Must + le leve come opt-in additive Should).
- **DA-a — Quali leve per prime** (query transformation/HyDE vs filtro metadata vs contextual retrieval).
  *Design, guidato dal costo atteso vs lift per-superficie — deciso dai numeri della baseline.*
- **DA-b — Costruzione del set NL** (quante query per superficie; come etichettare intento e «needs both»
  in modo ripetibile; hold-out). *Riuso/estensione di `eval-suite-author`.*
- **DA-c — Soglie di «miglioramento»** (delta minimo per-superficie su hit@k/MRR e soglia di fusion
  coverage) per dichiarare done. *Le costanti sono design; il principio «nessun migliore senza numero» è
  requisito (REQ-014).*
- **DA-d — Rapporto con FEAT-004/005/006/007:** se una leva entra qui, la sua feature dedicata diventa il
  «come»; coordinamento con le soglie di astensione (FEAT-004, ortogonali).
- **DA-e — Valore reale vs agente:** target = migliorare il **single-shot** o documentare il **pattern
  agentico** (l'agente già itera via MCP, R-4). *Decide se è core-work o per lo più documentazione;
  non cambia lo scope Must (la misura serve in entrambi i casi).*
