# Tasks — `search_combined` a contratto strutturato (Tempo 2 FEAT-003)

**Branch**: `070-search-combined-strutturato` | **Generato**: 2026-06-21
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/library-contract.md`](contracts/library-contract.md) ·
[`contracts/mcp-search-combined.md`](contracts/mcp-search-combined.md) ·
[`contracts/cli-search-combined.md`](contracts/cli-search-combined.md) ·
[`contracts/event-fused-eval.md`](contracts/event-fused-eval.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del refactor: BREAKING CHANGE atomico.** `search_combined` cambia tipo di ritorno da
> `list[RetrievalResult]` a `FusedResults(docs, code)`. Questo impone un vincolo architetturale
> fondamentale: il **core** (entità + facade + eval) e **tutti i consumatori** (MCP, CLI, test)
> devono essere aggiornati **nella stessa fase**, mai in stadi separati, per non lasciare mai la
> suite in uno stato rosso a metà. La Fase Refactor è pertanto **coesa e indivisibile** dal punto
> di vista della suite (si può procedere per task ordinati dentro di essa, ma la fase si considera
> completa solo quando tutti i suoi task sono verdi). Vedi §Complexity Tracking nel `plan.md`.
>
> **Strategia MVP/incrementale.**
> - **Setup** (TASK-G01): prerequisito zero; abilita la factory `FusedResults` nell'export pubblico.
> - **Fondazionale** (TASK-F01): entità pura `FusedResults` + `flatten()` nel domain; zero
>   dipendenze runtime; bloccante per tutto il resto; testabile isolatamente.
> - **Refactor atomico** (TASK-R01–R08): nucleo del cambiamento. Core (facade + fusion + runner) e
>   tutti i consumatori (CLI + MCP) e i loro test, aggiornati **in blocco**. Questa fase non è
>   terminata finché la suite non è verde con lint pulito. L'ordine interno raccomandato va dal
>   modello verso l'esterno (facade → eval → CLI → MCP → test), ma il merge avviene solo a
>   suite verde.
> - **Polish** (TASK-P01–P03): suite non-cloud verde, lint ruff, verifica additività residua,
>   smoke test end-to-end.
> - **Re-baseline** (TASK-RB01): MECCANICO ma richiede indice dogfood attivo (Azure-large, costo
>   centesimi); eseguito dal flusso principale dopo il merge dell'MVP meccanico su master.
>
> La feature è un **breaking change circoscritto**: `search_code`/`search_docs`, le porte, gli
> engine (hybrid/baseline/`evaluate`), la composition root `build_*`, `apply_min_score` e
> `content_fields` sono **invariati** (RNF-1/SC-010). Non toccano alcun task qui sotto.

---

## Fase 0 — Setup (1 task)

> Prerequisiti: nessuno. Bloccante per TASK-F01.

### TASK-G01 — Riesporta `FusedResults` da `__init__.py` dopo la sua creazione (dipendente da TASK-F01)
**File**: `src/sertor_core/__init__.py`
→ dipende da: TASK-F01
- [x] Aggiungi `FusedResults` alle entità riesportate dal package pubblico `sertor_core`
      (accanto a `RetrievalResult`, `ContextBundle`, ecc.), così che i consumatori (MCP, CLI,
      test) possano importarla da `sertor_core` senza conoscere `domain.entities` direttamente.
- [x] Verifica: `from sertor_core import FusedResults` funziona senza errori; nessun import
      circolare introdotto; i test esistenti di `__init__.py` continuano a passare (RNF-5).

> **Nota:** TASK-G01 dipende da TASK-F01 (l'entità deve esistere prima di essere riesportata).
> È separato per chiarire che l'export è un atto distinto dalla definizione.

---

## Fase 1 — Fondazionale: entità `FusedResults` (1 task)

> Prerequisiti: nessuno. Bloccante per tutta la Fase Refactor. Testabile in isolamento.

### TASK-F01 — Definisci `FusedResults(docs, code)` + `flatten()` in `domain/entities.py`
**File**: `src/sertor_core/domain/entities.py`
→ dipende da: nessuno
- [x] Aggiungi la frozen dataclass `FusedResults` accanto a `RetrievalResult` (data-model §1):
      ```python
      @dataclass(frozen=True)
      class FusedResults:
          docs: tuple[RetrievalResult, ...] = ()
          code: tuple[RetrievalResult, ...] = ()

          def flatten(self) -> list[RetrievalResult]:
              ...
      ```
- [x] `docs` contiene solo risultati `doc_type=DOC`; `code` solo `doc_type=CODE` (garantito
      dalla facade, non da un guard sull'entità — l'entità è puro dato).
- [x] `flatten()` implementa l'interleave deterministico per rank (DA-c, research §DA-c):
      `docs[0], code[0], docs[1], code[1], …`; gli avanzi della lista più lunga seguono in ordine.
      Loop: `for i in range(max(len(self.docs), len(self.code)))`, due guard `if i < len(...)`.
- [x] Garanzie `flatten()` da testare (library-contract.md):
      - `docs=[d0,d1], code=[c0,c1]` → `[d0,c0,d1,c1]`
      - `docs=[d0,d1,d2], code=[c0]` → `[d0,c0,d1,d2]`
      - `docs=[], code=[c0,c1]` → `[c0,c1]`
      - `docs=[], code=[]` → `[]`
      - stesso input ri-eseguito → stessa lista (SC-003)
- [x] Aggiungi test in un file dedicato `tests/unit/test_fused_results.py` (o inline in
      `test_retrieval_facade.py` se il progetto lo prevede): tutti e 5 i casi della tabella
      qui sopra + determinismo (ri-esecuzione) + verifica che `FusedResults` sia hashable.
- [x] **Nessun import di SDK esterni** in `domain/entities.py` (Principio I); la frozen
      dataclass è pure data, zero dipendenze dal domain verso l'esterno.
- [x] Verifica: `domain/entities.py` importabile senza dipendenze esterne; i test esistenti di
      entità (`RetrievalResult`, `ContextBundle`, ecc.) continuano a passare invariati (RNF-5).

---

## Fase 2 — Refactor atomico: core + consumatori + test (8 task)

> Questa fase è il nucleo del breaking change. L'ordine interno raccomandato è facade → eval
> (fusion + runner) → CLI → MCP → test, ma tutti gli 8 task fanno parte dello **stesso giro
> atomico**: la suite non è verde finché tutti e 8 non sono completati. TASK-R02 e TASK-R03
> sono parallelizzabili tra loro (dipendono entrambi da TASK-R01); TASK-R04 e TASK-R05 sono
> parallelizzabili tra loro (dipendono entrambi da TASK-R01). I task di test (TASK-R06/R07/R08)
> possono essere scritti in parallelo con le loro controparti di implementazione.
>
> Prerequisiti comuni: TASK-F01 (entità) + TASK-G01 (export).

### TASK-R01 — Aggiorna `RetrievalFacade.search_combined` → `FusedResults` in `services/retrieval.py`
**File**: `src/sertor_core/services/retrieval.py` (riga 166 e dintorni)
→ dipende da: TASK-F01, TASK-G01
- [x] Cambia la firma di `search_combined`:
      ```python
      # PRIMA
      def search_combined(self, query: str, k: int | None = None) -> list[RetrievalResult]:

      # DOPO
      def search_combined(self, query: str, k: int | None = None) -> FusedResults:
      ```
- [x] Sostituisci il corpo da `self._search(query, k, "both")` (budget condiviso) a due chiamate
      separate ai percorsi mono-tipo (data-model §2, research §DA-b):
      ```python
      docs = self._search(query, k, "doc")    # stesso percorso di search_docs
      code = self._search(query, k, "code")   # stesso percorso di search_code
      return FusedResults(docs=tuple(docs), code=tuple(code))
      ```
      Il parametro `k` effettivo (o `default_k` da Settings) è usato **separatamente** per ogni
      lista — budget distinto, non condiviso (FR-001/SC-001).
- [x] Conserva la gestione del fan-out multi-corpus (feature 010, data-model §2): quando ci sono
      `extra_collections`, ogni lista (`docs`/`code`) fa il fan-out con il proprio filtro
      `doc_type` e il proprio top-k. `ProviderMismatchError` e policy `no_index` restano invariati.
- [x] `search_code` e `search_docs` **non vanno toccate** (FR-003/SC-002): solo `search_combined`
      cambia.
- [x] Logging invariato per costruzione: i due `_search` per tipo emettono i propri eventi
      `retrieve` (collection/provider/doc_type/k/results/elapsed) come già fanno
      `search_docs`/`search_code`. Nessun evento nuovo richiesto sulla facade (data-model §2).
- [x] Aggiorna docstring di `search_combined` per rispecchiare il nuovo contratto (budget separato,
      ritorno `FusedResults`).
- [x] Verifica: la firma aderisce al library-contract.md; nessun consumatore è ancora
      aggiornato a questo punto (la suite sarà rossa — normale, il giro è atomico).

### TASK-R02 — Aggiorna `fusion.py`: `fusion_coverage` consuma `FusedResults` [P]
**File**: `src/sertor_core/services/eval/fusion.py`
→ dipende da: TASK-R01, TASK-F01
- [x] Aggiorna la firma di `fusion_coverage`:
      ```python
      # PRIMA
      def fusion_coverage(cases, search_fn: Callable[[str, int], list[RetrievalResult]], k) -> FusionReport:

      # DOPO
      def fusion_coverage(cases, search_fn: Callable[[str, int], FusedResults], k) -> FusionReport:
      ```
- [x] Aggiorna il corpo per leggere `has_doc`/`has_code` dalle **due liste separate** (data-model §3):
      ```python
      fused = search_fn(case.query, k)           # FusedResults
      has_doc  = any(r.path in expected for r in fused.docs)
      has_code = any(r.path in expected for r in fused.code)
      covered  = has_doc and has_code
      hit_at_k = any(r.path in expected for r in fused.flatten())
      ```
      Non si filtra più per `doc_type` su una lista unica: `has_doc` dalla lista `docs`,
      `has_code` dalla lista `code` (più semplice e più fedele al contratto, FR-006).
- [x] `FusionCaseResult`/`FusionReport` (`models.py`) **non cambiano forma**: cambia solo la
      sorgente di `has_doc`/`has_code`. Se `models.py` è in un file separato, verificare che
      le entità siano importate, non ridefinite.
- [x] Verifica: funzione pura deterministica (stesso input → stesso output); mockabile con
      `search_fn=lambda q,k: FusedResults(docs=(...), code=(...))`.

### TASK-R03 — Aggiorna `fused_runner.py`: `_SURFACES` 3→2 + fusion coverage sulla coppia [P]
**File**: `src/sertor_core/services/eval/fused_runner.py`
→ dipende da: TASK-R01, TASK-R02
- [x] Rimuovi `"search_combined"` da `_SURFACES` (data-model §4, research §superficie):
      ```python
      # PRIMA
      _SURFACES = ("search_code", "search_docs", "search_combined")

      # DOPO
      _SURFACES = ("search_code", "search_docs")
      ```
      `FusedEvalReport.surfaces` conterrà quindi 2 `SurfaceEvalReport` invece di 3.
- [x] `_SurfaceEngine` (o la logica equivalente) non deve più wrappare `search_combined` come
      superficie IR ranked (era la metrica sbagliata su score incommensurabili — research §superficie).
      `search_combined` è misurato **esclusivamente** dalla fusion coverage.
- [x] La chiamata a `fusion_coverage` già usa `facade.search_combined` come `search_fn`: ora che
      `search_combined` ritorna `FusedResults`, la firma di `fusion_coverage` è aggiornata (TASK-R02)
      → la chiamata è già corretta. Verificare che la signature sia coerente.
- [x] Aggiorna `emit_fused_eval_event` (o `emit_fused_eval_event`): i campi `surface_mrr` e
      `surface_hit3` ora hanno **2 chiavi** (`search_code`/`search_docs`) invece di 3
      (event-fused-eval.md). Il campo `cases.both` (`fusion.cases_count`) resta invariato.
      Cardinalità chiusa, metrics-only, nessun testo libero (Principio IX).
- [x] Verifica: l'evento `fused_eval` ha esattamente le 2 chiavi in `surface_mrr`/`surface_hit3`;
      nessun riferimento a `search_combined` in `_SURFACES` o nell'evento.

### TASK-R04 — Aggiorna CLI `_cmd_search` in `cli/__main__.py`: consuma `FusedResults` [P]
**File**: `src/sertor_core/cli/__main__.py` (righe 508–510 circa: `_cmd_search`, e 687–704: `_fused_baseline_from`)
→ dipende da: TASK-R01, TASK-F01
- [x] Nella funzione `_cmd_search` (gestione `--type both`): sostituisci il consumo di
      `list[RetrievalResult]` con il consumo di `FusedResults` (cli-search-combined.md):
      - `facade.search_combined(query, k)` ritorna ora un `FusedResults`.
      - Passa `FusedResults` al formatter `format_search_results` (TASK-R05 aggiornerà il formatter;
        questo task adegua solo il punto di chiamata).
- [x] `--type code` e `--type doc` restano invariati (SC-002): non toccarli.
- [x] Nella funzione `_fused_baseline_from` (righe 687–704): aggiorna per iterare su
      `report.surfaces` (che ora ha 2 elementi invece di 3) — la forma è invariata, cambia solo
      che le superfici sono 2 (data-model §5). Verificare che l'iterazione non faccia assunzioni
      sul numero fisso di superfici.
- [x] Verifica: il CLI thin (nessuna logica di metrica nel CLI, Principio I); exit code coerenti;
      nessun import diretto di adapter.

### TASK-R05 — Aggiorna `cli/output.py`: `format_search_results` a due sezioni etichettate [P]
**File**: `src/sertor_core/cli/output.py`
→ dipende da: TASK-F01
- [x] Aggiorna `format_search_results` (o la funzione che rende il combined) per accettare
      `FusedResults` quando `--type both` (cli-search-combined.md):
      ```
      # Resa umana:
      docs:
        <risultati doc, formato esistente per ciascun risultato>

      code:
        <risultati code, formato esistente per ciascun risultato>
      ```
      Ogni sezione usa la logica `format_search_results` esistente per i singoli risultati
      (no duplicazione, Principio III/VII). Sezione senza risultati → etichetta + riga
      `(nessun risultato)` (degrado onesto, niente silenzio).
- [x] In modalità `--json` (`--type both`):
      ```json
      { "docs": [ {…} ], "code": [ {…} ] }
      ```
      Gemello del MCP (cli-search-combined.md). `--type code`/`--type doc` restano lista JSON
      come oggi (invariati).
- [x] `search_code`/`search_docs` (`--type code`/`--type doc`) producono ancora una sezione unica
      (invariati — SC-002): non toccarli.
- [x] Formato citabile `path#chunk` preservato (cli-search-combined.md §Invarianti).
- [x] Funzione pura (zero I/O, zero side-effect): testabile senza adapter.

