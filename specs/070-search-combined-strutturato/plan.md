# Implementation Plan: `search_combined` a contratto strutturato (due flussi etichettati) — Tempo 2 FEAT-003

**Branch**: `070-search-combined-strutturato` | **Date**: 2026-06-21 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `specs/070-search-combined-strutturato/spec.md`

## Summary

Il Tempo 1 (`069`) ha **misurato** che `search_combined` non funziona per il caso-firma
requisito→implementazione: **fusion coverage 0.17** (`eval/baseline.toml` `[fused_baseline]`).
La causa è strutturale e verificata nel codice: `search_combined` fonde doc+code in **una sola lista
ranked a budget condiviso** (`RetrievalFacade.search_combined → _search(..., "both")`,
`services/retrieval.py:166-175`); gli score code/doc sono **incommensurabili** e i documenti
**annegano** il codice nello stesso top-k.

Questa feature **ripara la causa** (Principio XII): `search_combined` ritorna una **coppia strutturata**
`FusedResults(docs, code)`, **ciascuna col proprio top-k** (budget separato), + helper `flatten()`
(interleave deterministico). `search_code`/`search_docs` **invariati**. La fusion coverage si adatta
alle **due liste** (doc pertinente nel top-k `docs` AND code pertinente nel top-k `code`); la baseline
fusa è **ri-registrata** sul nuovo valore (> 0.17 atteso). È un **breaking change volontario**,
circoscritto a `search_combined` + entità nuova + i suoi consumatori di **prima parte** (MCP, CLI,
fused-eval, test), giustificato dal Principio XII e dal gate **Allineamento alla missione**.

Approccio (research): riuso del percorso mono-tipo esistente (`_search(..., "doc")`/`"code"`) per
comporre la coppia; `flatten()` interleave; fusion coverage che legge `has_doc`/`has_code` dalle due
liste; rimozione di `search_combined` dall'insieme delle superfici IR ranked del fused-runner (era la
metrica sbagliata sulla superficie sbagliata) — la fusion coverage **è** la misura della superficie fusa.

## Technical Context

**Language/Version**: Python 3.11+ (`pyproject.toml`).
**Primary Dependencies**: nessuna nuova. `sertor-core` (domain/services/cli), `sertor-mcp` (FastMCP),
stdlib (`tomllib`/`dataclasses`). Embedder/store dietro porte (Principio I).
**Storage**: `eval/baseline.toml` (versionato) — sezione `[fused_baseline]` ri-registrata; Chroma
locale per la misura dogfood.
**Testing**: pytest (unit + integration), marker `not cloud` per la CI locale; ruff.
**Target Platform**: libreria + vehicles (CLI `sertor-rag`, MCP), host-agnostica.
**Project Type**: single project (libreria `sertor-core` + pacchetto MCP).
**Performance Goals**: la coppia esegue **due** retrieval mono-tipo (era un retrieval `"both"`): costo
~2× sulla query del combined; trascurabile e atteso (è il prezzo del budget separato). Determinismo
invariato.
**Constraints**: local-first, deterministico, nessun LLM nel run oltre l'embedder (RNF-3); misura via
vehicle (Principio XI); nessun segreto nei log (Principio IX).
**Scale/Scope**: refactor confinato; ~9 file di prima parte + test.

## Constitution Check

*GATE: superato PRIMA della Phase 0 e RI-VERIFICATO dopo la Phase 1.*

Gate derivati da `.specify/memory/constitution.md` (v1.4.0). 12 principi + gate missione.

### PRE-design (prima della Phase 0)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS *(con deviazione additività
  dichiarata, vedi Complexity Tracking)*. `FusedResults` è una frozen dataclass di dominio, **nessun
  SDK**; la facade dipende solo dalle porte. Il **cambio di tipo di ritorno** di `search_combined` è
  una rottura di contratto **dichiarata e tracciata**, non una violazione strutturale: il core resta
  importabile e mockabile. Vedi Complexity Tracking.
- [x] **II — Boundary & local-first:** PASS. Embedder/store restano dietro le porte; misura locale
  (mock/Chroma), nessuna nuova dipendenza esterna.
