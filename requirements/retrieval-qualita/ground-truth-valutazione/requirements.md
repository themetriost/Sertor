# Requisiti — Ground-truth & valutazione della pertinenza

<!-- Deriva da: FEAT-001 (epica retrieval-qualita) -->

> **Riformulazione cardine (utente, 2026-06-20).** Questa feature non è «un comando che carica un
> file statico e calcola hit@k». È la **capacità di ciclo di vita di una suite di valutazione del
> retrieval**, eseguibile su **qualunque progetto ospite** (non solo il dogfood Sertor): dopo aver
> indicizzato il progetto con il RAG Sertor + Wiki, l'utente **costruisce** una suite di domande con
> risposta attesa (a mano oppure delegando a un LLM la generazione dai contenuti indicizzati, da
> approvare); da quel momento **quelle sono le domande del test**; le si **ri-esegue** per verificare
> che il RAG **non degradi** e tenga un livello alto; e si **raffina** la suite col feedback esplicito
> dell'utente sui risultati delle ricerche.

## 1. Contesto e problema (perché)

Oggi Sertor restituisce risultati ma «funziona» non è «misurato» (Principio V). Una misura della
pertinenza **esiste già**, ma è **sepolta nei test** e legata al solo corpus Sertor:

- `src/sertor_core/engines/evaluation.py` → `evaluate(engine, ground_truth, ks=(1,3,5,10))` ritorna
  `EvalReport(hit_rate: dict[int,float], mrr, queries, provider)`. Funzione **pura, deterministica**.
  Astrazione `QueryableEngine` (solo `.provider` + `.query`); `GroundTruth = list[(query, expected_paths)]`.
- `tests/fixtures/ground_truth.py` → `GROUND_TRUTH`, 11 coppie (`kind ∈ {symbol, nl}`) sul corpus
  Sertor + `relative_to(prefix)` per il rebase dei path. **È un fixture Python di test**, non un
  artefatto-dato del progetto: un ospite **non** può portare il *suo* set.
- `tests/integration/test_baseline_quality.py` → confronto baseline vs ibrido; i 2 xfail storici di
  pertinenza sono già chiusi strict.

Il gap che questa feature chiude: **promuovere l'harness di valutazione a capacità di prima classe,
host-agnostica e ripetibile**, con una suite che vive **nel progetto valutato** e un ciclo
crea→esegui→raffina che presidia la **non-regressione** del retrieval nel tempo. Senza un numero
ripetibile su un set *del progetto*, le altre feature dell'epica non hanno un metro per dirsi migliori.

> Il *come* (formato file, nome dei comandi, struttura del codice) è materia della **fase di design**.
> Qui solo *cosa* e *perché*. Dove cito file/simboli è solo per **ancorare** i requisiti all'esistente.

## 2. Obiettivi e criteri di successo

- **OB-1 — Suite come dato del progetto.** Esiste un artefatto di valutazione **versionato e fornito
  dall'ospite** (query→atteso), indipendente dal codice di test, che vive nel progetto valutato.
  *CS:* su un progetto terzo (non Sertor), creo la suite e la versiono nel suo repo; nessun import di
  codice di test è necessario per usarla.
- **OB-2 — Genesi assistita.** L'utente costruisce la suite **interattivamente** oppure **delegando a
  un LLM** la generazione di candidati dai contenuti già indicizzati, che cura/approva.
  *CS:* da una sessione di authoring ottengo una suite non vuota; i candidati LLM sono **proposti, non
  imposti** (solo gli approvati vengono persistiti).
- **OB-3 — Misura ripetibile e deterministica.** Un comando ripetibile esegue la suite e calcola
  `hit-rate@k`/`MRR` in modo **deterministico** (stesso indice + stessa suite → stesso numero),
  accedendo al retrieval **solo via vehicle**.
  *CS:* due esecuzioni a parità di indice/suite danno metriche identiche; report umano **e** JSON.
- **OB-4 — Non-regressione.** La misura è confrontabile con un **riferimento** del progetto e
  **segnala il degrado** oltre una tolleranza, con esito azionabile (es. exit non-zero) utilizzabile
  come gate.
  *CS:* abbassando artificialmente la qualità (suite invariata) il comando segnala la regressione e
  fallisce; entro tolleranza passa.
