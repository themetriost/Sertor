# Phase 0 — Research: Valutazione della navigazione del grafo (set-based) (FEAT-011)

**Branch**: `066-valutazione-navigazione-grafo` · **Date**: 2026-06-20 · **Spec**:
[`spec.md`](spec.md)

> **Nota di processo.** `.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> **assenti** nel repo → parametri per convenzione dal branch; nessun hook SpecKit eseguito. Git
> **delegato** (mai eseguito qui). MCP `sertor-rag` interrogato per ancorare al codice reale
> (`get_context run_evaluation`, `find_symbol build_graph_service`/`SymbolHit`, `search_code`);
> **nessun errore tool** da riportare. Le 5 forche di scope (A–E) sono **già decise dall'utente** e qui
> sono **vincoli**, non oggetto di ricerca; le 4 forche residue di *come* (DA-a..DA-d) sono risolte sotto.

---

## Premessa: cosa esiste già (ancoraggio verificato)

Verifica diretta sui file (non inferenza):

- **`engines/evaluation.py::evaluate(engine, GroundTruth, ks)`** — misura IR **path-only, rank-based**:
  `hit@k`/`MRR` su contenimento di `result.path ∈ expected` ordinato per rank. `QueryableEngine`
  Protocol = `query(query,k)->list[RetrievalResult]` + `provider`. **Conclusione di design:** il nuovo
  oracolo a insiemi **NON va instradato qui** (niente rank, niente @k): è un secondo oracolo parallelo.
- **`services/eval/`** — `models.py` (EvalCase/EvalSuite/Baseline/MetricDelta/RegressionVerdict/
  ComparisonReport/PathValidation, frozen dataclass pure), `runner.py` (`run_evaluation` avvolge
  `evaluate`; `emit_eval_event` metrics-only; `RoutedEvalEngine` symbol→`find_symbol`; `validate_paths`
  puro), `suite_io.py` (loader `tomllib` + **serializzatore TOML a mano** + round-trip `SuiteWriteError`,
  `add_case`/`amend_case` idempotenti su `query`), `baseline_io.py` (load/write, assente→`None`),
  `regression.py` (`compare_to_baseline` puro: per ogni metrica comune `delta=current-baseline`,
  `regressed=delta < -tolerance`).
- **`domain/ports.py::CodeGraph`** (Protocol) — `find_symbol(name)->list[SymbolHit]` (le **definizioni**),
  `who_calls(name)->list[SymbolHit]` (i **chiamanti**), `related_docs(name)->list[str]`,
  `get_context(name)->ContextBundle`, `exists(corpus)`/`reset`/`build`. Due semantiche d'assenza:
  grafo non costruito → `GraphNotFoundError`; simbolo assente → risultati **vuoti** (legittimo).
- **`domain/entities.py::SymbolHit`** — `path`, `line`, `kind`, `qualname`, **`ref` (`path#qualname`)**:
  l'identità stabile richiesta dalla decisione D. `who_calls`/`find_symbol` ritornano già `SymbolHit`
  ordinati per `ref` (deterministici).
- **`adapters/graph/networkx_graph.py::NetworkxCodeGraph`** — adapter concreto; `_incoming(name,"calls")`
  → chiamanti, `find_symbol` → definizioni; cache invalidata al re-index (no stale).
- **`composition.py`** — `build_graph_service(settings)` (factory esistente, ortogonale a `SERTOR_ENGINE`),
  `build_eval_runner` + `_EvalRunner.run/run_labelled/run_by_kind`, `build_indexed_docs`.
- **`cli/__main__.py`** — gruppo `eval` con `run`/`add-case`/`validate-path` (argparse sub-subparser,
  `set_defaults(handler=...)`), exit 0/1 (SertorError)/2 (usage). Pattern `_resolve_settings` +
  `_check_backend` + `enable_observability` (Principio XI: il CLI è il vehicle).
- **`config/settings.py`** — `eval_dir` (default `eval`, `SERTOR_EVAL_DIR`), `eval_tolerance`
  (default `0.0`, `SERTOR_EVAL_TOLERANCE`). Template `.env` dell'installer già con le 2 voci commentate.