- [x] **III — YAGNI & unità piccole:** PASS *(con la stessa deviazione di I)*. Una sola entità nuova,
  due campi nominati (no `dict`/generalizzazioni); `flatten()` piccolo e puro; nessuna manopola k
  asimmetrica (non c'è evidenza presente). La rottura di additività è giustificata, non un'aggiunta
  speculativa.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS. Policy invariata: indice assente → coppia
  vuota + warning (tollerante); `ProviderMismatchError` conservato sul fan-out; `_guard` MCP
  ri-solleva. Niente `None` silenzioso (la coppia è sempre strutturata).
- [x] **V — Testabilità & misure:** PASS. `FusedResults`/`flatten()`/fusion coverage testabili con
  liste fittizie (F.I.R.S.T.); il valore si dimostra con un numero (fusion coverage > 0.17).
- [x] **VI — Idempotenza & non-distruttività:** PASS. Determinismo della coppia e di `flatten()`;
  re-baseline via `--record-baseline` (esplicito, non distruttivo); preserve-both su `baseline.toml`.
- [x] **VII — Leggibilità:** PASS. `FusedResults`/`flatten()` vocabolario di dominio («fuse»); due
  sezioni etichettate per resa.
- [x] **VIII — Configurabilità centralizzata:** PASS. `k`/`default_k` da `Settings`; nessun default
  hardcoded nuovo.
- [x] **IX — Osservabilità:** PASS. I due `_search` per tipo emettono i `retrieve` esistenti; evento
  `fused_eval` metrics-only (set di superfici 3→2, cardinalità chiusa).
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS. Nessuna assunzione dell'ospite; `FusedResults`/
  resa funzionano su qualsiasi corpus (anche solo-doc o solo-code → una lista vuota).
- [x] **XI — Consumo via vehicles:** PASS. Misura via `sertor-rag eval --fused`
  (`build_fused_eval_runner`); MCP/CLI consumano la facade, niente import diretto di `sertor_core` a
  runtime (eccetto i test).
- [x] **XII — Fail Loud, Fix the Cause:** PASS *(è il principio guida)*. Si **ripara la causa** (budget
  condiviso/score incommensurabili) invece di affiancare una superficie corretta lasciando viva quella
  rotta; la superficie IR ranked `search_combined` (metrica sbagliata) viene **rimossa** con decisione
  esplicita e tracciata, sostituita dalla fusion coverage (la misura giusta).
- [x] **Allineamento alla missione:** PASS. La fusione code+doc è la **stella polare** e oggi è rotta
  (0.17): il refactor rende strutturalmente possibile che una query requisito→implementazione renda
  **doc + codice insieme**. È esattamente il differenziatore, non un concern periferico.

**Esito PRE: PASS 12/12 + gate missione PASS**, con **una deviazione tracciata** (additività su I/III)
nel Complexity Tracking.

### POST-design (dopo la Phase 1)

Rivalutato su data-model + contracts. Nessuna nuova violazione introdotta dal design:
- **I/III**: la deviazione additività è **circoscritta** come previsto (solo `search_combined` + entità
  + consumatori di prima parte); `search_code`/`search_docs`/porte/engine/`evaluate` **invariati**
  (data-model §2/§4; contracts). Il core resta importabile/mockabile.
- **IV**: i contratti confermano coppia-sempre-strutturata e ri-sollevamento errori.
- **V/VI**: contratti di test e determinismo `flatten()` espliciti (library-contract).
- **IX**: event-fused-eval.md conferma metrics-only e cardinalità chiusa (2 superfici).
- **XI/XII/missione**: invariati; la rimozione della superficie IR ranked combined è documentata
  (research §superficie, data-model §4).

**Esito POST: PASS 12/12 + gate missione PASS**, deviazione additività invariata e tracciata.

## Project Structure

### Documentation (this feature)

```text
specs/070-search-combined-strutturato/
├── plan.md              # questo file
├── research.md          # Phase 0 — DA-a..d risolte + causa-radice + superficie IR
├── data-model.md        # Phase 1 — FusedResults + delta facade/fusion/runner/baseline/serializzazione
├── quickstart.md        # Phase 1 — come esercitare/verificare
├── contracts/           # Phase 1
│   ├── library-contract.md       # FusedResults + search_combined
│   ├── mcp-search-combined.md    # tool MCP {"docs","code"}
│   ├── cli-search-combined.md    # CLI due sezioni / JSON
│   └── event-fused-eval.md       # evento fused_eval (3→2 superfici)
├── spec.md
└── checklists/
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/entities.py                  # + FusedResults(docs, code) + flatten()  [NEW entity]
├── services/
│   ├── retrieval.py                    # search_combined → FusedResults (due _search per tipo)
│   └── eval/
│       ├── fusion.py                   # fusion_coverage consuma la coppia (has_doc/has_code dalle 2 liste)
│       └── fused_runner.py             # _SURFACES 3→2; combined misurato SOLO da fusion coverage; evento
├── cli/
│   ├── __main__.py                     # _cmd_search (--type both) consuma FusedResults; _fused_baseline_from (2 surf)
│   └── output.py                       # format_search_results: due sezioni etichettate / JSON {"docs","code"}
src/sertor_mcp/
└── server.py                           # tool search_combined → {"docs","code"}; _run/_fmt serializzazione

eval/baseline.toml                      # [fused_baseline] ri-registrato (2 superfici + fusion_coverage > 0.17)

tests/
├── unit/{test_retrieval_facade,test_fusion,test_fused_runner,test_output_fused_eval,
│         test_cli_fused_eval,test_regression_fused,test_baseline_io_fused,test_mcp_server}.py
└── integration/test_end_to_end.py
```

**Structure Decision**: single project. Modifiche confinate a domain/services/cli di `sertor-core` +
`sertor_mcp/server.py` + test. **Porte, engine (hybrid/baseline/`evaluate`), adapter, composition root
`build_*` INVARIATI** (la composizione `build_fused_eval_runner`/`build_facade` resta il punto
d'ingresso, riusata). Il prototipo (`prototype/**`) è congelato, fuori ambito.

## Consumatori da aggiornare (breaking change contenuto, tutti di prima parte)

Verificato via MCP + `Grep` (research §consumatori). Tutti nel repo, aggiornati **in blocco** (FR-004):

1. **Entità** `src/sertor_core/domain/entities.py` — nuova `FusedResults(docs, code)` + `flatten()`.
2. **Facade** `services/retrieval.py:166` — `search_combined` ritorna `FusedResults` (due `_search`
   per tipo, budget separato); fan-out 010 produce due liste filtrate per tipo.
3. **Fusion coverage** `services/eval/fusion.py` — `has_doc`/`has_code` dalle due liste; `search_fn`
   tipato `→ FusedResults`.
4. **Fused runner** `services/eval/fused_runner.py` — `_SURFACES` a due (`search_code`/`search_docs`);
   fusion coverage sulla coppia; evento `fused_eval` (2 chiavi `surface_*`).
5. **CLI esecuzione** `cli/__main__.py` `_cmd_search` — `--type both` consuma `FusedResults`.
6. **CLI baseline** `cli/__main__.py` `_fused_baseline_from` — itera due superfici (forma invariata).
7. **CLI resa** `cli/output.py` `format_search_results` — due sezioni etichettate / JSON
   `{"docs","code"}`.
8. **MCP** `src/sertor_mcp/server.py` — tool `search_combined` → `{"docs","code"}`; `_run`/`_fmt`
   serializzazione; docstring/instructions aggiornate.
9. **Test** (lista §Source Code) — adeguati al nuovo contratto/serializzazione; nessun chiamante rotto.

**Re-baseline (passo operativo, non design):** dopo il refactor, `sertor-rag eval run --fused
--record-baseline` su Azure-large → nuovo `fusion_coverage` (> 0.17) e `[[fused_baseline.surface]]` a
due voci; `[baseline]` IR intatto (preserve-both).

## Forche di design risolte (DA-a..d)

- **DA-a (forma entità):** `FusedResults(docs: tuple[RetrievalResult,...], code: tuple[...])` frozen,
  nel domain, `flatten()` come metodo. *(research §DA-a)*
- **DA-b (allocazione k):** budget **separato**, stesso `k` per entrambe (da `Settings`), nessuna
  nuova manopola (YAGNI). Riuso dei percorsi mono-tipo `_search(..., "doc"/"code")`. *(research §DA-b)*
- **DA-c (flatten):** **interleave per rank** deterministico; avanzi in coda; score-merge scartato
  (causa-radice). *(research §DA-c)*
- **DA-d (serializzazione):** MCP `{"docs","code"}`; CLI due sezioni etichettate / JSON
  `{"docs","code"}`; formato citabile `path#chunk` preservato. *(research §DA-d, contracts)*
- **Superficie IR ranked combined:** **rimossa** dal fused-runner; la fusion coverage è la misura della
  superficie fusa. *(research §superficie, data-model §4)*

## Complexity Tracking

> Deviazione da giustificare: **rottura dell'additività** (Principi I/III).

| Violazione | Perché necessaria | Alternativa più semplice scartata perché |
|---|---|---|
| **Breaking change del tipo di ritorno di `search_combined`** (`list[RetrievalResult]` → `FusedResults`) — deviazione dall'**additività** (I/III) | La superficie fusa è **rotta alla radice** (fusion coverage 0.17): budget condiviso + score code/doc **incommensurabili** fanno annegare il codice. **Principio XII** impone di **riparare la causa**, non di affiancare un workaround. **Gate Allineamento alla missione**: la fusione code+doc è la **stella polare** e oggi non funziona — riparare il contratto è servire la missione, non un concern periferico. Ammissibile: pre-1.0 `git+url`, **nessun contratto pubblico stabile**, **tutti i consumatori di prima parte e nel repo** (aggiornati in blocco). | **(a)** Aggiungere `search_combined_pair()` lasciando vivo il vecchio blended — viola XII (lascia viva la superficie rotta), confonde i consumatori, raddoppia la superficie. **(b)** Tarare un blend «smart» (pesi doc/code) — è ancora budget conteso su score incommensurabili: cura il sintomo, non la causa. **(c)** Score-merge in `flatten()` — reintrodurrebbe la causa-radice. La deviazione è **circoscritta** (solo `search_combined` + entità + consumatori di prima parte; `search_code`/`search_docs`/porte/engine invariati — RNF-1/SC-010) e **tracciata**. |

## Nodi residui

- **Valore esatto del re-baseline**: noto solo a refactor implementato (atteso > 0.17); è un passo del
  piano (`--record-baseline`), non del design.
- **k asimmetrici docs/code**: rinviato (YAGNI); se emergerà dal tuning → additivo (Settings + template
  `.env` dell'installer). Non blocca.
- **Nessun `NEEDS CLARIFICATION`**: scope fisso, quattro forche risolte.
- **Nota di processo:** `setup-plan.ps1`/`speckit-plan/SKILL.md` assenti → parametri per convenzione dal
  branch; nessun hook eseguito. MCP `sertor-rag` interrogato senza errori tool.
