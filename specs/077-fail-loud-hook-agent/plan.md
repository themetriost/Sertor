# Implementation Plan — Fail-loud breadcrumb negli hook + fallback «asset mancante → STOP» negli agent

**Branch**: `077-fail-loud-hook-agent` · **Spec**: `specs/077-fail-loud-hook-agent/spec.md` · **Data**: 2026-06-29
**Feature**: E10-FEAT-019 (epica **debito-tecnico**) · **Status**: Plan completo (research + design)

> **Nota di processo.** `.specify/scripts/.../setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> **ASSENTI** nel repo → parametri ricavati per convenzione dal branch (forma da `074`/`075`/`076`).
> Nessun hook SpecKit eseguito. MCP `sertor-rag` interrogato (`search_code` su
> `rag-health.json`/`RUNTIME_IGNORES`) **senza errori tool**; ancoraggio completato con `Read`/`git`.

## Summary

La feature realizza il **Principio XII «Fail Loud, Fix the Cause»** su due classi di asset first-party
distribuiti agli ospiti, **senza toccare `sertor_core`** né alcun comando/vehicle (additiva,
host-facing). **(1)** I 4 hook PowerShell in scope (`memory-capture`, `rag-freshness` sui soli path
catastrofici, `wiki-pending-check`, `version-check`) smettono di inghiottire in silenzio i fallimenti:
sui path degradati scrivono un **breadcrumb ispezionabile** `.sertor/.last-hook-error` (JSON
`hook.error/1`, sovrascritto = «ultimo errore», + nota stderr), gemello di `.sertor/.rag-health.json`,
restando **non-fatali** (`exit 0` sempre, scrittura best-effort). **(2)** I 3 body agent (`concierge`,
`wiki-curator`, `requirements-analyst`) ricevono la regola uniforme **«asset mancante → STOP e
segnala»** in testo host-agnostico byte-identico Claude↔Copilot. Più: **copie dogfood** ri-sincronizzate
e **guardie anti-regressione** (lint breadcrumb + assert fallback + sync rag dogfood + RUNTIME_IGNORES).

## Technical Context

- **Linguaggio/superficie**: asset PowerShell (`.ps1`) + body markdown agent; test Python (pytest,
  stdlib + `iter_asset_dir`). **Nessun** runtime di core toccato.
- **Convenzione breadcrumb**: funzione inline `Write-HookBreadcrumb` **byte-identica** nei 4 hook (non
  un file condiviso — research D-1), schema file `hook.error/1` (contract).
- **Confine D↔N**: gli hook restano **meccanici** (scrivono una traccia, niente ragionamento, **mai un
  LLM**, mai import di `sertor_core` — Principio XI); il fallback agent è **giudizio** del body (testo).
- **Lifecycle/installer**: unica modifica al kit = **una riga** in `RUNTIME_IGNORES`. Nessun nuovo
  `ArtifactKind`/`WriteStrategy`/`Surface`/seam.
- **Cross-pacchetto**: asset in `sertor` (4 hook + `concierge` + `wiki-curator`) e `sertor-flow`
  (`requirements-analyst`). `sertor-flow` resta **senza** dipendenza da `sertor-core`.
- **Ignoti**: nessuno (`NEEDS CLARIFICATION` = 0). Le 3 forche di prodotto sono RISOLTE in spec; le 2
  forche di plan (DA-D-r1/r2) sono risolte in `research.md` (+ scoperta D-5 sul sync rag dogfood).

## Constitution Check (PRE-design)

| # | Principio | Esito | Note |
|---|---|---|---|
| I | Libreria importabile / Clean Arch | PASS | `sertor_core` invariato; nessun import dagli hook. |
| II | Dettagli sostituibili / no lock-in | PASS | hook = wrapper sottili sui vehicle; nessun nuovo accoppiamento. |
| III | YAGNI / additività | PASS | inline function + 1 riga ignore + guardie; nessuna astrazione nuova. |
| IV | Errori chiari | PASS | breadcrumb = traccia ispezionabile esplicita; nota stderr. |
| V | Misurabilità | PASS | guardie deterministiche (lint + assert + byte-identità). |
| VI | Non distruttività | PASS | sovrascrive solo il proprio file runtime; mai asset/dato utente. |
| VII | Idempotenza | PASS | breadcrumb «ultimo errore» sovrascritto; no-op gated non scrive. |
| VIII | Local-first / offline | PASS | scrittura file locale; guardie offline. |
| IX | Privacy | PASS | `reason` secret-free (hook-local o scrubbato alla fonte). |
| X | Host-agnostico | PASS | nessun path hardcodato; parità Claude↔Copilot; body byte-identici. |
| XI | Accesso solo via vehicles | PASS | gli hook NON importano `sertor_core`, NON chiamano un LLM. |
| XII | **Fail Loud, Fix the Cause** | PASS | **è esattamente ciò che la feature realizza.** |
| — | **Allineamento alla missione** | PASS | rende **visibile** ogni rottura del macchinario che degraderebbe il contesto reso all'agente (anti dogfooding cieco) — protegge la stella polare. |

**Esito PRE: PASS 12/12 + missione PASS.** Nessuna deroga. Complexity Tracking **vuoto**.

## Project Structure (artefatti toccati)

```
packages/sertor/src/sertor_installer/assets/
  rag/hooks/memory-capture.ps1        # + Write-HookBreadcrumb + 1 punto breadcrumb
  rag/hooks/rag-freshness.ps1         # + Write-HookBreadcrumb + 3 punti (spawn/index/worker-crash)
  rag/hooks/version-check.ps1         # + Write-HookBreadcrumb + 1 punto (catch catastrofico)
  claude/hooks/wiki-pending-check.ps1 # + Write-HookBreadcrumb + 1 punto (scan fallita)
  rag/agents/concierge.md             # + fallback «guided-setup mancante → STOP»
  claude/agents/wiki-curator.md       # + fallback «wiki-playbook/ops mancante → STOP»