### TASK-R06 — Aggiorna `src/sertor_mcp/server.py`: tool `search_combined` → `{"docs","code"}`
**File**: `src/sertor_mcp/server.py` (righe 114–117 circa + `_run`/`_fmt`)
→ dipende da: TASK-R01, TASK-F01
- [x] Il tool MCP `search_combined` ora ritorna un `dict` invece di `list[dict]`
      (mcp-search-combined.md):
      ```python
      @mcp.tool()
      def search_combined(query: str, k: int = 6) -> dict:
          fused = facade.search_combined(query, k)   # FusedResults
          return {
              "docs": [_fmt(r) for r in fused.docs],
              "code": [_fmt(r) for r in fused.code],
          }
      ```
- [x] `_fmt(r)` è invariato (path/source/chunk/score/preview, formato citabile `path#chunk`).
- [x] Una lista vuota → chiave esiste comunque con `[]` (forma sempre strutturata —
      mcp-search-combined.md §Una lista vuota).
- [x] `_guard` invariato: persiste `mcp.search_combined.error` e ri-solleva (visibilità,
      Principio XII). Il log di superficie `mcp.search_combined` può riportare `docs`/`code` counts.
- [x] `search_code`/`search_docs` e gli altri 4 tool invariati (solo `search_combined` cambia).
- [x] Aggiorna docstring del tool `search_combined` e le `instructions` del server (righe 33–37
      circa) per indicare che il tool ritorna i due flussi etichettati `{"docs","code"}` —
      testo «use when both are needed» invariato nel senso, aggiorna solo la descrizione del formato.