- **OB-5 — Raffinamento con feedback esplicito.** L'utente dà un giudizio esplicito
  (pertinente/non pertinente) sui risultati di una ricerca, che **aggiorna gli `expected`** della suite.
  *CS:* dopo il feedback su una query, gli `expected` di quel caso riflettono il giudizio dato.
- **OB-6 — Installabile su un ospite.** La capacità (artefatto, comando, eventuali skill/manopole) è
  **distribuita via installer** e funziona su un progetto terzo (corollario «feature completa solo se
  installabile»).
  *CS:* su un host pulito, dopo `sertor install`, la suite si crea/esegue senza copiare file da Sertor.

## 3. Stakeholder e attori

- **Owner/maintainer del progetto ospite** — vuole sapere *quanto* è buono il retrieval sul **suo**
  corpus e accorgersi se un cambiamento (re-index, cambio provider/motore, refactor) lo peggiora.
- **Agente LLM** — sia *beneficiario* (contesto più pertinente) sia *strumento* (genera i candidati
  della suite dai contenuti indicizzati, da approvare).
- **Il core di Sertor** — fornisce i motori e la misura deterministica (`evaluate`); la feature li
  **consuma** via vehicle, non li ridefinisce.
- **Epica `osservabilita`** — consuma a valle il segnale (questa **produce** la misura puntuale, quella
  ne storicizza il **trend**: FEAT-009 di `osservabilita`, fuori ambito qui).

## 4. Ambito

### In ambito
- Artefatto **suite di valutazione** del progetto (query → path attesi + metadati come `kind`),
  versionabile e fornito dall'ospite; migrazione del fixture Sertor a **esempio dogfood** in questa forma.
- **Genesi interattiva** della suite (l'utente immette query→atteso curati).
- **Genesi delegata a LLM** dai contenuti indicizzati, come **proposta da approvare** (giudizio).
- **Esecuzione ripetibile** della suite con metriche `hit-rate@k`/`MRR` deterministiche, via vehicle;
  report umano + macchina.
- **Non-regressione**: confronto con un riferimento del progetto + segnalazione/gate del degrado;
  registrazione del riferimento corrente come baseline.
- **Feedback esplicito** dell'utente sui risultati di ricerca che raffina gli `expected` della suite.
- **Confronto locale fra due configurazioni** (es. baseline vs ibrido) in un'esecuzione (il codice
  esiste già: `evaluate` chiamato due volte).
- **Distribuzione su ospite** della capacità (manopole nel template `.env`, eventuali skill/comandi
  cablati in `sertor install`).

### Fuori ambito
- Le **modalità** di retrieval in sé (vettoriale/ibrido/grafo/agentico): epica `sertor-core`.
- **Confronto live sul provider forte/cloud** (modello reale, marker `cloud`): **FEAT-002** dell'epica.
- **Miglioramento** di `search_code` su query architetturali: **FEAT-003**; **calibrazione** delle
  soglie dal ground-truth: **FEAT-004**; tecniche avanzate HyDE/filtro/contextual: **FEAT-005/006/007**.
  Questa feature **abilita** quelle (fornisce il metro), non le esegue.
