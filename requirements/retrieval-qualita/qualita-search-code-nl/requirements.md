# Requisiti — Qualità di `search_code` su query NL / architetturali

<!-- Deriva da: FEAT-003 (epica retrieval-qualita) -->

## 1. Contesto e problema (perché)

`search_code` (motore **ibrido** BM25+dense+RRF, default — `engines/hybrid.py`) è **forte sui simboli**
ma **debole sulle query in linguaggio naturale / architetturali** (intento ampio: «come funziona X»,
«dove viene applicato Y», «dove si fondono i risultati»). Le query a **simbolo** sono già ben servite
instradandole al code-graph (`find_symbol`, via `sertor-rag eval run --by-kind`); il bersaglio di
questa feature sono le **query NL**.

Non è più un'impressione, è **misurato** (sessione 2026-06-20, con l'harness FEAT-001/011 ora su
`master`): nell'eval i casi `nl` colpiscono a **rank 3-6**, con file di **test** e **documentazione**
che rankano **sopra il sorgente**. Esempio reale: la query NL *«navigating the code graph to find which
functions call a given symbol»* → top result `docs/retrieval.md`, mentre l'implementazione
`adapters/graph/networkx_graph.py` **non è nei top-10**. L'audit RAG (skill `rag-production-audit`,
2026-06-20) ha indicato come cause plausibili i gap **B3** (nessuna query transformation/espansione) e
**B4** (nessuna contextual compression), oggi mitigati solo dal fatto che l'**agente itera** più query
via MCP.

**Sfumatura cardine (decisione utente 2026-06-20):** «test/doc sopra il sorgente» **non è sempre
sbagliato** — dipende dal **verbo** della query. *«where is X applied/used»* → un test che lo esercita è
pertinente; *«where is X defined»* → serve il sorgente; *«spiegami come funziona X»* → la **doc** + il
codice. Quindi il «buono» per le NL è **intent-dependent**: il ground-truth deve riflettere l'intento,
altrimenti misuriamo un *bias sul tipo di file* invece della pertinenza.

Lo **strumento di misura esiste già** (la suite di valutazione `sertor-rag eval`, hit@k/MRR): questa
feature non lo reinventa, lo **usa come criterio di accettazione**.

## 2. Obiettivi e criteri di successo

- **CS-1 (set NL onesto):** esiste un set di valutazione NL/architetturale versionato, con `expected`
  **coerenti con l'intento** della query, sufficiente a misurare la pertinenza di `search_code` sulle
  NL in modo distinto dai casi simbolo.
- **CS-2 (baseline):** è registrata una **baseline** della pertinenza NL (hit@k/MRR) *prima* di
  qualunque intervento, come riferimento di «miglioramento».
