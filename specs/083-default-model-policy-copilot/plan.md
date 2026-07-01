# Implementation Plan — Default model-policy per i subagent Copilot CLI (E2-FEAT-015)

**Branch**: `083-default-model-policy-copilot` · **Spec**: `specs/083-default-model-policy-copilot/spec.md`
**Epica**: `sertor-cli` (E2) · **Data**: 2026-07-01 · **Constitution**: v1.4.0 (12 principi + gate Missione)

> **Nota di processo.** `.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> **ASSENTI** nel repo → parametri ricavati per convenzione dal branch (forma dai plan 074-082); nessun
> hook eseguito; git non eseguito (delega al `configuration-manager`). MCP `sertor-rag` interrogato
> (`find_symbol`/`search_code`/`who_calls` su `render_custom_agent` e i call-site) — **nessun errore tool**.

## Summary

Quando l'ospite è **GitHub Copilot CLI**, Sertor rende i 5 agenti Sertor-authored come `.agent.md` ma
**omette sempre** `model:` → modello implicito, variabilità non voluta tra installazioni. La feature
distribuisce a ciascuno dei 5 un **default ragionato** (meccanici → `claude-haiku-4.5`; scrittura/
sintesi → `claude-sonnet-4.6`) via il campo `model:` del frontmatter, da una **fonte unica versionata**
nel kit condiviso `sertor-install-kit`, con **fail-loud install-time** se il profilo non copre un agente
in ambito. **ADDITIVA / distribuzione pura, ZERO `sertor_core`** (Principio XI), zero LLM, path Claude
byte-identico.

## Technical Context

- **Linguaggio**: Python ≥ 3.11, stdlib-only nei pacchetti installer (kit senza dipendenza da `sertor-core`).
- **Pacchetti toccati**: `sertor-install-kit` (profilo + errore + renderer), `sertor` (concierge/wiki-curator
  + guardie), `sertor-flow` (i 3 governance).
- **`sertor-core`**: INVARIATO (RNF-8).
- **Testing**: pytest offline (nessuna rete/tenant), sui piani resi in `tmp_path` + unit sul renderer/profilo.
- **Ignoti (`NEEDS CLARIFICATION`)**: **nessuno**. Le 5 DA di requisiti sono risolte (§10 requirements);
  le 6 forche di *come* sono risolte in `research.md`.

## Constitution Check (PRE-design)

| # | Principio | Esito | Nota |
|---|---|---|---|
| I | Core a dipendenze verso l'interno | **PASS** | Core non toccato; feature solo installer. |
| II | Provider/backend intercambiabili, local-first | **PASS** | N/A; nessun provider/backend runtime. |
| III | Semplicità/YAGNI, unità piccole | **PASS** | Mappa costante minima, no file-data, no fallback struct; DRY (fonte unica). |
| IV | Errori espliciti, no null silenzioso | **PASS** | `ModelPolicyError` nominante; mai default silenzioso. |
| V | Testabilità/misura | **PASS** | Verificabilità offline; guardie riconciliate + real-asset guard. |
| VI | Idempotenza/determinismo/non-distruttività | **PASS** | Render deterministico da costante; `update_file_if_changed`; uninstall invariato. |
| VII | Leggibilità | **PASS** | Un solo artefatto per bump; docstring esplicite. |
| VIII | Config centralizzata (core) | **PASS** | N/A core; la policy È la config centralizzata dell'installer (fonte unica). |
| IX | Osservabilità runtime | **PASS** | N/A core; modello risolto visibile nel file depositato (RNF-3), nessun evento core. |
| X | Host-agnostico (portabilità) | **PASS** | Parità Claude/Copilot; Claude invariato, Copilot riceve default ragionato → host-agnosticità più reale. |
| XI | Consumo via vehicles, no core a runtime | **PASS** | Zero import `sertor_core`, zero LLM. |
| XII | Fail Loud, Fix the Cause | **PASS** | Fail-loud reale su profilo incompleto; disponibilità tenant onesta/documentale (no probe finto). |
| — | **Gate Missione (stella polare)** | **PASS** | Periferico al differenziatore code+doc, ma migliora **qualità e prevedibilità** del lavoro dell'agente ospite sul corpus fuso e rende reale la host-agnosticità (Principio X). Giustificato, non gonfiato. |

**Esito PRE: PASS 12/12 + Missione PASS.** Nessuna deroga. Complexity Tracking vuoto.

## Project Structure (artefatti di design)

```
specs/083-default-model-policy-copilot/
├─ spec.md            # input (COSA/PERCHÉ)
├─ plan.md            # questo file
├─ research.md        # Phase 0 — 6 forche DA-D risolte
├─ data-model.md      # Phase 1 — entità/simboli del kit + estensioni
├─ contracts/
│  └─ model-policy.md # Phase 1 — contratti offline (C1..C5)
└─ quickstart.md      # Phase 1 — verifica offline
```

## Phase 0 — Research (→ `research.md`)

Le 6 forche risolte, ancorate al codice reale (sintesi; dettaglio in `research.md`):

- **DA-D-1** Profilo = nuovo modulo `sertor_install_kit/model_policy.py`: **mappa costante Python** +
  `MODEL_POLICY_VERSION` + `IN_SCOPE_AGENTS` + `resolve_model()`; riesportato dal kit. Scartati file-dati
  e risolutore esterno.
- **DA-D-2** Innesto = estendere `render_custom_agent` sostituendo `include_model: bool` con
  `model: str | None` (sostituzione, mai eco); i 3 call-site derivano il nome dal basename `target_rel` e
  passano `resolve_model(name)`. Scartato il post-processing.
- **DA-D-3** Guardie riconciliate da «substring `haiku` assente» a «valore `model:` non è un **alias nudo**
  (`haiku`/`sonnet`/`opus`) e = policy-id»; helper `_model_value`; nuova real-asset guard sui 5 depositi;
  `_render_rag` parity allineato. **Sottigliezza:** `claude-haiku-4.5` contiene `haiku` → il vecchio assert
  darebbe falso positivo.
- **DA-D-4** Fail-loud = nuovo `ModelPolicyError(InstallerError)` nominante, materializzato al **build del
  piano** (prima di ogni scrittura → FR-009), stesso `resolve_model` usato dal render.
- **DA-D-5** Profilo NON è un asset → fuori dal sync-guard; importato non copiato → no drift per costruzione
  (scioglie R-5). Guardia di coerenza al posto: `IN_SCOPE_AGENTS` == 5 nomi depositati + pin dei 5 ID.
- **DA-D-6** Nessun fallback strutturale nel primo taglio; documentale/globale (YAGNI III).

## Phase 1 — Design (→ `data-model.md`, `contracts/`, `quickstart.md`)

**Modifiche pianificate (enumerate):**

*Kit `sertor-install-kit`:*
1. `model_policy.py` (NUOVO): `MODEL_POLICY_VERSION`, `_MODEL_POLICY`, `IN_SCOPE_AGENTS`, `resolve_model`.
2. `errors.py`: `+ ModelPolicyError(InstallerError)`.
3. `surfaces.py`: `render_custom_agent` firma `include_model: bool` → `model: str | None`; emissione
   sostitutiva; `_yaml_scalar`/`split_frontmatter` invariati.
4. `__init__.py`: re-export `resolve_model`/`MODEL_POLICY_VERSION`/`ModelPolicyError`.

*`sertor`:*
5. `install_rag.py`: `_render_rag_file` iniezione policy sul `.agent.md`; `build_rag_plan` validazione
   fail-loud (concierge, se copilot). `_apply_rag_upgrade` invariato (usa già `_render_rag_file`).
6. `install_wiki.py`: `_render_for_target` iniezione policy; `build_install_plan` validazione (wiki-curator).
7. `surfaces.py` shim: passa `model` (nessuna logica nuova).
8. Test riconciliati: `test_assets_copilot_guard.py`, `test_schema_copilot_frontmatter.py`,
   `test_assets_copilot_parity.py` (`_render_rag`) + **nuova real-asset guard** + **guardia di coerenza profilo**.

*`sertor-flow`:*
9. `install_governance.py`: `_render_for_target` iniezione policy; `build_governance_plan` validazione
   (i 3). Test di parità governance allineati se presenti.

*Documentazione utente (DoD, stesso step):*
10. `docs/install-copilot.md`: default per-agente + come cambiarlo (`/subagents`/edit frontmatter) +
    confine `speckit.*` + caveat disponibilità tenant.
11. `packages/sertor/docs/install.md`: tabella capability aggiornata (modello di default per agente).

*Backlog (tracciamento scope):*
12. **DICHIARATO (edit del flusso principale):** nuova voce `FEAT-NNN` nell'epica `sertor-cli`
    (`requirements/sertor-cli/epic.md`) per l'assegnazione di modello agli `speckit.*` (previa spike di
    verifica del supporto `model:` sui prompt-file). Non sepolto in `specs/`.

**Aggiornamento riferimento piano in `CLAUDE.md`** tra i marker SpecKit — a cura del flusso principale.

## Constitution Check (POST-design)

Rivalutato dopo il design. Nessuna nuova astrazione oltre la mappa costante + un errore + un parametro
di funzione: la superficie è additiva e minima. Fail-loud reso reale (XII), host-agnosticità rafforzata
(X), DRY per fonte unica importata (III), Claude isolato (VI/X). **Esito POST: PASS 12/12 + Missione
PASS.** Nessuna deroga. **Complexity Tracking: vuoto.**

## Complexity Tracking

*(vuoto — nessuna deviazione dai principi da giustificare.)*

## Definition of Done

- I 5 agenti Copilot ricevono `model:` di policy via `sertor install rag` + `sertor-flow install`, senza
  passi manuali (FR-014/CS-6).
- Fail-loud su profilo incompleto nomina l'agente mancante; 0 depositi parziali (FR-008/009/CS-5).
- Fonte unica versionata condivisa dai due pacchetti; 0 ID hardcoded per-agente (FR-005/006/CS-3).
- 0 leak di alias Claude nudo; path Claude byte-identico (FR-012/013/CS-2/CS-7).
- Idempotenza install/upgrade; uninstall invariato (FR-010/011/CS-4).
- Doc utente aggiornata nello stesso step (FR-015/CS-6); confine `speckit.*` promosso a backlog.
