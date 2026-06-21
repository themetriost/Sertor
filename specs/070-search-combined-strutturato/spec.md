# Feature Specification: `search_combined` a contratto strutturato (due flussi etichettati) — Tempo 2 FEAT-003

**Feature Branch**: `070-search-combined-strutturato` · **Created**: 2026-06-21 · **Status**: Draft

<!-- Deriva da: FEAT-003 (epica retrieval-qualita) — Tempo 2 (refactor strutturale) -->

**Input**: Tempo 2 di **FEAT-003** (epica `retrieval-qualita`). Il Tempo 1
(`specs/069-qualita-fusione-code-doc/spec.md`) ha reso **misurabile** la fusione code+doc e ha **misurato**
che la superficie fusa `search_combined` **non funziona** per il caso-firma requisito→implementazione:
**fusion coverage 0.17 (1 caso su 6)**. Questa feature **ripara la causa**: cambia il **contratto** di
`search_combined` da una lista unica blended a una **coppia strutturata di due flussi etichettati** (`docs`
e `code`), **ciascuno col proprio top-k**. Vedi `requirements/retrieval-qualita/epic.md`.

---

> **Stella polare (gate «Allineamento alla missione», costituzione v1.4.0) — riportata nella spec.** Il
> differenziatore di Sertor è la **fusione di codice e documenti**: *il codice dice cosa fa, la
> documentazione dice perché*. `search_combined` **è** la superficie-firma di quella fusione. Oggi è
> **rotta** (fusion coverage 0.17): la lista unica blended fa **annegare il codice** sotto i documenti.
> Questa feature non aggiunge un concern periferico — **ripara la stella polare**: rende strutturalmente
> possibile che una query architetturale/«requisiti» restituisca **doc + codice insieme**.

> **Natura del cambiamento: BREAKING CHANGE volontario (dichiarato).** Cambiare il tipo di ritorno di
> `search_combined` è una **deviazione consapevole dall'additività** (Principi I/III). È **giustificata**
> dal **Principio XII (fix the cause, not the symptom)** e dal **gate «Allineamento alla missione»**: la
> superficie blended è rotta alla radice — si **ripara** la causa (score code/doc incommensurabili,
> budget condiviso), **non** si affianca una versione corretta lasciando viva quella rotta. Il **nome
> resta `search_combined`**. Il refactor è ammissibile perché **tutti i consumatori sono di prima parte e
> nel repo** e il progetto è **pre-1.0** a distribuzione `git+url`: **nessun contratto pubblico stabile**
> da preservare.

> **Causa-radice (misurata, non ipotetica).** Oggi `search_combined` fonde doc e code in **una sola lista
> ranked con budget condiviso** (`_search(..., "both")` in `src/sertor_core/services/retrieval.py`). Gli
> score code/doc sono **incommensurabili** — come dense vs BM25, per cui l'ibrido usa RRF — e i documenti,
> essendo prosa NL vicina alla query NL, **annegano** il codice. Misurare la fusione su una lista unica è
> una **congiunzione su budget condiviso** (servono entrambi nello **stesso** top-k contesato):
> strutturalmente fragile. Due budget separati la trasformano da congiunzione su slot contesi a **unione
> di due top-k indipendenti**.

> **Confine / altitudine (D↔N, mission).** Il core **riserva i due flussi etichettati** — *il cosa*
> (code) e *il perché* (doc) — e li rende all'agente; la **sintesi** la fa l'agente consumatore (MCP/CLI),
> coerente con la missione (generare/servire **delegati** all'agente frontier; il core fornisce la
> **qualità del retrieval reso**). Smettere di fingere che un ranking blended cross-tipo abbia senso è
> **alzare l'altitudine al posto giusto**, non rinunciare a una capacità: la lista unica resta disponibile
> via un helper di cortesia.

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Le superfici esistono:
> `search_code` / `search_docs` / `search_combined` in `src/sertor_core/services/retrieval.py` (oggi tutte
> ritornano `list[RetrievalResult]`). I consumatori di prima parte di `search_combined` sono: il tool MCP
> `search_combined` (`src/sertor_mcp/server.py`), la CLI (`src/sertor_core/cli/__main__.py` +
> `cli/output.py`), il fused-eval runner (`src/sertor_core/services/eval/fused_runner.py`,
> `services/eval/fusion.py`) e i test. La metrica di **fusion coverage** e il set NL fuso esistono dal
> Tempo 1. I riferimenti a file servono ad **ancorare** i requisiti, non a prescrivere il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ottengo i due flussi etichettati in un giro, senza che un tipo anneghi l'altro (P1, Must)
Un consumatore (agente via MCP, o utente via CLI) chiede a `search_combined` la fusione code+doc per una
query NL/architetturale. Invece di una lista unica in cui i documenti soppiantano il codice, riceve una
**coppia strutturata**: due liste etichettate, `docs` e `code`, **ciascuna col proprio top-k** (budget
separato). Vede *il perché* (doc) **e** *il cosa* (code) affiancati, e decide come sintetizzarli.