### TASK-R07 — Aggiorna test del refactor: facade + eval (unit, F.I.R.S.T.) [P]
**File**: `tests/unit/test_retrieval_facade.py`, `tests/unit/test_fusion.py`,
          `tests/unit/test_fused_runner.py`, `tests/unit/test_regression_fused.py`,
          `tests/unit/test_baseline_io_fused.py`
→ dipende da: TASK-R01, TASK-R02, TASK-R03
- [x] **`test_retrieval_facade.py`** — aggiorna/aggiungi casi per `search_combined`:
      - `search_combined` ritorna `FusedResults` (non più `list[RetrievalResult]`).
      - `fused.docs` contiene solo `DocType.DOC`; `fused.code` solo `DocType.CODE`.
      - Budget separato: con mock che dà score più alti ai doc, `fused.code` **non** è vuota
        (SC-001/US1 — la causa-radice del budget condiviso non si ripresenta).
      - Indice senza codice → `code=()`, `docs` popolata (edge case).
      - `search_code`/`search_docs` invariati: stesso tipo e valori di prima (SC-002).
      - `flatten()` su `FusedResults` produce lista deterministica (verifica almeno un caso).
- [x] **`test_fusion.py`** — aggiorna per `search_fn: Callable[[str,int], FusedResults]`:
      - `fusion_coverage([caso_both], search_fn=mock_FusedResults(docs=[d_pert], code=[c_pert]), k=5)`
        → `covered=True`, `coverage=1.0`.
      - Mock che ritorna `FusedResults(docs=[d_pert], code=[])` → `covered=False`, `has_code=False`,
        `hit_at_k=True` (via `flatten()`), `hit_but_not_covered=1`.
      - Mock che ritorna `FusedResults(docs=[], code=[c_pert])` → `covered=False`, `has_doc=False`.
      - `fusion_coverage([], ...)` → report vuoto onesto (coverage=0.0, cases_count=0).
      - Determinismo: stesso `FusedResults` mock → stesso `FusionReport` su chiamate multiple.