**Implicazione cardine:** la feature è un'**estensione additiva** del servizio `services/eval/` con un
**secondo tipo di caso** (`[[graph_case]]`), un **secondo oracolo** (a insiemi, NUOVO modulo parallelo a
`evaluate`, **non** dentro `RoutedEvalEngine`), un **secondo runner** che naviga la porta `CodeGraph` via
`build_graph_service`, e un **secondo blocco** di report/baseline/gate. I `[[case]]` IR esistenti e
`evaluate` restano **invariati** (RNF-4).

---

## DA-a — Tolleranza sugli insiemi (gate di non-regressione)

**Domanda.** La non-regressione (REQ-032) si valuta su **quale metrica aggregata** e con **quale
tolleranza**, e come si tiene **separata** dalla baseline IR (REQ-031)?

**Decisione.** Gate sul **F1 medio** (`mean_f1`) aggregato dei `graph_case`, come metrica primaria; il
**recall medio** (`mean_recall`) e la **precision media** (`mean_precision`) sono **metriche secondarie**
esposte nel report e **salvate nella baseline** (così la diagnosi vede *quale* leva è scesa), ma il **gate
scatta sul solo `mean_f1`** per default. Riuso del **meccanismo di tolleranza esistente**
(`compare_to_baseline`-style: `delta = current - baseline`, `regressed = delta < -tolerance`) ma con una
**baseline SEPARATA** per le metriche di grafo: file distinto **`eval/graph_baseline.toml`**, manopola
distinta **`SERTOR_GRAPH_EVAL_TOLERANCE`** (default `0.0`). La baseline IR (`eval/baseline.toml`) e la sua
tolleranza (`SERTOR_EVAL_TOLERANCE`) restano **intatte** (RNF-4).

**Razionale.**
- **F1 come gate, recall come segnale secondario.** L'F1 bilancia precision e recall: un cambiamento che
  *allarga* l'insieme navigato (più extra → precision giù) o lo *restringe* (più missing → recall giù)
  abbassa l'F1 in entrambi i casi → un singolo gate cattura le due regressioni. Il **recall medio** nel
  report è prezioso perché per una domanda relazionale «mi manca un chiamante» è spesso più grave di «ne
  ho uno di troppo»: esponendolo, l'utente vede *se* la perdita è di copertura. Esporre **tre** metriche
  (P/R/F1) nel report ma **gate-are solo F1** evita un gate ipersensibile a oscillazioni di una sola leva.
- **Baseline separata, non sezione condivisa.** REQ-031 chiede esplicitamente un riferimento **separato**
  dalla baseline IR. Tenere `eval/baseline.toml` (IR) e `eval/graph_baseline.toml` (grafo) come **due
  file** è più semplice del fondere due schemi in uno (lo schema IR ha `[hit_rate]` per-k, quello grafo
  ha medie set-based: schemi diversi). Due file = due `--record-baseline` semanticamente distinti, due
  diff puliti, zero rischio di rompere il loader IR esistente. Riusa il **pattern** di `baseline_io.py`
  (serializzatore a mano, round-trip `SuiteWriteError`, assente→`None`).
- **Tolleranza di default `0.0`.** Coerente col gate IR (`eval_tolerance=0.0`): per default «nessun
  peggioramento ammesso». L'utente alza la soglia (es. `0.05`) per assorbire micro-oscillazioni legittime
  dell'estrazione. Manopola separata da quella IR per regolarle indipendentemente.

**Alternative scartate.**
- **Gate sul recall medio** (raccomandazione iniziale tra parentesi): scartato come *primario* perché
  ignora gli extra (un grafo che restituisce TUTTO avrebbe recall 1 e gate verde, ma precision pessima).
  Recall resta come **secondario** nel report.
- **Pavimento assoluto per-caso** (ogni caso ≥ soglia): più rigido, utile ma rinviato (gemello del
  «pavimento assoluto» rinviato Could nel 065 / DA-b di FEAT-001). MVP = baseline relativa + tolleranza.
- **Fondere graph-baseline nello stesso `baseline.toml`** con una sezione `[graph]`: viola la lettera di
  REQ-031 («separato»), complica il loader IR esistente e i suoi test. Scartato.

---

## DA-b — `related_docs` come relazione futura (unità = documento)

**Domanda.** Quando entrerà `related_docs` (Could), l'unità è il **documento** (path), non il simbolo:
condivide la metrica a insiemi o ha un proprio oracolo/report?

