# Implementation Plan — Cattura memoria su GitHub Copilot CLI (FEAT-008)

**Branch**: `073-cattura-copilot-cli` · **Data**: 2026-06-22 · **Epica**: memoria-conversazioni
**Spec**: [`spec.md`](spec.md) · **Requisiti**: `requirements/memoria-conversazioni/cattura-multi-assistente/requirements.md`

## Summary

Aggiunge il **secondo adapter di cattura transcript** — GitHub Copilot CLI — dietro la porta esistente
`TranscriptCaptureAdapter` (8ª porta). L'MVP della memoria conversazioni è host-agnostico in tutto il
tier (archivio FEAT-001, full-text FEAT-002, semantica FEAT-004, distillazione FEAT-003) **tranne** la
cattura, che oggi ha un solo adapter `claude-code`. L'hook `SessionEnd` distribuito su ospiti Copilot
da FEAT-009 è **inerte** perché manca la sorgente Copilot. Questa feature la fornisce: un componente
host-specifico che legge `~/.copilot/session-state/<uuid>/events.jsonl`, ne estrae i soli turni
user/assistant e associa ogni sessione al progetto via cwd/gitRoot del suo `session.start`. Una volta
presente, **l'intero tier a valle diventa operativo su Copilot senza modifiche**.

Cambiamento **additivo**: nessuna nuova porta, nessun nuovo motore, nessun tocco al tier. A leva spenta
(`SERTOR_MEMORY=false`, default) costo/comportamento identici a oggi (gate `memory_enabled` → adapter
non costruito, import lazy). Default adapter invariato (`claude-code`, non-regressione).

## Technical Context

- **Linguaggio:** Python ≥ 3.11. **Build/test:** `uv`, `pytest` (marker `not cloud`), `ruff`.
- **Riuso (no nuove dipendenze, RNF-7):** porta `TranscriptCaptureAdapter` ed entità
  `SessionRef`/`TranscriptTurn`/`TranscriptContent` (`domain/memory.py`), adapter di riferimento
  `claude_code.py`, selettore `composition.py#build_capture_adapter`, manopole memoria in `Settings`,
  `log_event`. **stdlib-only** nel corpo dell'adapter (`json`/`logging`/`os`/`datetime`/`pathlib`).
- **Determinismo/local-first (NFR-002):** l'adapter legge solo file locali; zero rete; nessun cloud-sync,
  nessun `session-store.db`. Testabile con una directory di fixture senza Copilot installato (RNF-4).
- **Accesso via vehicle (Principio XI):** cattura esercitata via CLI `sertor-rag memory archive` / hook
  `SessionEnd`; mai importando `sertor_core` a runtime fuori dai test.
- **Decisioni di scope (ricognizione empirica Copilot CLI 1.0.63, 2026-06-22) — fissate, non riaperte:**
  sorgente = `events.jsonl`; turni = solo `user.message`/`assistant.message` (testo = `data.content`);
  associazione = cwd/gitRoot di `session.start`; nome adapter = `copilot-cli`; legacy
  `history-session-state/` ignorata; cloud-sync = sola documentazione.
- **Ignoti residui:** nessun `NEEDS CLARIFICATION`. Le forche residue DA-CM-1..4 sono chiuse in
  [`research.md`](research.md): testo = `data.content` (no streaming); progetto indeterminabile = skip;
  override = `SERTOR_MEMORY_COPILOT_SESSION_DIR`; filtro = path-containment normalizzato.

## Constitution Check — PRE-design