- [x] **`test_fused_runner.py`** — aggiorna per le 2 superfici:
      - `run_fused_evaluation(facade_mock, suite_intent, ks, fusion_k)` → `FusedEvalReport` con
        **2** `SurfaceEvalReport` (search_code/search_docs, non 3).
      - `emit_fused_eval_event` emette `surface_mrr`/`surface_hit3` con esattamente 2 chiavi
        (`search_code`/`search_docs`); verifica via `caplog` o mock di `log_event` che `search_combined`
        non compaia come chiave (Principio IX/metrics-only, event-fused-eval.md).
      - Nessun campo di testo libero emesso nell'evento.
- [x] **`test_regression_fused.py`** — verifica coerente con 2 superfici (non 3):
      - Il verdetto di regressione copre le 2 superfici + `fusion_coverage`.
      - Nessun delta per `search_combined` (rimosso).
- [x] **`test_baseline_io_fused.py`** — round-trip con `[fused_baseline]` a 2 `[[fused_baseline.surface]]`
      (non 3):
      - File con voce `search_combined` in `[fused_baseline]` pre-esistente → il round-trip la
        esclude dopo il refactor (o verifica che il loader ignori voci extra). Se il loader
        tollera voci non in `_SURFACES`, documentare il comportamento.
      - Preserve-both: `[baseline]` IR non toccato da `write_fused_baseline`.
