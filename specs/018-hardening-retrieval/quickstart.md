# Quickstart — 018 Hardening retrieval

Come si esercita la feature (scenari dello spec → comandi/test). Tutto **offline**.

## Resilienza embedding (US1)

Abilitata di default (3 tentativi). Per regolarla o disattivarla:

```bash
# nel .env (o env del runtime .sertor/.env)
SERTOR_EMBED_RETRY_ATTEMPTS=3     # 1 = disattiva i ritentativi
SERTOR_EMBED_RETRY_BASE=0.5       # base del backoff (s)
```

Verifica (test offline, nessuna attesa reale): un provider fittizio che fallisce con 429 e poi
risponde 200 deve completare; uno che fallisce sempre con 429 deve sollevare `EmbeddingError` dopo
`attempts` tentativi; un 401 (non ritentabile) deve fallire subito.

```python
# pseudo-test (tests/unit/test_embed_retry.py)
calls = {"n": 0}
def flaky_post(*a, **k):
    calls["n"] += 1
    if calls["n"] == 1:
        raise httpx.HTTPStatusError("429", request=..., response=Resp(429))
    return Resp(200, {"data": [{"index": 0, "embedding": [0.1, 0.2]}]})

emb = AzureEmbedder(..., client=FakeClient(flaky_post),
                    retry=RetryPolicy(max_attempts=3, base_backoff_s=0.5),
                    sleep=lambda s: waits.append(s), rng=lambda: 0.0)
assert emb.embed(["q"]) == [[0.1, 0.2]]      # SC-001: completa senza intervento
assert waits == [0.5]                          # backoff applicato, deterministico (no sleep reale)
```

## Segnale di confidenza / soglia (US2)

Disattivata di default. Per abilitarla:

```bash
SERTOR_MIN_SCORE=0.35    # soglia di similarità (coseno); assente = comportamento odierno
```

Verifica (store mock con score controllati):

```python
# query in-dominio (score alti) → risultati restituiti
facade = build_facade(Settings(... retrieval_min_score=0.35))   # via composition in pratica
assert facade.search_code("query nota") != []

# query fuori-dominio (tutti gli score < 0.35) → lista vuota + log low_confidence
assert facade.search_code("query irrilevante") == []           # SC-003: niente contesto spurio

# soglia assente → identico a oggi (nessun filtro)
facade0 = build_facade(Settings(... retrieval_min_score=None))
assert len(facade0.search_code("query irrilevante")) > 0       # SC-004: regressione
```

## Esecuzione test

```bash
uv run pytest tests/unit/test_embed_retry.py tests/unit/test_confidence_threshold.py -q
uv run pytest -m "not cloud"          # l'intera suite resta verde (SC-006)
uv run ruff check .
```

## Criteri di accettazione mappati
- SC-001/002 → `test_embed_retry.py` (429→200; esaurimento; backoff registrato; non-ritentabile).
- SC-003 → `test_confidence_threshold.py` (fuori-dominio = []; in-dominio = risultati; log emesso).
- SC-004/006 → soglia/retry ai default ⇒ nessun cambiamento; suite esistente invariata.
- SC-005 → tutti i test sopra sono offline, `sleep`/`rng`/`client`/store iniettati.
