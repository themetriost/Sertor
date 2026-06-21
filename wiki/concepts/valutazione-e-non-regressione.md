---
title: Valutazione del retrieval & non-regressione (suite di valutazione host-side)
type: concept
tags: [retrieval-qualita, valutazione, ground-truth, non-regressione, eval, hit-rate, mrr, feat-001, graph-eval, precision, recall, f1, feat-011, fusion-coverage, feat-003]
created: 2026-06-20
updated: 2026-06-21
sources: ["specs/065-ground-truth-valutazione/plan.md", "specs/066-valutazione-navigazione-grafo/plan.md", "specs/069-qualita-fusione-code-doc/plan.md", "requirements/retrieval-qualita/ground-truth-valutazione/requirements.md", "src/sertor_core/services/eval/", "src/sertor_core/engines/evaluation.py"]
---

# Valutazione del retrieval & non-regressione

La capacità che trasforma «il RAG funziona» in «il RAG è **misurato e presidiato**» (Principio V),
su **qualunque progetto ospite** (non solo il dogfood Sertor). È la prima feature consegnata dell'epica
[[roadmap|retrieval-qualita]] (E5, FEAT-001), branch `065-ground-truth-valutazione`.

## Il problema che chiude

Una misura di pertinenza **esisteva già** ma **sepolta nei test**: la funzione pura
`evaluate()`/`EvalReport` in `engines/evaluation.py` e un ground-truth come *fixture Python*
(`tests/fixtures/ground_truth.py`), entrambi legati al solo corpus Sertor e non usabili da un ospite.
Questa feature **promuove** quell'harness a capacità di prima classe, host-agnostica e ripetibile — non
reinventa nulla.

## Le tre metà del ciclo di vita