**Independent Test**: su un progetto indicizzato, una query requisito→implementazione a `search_combined`
restituisce **entrambe** le liste etichettate, ciascuna popolata fino al proprio top-k; la lista `code`
**non** è vuota per il fatto che i documenti hanno score più alti (il difetto del budget condiviso non si
ripresenta).

**Acceptance**:
1. **Given** un indice con code+doc, **When** invoco `search_combined`, **Then** ottengo una **coppia
   strutturata** con due liste etichettate `docs` e `code`, **ciascuna col proprio top-k** (budget
   separato, non condiviso).
2. **Given** una query NL vicina alla prosa dei documenti, **When** invoco `search_combined`, **Then** la
   lista `code` è popolata secondo il **proprio** budget e **non** annegata dai documenti.
3. **Given** la coppia strutturata, **When** il consumatore vuole una lista sola, **Then** un **helper di
   cortesia** (`flatten()`) produce una lista unica **deterministica** dalle due liste.
4. **Given** lo stesso indice e la stessa query, **When** ri-invoco `search_combined`, **Then** il
   risultato (entrambe le liste e il `flatten()`) è **identico** (determinismo; nessun LLM oltre
   l'embedder).

### User Story 2 — `search_code` e `search_docs` restano invariati (P1, Must)
Chi usa le superfici mono-tipo non subisce alcun cambiamento: `search_code` e `search_docs` continuano a
rispondere come oggi (query su una sola superficie, una sola lista di risultati). Solo `search_combined`
— la chiamata «dammi **entrambi** i flussi etichettati in un giro» — cambia forma.

**Independent Test**: le chiamate a `search_code` e a `search_docs`, a parità di indice/query, producono
lo **stesso** tipo di risultato e gli **stessi** valori di prima del refactor.

**Acceptance**:
1. **Given** un indice, **When** invoco `search_code` o `search_docs`, **Then** il contratto (forma del
   ritorno) e i risultati sono **invariati** rispetto a oggi.
2. **Given** il refactor di `search_combined`, **When** esamino le superfici mono-tipo, **Then** **solo**
   `search_combined` ha contratto nuovo; `search_code`/`search_docs` non sono toccate.

### User Story 3 — Tutti i consumatori di prima parte sono aggiornati e coerenti (P1, Must)
Poiché è un breaking change, ogni chiamante di `search_combined` nel repo è aggiornato **in blocco** al
nuovo contratto: il tool MCP, la CLI (esecuzione e resa), il fused-eval runner e i test. Nessun chiamante
resta rotto; la capacità «lista unica» non si perde (resta via `flatten()`).

**Independent Test**: dopo il refactor, la suite è **verde** e il lint **pulito**; non esiste alcun
chiamante di `search_combined` che assuma ancora il vecchio contratto a lista unica.

**Acceptance**:
1. **Given** il nuovo contratto, **When** ispeziono i consumatori di prima parte (MCP, CLI, eval, test),
   **Then** ciascuno consuma la **coppia strutturata** (o `flatten()` dove serve una lista) ed è coerente.
2. **Given** il MCP / la CLI, **When** mostrano i risultati di `search_combined`, **Then** i due flussi
   sono **etichettati** (`docs` / `code`) nella resa, così l'utente/agente vede entrambi.
3. **Given** la suite di test, **When** la eseguo dopo il refactor, **Then** è **verde** e il lint è
   **pulito**, senza alcun chiamante rotto.

### User Story 4 — La fusione misurata migliora rispetto alla baseline 0.17 (P1, Must)
È l'obiettivo che giustifica il refactor: misurata sui casi-fusione del set NL (Tempo 1), la **fusion
coverage** adattata ai due flussi **migliora** rispetto alla baseline 0.17. La metrica si adatta: un caso
è coperto quando la lista `docs` contiene un documento pertinente **nel suo top-k** **E** la lista `code`
contiene un sorgente pertinente **nel suo top-k**. La baseline fusa va **ri-registrata** sul nuovo valore.

**Independent Test**: eseguendo il fused-eval sul set NL con il nuovo contratto, la fusion coverage sui
casi-fusione **supera** 0.17; il valore è deterministico e riproducibile.

**Acceptance**:
1. **Given** i casi-fusione del set NL e l'indice, **When** eseguo il fused-eval col nuovo contratto,
   **Then** la **fusion coverage migliora** rispetto alla baseline misurata di 0.17.
2. **Given** la metrica adattata ai due flussi, **When** misuro, **Then** un caso conta **coperto** solo
   se la lista `docs` ha un doc pertinente nel suo top-k **E** la lista `code` ha un code pertinente nel
   suo top-k (unione di due top-k, non congiunzione su slot contesi).
3. **Given** il cambio di contratto, **When** si stabilizza il nuovo valore, **Then** la **baseline fusa
   è ri-registrata** sul nuovo numero (la baseline precedente non vale più).

## Edge Cases
- **Una sola superficie ha risultati** (es. indice senza codice, o query puramente doc): `search_combined`
  ritorna comunque la **coppia**, con una lista popolata e l'altra **vuota** (forma sempre strutturata).
- **`flatten()` su coppia con una lista vuota**: produce la lista non vuota, deterministicamente; su due
  liste vuote produce una lista vuota.
- **Consumatore che vuole ancora una lista unica**: usa `flatten()` — la capacità non si perde, cambia
  solo il punto in cui si compone.
- **Caso-fusione coperto su una lista ma non sull'altra**: conta **miss** su fusion coverage (servono
  entrambi i flussi, ciascuno nel proprio top-k).
