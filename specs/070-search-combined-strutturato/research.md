# Phase 0 — Research: `search_combined` a contratto strutturato (Tempo 2 FEAT-003)

**Branch**: `070-search-combined-strutturato` · **Spec**: [`spec.md`](./spec.md) · **Data**: 2026-06-21

Questo documento risolve le forche di design DA-a..d della spec e ancora ogni decisione all'esistente
(verificato via MCP `sertor-rag` + `Read`). Lo scope è **fisso** (contratto strutturato a due flussi
etichettati con `flatten()`); qui si decide solo il *come*.

> **Nota di processo.** `.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> sono **ASSENTI** nel repo (come per le feature 052/058/065/066). Parametri ricavati per convenzione dal
> branch: `FEATURE_SPEC = specs/070-search-combined-strutturato/spec.md`, `IMPL_PLAN =
> specs/070-search-combined-strutturato/plan.md`, `SPECS_DIR = specs/070-search-combined-strutturato/`,
> `BRANCH = 070-search-combined-strutturato`. Nessun hook SpecKit eseguito.
> **MCP `sertor-rag` interrogato** (`search_code` ×2): nessun errore tool — l'indice dogfood ha servito i
> riferimenti correttamente. Per i file puntuali (entità, server, runner) si è usato `Read` dopo che l'MCP
> ha indicato i percorsi.

---

## 0. Causa-radice, misurata (perché esiste questa feature)

Il Tempo 1 (`069`) ha **misurato** che `search_combined` non funziona per il caso-firma
requisito→implementazione: **fusion coverage 0.17 (1 caso su 6)** — registrata in
`eval/baseline.toml` `[fused_baseline]` `fusion_coverage = 0.1667`.

La causa è strutturale e verificata nel codice: `search_combined` fonde doc+code in **una sola lista
ranked a budget condiviso** — `RetrievalFacade.search_combined → self._search(query, k, "both")`
(`src/sertor_core/services/retrieval.py:166-175`), che fa `store.query(collection, vector, k, "both")`
e ritorna i primi `k` ordinati per score. Gli score code/doc sono **incommensurabili** (è la stessa
ragione per cui l'ibrido usa RRF tra dense e BM25): i documenti, prosa NL vicina alla query NL, hanno
score più alti e **annegano** il codice nello stesso top-k conteso. Misurare la fusione su una lista
unica è una **congiunzione su slot contesi**: servono doc *e* code nello **stesso** budget.

**Decisione (scope, già in spec).** Si **ripara la causa** (Principio XII): `search_combined` ritorna
una **coppia strutturata** `(docs, code)`, **ciascuna col proprio top-k** (budget separato) → la
misura diventa **unione di due top-k indipendenti**, non più congiunzione su slot contesi. Breaking
change volontario (vedi §6).

---

## DA-a — Forma esatta dell'entità di ritorno

**Decisione:** una dataclass **frozen** nel dominio:

```python
# src/sertor_core/domain/entities.py
@dataclass(frozen=True)
class FusedResults:
    """Structured return of `search_combined` (070): the two labelled flows of the fusion.

    `docs` and `code` are each rank-ordered (own top-k, separate budget): no cross-type blended
    ranking (scores are incommensurable — root cause of 069's 0.17). `flatten()` produces a single
    deterministic list for consumers that want one (DA-c). Pure data, no SDK (Principio I)."""
    docs: tuple[RetrievalResult, ...] = ()
    code: tuple[RetrievalResult, ...] = ()

    def flatten(self) -> list[RetrievalResult]: ...