1. **Genesi della suite** — l'utente costruisce una suite di domande con risposta attesa (`query → path
   attesi`), a mano *oppure* delegando all'**agente** (vedi sotto) la proposta di candidati dal corpus
   indicizzato, da approvare.
2. **Run & non-regressione** (deterministico) — `sertor-rag eval run` misura `hit-rate@k`/`MRR` sulla
   suite, col dettaglio per-query, e fa **gate di non-regressione** contro una baseline registrata.
3. **Feedback** — l'utente giudica i risultati di una ricerca (pertinente/no) e raffina gli `expected`.

## Confine D↔N: cosa è deterministico, cosa è giudizio

Il [[deterministic-vs-judgment|confine D↔N]] è l'asse portante del design:

- **Deterministico (core/CLI, via vehicle):** `sertor-rag eval` — sottocomandi `run` (metriche + verdetto),
  `add-case` (aggiunge un caso, validato contro l'indice), `validate-path` (primitiva per le skill). Il
  comando costruisce engine e manifest **solo** dalle factory `build_*` del composition
  (`build_eval_runner`, `build_indexed_docs`, `build_engine_for`) — mai import diretto dell'engine
  ([[thin-consumer|Principio XI]]). Il servizio puro vive in `src/sertor_core/services/eval/`.
- **Giudizio (skill dell'agente):** la **genesi assistita** (`eval-suite-author`) e il **feedback**
  (`eval-feedback`) sono **skill** che l'agente esegue, usando i tool RAG/MCP del progetto per leggere il
  corpus e proporre/raffinare; persistono solo via il vehicle CLI (`eval add-case`). **Non importano mai**
  `sertor_core`.

> **«LLM» = l'agente, non un servizio terzo.** La «genesi via LLM» è l'agente conversazionale dell'utente
> (es. Claude) via skill — **non** una chiamata programmatica a un'API LLM dentro il core. Il core e il
> comando di run **non chiamano mai un LLM**: l'unico LLM «di sistema» resta l'embedder del retrieval.
> Stesso spirito della (proposta) skill `derive-entity-types`.

## Decisioni di design (le 5 forche)

| Forca | Decisione |
|---|---|
| Formato artefatto | **TOML** (`eval/suite.toml`, `eval/baseline.toml`), leggibile/diffabile a mano; lettura `tomllib` (stdlib), **scrittura con serializzatore minimale a mano** (schema piatto: sezioni `[ [ case ] ]`) + round-trip validato + `SuiteWriteError`. **0 nuove dipendenze** (`tomli-w` come fallback non necessario). |
| Riferimento non-regressione | **Baseline su file versionato + tolleranza** → coglie il degrado *relativo* («non peggiorare»). Sotto baseline oltre tolleranza → `eval run` esce **non-zero** (gate CI). Pavimento assoluto = [[roadmap|FEAT-010]] (Could). |
| Genesi assistita | **Skill nuova** (`eval-suite-author`), riusa il *pattern* «proposta data-driven dal corpus, da approvare». FEAT-008 (P2). |
| Superficie | run/gate = `sertor-rag eval` (vehicle); authoring/feedback = skill. |
| Validazione `expected_path` | a **write-time** contro l'elenco dei documenti indicizzati (`IndexManifest.load(...).files`, con rebase à la `relative_to`); assente → warning + conferma. |

## Dove vivono gli artefatti

Suite e baseline in **`eval/`** alla radice del progetto — **versionato** (sono *dato del progetto*, non
output rigenerabile), override `SERTOR_EVAL_DIR`. **Mai** in `.sertor/` (sede runtime gitignored). Il set
Sertor è migrato in `eval/suite.toml` (11 casi symbol/nl) come esempio dogfood.

## Additività e installabilità

- **Estensione core non-breaking:** solo `EvalReport.per_query` (default vuoto) + `QueryOutcome` in
  `engines/evaluation.py`; firma di `evaluate`/`GroundTruth` invariata, `kind` viaggia come metadato
  dell'artefatto/report. A leve spente, comportamento e costo identici a oggi (Principi I/III).
- **Installabile su ospite** ([[sertor-installer|Principio X]]): manopole (`SERTOR_EVAL_DIR`, tolleranza)
  nei template `.env`; skill cablate in `build_rag_plan` come **native-skill dual-target** (Claude
  `.claude/skills/` + Copilot `.github/skills/`). *Scoperta in implement:* `derive-entity-types` non
  esiste nel repo e il rag-installer non depositava skill — risolto col meccanismo nativo di
  [[assistant-targeting]].
- **Osservabilità:** evento `eval` **metrics-only** (per il futuro trend di qualità, FEAT-009 di
  `osservabilita`).

## Routing per-`kind` (`--by-kind`): misurare lo strumento giusto

Una scoperta dal **primo run reale sul dogfood** (2026-06-20): la metrica "nuda" dava `hit@1=0.18`,
`MRR=0.38` — *sospettosamente bassa* con due motori (denso+lessicale) + grafo. La causa non è la qualità
del RAG ma la **misura**: `eval run` chiamava un **solo motore** (l'ibrido), e i casi `symbol` sono
**domande da grafo poste alla ricerca**. La ricerca per similarità ordina le *menzioni* (usi, test, doc)
sopra la *definizione*; per `"log_event"` la definizione (`observability/logging.py`) non era nemmeno nei
primi 10 — mentre `find_symbol` la trova esatta e istantanea. *(Il "routing" del metodo a runtime non
vive nel core: vive nell'**agente** che sceglie il tool MCP. Nessun router automatico nel core — decisione
«agenzia composita». La modalità `--by-kind` è un router **deterministico** confinato all'eval.)*

`RoutedEvalEngine` (`services/eval/runner.py`) instrada per `kind`: `symbol`→`find_symbol` (code-graph),
altro→motore ibrido; riusa `evaluate` invariato. Opt-in `sertor-rag eval run --by-kind` (additivo).
Effetto misurato sul dogfood:

| Metrica | solo ibrido | `--by-kind` |
|---|---|---|
| hit@1 | 0.18 | **0.64** |
| hit@10 | 0.91 | **1.00** |
| MRR | 0.38 | **0.75** |

Dimostra che il **sistema composito è sano** e isola i difetti *veri*: un simbolo definito due volte
(`log_event` in `sertor_core` e in `sertor-install-kit`) e la qualità dell'ibrido sulle query NL
(materia di FEAT-003). *Idea correlata registrata:* **vedere nella TUI quando si scende sul grafo vs la
ricerca densa/ibrida** (roadmap → Nuove funzionalità, epica `osservabilita`).

## Valutazione SET-BASED della navigazione del grafo (FEAT-011)

Una **seconda metà** della valutazione emerge dalle query relazionali del code-graph: «chi chiama X?»,
«da cosa dipende Y?». L'oracolo a **insiemi** (non @k, non rank) è parallelo e complementare alla
metrica IR.

| Aspetto | Hit@k (IR) | Set-based (graph) |
|---|---|---|
| Domanda | Trova il documento top-1 in un ranking? | Tutti i risultati relazionali corretti? |
| Oracolo | Elenco ordinato, misura posizione (MRR) | Insieme, misura copertura (precision/recall/F1) |
| Semantica | Similarità: la risposta più rilevante per rank | Correttezza strutturale: il grafo conosce la relazione? |
| Assenza | Silenzio su cosa manca (item non trovato) | Esplicita: nodo non toccato ↔ nodo falso positivo |

Le **query symbol** come `find_symbol("log_event")` chiedono un **nodo esatto** — il grafo non risponde
«top-10 risultati ordinati», bensì una lista di path/nomi qualificati. La correttezza non è una ranking
ma l'**esattezza di copertura**: ricorda *tutte* le definizioni? ricorda solo definizioni vere?

**Architettura:** un oracolo a insiemi **nuovo e separato** — modulo `services/eval/graph_eval.py`
(navigazione + confronto puri) con runner `graph_runner.py` (+ evento `graph_eval` metrics-only),
regressione `graph_regression.py` e I/O `graph_baseline_io.py`. È **parallelo** a `evaluate` e **distinto**
da `RoutedEvalEngine` (che resta il router per-kind della metrica IR, symbol→`find_symbol` su path). Naviga
via la porta `CodeGraph` (vehicle Principio XI, riusa `build_graph_service`). Nuovo tipo di caso versionato
`[graph_case]` in `eval/suite.toml`: `relation` ∈ {`who_calls`, `defines`} (`defines` mappa su
`find_symbol` della porta; `depends_on`/`related_docs` rinviate, Could), `target` (simbolo da cui navigare),
`expected` (insieme di `ref` `path#qualname`). Metriche pure: **precision** (frazione di risultati veri),
**recall** (frazione di veri trovati), **F1** (media armonica), per caso e aggregate. **Baseline separata**
(`eval/graph_baseline.toml`) + manopola `SERTOR_GRAPH_EVAL_TOLERANCE`; il gate di non-regressione scatta sul
**F1 medio**. Gate match-esatto opzionale (`--exact`/`SERTOR_GRAPH_EVAL_EXACT`).

