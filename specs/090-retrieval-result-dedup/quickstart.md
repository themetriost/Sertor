# Quickstart — dedup risultati (Phase 1)

Come esercitare e **misurare** la feature. Il criterio di «fatto» è il **lift misurato**, non l'intenzione.

## 1. Misura di partenza (baseline rosso — già osservato)

```powershell
uv run --project .sertor sertor-rag eval run --fused
# oggi: search_docs hit@3 0.625 (< baseline 0.75), union 0.833, gate ROSSO
```

## 2. Toggle della dedup

```powershell
# default: on
$env:SERTOR_DEDUP = "false"   # bypass (deve dare le metriche pre-feature)
$env:SERTOR_DEDUP = "true"    # attiva
```

O in modo persistente: riga `SERTOR_DEDUP=true` in `.sertor/.env`.

## 3. Prova il caso reale (dogfood)

```powershell
# prima: il blocco CLAUDE.md + la copia assets/ scavalcano la pagina concetto
uv run --project .sertor sertor-rag search-docs "the step ritual and definition of done"
# atteso con dedup on: wiki/concepts/step-ritual.md rientra nel top-3
```

## 4. Verifica il lift (il gate)

```powershell
uv run --project .sertor sertor-rag eval run --fused
# atteso con dedup on: search_docs hit@3 ≥ 0.75, union risale, gate VERDE
# NON eseguire --record-baseline finché il lift non è reale (Principio XII)
```

## 5. Confronto A/B (prova che è la dedup)

```powershell
$env:SERTOR_DEDUP = "false"; uv run --project .sertor sertor-rag eval run --fused   # metriche pre-feature
$env:SERTOR_DEDUP = "true";  uv run --project .sertor sertor-rag eval run --fused   # metriche con lift
# il delta isola l'effetto della dedup (SC-002/SC-003)
```

## 6. Gate pre-merge (SC-005)

```powershell
uv run pytest -m "not cloud"      # incl. tests/unit/test_dedup.py + engine tests
uv run ruff check .
git diff --stat src/sertor_core/services/ingestion* src/sertor_core/services/indexing*   # DEVE essere vuoto (indicizzazione invariata)
```

## 7. Post-merge (dogfood)

Re-lock runtime → re-index → `eval run --fused` (conferma gate verde sul corpus reale) → smoke MCP →
EXEC roadmap. Se il lift è reale e stabile, **allora** si può `--record-baseline` per fissare il nuovo
livello (decisione esplicita, non riflesso).

---

## Nota (fuzzy = follow-up)

Se dopo la dedup **esatta** resta un residuo di near-duplicate *non identici* (stesso senso, testo
leggermente diverso), è il segnale per promuovere il **fuzzy** (MinHash/shingling) — tracciato nel backlog
E5, fuori da questo MVP.
