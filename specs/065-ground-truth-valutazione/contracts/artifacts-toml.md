# Contract — Artefatti TOML: `eval/suite.toml` e `eval/baseline.toml` (FEAT-001)

Dati **versionati del progetto** (REQ-006/041/RNF-6): mai segreti, mai output rigenerabile. Vivono in
`eval/` a root del progetto ospite (override `SERTOR_EVAL_DIR`). Letti con `tomllib` (stdlib); scritti
con un serializzatore minimale a mano (research DA-a), round-trip validato dopo ogni scrittura.

---

## `eval/suite.toml` — la suite di valutazione (REQ-001/002/003)

### Schema
Array di tabelle `[[case]]`. Per ogni caso:

| Chiave | Tipo | Obbligo | Vincolo |
|---|---|---|---|
| `query` | string | sì | non vuota |
| `expected` | array di string | sì | ≥1 path; POSIX; relativi alla root indicizzata |
| `kind` | string | no | libero (es. `"symbol"`, `"nl"`); preservato e mostrato nel report (REQ-003) |

### Esempio (migrazione del fixture dogfood `tests/fixtures/ground_truth.py`)
```toml
# Sertor eval suite (dogfood example). Versioned project data — no secrets.
# kind ∈ {"symbol","nl"} (optional). Paths are repo-root-relative POSIX.

[[case]]
query = "EmbeddingProvider"
expected = ["src/sertor_core/domain/ports.py"]
kind = "symbol"

[[case]]
query = "IndexNotFoundError"
expected = ["src/sertor_core/domain/errors.py", "src/sertor_core/engines/baseline.py"]
kind = "symbol"

[[case]]
query = "where concrete adapters are chosen and the configuration is wired"
expected = ["src/sertor_core/composition.py"]
kind = "nl"

[[case]]
query = "redaction of secrets in structured logs"
expected = ["src/sertor_core/observability/logging.py"]
kind = "nl"
```

### Validazione (REQ-004 — Principio IV)
- voce senza `query`/`expected`, o tipi errati, o `expected` vuoto → **`SuiteValidationError`** che
  **identifica il caso** offendente (indice + contenuto parziale), nessun punteggio fasullo.
- file assente o `cases` vuoto → al run è `SuiteNotFoundError` (REQ-032), non zero ingannevole.

### Regole del writer (idempotenza/non-distruttività — REQ-011, Principio VI)
- preserva i casi esistenti e il loro ordine; append in coda.
- escape stringhe basic (`"`→`\"`, `\`→`\\`); query multilinea → basic multiline `"""…"""`.
- dopo la scrittura, **ri-legge con `tomllib`** (round-trip): fallimento → `SuiteWriteError` (mai TOML
  ambiguo persistito).

---

## `eval/baseline.toml` — il riferimento di non-regressione (REQ-041)

### Schema
| Chiave | Tipo | Uso |
|---|---|---|
| `recorded_at` | string (ISO-8601 UTC) | informativo |
| `provider` | string | provenienza della misura |
| `queries` | integer | n. casi della misura |
| `mrr` | float | metrica di gate |
| `[hit_rate]` (tabella `k = float`) | table | hit-rate@k per ogni k registrato |

### Esempio
```toml
recorded_at = "2026-06-20T11:30:00Z"
provider = "ollama:nomic-embed-text"
queries = 11
mrr = 0.83

[hit_rate]
1 = 0.55
3 = 0.82
5 = 0.91
10 = 1.0
```

### Regole (REQ-040/044)
- scritto/aggiornato **solo** su `--record-baseline` (accettazione esplicita); mai automatico.
- assente → `load_baseline` ritorna `None`; il run lo segnala (`verdict=no-baseline`, exit 0) e **offre**
  di registrarlo.
- confronto: per ogni metrica `current < baseline - tolerance` → `regressed` (gate, exit 1, REQ-043).

---

## Invarianti
- entrambi i file sono **versionati e diffabili a mano** (TOML leggibile, Principio X — l'ospite li cura).
- nessun segreto (RNF-6); nessun path assoluto host-specifico (path relativi alla root indicizzata,
  rebasabili via `relative_to`/REQ-005).
- lettura stdlib (`tomllib`), scrittura senza dipendenze pesanti (Principio II/III).