**Skill (genesi assistita):** `eval-suite-author` estesa a proporre i `[ [ graph_case ] ]` (tipo di caso nel TOML) (snapshot dal
grafo del corpus, da approvare). Nessun LLM nel core: l'agente via skill propone e persiste solo via
vehicle (`graph-eval add-case`).

**Run misurato:** sul dogfood (4 `[ [ graph_case ] ]` (tipo di caso nel TOML)) con `sertor-rag graph-eval run` → mean_f1=0.96,
recall=1.00, precision=0.94 (defines=1.00, who_calls=0.93). L'unico parziale è `who_calls build_graph_service`
con un **extra** legittimo (un test che lo chiama, precision 0.75 su quel caso): raffinamento di authoring,
non un difetto del grafo.

## Misura della fusione code+doc (fusion coverage) — FEAT-003

La **stella polare** della mission è la **fusione di codice e documenti in un unico corpus** (Principio XII).
I due strumenti — `search_code` (per il codice) e `search_docs` (per la documentazione) — sono misurati
*separatamente* dalle metriche IR precedenti. Ma un caso significativo come «passare da **requisito a
implementazione**» rimane **nascosto**: se il top-k contiene la documentazione del requisito senza
l'implementazione (o viceversa), le metriche hit@k/MRR non lo segnalano — la fusion coverage lo rende
**esplicito e quantificato**.