**Decisione (per il MVP).** **Fuori ambito MVP** (resta **Could**, già tracciata nel backlog d'epica e
nella MoSCoW dei requisiti). **In design** progetto lo schema/metrica così da **non precludere** un
oracolo a insiemi su path-documento poi: l'insieme atteso di un `[[graph_case]]` è una **tupla di
stringhe** (i `ref`) e la metrica a insiemi (P/R/F1) è **agnostica rispetto al tipo di elemento**. Per
`related_docs` l'elemento sarà un **path di documento** invece di un `ref = path#qualname`. Quindi:
- la **stessa** metrica set-based (P/R/F1) si riuserà tale e quale (confronto di insiemi di stringhe);
- l'**unica** differenza sarà la `relation` (`related_docs`) e il **mapping** alla porta
  (`CodeGraph.related_docs(name)->list[str]`, che già ritorna **path**, non `SymbolHit`);
- nessuna nuova entità/metrica servirà alla promozione: si aggiungerà `related_docs` all'insieme
  `_SUPPORTED_RELATIONS` e un ramo nel navigatore. **Lo schema non va cambiato** per accoglierla.

**Razionale.** La metrica a insiemi è già naturalmente poliforma: confronta `set(got)` vs
`set(expected)`. Tenere l'`expected` come stringhe (e non come `SymbolHit` tipizzati) è ciò che mantiene la
porta aperta a documenti senza precludere nulla. La **validazione** in genesi (REQ-042) differirà
(documenti vs simboli), ma è la skill, non lo schema, a doverlo gestire alla promozione.

**Alternative scartate.** Anticipare `related_docs` ora (scope-creep, R-3); un secondo oracolo dedicato ai
documenti (YAGNI — la metrica a insiemi basta). Entrambe rinviate.

---

## DA-c — Workflow di re-congelamento dello snapshot

**Domanda.** Un cambiamento *legittimo* del grafo come si riapprova: stesso `--record-baseline` esteso, o
un verbo dedicato per gli insiemi?

**Decisione.** Distinguere **nettamente DUE cose** che la domanda confonde:

1. **La BASELINE = pavimento metrico** (il livello P/R/F1 da non degradare). Si registra **estendendo
   `--record-baseline`** sul comando di navigazione: `sertor-rag graph-eval run --record-baseline`
   scrive/aggiorna `eval/graph_baseline.toml` con le metriche correnti (accettazione esplicita, gemello
   di REQ-040/044 IR). È **metrica**, non insieme.
2. **Lo SNAPSHOT = gli INSIEMI attesi** (il `[[graph_case]].expected`, il *dato* della suite). Si
   ri-congela **ri-autorando il caso** — via skill `eval-suite-author` estesa (genesi assistita) o via il
   vehicle deterministico `graph-eval add-case`/`amend-case`, **NON** via `--record-baseline`.
   `--record-baseline` **non tocca mai** gli `expected` di un caso.

Quindi il workflow di re-congelamento dopo un cambiamento legittimo del grafo è:
- *cambia il pavimento ma gli insiemi attesi restano corretti* → `--record-baseline` (ri-congela il
  pavimento metrico);
- *cambia l'insieme atteso* (un chiamante nuovo è legittimo) → **ri-autora il caso** (snapshot
  proposto+approvato), poi eventualmente `--record-baseline` per riallineare il pavimento.

**Razionale.** Confondere le due cose è il rischio R-1 (fragilità dello snapshot). Tenerle separate
rispetta:
- **Principio VI (idempotenza/non-distruttività):** `--record-baseline` aggiorna **solo** un file di
  pavimento metrico, mai il dato-suite; ri-autorare un caso passa dal writer non-distruttivo
  (`amend_case`-style su `[[graph_case]]`).
- **Confine D↔N:** la ri-approvazione dell'**insieme** è **giudizio** (l'utente decide se il nuovo
  chiamante è legittimo) → skill; la ri-registrazione del **pavimento** è **deterministica** → CLI.
- **Coerenza con FEAT-001:** stesso modello mentale del 065 (baseline = file su flag esplicito; suite =
  dato curato). Nessun nuovo verbo per il re-congelamento del pavimento (riusa `--record-baseline`);
  l'`amend` degli insiemi è la primitiva di authoring (gemella di `amend_case` IR).

