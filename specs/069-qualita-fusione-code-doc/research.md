# Research — Qualità del retrieval fuso code+doc su query NL/architetturali (FEAT-003)

**Branch**: `069-qualita-fusione-code-doc` · **Date**: 2026-06-21 · Fase 0 del `plan`.

**Input**: `spec.md` · `requirements/retrieval-qualita/qualita-search-code-nl/requirements.md`
(REQ-001..043, gruppi A–E, RNF1–5, DA-a..e) · costituzione v1.4.0.

> **Nota di processo.** `.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> **ASSENTI** nel repo → parametri per convenzione dal branch (modello di forma:
> `specs/066-valutazione-navigazione-grafo/`); nessun hook SpecKit eseguito. Git **delegato** al
> `configuration-manager` (mai eseguito qui). MCP `sertor-rag` interrogato per l'ancoraggio
> (`search_code graph_case suite_io`, `search_code evaluate EvalReport per_query`) + `Read` mirati;
> **nessun errore tool** da riportare.

---

## 0. Quadro: cosa esiste già (ancoraggio verificato)

L'harness eval è su `master` (FEAT-001/011). Ancorato via MCP + `Read`:

- `engines/evaluation.py` — `evaluate(engine, ground_truth, ks) → EvalReport` con `hit_rate`/`mrr`/
  `per_query` (tupla di `QueryOutcome`: `query`/`expected`/`hit`/`rank`/`top_path`). **Il core misura,
  non classifica**: il `kind` non vive qui (commento esplicito al modello). `QueryableEngine` =
  `Protocol` (solo `provider` + `query`).
- `services/eval/models.py` — `EvalCase(query, expected, kind)`, `EvalSuite(cases, graph_cases)`,
  `Baseline`, `RegressionVerdict`, `ComparisonReport`, `PathValidation` + il blocco graph (FEAT-011:
  `GraphCase`/`SetMetric`/`GraphEvalReport`/…). `EvalSuite.to_ground_truth()` proietta su `GroundTruth`,
  `kinds()` mantiene il `kind` in parallelo per il report.
- `services/eval/suite_io.py` — `load_suite`/`write_suite` su `eval/suite.toml` (TOML letto con
  `tomllib`, **scritto con serializzatore a mano**); `add_case`/`amend_case`/`add_graph_case`/
  `amend_graph_case`. Il writer (`_serialize_suite`) **preserva entrambe** le sezioni `[[case]]` e
  `[[graph_case]]` (DA-d di FEAT-011) — è il pattern da riusare per il nuovo campo.
- `services/eval/runner.py` — `run_evaluation(engine, suite, ks) → (EvalReport, kinds)`,
  `emit_eval_event` (evento `eval` metrics-only), `RoutedEvalEngine` (routing per `kind`),
  `validate_paths`.
- `services/retrieval.py` — `RetrievalFacade.search_code`/`search_docs`/`search_combined`;
  ogni `RetrievalResult` porta **`doc_type: DocType` (`CODE`/`DOC`)** — il discriminante che la fusion
  coverage richiede esiste **già** nell'entità (`domain/entities.py`).
- CLI `cli/__main__.py` — gruppo `eval` (`run`/`add-case`/`validate-path`) con `--compare`/`--by-kind`/
  `--record-baseline`/`-k`/`--json`; gruppo separato `graph-eval`. `build_eval_runner`/
  `build_graph_eval_runner` in `composition.py` (`_EvalRunner` con `run`/`run_labelled`/`run_by_kind`).

**Conseguenza di design (cardine).** La feature **estende l'harness IR esistente**, non ne crea uno
parallelo. A differenza di FEAT-011 (la navigazione del grafo è *set-based* → oracolo nuovo), qui la
misura è **ancora rank-based** (hit@k/MRR su `search_*`): le due novità — *attesi intent-typed* +
*categoria fusione* + *fusion coverage* — sono **additivi sopra `evaluate`**. La fusion coverage NON è
un secondo oracolo: è una metrica calcolata **dal `per_query` arricchito** dei tipi recuperati.

---

## 1. Le tre superfici come «config etichettate» (riuso del meccanismo `--compare`)

REQ-010 chiede **baseline distinte** per `search_code`/`search_docs`/`search_combined`; REQ-013 misura
il combined come **test d'integrazione**. Domanda: come misurare tre superfici senza tre suite?

**Decisione.** Una **sola** suite (`eval/suite.toml`); ogni `EvalCase` dichiara su **quale superficie**
va misurato (il suo intento, vedi §2). Il run misura ciascuna superficie con la `search_*`
corrispondente, riusando il **meccanismo `--compare` già esistente** in forma generalizzata: invece di
confrontare *engine* (`baseline,hybrid`), il run produce un `EvalReport` **per-superficie**
(`search_code`/`search_docs`/`search_combined`), ognuno valutato **solo** sui casi pertinenti a quella
superficie.

- **Rationale.** `evaluate` è già parametrico sull'`engine` (`QueryableEngine` = `provider`+`query`). Una
  superficie è un **adattatore sottile** `QueryableEngine` che instrada `query` → `facade.search_code`
  (o `_docs`/`_combined`). Tre wrapper minimi sul `RetrievalFacade` (costruito da `build_facade`),
  zero modifiche a `evaluate`. È DRY (Principio III) e riusa la macchina di confronto.
- **Alternativa scartata.** Tre file-suite separati → triplica la manutenzione del set, rompe
  l'invariante «una suite-dato del progetto», complica la genesi assistita. YAGNI.

**Combined come integrazione (REQ-013).** Il combined è misurato sui **casi cross-artefatto** (e su
tutti i casi, come superficie fusa) e su di esso si calcola la **fusion coverage** (§3). «Integrazione»
= il combined deve **mantenere** i tipi che le superfici singole trovano: un guadagno per-superficie che
poi annega un tipo nel combined è respinto dal gate (§4, R-3).

---

## 2. DA-b — Costruzione del set NL: come marcare l'intento (additivo e versionato)

REQ-003 chiede attesi **intent-typed**: source per «where defined», doc per «why/how», **entrambi** per
cross-artefatto. REQ-002 chiede la **categoria fusione** distinta. REQ-004 esclude i casi senza atteso
coerente.

**Decisione — campo additivo `intent` su `[[case]]`.** Estendo `EvalCase` con un campo opzionale
`intent ∈ {code, doc, both}` (default `None`, retrocompatibile coi casi esistenti che hanno solo
`kind`). Semantica:

| `intent` | Superficie misurata | Tipi attesi nel top-k | Categoria |
|---|---|---|---|
| `code` | `search_code` | ≥1 `CODE` pertinente | code-oriented |
| `doc` | `search_docs` | ≥1 `DOC` pertinente | doc-oriented |
| `both` | `search_combined` | ≥1 `DOC` **E** ≥1 `CODE` pertinenti | **fusione (cross-artefatto)** |

- `intent` è **distinto da `kind`** (`symbol`/`nl`): `kind` descrive la *natura* della query (per il
  routing FEAT-011 e il report per-kind); `intent` descrive il *tipo atteso della risposta* e la
  *superficie*. Coesistono (es. un caso `kind="nl"`, `intent="both"`).
- I casi `intent="both"` **sono** la categoria di fusione (REQ-002) — non serve un campo `category`
  separato: `intent="both"` la identifica univocamente (YAGNI). Sono misurabili a sé filtrando per
  `intent`.
- **REQ-004 (esclusione).** Un caso a cui non si può dare un `intent` coerente non si scrive: il writer
  accetta `intent=None` (resta nei conteggi IR generali ma **non** contribuisce alle metriche
  per-superficie/fusione, che richiedono `intent` esplicito). Il criterio «escluso anziché valutato su un
  bersaglio arbitrario» è enforced **a authoring time** (la skill propone `intent`; l'utente che non sa
  assegnarlo non lo scrive) — non è un errore di validazione (un caso IR senza intent resta legittimo per
  hit@k generale).

**Come tipizzare l'`expected`.** L'`expected` resta una **tupla di path** (come oggi): il **tipo** (CODE
vs DOC) di ogni risultato recuperato si legge da `RetrievalResult.doc_type` a runtime, **non** si
duplica nel set. Così la fusion coverage si calcola confrontando i `doc_type` dei risultati top-k con
ciò che l'`intent` richiede, **senza** dover etichettare a mano il tipo di ogni path atteso (meno
manutenzione, meno deriva). Per i casi `both` la copertura è soddisfatta se il top-k contiene ≥1
risultato `DOC` pertinente **e** ≥1 `CODE` pertinente (pertinente = path ∈ `expected`).

**Quante query per superficie (proposta onesta, DA-b).** Minimo per un set rappresentativo ma non
overfittato (R-1): **≥8 per superficie** (`code`/`doc`/`both`), di cui **≥6 cross-artefatto (`both`)**
perché sono la categoria-firma della mission e oggi la più debole (audit: rank 3-6). Totale di partenza
**~24-30 casi NL** accanto ai casi IR/`symbol` esistenti. Numeri **indicativi** (il set cresce con la
genesi assistita, US5); il vincolo duro è solo «coprire tutte e tre le superfici con la categoria
fusione distinta» (SC-001). L'**hold-out** di validazione resta **Could** (R-1, già nel backlog).

**Genesi assistita (DA-b, US5).** Riuso/estensione della skill `eval-suite-author` (FEAT-011 l'ha già
estesa ai `[[graph_case]]`): l'agente legge il corpus **via i tool di retrieval (MCP/CLI)**, propone
candidati `query NL → expected (+ intent)`, l'utente approva, e **solo gli approvati** sono persistiti
**via il vehicle** (`sertor-rag eval add-case --intent …`). Confine D↔N: la skill è **giudizio**, il run
resta deterministico. È un **debito di completamento P2** (gruppo E/Should), come in FEAT-011.

---

## 3. DA — Fusion coverage: definizione operativa (REQ-020/021/022, P2.b)

**Decisione.** La fusion coverage è una **metrica derivata, pura e deterministica**, calcolata sul run
della superficie `search_combined` ristretto ai casi `intent="both"`:

```
per ogni caso `both`:
  top_k = search_combined(query, k)              # già rank-ordinati
  relevant = [r for r in top_k if r.path in expected_set]
  has_doc  = any(r.doc_type == DOC  for r in relevant)
  has_code = any(r.doc_type == CODE for r in relevant)
  covered  = has_doc and has_code                 # REQ-020