```

**Rationale.**
- **Frozen dataclass nel `domain`** — coerente con tutte le entità esistenti (`RetrievalResult`,
  `ContextBundle`, `GraphData`): nessun import di SDK (Principio I), structural-typing-friendly. La
  spec suggerisce `FusedResults(docs, code)`; lo adottiamo.
- **`tuple` invece di `list`** per i campi — immutabilità coerente con `ContextBundle.definitions`,
  `GraphData.nodes` (tutte tuple); `flatten()` ritorna una `list` perché è il tipo che i consumatori
  (CLI/MCP/test) si aspettano da un'operazione di composizione, gemello di `RetrievalResult` listati.
- **Niente metadato aggiuntivo nell'MVP** (YAGNI, Principio III): nessun `query`/`provider`/`elapsed`
  sull'entità. L'osservabilità resta nei `log_event` della facade (Principio IX); l'entità è puro
  dato di ritorno. Se in futuro servisse un metadato, è additivo (campo con default).
- **Nome `FusedResults`** — vocabolario di dominio (Principio VII): «fuse» è già il verbo del dominio
  (vedi docstring `_materialize` ibrido, mission «fusione code+doc»).

**Alternative scartate.**
- `NamedTuple` — meno espressivo per docstring/metodo; il repo usa `@dataclass(frozen=True)` ovunque
  per le entità (coerenza, Principio VII).
- `dict {"docs": [...], "code": [...]}` — niente tipo, niente `flatten()` come metodo, niente
  garanzie statiche; è la forma di **serializzazione** (DA-d), non quella di dominio.
- Generalizzare a `FusedResults(by_type: dict[DocType, ...])` — over-engineering: oggi i tipi sono
  esattamente due (`DocType.CODE`/`DocType.DOC`); i due campi nominati sono più leggibili e bastano
  (Principio III).

---

## DA-b — Allocazione dei k per `docs` e `code`

**Decisione:** **budget separato** — `docs` ottiene il proprio top-k e `code` il proprio top-k;
**nessun budget condiviso**. Default: **stesso `k`** per entrambe (il `k` passato a `search_combined`,
o `default_k` da `Settings`). **Nessuna nuova manopola host-facing** nell'MVP.

**Rationale.**
- È **il punto del refactor** (FR-001/SC-001): se le due liste contendessero un budget unico,
  avremmo solo spostato il problema. Due budget separati = due top-k indipendenti.
- **`k` unico per entrambe** è la scelta più semplice e la meno sorprendente: chi chiama
  `search_combined(query, k=6)` ottiene «fino a 6 doc **e** fino a 6 code». Riusa il `default_k`
  esistente della facade (Principio VIII — config centralizzata, niente hardcode).
- **Nessun `SERTOR_COMBINED_K_DOCS`/`_CODE`** ora (YAGNI, Principio III): non c'è evidenza presente di
  voler k asimmetrici. Se servisse, sarebbe additivo in `Settings` + template `.env` dell'installer
  (corollario installabile della spec) — tracciato come possibile estensione, non implementato.

**Implementazione (riuso del path mono-tipo esistente).** `search_combined` chiamerà **due volte** il
percorso interno per tipo singolo, una con filtro `"doc"` e una con `"code"`, ciascuna col proprio
budget `k`. Questo riusa `_search(query, k, "doc")` e `_search(query, k, "code")` — gli **stessi**
percorsi di `search_docs`/`search_code` (che restano invariati, FR-003), incluso il logging
`retrieve` per superficie, `apply_min_score`, e la delega al `retriever` ibrido se presente. La
facade compone i due risultati in `FusedResults`.

> **Conseguenza sul fan-out multi-corpus (feature 010).** Oggi `search_combined` instrada al
> `_search_multi` quando ci sono `extra_collections` (corpora disgiunti). Con il nuovo contratto, la
> coppia `(docs, code)` si ottiene filtrando **per `doc_type`** su tutte le collezioni-target: ogni
> lista (`docs`/`code`) fa il fan-out con il proprio filtro e il proprio top-k. La logica di
> `_available_targets()` (degrado `no_index`, `ProviderMismatchError`) **si conserva**; cambia solo
> che si producono due liste filtrate per tipo invece di una lista blended. Nessuna porta toccata.

**Alternative scartate.**
- Budget condiviso «smart» (es. 70% doc / 30% code) — è ancora una congiunzione su slot, e arbitraria
  (è proprio la causa che stiamo eliminando).
- Manopole k asimmetriche di default — YAGNI; le aggiungiamo solo guidati da misura (l'epica ha
  FEAT-005/006/007 per le leve).

---

## DA-c — Strategia di `flatten()`

**Decisione:** **interleave per rank** deterministico — `docs[0], code[0], docs[1], code[1], …`,
preservando il bilanciamento; gli **avanzi** della lista più lunga vanno in coda nel loro ordine.
Su una lista vuota → produce l'altra; su due vuote → `[]`.

```
flatten():  for i in range(max(len(docs), len(code))):
                if i < len(docs): out.append(docs[i])
                if i < len(code): out.append(code[i])
            return out