| # | Principio | Esito | Motivo |
|---|-----------|-------|--------|
| I | Core dipendenze verso l'interno | **PASS** | adapter concreto in `adapters/`, dietro la porta `TranscriptCaptureAdapter`; nessun SDK nel dominio; scelta concreta solo in `composition` |
| II | Provider/backend dietro boundary; local-first | **PASS** | la sorgente di cattura è guidata da config (`SERTOR_MEMORY_ADAPTER`); local-first (solo file locali, no rete) |
| III | YAGNI, unità piccole | **PASS** | NESSUNA nuova porta (8ª riusata); NESSUN nuovo motore; nessun marcatore «unknown-project» (skip — DA-CM-2); helper piccoli/puri come Claude |
| IV | Errori espliciti, niente null silenzioso | **PASS** | valore adapter ignoto → `ConfigError` azionabile (riuso); degradazione **segnalata** con warning, mai `None` silenzioso per assenza |
| V | Testabilità e misura | **PASS** | adapter testabile con fixture (events.jsonl + session.start) senza Copilot/rete (RNF-4); SC-001 verificabile (#archiviate = N) |
| VI | Idempotenza/determinismo/non-distruttività | **PASS** | `session_key` = UUID stabile → idempotenza ereditata (REQ-011); sorgente read-only; install≠run |
| VII | Leggibilità | **PASS** | vocabolario di dominio (session/turn/capture); guard clause; mapping evento→ruolo in un dict nominato |
| VIII | Config centralizzata | **PASS** | `copilot_session_dir` solo in `Settings` (default qui); selettore riusa `SERTOR_MEMORY_ADAPTER` |
| IX | Osservabilità | **PASS** | eventi metrics-only `memory_capture_*` (parità Claude) + nuovo `_session_unassociated`; mai testo transcript |
| X | Host-agnostico | **PASS** | TUTTA la host-specificità Copilot (percorsi, formato, associazione) confinata nell'adapter; tier a valle invariato (REQ-016) |
| XI | Consumo via vehicles | **PASS** | cattura via CLI `memory archive` / hook; import diretto del core solo nei test (eccezione) |
| XII | Fail loud, fix the cause | **PASS** | degradazione **segnalata** (warning su sorgente assente / riga invalida / progetto indeterminabile); nessuna soppressione silenziosa; nessuna misattribuzione |
| — | **Allineamento alla missione** | **PASS** | porta la **qualità del contesto reso all'agente nel tempo** (auto-conoscenza portabile) al **secondo assistente ospite** senza duplicare il tier; è host-agnosticità (Principio X) resa reale per la memoria, non un concern periferico |

**Esito PRE: PASS 12/12 + missione PASS.** Nessuna deroga.

## Project Structure (artefatti nuovi/toccati)

```
src/sertor_core/
  adapters/capture/copilot_cli.py    # NUOVO: CopilotCliCaptureAdapter (kind="copilot-cli"),
                                      #        stdlib-only, best-effort non-fatale; rispecchia claude_code.py
  config/settings.py                 # TOCCATO: campo copilot_session_dir + lettura
                                      #          SERTOR_MEMORY_COPILOT_SESSION_DIR in load()
  composition.py                     # TOCCATO: "copilot-cli" in _VALID_MEMORY_ADAPTERS;
                                      #          dispatch su settings.memory_adapter in build_capture_adapter (import lazy)
tests/unit/test_copilot_capture.py   # NUOVO: discovery/associazione/turni/non-fatale/source-absent (fixture)
tests/unit/test_composition.py       # TOCCATO: copilot-cli → CopilotCliCaptureAdapter; default invariato; valore ignoto → ConfigError
tests/unit/test_settings.py          # TOCCATO: default copilot_session_dir + override env
specs/073-cattura-copilot-cli/       # spec, research, data-model, contracts, quickstart, plan, (tasks)
```

`sertor-core` **invariato** fuori dai punti elencati: `domain/memory.py`, `domain/ports.py`,
`adapters/capture/claude_code.py`, l'intero tier (`services/memory_*`, `MemoryArchive`,
distillazione) **non toccati** (REQ-016/017, RNF-005).

## Phase 0 — Research

Vedi [`research.md`](research.md). Forche residue chiuse: **DA-CM-1** testo = `data.content` (nessuno
streaming/delta; `transformedContent` scartato) · **DA-CM-2** progetto indeterminabile = **skip** +
warning (no marcatore) · **DA-CM-3** override = **`SERTOR_MEMORY_COPILOT_SESSION_DIR`** (mirror di
`SERTOR_MEMORY_CLAUDE_PROJECTS_DIR`) · **DA-CM-4** filtro = **path-containment normalizzato**
(cwd/gitRoot antenato-o-uguale al progetto, case-insensitive su Windows).

## Phase 1 — Design

- [`data-model.md`](data-model.md): entità riusate invariate, nuovo adapter concreto + helper puri,
  campo Settings, selettore esteso, eventi di osservabilità, confini.
- [`contracts/copilot-capture.md`](contracts/copilot-capture.md): contratto
  `memory.capture.copilot/1` (porta riusata + `list_sessions`/`read_session` + vehicle CLI/hook +
  invarianti).
- [`quickstart.md`](quickstart.md): abilitazione a strati, cattura, recupero alla pari di Claude,
  sorgente assente, privacy/cloud-sync, verifica offline.

## Phase 2 — Implementazione (ordine, per `/speckit-tasks`)

1. **Settings** — campo `copilot_session_dir` (default `~/.copilot/session-state`) + lettura
   `SERTOR_MEMORY_COPILOT_SESSION_DIR` in `load()` (mirror esatto di `claude_projects_dir`).