- **CS-3 (miglioramento dimostrato):** la pertinenza NL misurata **migliora di un margine
  misurabile** rispetto alla baseline (un numero, non un'impressione) — è il CS-3 dell'epica.
- **CS-4 (additività):** a leve di miglioramento **spente**, comportamento e costo restano **identici a
  oggi**; nessuna regressione sui casi esistenti (simbolo, NL, graph-eval).
- **CS-5 (selezione guidata-da-misura):** ogni tecnica adottata è giustificata da un **lift misurato**
  sul set NL, non da una scelta a priori.

## 3. Stakeholder e attori
- **Owner/maintainer (tu):** vuole un `search_code` che, su una domanda architetturale, restituisca il
  file giusto **per l'intento**, e poterlo dimostrare con un numero.
- **Agente LLM (consumatore via MCP):** beneficiario diretto — meno iterazioni per arrivare al file
  giusto; oggi compensa la debolezza NL con query multiple.
- **La suite di valutazione (FEAT-001/011):** lo strumento di accettazione di questa feature.

## 4. Ambito

### In ambito
- Un **set di valutazione NL** (query architetturali reali con `expected` intent-dependent) e la sua
  **baseline**.
- La **misura** della pertinenza NL di `search_code` e il suo **miglioramento dimostrabile** rispetto
  alla baseline.
- La **valutazione comparativa, guidata-da-misura, di una o più leve** candidate (query
  transformation/HyDE, filtro metadata, contextual retrieval) come **opt-in additivi**, e l'adozione
  **solo** di ciò che migliora.
- Il **gate di non-regressione** sui casi esistenti quando si interviene sulla qualità NL.

### Fuori ambito
- Le **modalità** di retrieval in sé (vettoriale/ibrido/grafo): epica `sertor-core`.
- L'eval **su provider forte/cloud**: FEAT-002 (questa misura è local-first).
- La **calibrazione delle soglie** `SERTOR_MIN_SCORE` (FEAT-004): gemella ma distinta — le soglie
  governano l'**astensione**, non il ranking NL.
- Le tecniche avanzate **come feature a sé** (FEAT-005 HyDE / FEAT-006 filtro metadata / FEAT-007
  contextual retrieval): qui sono **leve candidate**, non l'oggetto; quale leva e *come* = fase di
  design.
- Il *come* (stack/tecnica scelta, struttura del codice): fase di **design**.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Set di valutazione NL e baseline
- **REQ-001 (Ubiquitous):** *The system shall provide a versioned natural-language/architectural
  evaluation set whose expected results reflect each query's intent, sufficient to measure
  `search_code` NL pertinence distinctly from symbol cases.*
- **REQ-002 (Ubiquitous):** *The system shall record a baseline of NL `search_code` pertinence
  (hit-rate@k/MRR) before any improvement, as the reference for measuring lift.*
- **REQ-003 (Ubiquitous):** *The system shall allow an NL case's expected results to include the
  intent-appropriate target (source for "where defined"; documentation/docstring or test for
  "how does it work / where applied"), so that a hit denotes intent-relevance rather than file-type
  bias.*
- **REQ-004 (Unwanted):** *If an NL case cannot be given an intent-appropriate expected target, then it
  shall be excluded from the set rather than scored against an arbitrary target.*

### Gruppo B — Miglioramento misurato (l'obiettivo)
- **REQ-010 (Ubiquitous):** *The system shall improve NL `search_code` pertinence on the evaluation set
  by a measurable margin over the recorded baseline.*
- **REQ-011 (Ubiquitous):** *The system shall not declare any technique an improvement unless it shows
  a measured lift on the NL set versus the baseline.*
- **REQ-012 (Event-driven):** *When a candidate technique is evaluated, the system shall report its NL
  metrics side-by-side with the baseline so the lift (or its absence) is explicit.*
- **REQ-013 (Unwanted):** *If a candidate technique does not measurably improve the NL set, then it
  shall not be adopted, or shall remain disabled by default.*

### Gruppo C — Leve come opt-in additive
- **REQ-020 (Optional feature):** *Where an NL-improvement lever (query transformation, extended
  metadata filtering, contextual retrieval, …) is enabled, the system shall apply it while leaving
  default behaviour and cost unchanged when disabled.*
- **REQ-021 (Ubiquitous):** *The system shall keep any adopted lever disabled by default until a
  default change is justified by its measured lift and decided explicitly.*
- **REQ-022 (Ubiquitous):** *The system shall let the choice of which lever(s) to adopt be driven by
  the measured comparison, not prescribed in advance.*

### Gruppo D — Non-regressione, local-first, costo
- **REQ-030 (Unwanted):** *If an NL improvement regresses the existing symbol/NL retrieval cases or the
  graph-eval beyond tolerance, then it shall be rejected (non-regression gate).*
- **REQ-031 (Ubiquitous):** *The system shall keep the NL measurement local-first and deterministic
  (no cloud provider required).*
- **REQ-032 (Optional feature):** *Where a lever adds latency or token cost, the system shall make that
  cost observable and the lever opt-in.*

### Gruppo E — Misura via vehicle / confine D↔N
- **REQ-040 (Ubiquitous):** *The system shall measure NL pertinence through the existing vehicle
  (`sertor-rag eval`), reusing hit-rate@k/MRR rather than a new bespoke metric.*
- **REQ-041 (Optional feature):** *Where the NL set is authored with agent assistance
  (`eval-suite-author`), the candidates shall be persisted only via the vehicle and the run shall
  remain deterministic (confine D↔N; no LLM in the run path beyond the embedder).*

## 6. Requisiti non funzionali
- **RNF-1 (additività):** a leve spente, comportamento e costo identici a oggi; `sertor-core` invariato
  fuori dai punti nuovi (Principio I/III).
- **RNF-2 (misurabilità prima di tutto):** nessuna affermazione di «miglioramento» senza numero sul
  ground-truth (Principio V).
- **RNF-3 (local-first / deterministico):** misura locale, ripetibile, senza rete; nessun LLM nel
  percorso di run (l'embedder è l'unico modello).
- **RNF-4 (costo consapevole):** il costo aggiuntivo di una leva (latenza/token) è osservabile e
  opt-in (Principio VI).
- **RNF-5 (no regressione):** i casi e le baseline esistenti (FEAT-001/011) restano validi; il gate li
  protegge.

## 7. Vincoli, assunzioni e dipendenze
- **Dipende da FEAT-001** (suite/metriche IR, su `master`) come **strumento di accettazione**, e ne
  riusa l'harness (`engines/evaluation.py`, `services/eval/`, `eval/suite.toml`).
- **Relazioni (non sovrapposizioni):** FEAT-004 (soglie/astensione) è **ortogonale**; FEAT-005/006/007
  sono le **leve candidate** (il «come» possibile); FEAT-002 (cloud) è **fuori ambito**.
- **Assunzione:** la debolezza NL è del **singolo** `search_code`; l'agente la mitiga già iterando via
  MCP — quindi il valore va pesato (vedi DA-e).
- **Confine D↔N:** run deterministico nel core/CLI; il giudizio sui candidati (set, intento, leva) è
  giudizio dell'agente/utente (skill).
- Riferimenti codice: `engines/hybrid.py`, `services/retrieval.py` (`apply_min_score`),
  `engines/evaluation.py`, `services/eval/` (suite, runner, `--by-kind`), `eval/suite.toml`.

## 8. Rischi
- **R-1 — Overfitting al set** (R-2 dell'epica): ottimizzare sul set NL può non generalizzare.
  Mitigazione: set rappresentativo; valutare un *hold-out* di validazione separato dai casi su cui si
  itera.
- **R-2 — Etichettatura d'intento soggettiva:** l'`expected` intent-dependent richiede giudizio.
  Mitigazione: criteri d'intento espliciti e versionati col set.
- **R-3 — Leva che migliora il set ma costa/non generalizza** (R-3 epica): misurare il trade-off
  qualità↔costo, non attivare per default.
- **R-4 — Valore marginale rispetto all'agente:** se l'agente già aggira la debolezza con query
  iterative, un miglioramento del core potrebbe rendere poco. Mitigazione: misurare il guadagno *reale*
  (single-shot) e decidere se vale (DA-e).

## 9. Prioritizzazione (MoSCoW)
- **Must:** Gruppo A (set NL + baseline + expected intent-dependent), Gruppo B REQ-010/011/012
  (miglioramento misurato + criterio d'accettazione), Gruppo D REQ-030/031 (non-regressione,
  local-first), Gruppo E REQ-040 (via vehicle).
- **Should:** Gruppo C (almeno **una** leva valutata e, se migliora, adottata **opt-in**), REQ-013,
  REQ-041, REQ-032.
- **Could:** adozione di **più** leve; cambio del **default** se il lift è forte e stabile; hold-out di
  validazione formale.
- **Won't (qui):** prescrivere una tecnica a monte; eval cloud (FEAT-002); calibrazione soglie
  (FEAT-004); le leve come feature dedicate (FEAT-005/006/007).

## 10. Domande aperte
- **DA-a — Quali leve per prime:** valutare prima query transformation/multi-query/HyDE (B3), filtro
  metadata (B6), o contextual retrieval (I2/B4)? *(Design, guidato da costo atteso vs lift.)*
- **DA-b — Costruzione del set NL:** quante query, come etichettare l'intento in modo ripetibile, e
  come separare un hold-out per non overfittare? Riusare `eval-suite-author` per proporle?
- **DA-c — Soglia di «miglioramento»:** quale delta minimo su hit@k/MRR NL fa dichiarare la feature
  *done* (e su quale k)?
- **DA-d — Rapporto con FEAT-004/005/006/007:** se una leva entra qui, la sua feature dedicata diventa
  il «come» (e FEAT-003 la *consuma*), oppure FEAT-003 la assorbe? E come si coordina con le soglie di
  FEAT-004 (ortogonali ma entrambe toccano la pertinenza percepita)?
- **DA-e — Valore reale vs agente:** dato che l'agente itera già via MCP (mitiga B3 a livello agente),
  il target è migliorare il **single-shot** `search_code`, o basta documentare il pattern agentico?
  *(Decide se la feature è core-work o per lo più documentazione.)*
