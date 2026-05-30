# 03 — GraphRAG (A: code graph leggero)

Code knowledge graph costruito dall'**AST** del codice (`networkx`), per query strutturali
e multi-hop complementari al retrieval vettoriale. Riusa il corpus `raw/fastapi`.

> Questa è la **parte A** (grafo custom leggero). La **parte C** (Microsoft GraphRAG +
> confronto) è pianificata in seguito.

## Componenti
- `build_graph.py` — AST → grafo: nodi module/class/function/method/doc; archi
  contains/imports/calls/inherits/mentions (doc→simbolo). Salva GraphML in `.index/`.
- `graph_query.py` — `def` / `callers` / `callees` / `docs` / `context` (multi-hop).
- `evaluate.py` — precisione "definizione@1" sulle query a simbolo + ricchezza multi-hop.

## Uso
```bash
python 03-graphrag/build_graph.py
python 03-graphrag/graph_query.py context OAuth2PasswordBearer
python 03-graphrag/evaluate.py
```

## Esito (sintesi)
- Grafo: 1917 nodi / 4868 archi (1256 contains, 1166 calls, 1651 mentions, 579 imports, 216 inherits).
- Definizione corretta al rank 1: **6/8** simboli. I 2 miss (`JSONResponse`,
  `WebSocketDisconnect`) sono **re-export da Starlette** → non definiti localmente (limite AST).
- Navigazione preziosa: es. `HTTPException` ha 69 chiamanti; `APIRouter` collegato a 10 doc.

Dettagli e learnings in [`wiki/experiments/03-graphrag.md`](../wiki/experiments/03-graphrag.md).
