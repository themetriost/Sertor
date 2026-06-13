# Library contract — 018 Hardening retrieval

Sertor-core è una **libreria**: il suo contratto pubblico sono le manopole `Settings`, le firme dei
componenti e gli eventi di log. Tutte le aggiunte qui sono **additive e forward-compatible**.

## 1. Configurazione (env / `Settings`)

| Env | Tipo | Default | Effetto |
|---|---|---|---|
| `SERTOR_EMBED_RETRY_ATTEMPTS` | int | `3` | tentativi totali per chiamata di embedding; `1` disattiva il retry |
| `SERTOR_EMBED_RETRY_BASE` | float | `0.5` | base (s) del backoff esponenziale |
| `SERTOR_MIN_SCORE` | float | *(assente)* | soglia di similarità per il segnale di confidenza; assente = disattivata |

Contratto: con i default, il comportamento osservabile è **identico** alla versione precedente.

## 2. Retry helper — `with_retry`

```
with_retry(fn: Callable[[], T], policy: RetryPolicy, *,
           sleep: Callable[[float], None], rng: Callable[[], float]) -> T
```
- Esegue `fn()`. Su `EmbeddingError` con `retriable=True` e tentativi residui: attende
  `policy.base_backoff_s * 2**i * (0.5 + rng())` secondi (via `sleep`), poi riprova.
- Su `EmbeddingError` con `retriable=False`: ri-solleva **immediatamente** (nessun tentativo extra).
- Esauriti i tentativi: ri-solleva l'**ultimo** `EmbeddingError` (tipo preservato).
- Emette `log_event(... "embeddings_retry", provider, attempt, reason, wait_ms)` a ogni ritentativo.
- `policy.max_attempts <= 1` ⇒ esegue `fn()` una sola volta (nessun retry, nessun overhead).

**Determinismo in test:** `sleep` e `rng` sono iniettati → nessuna attesa reale, jitter riproducibile.

## 3. Embedding providers (porta `EmbeddingProvider` invariata)

La porta `embed(texts) -> list[list[float]]` **non cambia**. Gli adapter accettano in più
`retry: RetryPolicy | None`, `sleep`, `rng` (default reali). Comportamento:
- `retry=None` o `max_attempts<=1` → come oggi (un tentativo per batch).
- altrimenti → ogni `_embed_batch` è ritentato secondo la policy; a esaurimento, `EmbeddingError`.

## 4. Retrieval — soglia & segnale di confidenza

Le firme **non cambiano**: `search_code/search_docs/search_combined`, `BaselineEngine.query`,
`HybridEngine.query/retrieve` restano `-> list[RetrievalResult]`.

Comportamento con `min_score` impostata:
- **Facade percorso denso / multi** e **Baseline**: esclude i risultati con `score < min_score`.
- **Hybrid**: filtra il **pool denso** (similarità) prima della fusione RRF; lo score finale resta RRF.
- Quando il filtro svuota l'esito (c'erano candidati, nessuno ≥ soglia): ritorna `[]` ed emette
  `log_event(... "low_confidence", collection, provider, min_score, best_score, candidates)`.
- `min_score=None`: nessun filtro, nessun evento (contratto invariato).

Garanzia consumer (FR-014): chi ignora il segnale riceve comunque una lista (eventualmente vuota) e
continua a funzionare senza modifiche.

## 5. Policy errori (invariata, FR-015)
- Baseline resta **strict**: indice assente → `IndexNotFoundError` (la soglia NON lo altera).
- Facade resta **tollerante**: indice assente → `[]` + warning `no_index`.
- La soglia è un filtro su un indice **esistente**: una lista vuota da soglia è un **segnale
  intenzionale e loggato**, non un null silenzioso (Principio IV rispettato).

## 6. Eventi di log nuovi (Principio IX)
| operation | quando | campi (redatti) |
|---|---|---|
| `embeddings_retry` | a ogni ritentativo | `provider`, `attempt`, `reason`, `wait_ms` |
| `low_confidence` | esito svuotato dalla soglia | `collection`, `provider`, `min_score`, `best_score`, `candidates` |
