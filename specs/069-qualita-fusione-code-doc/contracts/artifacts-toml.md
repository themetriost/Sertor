# Contract — Artefatti TOML: `intent` su `[[case]]` + `FusedBaseline` (FEAT-003)

Estensione **additiva** dello schema versionato dell'harness (065/066). Tutto è dato del progetto
ospite (`eval/`, versionato; mai segreti, mai output rigenerabile). Letto con `tomllib` (stdlib),
**scritto** col serializzatore a mano esistente (`_serialize_suite`/baseline writer), con
**round-trip validato** (fail-safe → `SuiteWriteError`).

---

## 1. `eval/suite.toml` — campo `intent` su `[[case]]`

```toml
# [[case]]       = retrieval (IR) — query → expected paths (hit@k/MRR).
# intent (069)   = "code" | "doc" | "both" → superficie misurata + tipi attesi (fusion coverage).
# kind/intent sono indipendenti. Paths POSIX, relativi alla root indicizzata.

[[case]]
query = "EmbeddingProvider"
expected = ["src/sertor_core/domain/ports.py"]
kind = "symbol"
# (nessun intent → caso IR puro, non contribuisce alle metriche per-superficie/fusione)

[[case]]
query = "where the hybrid engine fuses BM25 and dense results"
expected = ["src/sertor_core/engines/hybrid.py"]
kind = "nl"
intent = "code"

[[case]]
query = "why combined search merges results by score across collections"
expected = ["src/sertor_core/services/retrieval.py"]
kind = "nl"
intent = "doc"

[[case]]
query = "requirements of the fused code+doc quality feature and where measured"
expected = [
  "requirements/retrieval-qualita/qualita-search-code-nl/requirements.md",
  "src/sertor_core/services/eval/fusion.py",
]
kind = "nl"
intent = "both"
```

**Regole.**
- `intent` opzionale; se presente ∈ `{code, doc, both}` (altrimenti `SuiteValidationError` nomina il
  caso, REQ-004). Default assente → retrocompatibile coi casi 065/066 esistenti.
- I `[[graph_case]]` (066) e i casi senza `intent` sono **preservati** da ogni scrittura (DA-d).
- L'`expected` resta una **tupla di path**: il **tipo** (CODE/DOC) NON si scrive nel set, si legge da
  `RetrievalResult.doc_type` a runtime (research §2/§3). Per i casi `both`, `expected` dovrebbe contenere
  **sia** path doc **sia** path code (è ciò che rende «coperto» possibile), ma non è imposto a write-time
  (è giudizio dell'autore; la skill propone, l'utente cura).
- Ordine dei casi stabile; dedup per `query` (idempotenza, REQ-002).

---

## 2. `eval/baseline.toml` — sezione `FusedBaseline` (additiva)

Il file ospita **due** baseline distinte, in sezioni separate; il writer le preserva entrambe
(preserve-both, come `suite.toml` per `[[graph_case]]`):

```toml
# Baseline IR (065) — hit@k/MRR globale, per `eval run`.
[baseline]
mrr = 0.83
queries = 11
provider = "ollama:nomic"
recorded_at = "2026-06-21T10:00:00Z"
[baseline.hit_rate]
1 = 0.55
3 = 0.82
5 = 0.91
10 = 1.0

# Baseline di fusione (069) — per-superficie + fusion coverage, per `eval run --fused`.
[fused_baseline]
fusion_coverage = 0.50
queries = 22
provider = "ollama:nomic"
recorded_at = "2026-06-21T10:05:00Z"

[[fused_baseline.surface]]
surface = "search_code"
mrr = 0.64
[fused_baseline.surface.hit_rate]
1 = 0.50
3 = 0.75
5 = 0.88

[[fused_baseline.surface]]
surface = "search_docs"
mrr = 0.73
[fused_baseline.surface.hit_rate]
1 = 0.62
3 = 0.88
5 = 0.88

[[fused_baseline.surface]]
surface = "search_combined"
mrr = 0.69
[fused_baseline.surface.hit_rate]
1 = 0.55
3 = 0.82
5 = 0.91
```

**Regole.**
- `[fused_baseline]` scritto **solo** su `eval run --fused --record-baseline` (accettazione esplicita,
  REQ-010/040). Senza il flag non si tocca.
- Registrare la baseline di fusione **non** tocca `[baseline]` IR né i `[[case]]`/`[[graph_case]]` della
  suite (non-distruttività, Principio VI).
- `[fused_baseline]` assente → il gate di fusione passa con verdetto `no-baseline` (exit 0): non si
  fallisce per assenza di confronto (gemello del comportamento IR).
- Round-trip validato; un risultato non parsabile → `SuiteWriteError`/`BaselineWriteError`, nessun file
  ambiguo lasciato (fail-safe).

---

## 3. Invarianti
- **Additività:** suite/baseline esistenti restano valide e parsabili; il nuovo campo/sezione hanno
  default che riproducono il comportamento odierno (RNF-1/RNF-5).
- **Versionati, non segreti, non output** → in `eval/` (versionato), MAI in `.sertor/` (gitignored).
- **Determinismo del round-trip** (Principio VI): scrivere → rileggere produce le stesse entità.
- **Host-agnostico (Principio X):** `eval/` è dato dell'ospite (override config); i path sono relativi
  alla root indicizzata.