- **Storicizzazione/trend** della qualità nel tempo: FEAT-009 di `osservabilita`.
- Definizione del *come* (formato dell'artefatto, nomi dei comandi, schema): fase di **design**.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Suite di valutazione come artefatto-dato del progetto
- **REQ-001 (Ubiquitous):** *The system shall represent the evaluation suite as a versioned data
  artifact, supplied by the host project and independent of any test code, where each case associates a
  query with its expected result path(s).*
- **REQ-002 (Ubiquitous):** *The system shall locate the project's evaluation suite by convention
  within the host project, so the suite lives together with the project being evaluated.*
- **REQ-003 (Optional):** *Where a case carries a kind classification (e.g. exact-symbol vs
  natural-language), the system shall preserve it and surface it in the evaluation report.*
- **REQ-004 (Event-driven):** *When the suite artifact is loaded, the system shall validate its
  structure and reject malformed entries with an actionable message that identifies the offending case.*
- **REQ-005 (Optional):** *Where expected paths are expressed relative to the repository root but the
  indexing root differs, the system shall rebase the expected paths to the indexing root being evaluated.*
- **REQ-006 (Ubiquitous):** *The system shall never embed secrets in the suite artifact and shall treat
  the artifact as project-versioned data, not as runtime-regenerable output.*

### Gruppo B — Genesi interattiva della suite
- **REQ-010 (Event-driven):** *When the user authors the suite interactively, the system shall collect
  query→expected pairs from the user and persist the curated cases into the project's suite.*
- **REQ-011 (Ubiquitous):** *The system shall add or amend suite cases non-destructively and
  idempotently, preserving pre-existing cases unless the user explicitly removes or overwrites them.*
- **REQ-012 (Unwanted):** *If the user supplies an expected path that does not exist in the indexed
  corpus, then the system shall warn and require explicit confirmation before persisting that case.*

### Gruppo C — Genesi delegata a un LLM (proposta da approvare) — *giudizio*
- **REQ-020 (Optional):** *Where the user delegates suite generation to an LLM, the system shall derive
  candidate query→expected cases from the already-indexed corpus and present them to the user for review.*
- **REQ-021 (Event-driven):** *When the user reviews LLM-generated candidates, the system shall persist
  only the approved cases into the suite and discard the rest.*
- **REQ-022 (Unwanted):** *If no index/corpus is available when generation is requested, then the
  system shall fail with an actionable message instructing the user to index the project first.*
- **REQ-023 (Ubiquitous):** *The system shall keep LLM-assisted generation a judgment surface
  (skill/agent) separate from the deterministic run, so the run never depends on an LLM.*

### Gruppo D — Esecuzione e misura (deterministica, via vehicle)
- **REQ-030 (Ubiquitous):** *The system shall provide a repeatable command that runs the project's
  evaluation suite against the current index and reports `hit-rate@k` and `MRR` deterministically.*
- **REQ-031 (Ubiquitous):** *The system shall access retrieval only through the supported vehicle
  (composition-root factory / CLI / MCP), never importing engine internals outside tests (Principle XI).*
- **REQ-032 (Unwanted):** *If no evaluation suite is configured, then the evaluation command shall fail
  with an actionable message rather than report a meaningless score.*
- **REQ-033 (Ubiquitous):** *The system shall emit the evaluation report in both a human-readable form
  and a machine-readable form (e.g. JSON), with per-query detail of hit/miss to enable diagnosis.*
- **REQ-034 (Optional):** *Where two local configurations are selected (e.g. baseline vs hybrid), the
  system shall evaluate both on the same suite and present a side-by-side comparison.*
- **REQ-035 (Ubiquitous):** *The system shall, with the same index and the same suite, produce
  identical metrics across repeated runs (determinism).*

### Gruppo E — Non-regressione
- **REQ-040 (Optional):** *Where no reference baseline exists yet, the system shall offer to record the
  current metrics as the project's reference baseline.*
- **REQ-041 (Ubiquitous):** *The system shall persist the reference baseline as a versioned project
  artifact, so degradation is meaningful across time and commits.*
- **REQ-042 (Event-driven):** *When the suite is evaluated against an existing reference, the system
  shall compare the measured metrics to the reference and report any degradation.*
- **REQ-043 (Unwanted):** *If the measured metrics fall below the reference by more than a configured
  tolerance, then the command shall exit with a non-zero status so it can act as a quality gate.*
- **REQ-044 (Optional):** *Where the user explicitly accepts a new quality level, the system shall allow
  updating the reference baseline to the current metrics.*

### Gruppo F — Feedback esplicito (human-in-the-loop) — *giudizio*
- **REQ-050 (Event-driven):** *When the user explicitly judges a retrieval result as relevant or not
  relevant for a query, the system shall update the expected paths of the corresponding suite case
  accordingly.*
- **REQ-051 (Ubiquitous):** *The system shall apply relevance feedback only on explicit user action and
  never infer or persist judgments automatically.*
- **REQ-052 (Optional):** *Where a judged query has no matching case in the suite, the system shall offer
  to create a new case from that query and the judged results.*

### Gruppo G — Host-agnosticità e installabilità
- **REQ-060 (Ubiquitous):** *The system shall make the evaluation capability usable on a third-party
  host project, storing the suite and reference within the host project (Principle X).*
- **REQ-061 (Optional):** *Where the capability introduces configuration knobs or host-facing assets
  (skills/commands), the system shall wire them into the installer (e.g. `.env` template, `sertor
  install`), so a host obtains the capability through the install path.*
- **REQ-062 (Ubiquitous):** *The system shall, when its levers are disabled/unused, leave the existing
  index and search behaviour and their cost unchanged (additive, Principles I/III).*

## 6. Requisiti non funzionali
- **RNF-1 (Determinismo):** la misura è deterministica e local-first; gira in locale (mock/Chroma)
  senza richiedere il cloud. Il confronto col provider forte è FEAT-002 (cloud, fuori ambito).
- **RNF-2 (Additività):** il contratto delle porte e degli engine resta invariato; l'harness consuma,
  non modifica, le modalità di retrieval (Principio I).
- **RNF-3 (Osservabilità):** l'esecuzione emette un evento strutturato con le metriche (per il trend di
  `osservabilita`), senza testo libero/segreti oltre la redazione già fatta dal core.
