# Data model — 018 Hardening retrieval

Poche entità nuove e additive. **Nessuna modifica** a `RetrievalResult` o alle porte
(`EmbeddingProvider`, `VectorStore`, `RetrieverStrategy`): la compatibilità è garantita per costruzione.

## Nuove strutture

### `RetryPolicy` (in `adapters/embeddings/_retry.py`)
Politica di ritentativo per le chiamate di embedding.

| Campo | Tipo | Default | Note |
|---|---|---|---|
| `max_attempts` | `int` | (da Settings) | numero totale di tentativi; `1` = nessun ritentativo (FR-006) |
| `base_backoff_s` | `float` | (da Settings) | base dell'attesa esponenziale (secondi) |

Regole: `max_attempts >= 1` (un valore < 1 è normalizzato a 1). Immutabile (`frozen=True`).
Funzione companion `with_retry(fn, policy, *, sleep, rng)` (vedi contracts).

### `Settings` (campi aggiunti — `config/settings.py`)
Default SOLO qui (Principio VIII). Tutti con env override.

| Campo | Tipo | Default | Env | Requisito |
|---|---|---|---|---|
| `embed_retry_attempts` | `int` | `3` | `SERTOR_EMBED_RETRY_ATTEMPTS` | FR-002/006 |
| `embed_retry_base_s` | `float` | `0.5` | `SERTOR_EMBED_RETRY_BASE` | FR-002 |
| `retrieval_min_score` | `float \| None` | `None` | `SERTOR_MIN_SCORE` | FR-010/013 |

`retrieval_min_score=None` (env assente) ⇒ feature confidenza disattivata = comportamento odierno.

## Strutture modificate (firma costruttore, additive)

### `AzureEmbedder` / `OllamaEmbedder`
Aggiunti parametri opzionali, default = comportamento odierno:
`retry: RetryPolicy | None = None`, `sleep: Callable[[float], None] = time.sleep`,
`rng: Callable[[], float] = random.random`. `embed()` avvolge `_embed_batch` in `with_retry` quando
`retry` è presente con `max_attempts > 1`; altrimenti chiama direttamente (zero overhead, zero
cambiamento). Il `client` httpx resta iniettabile come oggi.

### `RetrievalFacade`
Aggiunto `min_score: float | None = None` al costruttore. Applicato SOLO sul percorso denso proprio
(`_search` senza retriever, `_search_multi`); sul percorso con `retriever` (ibrido iniettato) la soglia
è applicata dall'ibrido — niente doppio filtro.

### `BaselineEngine` / `HybridEngine`
Nessun nuovo parametro costruttore: leggono `self._settings.retrieval_min_score`. Baseline filtra
l'esito (score = similarità). Hybrid filtra il **ramo denso** prima della fusione RRF (research D4).

## Funzione pura condivisa (in `services/retrieval.py`)

```
apply_min_score(results: list[RetrievalResult], min_score: float | None)
    -> tuple[list[RetrievalResult], bool]
```
Ritorna `(results, False)` se `min_score is None`. Altrimenti `(kept, low_confidence)` dove
`kept = [r for r in results if r.score >= min_score]` e `low_confidence = bool(results) and not kept`
(c'erano candidati, nessuno supera la soglia). Pura, deterministica, testabile in isolamento (D5).

## Invarianti
- **Retro-compatibilità (FR-013/014):** con default (`retry=None`/`attempts=1`, `min_score=None`) ogni
  percorso è byte-identico a oggi → coperto da SC-004/SC-006 (suite esistente verde).
- **Tipo errore preservato (FR-003):** l'eccezione a tentativi esauriti resta `EmbeddingError`.
- **Policy errori invariata (FR-015):** la soglia non altera `IndexNotFoundError` (baseline) né il
  warning `no_index` (facade). Filtra solo risultati su indice esistente.
- **Nessun segreto nei log (Principio IX):** nuovi eventi passano da `redact()`.