```

**Rationale.**
- **Score-merge è scartato** — fondere per score è esattamente la causa-radice (score
  incommensurabili). `flatten()` **non** deve reintrodurla.
- **Interleave** preserva il valore del refactor anche nella lista unica: alterna i due flussi così
  che nemmeno la lista appiattita faccia annegare il codice (il primo code arriva in posizione 2, non
  in coda). È **deterministico** (FR-002/SC-003): stesso input → stesso ordine, nessun float-compare.
- **Concat doc-then-code** scartato come default — riproporrebbe l'annegamento (tutti i doc prima di
  ogni code) nella lista appiattita; l'interleave è più fedele alla missione (doc *e* code affiancati).
- È **puro** e privo di I/O: testabile con liste fittizie (gemello di `apply_min_score`).

**Edge case (dalla spec).** `flatten()` su coppia con una lista vuota → la lista non vuota,
deterministicamente; due liste vuote → `[]`. Coperti dal `range(max(...))` + i due guard `if i < len`.

---

## DA-d — Serializzazione MCP/CLI dei due flussi etichettati

**Decisione (MCP):** il tool `search_combined` ritorna un **oggetto strutturato etichettato**
`{"docs": [...], "code": [...]}` (non più `list[dict]`), dove ogni elemento è il `_fmt(r)` esistente
(`path`/`source`/`chunk`/`score`/`preview`). Mantiene il **formato citabile `path#chunk`**.

**Decisione (CLI):** `search --type both` rende **due sezioni etichettate** — una intestazione `docs`
e una `code`, ciascuna con i propri risultati nel formato `format_search_results` esistente. In
modalità `--json`, `{"docs": [...], "code": [...]}` (gemello del MCP). `search_code`/`search_docs`
restano una sezione unica come oggi.

