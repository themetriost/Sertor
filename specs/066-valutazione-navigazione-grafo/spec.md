# Feature Specification: Valutazione della navigazione del grafo (set-based) (FEAT-011)

**Feature Branch**: `066-valutazione-navigazione-grafo` · **Created**: 2026-06-20 · **Status**: Draft

<!-- Deriva da: FEAT-011 (epica retrieval-qualita) -->

**Input**: Deriva da `requirements/retrieval-qualita/valutazione-navigazione-grafo/requirements.md`
(FEAT-011, epica `retrieval-qualita`, Must; con Gruppi E/F Should e relazioni `depends_on`/`related_docs`
Could). Vedi anche `requirements/retrieval-qualita/epic.md` (FEAT-011 nel backlog §8) e la feature gemella
`specs/065-ground-truth-valutazione/spec.md` (FEAT-001, harness IR su `master`). La feature rende
**misurabile** la potenza relazionale del code-graph: trasforma «la navigazione funziona» (oggi esercitata
solo da unit test interni all'adapter) in «la navigazione è misurata e presidiata» come capacità
host-side, versionata e ripetibile via vehicle.

---

> **Perché serve (problema).** L'harness di valutazione esistente (FEAT-001, su `master`) misura la
> **rilevanza IR**: data una `query → [path attesi]`, segna un *hit* se un risultato compare in cima a un
> **ranking** (`hit-rate@k`/`MRR`). Provando dal vivo la skill `eval-feedback` su una query **relazionale**
> — *«chi chiama X / cosa definisce X / da cosa dipende X»* — è emerso che quell'harness **non sa
> esprimerla**: la risposta corretta a una domanda relazionale è un **insieme** di simboli/nomi (senza
> ordine, senza path-ranking), non «quale file è primo». La **navigazione** del grafo esiste già e funziona
> (porta `CodeGraph` con `find_symbol`/`who_calls`/`related_docs`/`get_context`); manca la sua
> **valutazione** come capacità del prodotto. La potenza relazionale del grafo è oggi **completamente non
> misurata**.

> **Confine vincolante (D↔N).** Il **run deterministico** (esecuzione dei casi, metriche a insiemi,
> non-regressione) vive nel core/CLI e accede al grafo **solo via vehicle** (Principio XI): mai un import di
> `sertor_core` fuori dai test, mai una chiamata LLM. La **genesi assistita** dei casi (snapshot proposto da
> approvare) è una superficie di **giudizio** (skill dell'agente), separata dal run. Le due metà non si
> mescolano: il run resta riproducibile e indipendente da qualunque LLM.

> **«LLM» = l'agente dell'utente via skill** (chiarimento terminologico vincolante, come in FEAT-001). Nel
> contesto di questa feature «LLM»/«delegare a un LLM» indica l'**agente conversazionale** (es. Claude) che
> opera tramite una **skill** e usa gli strumenti del progetto; **non** una chiamata programmatica a un
> servizio LLM dentro il core/CLI. Il core e il comando di esecuzione **non chiamano mai un LLM** (la genesi
> dei casi è solo uno **snapshot deterministico** dell'output del grafo, presentato dall'agente per
> approvazione).

> **Ancoraggio all'esistente (dato di partenza, non dettaglio da progettare).** La navigazione esiste già —
> porta `CodeGraph` e adapter `NetworkxCodeGraph`, factory `build_graph_service`, i 4 tool MCP. L'harness
> deterministico di FEAT-001 esiste — servizio `services/eval/` + `engines/evaluation.py`, suite e baseline
> in `eval/` versionato. Questa feature **estende** quell'harness con un **secondo oracolo** (a insiemi) per
> i casi relazionali, **senza** toccare i casi e le metriche path-based esistenti. I riferimenti a
> file/simboli servono ad **ancorare** i requisiti all'esistente, non a prescrivere il *come*.

> **Additività (Principi I/III, local-first).** A capacità spenta, comportamento e **costo** del sistema
> restano identici a oggi; `sertor-core` resta invariato fuori dai moduli nuovi. Le suite, baseline e
> metriche IR esistenti continuano a funzionare senza modifiche. Il run è **deterministico, locale, senza
> alcun LLM** e non richiede rete.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Misuro se il grafo restituisce l'insieme giusto (P1, Must)
Owner/maintainer di un progetto ospite indicizzato col RAG di Sertor: vuole sapere se la navigazione del
grafo per una relazione (es. *«chi chiama questo simbolo»*) restituisce **l'insieme corretto** di
riferimenti, non «quale file è in cima». Scrive (o fa proporre) casi di navigazione `relazione + simbolo
target → insieme atteso di riferimenti`, li versiona accanto ai casi di retrieval, e li **ri-esegue** via
vehicle per ottenere `precision`/`recall`/`F1` deterministici.

**Independent Test**: su un progetto indicizzato con una suite di pochi casi di navigazione, due esecuzioni
a parità di grafo/suite danno **metriche a insiemi identiche** (report umano + JSON); ogni caso espone il
dettaglio `expected`/`got`/`missing`/`extra` per la diagnosi.

**Acceptance**:
1. **Given** un progetto indicizzato con il grafo costruito e una suite versionata di casi di navigazione
   `relazione + simbolo → insieme atteso di riferimenti`, **When** eseguo il comando di valutazione,
   **Then** ogni caso produce `precision`/`recall`/`F1` sull'insieme — **senza rank né @k** — con dettaglio
   per-caso `expected`/`got`/`missing`/`extra`.
2. **Given** la stessa suite e lo stesso grafo, **When** ri-eseguo il comando, **Then** le metriche sono
   **identiche** (determinismo).
3. **Given** un caso `who_calls`, **When** lo eseguo, **Then** il sistema naviga il grafo all'**insieme dei
   chiamanti** del simbolo target e lo confronta con l'insieme atteso.
4. **Given** un caso `defines`, **When** lo eseguo, **Then** il sistema naviga il grafo all'**insieme delle
   definizioni** del simbolo target e lo confronta con l'insieme atteso.
5. **Given** il grafo non costruito, **When** eseguo i casi di navigazione, **Then** il comando **fallisce
   con un messaggio azionabile** («costruisci prima l'indice»), non riporta un punteggio privo di senso.
6. **Given** un simbolo target assente dal grafo, **When** eseguo il caso, **Then** il sistema tratta
   l'insieme navigato come **insieme vuoto** (assenza legittima) e lo confronta con l'atteso **senza
   errore**.

### User Story 2 — La navigazione è presidiata da un gate di non-regressione (P1, Must)
L'utente registra le metriche di navigazione correnti come **riferimento** separato (distinto dalla
baseline IR). Da quel momento, un'esecuzione in cui le metriche di navigazione **degradano** oltre la
tolleranza configurata **fallisce** con stato non-zero, così un cambiamento all'estrazione/traversata del
grafo che peggiora gli insiemi non passa inosservato.

**Independent Test**: registrata la baseline di navigazione, degradando artificialmente la navigazione
(suite invariata) il comando **segnala la regressione ed esce con stato non-zero**; entro tolleranza esce
zero; senza baseline registrata il gate **passa** (niente da confrontare).

**Acceptance**:
1. **Given** una suite di navigazione valutata, **When** registro la baseline, **Then** le metriche di
   navigazione sono salvate come **riferimento versionato separato** dalla baseline IR.
2. **Given** un riferimento di navigazione esistente e metriche che scendono **oltre la tolleranza**,
   **When** valuto, **Then** il comando **esce con stato non-zero** (gate), coerente col gate IR esistente;
   entro tolleranza esce zero.
3. **Given** nessun riferimento di navigazione registrato, **When** valuto, **Then** il gate **passa**
   (nulla da confrontare), senza fallire.
4. **Given** un report con entrambi i tipi di caso, **When** lo leggo, **Then** le metriche di navigazione
   appaiono in una **sezione distinta** da quelle di retrieval (`hit@k`/`MRR`).

### User Story 3 — Genesi assistita: l'agente propone l'insieme dal grafo (P2, Should)
L'utente, invece di elencare a mano l'insieme atteso, **delega all'agente** (via skill `eval-suite-author`
estesa) la proposta: l'agente **esegue la navigazione corrente** del grafo per la relazione+simbolo e
**presenta il risultato come insieme candidato** da approvare. Approvato una volta, l'insieme viene
**congelato** come sentinella di regressione.

**Independent Test**: per una relazione+simbolo su un grafo costruito, l'agente propone un **insieme
candidato** (lo snapshot deterministico della navigazione corrente); l'utente lo approva e **solo allora**
il caso viene persistito via vehicle; con il grafo non costruito la proposta **fallisce azionabile**.

**Acceptance**:
1. **Given** un grafo costruito e una relazione+simbolo, **When** l'utente delega all'agente la genesi,
   **Then** l'agente **esegue la navigazione corrente** e presenta il suo risultato come **insieme
   candidato** per l'approvazione.
2. **Given** un caso candidato, **When** l'utente lo approva, **Then** il caso è persistito **solo via
   vehicle** e **solo dopo approvazione esplicita** (nessuna scrittura implicita o automatica).
3. **Given** la scrittura di un caso di navigazione, **When** lo si autora, **Then** il sistema **valida i
   riferimenti attesi contro il grafo** e **nomina** quelli che non può verificare.
4. **Given** la genesi assistita, **When** la si esercita, **Then** essa resta una **superficie di giudizio
   (skill)** separata dal run deterministico: né il core né il comando di esecuzione invocano mai un LLM.

### User Story 4 — La capacità è installabile su un ospite (P1, Must)
Su un **progetto terzo** (non Sertor), dopo `sertor install`, l'utente crea/esegue la suite di navigazione e
registra la baseline **senza copiare file da Sertor**: la suite di navigazione vive nel suo repo come dato
versionato del progetto; eventuali manopole/skill arrivano dall'installer.

**Independent Test**: su un host pulito, dopo `sertor install`, la suite di navigazione si crea, si esegue e
produce metriche a insiemi; suite e baseline di navigazione sono memorizzate **dentro il progetto ospite**;
nessun import del codice di test di Sertor è necessario.

**Acceptance**:
1. **Given** un host pulito dopo `sertor install`, **When** creo ed eseguo la suite di navigazione,
   **Then** funziona senza copiare file da Sertor; suite e baseline sono **dentro il progetto ospite**, in
   `eval/` versionato.
2. **Given** che la feature introduce manopole di configurazione o asset host-facing (skill estesa),
   **When** si installa, **Then** essi sono **cablati nell'installer** (es. template `.env`, `sertor
   install`), così l'ospite li ottiene **dal percorso di installazione**.
3. **Given** le leve di questa feature disabilitate/non usate, **When** si indicizza e si cerca, **Then**
   comportamento e **costo** sono **identici a oggi** (additivo, Principi I/III); le suite/baseline/metriche
   IR esistenti restano valide.

### Edge Cases
- **Grafo non costruito al run** — il comando **fallisce azionabile** («costruisci prima l'indice»), non
  riporta un punteggio fasullo. *(REQ-013)*
- **Simbolo target assente dal grafo** — l'insieme navigato è l'**insieme vuoto** (assenza legittima),
  confrontato con l'atteso **senza errore** (recall 0 se l'atteso era non vuoto; non un crash). *(REQ-014)*
- **Caso malformato** — un `[[graph_case]]` privo di `relation`, `target` o `expected` fa **fallire il
  caricamento della suite** con un messaggio che **identifica il caso** offendente. *(REQ-004)*
- **Relazione non supportata** — un caso che dichiara una relazione fuori dall'insieme MVP
  (`who_calls`/`defines`) **rifiuta la suite** con messaggio azionabile. *(REQ-005)*
- **Riferimento atteso non verificabile in genesi** — quando si autora un caso, i `ref` attesi che il grafo
  non conferma sono **nominati** (avviso), non persistiti silenziosamente come validi. *(REQ-042)*
- **Snapshot fragile** — un cambiamento *legittimo* dell'estrazione/traversata cambia l'insieme: la
  sentinella si **ri-congela su conferma esplicita** (re-record della baseline), come per l'eval IR. *(R-1)*
- **`ref` instabile ai refactor** — rinominare un simbolo/file cambia il `ref` atteso: è **dato versionato**
  e si aggiorna col refactor (diff visibile). *(R-2)*
- **Determinismo del run** — stesso grafo + stessa suite → stesse metriche, sempre. *(REQ-015)*
- **Segreti** — suite e baseline di navigazione sono **dati versionati del progetto**, mai output
  rigenerabile gitignored: nessun segreto vi è incorporato. *(RNF-5)*

## Requirements *(mandatory)*
Fonte autorevole: `requirements/retrieval-qualita/valutazione-navigazione-grafo/requirements.md`
(REQ-001..061, gruppi A–G; RNF-1..5). In sintesi (mappatura per gruppo):

- **A — Artefatto: il caso di navigazione (Must):** un caso = **relazione + simbolo target + insieme atteso
  di riferimenti**, come **dato versionato** del progetto (REQ-001); memorizzato nel **medesimo artefatto
  eval** dei casi di retrieval, come **tipo di caso distinto**, **senza alterare** i casi path-based
  esistenti (REQ-002); ogni nodo atteso identificato da un **riferimento stabile** (path + qualified name),
  non da un nome nudo (REQ-003); caso privo di relazione/target/atteso → **fallimento di caricamento** che
  nomina il caso (REQ-004); relazione fuori dall'insieme supportato → **suite rifiutata** con messaggio
  azionabile (REQ-005).
- **B — Esecuzione via vehicle (Must, deterministica):** i casi si eseguono **navigando il grafo via
  vehicle (CLI)**, **senza import del core** a runtime — Principio XI (REQ-010); `who_calls` → insieme dei
  **chiamanti** (REQ-011); `defines` → insieme delle **definizioni** (REQ-012); grafo non costruito →
  **fallisce azionabile** (REQ-013); target assente → **insieme vuoto** confrontato senza errore (REQ-014);
  **determinismo** a parità di suite/grafo (REQ-015).
- **C — Metriche a insiemi (Must per 020/021/023; Should per 022):** ogni caso valutato per **confronto di
  insiemi**, riportando `precision`/`recall`/`F1` — **senza rank né @k** (REQ-020); aggregazione a livello
  suite delle metriche a insiemi (REQ-021); **gate match-esatto opzionale** (caso fallito se l'insieme non
  è uguale all'atteso) (REQ-022, Should); **dettaglio per-caso** `expected`/`got`/`missing`/`extra`
  (REQ-023).
- **D — Report e non-regressione (Must):** metriche di navigazione in una **sezione distinta** dalle IR
  (REQ-030); **baseline registrabile separata** da quella IR (REQ-031); sotto baseline oltre tolleranza →
  **exit non-zero**, coerente col gate esistente (REQ-032); **nessuna baseline registrata → gate passa**
  (REQ-033).
- **E — Genesi assistita (Should, *giudizio*):** l'agente (via skill) propone i casi **eseguendo la
  navigazione corrente** e presentandone il risultato come **insieme candidato** da approvare (REQ-040);
  persistenza **solo via vehicle** e **solo dopo approvazione esplicita** (REQ-041); in authoring i `ref`
  attesi sono **validati contro il grafo** e i non verificabili **nominati** (REQ-042).
- **F — Osservabilità (Should):** evento di osservabilità **metrics-only** per un run di navigazione, senza
  nomi di simboli, path o testo libero — **gemello** dell'evento `eval` esistente (REQ-050).
- **G — Host-side / installabile (Must per 060; Should per 061):** capacità usabile su **qualunque host
  indicizzato** via vehicle, con la suite di navigazione come **dato versionato del progetto** — Principio X
  (REQ-060); eventuali manopole nuove (tolleranza metrica-grafo, gate match-esatto) **incluse nel template
  `.env`** dell'installer (REQ-061, Should).

### Requisiti non funzionali (sintesi)
- **RNF-1 (additività):** a capacità spenta, comportamento e costo identici a oggi; `sertor-core` invariato
  fuori dai moduli nuovi (entità eval additive, runner nuovo, factory).
- **RNF-2 (determinismo/local-first):** run deterministico, locale, **senza alcun LLM**; nessun accesso di
  rete necessario per la misura.
- **RNF-3 (privacy):** l'evento di osservabilità è **metrics-only**; nomi/path/insiemi non compaiono mai
  nella telemetria (vivono solo nell'artefatto-dato versionato e nel report umano locale).
- **RNF-4 (compatibilità):** suite, baseline e metriche IR esistenti (FEAT-001) restano valide e
  non-breaking; il nuovo tipo di caso convive nello stesso artefatto.
- **RNF-5 (dato non output):** la suite di navigazione è **dato di progetto versionato** in `eval/`, non
  artefatto rigenerabile in una sede gitignored.

### Key Entities
- **Caso di navigazione del grafo** *(artefatto-dato del progetto)* — `relazione` (MVP:
  `who_calls`/`defines`), `simbolo target`, `insieme atteso di riferimenti`; tipo di caso **distinto** dai
  casi path-based, **nello stesso artefatto eval** versionato.
- **Riferimento di nodo (`ref`)** — identità **stabile** di un nodo del grafo: path + qualified name (es.
  `path#qualname`), non un nome nudo; chiave dell'insieme atteso e di quello navigato.
- **Insieme navigato** — l'insieme dei `ref` restituito dalla navigazione corrente del grafo per
  relazione+target; può essere **vuoto** (assenza legittima).
- **Metrica a insiemi** — `precision`/`recall`/`F1` dal confronto insieme-navigato↔insieme-atteso; **senza
  rank né @k**; con dettaglio `missing`/`extra`; aggregabile a livello suite.
- **Riferimento (baseline) di navigazione** *(artefatto-dato del progetto)* — metriche di navigazione
  registrate come livello da non degradare, **separato** dalla baseline IR; aggiornabile solo su
  accettazione esplicita.
- **Report di navigazione** — esito del run: metriche a insiemi + dettaglio per-caso, in **sezione
  distinta** da quella IR; reso in forma umana e macchina (JSON).
- **Esito di non-regressione (grafo)** — confronto misura↔baseline con tolleranza, e **stato d'uscita**
  utilizzabile come gate.
- **Candidato (genesi assistita)** — insieme atteso **proposto** dall'agente come snapshot della
  navigazione corrente, in attesa di approvazione; non persistito finché non approvato.

## Success Criteria *(mandatory)*
- **SC-001 (oracolo a insiemi deterministico):** su un grafo costruito con una suite di navigazione
  versionata, il comando misura la correttezza per **confronto di insiemi** via vehicle, producendo
  `precision`/`recall`/`F1` con dettaglio `expected`/`got`/`missing`/`extra`; **due esecuzioni** a parità di
  grafo/suite danno **metriche identiche**, **senza rank né @k**. *(REQ-010/015/020/023; CS-1)*
- **SC-002 (metrica graduata + additività):** ogni caso produce `precision`/`recall`/`F1` sull'insieme;
  **spegnendo la capacità**, comportamento e **costo** del sistema restano **identici a oggi** e le
  suite/metriche IR esistenti non cambiano. *(REQ-020/021; RNF-1; CS-2)*
- **SC-003 (non-regressione separata):** registrata la baseline di navigazione (separata dalla IR),
  **degradando** artificialmente la navigazione (suite invariata) il comando **segnala la regressione ed
  esce non-zero**; entro tolleranza esce zero; **senza baseline → gate passa**. *(REQ-031/032/033; CS-3)*
- **SC-004 (host-side):** su un progetto terzo indicizzato, la suite di navigazione si crea, si versiona nel
  suo repo (`eval/`) e si usa via vehicle **senza alcun import del codice di test** di Sertor né dipendenza
  da un LLM. *(REQ-001/002/060; CS-4)*
- **SC-005 (via vehicle, niente LLM nel run):** il run accede al grafo **solo via vehicle**; né il core né
  il comando di esecuzione importano `sertor_core` fuori test né invocano un LLM. *(REQ-010; Principio XI)*
- **SC-006 (genesi proposta, non imposta):** l'agente propone l'insieme come **snapshot** della navigazione
  corrente; **solo dopo approvazione esplicita** il caso è persistito via vehicle, e i `ref` non
  verificabili sono **nominati**. *(REQ-040/041/042)*
- **SC-007 (report distinto):** le metriche di navigazione appaiono in una **sezione distinta** da quelle
  IR (`hit@k`/`MRR`) nel report. *(REQ-030)*
- **SC-008 (assenze gestite):** grafo non costruito → **fallimento azionabile**; target assente →
  **insieme vuoto** scorato senza errore. *(REQ-013/014)*
- **SC-009 (osservabilità metrics-only):** un run di navigazione emette un evento **metrics-only** che non
  porta nomi/path/insiemi/testo libero (gemello dell'evento `eval`). *(REQ-050; RNF-3)*
- **SC-010 (installabile):** su un host pulito, dopo `sertor install`, suite/baseline di navigazione si
  creano/usano dal percorso di installazione; eventuali manopole/asset host-facing sono nell'installer.
  *(REQ-060/061)*

## Assumptions
- **Indice e grafo presenti prima dell'uso.** Si assume il progetto **già indicizzato** con il **code-graph
  costruito** (default `SERTOR_GRAPH=true`) prima di eseguire o autorare i casi di navigazione; il grafo non
  costruito è un errore azionabile, non uno zero ingannevole (REQ-013).
- **`ref` come identità stabile.** Si assume che il `ref` (`path#qualname`) sia la chiave d'identità stabile
  esposta dai risultati del grafo, e che l'insieme atteso di un caso viva nel solo perimetro del grafo del
  corpus indicizzato.
- **«LLM» = agente dell'utente via skill**, non un servizio LLM terzo nel codice. Il core e il comando di
  esecuzione non chiamano mai un LLM; la genesi è uno **snapshot deterministico** dell'output del grafo,
  presentato per approvazione.
- **Estensione, non reinvenzione.** La feature **estende** l'harness eval di FEAT-001 (servizio
  `services/eval/`, suite/baseline in `eval/`) con un secondo oracolo a insiemi e un secondo tipo di caso,
  **senza** toccare i casi e le metriche path-based esistenti (RNF-4); riusa la navigazione esistente
  (porta `CodeGraph`, `build_graph_service`).
- **Dipendenza installer.** La distribuzione su ospite riusa il percorso `sertor install` /
  `sertor-install-kit` (manopole nel template `.env`, skill estesa).
- **Confine osservabilità.** Questa feature **produce** la misura puntuale e l'evento metrics-only; la
  **storicizzazione/trend** delle metriche è dell'epica `osservabilita` (fuori ambito).

### Fuori ambito (dichiarato)
- Le relazioni **`depends_on`/callees** (via `get_context`) e **`related_docs`** (unità = documento, non
  simbolo): **rinviate** (Could), da non perdere — vedi promozione sotto.
- Il **miglioramento** della qualità della navigazione o dell'estrazione del grafo: questa feature
  **misura**, non ridefinisce il grafo — è dell'epica `sertor-core`.
- Le **metriche IR** (`hit@k`/`MRR`) e i casi **path-based**: restano FEAT-001, **invariati**.
- La **storicizzazione/trend** delle metriche nel tempo: epica `osservabilita`.
- Qualunque metrica di **ordine/rank/@k** per la navigazione (concettualmente sbagliata per una risposta a
  insiemi): **Won't**.
- Il **come** (schema TOML preciso, moduli, firme, nomi di comando/manopola, struttura del codice): fase di
  **design/plan**.

> **Tracciamento dello scope (regola «gli Out-of-Scope si promuovono»).** Le relazioni rinviate
> (`depends_on`/callees via `get_context`, `related_docs` con unità documento) e un eventuale comando di
> *refresh* assistito dello snapshot sono **Could** già registrati nel backlog d'epica e nella MoSCoW dei
> requisiti (`requirements/retrieval-qualita/valutazione-navigazione-grafo/requirements.md` §9;
> `requirements/retrieval-qualita/epic.md` §8). Al `plan`, se una di queste cresce in capacità reale, resta
> tracciata lì; nessun rinvio reale vive solo dentro `specs/`.

### Forche di design (NON risolte qui — per `/speckit-clarify` o `/speckit-plan`)
Sono questioni di **come**, fuori dal *cosa/perché* della spec; menzionate per non seppellirle. **Le forche
di scope A–E dei requisiti sono già decise** (vedi sotto) e **non** sono qui.
- **DA-a — Tolleranza sugli insiemi (gate):** la non-regressione (REQ-032) si valuta su quale **metrica
  aggregata** (F1 medio? recall medio?) e con quale tolleranza di default? *(Design.)*
- **DA-b — `related_docs` come relazione futura:** quando entrerà (Could), l'unità è il **documento**
  (path), non il simbolo: condivide la metrica a insiemi o ha un proprio oracolo/report? *(Design, alla
  promozione dal Could.)*
- **DA-c — Workflow di re-congelamento dello snapshot:** un cambiamento *legittimo* del grafo come si
  riapprova — stesso `--record-baseline` esteso, o un verbo dedicato per gli insiemi? *(Design.)*
- **DA-d — File singolo vs dedicato:** `[[graph_case]]` in `eval/suite.toml` insieme ai `[[case]]`, oppure
  un `eval/graph_suite.toml` separato? (Deciso A = stesso file; **da confermare in design** se
  dimensione/leggibilità suggeriscono lo split.)

> **Decisioni di scope già risolte (utente, 2026-06-20) — riportate come vincoli, NON come domande.**
> **A (schema):** tabella TOML **separata** `[[graph_case]]` (relation, target, expected = insieme di
> `ref`), nello **stesso** `eval/suite.toml`, **senza** alterare i `[[case]]`. **B (metrica):** graduata
> `precision`/`recall`/`F1` sull'insieme + **match-esatto** come gate opzionale; **niente @k/MRR**.
> **C (relazioni MVP):** `who_calls` + `defines`; `depends_on`/callees e `related_docs` rinviati (Could).
> **D (identità nodo):** per `ref` (`path#qualname`). **E (genesi):** snapshot-bootstrap dall'output
> corrente del grafo (deterministico) → proposto, approvato una volta → congelato come sentinella; skill
> `eval-suite-author` estesa; confine D↔N (run nel core/CLI; genesi = giudizio/skill).