packages/sertor-flow/src/sertor_flow/assets/claude/agents/requirements-analyst.md
                                      # + fallback «requirements mancante → STOP»
packages/sertor-install-kit/src/sertor_install_kit/gitignore_append.py
                                      # RUNTIME_IGNORES += ".sertor/.last-hook-error"
.claude/hooks/{memory-capture,rag-freshness,version-check}.ps1   # ri-sync dogfood (manuale)
.claude/hooks/wiki-pending-check.ps1 · .claude/agents/wiki-curator.md   # ri-sync via sync.py
.claude/agents/requirements-analyst.md                            # ri-sync via sertor-flow sync

# Guardie nuove
packages/sertor/tests/test_assets_hook_breadcrumb.py   # Guardia A (lint breadcrumb)
packages/sertor/tests/test_assets_agent_fallback.py    # Guardia B (assert fallback 3 body)
tests/unit/test_assets_rag_dogfood_sync.py             # Guardia C (sync rag dogfood, scoperta D-5)
# Guardia D = assert in un test install_rag esistente: ".sertor/.last-hook-error" in RUNTIME_IGNORES
```

## Phase 0 — Research (completata → `research.md`)
Risolte DA-D-r1 (punti di scrittura + convenzione inline + no-op gated per hook) e DA-D-r2 (forma delle
guardie + parità riusata). Scoperta **D-5**: i 3 hook **rag** dogfood `.claude/hooks/` non sono coperti
da alcuna guardia di sync → nuova Guardia C dedicata.

## Phase 1 — Design (completata → data-model, contracts, quickstart)
- `data-model.md`: entità breadcrumb (file runtime), convenzione `Write-HookBreadcrumb`, convenzione
  fallback agent, classificazione hook, lifecycle additivo.
- `contracts/last-hook-error-state.md`: schema `hook.error/1` + invarianti (sovrascrittura, no-op gated,
  best-effort, secret-free, non versionato).
- `contracts/anti-regression-guard.md`: Guardie A/B/C/D + parità riusata.
- `quickstart.md`: verifiche manuali/offline.

## Constitution Check (POST-design)
Il design non introduce astrazioni nuove (funzione inline, 1 riga ignore, guardie statiche), nessun
import di core, nessun LLM, nessun path hardcodato. **Esito POST: invariato — PASS 12/12 + missione
PASS, nessuna deroga.** Complexity Tracking vuoto.

## Ordine di implementazione suggerito (per `/speckit-tasks`)
1. Definire `Write-HookBreadcrumb` (funzione inline) + integrare i punti breadcrumb nei 4 hook canonici
   (memory-capture, rag-freshness ×3, wiki-pending-check, version-check) — research D-2.
2. Aggiungere la frase di fallback host-agnostica ai 3 body agent (token `STOP` + asset + «cannot be
   resolved or read») — research D-4 Guardia B.
3. `RUNTIME_IGNORES += ".sertor/.last-hook-error"` (kit) + assert gemello in un test install_rag.
4. Guardie A/B/C (con meta-test positivi/negativi, anti-vacuità).
5. Ri-sync dogfood: `python -m sertor_installer.sync` (wiki-pending-check + wiki-curator) + copia manuale
   dei 3 hook rag in `.claude/hooks/`; ri-sync `requirements-analyst` (sertor-flow).
6. Suite verde: nuove guardie + `test_assets_copilot_parity` + `test_assets_sync` (root e flow) +
   `test_assets_hook_cli_invocation` (non regressione).

## Note di scope / tracciamento (Out-of-Scope promossi)
- Consumo attivo della traccia all'avvio → **Could** epica debito-tecnico (oltre l'induzione `degraded`
  di FEAT-011).
- Portabilità OS hook + onestà surface Copilot inerti → **FEAT-018**.
- Pulizia stile/altitude body + blocchi `CLAUDE.md` → **FEAT-021/FEAT-022**.
Nessun rinvio reale resta sepolto in `specs/`.

## Definition of Done
Hook in scope scrivono il breadcrumb sui path degradati (no-op gated escluso); i 3 body portano il
fallback host-agnostico byte-identico; le guardie (A lint breadcrumb, B fallback, C sync rag dogfood, D
RUNTIME_IGNORES) verdi; parità Copilot + sync esistenti verdi; `.sertor/.last-hook-error` ignorato e
rimosso dall'uninstall; `sertor_core` invariato.
