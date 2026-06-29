---
title: "FEAT-019: Fail-loud breadcrumb negli hook + fallback agente"
type: experiment
tags: [feat-019, hook, agent, fail-loud, principio-xii, deterministic, asset-distribution]
created: 2026-06-29
updated: 2026-06-29
sources: ["specs/077-fail-loud-hook-agent/spec.md", "specs/077-fail-loud-hook-agent/plan.md", "specs/077-fail-loud-hook-agent/tasks.md", "requirements/debito-tecnico/fail-loud-hook-agent/requirements.md"]
---

# FEAT-019: Fail-loud breadcrumb negli hook + fallback agente

**Implementazione completata** (2026-06-29, branch `077-fail-loud-hook-agent`): il primo step dell'epica **debito-tecnico** (E10) che realizza il **Principio XII «Fail Loud, Fix the Cause»** — non silenziosità sui degradamenti, ma **segnalazione esplicita e azionabile**.

## Contenuto tecnico

### Breadcrumb sugli hook PowerShell

**4 hook distribuiti** scrivono un file di stato ispezionabile `.sertor/.last-hook-error` quando degradano silenziosamente:
- `memory-capture.ps1` — non-bloccante (exit 0), logging silenzioso
- `rag-freshness.ps1` — tre path catastrofici (re-index fallito, smoke fallito) restano non-bloccanti
- `wiki-pending-check.ps1` — segnalazione hook-level se CLI fallisce
- `version-check.ps1` — auto-updater residuo

**Meccanismo univoco**:
- Funzione inline `Write-HookBreadcrumb` (byte-identica tra tutti gli hook) che scrive lo stato `.sertor/.last-hook-error`
- **Schema `hook.error/1`**: campi `hook`, `timestamp` (UTC), `reason` (string descrittivo, secret-free)
- **Sovrascritto** non accumulato: «ultimo errore visibile», no append-only
- **Gated su no-op**: es. `SERTOR_MEMORY` off → breadcrumb non scritto
- **Try/catch interno** mai fatale; exit sempre 0 su tutti i path
- **Footgun risolto**: in PowerShell, l'exit non-zero di `uv run` non solleva eccezione → si ispeziona `$LASTEXITCODE` oltre al `catch`

### Fallback agente uniforme: «asset mancante → STOP»

**3 agenti** (`concierge`, `wiki-curator`, `requirements-analyst`) ricevono un fallback **identico** host-agnostico:

```
Se l'asset principale di cui sei guscio (skill/playbook/... file X) 
non è leggibile o il body non si risolve:
  1. STOP (non procedere a vuoto)
  2. Segnala esplicitamente all'utente il percorso + motivo
```

**Implementazione**: testo fissato nei body agent markdown, **riusato byte-per-byte tra Claude e Copilot CLI** (nessun adattamento per-assistente). Fallback azionato su errore di `Read` nel primo passo.

### Kit e Principio XI

**ZERO dipendenza dal core**: gli hook non importano `sertor_core` né eseguono LLM.

**Kit**: nuovo path `.sertor/.last-hook-error` aggiunto a `RUNTIME_IGNORES` (non committa, non accumula sugli ospiti).

## Architettura del confine D↔N

| Livello | Cosa fa | Executor |
|---------|---------|----------|
| **Hook PS (D)** | Scrive breadcrumb JSON deterministico | PowerShell nativo |
| **Agent body (N)** | Legge breadcrumb su errore, segnala all'utente | LLM agente |

## Guardie anti-regressione

1. **Lint breadcrumb sui body `.ps1`**: nessun `catch` con `exit 0` senza `Write-HookBreadcrumb` prima
2. **Assert fallback sui 3 body agent**: testo presente e identico Claude↔Copilot
3. **Sync rag-hook dogfood**: byte-identità `.claude/hooks/` ↔ canonico del kit (prima scoperto il buco: non coperto da `test_assets_sync.py`)
4. **RUNTIME_IGNORES validazione**: `.sertor/.last-hook-error` non committa

## Esiti

- **SpecKit completo**: spec → plan → tasks → implement (branch `077`)
- **Constitution Check**: PASS 12/12 + missione, nessuna deroga
- **Complexity Tracking**: vuoto (no trade-off)
- **Test**: sertor 443 · sertor-flow 137 · kit 132 · root 1131 passed, 3 skip attesi (packaging `git+url`)
- **Ruff**: pulito
- **Core invariato**: verificato `git status src/sertor_core/`

## Follow-up (D↔N)

**Comportamento runtime del fallback agent** (CS-3, criterio di successo): agente ospite riceve asset non-risolvibile → STOP+segnala. Verificabile solo con **prova LIVE su ospite reale** (giudizio LLM); il done offline è raggiunto.

## Backlink

- [[step-ritual]] — conformità rituale di step (record + distill + lint)
- [[deterministic-vs-judgment]] — confine D↔N illustrato dalle guardie breadcrumb
- [[constitution]] — Principio XII fail-loud implementato
- [[assistant-targeting]] — parità byte-identica Claude↔Copilot
- [[sertor-installer]] · [[sertor-install-kit]] — hook distribution, RUNTIME_IGNORES
- [[feat-074-doctor-salute]] — gemella enforcement (`.rag-health.json` file di stato)

## Artefatti di design

Spec e plan nel ramo `077-fail-loud-hook-agent`:
- `specs/077-fail-loud-hook-agent/` (spec.md, research.md, data-model.md, contracts/*.md, quickstart.md, plan.md, tasks.md)
- `requirements/debito-tecnico/fail-loud-hook-agent/requirements.md`
