# Contratto — file di stato di salute RAG `rag.health/1`

**Branch**: `076-enforcement-freschezza-rag` · `.sertor/.rag-health.json`

Il file che l'hook `SessionEnd` scrive e il segnale `SessionStart` legge (DA-D-r1, research D-1).
Schema piatto, stabile e versionato; gitignored sotto `.sertor/`.

## Schema (`rag.health/1`)

```json
{
  "schema": "rag.health/1",
  "verdict": "healthy | degraded",
  "timestamp": "<ISO-8601 UTC>",
  "reason": "<string: causa/area che ha fallito; scrubbed; vuota se healthy>",
  "areas": { "config": "pass|warn|fail", "provider": "pass|warn|fail",
             "index": "pass|warn|fail", "mcp": "pass|warn|fail" },
  "exit_code": 0
}
```

## Regole (MUST)
- **C1** `schema` sempre presente = `"rag.health/1"` (versiona il contratto).
- **C2** `verdict` ∈ `{healthy, degraded}` (FR-006/011).
- **C3** `timestamp` ISO-8601 UTC (FR-011).
- **C4** se `verdict=degraded` → `reason` non vuota nomina l'area/causa (FR-011); se `healthy` →
  `reason` può essere vuota.
- **C5** nessun segreto in alcun campo (NFR-3): `reason`/`areas` derivano da `doctor` (già scrubbed),
  mai da `.env`.
- **C6** a `verdict=healthy` il file è **riscritto** (non cancellato): l'ultimo verdetto è sempre
  ispezionabile e il segnale d'avvio fa no-op (INV-1/NFR-6, FR-010/015).

## Esempi
**Degradato (indice stantio)**
```json
{ "schema": "rag.health/1", "verdict": "degraded",
  "timestamp": "2026-06-24T20:50:00Z",
  "reason": "index area: stale (source files newer than manifest mtime)",
  "areas": { "config": "pass", "provider": "pass", "index": "fail", "mcp": "pass" },
  "exit_code": 1 }
```
**Sano (clear dopo guarigione)**
```json
{ "schema": "rag.health/1", "verdict": "healthy",
  "timestamp": "2026-06-24T21:10:00Z", "reason": "",
  "areas": { "config": "pass", "provider": "pass", "index": "pass", "mcp": "pass" },
  "exit_code": 0 }
```
