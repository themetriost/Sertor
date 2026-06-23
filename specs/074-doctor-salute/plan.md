# Implementation Plan — `sertor-rag doctor` (E12-FEAT-001)

**Branch**: `074-doctor-salute` · **Spec**: [`spec.md`](spec.md) · **Data**: 2026-06-23
**Input**: spec approvata (8 US, 18 FR, 12 SC) + `requirements/usabilita/sertor-rag-doctor/requirements.md`
+ costituzione v1.4.0.

> **Nota di processo.** `.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> sono **ASSENTI** nel repo: parametri ricavati per convenzione dal branch (forma da `073`/`072`).
> Nessun hook SpecKit eseguito. MCP `sertor-rag` interrogato per ancorare il design
> (`find_symbol`/`search_code`/`Read`) — **nessun errore tool** (tutti i lookup risolti: `validate_backend`,
> `_probe_live`, `collection_name`, `build_indexed_docs`, `build_embedder`, `emit_eval_event`,
> `enable_observability`, `LiveCheckOutcome`).

## Riassunto

`sertor-rag doctor` è la **primitiva deterministica «ha funzionato?»**: in un comando riporta la salute
di quattro aree (config/env · provider embeddings · indice · MCP) con esito pass/warn/fail, causa +
rimedio per ogni problema, esito umano e `--json` a schema stabile, ed exit code non-zero se un check
critico fallisce. **Sola lettura, nessun LLM** (confine D↔N). La feature chiude anche il debito
*deferred* di `sertor configure --check` (scope esteso al pacchetto `sertor`), che diventa un
sottoinsieme config che invoca `doctor`.

Architettura: comando **vehicle** (Principio XI) nel CLI `sertor-rag`, un **servizio puro** di diagnosi
nel core (`services/doctor.py`), formatter puri in `cli/output.py`. Riusa i segnali **già esistenti**
(`validate_backend()`, `IndexManifest`, `.mcp.json`, `build_embedder`) — nessuna nuova porta, **nessuna
nuova dipendenza** per i check statici. Additivo: a comando non invocato il comportamento è identico
(SC-012).

## Technical Context

- **Linguaggio/runtime:** Python ≥ 3.11.
- **Pacchetti:** `sertor-core` (comando + servizio + formatter) · `sertor` (wizard `_probe_live`).
- **Dipendenze nuove:** nessuna (stdlib: `json`, `pathlib`, `os`; `sqlite3` via `IndexManifest`).
- **Storage (sola lettura):** `<index_dir>/index_manifest.sqlite` (presenza+freschezza), `.mcp.json`
  (registrazione MCP), env/`.env` via `Settings`.
- **Vehicle:** factory `build_embedder` (probe), `Settings.validate_backend` (env), `enable_observability`.
- **Test:** offline/deterministici; servizio puro con input sintetici; handler con core/runner mockati.
- **Performance:** check statici in tempo trascurabile (RNF-1); freschezza = `os.stat` sui soli file
  noti, **nessun re-scan/re-hash** del repo.
- **Ignoti (NEEDS CLARIFICATION):** nessuno residuo — DA-D1/D2/D3 chiuse in spec; **DA-D4** codificata
  (research D2); **DA-D5** risolta (research D3/D4).

## Constitution Check — Phase 0 (pre-design) e Phase 1 (post-design)

Tabella unica: la valutazione **non cambia** tra pre e post design (il design non introduce deroghe).

| Principio | Pre | Post | Nota |
|-----------|-----|------|------|
| I — core verso l'interno | PASS | PASS | comando = vehicle; servizio puro nel core, testabile come libreria; nessun SDK importato |
| II — provider dietro boundary; local-first | PASS | PASS | probe via `EmbeddingProvider`/factory; statici girano in locale |
| III — YAGNI, unità piccole | PASS | PASS | nessuna porta/dipendenza nuova; flag, non env (no knob inutile); funzioni pure piccole |
| IV — errori espliciti | PASS | PASS | gate critico → `DoctorCheckFailed` (exit 1); degradi (offline/manifest assente) **segnalati**, mai null silenzioso |
| V — testabilità/misure | PASS | PASS | servizio puro F.I.R.S.T.; un caso per area verificabile (SC-002) |
| VI — idempotenza/non-distruttività | PASS | PASS | sola lettura in ogni scenario (FR-014/SC-009) |
| VII — leggibilità | PASS | PASS | vocabolario di dominio (diagnose/probe/freshness), guard-clause |
| VIII — config centralizzata | PASS | PASS | tutto da `Settings`/`validate_backend()`; zero default hardcoded nel comando |
| IX — osservabilità | PASS | PASS | evento `doctor` metrics-only (contract event-doctor.md) |
| X — host-agnostico | PASS | PASS | nessuna assunzione sull'ospite; gira su qualunque progetto |
| XI — vehicles | PASS | PASS | CLI + `build_*`; `configure --check` invoca `doctor` in subprocess; nessuna scorciatoia di import |
| XII — fail loud, fix the cause | PASS | PASS | probe riporta il motivo; stantio MCP `unknown` onesto (non finto); nessuna soppressione |
| **Allineamento alla missione** | **PASS** | **PASS** | `doctor` rende **reale** la host-agnosticità (X): un agente verifica da solo la salute su un ospite qualunque — prerequisito perché il retrieval fuso code+doc sia davvero fruibile. Periferico al differenziatore ma **abilitante** l'adozione/portabilità; il core resta deterministico (l'intelligenza è nelle skill). |

**Esito: PASS 12/12 + missione PASS (pre e post-design), nessuna deroga, nessun Complexity Tracking.**

## Architettura

### Dove vive `doctor`

```
src/sertor_core/
  cli/__main__.py        + _add_doctor_parser(sub)  → `doctor` (flag --online/--area/--json/--corpus)
                         + _cmd_doctor(args)          → handler thin (risolve segnali, chiama servizio, formatta, gate)
  cli/output.py          + format_health_report(report, *, json)   → resa pura umano/JSON (schema doctor.report/1)
  services/doctor.py     NUOVO: entità di esito (HealthReport/AreaReport/Problem/…) + funzioni pure
                         (check_config/check_provider/freshness_from_manifest/check_mcp/assemble)
                         + DoctorCheckFailed (errore di dominio, se non co-locato in errors.py)
  domain/errors.py       + DoctorCheckFailed(SertorError)   (gate exit, gemello RegressionDetected)
  composition.py         + helper sottili per i side-effect del handler:
                           - build_provider_probe(settings) → ProviderProbe   (build_embedder + embed(sentinel))
                           - read_mcp_registration(root)    → bool            (legge .mcp.json)
                           - current_source_stats(state, root) → [(path, mtime)]  (os.stat sui file noti)