fusion_coverage = covered_cases / total_both_cases
```

- **REQ-022 (hit@k non nasconde la lacuna).** Un caso `both` può essere `hit@k` (almeno un path atteso
  nel top-k) ma **non coperto** (manca un tipo). I due numeri sono riportati **affiancati** (REQ-021):
  hit@k/MRR + fusion coverage. La fusion coverage è **più severa** di hit@k by construction.
- **Dove vive.** Funzione **pura** `fusion_coverage(outcomes_with_types) → FusionReport` in un modulo
  nuovo `services/eval/fusion.py`, parallela a `evaluate`. Per calcolarla servono i `doc_type` dei
  risultati: l'adattatore-superficie `search_combined` deve esporre i tipi top-k. Due opzioni studiate:
  - **(A)** arricchire `QueryOutcome` con i tipi recuperati → invasivo su `evaluate`/`EvalReport`.
  - **(B, SCELTA)** un **runner di fusione dedicato** che chiama `facade.search_combined` direttamente
    (è un `RetrievalResult` con `doc_type` e `path`), calcola la copertura, e **non** passa per
    `evaluate` (che proietta via solo i `.path`). `evaluate` resta invariato; la fusione è un secondo
    passaggio additivo sugli stessi casi `both`. **Rationale:** additività massima su `evaluate`
    (Principio I/III), e la fusione è semanticamente «set di tipi presenti», non rank — come l'oracolo
    set-based di FEAT-011 fu tenuto fuori da `evaluate`.
- **Riportata accanto, non al posto (REQ-042/SC-008).** Il `FusionReport` è un **campo additivo** del
  report esteso, non sostituisce hit@k/MRR.

---

## 4. DA-c — Soglie di «miglioramento» e gate di non-regressione (REQ-040, riuso meccanismo)

**Decisione.** Riuso il **meccanismo baseline+tolleranza** già esistente (FEAT-001 `Baseline`/
`RegressionVerdict`/`compare_to_baseline` + `SERTOR_EVAL_TOLERANCE`), esteso a:

1. **Baseline per-superficie** — `eval/baseline.toml` esteso (o sezioni per-superficie) registra
   hit@k/MRR **distinti** per `search_code`/`search_docs`/`search_combined` + la **fusion coverage** del
   combined. Registrazione **solo** su `--record-baseline` esplicito (accettazione esplicita, come oggi).
2. **Gate** — una misura che scende sotto **una qualsiasi** baseline per-superficie (o sui casi IR
   esistenti) oltre tolleranza → `RegressionDetected` (exit 1). La fusion coverage entra nel gate come
   metrica del combined: una leva che migliora una superficie ma **rompe la fusione** è respinta (R-3,
   REQ-040).

**Valori di partenza proposti (DA-c, design — non requisito).**
- **Tolleranza di non-regressione:** `SERTOR_EVAL_TOLERANCE` default `0.0` (come IR) — la baseline è un
  **pavimento**: nessuna regressione tollerata di default. (Resta una manopola dell'ospite.)
- **Delta minimo per «miglioramento» (US4, Should):** un lift è «misurabile» se ≥ **+0.05** su hit@k
  della superficie rilevante **o** ≥ **+0.05** su fusion coverage del combined, rispetto alla baseline.
  Questo NON è un gate (il gate è la non-regressione); è il **criterio di adozione** di una leva
  (giudizio, US3/US4). Valore di partenza onesto, rivedibile dopo aver visto le baseline reali.
- **«Done» della categoria fusione (SC-011):** la fusion coverage è **misurata e riportata** (Must); un
  *target assoluto* (es. ≥0.6) è **Could** — si fissa dopo la baseline reale, non a priori (Principio V:
  prima il numero, poi la soglia).

**Rationale.** Riusare il meccanismo (file versionato + tolleranza) è coerente con FEAT-001/011 e con
Principio V/VI. Per-superficie = estensione dello schema baseline, non un secondo meccanismo.

---

## 5. DA-a — Quale leva per prima (valutazione, NON prescrizione)

La feature **VALUTA** le leve; non ne adotta nessuna a priori (decisione di prodotto: leve opt-in, scelte
per misura). Ordine **raccomandato** di valutazione, per costo atteso crescente vs lift atteso:

| Ordine | Leva | Costo atteso | Lift atteso | Note |
|---|---|---|---|---|
| 1 | **Filtro metadata esteso** | basso (deterministico, zero LLM extra) | medio su `code` (NL→simbolo) | candidato economico/deterministico → prima. FEAT-006 sarà il «come». |
| 2 | **Contextual retrieval** (arricchimento chunk) | medio (re-index, no LLM nel run) | medio su `doc` | tocca l'indicizzazione, non il run. FEAT-007. |
| 3 | **Query transformation / HyDE** | alto (LLM al query-time → ATTENZIONE confine D↔N) | alto su NL ampie | FEAT-005. **Vincolo duro:** se introduce un LLM nel *run di misura*, viola RNF-3 → la leva va valutata **fuori** dal run deterministico (es. pre-espansione offline materializzata), o resta documentazione del pattern agentico (DA-e). |

- **Raccomandazione (non prescrizione).** Valutare **prima il filtro metadata** (economico,
  deterministico, non rischia RNF-3), poi contextual retrieval, infine query transformation con cautela
  sul confine LLM. La **scelta finale è guidata dai numeri** della baseline (REQ-031): se la baseline
  mostra che la debolezza è su `doc`, si privilegia contextual retrieval, ecc.
- **Confine D↔N critico.** Una leva che richiederebbe un LLM **nel run** è incompatibile con il run
  deterministico (RNF-3, SC-004). Tali leve si valutano solo se materializzabili offline o come
  documentazione del pattern agentico (DA-e). Questo è un **finding di design**, non un blocco di scope:
  il Must (misura) non dipende da alcuna leva.

---

## 6. DA-d — Rapporto con FEAT-004/005/006/007 (confine)

- **FEAT-004 (soglie `SERTOR_MIN_SCORE`/astensione):** **ortogonale**. Governa l'astensione, non la
  pertinenza NL. Coordinamento: il run di misura **non** attiva `min_score` di default (misura la
  pertinenza grezza); se una baseline è registrata con una certa soglia, va documentata nel set. Confine:
  qui NON si calibrano le soglie.
- **FEAT-005 (query transformation/HyDE), FEAT-006 (filtro metadata esteso), FEAT-007 (contextual
  retrieval):** sono le **leve candidate**. Se una entra qui come opt-in con lift misurato, la sua
  **feature dedicata diventa il «come»/estensione** (implementa la leva a regime, con manopole proprie,
  distribuzione, ecc.). Qui si introduce **al più** il *seam* per attivarla come opt-in nel run, **non**
  la sua implementazione completa. Già promosse nel backlog d'epica (Out-of-Scope → casa durevole, OK).

---

## 7. DA-e — Valore single-shot vs pattern agentico

**Raccomandazione (decisione di prodotto già fissa, qui motivata).** Il target è il **miglioramento
single-shot misurabile**: la **misura serve in ogni caso** (è il valore base, Must). Se i dati mostrassero
che l'agente già compensa (itera via MCP, R-4), **lo si documenta** (la fusion coverage misura comunque
quanto male/bene va il single-shot, che è ciò che l'agente paga in iterazioni). **Non blocca lo scope:**
il Must (infrastruttura di misura) è indipendente da questa domanda; le leve (Should) si adottano solo se
mostrano lift single-shot misurato.

---

## 8. Separazione MECCANICO ↔ GIUDIZIO (vincolante, riflessa nel plan)

| Aspetto | Natura | Dove |
|---|---|---|
| Schema `[[case]]` + campo `intent` | **meccanico** | `models.py`/`suite_io.py` (codice deterministico) |
| Metrica fusion coverage | **meccanico** | `services/eval/fusion.py` (funzione pura) |
| Baseline per-superficie + gate | **meccanico** | `models.py`/`baseline_io`/`regression` (riuso) |
| Run di misura via vehicle | **meccanico** | `composition.py` + `cli` |
| Quali query NL, quale intento, quale «needs both», quale «pertinente» | **GIUDIZIO** | skill `eval-suite-author` (estesa) + utente |
| Quale leva valutare/adottare | **GIUDIZIO** | misura (US3/US4) + decisione utente |

Il **MUST è tutto meccanico** (misura). Le superfici di **giudizio** (genesi set + scelta leva) sono
Should, separate dal run.

---

## 9. Esito Phase 0
- **DA-a** risolta: ordine di **valutazione** raccomandato (metadata→contextual→query-transform), guidato
  dai numeri; nessuna adozione prescritta; finding sul confine LLM/RNF-3.
- **DA-b** risolta: campo additivo `intent ∈ {code,doc,both}` su `[[case]]`; tipi letti da `doc_type` a
  runtime (no doppia etichettatura); ≥8/superficie, ≥6 fusione; genesi via `eval-suite-author` (P2).
- **DA-c** risolta: baseline per-superficie + tolleranza `0.0` (riuso meccanismo); delta-lift +0.05 come
  criterio di adozione (non gate); target assoluto fusion coverage = Could (dopo la baseline).
- **DA-d** risolta: FEAT-004 ortogonale (no `min_score` di default nel run); FEAT-005/006/007 = leve
  candidate, le loro feature diventano il «come».
- **DA-e** risolta: target single-shot misurabile; pattern agentico documentato se i dati lo indicano;
  non blocca lo scope.
- **Cardine architetturale:** estensione **additiva** dell'harness IR (NON un secondo oracolo come
  FEAT-011): `evaluate`/`EvalReport` invariati; superfici = wrapper `QueryableEngine` sul facade; fusion
  coverage = secondo passaggio puro sui casi `both`. Nessuna nuova porta, nessuna nuova dipendenza.
