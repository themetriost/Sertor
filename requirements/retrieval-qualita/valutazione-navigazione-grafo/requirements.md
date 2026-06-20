# Requisiti — Valutazione della navigazione del grafo (set-based)

<!-- Deriva da: FEAT-011 (epica retrieval-qualita) -->

## 1. Contesto e problema (perché)

La capacità di **valutazione del retrieval** (FEAT-001, su `master`) misura la **rilevanza IR**:
`engines/evaluation.py::evaluate` prende un `GroundTruth = (query, [path])`, interroga un
`QueryableEngine.query → list[RetrievalResult]` e segna un *hit* se `result.path ∈ expected`,
ordinato per **rank** (hit-rate@k / MRR). `services/eval/runner.py::RoutedEvalEngine` instrada solo
`symbol → find_symbol`, e usa il grafo **unicamente** per mappare un nome-simbolo sul **path** della
sua definizione (resta una misura path-based, rank-based).

Provando dal vivo la skill `eval-feedback` su una query **relazionale** — *«dammi tutte le dipendenze
di X / chi lo chiama / da cosa dipende»* — è emerso che questo harness **non può esprimerla**. La
risposta corretta a una domanda relazionale è un **insieme di simboli/nomi** (qualname), senza ordine
e senza path-ranking: non «quale file compare in cima», ma «l'insieme restituito è quello giusto».

