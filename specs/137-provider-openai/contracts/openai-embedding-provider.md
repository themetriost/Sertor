# Contratto — provider di embedding `openai`

## Richiesta al servizio

```
POST {OPENAI_BASE_URL senza barra finale}/embeddings
Authorization: Bearer {OPENAI_API_KEY}
Content-Type: application/json

{"model": "{OPENAI_EMBED_MODEL}", "input": ["testo 1", "testo 2", ...]}
```

- Nessun parametro di query.
- Al più `EMBED_BATCH_SIZE` testi per richiesta; i lotti vanno in sequenza.

## Risposta attesa

```
{"data": [{"index": 0, "embedding": [...]}, ...], "usage": {"total_tokens": N}}
```

- I vettori si riordinano per `index` e si restituiscono nell'ordine d'ingresso.
- `usage.total_tokens` assente ⇒ il campo `tokens` dell'evento è omesso (mai `0`).

## Errori (eccezione di dominio `EmbeddingError`)

| Condizione | `reason` | `retriable` | evento |
|---|---|---|---|
| HTTP 429 | `http 429` | sì | `embeddings_error` |
| HTTP 5xx | `http <stato>` | sì | `embeddings_error` |
| HTTP 4xx (≠429), es. 401/400/404 | `http <stato>` | no | `embeddings_error` |
| rete/timeout | nome dell'eccezione | sì | `embeddings_error` |
| config incompleta (costruzione) | `<campi> missing` | no | — |

`provider` dell'errore e dell'evento = `openai:<model>`. **Mai** nel messaggio, nella `reason` o nei
campi dell'evento: la chiave, le intestazioni, il corpo della richiesta.

## Eventi di osservabilità

- `embeddings_provider_selected` non è emesso dai provider cloud oggi (parità con `azure`).
- `embeddings` (INFO): `provider`, `texts`, `tokens` (se noto).
- `embeddings_error` (ERROR): `provider`, `reason`, `retriable`.

## Controllo di salute (`sertor-rag doctor`)

- Statico: provider `openai` con chiave vuota ⇒ area *provider* `fail`, problema che nomina
  `OPENAI_API_KEY`.
- `--online`: embedda la sentinella; errore ⇒ area *provider* `warn` con motivo ripulito.

## Non-regressione `azure`

Identico a prima: `POST {endpoint}/embeddings`, intestazione `api-key`, `api-version` solo se l'endpoint
non contiene `/openai/v1`, nome `azure:<deployment>`, messaggio di config incompleta invariato.
