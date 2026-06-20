---
title: Valutazione del retrieval & non-regressione (suite di valutazione host-side)
type: concept
tags: [retrieval-qualita, valutazione, ground-truth, non-regressione, eval, hit-rate, mrr, feat-001]
created: 2026-06-20
updated: 2026-06-20
sources: ["specs/065-ground-truth-valutazione/plan.md", "requirements/retrieval-qualita/ground-truth-valutazione/requirements.md", "src/sertor_core/services/eval/", "src/sertor_core/engines/evaluation.py"]
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
| Formato artefatto | **TOML** (`eval/suite.toml`, `eval/baseline.toml`), leggibile/diffabile a mano; lettura `tomllib` (stdlib), **scrittura con serializzatore minimale a mano** (schema piatto `[[case]]`) + round-trip validato + `SuiteWriteError`. **0 nuove dipendenze** (`tomli-w` come fallback non necessario). |
| Riferimento non-regressione | **Baseline su file versionato + tolleranza** → coglie il degrado *relativo* («non peggiorare»). Sotto baseline oltre tolleranza → `eval run` esce **non-zero** (gate CI). Pavimento assoluto = [[roadmap\|FEAT-010]] (Could). |
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

## Confini

Misura e presidia; **non** ridefinisce le modalità di retrieval ([[retrieval-core]]). Fuori ambito:
confronto live su provider forte/cloud (FEAT-002), miglioramento `search_code` architetturale (FEAT-003),
calibrazione delle soglie dal ground-truth (FEAT-004), tecniche avanzate (FEAT-005/006/007), trend storico
(`osservabilita` FEAT-009).

## Pagine collegate
[[retrieval-core]] · [[deterministic-vs-judgment]] · [[thin-consumer]] · [[indexing-and-retrieval]] ·
[[retrieval-confidence]] · [[sertor-rag-cli]] · [[assistant-targeting]] · [[roadmap]]
