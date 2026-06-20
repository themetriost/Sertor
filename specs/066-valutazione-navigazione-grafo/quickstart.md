# Quickstart — Valutazione della navigazione del grafo (set-based) (FEAT-011)

Percorso utente end-to-end della capacità. Tutti i comandi via **vehicle** (`sertor-rag`, Principio XI),
**deterministici**, **senza LLM** nel run. Presuppone un progetto **indicizzato col code-graph costruito**
(`sertor-rag index .`, default `SERTOR_GRAPH=true`).

## 0. Prerequisito — indice + grafo
```powershell
sertor-rag index .
```
Senza grafo costruito, `graph-eval run` fallisce azionabile («costruisci prima l'indice», REQ-013).

## 1. Crea un caso di navigazione (deterministico)
Misuri se la navigazione restituisce l'**insieme giusto** di riferimenti. Identità del nodo = `ref`
(`path#qualname`).
```powershell
sertor-rag graph-eval add-case --relation defines --target build_facade `
    --expected "src/sertor_core/composition.py#build_facade"

sertor-rag graph-eval add-case --relation who_calls --target build_graph_service `
    --expected "src/sertor_core/composition.py#_GraphEvalRunner.run,src/sertor_core/cli/__main__.py#_cmd_graph_eval_run"
```
Ogni `ref` atteso è **validato contro il grafo** (REQ-042): un `ref` che il grafo non conferma genera un
warning che lo **nomina** e richiede `--confirm` prima di scrivere. Il caso finisce in `eval/suite.toml`
(array `[[graph_case]]`, accanto ai `[[case]]` IR esistenti — non li tocca).

## 2. Esegui la valutazione a insiemi
```powershell
sertor-rag graph-eval run
```
Output (sezione **distinta** da hit@k/MRR):
```
graph navigation eval  cases=2
mean_f1=0.93  mean_recall=1.00  mean_precision=0.88
by-relation: who_calls=0.86  defines=1.00
[exact] defines    build_facade        P=1.00 R=1.00 F1=1.00
[part ] who_calls  build_graph_service P=0.75 R=1.00 F1=0.86  +extra: src/.../x.py#Y
non-regression: no baseline recorded (run --record-baseline to set one)
```
`--json` per la forma macchina (equivalenza informativa). Due run identici → metriche identiche (REQ-015).

## 3. Registra il pavimento metrico (baseline separata)
```powershell
sertor-rag graph-eval run --record-baseline
```
Scrive `eval/graph_baseline.toml` (file **distinto** da `eval/baseline.toml` IR). Da ora il gate confronta
il `mean_f1` corrente col pavimento.

## 4. Il gate di non-regressione
```powershell
sertor-rag graph-eval run        # exit 0 se mean_f1 ≥ baseline - tolleranza; exit 1 se degrada oltre
```
La tolleranza è `SERTOR_GRAPH_EVAL_TOLERANCE` (default `0.0`). Senza baseline registrata il gate **passa**
(REQ-033). `recall`/`precision` medi appaiono come delta informativi (diagnosi), il gate scatta sul `mean_f1`
(DA-a).

### Gate match-esatto opzionale
```powershell
sertor-rag graph-eval run --exact     # un caso con got != expected → exit 1 (REQ-022)
```

## 5. Re-congelamento dopo un cambiamento legittimo del grafo
Due casi **distinti** (DA-c):
- **Cambia solo il pavimento** (gli insiemi attesi restano corretti) → ri-registra la baseline:
  ```powershell
  sertor-rag graph-eval run --record-baseline
  ```
- **Cambia l'insieme atteso** (un chiamante nuovo è legittimo) → ri-autora il caso (lo **snapshot**), poi
  riallinea il pavimento:
  ```powershell
  sertor-rag graph-eval amend-case --relation who_calls --target build_graph_service `
      --expected "<insieme aggiornato di ref>"
  sertor-rag graph-eval run --record-baseline
  ```
`--record-baseline` **non tocca mai** gli `expected` di un caso (solo il pavimento metrico).

## 6. Genesi assistita (giudizio — skill, Should)
Invece di elencare a mano l'insieme atteso, deleghi all'agente via skill `eval-suite-author` (estesa):
l'agente **esegue la navigazione corrente** del grafo per relazione+simbolo, presenta il risultato come
**insieme candidato**, e — **solo dopo la tua approvazione** — lo persiste via vehicle
(`graph-eval add-case`). Né il core né il comando di esecuzione invocano mai un LLM (confine D↔N). La skill
verifica i `ref` con `graph-eval validate-ref` (deterministico, exit 0 sempre).

## 7. Host-side / installabile
Su un progetto terzo, dopo `sertor install`: la suite di navigazione vive in `eval/suite.toml` del **tuo**
repo (dato versionato); le manopole (`SERTOR_GRAPH_EVAL_TOLERANCE`, `SERTOR_GRAPH_EVAL_EXACT`) arrivano dal
template `.env` dell'installer; la skill estesa è distribuita con `sertor install`. Nessun import del codice
di test di Sertor è necessario (SC-004/SC-010).

## Invarianti percepibili
- **Niente rank/@k**: la risposta a una domanda relazionale è un insieme; si misura per insiemi.
- **Sezione distinta**: la navigazione non si mescola con hit@k/MRR (comando, report e baseline separati).
- **Additivo**: a `graph-eval` non invocato, `index`/`search`/`eval` e il loro costo sono identici a oggi.
