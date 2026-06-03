# Contratto — Valutazione della pertinenza

Misura la qualità del retrieval del motore su un ground-truth (REQ-011). Capacità di prima classe:
"una feature senza misura non è fatta" (Principio V).

## Interfaccia

```python
def evaluate(
    engine: BaselineEngine,
    ground_truth: list[tuple[str, list[str]]],   # (query, expected_paths)
    ks: tuple[int, ...] = (1, 3, 5, 10),
) -> EvalReport:
    """Calcola hit-rate@k (per ogni k) e MRR@10 sul ground-truth fornito."""
```

`EvalReport`: `{ hit_rate: dict[int, float], mrr: float, queries: int, provider: str }`.

## Contratto comportamentale

| # | Precondizione | Comportamento | Postcondizione | Req |
|---|---------------|---------------|----------------|-----|
| 1 | ground-truth (query→file attesi), indice presente | per ogni query: top-10 dal motore | `hit_rate[k]` per k∈ks e `mrr` calcolati e riportati | REQ-011 |
| 2 | risultato con `path` ∈ expected | conta come hit a rango = posizione | contribuisce a hit@k (k≥rango) e a MRR | REQ-011 |
| 3 | nessun risultato pertinente nei top-10 | rango assente | contributo 0 a MRR, nessun hit | REQ-011 |
| 4 | ground-truth vuoto | nessuna query valutata | report con metriche a 0, **nessun errore** | edge |
| 5 | provider locale vs cloud | due valutazioni confrontabili | soglia ridotta ammessa per il locale | SC-002, DA-3 |

## Definizioni

- **hit@k** = |{ query : ∃ risultato nei primi k con path ∈ expected_paths }| / |query|.
- **MRR@10** = (1/|query|) · Σ (1/rango_primo_pertinente), 0 se nessun pertinente nei primi 10.
- **pertinente** = `RetrievalResult.path ∈ expected_paths` della query.

## Soglie (DA-1/DA-3, SC-002)

Le soglie di accettazione **non** sono nel codice: si fissano alla misura, baseline = prototipo
(azure-small hit@5 ≈ 0.80; ollama hit@5 ≈ 0.67), soglia ridotta per il locale. Il test di soglia è
`xfail` finché manca un ground-truth reale.

## Test (contract tests)

Con un mini ground-truth costruito su un indice popolato (`FakeEmbedder`+store): hit@k coerenti con i
risultati attesi (#1/#2), MRR su ranghi noti (#2/#3), ground-truth vuoto → metriche 0 (#4). La soglia
reale resta `xfail` (DA-1).