**Alternative scartate.** Un verbo dedicato `graph-eval refreeze` che fa entrambe le cose (baseline +
insiemi): scartato perché impasta metrica e dato, e perché la ri-approvazione degli insiemi è giudizio
(deve restare nella skill, non in un verbo deterministico che riscrive `expected` automaticamente — sarebbe
una scrittura implicita, viola REQ-041).

---

## DA-d — File singolo vs file dedicato

**Domanda.** `[[graph_case]]` in `eval/suite.toml` insieme ai `[[case]]`, oppure un `eval/graph_suite.toml`
separato?

**Decisione.** **Confermo la decisione A: `[[graph_case]]` nello STESSO `eval/suite.toml`**, come array di
tabelle distinto dai `[[case]]` IR. Lo split in un file dedicato resta **una mera eventualità di
leggibilità futura, NON MVP**.

**Razionale.**
- **Decisione di scope già presa dall'utente (A).** La spec la fissa; il design conferma che è
  realizzabile senza attrito: `tomllib` legge entrambi gli array dallo stesso file
  (`data.get("case", [])` e `data.get("graph_case", [])`); il serializzatore a mano emette **due sezioni**
  (`[[case]]` e poi `[[graph_case]]`) nello stesso testo, ognuna col proprio loader/parser.
- **Una sola sede `eval/` versionata, un solo file da committare/diffare.** L'ospite ha *una* suite del
  progetto: tenere IR e navigazione nello stesso file riduce la superficie e il rischio di drift fra due
  file paralleli.
- **Non-distruttività preservata.** Il writer **deve preservare** entrambe le sezioni: scrivere un
  `[[graph_case]]` non deve cancellare i `[[case]]` esistenti e viceversa. → Il writer va **riarchitettato
  in modo da serializzare la suite intera** (entrambi gli array) da un modello che le contiene
  **entrambe** (vedi data-model: `EvalSuite` esteso con `graph_cases`, oppure un wrapper). Questo è il
  punto di attenzione implementativo principale di DA-d.

**Alternative scartate.** File separato `eval/graph_suite.toml` (più file da gestire, contro la decisione
A; riconsiderabile solo se la dimensione lo imponesse — non è il caso MVP).

---

## Nodi di design (oltre le 4 forche)

### N1 — Oracolo a insiemi: NUOVO modulo, non `RoutedEvalEngine`, non `evaluate`

Il nuovo oracolo è un **modulo nuovo** in `services/eval/` (proposto `graph_eval.py`) con una funzione
**pura** `evaluate_graph_case(navigated: frozenset[str], expected: frozenset[str]) -> SetMetric` (P/R/F1 +
`missing`/`extra`) e l'aggregatore `evaluate_graph_suite(...)`. **Non** si tocca `evaluate`
(`engines/evaluation.py`): è path-only/rank-based e resta IR. **Non** si usa `RoutedEvalEngine` (che mappa
symbol→`find_symbol` e produce `RetrievalResult` per `evaluate`): semantica diversa (rank vs insiemi). La
**navigazione** è fatta dal runner via la porta `CodeGraph` (`build_graph_service`), non via
`QueryableEngine`. Confine Clean Architecture: il `domain` non importa SDK; il navigatore dipende dalla
**porta** `CodeGraph`, l'implementazione concreta (`NetworkxCodeGraph`) è scelta **solo** in composition.

### N2 — `defines` = `find_symbol`, `who_calls` = `who_calls` (mapping relazione→porta)

Nella porta `CodeGraph` **non esiste** un metodo `defines`: le **definizioni** di un simbolo sono
`find_symbol(name)->list[SymbolHit]`. Quindi il mapping relazione→navigazione MVP è:
- `who_calls` → `graph.who_calls(target)` → `{hit.ref for hit in …}`
- `defines` → `graph.find_symbol(target)` → `{hit.ref for hit in …}`

