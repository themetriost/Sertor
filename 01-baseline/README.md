# 01 — Baseline (vector retrieval)

RAG baseline su corpus campione `raw/fastapi` (codice + esempi + doc Markdown).
Chunk + embeddings + similarity search su **Chroma**, con una collection per provider
di embedding (Ollama, Azure small, Azure large) per poterli confrontare.

## Componenti
- `chunking.py` — splitter language-aware (Python) e markdown (baseline; tree-sitter più avanti).
- `index.py` — costruisce i chunk e indicizza su Chroma (`.index/`, gitignored).
- `search.py` — similarity search su una collection.

## Uso
```bash
# indicizza (un provider o tutti)
python 01-baseline/index.py --provider ollama
python 01-baseline/index.py --provider all

# cerca
python 01-baseline/search.py "how to declare a dependency with Depends" --provider ollama -k 5
```

## Stato corrente
- 655 documenti → **3500 chunk**.
- Indicizzati: `ollama` (768), `azure-small` (1536), `azure-large` (3072).
- Retrieval dual-corpus funzionante (recupera sia codice sia doc pertinenti).

Vedi la valutazione e i confronti in [`wiki/experiments/01-baseline.md`](../wiki/experiments/01-baseline.md).