- **RNF-4 (Confine D↔N):** run + metriche = deterministico (core/CLI); generazione LLM + cura/feedback =
  giudizio (skill/agente). Le due metà non si mescolano: il run non dipende mai da un LLM.
- **RNF-5 (Prestazioni):** una suite di poche decine di casi si esegue in tempi compatibili con un uso
  interattivo/CI; il costo è dominato dalle query di retrieval, non dall'harness.
- **RNF-6 (Privacy/segreti):** nessun segreto nell'artefatto suite/baseline; sono dati versionati del
  progetto, non output rigenerabile.

## 7. Vincoli, assunzioni e dipendenze
- **Ancoraggio all'esistente:** riusa `evaluate`/`EvalReport`/`QueryableEngine` del core e la forma
  `(query, expected_paths, kind)` del fixture, **promuovendoli** invece di reinventarli.
- **Assunzione:** il progetto è già indicizzato (RAG) prima di generare/eseguire la suite; la genesi LLM
  richiede un indice popolato.
- **Dipendenza FEAT-018 (su master):** la soglia `SERTOR_MIN_SCORE` esiste; la sua **calibrazione** dal
  ground-truth è FEAT-004 (fuori ambito), ma la suite ne è il presupposto.
- **Dipendenza installer:** la distribuzione su ospite riusa il percorso `sertor install` /
  `sertor-install-kit` (manopole, eventuali skill/comandi).
- **Vincolo Principio XI:** l'esecuzione passa dal vehicle; nessun `build_facade()/engine` importato a
  runtime fuori dai test.

## 8. Rischi
- **R-1 — Ground-truth costoso/soggettivo.** Costruire il set richiede giudizio; mitigare con set piccolo
  ma onesto, ancorato a casi reali, e con la genesi LLM-assistita (proposta da approvare) per abbassare
  l'attrito.
- **R-2 — Overfitting al set / falsa sicurezza.** Una suite troppo piccola o auto-confermante dà numeri
  rassicuranti ma non rappresentativi; mitigare con casi misti (symbol/nl) e revisione umana.
- **R-3 — Path attesi fragili al refactor.** Gli `expected` sono path: un refactor li rompe senza che il
  retrieval sia peggiorato. Mitigare con validazione del path contro l'indice (REQ-012) e feedback (Gruppo F).
- **R-4 — Confusione D↔N.** Mescolare generazione LLM e run deterministico renderebbe la misura non
  riproducibile; il confine RNF-4 è un invariante, non un'opzione.
- **R-5 — Costo della genesi LLM.** Generare candidati dai contenuti indicizzati costa chiamate LLM;
  resta opt-in e su richiesta esplicita (Gruppo C).

