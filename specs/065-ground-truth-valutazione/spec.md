# Feature Specification: Ground-truth & valutazione della pertinenza (FEAT-001)

**Feature Branch**: `065-ground-truth-valutazione` · **Created**: 2026-06-20 · **Status**: Draft

<!-- Deriva da: FEAT-001 (epica retrieval-qualita) -->

**Input**: Deriva da `requirements/retrieval-qualita/ground-truth-valutazione/requirements.md` (FEAT-001,
epica `retrieval-qualita`, Must; con Gruppi C/F Should promossi a FEAT-008/FEAT-009). Vedi anche
`requirements/retrieval-qualita/epic.md` (criteri di successo CS-1..5). La feature trasforma la
pertinenza del retrieval da impressione a **numero ripetibile** e introduce il **ciclo di vita di una
suite di valutazione** che vive *nel progetto valutato* (host-side), non solo nel dogfood di Sertor.

---

> **Chiarimento terminologico vincolante (utente, 2026-06-20) — riportato nella spec.** In questo
> documento «**LLM**» e «**delegare a un LLM**» indicano **l'agente conversazionale dell'utente** (es.
> Claude) che opera tramite una **skill** e usa gli **strumenti di retrieval del progetto** (RAG/MCP)
> per *leggere* il corpus indicizzato e *proporre* candidati da approvare. **NON** è una chiamata
> programmatica a un servizio LLM terzo dentro `sertor-core`/CLI: **il core e il comando di esecuzione
> non chiamano mai un LLM** (nessun SDK/chiave LLM per la genesi). È lo stesso pattern della skill
> `derive-entity-types`. L'unico LLM «di sistema» resta l'embedder del retrieval; la *generazione/
> ragionamento* dei casi di test è dell'agente, fuori dal core.

