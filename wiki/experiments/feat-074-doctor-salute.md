---
title: "E12-FEAT-001 sertor-rag doctor — verifica di salute deterministica"
type: experiment
tags: [usabilita, diagnostica, sertor-rag, deterministic, vehicle, principio-x, principio-xi]
created: 2026-06-23
updated: 2026-06-23
branch: ["074-doctor-salute", "076-doctor-freshness-hash"]
sources: ["specs/074-doctor-salute/plan.md", "src/sertor_core/services/doctor.py", "src/sertor_core/cli/__main__.py"]
---

# E12-FEAT-001 sertor-rag doctor — verifica di salute deterministica

## Essenza

Implementazione del **primitive deterministico** centrale dell'epica E12 `usabilità`: il comando **`sertor-rag doctor`** che risponde a «ha funzionato?» dopo install/configure di Sertor con una **diagnostica a quattro aree** — config/env · provider embeddings · indice RAG · server MCP — per ogni problema riporta **causa + rimedio concreto**, esito per-area **pass/warn/fail** (fallback umano), output umano + `--json` (contratto `doctor.report/1`), **exit code gate** (≠0 se ≥1 problema CRITICO).

Puramente **deterministico** (confine D↔N vincolante): **nessun LLM** nel run, sola lettura, **offline-safe by default** (probe di raggiungibilità provider opt-in dietro flag `--online`, minimale, mai scarica GloVe). Rientra nel pattern **thin-consumer** via `build_provider_probe` + helper sola-lettura nel composition root.

## Decisioni di design

### DA-D4: Criteri di severità (pass/warn/fail)

| Aspetto | Criterio CRITICO | Criterio WARN | Criterio OK |
|---------|---|---|---|
| **Config** | var env mancante | — | presente e valida |
| **Indice** | assente O incompatibile (provider diverso, logic_version stantio) | stantio (mtime recente vs mtime file) | fresco e compatibile |
| **Provider embeddings** | — | irraggiungibile (probe fail) quando online=true | raggiungibile o online=false |
| **Server MCP** | — | non registrato OU richiede riavvio | registrato e funzionante |

**Regola:** exit 0 se TUTTI gli aspetti ≥ WARN; exit 1 se ≥1 CRITICO.

### DA-D5a: Probe provider (online-opt-in, idempotente, offline-safe)

- **Default (online=False):** verifica statica struttura (validation via `Settings.validate_backend()` odierno, zero rete, zero download GloVe).
- **Opt-in (--online):** `build_embedder(allow_download=False)` + embed di una sentinella breve (es. token-count non embedding). Path provider costruito via vehicle, **non** importazione diretta (Principio XI).
- **Fallback:** provider non raggiungibile → problema WARN (exit 0), nomina il rimedio («configura AZURE_OPENAI_API_KEY» o «avvia Ollama»).

### DA-D5b: Rilevamento stantio-MCP (best-effort, no fake)

Rilevamento forte cross-processo **non affidabile oggi** (il server non ha self-check di freschezza indice, il MCP è out-of-process):
- **Segnale debole:** indice stantio + MCP registrato → warn «MPC potrebbe servire un indice non fresco; riavvia con `claude restart --session <name>`» (consiglio, non certezza).
- **Segnale assente:** ✅ **riportato `unknown`**, non finto (Principio XII).
- **Debito promosso:** server self-check su storage Chroma writable/collection mtime (FEAT-011, non qui).

## Architettura

### Componenti

**Servizio puro** `services/doctor.py`:
- Entità frozen: `HealthReport` (quattro `AreaReport`) · `AreaReport` (stato per-area, lista `Problem`) · `Problem` (title/description/severity/remedies) · `ProviderProbe` (provider, reachable, error_message) · enum `ProblemSeverity` {OK, WARN, CRITICAL} · `MCP_RegistrationState` {registered, not_registered, unknown}
- Funzioni pure di diagnosi (per-area): `diagnose_config`/`diagnose_index`/`diagnose_provider`/`diagnose_mcp`
- Funzione di rollup: `rollup_verdict(health_report)` → `(overall_severity, exit_code, should_abort_here)`

**Formatter puro** `format_health_report(report, json=False)` in `cli/output.py`:
- Umano: scheda per-area con severity badge (✓/⚠/✗), problema + rimedi indentati
- JSON: schema `doctor.report/1` con tutti i campi strutturati

**Handler thin** in `cli/__main__.py`:
- Subcommand `doctor [--area {config,index,provider,mcp}] [--online] [--json]`
- Gate: `exit_code ≠ 0` se `overall_severity == CRITICAL`

### Helper nel composition root

`composition.py` esteso con funzioni **sola-lettura**:
- `load_manifest_state(index_dir, collection_name)` → manifest FEAT-009 letto (None se assente, nessuna eccezione)
- `build_provider_probe(settings, allow_download)` → `ProviderProbe` via `build_embedder(..., allow_download)` + embed sentinella
- `read_mcp_registration()` → scruta `~/.claude/` (Linux/Mac) o equivalent su Windows; stato registrazione letto best-effort
- `current_source_stats()` → mtime maggiore fra i file del manifest (indice stantio se > N giorni da config)

### Osservabilità