- [x] Tutti i test: `@pytest.mark.not_cloud` o nessun marker; zero rete.

### TASK-R08 — Aggiorna test CLI + MCP + integration: consumatori di prima parte [P]
**File**: `tests/unit/test_output_fused_eval.py`, `tests/unit/test_cli_fused_eval.py`,
          `tests/unit/test_mcp_server.py`, `tests/integration/test_end_to_end.py`
→ dipende da: TASK-R04, TASK-R05, TASK-R06
- [x] **`test_output_fused_eval.py`** — aggiorna il formatter per la resa a due sezioni:
      - `format_search_results` con `FusedResults` e `--type both` → output umano contiene sezione
        `docs:` E sezione `code:` etichettate.
      - `--json` con `FusedResults` → `{"docs":[...],"code":[...]}` (valido JSON).
      - `FusedResults` con `docs=()` → output umano ha etichetta `docs:` + `(nessun risultato)`.
      - `--type code`/`--type doc` invariati (una sola sezione, stesso output di prima — SC-002).
- [x] **`test_cli_fused_eval.py`** — aggiorna i test del percorso `--type both`:
      - `search --type both` con facade mock che ritorna `FusedResults` → exit 0, output con
        due sezioni `docs`/`code`.
      - `search --type both --json` → output JSON con le due chiavi.
      - `search --type code`/`--type doc` → output invariato (SC-002, non 2 sezioni).
      - `_fused_baseline_from` con `FusedEvalReport` a 2 superfici → itera correttamente.