> **Confine vincolante (D↔N).** Il **run deterministico** (esecuzione suite, metriche, non-regressione)
> vive nel core/CLI e accede al retrieval **solo via vehicle** (Principio XI): mai un import di engine
> fuori dai test, mai una chiamata LLM. La **genesi assistita** e il **feedback esplicito** sono
> superfici di **giudizio** (skill dell'agente), separate dal run. Le due metà non si mescolano: il run
> resta riproducibile e indipendente da qualunque LLM.

> **Ancoraggio all'esistente (dato di partenza, non dettaglio da progettare).** L'harness deterministico
> esiste già — `evaluate()/EvalReport/QueryableEngine` in `src/sertor_core/engines/evaluation.py`; il
> ground-truth esiste come **fixture di test** (`tests/fixtures/ground_truth.py`, 11 coppie kind
> symbol/nl + `relative_to`); il confronto baseline/ibrido esiste in
> `tests/integration/test_baseline_quality.py`. Questa feature **promuove** quell'harness a capacità di
> prima classe, host-agnostica, con la suite come **dato del progetto** invece che fixture Python. I
> riferimenti a file/simboli servono solo ad **ancorare** i requisiti all'esistente, non a prescrivere
> il *come*.

> **Additività (Principi I/III, local-first).** A leve spente, l'indice, il comportamento di ricerca e
> il **costo** restano identici a oggi. La valutazione gira in **locale** (mock/Chroma) senza richiedere
> il cloud; il confronto live sul provider forte è **fuori ambito** (FEAT-002).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Misuro e presidio il retrieval del mio progetto (P1, Must)
Owner/maintainer di un progetto ospite (non Sertor): dopo aver indicizzato il progetto col RAG di Sertor,
crea **a mano** una suite di domande con risposta attesa (query → path), la versiona nel repo del
progetto, e la **ri-esegue** quando serve per ottenere `hit-rate@k`/`MRR` deterministici. Registra il
risultato corrente come **riferimento** e d'ora in poi un'esecuzione che scende sotto quel riferimento
oltre tolleranza **fallisce** (gate di non-regressione).

**Independent Test**: su un progetto indicizzato con una suite curata a mano di pochi casi, due
esecuzioni a parità di indice/suite danno **metriche identiche** (report umano + JSON); registrando la
baseline e poi degradando artificialmente la qualità (suite invariata), il comando **segnala la
regressione ed esce con stato non-zero**; entro tolleranza passa con stato zero.

**Acceptance**:
1. **Given** un progetto indicizzato e una suite versionata di casi `query → path attesi (+ kind)`,
   **When** eseguo il comando di valutazione, **Then** ottengo `hit-rate@k` e `MRR` deterministici, con
   report **umano e JSON** e dettaglio **per-query** hit/miss.
2. **Given** la stessa suite e lo stesso indice, **When** ri-eseguo il comando, **Then** le metriche
   sono **identiche** (determinismo).
3. **Given** nessuna suite configurata, **When** eseguo il comando, **Then** **fallisce con un messaggio
   azionabile** invece di riportare un punteggio privo di senso.
4. **Given** una suite valutata senza riferimento ancora registrato, **When** lo chiedo, **Then** il
   sistema **registra** le metriche correnti come riferimento del progetto (artefatto versionato).
5. **Given** un riferimento esistente e una qualità misurata che scende oltre la tolleranza configurata,
   **When** valuto, **Then** il comando **esce con stato non-zero** (gate); entro tolleranza esce zero.
6. **Given** una voce della suite malformata, **When** la suite viene caricata, **Then** il sistema la
   **rifiuta con un messaggio che identifica il caso** offendente, senza eseguire un punteggio fasullo.

### User Story 2 — Genesi assistita: l'agente propone i casi dal corpus (P2, Should → FEAT-008)
L'utente, invece di scrivere ogni caso a mano, **delega all'agente** (via skill) la generazione di
candidati `query → atteso` **dai contenuti già indicizzati**, usando i tool di retrieval del progetto.
L'agente li **propone**; l'utente cura/approva; **solo gli approvati** vengono persistiti nella suite.

**Independent Test**: a partire da un corpus indicizzato, una sessione di authoring assistito produce una
suite **non vuota** di candidati **proposti** (non imposti); rifiutando un sottoinsieme, solo i casi
approvati finiscono nell'artefatto; con corpus/indice assente la generazione **fallisce con un messaggio
azionabile** («indicizza prima il progetto»).

**Acceptance**:
1. **Given** un corpus indicizzato, **When** l'utente delega la generazione all'agente, **Then** l'agente
   **deriva candidati** `query → atteso` dal corpus tramite i tool di retrieval e li **presenta per
   revisione**.
2. **Given** un set di candidati proposti, **When** l'utente ne approva alcuni e ne scarta altri, **Then**
   **solo gli approvati** vengono persistiti nella suite; gli scartati sono ignorati.
3. **Given** nessun indice/corpus disponibile, **When** si richiede la generazione, **Then** **fallisce
   con messaggio azionabile** che istruisce a indicizzare prima il progetto.
4. **Given** la genesi assistita, **When** la si esercita, **Then** essa resta una **superficie di
   giudizio (skill)** separata dal run deterministico: né il core né il comando di esecuzione invocano
   mai un LLM.

### User Story 3 — Feedback esplicito che raffina la suite (P3, Should → FEAT-009)
Vedendo i risultati di una ricerca, l'utente dà un **giudizio esplicito** (pertinente / non pertinente)
per una query; il giudizio **aggiorna gli `expected`** del caso corrispondente. Mai automatico: solo su
azione esplicita.

**Independent Test**: dopo che l'utente giudica un risultato di una query, gli `expected` del caso
corrispondente **riflettono il giudizio**; nessun giudizio viene inferito o persistito senza azione
esplicita; se la query giudicata non ha un caso nella suite, il sistema **offre di crearne uno**.

**Acceptance**:
1. **Given** i risultati di una ricerca per una query con un caso esistente nella suite, **When** l'utente
   marca esplicitamente un risultato come pertinente/non pertinente, **Then** gli `expected` di quel caso
   **vengono aggiornati** di conseguenza.
2. **Given** nessuna azione esplicita dell'utente, **When** avvengono ricerche, **Then** **nessun**
   giudizio viene inferito o persistito automaticamente.
3. **Given** una query giudicata senza caso corrispondente nella suite, **When** l'utente la giudica,
   **Then** il sistema **offre di creare un nuovo caso** da quella query e dai risultati giudicati.

### User Story 4 — Confronto locale di due configurazioni (P2, Should)
In un'unica esecuzione l'utente valuta **due configurazioni locali** (es. baseline vs ibrido) sulla
**stessa** suite e ottiene un confronto **affiancato**, per decidere quale tiene meglio sul suo corpus.

**Independent Test**: selezionando due configurazioni locali, il comando valuta entrambe sulla stessa
suite e presenta le metriche **fianco a fianco**, senza richiedere il cloud.

**Acceptance**:
1. **Given** due configurazioni locali selezionate (es. baseline e ibrido), **When** valuto, **Then**
   entrambe sono valutate sulla **stessa** suite e il report mostra il **confronto affiancato**.

### User Story 5 — La capacità è installabile su un ospite (P1, Must)
Su un **progetto terzo** (non Sertor), dopo `sertor install`, l'utente crea/esegue la suite e registra la
baseline **senza copiare file da Sertor**: la suite e il riferimento vivono nel suo repo; eventuali
manopole/skill/comandi arrivano dall'installer.

**Independent Test**: su un host pulito, dopo `sertor install`, la suite si crea, si esegue e produce
metriche; suite e riferimento sono memorizzati **dentro il progetto ospite**; nessun import del codice di
test di Sertor è necessario.

**Acceptance**:
1. **Given** un host pulito dopo `sertor install`, **When** creo ed eseguo la suite, **Then** funziona
   senza copiare file da Sertor; suite e riferimento sono **dentro il progetto ospite**.
2. **Given** che la feature introduce manopole di configurazione o asset host-facing (skill/comandi),
   **When** si installa, **Then** essi sono **cablati nell'installer** (es. template `.env`, `sertor
   install`), così l'ospite li ottiene **dal percorso di installazione**.
3. **Given** le leve di questa feature disabilitate/non usate, **When** si indicizza e si cerca, **Then**
   comportamento e **costo** sono **identici a oggi** (additivo, Principi I/III).

### Edge Cases
- **Path atteso inesistente nell'indice** — quando un caso (interattivo o assistito) indica un
  `expected_path` non presente nel corpus indicizzato, il sistema **avvisa** e richiede **conferma
  esplicita** prima di persistere il caso (evita suite che falliscono per path stantii più che per
  qualità). *(REQ-012)*
- **Path attesi relativi vs root di indicizzazione diversa** — se gli `expected` sono relativi alla root
  del repo ma la root indicizzata differisce, il sistema **rebase** gli `expected` sulla root valutata.
  *(REQ-005, eredita `relative_to` del fixture)*
- **Aggiunta/modifica di casi** — l'authoring è **non distruttivo e idempotente**: i casi preesistenti
  sono preservati salvo rimozione/sovrascrittura esplicita dell'utente. *(REQ-011)*
- **Suite vuota / assente al run** — il comando **fallisce azionabile**, non riporta uno zero ingannevole.
  *(REQ-032)*
- **Segreti** — l'artefatto suite e la baseline sono **dati versionati del progetto**, mai output
  rigenerabile: nessun segreto vi è incorporato. *(REQ-006, RNF-6)*
- **Generazione senza indice** — la genesi assistita senza corpus indicizzato **fallisce azionabile**
  («indicizza prima»). *(REQ-022)*
- **Determinismo del run** — stesso indice + stessa suite → stesse metriche, sempre. *(REQ-035)*

## Requirements *(mandatory)*
Fonte autorevole: `requirements/retrieval-qualita/ground-truth-valutazione/requirements.md` (REQ-001..062,
gruppi A–G; RNF-1..6). In sintesi (mappatura per gruppo):

- **A — Suite come artefatto-dato del progetto (Must):** suite = artefatto **versionato, fornito
  dall'ospite, indipendente dal codice di test**, ogni caso `query → path attesi` (REQ-001); localizzata
  per convenzione nel progetto (REQ-002); `kind` preservato e mostrato nel report (REQ-003); struttura
  **validata**, voci malformate rifiutate con messaggio che identifica il caso (REQ-004); rebase dei path
  alla root indicizzata (REQ-005); **nessun segreto**, dato versionato non rigenerabile (REQ-006).
- **B — Genesi interattiva (Must):** raccoglie coppie `query → atteso` dall'utente e le persiste (REQ-010);
  aggiunta/modifica **non distruttiva e idempotente** (REQ-011); path inesistente → **avviso + conferma**
  prima di persistere (REQ-012).
- **C — Genesi assistita dall'agente (Should → FEAT-008, *giudizio*):** l'agente **deriva candidati** dal
  corpus indicizzato via tool di retrieval e li **propone** (REQ-020); persiste **solo gli approvati**
  (REQ-021); senza indice → **fallisce azionabile** (REQ-022); resta **skill separata**, né core né run
  invocano un LLM (REQ-023).
- **D — Esecuzione e misura (Must, deterministica, via vehicle):** comando ripetibile che esegue la suite
  e riporta `hit-rate@k`/`MRR` deterministici (REQ-030); accesso al retrieval **solo via vehicle**
  (composition-root/CLI/MCP), mai engine internals fuori test — **Principio XI** (REQ-031); suite assente
  → **fallisce azionabile** (REQ-032); report **umano + JSON** con dettaglio per-query hit/miss (REQ-033);
  **confronto locale di due configurazioni** affiancato (REQ-034, Should); **determinismo** garantito
  (REQ-035).
- **E — Non-regressione (Must):** offre di registrare le metriche correnti come **riferimento** se assente
  (REQ-040); riferimento **persistito come artefatto versionato** (REQ-041); confronto col riferimento e
  **report del degrado** (REQ-042); sotto soglia oltre tolleranza → **exit non-zero** (gate) (REQ-043);
  aggiornamento del riferimento **solo su accettazione esplicita** (REQ-044).
- **F — Feedback esplicito (Should → FEAT-009, *giudizio*):** giudizio esplicito pertinente/non
  pertinente **aggiorna gli `expected`** del caso (REQ-050); applicato **solo su azione esplicita**, mai
  automatico (REQ-051); query senza caso → **offre di crearne uno** (REQ-052).
- **G — Host-agnosticità e installabilità (Must):** capacità usabile su **host terzo**, suite e
  riferimento **nel progetto ospite** — Principio X (REQ-060); manopole/asset host-facing **cablati
  nell'installer** (REQ-061); a leve spente comportamento **e costo identici a oggi** (REQ-062).

### Requisiti non funzionali (sintesi)
- **RNF-1 (determinismo/local-first):** misura deterministica, gira in locale (mock/Chroma) senza cloud.
- **RNF-2 (additività):** porte/engine invariati; l'harness **consuma**, non modifica le modalità.
- **RNF-3 (osservabilità):** il run emette un **evento strutturato** con le metriche (per il trend di
  `osservabilita`), senza testo libero/segreti oltre la redazione già fatta dal core.
- **RNF-4 (confine D↔N):** run+metriche = deterministico (core/CLI); generazione+cura/feedback = giudizio
  (skill). Le due metà non si mescolano; il core/CLI non chiama mai un LLM.
- **RNF-5 (prestazioni):** una suite di poche decine di casi gira in tempi compatibili con uso
  interattivo/CI; il costo è dominato dalle query di retrieval, non dall'harness.
- **RNF-6 (privacy/segreti):** nessun segreto in suite/baseline (dati versionati, non output).

### Key Entities
- **Suite di valutazione** *(artefatto-dato del progetto)* — insieme di **casi**, ognuno `query → path
  attesi (+ `kind` opzionale, es. exact-symbol vs natural-language)`; versionata e fornita dall'ospite,
  indipendente dal codice di test. (Promozione del fixture `GROUND_TRUTH` a dato del progetto.)
- **Caso di valutazione** — `query`, `expected_paths`, `kind`; unità di hit/miss nel report.
- **Riferimento (baseline)** *(artefatto-dato del progetto)* — metriche registrate come livello di
  qualità da non degradare; versionato; aggiornabile solo su accettazione esplicita.
- **Report di valutazione** — esito del run: `hit-rate@k`, `MRR`, dettaglio per-query hit/miss, `kind`,
  eventuale confronto affiancato; reso in forma **umana e macchina (JSON)**. (Promozione di `EvalReport`.)
- **Esito di non-regressione** — confronto misura↔riferimento con tolleranza, e **stato d'uscita**
  utilizzabile come gate.
- **Candidato (genesi assistita)** — caso `query → atteso` **proposto** dall'agente dal corpus, in attesa
  di approvazione; non persistito finché non approvato.

## Success Criteria *(mandatory)*
- **SC-001 (misura ripetibile):** su un progetto indicizzato con una suite versionata, il comando produce
  `hit-rate@k`/`MRR` con report **umano e JSON** e dettaglio per-query; **due esecuzioni** a parità di
  indice/suite danno **metriche identiche**. *(REQ-030/033/035; CS-1 epica)*
- **SC-002 (suite host-side):** su un progetto terzo (non Sertor), la suite si crea e si versiona nel suo
  repo e si usa **senza alcun import del codice di test** di Sertor. *(REQ-001/002/060)*
- **SC-003 (genesi non vuota e proposta):** una sessione di authoring (interattivo o assistito) produce
  una suite **non vuota**; i candidati dell'agente sono **proposti, non imposti** — solo gli approvati
  sono persistiti. *(REQ-010/020/021)*
- **SC-004 (gate di non-regressione):** registrata la baseline, **degradando** artificialmente la qualità
  (suite invariata) il comando **segnala la regressione e esce non-zero**; entro tolleranza esce zero.
  *(REQ-040..043)*
- **SC-005 (feedback raffina la suite):** dopo un giudizio esplicito su una query, gli `expected` del caso
  **riflettono il giudizio**; nessun giudizio è inferito/persistito automaticamente. *(REQ-050/051)*
- **SC-006 (via vehicle, niente LLM nel run):** il run accede al retrieval **solo via vehicle**; né il
  core né il comando di esecuzione importano engine internals fuori test né invocano un LLM. *(REQ-031/023;
  Principio XI)*
- **SC-007 (confronto 2 config):** due configurazioni locali sono valutate sulla **stessa** suite con
  confronto affiancato, **in locale** senza cloud. *(REQ-034; CS-2 epica)*
- **SC-008 (installabile):** su un host pulito, dopo `sertor install`, suite/baseline si creano/usano dal
  percorso di installazione; manopole/asset host-facing sono nell'installer. *(REQ-060/061)*
- **SC-009 (additività a leve spente):** con le leve di questa feature disabilitate/non usate, indice,
  comportamento di ricerca e **costo** sono **identici a oggi**. *(REQ-062, Principi I/III)*
- **SC-010 (suite assente → azionabile):** senza suite configurata il comando **fallisce con messaggio
  azionabile**, non riporta uno zero ingannevole. *(REQ-032; REQ-E3 epica)*

## Assumptions
- **Indice presente prima dell'uso.** Si assume che il progetto sia **già indicizzato** (RAG) prima di
  generare/eseguire la suite; la genesi assistita richiede un indice popolato (REQ-022).
- **«LLM» = agente dell'utente via skill**, non un servizio LLM terzo nel codice (chiarimento vincolante
  in testa). Il core e il comando di esecuzione non chiamano mai un LLM.
- **Riuso dell'esistente.** La feature **promuove** `evaluate`/`EvalReport`/`QueryableEngine` e la forma
  `(query, expected_paths, kind)` del fixture, invece di reinventarli; il fixture Sertor diventa
  l'**esempio dogfood** nella nuova forma di artefatto-dato.
- **Dipendenza installer.** La distribuzione su ospite riusa il percorso `sertor install` /
  `sertor-install-kit` (manopole nel template `.env`, eventuali skill/comandi).
- **Dipendenza FEAT-018 (su master).** La soglia `SERTOR_MIN_SCORE` esiste; la sua **calibrazione** dal
  ground-truth è **FEAT-004** (fuori ambito), ma la suite ne è il presupposto.
- **Confine osservabilità.** Questa feature **produce** la misura puntuale e l'evento; la
  **storicizzazione/trend** è FEAT-009 dell'epica `osservabilita` (fuori ambito).

### Fuori ambito (dichiarato)
- Le **modalità** di retrieval in sé (vettoriale/ibrido/grafo/agentico): epica `sertor-core`.
- **Confronto live sul provider forte/cloud** (marker `cloud`): **FEAT-002** dell'epica.
- **Miglioramento** di `search_code` su query architetturali: **FEAT-003**.
- **Calibrazione** delle soglie `SERTOR_MIN_SCORE` e affini dal ground-truth: **FEAT-004**.
- **Tecniche avanzate** HyDE/multi-query, filtro metadata esteso, contextual retrieval:
  **FEAT-005/006/007**.
- **Storicizzazione/trend** della qualità nel tempo: **FEAT-009** dell'epica `osservabilita`.
- Definizione del **come** (formato dell'artefatto TOML/JSON/YAML, nomi dei comandi, schema, struttura
  del codice): fase di **design/plan**.

> **Tracciamento dello scope (regola «gli Out-of-Scope si promuovono»).** I Gruppi C (genesi assistita) e
> F (feedback esplicito), pur coesi con questa feature, sono già **promossi** a casa durevole nel backlog
> d'epica: **FEAT-008** «Generazione assistita della suite» e **FEAT-009** «Feedback esplicito di
> pertinenza» (`requirements/retrieval-qualita/epic.md` §8). Se al `plan` crescono, restano lì; nessun
> rinvio reale vive solo dentro `specs/`.

### Forche di design (NON risolte qui — per `/speckit-clarify` o `/speckit-plan`)
Sono questioni di **come**, fuori dal *cosa/perché* della spec; menzionate per non seppellirle.
- **DA-a — Formato dell'artefatto suite:** TOML vs JSON vs YAML. *Contesto:* leggibile/diffabile a mano e
  parsabile in stdlib (Principio II). *Raccomandazione fonte:* TOML per la suite curata + import/export
  JSON per la genesi assistita.
- **DA-b — Riferimento della non-regressione:** baseline-su-file versionato vs soglia assoluta vs entrambi.
  *Raccomandazione fonte:* baseline su file + tolleranza configurabile; soglia assoluta opzionale.
- **DA-c — Genesi assistita: skill nuova o estende `derive-entity-types`.** *Raccomandazione fonte:* skill
  dedicata che riusa il *pattern* (non il codice).
- **DA-d — Superficie di comando:** run/non-regressione deterministico = sottocomando CLI via vehicle (es.
  `sertor-rag eval`); authoring/feedback = skill (giudizio).
- **DA-e — Validazione `expected_path` contro l'indice (REQ-012):** come verificare l'esistenza del path
  nel corpus indicizzato. *Raccomandazione fonte:* validare contro l'elenco dei documenti indicizzati al
  momento della scrittura del caso.