2. **Adapter** `adapters/capture/copilot_cli.py` — `CopilotCliCaptureAdapter` (`kind="copilot-cli"`):
   `list_sessions` (enumera UUID → `session.start` cwd/gitRoot → `_paths_match` → `SessionRef`),
   `read_session` (events.jsonl → turni `user`/`assistant` via `_turn_from_event`), helper puri
   (`_session_context`, `_paths_match`, `_parse_line`, `_parse_timestamp`); eventi `memory_capture_*`;
   degradazione non-fatale ovunque. Docstring dichiara la versione Copilot CLI verificata (NFR-006).
3. **Composition** — `"copilot-cli"` in `_VALID_MEMORY_ADAPTERS`; dispatch su `settings.memory_adapter`
   in `build_capture_adapter` con import **lazy** del nuovo adapter; ramo `claude-code` invariato.
4. **Test** — `test_copilot_capture.py` (fixture events.jsonl con mix di eventi + più progetti);
   estensioni a `test_composition.py` (dispatch + default + valore ignoto) e `test_settings.py`
   (default/override). Offline, `not cloud`.

## Consumatori / punti toccati (enumerati)

1. `config/settings.py` — 1 campo nuovo + 1 lettura env in `load()`.
2. `adapters/capture/copilot_cli.py` — **nuovo** (adapter + helper).
3. `composition.py` — `_VALID_MEMORY_ADAPTERS` += `"copilot-cli"`; ramo di dispatch in
   `build_capture_adapter` (import lazy).
4. `tests/unit/` — nuovo `test_copilot_capture.py` + estensioni a `test_composition.py`/`test_settings.py`.
5. **Debito di completamento (NON in questa feature, promosso):** distribuzione del valore
   `SERTOR_MEMORY_ADAPTER=copilot-cli` (+ `SERTOR_MEMORY_COPILOT_SESSION_DIR`) nel template `.env` di
   `sertor install` su host Copilot → **FEAT-009** (owner `sertor install`), già nel backlog d'epica
   (`requirements/memoria-conversazioni/epic.md`). La feature non è *done* finché un ospite Copilot non
   riceve il valore adapter per il percorso d'installazione (regola «feature completa = installabile»).

## Out of Scope (ribadito)

- **Cablaggio `SERTOR_MEMORY_ADAPTER=copilot-cli` nel template `.env` dell'installer** → debito di
  completamento, **cross-ref FEAT-009** (NON qui).
- **Modifiche al tier a valle** (archivio/full-text/semantica/distillazione): la feature lo **alimenta**,
  non lo tocca.
- **Altri assistenti** (Codex, ecc.): estendibili col medesimo pattern, fuori da questa feature.
- **Sede legacy `~/.copilot/history-session-state/`** e **fonte alternativa `session.db`**: non lette.
- **Interazione col cloud-sync di Copilot**: Sertor legge solo il locale.

## Constitution Check — POST-design

Rivalutato dopo Phase 1: il design non introduce alcun nuovo accoppiamento. Un solo componente concreto
dietro la porta esistente (I/III); nessuna nuova porta, nessun nuovo motore, nessun tocco al tier
(III/REQ-016/017, RNF-005). Il dispatch gated + import lazy preserva l'additività e il default invariato
(I/RNF-003, SC-010/011). La host-specificità è interamente confinata nell'adapter (X). La politica di
skip su progetto indeterminabile evita la misattribuzione e **segnala** con warning (IV/XII), senza
introdurre stato artificiale (III). Gli eventi restano metrics-only, mai testo (IX). La cattura resta
local-first (II, NFR-002) e si esercita via vehicle (XI). Allineamento alla missione confermato: estende
la qualità del contesto reso all'agente al secondo assistente, riusando l'intero tier.

**Esito POST: PASS 12/12 + missione PASS.** Nessuna deroga, nessun Complexity Tracking necessario.

## Note di processo

- `setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md` **ASSENTI** nel repo → parametri ricavati
  per convenzione dal branch `073-cattura-copilot-cli` (forma da `072`). Nessun hook eseguito; nessun
  comando git (delega al `configuration-manager`).
- MCP `sertor-rag` interrogato per l'ancoraggio (`find_symbol build_capture_adapter`/`SessionRef`,
  `search_code` sulla porta `TranscriptCaptureAdapter`): **nessun errore tool**.
- Riferimento al piano aggiornato in `CLAUDE.md` tra i marker `<!-- SPECKIT START/END -->`.