**Rationale.**
- **MCP oggetto etichettato** — è la resa migliore **per l'agente** (FR-005/SC-007): l'agente vede
  esplicitamente *il perché* (docs) e *il cosa* (code) separati e decide come sintetizzarli. Coerente
  con la missione («il core riserva i due flussi etichettati; la sintesi la fa l'agente»). Il tool
  `get_context` già ritorna un `dict` strutturato a sezioni (`definitions`/`callers`/…): precedente
  nel server.
- **CLI due sezioni** — l'utente umano vede entrambi i flussi distintamente, non una lista in cui un
  tipo domina. Riusa `format_search_results` per ciascuna sezione (Principio III/VII, no duplicazione).
- **`flatten()` NON è il default della resa** — i consumatori che renderebbero una lista unica
  (improbabile per il combined) userebbero `flatten()` esplicitamente; per MCP/CLI la forma etichettata
  è il punto.

**Aggiornamento dell'help/instructions MCP.** La docstring del tool `search_combined` e le
`instructions` del server (`server.py:33-37`) menzionano «search_combined when both are needed» — il
testo resta valido; si aggiorna solo per dire che ritorna i due flussi etichettati.

**Alternative scartate.**
- MCP che ritorna `flatten()` come `list[dict]` (retrocompat con la forma vecchia) — perde
  l'etichettatura, il valore-chiave per l'agente (FR-005). La spec ha deciso il breaking change: lo
  onoriamo fino alla superficie.
- CLI lista unica con colonna «type» — meno leggibile delle due sezioni; le sezioni rendono il
  «budget separato» evidente.

---

## Metrica di fusion coverage — adattamento alle DUE liste

**Decisione:** `fusion.py`/`fused_runner.py` consumano la **coppia** `FusedResults`:
- **copertura** = (la lista `docs` (top-k) contiene un **doc pertinente**) **AND** (la lista `code`
  (top-k) contiene un **code pertinente**), dove «pertinente» = `path ∈ expected` (REQ-020/FR-006).
- `has_doc` si calcola sulla **lista `docs`**; `has_code` sulla **lista `code`** — non più filtrando
  per `doc_type` un'unica lista blended. Più semplice e più significativa: rispecchia esattamente il
  contratto (due top-k indipendenti).
- `hit_at_k` (la lacuna visibile REQ-022) = un path atteso è in `flatten()` (o nell'unione delle due
  liste). `hit_but_not_covered` resta il segnale «un tipo annega l'altro», ora **misurato sul
  contratto giusto**.

**Conseguenza misurata attesa.** Su `azure:text-embedding-3-large` la copertura **deve migliorare**
rispetto a 0.17 (FR-008/SC-004): casi che prima fallivano perché il code annegava sotto i doc nello
stesso top-k ora hanno il code nel **proprio** top-k.

### La superficie IR ranked `search_combined`: cosa farne

**Problema.** Oggi il fused-runner misura **tre** superfici IR ranked
(`_SURFACES = ("search_code","search_docs","search_combined")`,
`fused_runner.py:29`): per ciascuna calcola hit-rate@k/MRR via l'invariante `evaluate`, e la baseline
`[fused_baseline]` registra `surface="search_combined"` con `hit_rate`/`mrr` propri
(`eval/baseline.toml:36-43`). Ma `evaluate` su una superficie richiede una **lista ranked unica**
(`QueryableEngine.query → list[RetrievalResult]`): con il nuovo contratto `search_combined` **non**
ritorna più una lista ranked unica — il suo «ranking» cross-tipo è precisamente ciò che si è
dichiarato privo di senso (score incommensurabili).

**Decisione (documentata, raccomandazione confermata):** **rimuovere `search_combined` dall'insieme
delle superfici IR ranked**. Le superfici IR per-superficie restano **due**:
`search_code` (cases `intent="code"`) e `search_docs` (cases `intent="doc"`). La capacità di
`search_combined` è ora misurata **esclusivamente** dalla **fusion coverage** sulla coppia (la metrica
giusta per un'unione di due top-k). Cioè:
- `_SURFACES → ("search_code", "search_docs")`;
- `FusedEvalReport.surfaces` ha due elementi;
- la fusion coverage **sostituisce** `search_combined` come misura della superficie fusa (non era
  significativa come ranking unico: era la metrica sbagliata applicata alla superficie sbagliata —
  Principio XII, fix the cause).

**Implicazione baseline (re-baseline).** La sezione `[fused_baseline]` perde la voce
`surface="search_combined"` (resta `search_code`/`search_docs` + `fusion_coverage`). Il
`FusedBaseline`/`SurfaceBaseline` non cambiano forma (tuple di superfici): semplicemente conterrà due
superfici. La **baseline va ri-registrata** dopo il refactor (FR-007, **passo del piano, non del
design**) col nuovo `fusion_coverage` (> 0.17 atteso). Le baseline per-superficie `search_code`/
`search_docs` e i casi esistenti restano protetti (RNF-5).

**Alternativa scartata:** mantenere `search_combined` come superficie IR ranked misurando
`evaluate` su `flatten()`. Scartata perché reintrodurrebbe un ranking unico cross-tipo da misurare con
hit@k/MRR — la stessa illusione di commensurabilità che la feature elimina; e duplicherebbe la
copertura (già misurata meglio dalla fusion coverage). Sarebbe «fix the symptom», non «the cause».

---

## Consumatori di prima parte da aggiornare (breaking change, tutto nel repo)

Verificato (MCP + `Grep`): tutti i chiamanti di `search_combined` sono di prima parte. Mappa
consumatore → modifica (dettaglio nel `plan.md`):

| Consumatore | File | Modifica |
|---|---|---|
| Facade `search_combined` | `src/sertor_core/services/retrieval.py:166` | ritorna `FusedResults` (due `_search` per tipo, budget separato); fan-out 010 produce due liste filtrate per tipo |
| Entità | `src/sertor_core/domain/entities.py` | nuova `FusedResults(docs, code)` + `flatten()` |
| Tool MCP | `src/sertor_mcp/server.py:114-117` (+ `_run`/`_fmt`) | output `{"docs":[…],"code":[…]}`; `_run` per il combined adatta la serializzazione |
| CLI esecuzione | `src/sertor_core/cli/__main__.py:508-510` (`_cmd_search`) | `--type both` consuma `FusedResults`, due sezioni |
| CLI resa | `src/sertor_core/cli/output.py` (`format_search_results`) | due sezioni etichettate per il combined / `{"docs","code"}` in JSON |
| Fusion coverage | `src/sertor_core/services/eval/fusion.py` | `has_doc`/`has_code` dalle due liste della coppia |
| Fused runner | `src/sertor_core/services/eval/fused_runner.py:29,77` | `_SURFACES` a due; fusion coverage sulla coppia; evento `fused_eval` (`cases.both` resta) |
| CLI fused-baseline | `src/sertor_core/cli/__main__.py:687-704` | `_fused_baseline_from` itera due superfici (forma invariata) |
| Test | `tests/unit/test_retrieval_facade.py`, `test_fusion.py`, `test_fused_runner.py`, `test_output_fused_eval.py`, `test_cli_fused_eval.py`, `test_regression_fused.py`, `test_baseline_io_fused.py`, `test_mcp_server.py`, `tests/integration/test_end_to_end.py` | adeguati al nuovo contratto/serializzazione |

**Fuori dal blocco (NON toccare):** `search_code`/`search_docs` (FR-003), le **porte**
(`EmbeddingProvider`/`VectorStore`/…), gli **engine** (hybrid/baseline/evaluation `evaluate`
invariato), `apply_min_score`/`content_fields` (riusati). Il prototipo (`prototype/**`) è congelato e
fuori ambito.

---

## Breaking change: perché è ammissibile e come è circoscritto

- **Pre-1.0, distribuzione `git+url`** → nessun contratto pubblico stabile da preservare (Assumptions
  della spec, verificate).
- **Tutti i consumatori sono nel repo** e si aggiornano **in blocco** (FR-004/US3): gate = suite verde
  + lint pulito (RNF-5/SC-006).
- La deviazione è **circoscritta** a `search_combined` + entità nuova + i suoi consumatori di prima
  parte; `search_code`/`search_docs`/porte/engine restano invariati (RNF-1/SC-010).
- È una **scelta motivata** dal Principio XII (riparare la causa di una superficie rotta) e dal gate
  **Allineamento alla missione** (la fusione code+doc è la stella polare, oggi rotta) — vedi
  Constitution Check (Complexity Tracking) nel `plan.md`.

---

## Local-first / determinismo / vehicle (invarianti)

- Nessun LLM nel run oltre l'embedder (RNF-3/SC-008); la misura passa per `sertor-rag eval --fused`
  (vehicle, Principio XI) — `build_fused_eval_runner` invariato come punto d'ingresso.
- `FusedResults`/`flatten()`/fusion coverage sono **puri e deterministici** (Principio VI): stesso
  indice + query → stessa coppia e stesso `flatten()`.
- Misura locale (mock/Chroma), senza rete (RNF-3); il re-baseline su Azure-large è un passo operativo
  del piano (costo centesimi), non un requisito di run.

## Nodi residui

- **Re-baseline**: valore numerico esatto noto solo a refactor implementato (passo del piano). Atteso
  > 0.17; il piano lo registra via `--record-baseline`.
- **k asimmetrici docs/code**: rinviato (YAGNI). Se emergerà dal tuning, additivo (Settings + `.env`).
  Non è un blocco.
- **Nessun `NEEDS CLARIFICATION`**: lo scope è fisso e le quattro forche sono risolte.