- [x] **`test_mcp_server.py`** — aggiorna i test del tool `search_combined`:
      - Tool ritorna `dict` con chiavi `docs`/`code`, ciascuna `list[dict]` con i campi `_fmt`
        (`path`/`source`/`chunk`/`score`/`preview`).
      - `FusedResults(docs=(), code=[c])` → `{"docs":[],"code":[{…}]}` (chiave `docs` con `[]`).
      - Errore del facade → evento `mcp.search_combined.error` + ri-sollevato (invariato).
      - `search_code`/`search_docs` tool invariati (ritornano `list[dict]` come prima).
- [x] **`tests/integration/test_end_to_end.py`** — aggiorna i casi che esercitano `search_combined`:
      - Verifica che il combined restituisca la struttura `FusedResults` (o il JSON `{"docs","code"}`
        a seconda di come il test esercita la surface).
      - Nessun chiamante di `search_combined` assume più il vecchio `list[RetrievalResult]`.
- [x] Tutti i test: `not cloud`, deterministici; i test `@integration` usano corpus minimale locale.

---

## Fase 3 — Polish e cross-cutting (3 task)

> Prerequisiti: Fase 2 completa (suite verde). TASK-P01 e TASK-P02 sono parallelizzabili tra loro.
> TASK-RB01 è separato perché richiede indice dogfood attivo.

### TASK-P01 — Suite non-cloud verde + lint ruff pulito [P]
→ dipende da: tutti i task della Fase 2
- [x] Esegui `uv run pytest -m "not cloud" tests/unit/` → verde (tutti i test unit, inclusi
      quelli pre-esistenti IR/graph-eval che devono restare invariati — RNF-5).
- [x] Esegui `uv run pytest -m "not cloud" tests/` → verde (suite completa escludendo `@cloud`).
- [x] Esegui `uv run ruff check .` → zero errori sui file nuovi/modificati
      (regole E,F,I,UP,B; line-length 100). Correggi eventuali errori prima del merge.
- [x] Verifica che i test esistenti IR (`eval run`, senza `--fused`) e graph-eval siano
      **invariati**: nessuna modifica alle loro fixture o ai loro path — SC-002/RNF-5.

### TASK-P02 — Verifica additività residua: `search_code`/`search_docs`/porte/engine invariati [P]
→ dipende da: tutti i task della Fase 2
- [x] Verifica che **nessun** file tra i seguenti sia stato modificato (RNF-1/SC-010):
      - Porte del domain: `src/sertor_core/domain/ports.py` (EmbeddingProvider, VectorStore, …)
      - Engine: `src/sertor_core/engines/hybrid.py`, `engines/baseline.py`, `engines/evaluation.py`
      - Adapter: `src/sertor_core/adapters/` (tutti i file)
      - `services/retrieval.py` solo `search_code` e `search_docs` (non toccarli)
      - `apply_min_score` e `content_fields` in `services/retrieval.py`
      - `composition.py` (le factory `build_*` esistenti restano invariate; nessuna nuova factory
        richiesta per questo refactor)
- [x] Verifica comportamenti CLI invariati (spot check manuale o via test):
      - `uv run sertor-rag search "test" --type code` → output invariato (una sezione, `list`).
      - `uv run sertor-rag search "test" --type doc` → output invariato.
      - `uv run sertor-rag eval run` (IR, senza `--fused`) → output invariato (hit@k/MRR, nessun
        `fusion_coverage`, nessun overhead).
      - `uv run sertor-rag graph-eval run` → invariato.
- [x] Documenta l'additività verificata come commento nel tasks.md o nel commit brief.

### TASK-P03 — Smoke test MCP con nuovo contratto (post-merge, pre-re-baseline)
→ dipende da: TASK-P01, TASK-P02
- [x] Dopo il merge su master (o su branch pronto), riavvia il server MCP `sertor-rag`
      (serve codice nuovo, non solo indice — quickstart §4).