- **Determinismo**: stesso indice + stessa query → stessa coppia e stesso `flatten()`, sempre; nessun LLM
  nel run oltre l'embedder.

## Requirements *(mandatory)*

### Requisiti funzionali
- **FR-001 (contratto strutturato).** `search_combined` ritorna una **coppia strutturata** di due liste
  etichettate — `docs` e `code` — **ciascuna col proprio top-k** (budget separato), **non** una singola
  lista blended a budget condiviso. Il **nome resta `search_combined`**.
- **FR-002 (helper `flatten()`).** La coppia strutturata espone un **helper di cortesia `flatten()`** che
  compone una **lista unica deterministica** (concat/interleave) per chi vuole una sola lista; la capacità
  «lista unica» **non si perde**.
- **FR-003 (mono-tipo invariate).** `search_code` e `search_docs` **non cambiano** contratto né
  comportamento: restano query mono-superficie che ritornano una sola lista, come oggi.
- **FR-004 (consumatori aggiornati in blocco).** Tutti i consumatori di prima parte di `search_combined`
  nel repo sono aggiornati al nuovo contratto e restano **coerenti**: tool MCP `search_combined`, CLI
  (esecuzione + resa), fused-eval runner/fusione, test. **Nessun chiamante rotto.**
- **FR-005 (resa etichettata).** Dove `search_combined` viene presentata (MCP/CLI), i due flussi sono
  **etichettati** (`docs` / `code`), così il consumatore vede entrambi distintamente.
- **FR-006 (fusion coverage adattata).** La metrica di **fusion coverage** si adatta ai due flussi: un
  caso-fusione è **coperto** solo se la lista `docs` contiene un doc pertinente nel **proprio** top-k **E**
  la lista `code` contiene un code pertinente nel **proprio** top-k. Resta significativa e riportata
  accanto a hit-rate@k/MRR.
