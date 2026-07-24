# Data Model — Contratto di retrieval verso l'agente

**Feature**: `118-contratto-retrieval-agente` · **Data**: 2026-07-24

Entità **pure**, senza SDK esterni (Principio I). Dataclass `frozen`, campi a **tuple** anziché liste,
coerentemente con `domain/entities.py`.

---

## Entità nuove — `domain/agent_context.py`

### `EntrySource` (Literal)

```
"extracted_from_query" | "symbol_table_match"
```

L'origine di un punto d'ingresso — **solo le due vie effettivamente prodotte**.

**Due valori esclusi, per la stessa ragione:**
- `expanded_from_code` — la via per espansione semantica è rinviata (R15);
- `caller_supplied` — richiederebbe un parametro sul tool per dichiarare i simboli, che questa
  feature non espone.

Includerli nel tipo senza produrli mai sarebbe un'astrazione senza evidenza (Principio III).
*(Rilievo F1 dell'analisi incrociata: il primo era già escluso, il secondo era rimasto per svista —
lo stesso argomento vale per entrambi.)*

### `RelationStatus` (Literal)

```
"ok" | "empty" | "unavailable"
```

Distingue *«ho guardato e non c'è»* (`empty`, conclusione legittima) da *«non ho potuto guardare»*
(`unavailable`, che invalida ogni conclusione di assenza).

### `EntryPoint`

| Campo | Tipo | Note |
|---|---|---|
| `symbol` | `str` | il nome qualificato interrogato |
| `source` | `EntrySource` | **come** è stato ricavato — è ciò che permette all'agente di scontare gli ingressi deboli |

### `RelationBlock`

| Campo | Tipo | Default | Note |
|---|---|---|---|
| `items` | `tuple[SymbolHit, ...]` | `()` | riusa l'entità esistente |
| `status` | `RelationStatus` | `"ok"` | |
| `reason` | `str \| None` | `None` | valorizzato **solo** se `status == "unavailable"` |
| `shown` | `int` | `0` | quanti elementi sono presenti |
| `total` | `int` | `0` | quanti ne esistono a monte del taglio |

**Invarianti:**
- `status == "empty"` ⟺ `items` vuoto **e** `reason is None`
- `status == "unavailable"` ⟹ `reason` non nullo (un'indisponibilità senza causa è il silenzio che
  FR-027 vieta)
- `shown == len(items)`
- `shown <= total`
- `truncated` (property) ⟺ `shown < total`

### `SymbolContext`

| Campo | Tipo | Note |
|---|---|---|
| `qualname` | `str` | il simbolo risolto |
| `definitions` | `RelationBlock` | dove è definito |
| `callers` | `RelationBlock` | chi lo chiama |
| `callees` | `RelationBlock` | cosa chiama |
| `docs` | `RelationBlock` | quali documenti lo menzionano |

I quattro blocchi hanno stati **indipendenti**: il caso misto (chiamanti calcolati, documenti no) è la
norma, non l'eccezione (spec, Edge Cases).

### `GraphBranch`

| Campo | Tipo | Default | Note |
|---|---|---|---|
| `entry_points` | `tuple[EntryPoint, ...]` | `()` | |
| `symbols` | `tuple[SymbolContext, ...]` | `()` | |
| `unavailable_reason` | `str \| None` | `None` | indisponibilità **globale** (il grafo stesso) |

**`status` è una property calcolata, non un campo** (R5, FR-028):

```
unavailable_reason valorizzato        → "unavailable"
entry_points vuoto                    → "not_attempted"
qualche RelationBlock non è "ok"      → "partial"
altrimenti                            → "ok"
```

**Invariante garantita per costruzione:** `status == "not_attempted"` ⟺ `entry_points` vuoto
(FR-029). Non essendoci un campo impostabile, non può divergere dai sotto-stati.

### `AgentContext`

| Campo | Tipo | Note |
|---|---|---|
| `docs` | `tuple[RetrievalResult, ...]` | flusso di somiglianza, documentazione |
| `code` | `tuple[RetrievalResult, ...]` | flusso di somiglianza, codice |
| `graph` | `GraphBranch` | flusso strutturale |

*Nota al confine:* `search_combined` della facade restituisce **liste**; la conversione a tuple avviene
costruendo `AgentContext`. È deliberato — l'immutabilità è una proprietà delle entità di dominio, non
un vincolo che si impone alla facade esistente.

