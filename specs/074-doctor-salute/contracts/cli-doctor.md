# Contract — CLI `sertor-rag doctor` (E12-FEAT-001)

Vehicle deterministico (Principio XI): **mai un LLM**, **sola lettura** (FR-014/FR-015). Esito umano +
`--json` a schema stabile (`doctor.report/1`). Comando nuovo, additivo (SC-012).

## Sintassi

```
sertor-rag doctor [--online] [--area {config|provider|index|mcp|all}] [--json] [--corpus NAME] [-v] [--log-json] [--log-config FILE]
```

| Flag | Default | Significato |
|------|---------|-------------|
| `--online` | off | abilita i check che richiedono rete (probe provider; eventuale reachability futura). Senza il flag: **zero traffico di rete** (FR-007/012, SC-005). Nome del flag = decisione di design (DA-D1 lasciava il nome al plan): **`--online`**. |
| `--area` | `all` | restringe le aree eseguite. `config` = solo env/config (sottoinsieme usato da `configure --check`, D6). `all` = le quattro. |
| `--json` | off | emette `doctor.report/1` su stdout (resto invariato). |
| `--corpus` | `SERTOR_CORPUS` | override del namespace, come gli altri comandi. |
| logging | — | flag condivisi `_add_logging_flags` (osservabilità). |

## Comportamento

1. risolve `Settings` (+ `--corpus`), chiama `enable_observability(settings)` (no-op se off);
2. esegue le aree richieste (default tutte), leggendo i segnali via factory/`Settings` (vedi
   research D1);
3. con `--online`: esegue il **probe provider** = `build_embedder(settings, allow_download=False)` +
   `embed([sentinel])`; senza `--online`: l'area provider riporta solo lo stato statico, `probe=skipped`;
4. assembla `HealthReport`, lo stampa (umano o `--json`), poi solleva `DoctorCheckFailed` se
   `exit_code()==1`.

## Aree e criteri (DA-D4, deterministico)

| Area | pass | warn | fail (CRITICO) |
|------|------|------|----------------|
| `config` | nessuna chiave mancante | — | ≥1 chiave env mancante (`validate_backend()`) |
| `provider` | config provider completa (+ probe reachable se `--online`) | probe `unreachable`/`skipped` | config provider incompleta (eredita le chiavi provider da `validate_backend()`) |
| `index` | manifest presente + sorgenti note invariate | sorgenti note modificate/cancellate (stantio) | `IndexManifest.load()→None` (assente/incompatibile) |
| `mcp` | `sertor-rag` registrato in `.mcp.json` | non registrato; oppure stantio-dopo-reindex (best-effort) | — |

## Exit code (gate, FR-011/SC-004)

| Condizione | Exit |
|------------|------|
| nessun problema `CRITICAL` | `0` |
| ≥1 problema `CRITICAL` (env mancante / indice assente) | `1` (via `DoctorCheckFailed`) |
| errore d'uso (argparse) | `2` |

I **warn** non alterano l'exit (FR-001/US1.3). `doctor` non altera mai config/indice (SC-009).

## Offline-safe (FR-012/SC-005)

- senza `--online`: nessuna chiamata di rete in alcuna area; tutti gli statici girano e riportano;
- con `--online` ma offline: il probe → `unreachable`/`skipped` con motivo (scrubbed), **mai crash**;
- `glove` senza file dati + `--online`: `unreachable` azionabile (non scarica: `allow_download=False`).

## Privacy (FR-013/SC-006)

Ogni stringa di output (umano e JSON) passa da `scrub_text` (`observability/scrub.py`); l'evento
`doctor` è metrics-only (mai chiavi/valori/sentinella/motivi).

## Esempio (umano, installazione sana)

```
doctor: PASS
  config    pass  (provider=glove, store=local)
  provider  pass  (probe=skipped — run with --online to check reachability)
  index     pass  (last_index=2026-06-23T14:02:11Z)
  mcp       pass  (registered in .mcp.json)
```

## Esempio (umano, due problemi)

```
doctor: FAIL
  config    FAIL  missing AZURE_OPENAI_API_KEY → set it in .sertor/.env (or run `sertor configure`)
  provider  FAIL  provider config incomplete (AZURE_OPENAI_API_KEY)
  index     warn  sources changed since last index → run `sertor-rag index .`
  mcp       warn  server not registered → see `sertor install rag` / `.mcp.json`
exit: 1
```
