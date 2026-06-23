# Data Model — `sertor-rag doctor` (E12-FEAT-001)

**Branch**: `074-doctor-salute` · **Fase**: 1 (Design) · **Data**: 2026-06-23

Entità **pure** del dominio diagnostico (frozen dataclass, nessun SDK), separate dalla resa. Vivono in
`src/sertor_core/services/doctor.py` (servizio + entità di esito) — coerente con il pattern di
`services/eval/models.py`. Lo schema JSON è il **contratto stabile** per skill/CI (SC-003).

---

## Enum

### `Severity`
Severità di un singolo problema diagnosticato.

| Valore | Significato | Gate (exit ≠ 0)? |
|--------|-------------|------------------|
| `CRITICAL` | impedisce l'uso di Sertor ora (env mancante, indice assente) | **sì** |
| `WARN` | degrado noto e azionabile, ma usabile (stantio, MCP non registrato, irraggiungibile) | no |
| `INFO` | nota non bloccante (es. stantio MCP `unknown`) | no |

### `AreaStatus` (rollup per-area)
| Valore | Derivazione |
|--------|-------------|
| `pass` | nessun problema nell'area |
| `warn` | max severità dei problemi = `WARN`/`INFO` |
| `fail` | ≥1 problema `CRITICAL` |

### `AreaName`
`config` · `provider` · `index` · `mcp` (quattro aree, FR-001; ordine deterministico nel report).

### `ProbeStatus` (provider, opt-in)
`reachable` · `unreachable` · `skipped` (offline/no flag) · `not_applicable` (provider locale già coperto dallo statico).

---

## Entità

### `Problem` (frozen)
Un'anomalia rilevata in un'area: causa + rimedio (FR-002).

| Campo | Tipo | Note |
|-------|------|------|
| `severity` | `Severity` | determina il gate |
| `code` | `str` | identificatore stabile e machine-readable (es. `env_missing_key`, `index_absent`, `index_stale`, `provider_unreachable`, `mcp_not_registered`, `mcp_stale_after_reindex`) |
| `message` | `str` | causa, in chiaro (scrubbed) |
| `remedy` | `str` | rimedio concreto (es. `sertor-rag index .`, «imposta AZURE_OPENAI_API_KEY», «registra il server MCP») |
| `fields` | `tuple[str, ...]` | opzionale: chiavi env coinvolte (per env), **mai valori** |

### `AreaReport` (frozen)
| Campo | Tipo | Note |
|-------|------|------|
| `name` | `AreaName` | |
| `status` | `AreaStatus` | rollup puro dai `problems` |
| `problems` | `tuple[Problem, ...]` | vuoto ⇒ `pass` |
| `detail` | `dict[str, str \| bool \| None]` | metadati informativi per area (es. `last_index`, `provider`, `probe`) — solo dati non-segreti |

### `HealthReport` (frozen) — radice dell'esito
| Campo | Tipo | Note |
|-------|------|------|
| `areas` | `tuple[AreaReport, ...]` | le quattro, in ordine fisso |
| `online` | `bool` | il flag `--online` era attivo |
| `overall` | `AreaStatus` | rollup globale (`fail` se ≥1 area `fail`; else `warn` se ≥1 `warn`; else `pass`) |

Metodi puri:
- `is_healthy() -> bool` — `overall != fail` (gate: `False` ⇔ exit ≠ 0).
- `exit_code() -> int` — `1` se esiste ≥1 `Problem` `CRITICAL`, else `0` (FR-011/SC-004).

### `ProviderProbe` (frozen) — esito del probe rete (DA-D5a)
| Campo | Tipo | Note |
|-------|------|------|
| `status` | `ProbeStatus` | |
| `reason` | `str` | motivo scrubbed quando `unreachable`/`skipped`; vuoto altrimenti |

---

## Schema JSON stabile — `doctor.report/1` (SC-003, FR-010)

```json
{
  "schema": "doctor.report/1",
  "overall": "pass|warn|fail",
  "online": false,
  "exit_code": 0,
  "areas": [
    {
      "name": "config",
      "status": "pass|warn|fail",
      "detail": { "...": "..." },
      "problems": [
        {
          "severity": "critical|warn|info",
          "code": "env_missing_key",
          "message": "...",
          "remedy": "...",
          "fields": ["AZURE_OPENAI_API_KEY"]
        }
      ]
    },
    { "name": "provider", "status": "...", "detail": {"probe": "skipped"}, "problems": [] },
    { "name": "index", "status": "...", "detail": {"last_index": "2026-06-23T...Z"}, "problems": [] },
    { "name": "mcp", "status": "...", "detail": {"registered": true}, "problems": [] }
  ]
}
```

Invarianti dello schema:
- chiavi top-level **fisse**; `areas` sempre 4 elementi, **ordine** `config,provider,index,mcp`;
- `exit_code` ridondante nel JSON (comodità per skill che non ispezionano `$?`), coerente con
  `is_healthy()`;
- ogni stringa passa da `scrub_text` prima della serializzazione (FR-013/SC-006): nessun segreto;
- `detail` contiene **solo** metadati non-segreti (timestamp, booleani, nome provider, esito probe).

---

## Errore di dominio

### `DoctorCheckFailed(SertorError)`
Sollevato dal handler quando il report ha `exit_code() == 1` **dopo** aver stampato il report
(umano/JSON), così `main()` mappa a exit 1 (pattern di `RegressionDetected`/`GraphRegressionDetected`,
`cli/__main__.py:721,911`). Non è un crash: il report è già emesso; l'errore serve solo al gate
dell'exit code. Messaggio: sintesi delle aree critiche fallite (scrubbed).

---

## Mapping segnali → entità (puro, testabile)

| Funzione pura (in `services/doctor.py`) | Input | Output |
|-----------------------------------------|-------|--------|
| `check_config(missing: list[str])` | da `validate_backend()` | `AreaReport(config)` |
| `check_provider(missing_provider, probe: ProviderProbe \| None)` | sottoinsieme provider + probe | `AreaReport(provider)` |
| `freshness_from_manifest(state, current_stats)` | `ManifestState \| None` + `[(path, mtime)]` | `AreaReport(index)` |
| `check_mcp(registered: bool, index_stale: bool)` | lettura `.mcp.json` + esito index | `AreaReport(mcp)` |
| `assemble(areas, online)` | le 4 aree | `HealthReport` |

I *side-effect* (leggere `.mcp.json`, `os.stat`, costruire l'embedder per il probe) vivono in helper
sottili nel handler/composition; le funzioni di **decisione** sopra sono pure → testabili con input
sintetici, senza FS/rete (Principio V, F.I.R.S.T.).