---

## Entità estese

### `ContextBundle` (esistente) — campo additivo

| Campo | Tipo | Default | Note |
|---|---|---|---|
| `totals` | `tuple[tuple[str, int], ...]` | `()` | coppie `(nome_sezione, totale_pre-taglio)` |

Il default vuoto mantiene il contratto **retrocompatibile** per i consumatori esistenti (Principio VI).
Popolato dall'adapter **prima** di applicare i limiti configurati: dopo il taglio l'informazione non è
più recuperabile (R7).

### `RetrievalResult` (esistente) — corroborazione

La marcatura della corroborazione **non modifica l'entità di dominio**: viaggia nel campo `metadata`
già presente, sotto la chiave `corroborated_by`, come tupla di `qualname`.

*Motivazione:* aggiungere un campo tipizzato a `RetrievalResult` toccherebbe ogni produttore
(due adapter di store, il motore ibrido, il reranker, la memoria episodica) per un dato che riguarda
**solo** questa composizione. Il campo `metadata` esiste per questo, ed evita una modifica invasiva a
un'entità centrale.

### `CodeGraph` (porta) — metodo additivo

```
list_symbols() -> list[str]
```

Restituisce i nomi qualificati noti al grafo. Additivo: essendo un `Protocol` con structural typing, i
mock esistenti continuano a soddisfare la porta per i metodi che già implementano; vanno estesi solo
quelli usati dai test della nuova via d'ingresso.

---

## Diagramma delle relazioni

```
AgentContext
├── docs  : RetrievalResult[]        ← flusso di somiglianza (esistente)
├── code  : RetrievalResult[]        ← flusso di somiglianza (esistente)
└── graph : GraphBranch
           ├── entry_points : EntryPoint[]   (symbol + source)
           ├── symbols      : SymbolContext[]
           │                  ├── definitions : RelationBlock ─┐
           │                  ├── callers     : RelationBlock  │→ items: SymbolHit[]
           │                  ├── callees     : RelationBlock  │  status · reason
           │                  └── docs        : RelationBlock ─┘  shown · total
           └── status       : property derivata dai blocchi
```

---

## Transizioni di stato del ramo strutturale

Non c'è stato persistente: il ramo è ricalcolato a ogni ricerca. La «transizione» è la **catena di
decisioni** che porta a uno dei quattro esiti.

```
query
  │
  ├─ nessun punto d'ingresso ricavabile ────────────→ not_attempted   (costo ≈ 0)
  │
  └─ almeno un punto d'ingresso
       │
       ├─ grafo non consultabile ──────────────────→ unavailable
       │     ├─ artefatto assente        → graph_not_built
       │     ├─ libreria di navigazione  → navigation_library_missing
       │     └─ artefatto illeggibile    → graph_artifact_unusable
       │
       └─ grafo consultabile
            ├─ tutti i blocchi ok ───────────────→ ok
            └─ almeno un blocco empty/unavailable → partial
```

**Il ramo `not_attempted` non tocca il grafo**: è ciò che rende il costo auto-correlato alla rilevanza
(spec §4 dei requisiti). Una domanda concettuale che non nomina né implica alcun simbolo non paga nulla.

---

## Entità dell'harness (fuori dal prodotto)

Non sono entità di dominio: vivono in `eval_ab/` e non entrano in `sertor_core`.

### `MeasurementCase`

| Campo | Note |
|---|---|
| `query` | la domanda |
| `expected_paths` | le fonti attese (dalla suite di valutazione esistente) |
| `kind` | strutturale / non strutturale — partiziona beneficio e non-regressione |

### `ArmOutcome`

| Campo | Note |
|---|---|
| `case_id`, `arm`, `repetition` | identificano l'esecuzione |
| `cites_expected` | **almeno una** fonte attesa citata (unione, non congiunzione — FR-003a) |
| `invented_path` | ha citato un path assente dal materiale fornito |
| `payload_bytes` | dimensione del materiale (proxy dei token) |
| `latency_ms` | tempo della chiamata |

I due verdetti sono **deterministici**: le fonti attese sono note e i path citati si estraggono dal
testo della risposta. Nessun giudizio di modello è coinvolto.
