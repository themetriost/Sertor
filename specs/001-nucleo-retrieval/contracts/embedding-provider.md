# Contratto — Porta `EmbeddingProvider`

Astrazione del provider di embeddings (in `domain/ports.py`). Implementata dagli adapter
`adapters/embeddings/{ollama,azure}.py`. Il core dipende **solo** da questa porta (Principio I/II).

## Interfaccia

```python
class EmbeddingProvider(Protocol):
    name: str          # es. "ollama:nomic-embed-text", "azure:text-embedding-3-large"
    dim: int | None    # dimensione del vettore; scoperta al primo batch se None
    batch_size: int    # da Settings (REQ-014)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Vettori per ciascun testo, processati a batch. Ordine preservato."""
```

## Contratto comportamentale

| # | Precondizione | Comportamento | Postcondizione | Req |
|---|---------------|---------------|----------------|-----|
| 1 | provider configurato, `texts` non vuota | elabora a batch di `batch_size` | `len(out) == len(texts)`, ordine preservato; `dim` valorizzato | REQ-012/014 |
| 2 | `texts` vuota | nessuna chiamata di rete | `[]` | REQ-014 |
| 3 | configurazione local-only (Ollama) | nessuna connessione cloud | vettori da servizio locale | REQ-016 |
| 4 | provider non disponibile o errore | solleva `EmbeddingError` | `EmbeddingError(provider, reason, retriable)`; **nessun** vettore parziale silenzioso | REQ-015 |

## Invarianti

- Tutti i vettori di una stessa chiamata hanno la stessa dimensione `dim`.
- `embed` è una funzione pura rispetto al modello (stesso input+modello → stesso output, dove il
  provider è deterministico): base dell'idempotenza dei vettori (NFR-02).
- L'adapter **non** scrive segreti nei log (REQ-032).

## Adapter MVP

- **Ollama** (locale): `POST {host}/api/embed`, `{model, input}`. Default provider in `backend=local`.
- **Azure OpenAI** (cloud): `POST {endpoint}/embeddings` con header `api-key`; riordina `data` per `index`.

## Test (contract tests)

- Mock provider deterministico per i test del core (NFR-01).
- Verifica: lunghezza/ordine output (#1), vuoto (#2), errore strutturato su provider down (#4),
  assenza di rete in local-only (#3, via spia sul client HTTP).
