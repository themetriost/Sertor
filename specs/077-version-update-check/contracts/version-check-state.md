# Contratto — stato del version-check + stamp installato

**Branch**: `feat013-version-check-backlog`

Due artefatti runtime locali sotto `.sertor/`, entrambi gitignored (FR-018, `RUNTIME_IGNORES` esteso).

## 1. `.sertor/.version-check.json` — schema `version.check/1`

Scritto da `version-check.ps1` (SessionEnd); letto da `version-check-start.ps1` (Claude) / dal prompt
+ agente (Copilot) e da un umano.

### Esempio — indietro
```json
{
  "schema": "version.check/1",
  "verdict": "behind",
  "installed": "0.1.0",
  "latest": "0.2.0",
  "checked_at": "2026-06-25T20:50:00Z",
  "dimensions": { "sertor": "0.1.0", "sertor-flow": "0.1.0" }
}
```

### Esempio — allineato (stato canonico, no avviso)
```json
{
  "schema": "version.check/1",
  "verdict": "up-to-date",
  "installed": "0.2.0",
  "latest": "0.2.0",
  "checked_at": "2026-06-25T20:50:00Z"
}
```

### Esempio — inconcludente (offline / parse fallito)
```json
{
  "schema": "version.check/1",
  "verdict": "unknown",
  "installed": "0.1.0",
  "latest": "",
  "checked_at": "2026-06-24T09:00:00Z"
}
```

### Campi (MUST)
- `schema` = `"version.check/1"`.
- `verdict` ∈ `{behind, up-to-date, ahead, unknown}`.
- `installed` = stringa dallo stamp `.sertor/.sertor-version` (vuota → `unknown`).
- `latest` = stringa dal `/VERSION` remoto (vuota se GET fallita → `unknown`).
- `checked_at` = ISO-8601 UTC dell'ultima GET riuscita (gate cache ~24h).
- `dimensions` (opzionale, additivo) = mappa dimensione→versione installata (FR-012/US6).

### Regole (MUST)
- **S1 (gate dell'avviso)**: il SessionStart avvisa **solo** se `verdict == "behind"`. Ogni altro
  verdetto (o file assente) → no-op (INV-1/INV-2).
- **S2 (cache)**: `checked_at` entro ~24h e `SERTOR_VERSION_CHECK_FORCE` non impostata → riuso senza
  GET (FR-006); oltre 24h o forzato → nuova GET (FR-008).
- **S3 (mai falso «behind»)**: `installed`/`latest` non parsabili → `verdict: "unknown"`, `latest: ""`;
  nessun avviso (FR-010).
- **S4 (privacy)**: nessun segreto; solo numeri di versione pubblici (FR-015).
- **S5 (confronto, D-4)**: verdetto derivato dal confronto **semantico per segmenti numerici** con
  fallback lessicale; `installed >= latest` ⇒ verdetto non-`behind` (FR-004, dev-locale).

## 2. `.sertor/.sertor-version` (+ `.sertor/.sertor-flow-version`)

Stamp di **testo** a singola riga, scritto dall'installer a install/upgrade-time.

### Esempio
```
0.1.0
```

### Regole (MUST)
- **T1 (sorgente)**: scritto dall'installer dal proprio `/VERSION` (in-process via
  `importlib.metadata`), **mai** dall'hook a runtime (D-3: nessun Python nel path caldo).
- **T2 (upgrade)**: `upgrade` **riscrive** lo stamp con la nuova versione (chiude la loop, FR-013).
- **T3 (uninstall)**: rimosso con l'intero `.sertor/`.
- **T4 (per-dimensione)**: `sertor-flow install`/`upgrade` scrive `.sertor/.sertor-flow-version`
  (Could FR-012); se assente, il confronto usa il solo stamp `sertor`.
