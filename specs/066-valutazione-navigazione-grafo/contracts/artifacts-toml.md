# Contract — Artefatti TOML: `[[graph_case]]` + `eval/graph_baseline.toml` (FEAT-011)

Estende il contratto degli artefatti del 065. Dati **versionati del progetto** (REQ-001/002/RNF-5): mai
segreti, mai output rigenerabile. Vivono in `eval/` a root dell'ospite (`SERTOR_EVAL_DIR`). Letti con
`tomllib` (stdlib); scritti col **serializzatore minimale a mano** esistente (research DA-a), round-trip
validato dopo ogni scrittura (`SuiteWriteError` fail-safe).

---

## `eval/suite.toml` — array `[[graph_case]]` (REQ-002/003, decisione A/DA-d)

Lo **stesso** file della suite IR ospita due array di tabelle: `[[case]]` (IR, **invariato**) e
`[[graph_case]]` (navigazione, nuovo). Il writer **preserva entrambe** le sezioni a ogni scrittura
(Principio VI).

### Schema `[[graph_case]]`
| Chiave | Tipo | Obbligo | Vincolo |
|---|---|---|---|
| `relation` | string | sì | ∈ {`"who_calls"`, `"defines"`} (MVP); fuori insieme → suite rifiutata (REQ-005) |
| `target` | string | sì | non vuoto (nome del simbolo target) |
| `expected` | array di string | sì (può essere **vuoto**) | ogni elemento è un `ref` = `path#qualname` (REQ-003); `[]` = «nessun riferimento atteso» (legittimo) |

### Esempio (convivenza con i `[[case]]` IR)
```toml
# Sertor eval suite. Versioned project data — no secrets.
# [[case]]      = retrieval (IR) — query → expected paths (hit@k/MRR)
# [[graph_case]] = graph navigation — relation + target → expected set of refs (precision/recall/F1)

[[case]]
query = "EmbeddingProvider"
expected = ["src/sertor_core/domain/ports.py"]
kind = "symbol"

[[graph_case]]
relation = "defines"
target = "build_facade"
expected = ["src/sertor_core/composition.py#build_facade"]

[[graph_case]]
relation = "who_calls"
target = "build_graph_service"
expected = [
  "src/sertor_core/composition.py#_GraphEvalRunner.run",
  "src/sertor_core/cli/__main__.py#_cmd_graph_eval_run",
]

[[graph_case]]
relation = "who_calls"
target = "a_symbol_with_no_callers"
expected = []
```

### Validazione (REQ-004/005 — Principio IV)
- `[[graph_case]]` senza `relation`/`target`/`expected`, o tipi errati → **`GraphSuiteValidationError`** che
  **identifica il caso** (indice + contenuto parziale), nessun punteggio fasullo.
- `relation` fuori dall'insieme MVP → **suite rifiutata** con messaggio azionabile (REQ-005).
- `expected` **vuoto** è valido per un graph-case (a differenza degli IR-case): atteso «nessun chiamante».
- file assente o **nessun** `[[graph_case]]` → al run non è un crash: messaggio azionabile («crea casi con
  `graph-eval add-case`») + report vuoto onesto (no gate fasullo).

### Regole del writer (idempotenza/non-distruttività — REQ-041, Principio VI)
- **Preserva entrambe le sezioni**: scrivere un `[[graph_case]]` non cancella i `[[case]]` IR e viceversa.
- dedup di un graph-case per `(relation, target)`; ordine stabile; append in coda alla sezione graph.
- escape stringhe basic (`"`→`\"`, `\`→`\\`).
- dopo la scrittura, **ri-legge con `tomllib`** (round-trip): fallimento → `SuiteWriteError` (mai TOML
  ambiguo persistito).

---

## `eval/graph_baseline.toml` — pavimento metrico di navigazione (REQ-031, separato dalla IR)

File **distinto** da `eval/baseline.toml` (DA-a/REQ-031): schemi diversi (la IR ha `[hit_rate]` per-k, il
grafo ha medie set-based).

### Schema
| Chiave | Tipo | Uso |
|---|---|---|
| `recorded_at` | string (ISO-8601 UTC) | informativo |
| `cases` | integer | n. graph-case della misura |
| `mean_f1` | float | metrica di **gate** (DA-a) |
| `mean_recall` | float | secondaria (diagnosi) |
| `mean_precision` | float | secondaria (diagnosi) |

### Esempio
```toml
recorded_at = "2026-06-20T12:00:00Z"
cases = 6
mean_f1 = 0.83
mean_recall = 0.90
mean_precision = 0.79
```

### Regole (REQ-031/044-gemello)
- scritto/aggiornato **solo** su `graph-eval run --record-baseline` (accettazione esplicita); mai automatico.
- **non** contiene mai gli `expected` dei casi: la baseline è il **pavimento metrico**, lo **snapshot**
  (insiemi) vive nei `[[graph_case]]` (DA-c).
- assente → `load_graph_baseline` ritorna `None`; il run lo segnala (`verdict=no-baseline`, exit 0, REQ-033)
  e **offre** di registrarlo.
- confronto: `mean_f1 < mean_f1_baseline - tolerance` → `regressed` (gate, exit 1, REQ-032);
  `mean_recall`/`mean_precision` confrontati come **delta informativi** (mai gate).

---

## Invarianti
- entrambi gli artefatti sono **versionati e diffabili a mano** (TOML leggibile, Principio X).
- nessun segreto (RNF-5); ogni `ref` è `path#qualname` relativo alla root indicizzata, non un path assoluto.
- lettura stdlib (`tomllib`), scrittura senza dipendenze pesanti (Principio II/III).
- la suite IR (`[[case]]`) e la baseline IR (`eval/baseline.toml`) restano **invariate** (RNF-4).