- **FR-007 (baseline fusa ri-registrata).** Poiché il valore di fusion coverage cambia con il contratto,
  la **baseline fusa è ri-registrata** sul nuovo numero; le baseline per-superficie (FEAT-001/011) e i
  casi esistenti restano validi e protetti.
- **FR-008 (miglioramento misurato).** Sui casi-fusione del set NL, la fusion coverage misurata col nuovo
  contratto **migliora** rispetto alla baseline 0.17 (è l'obiettivo del refactor; nessun «migliore» senza
  numero).
- **FR-009 (determinismo / vehicle).** Il run di misura resta **deterministico** e accede al retrieval
  **solo via vehicle** (`sertor-rag eval`, Principio XI); nessun LLM nel run oltre l'embedder.

### Requisiti non funzionali
- **RNF-1 (deviazione additività dichiarata).** Questo è un **breaking change** di `search_combined`:
  deviazione **volontaria** dall'additività (Principi I/III), **giustificata** dal **Principio XII** e dal
  gate «Allineamento alla missione». La deviazione è circoscritta a `search_combined` e ai suoi consumatori
  di prima parte; `search_code`/`search_docs` e il resto di `sertor-core` restano invariati.
- **RNF-2 (misurabilità).** Il valore del refactor si **dimostra con un numero** (fusion coverage > 0.17;
  Principio V); nessun claim di miglioramento senza misura.
- **RNF-3 (local-first / deterministico).** La misura gira in **locale** (mock/Chroma), ripetibile, senza
  rete; nessun LLM nel run oltre l'embedder (Principio II).
- **RNF-4 (mission-alignment).** Il refactor **rafforza la fusione code+doc**: rende strutturalmente
  possibile che un caso requisito→implementazione renda doc+codice insieme (stella polare).
- **RNF-5 (suite verde, lint pulito).** Dopo il refactor la suite di test è **verde** e il lint
  **pulito**; nessun chiamante di prima parte resta rotto.

### Key Entities
- **Risultato fuso strutturato** — coppia di due liste etichettate `docs` e `code`, **ciascuna col
  proprio top-k**; è il nuovo ritorno di `search_combined`. (Forma esatta dell'entità = design/plan; es.
  `FusedResults(docs=[...], code=[...])`.)
- **Helper `flatten()`** — operazione di cortesia sulla coppia che produce una **lista unica
  deterministica** (concat/interleave) per i consumatori che vogliono un solo elenco.
- **Risultato mono-tipo** — la lista di risultati invariata di `search_code` / `search_docs`.
- **Metrica di fusion coverage (adattata)** — «coperto» = doc pertinente nel top-k della lista `docs`
  **E** code pertinente nel top-k della lista `code`; riportata accanto a hit-rate@k/MRR.
- **Baseline fusa (ri-registrata)** — nuovo riferimento di fusion coverage del progetto dopo il cambio di
  contratto; livello da non degradare in seguito.

## Success Criteria *(mandatory)*
- **SC-001 (due flussi etichettati col proprio top-k):** `search_combined` ritorna la coppia strutturata
  `docs`/`code`, ciascuna col proprio top-k (budget separato). *(FR-001)*
- **SC-002 (mono-tipo invariate):** `search_code` e `search_docs` restano invariate per contratto e
  risultati. *(FR-003)*
- **SC-003 (`flatten()` deterministico):** `flatten()` produce una lista unica deterministica dalle due
  liste; ri-eseguito a parità di input dà lo stesso ordine. *(FR-002)*
- **SC-004 (fusione migliora):** sui casi-fusione del set NL, la fusion coverage misurata col nuovo
  contratto **supera** la baseline 0.17. *(FR-006/FR-008; obiettivo del refactor)*
- **SC-005 (baseline fusa ri-registrata):** la baseline fusa è ri-registrata sul nuovo valore; baseline
  per-superficie e casi esistenti restano protetti. *(FR-007)*
- **SC-006 (nessun chiamante rotto):** tutti i consumatori di prima parte (MCP, CLI, eval, test) sono
  aggiornati e coerenti; suite **verde**, lint **pulito**. *(FR-004/RNF-5)*