- [x] Esercita il percorso del filtro metadata (regola standing, CLAUDE.md):
      - `search_code` con query a tua scelta → risposta con `list[dict]` invariata.
      - `search_docs` con query a tua scelta → risposta con `list[dict]` invariata.
      - `search_combined` con query a tua scelta → risposta `{"docs":[…],"code":[…]}` (nuovo contratto).
      - `find_symbol` su simbolo a posizione nota → riga coerente col file reale (freschezza
        code-graph).
- [x] Un tool in errore → segnala esplicitamente (regola *errori-MCP = finding, mai rumore*);
      riconnetti il server e ri-verifica; mai degradare in silenzio.

---

## Fase 4 — Re-baseline (1 task, richiede indice attivo)

> Questa fase è MECCANICA ma **non automatica**: richiede il corpus dogfood indicizzato e il
> backend Azure-large attivo (costo centesimi). Va eseguita dal flusso principale dopo il merge
> dell'MVP meccanico su master e dopo il re-index dogfood (`uv run sertor-rag index .`).

### TASK-RB01 — Ri-registra la baseline fusa su Azure-large dopo il refactor
**File**: `eval/baseline.toml` (sezione `[fused_baseline]`, aggiornata in-place)
→ dipende da: tutti i task delle Fasi 0–3 **su master** + indice dogfood attivo

> **STATO (2026-06-21): DIFFERITO.** Le Fasi 0–3 (13 task meccanici) sono complete e verdi offline.
> Questo task richiede l'indice dogfood attivo (Azure-large) e va eseguito dal flusso principale
> **dopo il merge** su master e il re-index (`uv run sertor-rag index .`). Non eseguibile offline.
- [ ] **PRECONDIZIONE**: corpus dogfood `sertor` indicizzato con `uv run sertor-rag index .`;
      backend Azure-large attivo (`RAG_BACKEND=azure`, `AZURE_OPENAI_DEPLOYMENT=text-embedding-3-large`).
- [ ] Misura con il nuovo contratto (vehicle, Principio XI):
      ```powershell
      uv run sertor-rag eval run --fused
      ```
      Verifica: exit 0; fusion coverage **supera** la baseline precedente 0.17 (SC-004/FR-008);
      le superfici IR riportate sono 2 (`search_code`/`search_docs`, non 3).
- [ ] Ri-registra la baseline fusa:
      ```powershell
      $env:RAG_BACKEND="azure"
      uv run sertor-rag eval run --fused --record-baseline
      ```
      Verifica: la sezione `[fused_baseline]` in `eval/baseline.toml` è aggiornata con il nuovo
      `fusion_coverage` (> 0.17 atteso) e **2** `[[fused_baseline.surface]]` (search_code/search_docs);
      la sezione `[baseline]` IR e `[graph_baseline]` sono **intatte** (preserve-both, SC-005/FR-007).
- [ ] Documenta il valore esatto di `fusion_coverage` ottenuto come finding (è il numero che
      dimostra il valore del refactor — RNF-2/SC-004).
- [ ] **Natura**: MECCANICO ma **richiede indice attivo** (Azure-large). Non è un test automatico;
      è un passo operativo del piano eseguito dal flusso principale nel contesto dell'implementazione.

---

## Grafo delle dipendenze (sintesi)

