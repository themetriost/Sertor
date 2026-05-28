# 02 — Hybrid + reranking

Estende il baseline (Tappa 1) con **retrieval lessicale BM25**, **fusione RRF** dense+sparse
e **reranking** cross-encoder. Riusa le collection Chroma indicizzate in `01-baseline/.index`.

## Componenti
- `hybrid.py` — `HybridIndex`: dense (Chroma) + sparse (BM25, tokenizer che preserva gli
  identificatori) + fusione `rrf()`. Modi: `dense` / `sparse` / `hybrid`.
- `rerank.py` — `rerank()`: cross-encoder FlashRank (ONNX, niente torch) sul pool fuso.
- `evaluate.py` — confronto dense vs hybrid vs hybrid+rerank sui 3 provider, su un eval
  set esteso (`eval_queries.json`) con query NL e a **simboli esatti**.

## Uso
```bash
python 02-hybrid-reranking/hybrid.py "OAuth2PasswordBearer" --provider ollama --mode hybrid -k 5
python 02-hybrid-reranking/evaluate.py
```

## Esito (sintesi)
- **hybrid+rerank trasforma l'embedder locale debole** (ollama: MRR 0.50→0.90; sui simboli 0.13→0.94).
- Sui forti embedder Azure (già vicini al soffitto su questo eval) il reranker generico
  ms-marco **non aiuta** e a volte peggiora leggermente.

Dettagli e learnings in [`wiki/experiments/02-hybrid-reranking.md`](../wiki/experiments/02-hybrid-reranking.md).
