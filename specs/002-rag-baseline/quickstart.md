# Quickstart — Motore RAG vettoriale (baseline)

Come usare il motore baseline come libreria. Riflette il design ([plan.md](plan.md)); i percorsi di
codice sono il layout target.

## 1. Costruire il motore (cablato da config)

```python
from sertor_core.composition import build_baseline_engine

engine = build_baseline_engine()     # provider/backend/k da Settings (env/.env)
print(engine.name)                   # "baseline"
```

## 2. Indicizzare una codebase (rebuild idempotente)

```python
report = engine.index("/path/al/repo")
print(report.chunks, report.embedding_dim)   # n. chunk + dimensione embedding (REQ-003)
```

- Ricostruisce l'indice **da zero** (REQ-002): nessun chunk duplicato o residuo da file rimossi.
- Se il provider non è disponibile, l'operazione **annulla** senza lasciare un indice parziale
  (REQ-004): l'indice preesistente resta intatto.

## 3. Interrogare (similarità vettoriale)

```python
hits = engine.query("come si valida un input", k=5)
for h in hits:
    print(h.path, h.doc_type, h.chunk_id, round(h.score, 3))
    print(h.text[:200])
```

- Calcola l'embedding della query con **lo stesso provider** dell'indice (REQ-006).
- `k` opzionale (default da Settings, REQ-008); `k` > disponibili → tutti i risultati.
- **Indice inesistente** → `IndexNotFoundError` esplicito (REQ-009), non lista vuota:

```python
from sertor_core import IndexNotFoundError
try:
    engine.query("x")
except IndexNotFoundError as e:
    print("Costruisci prima l'indice:", e)
```

## 4. Valutare la pertinenza (hit-rate@k, MRR)

```python
from sertor_core.engines.evaluation import evaluate

ground_truth = [
    ("come validare l'input", ["app/validation.py"]),
    ("avvio del server",       ["web/server.js"]),
]
report = evaluate(engine, ground_truth)
print(report.hit_rate)   # {1: .., 3: .., 5: .., 10: ..}
print(report.mrr)        # MRR@10
```

Le soglie di accettazione si fissano alla misura, con il prototipo come baseline (DA-1/DA-3).

## 5. Commutare provider (solo config)

```bash
RAG_BACKEND=local     # Ollama + Chroma (default)
RAG_BACKEND=azure     # Azure OpenAI + Azure AI Search
```

Nessuna modifica al codice: il motore prende provider e backend da `Settings` (REQ-010/012).

## 6. Verifica rapida (accettazione)

| Verifica | Atteso | Criterio |
|----------|--------|----------|
| Indicizza 2 repo distinti senza modifiche | indici interrogabili, isolati | SC-001 |
| Re-index stessa codebase | stesso n. chunk e stessi risultati | SC-003 |
| ≥2 provider (locale+cloud) | funziona cambiando solo config | SC-004 |
| Query su indice mancante | `IndexNotFoundError` | REQ-009 |
| Valutazione su ground-truth | hit-rate@k + MRR riportati | REQ-011 |
| Log di index/query | operazione, provider, conteggi, tempi | SC-006 |