Verifica sul codice (2026-06-20): nessun concetto set-based esiste nel repo
(0 match per `graph_case`/`expected_symbols`/`GraphNav`; nessuna metrica `precision`/`recall`/`F1`);
nell'eval `who_calls`/`get_context`/`related_docs` **non sono mai usati**. La **navigazione** del
grafo invece esiste e funziona (porta `CodeGraph` con `find_symbol`/`who_calls`/`related_docs`/
`get_context`, adapter `NetworkxCodeGraph`, i 4 tool MCP). **Manca la sua *valutazione*** come
capacità host-side, versionata e ripetibile via vehicle. Di conseguenza la **potenza relazionale del
grafo è oggi completamente non misurata** (la correttezza è esercitata solo da unit test interni
all'adapter — scaffolding di sviluppo, non una capacità del prodotto).

## 2. Obiettivi e criteri di successo

- **CS-1 (oracolo a insiemi):** esiste un modo ripetibile e deterministico per misurare la
  correttezza di una query di navigazione del grafo confrontando l'**insieme** di simboli restituito
  con un **insieme atteso versionato**, via il vehicle, senza rank né @k.
- **CS-2 (metrica graduata):** ogni caso produce `precision`/`recall`/`F1` sull'insieme; spegnendo la
  capacità il comportamento e il costo del sistema restano identici a oggi.
- **CS-3 (non-regressione):** le metriche di navigazione hanno una baseline registrabile separata e un
  gate che esce non-zero quando degradano oltre tolleranza, coerente con la non-regressione esistente.
- **CS-4 (host-side):** la capacità è esercitabile su qualunque progetto ospite indicizzato, con la
  suite come **dato versionato del progetto**, senza dipendere da un LLM.
- **CS-5 (additività):** `sertor-core` resta invariato fuori dai moduli nuovi; le suite e la baseline
  IR esistenti continuano a funzionare senza modifiche.

## 3. Stakeholder e attori

- **Owner/maintainer (tu):** vuole sapere se la navigazione del grafo restituisce *l'insieme giusto*,
  e se una modifica all'estrazione/traversata lo peggiora.
- **Agente LLM (via skill):** propone i casi (genesi assistita) leggendo l'output corrente del grafo;
  il giudizio di approvazione resta dell'utente.
- **Il code-graph di Sertor:** fornisce la navigazione (porta `CodeGraph`); questa feature la misura.
- **Epica `osservabilita`:** consuma a valle solo il segnale metrico (mai i nomi).

## 4. Ambito

### In ambito
- Un **tipo di caso** dedicato alla navigazione del grafo (relazione + simbolo target + insieme
  atteso), come dato versionato accanto ai casi di retrieval esistenti.
- L'**esecuzione** di questi casi via vehicle, navigando il grafo con la porta `CodeGraph`.
- Le **metriche a insiemi** (precision/recall/F1) + match-esatto opzionale come gate.
- **Report** distinto e **gate di non-regressione** con baseline separata per le metriche di grafo.
- **Genesi assistita** dei casi via skill (snapshot dall'output corrente, da approvare).
- Le relazioni **`who_calls`** e **`defines`** (definizioni) come insieme MVP.

### Fuori ambito
- Le relazioni **`depends_on`/callees** (via `get_context`) e **`related_docs`** (unità = documento,
  non simbolo): rinviate (vedi backlog/MoSCoW), da non perdere.
- Il **miglioramento** della qualità della navigazione o dell'estrazione del grafo (questa feature
  *misura*, non ridefinisce il grafo: è dell'epica `sertor-core`).
- Le metriche IR (hit@k/MRR) e i casi path-based: restano FEAT-001, invariati.
- La **storicizzazione/trend** delle metriche nel tempo: epica `osservabilita`.
- Il *come* (schema preciso, moduli, firme): fase di **design** a valle.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Artefatto: il caso di navigazione del grafo
- **REQ-001 (Ubiquitous):** *The system shall represent a graph-navigation evaluation case as
  versioned project data consisting of a relation, a target symbol, and an expected set of symbol
  references.*
- **REQ-002 (Ubiquitous):** *The system shall store graph-navigation cases in the same versioned eval
  artifact as the existing retrieval cases, as a distinct case type, without altering the existing
  path-based cases.*
- **REQ-003 (Ubiquitous):** *The system shall identify each expected node by a stable reference
  (file path plus qualified name), not by a bare symbol name.*
- **REQ-004 (Unwanted):** *If a graph-navigation case is missing its relation, target, or expected
  set, then the system shall fail to load the suite with a message naming the offending case.*
- **REQ-005 (Unwanted):** *If a graph-navigation case declares a relation outside the supported set,
  then the system shall reject the suite with an actionable message.*

### Gruppo B — Esecuzione via vehicle
- **REQ-010 (Ubiquitous):** *The system shall execute graph-navigation cases by querying the
  code-graph through the vehicle (CLI), without importing the core library at runtime.*
- **REQ-011 (Event-driven):** *When a `who_calls` case is run, the system shall navigate the graph to
  the set of callers of the target symbol and compare it against the expected set.*
- **REQ-012 (Event-driven):** *When a `defines` case is run, the system shall navigate the graph to
  the set of definitions of the target symbol and compare it against the expected set.*
- **REQ-013 (Unwanted):** *If the code-graph is not built, then the system shall fail with an
  actionable message (build the index first) rather than report a meaningless score.*
- **REQ-014 (Unwanted):** *If the target symbol is absent from the graph, then the system shall treat
  the navigated result as the empty set (legitimate absence) and score it against the expected set
  without error.*
- **REQ-015 (Ubiquitous):** *The system shall produce identical metrics for the same suite and the
  same graph artifact (determinism).*

### Gruppo C — Metriche a insiemi
- **REQ-020 (Ubiquitous):** *The system shall score each graph-navigation case by set comparison
  between the navigated set and the expected set, reporting precision, recall, and F1, without rank or
  @k.*
- **REQ-021 (Ubiquitous):** *The system shall aggregate the per-case set metrics into suite-level
  metrics for the graph-navigation cases.*
- **REQ-022 (Optional feature):** *Where an exact-set gate is enabled, the system shall mark a case as
  failed unless the navigated set equals the expected set.*
- **REQ-023 (Ubiquitous):** *The system shall provide per-case detail (expected, got, missing, extra)
  to support diagnosis of a failing case.*

### Gruppo D — Report e non-regressione
- **REQ-030 (Ubiquitous):** *The system shall report graph-navigation metrics in a section distinct
  from the retrieval (hit@k/MRR) metrics.*
- **REQ-031 (Ubiquitous):** *The system shall support a recorded baseline for graph-navigation
  metrics, kept separate from the retrieval baseline.*
- **REQ-032 (Event-driven):** *When graph-navigation metrics fall below the recorded baseline beyond
  the configured tolerance, the system shall exit non-zero, consistent with the existing
  non-regression gate.*
- **REQ-033 (Unwanted):** *If no graph-navigation baseline is recorded, then the gate shall pass
  (nothing to compare) without failing.*

### Gruppo E — Genesi assistita (snapshot, via skill)
- **REQ-040 (Optional feature):** *Where assisted authoring is requested, the agent (via skill) shall
  propose graph-navigation cases by running the current graph navigation and presenting its result as
  the candidate expected set for the user's approval.*
- **REQ-041 (Ubiquitous):** *The system shall persist graph-navigation cases only through the vehicle
  and only after explicit user approval (no implicit or automatic writes).*
- **REQ-042 (Event-driven):** *When a graph-navigation case is authored, the system shall validate the
  expected references against the graph and name those it cannot verify.*

### Gruppo F — Osservabilità
- **REQ-050 (Ubiquitous):** *The system shall emit a metrics-only observability event for a
  graph-navigation evaluation run, carrying no symbol names, paths, or free text (twin of the existing
  `eval` event).*

### Gruppo G — Host-side / installabile
- **REQ-060 (Ubiquitous):** *The system shall make the capability usable on any indexed host project
  via the vehicle, with the graph-navigation suite stored as the host's versioned project data.*
- **REQ-061 (Optional feature):** *Where the capability introduces new configuration knobs (e.g.
  graph-metric tolerance, exact-set gate), the system shall include them in the installer's `.env`
  template.*

## 6. Requisiti non funzionali
- **RNF-1 (additività):** a capacità spenta, comportamento e costo del sistema sono identici a oggi;
  `sertor-core` invariato fuori dai moduli nuovi (entità eval additive, runner nuovo, factory).
- **RNF-2 (determinismo / local-first):** il run è deterministico, locale, **senza alcun LLM**; nessun
  accesso di rete necessario per la misura.
- **RNF-3 (privacy):** l'evento di osservabilità è metrics-only; nomi/path/insiemi non compaiono mai
  nella telemetria (i nomi vivono solo nell'artefatto-dato versionato e nel report umano locale).
- **RNF-4 (compatibilità):** le suite, baseline e metriche IR esistenti (FEAT-001) restano valide e
  non-breaking; il nuovo tipo di caso convive nello stesso artefatto.
- **RNF-5 (dato non output):** la suite di navigazione è dato di progetto versionato in `eval/`, non
  artefatto rigenerabile in una sede gitignored.

## 7. Vincoli, assunzioni e dipendenze

**Decisioni di design già risolte (utente, 2026-06-20)** — riportate qui come vincoli, non come
domande aperte:
- **A — schema:** tabella TOML **separata** `[[graph_case]]` (relation, target, expected = insieme di
  `ref`); **non** si sovraccarica `[[case]]` (oracolo diverso, serializzatore a mano semplice). La
  suite `eval/suite.toml` può ospitare entrambi i tipi.
- **B — metrica:** **graduata** precision/recall/F1 sull'insieme + **match-esatto** come gate
  opzionale; niente @k, niente MRR.
- **C — relazioni MVP:** `who_calls` + `defines` (diretti sulla porta `CodeGraph`); `depends_on`/
  callees (via `get_context`) e `related_docs` rinviati (Could).
- **D — identità nodo:** per `ref` (`path#qualname`), stabile e non ambiguo.
- **E — genesi:** snapshot-bootstrap dall'output corrente del grafo (deterministico) → proposto,
  approvato una volta → congelato come **sentinella di regressione**; la skill `eval-suite-author` si
  estende a proporlo. Confine D↔N: run deterministico nel core/CLI; genesi assistita = giudizio/skill.

**Vincoli di piattaforma (come FEAT-001):** Principio XI (accesso a Sertor solo via vehicle CLI/MCP,
mai import di `sertor_core` fuori dai test); Principio X + corollario installabile (capacità host-side,
manopole nei template `.env` dell'installer); confine D↔N (deterministico nel core; giudizio nelle
skill).

**Dipendenze (codice esistente):** porta `CodeGraph` e adapter `NetworkxCodeGraph`
(`src/sertor_core/adapters/graph/networkx_graph.py`); factory `build_graph_service` (composition root,
già esistente); servizio eval `src/sertor_core/services/eval/{models,runner,suite_io,baseline_io,
regression}.py`; `engines/evaluation.py` (parallelo, NON instradato da `QueryableEngine` che è
path-only); `domain/ports.py` (`CodeGraph`, `SymbolHit` con `ref`).

**Assunzioni:** il `ref` (`path#qualname`) è la chiave d'identità stabile esposta dai risultati del
grafo (es. `find_symbol` → `…#NetworkxCodeGraph`); l'insieme atteso di un caso vive nel solo perimetro
del grafo del corpus indicizzato.

## 8. Rischi
- **R-1 — Fragilità dello snapshot:** un cambiamento *legittimo* dell'estrazione/traversata cambia
  l'insieme → falsi allarmi. Mitigazione: approvazione esplicita + re-record della baseline come per
  l'eval IR (la sentinella si ri-congela su conferma).
- **R-2 — Instabilità del `ref` ai refactor:** rinominare un simbolo/file cambia il `ref` atteso.
  Mitigazione: trattarlo come dato versionato (si aggiorna col refactor, diff visibile).
- **R-3 — Relazioni rinviate (`depends_on`/`related_docs`):** richiedono `get_context`/un'unità-doc
  diversa; rischio di scope-creep se anticipate. Mitigazione: confinarle a una seconda battuta (Could).
- **R-4 — Semantica della tolleranza sugli insiemi:** «degrado oltre tolleranza» va definito su una
  metrica aggregata (es. F1 medio) per non confondere con il pavimento per-caso. Resta come domanda
  aperta di design (vedi §10).

## 9. Prioritizzazione (MoSCoW)
- **Must:** Gruppo A (caso `[[graph_case]]` con `who_calls`+`defines`, identità per `ref`), Gruppo B
  (esecuzione via vehicle, semantiche di assenza), Gruppo C REQ-020/021/023 (precision/recall/F1 +
  dettaglio per-caso), Gruppo D (report distinto + gate con baseline separata), Gruppo G REQ-060.
- **Should:** Gruppo E (genesi assistita + snapshot-bootstrap), REQ-022 (gate match-esatto opzionale),
  REQ-050 (evento osservabilità), REQ-061 (manopole nel template `.env`).
- **Could:** relazioni `depends_on`/callees (via `get_context`) e `related_docs` (unità documento);
  un eventuale comando di *refresh* assistito dello snapshot.
- **Won't (per ora):** qualunque metrica di ordine/rank/@k per la navigazione del grafo (concettualmente
  sbagliata per una risposta a insiemi); storicizzazione/trend (è epica `osservabilita`).

## 10. Domande aperte
- **DA-a — Tolleranza sugli insiemi:** la non-regressione (REQ-032) si valuta su quale metrica
  aggregata (F1 medio? recall medio?) e con quale tolleranza di default? *(Design.)*
- **DA-b — `related_docs` come relazione:** quando entrerà, l'unità è il **documento** (path), non il
  simbolo: condivide la metrica set o ha un proprio oracolo/report? *(Design, quando si promuove dal Could.)*
- **DA-c — Workflow di re-congelamento dello snapshot:** un cambiamento legittimo del grafo come si
  riapprova — stesso `--record-baseline` esteso, o un verbo dedicato per gli insiemi? *(Design.)*
- **DA-d — Convivenza nel singolo file vs file dedicato:** `[[graph_case]]` in `eval/suite.toml`
  insieme ai `[[case]]`, oppure un `eval/graph_suite.toml` separato? (Deciso A = stesso file; da
  confermare in design se la dimensione/leggibilità suggerisce lo split.)