**Campo `intent` nei casi di valutazione:** ogni caso versionato in `[case]` di `eval/suite.toml`
porta ora un attributo `intent ∈ {code, doc, both}`:
- `code` — aspetta nel top-k **codice** (funzioni, simboli, test). Evalua su `search_code`.
- `doc` — aspetta **documentazione** (requisiti, spec, commenti). Evalua su `search_docs`.
- `both` — il **caso di fusione**: aspetta **documentazione E codice** correlati nello stesso top-k. Evalua su
  `search_combined`.

**Metrica fusion coverage:** un caso `intent="both"` è "coperto" SOLO se il top-k contiene:
- ≥1 risultato di tipo `doc` **pertinente**, E
- ≥1 risultato di tipo `code` **pertinente**.

L'assenza di una sorgente non è nascosta dal valore di hit@k (che conta solo «entrato nel top-k»), bensì
**riportata esplicitamente** nel verdetto coverage: `code_found=true`, `doc_found=false` → coverage falso.
Riflette il valore della missione: **il retrieval fuso è *completo* solo se entrambe le sorgenti
convergono su una risposta**.

**Misurazione per-superficie:** la suite eval giuda su tre **test di integrazione**:
1. `search_code` → `intent="code"`, hit-rate@k/MRR (azione: affinare `search_code` lessicale/semantica).
2. `search_docs` → `intent="doc"`, hit-rate@k/MRR (azione: qualità doc, indice, completezza).
3. `search_combined` → `intent="both"`, hit-rate@k/MRR + **fusion_coverage** (azione: diagnostica: se coverage è
   basso, quale sorgente manca? → indirizza il lavoro sul sub-problema).

**Baseline separata e gate di non-regressione:** un file `eval/fused_baseline.toml` (parallelo a
`baseline.toml` per i casi IR) registra il baseline di fusion coverage per i casi `both`. Manopola
`SERTOR_EVAL_FUSION_TOLERANCE` (default 0.0, no tolleranza) per il gate: se mean fusion coverage degrada
oltre il baseline, `sertor-rag eval run --fused` esce **non-zero** (fail-loud).

**Vehicle CLI:** opt-in `sertor-rag eval run --fused` (additivo, default OFF); comandi di authoring
`sertor-rag eval add-case --intent both` e `amend-case --intent both` per la genesi skill. Nessuna
modifica al run predefinito (backward-compatible).

**Estensione non-breaking:** il campo `intent` è **metadato dell'artefatto** (versionato nel TOML), non
parte della firma API di `EvalReport` / `GroundTruth`. A leve spente (intent non specificato = default al
tipo singolo), il comportamento e il costo sono **identici a FEAT-001** (Principio III).

**Differiti (fase successiva, empirica/giudizio):**
- **Autoraggio (TASK-C01):** genesi assistita via skill `eval-suite-author` estesa, propone candidati
  intent-typed dal corpus, utente approva.
- **Baseline reale (C02):** run sul dogfood con i casi intent-typed reali, registrazione baseline.
- **Adozione (D01/D02):** misurazione dell'impatto (es. fusion coverage prima/dopo ottimizzazione); opt-in
  per leve operative (es. agire sulla precisione lessicale vs semantica per categoria).

**Connessione alla mission:** il **Principio XII «Fail Loud»** fa sì che le lacune di fusione siano
**visibili, non silenziate**. La fusion coverage trasforma il claim astratto «fusiamo codice e doc» in un
numero misurabile e presidiato, parte del **ciclo di valutazione continua** dell'ospite.

## Confini

Misura e presidia; **non** ridefinisce le modalità di retrieval ([[retrieval-core]]) né di navigazione
([[code-graph]]). Fuori ambito: confronto live su provider forte/cloud (FEAT-002), miglioramento
architetturale di `search_code` (FEAT-004), calibrazione delle soglie dal ground-truth (FEAT-005),
tecniche avanzate (FEAT-006/007), trend storico (`osservabilita` FEAT-009).

## Pagine collegate
[[retrieval-core]] · [[deterministic-vs-judgment]] · [[thin-consumer]] · [[indexing-and-retrieval]] ·
[[retrieval-confidence]] · [[code-graph]] · [[hybrid-retrieval]] · [[mission-vision]] · [[sertor-rag-cli]] · 
[[assistant-targeting]] · [[roadmap]]