```

**Separazione logica↔resa.** `services/doctor.py` contiene la **decisione** (funzioni pure: dai segnali
→ `AreaReport`/`HealthReport`, severità, rollup, exit code). `cli/output.py::format_health_report` è la
**resa** (umano vs JSON), invariante di equivalenza informativa come gli altri formatter. I *side-effect*
(leggere `.mcp.json`, `os.stat`, costruire l'embedder) vivono in helper sottili del handler/composition,
non nelle funzioni di decisione → tutto il giudizio è testabile offline.

### Entità di esito

Vedi [`data-model.md`](data-model.md): `Severity`/`AreaStatus`/`AreaName`/`ProbeStatus` (enum),
`Problem`/`AreaReport`/`HealthReport`/`ProviderProbe` (frozen). Schema JSON stabile `doctor.report/1`.

### DA-D4 — criteri critico/warn (deterministico)

Codificato come funzione pura (research D2): **CRITICO** (exit ≠ 0) = env mancante **o** indice
assente/incompatibile; **WARN** (exit 0) = indice stantio, MCP non registrato, provider irraggiungibile
(probe). L'area `provider` (statico) eredita la criticità dell'env (stesse chiavi, fonte unica
`validate_backend()` — nessuna lista duplicata).

### DA-D5 — risolta (research D3/D4)

- **Probe provider (D3):** `build_embedder(settings, allow_download=False)` + `embed([sentinel])` su una
  stringa minima costante. Minimale, non-indicizzante (nessun upsert), offline-safe (saltato senza
  `--online`), non scarica mai GloVe. Testa il **path reale** attraverso il vehicle/factory senza
  accoppiare il comando a SDK/URL specifici per provider (Principio I/II). Motivo d'errore scrubbed.
- **Stantio-dopo-reindex MCP (D4):** best-effort derivato dai segnali già disponibili (indice stantio
  **e** MCP registrato → warn «riavvia il server»); la rilevazione *forte* cross-processo non esiste
  oggi → riportata come `unknown`, **non** sintetizzata in modo falsamente preciso (Principio XII).
  Debito forte promosso a osservabilità/MCP (vedi §Scope).

### Wiring `configure --check` (pacchetto `sertor`)

`_probe_live` (`configure.py:369`) cambia il comando da `sertor-rag check` a
`sertor-rag doctor --area config --json`; mapping exit→`LiveCheckOutcome` invariato nella forma
(degrado onesto preservato). Vedi [`contracts/configure-check.md`](contracts/configure-check.md).
`configure` senza `--check` resta byte-identico (FR-017/SC-011).

### Osservabilità

Evento `doctor` metrics-only emesso dal handler (gemello `eval`); `enable_observability(settings)`
chiamato come negli altri handler. Vedi [`contracts/event-doctor.md`](contracts/event-doctor.md).

## File toccati (enumerazione)

### `sertor-core` (comando `doctor`)
- `src/sertor_core/services/doctor.py` — **NUOVO**: entità di esito + funzioni pure di diagnosi.
- `src/sertor_core/cli/__main__.py` — `_add_doctor_parser` + `_cmd_doctor` (handler thin) + import.
- `src/sertor_core/cli/output.py` — `format_health_report` (pura, umano/JSON).
- `src/sertor_core/domain/errors.py` — `DoctorCheckFailed(SertorError)` (gate exit).
- `src/sertor_core/composition.py` — `build_provider_probe` + `read_mcp_registration` +
  `current_source_stats` (helper side-effect sottili, vehicle).
- `tests/unit/test_doctor.py` — **NUOVO**: funzioni pure (severità, rollup, freschezza, criteri DA-D4,
  exit code), per area; offline.
- `tests/unit/test_cli_doctor.py` — **NUOVO**: handler con core mockato (umano/JSON, exit 0/1,
  `--online` skip vs probe, `--area config`, redazione segreti); stile `test_cli_search`.
- (eventuale) `tests/unit/test_output.py` — estensione per `format_health_report` (equivalenza umano/JSON).

### `sertor` (wizard `configure --check`)
- `packages/sertor/src/sertor_installer/configure.py` — `_probe_live`: comando → `doctor --area config
  --json`, mapping esito invariato; degrado onesto preservato.
- `packages/sertor/tests/...test_configure.py` (o test del probe) — `FakeCommandRunner` per i quattro
  esiti + regression guard «senza `--check` nessuna invocazione».

### Documentazione / debito
- Nota nel backlog `requirements/sertor-cli/epic.md` (owner E2): se in futuro il probe diventasse
  governato da un env (`SERTOR_DOCTOR_*`), va promosso al template `.env` dell'installer — **oggi è un
  flag CLI, nessun knob nuovo** (SC-012). Promozione tracciata, non appesa in `specs/`.
- `requirements/usabilita/epic.md` / `wiki/syntheses/roadmap.md`: «stantio MCP forte» e «stantio su file
  nuovi» promossi come Could/roadmap (vedi §Scope).

## Tracciamento dello scope (Out-of-Scope promossi, non appesi)

| Voce rinviata | Casa durevole |
|---------------|---------------|
| Skill consumatrici (guided-setup, search-diagnose) | **FEAT-002 / E12** (già a backlog `requirements/usabilita/epic.md`) |
| Auto-fix / riparazione guidata | **FEAT-002 guided-setup** (E12) |
| Spiegazione conversazionale dell'esito | skill dell'ospite (E12 FEAT-007/009) |
| Stantio-dopo-reindex MCP **forte** (handshake col server) | debito → osservabilità/server MCP (FEAT-012 / server) — roadmap *Nuove funzionalità da discutere* |
| Stantio su «file nuovi mai indicizzati» | Could → riga `FEAT-NNN`/roadmap E12 (lo stantio MVP copre modifiche/delete dei file noti) |
| Knob env del probe (se mai introdotto) | template `.env` installer (owner E2) — oggi **non** introdotto |
| `configure --check` debito *deferred* | **chiuso qui** (US8, scope esteso a `sertor`), già tracciato nell'epica `sertor-cli` |

Nessun rinvio reale vive **solo** dentro `specs/`.

## Rischi / aperti per `/speckit-tasks`

- **R-1 (freschezza, mitigato):** lo stantio è `warn` mtime-only sui file noti → niente falsi positivi
  bloccanti su `sources` larghi (SC-007); il delta esatto resta al refresh incrementale/osservabilità.
- **R-2 (probe, mitigato):** una sola `embed` su stringa corta, opt-in, `allow_download=False`, nessun
  upsert (SC-008).
- **Aperto minore:** ordine di stampa/etichette umane = dettaglio di resa (formatter), nessuna ambiguità
  di scope. Nessun `NEEDS CLARIFICATION` residuo.
