# Quickstart — `search_combined` strutturato (Tempo 2 FEAT-003)

**Branch**: `070-search-combined-strutturato` · **Spec**: [`spec.md`](./spec.md)

Come esercitare e verificare il nuovo contratto. Comandi **PowerShell** (Windows); local-first,
nessuna rete oltre l'embedder.

## 1. Suite (no cloud)

```powershell
uv run pytest -m "not cloud"
uv run ruff check .
```

Atteso: **verde** + lint **pulito** (SC-006/RNF-5). Test rilevanti:
`tests/unit/test_retrieval_facade.py`, `test_fusion.py`, `test_fused_runner.py`,
`test_output_fused_eval.py`, `test_cli_fused_eval.py`, `test_mcp_server.py`,
`tests/integration/test_end_to_end.py`.

## 2. Libreria — la coppia strutturata (via test, Principio XI)

```python
fused = facade.search_combined("quali requisiti e dove sono implementati", k=6)
assert isinstance(fused, FusedResults)
assert all(r.doc_type is DocType.DOC for r in fused.docs)
assert all(r.doc_type is DocType.CODE for r in fused.code)
# budget separato: code NON è vuota perché i doc rankano più alti
assert fused.code  # SC-001 / US1
# lista unica deterministica
assert fused.flatten() == fused.flatten()  # SC-003
```

## 3. CLI — due sezioni etichettate

```powershell
uv run sertor-rag search "come funziona il retrieval ibrido" --type both
# → sezione `docs:` + sezione `code:`
uv run sertor-rag search "come funziona il retrieval ibrido" --type both --json
# → {"docs":[...],"code":[...]}
```

`--type code` / `--type doc` restano invariati (una sezione) — SC-002.

## 4. MCP — output etichettato per l'agente

Riavviare il server (serve codice nuovo, non solo indice). Il tool `search_combined` ritorna
`{"docs":[…],"code":[…]}` (SC-007). Smoke test del rituale: `search_code` **e** `search_docs`
(path-filter) + un `find_symbol` a posizione nota.

## 5. Fusion coverage migliorata + re-baseline (passo operativo)

```powershell
# misura col nuovo contratto (vehicle, deterministico)
uv run sertor-rag eval run --fused
# → fusion coverage > 0.17 atteso (SC-004); le superfici IR sono code/docs (combined non è più ranked)

# ri-registra la baseline fusa DOPO il refactor (su Azure-large, costo centesimi)
$env:RAG_BACKEND="azure"
uv run sertor-rag eval run --fused --record-baseline
# → aggiorna [fused_baseline] in eval/baseline.toml (fusion_coverage nuovo, 2 superfici);
#   la baseline IR [baseline] resta intatta (preserve-both, SC-005)
```

## 6. Re-index dogfood (rituale, dopo il merge)

```powershell
uv run sertor-rag index .
```

Poi smoke test MCP. NB: `search_combined` via MCP ora rende i due flussi etichettati.

## Definition of Done

- [ ] `FusedResults` + `flatten()` nel domain; `search_combined` ritorna `FusedResults`.
- [ ] `search_code`/`search_docs`/porte/engine **invariati**.
- [ ] MCP `{"docs","code"}`; CLI due sezioni etichettate + JSON.
- [ ] fusion coverage sulle due liste; superfici IR del runner a due; evento `fused_eval` aggiornato.
- [ ] baseline fusa **ri-registrata** (> 0.17); baseline IR intatta.
- [ ] suite verde, lint pulito; nessun chiamante di prima parte rotto.