Evento `doctor` metrics-only:
```json
{
  "operation": "doctor",
  "areas_checked": ["config", "index", "provider", "mcp"],
  "problems_critical": 0,
  "problems_warn": 1,
  "exit_code": 0,
  "probe_online": false
}
```

Niente query, niente path, niente segreti.

## Scope e non-scope

**Incluso:**
- Quattro aree di diagnostica (config, indice, provider, MCP)
- Probe opzionale provider con sentinella
- Output umano + JSON
- Exit code gate

**Escluso (deferred):**
- Health check inside il server MCP (FEAT-011, self-check mtime)
- Remediation automatica (es. «fatto, riavvia»)
- Drill-down nel dettaglio dei chunk/query-latency (osservabilità FEAT-003)
- Interazione LLM («dimmi cosa fare», agente concierge FEAT-002)

## Esiti

### Test
- Root **1118 passed / 3 skipped** (packaging integration, attesi per snapshot-phase)
- Sertor **333 passed** (34 nuovi per doctor)
- Doctor-specifici: `test_doctor.py` 29 ✓ · `test_cli_doctor.py` 20 ✓ · `test_output_doctor.py` 15 ✓
- ruff clean

### Constitution
**PASS 12/12 + missione senza deroghe:**
- Principio X (host-agnosticità): sola lettura, nessun hard-coded path
- Principio XI (vehicle-only): composizione dal `build_provider_probe`, no diretto build_embedder; uscita via CLI vehicle
- Principio XII (fail-loud): rilevamento stantio-MCP riportato `unknown` (non finto)

### File

Nuovi:
- `src/sertor_core/services/doctor.py` (152 linee, puro)
- `tests/unit/test_doctor.py` (168 linee, 29 test)
- `tests/unit/test_cli_doctor.py` (142 linee, 20 test)
- `tests/unit/test_output_doctor.py` (86 linee, 15 test)

Modificati:
- `src/sertor_core/domain/errors.py` → nuova `DoctorCheckFailed` exception
- `src/sertor_core/composition.py` → `load_manifest_state`, `build_provider_probe`, `read_mcp_registration`, `current_source_stats`
- `src/sertor_core/cli/__main__.py` → subcommand `doctor`
- `src/sertor_core/cli/output.py` → `format_health_report`
- `packages/sertor/src/sertor_installer/configure.py` → `--check` delega a `sertor-rag doctor --json`
- Test estensione: `test_composition.py` (probe), `test_configure_check.py` (integration)

## Backlink

- [[valutazione-e-non-regressione]] — gemello vehicle di diagnostica (la first fornisce ground-truth, `doctor` ne ricava il verdetto operativo)
- [[mission-vision]] — Principio X reso operativo: host-agnosticità reale nella diagnostica post-install
- [[indexing-and-retrieval]] — FEAT-009 manifest che il doctor legge per freschezza indice
- [[mcp-server]] — registrazione/stato MCP diagnosticato

## Pendente

- **Collegamento wizard configure:** `sertor configure --check` odierno fa call subprocess a `sertor-rag doctor --json`. Flusso: wizard → conferm config → `doctor` run online → exit 0/1.
- **Integrazione ospite:** ospiti che ricevono l'installer (FEAT-009 fase 2) avranno `sertor-rag doctor` disponibile subito (vehicle CLI di distribuzione).

## Fix (branch 076 — 2026-06-23)

**Difetto:** il rilevamento della freschezza dell'indice in `freshness_from_manifest` usava solo l'mtime per marcare lo stato; dopo operazioni git (checkout, merge, pull) gli mtime dei file si ribumpavano a contenuto identico, causando **falsi positivi cronici** (`index_stale` riportato erroneamente).

**Allineamento:** l'indicizzatore incrementale FEAT-009 usa mtime come pre-filtro + conferma col content-hash (un file toccato ma invariato rimane UNCHANGED); il doctor non applicava questa logica, divergendo da DA-D2 («coerente col refresh incrementale»).

**Implementazione:**
- `current_source_stats` in `composition.py` estesa: calcola il content-hash **solo per i file con mtime cambiato**, riusando lo stesso pipeline dell'indicizzatore (`read_source` + `content_hash`). Non riscansiona disco, ridotto ai soli percorsi nel manifest (SC-007).
- `freshness_from_manifest` in `services/doctor.py` raffinata: marca `stale` **solo** se *mtime cambiato AND content-hash diverso* (o file sparito); se il hash corrisponde al registrato → rimane `pass` anche con mtime avanzato.
- Test di regressione: `test_freshness_touched_but_unchanged_not_stale` (il caso esatto di mtime avanzato/hash invariato che falsava positivi).

**Verifica:** bump manuale dell'mtime di un file indicizzato a contenuto invariato (via shell `touch`) → doctor rimane `index pass` (prima riportava `warn index_stale`).

## Note

La decisione DA-D5b di riportare `unknown` al posto di inventare uno stato non osservabile è un'istanza del **Principio XII** (non mentire); migliora il grounding dell'agente rispetto a un segnale finto. Il **self-check MCP a vera freschezza** rimane un debito promosso a FEAT-011 nell'epica E10 (enforcement-hooks).