- **SC-007 (resa etichettata):** MCP e CLI mostrano i due flussi etichettati `docs`/`code`. *(FR-005)*
- **SC-008 (determinismo / via vehicle):** la misura passa per `sertor-rag eval`, è deterministica e non
  invoca alcun LLM oltre l'embedder. *(FR-009/RNF-3; Principio XI)*
- **SC-009 (mission-alignment verificabile):** un caso requisito→implementazione che rende doc+codice
  insieme è ora misurabile come coperto, dimostrando il rafforzamento della fusione code+doc. *(RNF-4;
  gate «Allineamento alla missione»)*
- **SC-010 (deviazione additività dichiarata e circoscritta):** la deviazione dall'additività è
  documentata come scelta motivata (Principio XII + gate missione) ed è circoscritta a `search_combined` e
  ai suoi consumatori di prima parte; il resto di `sertor-core` è invariato. *(RNF-1)*

## Assumptions
- **Tutti i consumatori di `search_combined` sono di prima parte e nel repo.** Pre-1.0, distribuzione
  `git+url`: **nessun contratto pubblico stabile** da preservare → il breaking change è gestibile in
  blocco. (Verificato: MCP `server.py`, CLI `cli/__main__.py`+`cli/output.py`, eval `fused_runner.py`+
  `fusion.py`, test.)
- **Set NL e metrica di fusione esistono già** dal Tempo 1 (FEAT-003, `069`); questa feature ne **adatta**
  la fusion coverage ai due flussi e **ri-registra** la baseline, non li reinventa.
- **«LLM» = agente dell'utente**, non un servizio LLM terzo nel codice. Il core e il comando di misura non
  chiamano mai un LLM; l'unico modello nel run è l'**embedder**.
- **Indice presente prima dell'uso.** Il progetto è già indicizzato prima di misurare.
- **Corollario installabile.** Eventuali manopole host-facing (es. k separati per `docs`/`code`) andranno
  cablate nel template `.env` di `sertor install` — *deciso in design se introdotte*.

### Fuori ambito (dichiarato)
- **Miglioramento della qualità per-superficie di `search_docs`** (MRR 0.55) — leva successiva, non qui.
- **Tecniche di miglioramento** (HyDE/query transformation, contextual retrieval, filtro metadata esteso):
  **FEAT-005/006/007** dell'epica.
- **Eval su provider forte/cloud** (marker `cloud`): **FEAT-002** — qui local-first.
- **Calibrazione delle soglie** `SERTOR_MIN_SCORE` (astensione): **FEAT-004**, ortogonale.
- **Il *come* di dettaglio** — forma esatta dell'entità di ritorno, allocazione esatta dei k per
  `docs`/`code`, strategia di `flatten()` (concat vs interleave), schema di serializzazione MCP/CLI,
  formato della baseline ri-registrata: fase di **design/plan**.

> **Tracciamento dello scope (regola «gli Out-of-Scope si promuovono»).** Le tecniche avanzate e il
> miglioramento per-superficie di `search_docs` sono già **promossi** a casa durevole nel backlog d'epica
> (`requirements/retrieval-qualita/epic.md`, FEAT-002/004/005/006/007). Nessun rinvio reale vive solo
> dentro `specs/`.

### Forche di design (NON risolte qui — per `/speckit-plan`)
Questioni di **come**, fuori dal *cosa/perché*. **Nessuna cambia lo scope** (il contratto strutturato a
due flussi con `flatten()` è deciso).
- **DA-a — Forma esatta dell'entità di ritorno** (es. `FusedResults(docs, code)`: dataclass/namedtuple,
  campi, eventuale metadato). *Design.*
- **DA-b — Allocazione dei k** per `docs` e `code` (k unico applicato a entrambe, k distinti configurabili,
  default). *Design; se introduce manopole host-facing → template `.env`.*
- **DA-c — Strategia di `flatten()`** (concat doc-then-code, interleave per rank, ordinamento): purché
  **deterministica** (FR-002). *Design.*
- **DA-d — Serializzazione MCP/CLI** dei due flussi etichettati e forma del report fused-eval aggiornato.
  *Design.*