## 9. Prioritizzazione (MoSCoW)
- **Must** — Gruppo A (artefatto suite), Gruppo D (run + metriche deterministiche via vehicle, report
  umano+JSON), Gruppo E (non-regressione: riferimento + gate), Gruppo G (host-agnosticità/installabile),
  e la genesi **interattiva** (Gruppo B). È l'MVP che trasforma «funziona» in «misurato e presidiato».
- **Should** — Gruppo C (genesi **delegata a LLM**, proposta da approvare) e Gruppo F (feedback esplicito
  che raffina la suite): alzano molto l'usabilità ma poggiano sull'MVP. REQ-034 (confronto locale 2
  config) è **Should** (codice già presente, basso costo).
- **Could** — registrazione/aggiornamento avanzato della baseline (più revisioni, storicità locale prima
  che subentri `osservabilita`).
- **Won't (qui)** — confronto live su provider cloud (FEAT-002); calibrazione soglie (FEAT-004);
  miglioramento `search_code` (FEAT-003); tecniche avanzate (FEAT-005/006/007); trend storico
  (`osservabilita` FEAT-009).

## 10. Domande aperte
- **DA-a — Formato dell'artefatto suite (→ design).** [DA CHIARIRE: TOML vs JSON vs YAML per la suite
  query→atteso. *Contesto:* deve essere leggibile/diffabile da umani (lo cura l'utente) e parsabile in
  stdlib (Principio II/no dipendenze pesanti). *Impatto:* TOML è il più leggibile per dati curati a mano
  e già usato nei template; JSON è il più neutro per la genesi LLM; YAML è comodo ma non-stdlib.
  *Raccomandazione:* **TOML** per la suite curata, con la possibilità di import/export JSON per la genesi
  LLM.]
- **DA-b — Dove vive il «riferimento» della non-regressione (→ design).** [DA CHIARIRE: baseline salvata
  su file versionato vs soglia assoluta configurabile vs entrambi. *Contesto:* REQ-041/043 richiedono un
  confronto significativo nel tempo. *Impatto:* la baseline-su-file coglie il *degrado relativo* (il caso
  d'uso «non peggiorare»); la soglia assoluta è più semplice ma arbitraria. *Raccomandazione:* **baseline
  su file versionato** come primario + tolleranza configurabile; soglia assoluta opzionale.]
- **DA-c — La genesi LLM è una skill nuova o estende `derive-entity-types` (→ design).** [DA CHIARIRE.
  *Contesto:* `derive-entity-types` già fa «proposta data-driven dal corpus indicizzato da approvare» —
  stesso pattern. *Impatto:* riusare il pattern evita duplicazione ma i due output sono diversi
  (entity_types vs casi di test). *Raccomandazione:* **skill dedicata** che riusa il *pattern* (non il
  codice) di `derive-entity-types`.]
- **DA-d — Superficie di comando (→ design).** [DA CHIARIRE: un sottocomando di esecuzione (es.
  `sertor-rag eval`) per il run/non-regressione deterministico, e *separatamente* il flusso di authoring
  (interattivo + LLM) come skill/comando. *Contesto:* il confine D↔N (RNF-4) suggerisce comando
  deterministico per il run, skill per la genesi. *Raccomandazione:* run = sottocomando CLI via vehicle;
  authoring/feedback = skill (giudizio).]
- **DA-e — Validazione `expected_path` contro l'indice (→ design).** [DA CHIARIRE: come la genesi/feedback
  verifica che un path atteso esista nel corpus indicizzato (REQ-012). *Contesto:* serve a evitare suite
  che falliscono per path stantii più che per qualità. *Raccomandazione:* validare contro l'elenco dei
  documenti indicizzati al momento della scrittura del caso.]
- **DA-f — Decomposizione futura.** Groups C (genesi LLM) ed F (feedback) sono coesi con questa feature
  ma **separabili**: se al `plan` crescono, si promuovono a feature proprie dell'epica (candidate
  FEAT-008 «Generazione assistita della suite» e FEAT-009 «Feedback esplicito di pertinenza»). Tracciato
  qui per non seppellire lo scope (regola «gli Out-of-Scope si promuovono»).
