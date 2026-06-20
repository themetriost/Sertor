# Contract — CLI `sertor-rag eval` (FEAT-001)

Superficie deterministica (vehicle, Principio XI). Thin consumer: parsing → composition factory →
`evaluate` (core) → `output.py`. Nessuna logica di retrieval nel CLI (Principio I). Stile e exit code
ereditati da `cli/__main__.py` (`index`/`search`/`memory`).

## Exit codes
| Code | Significato |
|---|---|
| `0` | successo (run pass / nessuna regressione / no-baseline) |
| `1` | `SertorError` su stderr: `SuiteNotFoundError`, `SuiteValidationError`, `SuiteWriteError`, `RegressionDetected`, `IndexNotFoundError` |
| `2` | usage error (argparse) |

---

## `sertor-rag eval run`

```
sertor-rag eval run [--compare LABELS] [--record-baseline] [-k K[,K…]]
                    [--corpus C] [--json] [-v] [--log-json] [--log-config F]
```

| Flag | Effetto |
|---|---|
| `--compare LABELS` | valuta ≥2 config locali sulla **stessa** suite (es. `--compare baseline,hybrid`); report affiancato (REQ-034). Senza il flag: la config corrente (`SERTOR_ENGINE`). |
| `--record-baseline` | registra/aggiorna `eval/baseline.toml` con le metriche correnti (REQ-040/044). Senza il flag la baseline non si tocca. |
| `-k` | lista dei k per hit-rate@k (default `1,3,5,10`). |
| `--json` | report come oggetto JSON (equivalenza informativa col testo, SC-002). |

### Comportamento
1. `_resolve_settings` + `_check_backend` + `enable_observability` (pattern esistente).
2. Carica `eval/suite.toml` via `build`-side `load_suite`. **Assente/vuota → `SuiteNotFoundError`**
   (exit 1, messaggio azionabile «crea la suite con `eval add-case`») — mai uno zero ingannevole
   (REQ-032/SC-010).
3. Costruisce l'engine via `build_engine`/`build_baseline_engine` (Principio XI), assicura l'indice
   (`ensure_index` → `IndexNotFoundError` se assente, exit 1).
4. Chiama `evaluate(engine, suite.to_ground_truth(), ks)`; riassocia `kind` per il report.
5. Se baseline presente (e non `--record-baseline`): `compare_to_baseline(…, tolerance)`.
   **`regressed` → `RegressionDetected` → exit 1** (gate, REQ-043). Entro tolleranza → exit 0.
6. Se `--record-baseline`: scrive `eval/baseline.toml` (accettazione esplicita, REQ-044), exit 0.
7. Determinismo: due run a parità di indice+suite → metriche identiche (REQ-035/SC-001).

### Output umano (esempio)
```
provider=ollama:nomic-embed-text  queries=11
hit@1=0.55  hit@3=0.82  hit@5=0.91  hit@10=1.00  mrr=0.83
[hit ] symbol  rank=1   EmbeddingProvider → src/sertor_core/domain/ports.py
[miss] nl      rank=-   fusion of multi-collection results … (top: services/retrieval.py)
…
non-regression: PASS (tolerance=0.00)  mrr Δ=+0.01  hit@5 Δ=0.00
```

### Output `--compare` (affiancato)
```
metric     baseline   hybrid
hit@5      0.82       0.91
mrr        0.74       0.83
```

---

## `sertor-rag eval add-case`

```
sertor-rag eval add-case --query Q --expected P[,P…] [--kind K]
                         [--confirm] [--corpus C] [--json]
```

- Persiste un caso in `eval/suite.toml` (writer TOML, non-distruttivo/idempotente, REQ-010/011).
- **Validazione write-time (REQ-012)**: ogni `expected` è verificato contro l'elenco dei documenti
  indicizzati (`build_indexed_docs`). Path assente → **warning** «path non presente nell'indice» e
  **richiede `--confirm`** (o conferma interattiva su TTY) prima di scrivere. Senza conferma: non scrive,
  exit 1 azionabile.
- Indice non disponibile (manifest assente) → warning «non posso verificare»; persiste solo con
  `--confirm` (degrado onesto, Principio IV).

---

## `sertor-rag eval validate-path`

```
sertor-rag eval validate-path P[…] [--corpus C] [--json]
```

- Primitiva **deterministica** per la skill di genesi assistita (FEAT-008) e per il feedback (FEAT-009):
  la skill — consumatore esterno — la invoca **via CLI** (Principio XI), non importa `sertor_core`.
- Ritorna `PathValidation` (`checked`/`missing`/`index_available`), umano + JSON. Exit 0 sempre (è una
  verifica, non un gate); `missing` non vuoto è informazione, non errore.

---

## Invarianti del contratto
- **Principio XI**: ogni accesso al retrieval/manifest passa dalle factory `build_*` (il CLI è il
  vehicle); la skill esterna passa dai sottocomandi, mai dalla libreria.
- **Equivalenza informativa** umano↔JSON (SC-002, invariante CLI esistente).
- **Additività** (SC-009): a comando non invocato, index/search e costo identici a oggi.