Entrambi ritornano `SymbolHit` con `.ref = path#qualname` (l'identità D). L'insieme navigato è
`frozenset(hit.ref ...)`. Simbolo assente → lista vuota → `frozenset()` (assenza legittima, REQ-014, **non**
un errore). Grafo non costruito → `GraphNotFoundError` propagato dalla porta → il comando fallisce
azionabile (REQ-013). Un mapping centralizzato (`_RELATION_NAVIGATORS`) tiene l'insieme MVP
(`who_calls`/`defines`) come **unica fonte**; una relazione fuori insieme → suite rifiutata (REQ-005).

### N3 — Report distinto + osservabilità metrics-only

Il report di navigazione vive in una **sezione distinta** da quella IR (REQ-030): nuove funzioni pure in
`cli/output.py` (`format_graph_eval_report`/`format_graph_regression`, umano + `--json`), gemelle delle IR.
L'evento osservabilità è un **gemello metrics-only** dell'evento `eval` (REQ-050): nuovo nome
**`graph_eval`** con SOLO metriche (`relations`/`cases`/`mean_precision`/`mean_recall`/`mean_f1`/
`regressed`/`tolerance`) — **mai** nomi di simboli, path, insiemi o testo libero (RNF-3, contract
`event-graph-eval.md`). Coerente con la policy export OTel metrics-only (feature 061).

### N4 — Installabilità (corollario Principio X)

Le **manopole nuove** (`SERTOR_GRAPH_EVAL_TOLERANCE`, e l'eventuale gate match-esatto
`SERTOR_GRAPH_EVAL_EXACT`) vanno nel **template `.env`** dell'installer (`env.local.tmpl`/`env.azure.tmpl`,
accanto a `SERTOR_EVAL_*`), commentate. La **skill estesa** (`eval-suite-author` → genesi dei
`graph_case`) è una superficie host-facing **distribuita via installer** (`packages/sertor/.../skills/
eval-suite-author/SKILL.md`): la sua estensione è **debito di completamento tracciato** (P2/Should, gruppo
E), da chiudere prima che la capacità conti come *done* host-side. Le capacità di **sola CLI** (il
sottocomando di navigazione, il navigatore, le metriche) viaggiano col pacchetto `sertor-core` → installabili
per costruzione; va **verificato** solo che le manopole compaiano nel template (fatto qui).

### N5 — Superficie CLI: nuovo gruppo `graph-eval` (non sovraccaricare `eval`)

Il run set-based **non** si infila in `eval run` (che è IR, rank-based, con `--compare`/`-k`/baseline IR):
semantica e baseline diverse. Nuovo gruppo di comando **`sertor-rag graph-eval`** con
`run`/`add-case`/`amend-case`/`validate-ref`, gemello strutturale di `eval` (stesso pattern argparse
sub-subparser, stessi exit code). Confine D↔N: il **run** è deterministico nel CLI/core; la **genesi**
(proporre l'insieme candidato) è giudizio nella skill, che invoca i sottocomandi (mai importa il core).
*Razionale del nome:* tenere `eval` per l'IR e `graph-eval` per la navigazione rende la **sezione distinta**
(REQ-030) visibile fin dalla CLI e impedisce di mescolare due oracoli sotto un solo verbo.

---

## Sintesi delle decisioni

| Forca | Decisione |
|---|---|
| **DA-a** (gate) | Gate su **F1 medio**; recall/precision medi come **secondari** nel report e nella baseline. **Baseline separata** `eval/graph_baseline.toml`, manopola `SERTOR_GRAPH_EVAL_TOLERANCE` (default 0.0). Riusa il pattern di tolleranza IR. |
| **DA-b** (`related_docs`) | **Fuori ambito MVP** (Could). Schema/metrica progettati agnostici al tipo di elemento (stringhe) → non preclusi i documenti. |
| **DA-c** (re-congelamento) | **Baseline (pavimento metrico)** = `--record-baseline` esteso al run di navigazione (deterministico). **Snapshot (insiemi attesi)** = ri-authoring via skill/`amend-case` (giudizio). Mai confuse: `--record-baseline` non tocca gli `expected`. |
| **DA-d** (file) | Confermato **A**: `[[graph_case]]` nello stesso `eval/suite.toml`. Writer ri-architettato per preservare **entrambe** le sezioni. Split solo eventualità futura. |

Nessuna nuova **porta** (la navigazione riusa `CodeGraph`); nessuna nuova **dipendenza** (stdlib +
serializzatore a mano già presente). `sertor-core` invariato fuori da: `services/eval/` (modulo
`graph_eval.py` nuovo + estensione `models.py`/`suite_io.py`), `composition.py` (factory), `cli` (gruppo
`graph-eval`), `config/settings.py` (manopole), template `.env` dell'installer.
