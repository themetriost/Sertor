# Contract — `.sertor/.last-hook-error` (schema `hook.error/1`)

**Tipo**: file di stato runtime, JSON, **singolo e sovrascritto** (semantica «ultimo errore»).
**Gemello**: `.sertor/.rag-health.json` (schema `rag.health/1`). **Stabilità**: schema versionato;
campi aggiuntivi sono additivi (un consumatore ignora i campi non noti).

## Forma

```json
{
  "schema": "hook.error/1",
  "hook": "memory-capture",
  "ts": "2026-06-29T14:03:21Z",
  "reason": "sertor-rag memory archive exited 3"
}
```

## Campi

| Campo | Tipo | Obbligo | Vincoli |
|---|---|---|---|
| `schema` | string | sì | letterale `"hook.error/1"` |
| `hook` | string | sì | uno tra `memory-capture` · `rag-freshness` · `wiki-pending-check` · `version-check` |
| `ts` | string | sì | UTC ISO-8601 `yyyy-MM-ddTHH:mm:ssZ` |
| `reason` | string | sì | breve, leggibile, **secret-free** (≤ ~200 char consigliati) |

## Produttore
La funzione inline `Write-HookBreadcrumb` (byte-identica nei 4 hook in scope). Scrive con
`Set-Content` (sovrascrittura), crea `.sertor/` se assente. **Best-effort**: ogni errore di scrittura è
inghiottito dal `catch` interno della funzione → l'hook prosegue a `exit 0`.

## Consumatore
In questa feature **nessun consumo attivo automatico** (out-of-scope, Could): la traccia è prodotta e
**ispezionabile** da un operatore o a un avvio successivo. L'induzione automatica resta quella di
FEAT-011 su `.rag-health.json`.

## Garanzie / invarianti
- Scritto **solo** su un path degradato reale (mai su no-op gated — REQ-004).
- **Sovrascritto** a ogni nuovo errore (non append — DA-3).
- `reason` **non** contiene segreti né contenuto `.env` (REQ-008).
- Non versionato: in `RUNTIME_IGNORES`; rimosso dall'uninstall di `.sertor/` (REQ-016).
- La sua scrittura non rende mai l'hook fatale (REQ-005/FR-005); l'hook esce 0 in ogni path (FR-007).