```
TASK-F01 (FusedResults + flatten) ──────────────────────────────────────────┐
         │                                                                    │
         └→ TASK-G01 (riesporta FusedResults da __init__)                   │
                  │                                                           │
                  └→ TASK-R01 (facade search_combined → FusedResults) ───────┤
                           │                                                  │
                           ├→ TASK-R02 [P] (fusion.py: search_fn tipato)     │
                           │        └→ TASK-R03 (fused_runner: _SURFACES 2)  │
                           │                                                  │
                           ├→ TASK-R04 [P] (CLI _cmd_search: FusedResults)   │
                           │        └→ TASK-R05 (output.py: 2 sezioni)       │
                           │                                                  │
                           └→ TASK-R06 [P] (MCP: {"docs","code"})            │
                                                                              │
                  TASK-R07 [P] (test facade+eval) ← TASK-R01, R02, R03       │
                  TASK-R08 [P] (test CLI+MCP+e2e) ← TASK-R04, R05, R06      │
                                                                              │
                  TASK-P01 [P] (suite verde + lint) ← tutti R0x             │
                  TASK-P02 [P] (additività residua) ← tutti R0x             │
                  TASK-P03 (smoke test MCP) ← P01, P02                       │
                                                                              │
                  TASK-RB01 (re-baseline, indice attivo) ← P01..P03 su master│
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (due flussi etichettati, budget separato) | `search_combined` ritorna `FusedResults`; `fused.docs` solo DOC, `fused.code` solo CODE; con doc ad alto score, `code` **non** è vuota (budget separato, causa-radice non si ripresenta); edge case una lista vuota → coppia sempre strutturata; `flatten()` deterministico (5 casi table). | TASK-F01, TASK-R01, TASK-R07 | MECCANICO |
| **US2** (mono-tipo invariati) | `search_code`/`search_docs` ritornano `list[RetrievalResult]` (tipo e valori invariati rispetto a prima del refactor); nessun file di porte/engine/adapter è stato modificato; CLI `--type code`/`--type doc` producono output invariato. | TASK-R07, TASK-P02 | MECCANICO |
| **US3** (consumatori di prima parte aggiornati) | Suite verde post-refactor; lint ruff pulito; MCP ritorna `{"docs","code"}` con ogni chiave sempre presente; CLI `--type both` produce 2 sezioni etichettate; `--json` produce `{"docs","code"}`; nessun chiamante assume più `list[RetrievalResult]`. | TASK-R04–R08, TASK-P01 | MECCANICO |
| **US4** (fusione migliora > 0.17) | `eval run --fused` sul dogfood con nuovo contratto → `fusion_coverage > 0.17`; la baseline fusa è ri-registrata con 2 superfici (non 3); `[baseline]` IR intatta; il numero è deterministico e riproducibile. | TASK-R02, TASK-R03, TASK-RB01 | MECCANICO (meccanismo) + **richiede indice attivo** (RB01) |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 (senza prerequisiti):**
- TASK-F01 (entità `FusedResults` + test `flatten()`)

**Sprint 2 (dopo Sprint 1):**
- TASK-G01 (export `__init__`)
- TASK-R01 (facade — bloccante per tutto il blocco R)

**Sprint 3 (dopo Sprint 2 — blocco atomico, proseguire in parallelo dove indicato):**
- TASK-R02 [P] (fusion.py) — parallelizzabile con R03
- TASK-R03 (fused_runner) — dopo R02
- TASK-R04 [P] (CLI `_cmd_search`) — parallelizzabile con R02/R03
- TASK-R05 (output.py) — dopo R04 (o in parallelo se le interfacce sono già stabilite)
- TASK-R06 [P] (MCP) — parallelizzabile con R02/R04

**Sprint 4 (dopo Sprint 3 — test atomici insieme all'implementazione):**
- TASK-R07 [P] (test facade+eval) — parallelizzabile con R08
- TASK-R08 [P] (test CLI+MCP+e2e)

**Sprint 5 (suite verde — Polish):**
- TASK-P01 [P] (suite verde + lint)
- TASK-P02 [P] (additività residua)
- TASK-P03 (smoke test MCP, dopo P01+P02)

**Sprint finale (su master, indice attivo):**
- TASK-RB01 (re-baseline Azure-large, passo operativo)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per Tempo 2 FEAT-003 — search_combined strutturato

Fase SpecKit "tasks" completata per specs/070-search-combined-strutturato.
14 task in 5 fasi:
  Fase 0 Setup    : 1 task  (TASK-G01 — export FusedResults)
  Fase 1 Fondaz.  : 1 task  (TASK-F01 — entità FusedResults + flatten)
  Fase 2 Refactor : 8 task  (TASK-R01..R08 — breaking change atomico, tutti i consumatori)
  Fase 3 Polish   : 3 task  (TASK-P01..P03 — suite verde, lint, smoke test MCP)
  Fase 4 Re-base  : 1 task  (TASK-RB01 — re-baseline dogfood, richiede indice attivo)

Task MECCANICI (automatizzabili, nessun indice): 13 (Fasi 0-3 complete).
Task che richiedono INDICE ATTIVO: 1 (TASK-RB01, Azure-large, passo operativo post-merge).

Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/070-search-combined-strutturato/tasks.md` (questo file, nuovo)
